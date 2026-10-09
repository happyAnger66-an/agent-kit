import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import agentkit  # noqa: E402


def write(p: pathlib.Path, text: str) -> pathlib.Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    return p


def make_kit(tmp_path, standard_fm: str, profile: str, budget: int = 2000):
    write(tmp_path / "agentkit.toml", f"""
        [budget]
        always_on_tokens = {budget}
        [[sources]]
        id = "ext"
        [[targets]]
        path = "~/repo"
        profiles = ["p"]
    """)
    write(tmp_path / "standards" / "x" / "rule-a.md", f"---\n{standard_fm}\n---\n\n# body\n")
    write(tmp_path / "profiles" / "p.toml", profile)
    cfg = agentkit.load_config(tmp_path / "agentkit.toml")
    standards = agentkit.load_standards(tmp_path)
    return agentkit.lint_standards(standards) + agentkit.lint_profiles(tmp_path, cfg, standards)


GOOD_FM = """id: rule-a
description: d
apply: always
owner: me
source: new
last_verified: 2026-10-09"""


def test_valid_kit_has_no_errors(tmp_path):
    assert make_kit(tmp_path, GOOD_FM, 'standards = ["rule-a"]\nsources = ["ext"]') == []


def test_missing_field_and_id_mismatch(tmp_path):
    fm = GOOD_FM.replace("owner: me\n", "").replace("id: rule-a", "id: other")
    errors = make_kit(tmp_path, fm, "standards = []")
    assert any("missing frontmatter 'owner'" in e for e in errors)
    assert any("must equal file name" in e for e in errors)


def test_globs_mode_requires_globs(tmp_path):
    errors = make_kit(tmp_path, GOOD_FM.replace("apply: always", "apply: globs"), "standards = []")
    assert any("requires 'globs'" in e for e in errors)


def test_unknown_references_are_reported(tmp_path):
    errors = make_kit(tmp_path, GOOD_FM, 'extends = ["nope"]\nstandards = ["missing"]\nsources = ["gone"]')
    assert any("unknown profile 'nope'" in e for e in errors)
    assert any("unknown standard 'missing'" in e for e in errors)
    assert any("unknown source 'gone'" in e for e in errors)


def test_always_on_budget_is_enforced(tmp_path):
    errors = make_kit(tmp_path, GOOD_FM, 'standards = ["rule-a"]', budget=1)
    assert any("exceeds budget" in e for e in errors)


def test_extends_cycle_is_reported(tmp_path):
    make_kit(tmp_path, GOOD_FM, 'extends = ["q"]')
    write(tmp_path / "profiles" / "q.toml", 'extends = ["p"]')
    cfg = agentkit.load_config(tmp_path / "agentkit.toml")
    errors = agentkit.lint_profiles(tmp_path, cfg, agentkit.load_standards(tmp_path))
    assert any("extends cycle" in e for e in errors)


def test_sync_writes_rules_and_check_passes(tmp_path):
    write(tmp_path / "agentkit.toml", """
        version = "0.1.0"
        [[targets]]
        path = "."
        mode = "managed"
        profiles = ["p"]
    """)
    write(tmp_path / "standards" / "rule-a.md", "---\n" + GOOD_FM + "\n---\n\n# 正文\n")
    write(tmp_path / "profiles" / "p.toml", 'standards = ["rule-a"]')
    write(tmp_path / "AGENTS.md", "# 手写\n\n<!-- agent-kit:begin -->\n<!-- agent-kit:end -->\n")
    cfg = tmp_path / "agentkit.toml"
    assert agentkit.main(["--config", str(cfg), "sync"]) == 0
    rule = tmp_path / ".cursor/rules/agent-kit/rule-a.mdc"
    assert "alwaysApply: true" in rule.read_text(encoding="utf-8")
    assert "正文" in rule.read_text(encoding="utf-8")
    assert "rule-a" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "# 手写" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert agentkit.main(["--config", str(cfg), "sync", "--check"]) == 0
    rule.write_text("changed\n", encoding="utf-8")
    assert agentkit.main(["--config", str(cfg), "sync", "--check"]) == 1

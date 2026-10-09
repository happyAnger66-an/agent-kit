#!/usr/bin/env python3
"""agent-kit CLI.

  lint          校验 standards/ 与 profiles/
  sync          按 profile 把规范生成到目标仓库
  sync --check  只比较，不写文件
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import sys
import tomllib

KIT_ROOT = pathlib.Path(__file__).resolve().parent.parent

APPLY_MODES = {"always", "globs", "on-demand"}
STANDARD_REQUIRED = ("id", "description", "apply", "owner", "source", "last_verified")
BEGIN = "<!-- agent-kit:begin -->"
END = "<!-- agent-kit:end -->"
RULES_DIR = pathlib.Path(".cursor/rules/agent-kit")


def load_config(path: pathlib.Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def expand(p: str, base: pathlib.Path) -> pathlib.Path:
    if p == ".":
        return base
    return pathlib.Path(os.path.expanduser(p))


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fm: dict[str, str] = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            fm[mm.group(1)] = mm.group(2).strip().strip("\"'")
    return fm


def body_of(text: str) -> str:
    return re.sub(r"^---\s*\n.*?\n---\s*", "", text, count=1, flags=re.S).strip() + "\n"


def yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- lint

def load_standards(kit: pathlib.Path) -> dict[str, tuple[pathlib.Path, dict, str]]:
    out = {}
    for p in sorted((kit / "standards").rglob("*.md")):
        if p.name == "README.md":
            continue
        text = p.read_text(encoding="utf-8")
        out[p.stem] = (p, parse_frontmatter(text), text)
    return out


def load_profiles(kit: pathlib.Path) -> dict[str, dict]:
    return {p.stem: load_config(p) for p in sorted((kit / "profiles").glob("*.toml"))}


def lint_standards(standards) -> list[str]:
    errors = []
    for stem, (p, fm, _) in standards.items():
        rel = p.relative_to(KIT_ROOT) if p.is_relative_to(KIT_ROOT) else p
        for key in STANDARD_REQUIRED:
            if not fm.get(key):
                errors.append(f"{rel}: missing frontmatter '{key}'")
        if fm.get("id") and fm["id"] != stem:
            errors.append(f"{rel}: id '{fm['id']}' must equal file name '{stem}'")
        if fm.get("apply") and fm["apply"] not in APPLY_MODES:
            errors.append(f"{rel}: apply must be one of {sorted(APPLY_MODES)}")
        if fm.get("apply") == "globs" and not fm.get("globs"):
            errors.append(f"{rel}: apply=globs requires 'globs'")
        if fm.get("last_verified"):
            try:
                dt.date.fromisoformat(fm["last_verified"])
            except ValueError:
                errors.append(f"{rel}: last_verified must be YYYY-MM-DD")
    return errors


def estimate_tokens(text: str) -> int:
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    return cjk + (len(text) - cjk) // 4


def resolve_ids(profiles: dict[str, dict], name: str, stack=()) -> tuple[list[str], list[str]]:
    errors = []
    if name not in profiles:
        return [], [f"unknown profile '{name}'"]
    if name in stack:
        return [], [f"profiles/{name}.toml: extends cycle {' -> '.join(stack + (name,))}"]
    prof = profiles[name]
    ids: list[str] = []
    for inc in prof.get("extends", []):
        nested, errs = resolve_ids(profiles, inc, stack + (name,))
        ids += nested
        errors += errs
    return ids + prof.get("standards", []), errors


def lint_profiles(kit: pathlib.Path, cfg: dict, standards) -> list[str]:
    errors = []
    budget = cfg.get("budget", {}).get("always_on_tokens", 2000)
    source_ids = {s["id"] for s in cfg.get("sources", [])}
    profiles = load_profiles(kit)
    for name, prof in profiles.items():
        for inc in prof.get("extends", []):
            if inc not in profiles:
                errors.append(f"profiles/{name}.toml: extends unknown profile '{inc}'")
        for sid in prof.get("standards", []):
            if sid not in standards:
                errors.append(f"profiles/{name}.toml: unknown standard '{sid}'")
        for src in prof.get("sources", []):
            if src not in source_ids:
                errors.append(f"profiles/{name}.toml: unknown source '{src}'")
        _, cycle = resolve_ids(profiles, name)
        errors += [e for e in cycle if "cycle" in e]

    seen = set()
    for name in profiles:
        ids, _ = resolve_ids(profiles, name)
        ids = list(dict.fromkeys(ids))
        always = [s for s in ids if s in standards and standards[s][1].get("apply") == "always"]
        tokens = sum(estimate_tokens(standards[s][2]) for s in always)
        if tokens > budget:
            errors.append(f"profiles/{name}.toml: always-on ~{tokens} tokens exceeds budget {budget} ({always})")
        seen.add(name)
    for target in cfg.get("targets", []):
        for prof in target.get("profiles", []):
            if prof not in profiles:
                errors.append(f"agentkit.toml target {target['path']}: unknown profile '{prof}'")
        if target.get("mode", "managed") != "managed":
            errors.append(f"agentkit.toml target {target['path']}: only mode=managed is implemented")
    return errors


def cmd_lint(args: argparse.Namespace) -> int:
    kit = args.config.resolve().parent
    cfg = load_config(args.config)
    standards = load_standards(kit)
    errors = lint_standards(standards) + lint_profiles(kit, cfg, standards)
    for e in errors:
        print(f"ERROR {e}")
    print(f"lint: {len(standards)} standards, {len(errors)} error(s)")
    return 1 if errors else 0


# ---------------------------------------------------------------- sync

def render_mdc(fm: dict, body: str, version: str) -> str:
    lines = ["---", f"description: {yaml_quote(fm['description'])}"]
    if fm["apply"] == "globs":
        lines.append(f"globs: {yaml_quote(fm['globs'])}")
    lines.append(f"alwaysApply: {'true' if fm['apply'] == 'always' else 'false'}")
    lines += ["---", "", f"<!-- generated by agent-kit {version} — do not edit -->", "", body]
    return "\n".join(lines)


def render_agents_block(items: list[tuple[str, dict]], version: str) -> str:
    lines = [BEGIN, "", f"由 agent-kit {version} 生成，不要手改。规范正文在 `.cursor/rules/agent-kit/`。", ""]
    for sid, fm in items:
        where = fm["apply"]
        if fm["apply"] == "globs":
            where = f"globs: {fm['globs']}"
        lines.append(f"- **{sid}**（{where}）：{fm['description']}")
    lines += ["", END]
    return "\n".join(lines) + "\n"


def splice_agents(text: str, block: str) -> str:
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        return pre + block + post.lstrip("\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n" + block


def planned_files(kit: pathlib.Path, cfg: dict, standards) -> dict[pathlib.Path, str]:
    """Return absolute path -> content for one sync."""
    version = cfg.get("version", "0")
    profiles = load_profiles(kit)
    out: dict[pathlib.Path, str] = {}
    for target in cfg.get("targets", []):
        root = expand(target["path"], kit)
        ids: list[str] = []
        for prof in target.get("profiles", []):
            nested, errs = resolve_ids(profiles, prof)
            if errs:
                raise SystemExit("sync: " + "; ".join(errs))
            ids += nested
        ids = list(dict.fromkeys(ids))
        missing = [s for s in ids if s not in standards]
        if missing:
            raise SystemExit(f"sync: unknown standards {missing}")
        items = [(s, standards[s][1]) for s in ids]
        for sid, fm in items:
            body = body_of(standards[sid][2])
            out[root / RULES_DIR / f"{sid}.mdc"] = render_mdc(fm, body, version)
        agents = root / "AGENTS.md"
        current = agents.read_text(encoding="utf-8") if agents.exists() else "# AGENTS\n"
        out[agents] = splice_agents(current, render_agents_block(items, version))
        claude = root / "CLAUDE.md"
        if not claude.exists() or claude.read_text(encoding="utf-8").strip() == "@AGENTS.md":
            out[claude] = "@AGENTS.md\n"
    return out


def extra_generated(root: pathlib.Path, expected: set[pathlib.Path]) -> list[pathlib.Path]:
    rules = root / RULES_DIR
    if not rules.exists():
        return []
    return sorted(p for p in rules.glob("*.mdc") if p not in expected)


def cmd_sync(args: argparse.Namespace) -> int:
    kit = args.config.resolve().parent
    cfg = load_config(args.config)
    standards = load_standards(kit)
    files = planned_files(kit, cfg, standards)
    roots = [expand(t["path"], kit) for t in cfg.get("targets", [])]
    extras = [p for root in roots for p in extra_generated(root, set(files))]
    diffs = []
    for path, content in files.items():
        actual = path.read_text(encoding="utf-8") if path.exists() else None
        if actual != content:
            diffs.append(path)
    if args.check:
        for p in diffs + extras:
            print(f"DIFF {p}")
        print(f"check: {len(diffs)} differ, {len(extras)} extra")
        return 1 if diffs or extras else 0
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for p in extras:
        p.unlink()
    print(f"sync: wrote {len(files)} file(s), removed {len(extras)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agentkit")
    ap.add_argument("--config", type=pathlib.Path, default=KIT_ROOT / "agentkit.toml")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("lint", help="validate standards and profiles")
    lp.set_defaults(func=cmd_lint)
    sp = sub.add_parser("sync", help="generate rules into configured targets")
    sp.add_argument("--check", action="store_true", help="compare only, do not write")
    sp.set_defaults(func=cmd_sync)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

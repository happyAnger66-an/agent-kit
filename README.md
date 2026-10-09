# agent-kit

个人仓库共用的 agent 规范。本阶段只有一条工作流：在这里改规范，同步成各工具能读的文件。不收录其他仓库的 skills。

```text
standards/   规范正文
profiles/    core、product-dev
tools/       agentkit lint | sync | sync --check
inbox/       以后放经验候选，现在是空的
```

```bash
python3 tools/agentkit.py lint
python3 tools/agentkit.py sync          # 写入 .cursor/rules/agent-kit/ 和 AGENTS.md
python3 tools/agentkit.py sync --check  # 生成结果和磁盘不一致则失败
python3 -m pytest -q tests
```

当前唯一目标是本仓库自己（`agentkit.toml` 里 `path = "."`）。要接到别的仓库，再加 `[[targets]]`。

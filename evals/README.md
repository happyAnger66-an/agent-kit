# evals

技能和规范的回归测试（第 3 阶段）。

每个被测技能一个目录 `evals/<skill>/`，放 3～10 个黄金任务：

```text
evals/<skill>/<case>/
  task.md      # 给 agent 的输入
  expect.md    # 期望行为
  check.sh     # 判定脚本，退出码 0 为通过
```

修改技能或升级 agent-kit 版本时，用固定模型重放这些任务，比较通过率、轮次和 token 消耗。

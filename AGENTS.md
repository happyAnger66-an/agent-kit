# 编辑 agent-kit

手写部分只放这里。规范正文在 `standards/`，改完运行：

```bash
python3 tools/agentkit.py lint
python3 tools/agentkit.py sync
python3 tools/agentkit.py sync --check
```

<!-- agent-kit:begin -->

由 agent-kit 0.1.0 生成，不要手改。规范正文在 `.cursor/rules/agent-kit/`。

- **respond-in-chinese**（always）：与用户交流一律使用简体中文；代码、标识符、提交信息按目标仓库约定
- **test-first**（always）：实现需求前先写测试，review 通过后再编码
- **bug-regression**（always）：修 bug 必须带回归测试，复现原失败路径
- **test-layout**（globs: tests/**,**/*_test.py,**/test_*.py）：测试代码放在 tests/，按被测对象组织，不与源码混排
- **arch-diagrams**（on-demand）：新项目立项或分层/公开类型变动时，先补架构图和类图，再写测试
- **synapsex-mlc-vla-boundary**（always）：公司级仓职责：通用 fused 核进 synapsex，DiT/模型 glue 只留 mlc-vla；勿混进上游 GR00T 或领域知识卡
- **perf-profiler-ab**（always）：负向或未达预期的性能改动收工前，必须用 profiler（nsys/ncu 等）做 A/B，禁止只交 wall-clock
- **perf-baseline-dual-track**（always）：抬全链路 baseline 必须交 stages+e2e 与 overall+per-dim；速度轨与精度轨分开，禁止只报 denoise

<!-- agent-kit:end -->

---
id: tvm-relax-core-boundary
description: tvm-relax 只管核心编译
apply: always
owner: zhangxa
source: inbox/2026-10-15-tvm-relax-core-boundary.yaml@48d4060（晓安哥 2026-10-17 批准晋升）
last_verified: 2026-10-17
---

# tvm-relax 边界

1. tvm-relax：只做 compiler+runtime；禁止新增通用/领域算子。
2. 算子进 synapsex。
3. 存量 libfpA_intB_gemm 等迁出前勿扩大表面积。
4. AiInfraKB 引用本标准与 synapsex-mlc-vla-boundary，不硬编码仓职责。

```text
# BAD：新增算子或扩 libfpA_intB_gemm
# GOOD：算子进 synapsex
```

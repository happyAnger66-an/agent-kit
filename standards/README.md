# standards

工具无关的规范正文。一条规范一个文件、一个关注点，由 adapter 生成 Cursor `.mdc`、`AGENTS.md` 片段等目标格式。

## frontmatter

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 与文件名一致，全局唯一 |
| `description` | 是 | 一句话，写成「什么时候生效 / 要求什么」 |
| `apply` | 是 | `always`（常驻）、`globs`（改到匹配文件时加载）、`on-demand`（按描述触发） |
| `globs` | apply=globs 时必填 | 逗号分隔 |
| `owner` | 是 | 维护人 |
| `source` | 是 | 来源路径@commit，或「新写」 |
| `last_verified` | 是 | `YYYY-MM-DD`，超期由整理流程提醒复核 |

## 写法

- 正文写清 why，并给一组 BAD / GOOD 示例。
- 能用 lint / hook / CI 检查的约束，优先做成检查，这里只留一句指向。
- `apply: always` 会进所有命中 profile 的常驻上下文，受 `agentkit.toml` 的 `budget.always_on_tokens` 约束。
- 只属于某一个仓库的规则留在那个仓库，不放这里。

---
layout: default
title: "Claude 的 usage_report / cost_report 被标为 legacy，如何迁移到 Analytics API 并正确传 beta header？"
description: "Claude 于 2026-10-29 发布 Usage and Cost Analytics API beta，同时将旧 Usage and Cost API 及部分 Enterprise 报表端点标为 legacy。了解新端点、beta header 和迁移入口。"
permalink: /news/claude-usage-cost-analytics-api-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#october-29-2026)

# Claude 的 usage_report / cost_report 被标为 legacy，如何迁移到 Analytics API 并正确传 beta header？

**结论：**Claude 平台在 2026 年 10 月 29 日发布了 Usage and Cost Analytics API beta，新接口是 `GET /v1/organizations/analytics/usage`（token 数和请求数）和 `GET /v1/organizations/analytics/cost`（美元成本）。每个请求都要带 `anthropic-beta: analytics-usage-cost-2026-08-24` 和 `anthropic-version` 两个请求头。旧的 Usage and Cost API，以及 Claude Enterprise Analytics API 里的 `usage_report`、`cost_report`、`user_usage_report`、`user_cost_report` 被标为 legacy，但官方写明**仍受支持**，发版说明里没有给出停用日期，所以现有报表不用紧急停掉，按官方迁移指南分批改即可。

依据：[Claude 平台发版说明（2026-10-29）](https://platform.claude.com/docs/en/release-notes/overview#october-29-2026)、[Usage and Cost Analytics API 文档](https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api)。

本文适合维护 Claude Console 或 Claude Enterprise 组织级用量、成本报表和看板的开发者。

## 先确认你用的是哪一套旧接口

官方给了两份迁移说明，先对号入座：

| 你现在调用的接口 | 组织类型 | 用什么 Key 调新接口 | 看官方哪一节 |
|---|---|---|---|
| `/v1/organizations/usage_report/messages`、`/v1/organizations/cost_report`（Usage and Cost API） | Claude Console | 原来的 Admin API Key，或带 `org:admin` 范围的 OAuth token（放在 `authorization: Bearer` 头） | Migrate from the Usage and Cost API |
| `/v1/organizations/analytics/` 下的 `usage_report`、`cost_report`、`user_usage_report`、`user_cost_report` | Claude Enterprise | 原来那把带 `read:analytics` 范围的 Key | Migrate from the Claude Enterprise usage and cost reports |

官方文档还提醒：Admin API 不对个人账户开放，要先在 Console 里建好组织。新接口的价值之一是同一套端点、参数和返回字段同时服务 Console 和 Enterprise 组织。

## beta header 怎么传：最小请求

官方快速上手示例（查 9 月第一周每天、每个模型的用量）：

```bash
curl --globoff "https://api.anthropic.com/v1/organizations/analytics/usage?\
starting_at=2026-09-01T00:00:00Z&\
ending_at=2026-09-08T00:00:00Z&\
time_bucket_width=1d&\
group_by[]=model&\
limit=10" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: analytics-usage-cost-2026-08-24" \
  -H "x-api-key: $ANTHROPIC_API_KEY"
```

要点：

- 请求头名是 `anthropic-beta`，值是 `analytics-usage-cost-2026-08-24`；`anthropic-version` 也必须带。
- 官方 SDK（`client.beta.organization.analytics.usage.list(...)`）和 `ant` CLI 会自动带上这两个头，并在你读取结果时自动翻页，此时 `limit` 只决定每页大小。
- 自己拼 HTTP 时，用 `--globoff` 或做好 URL 编码，避免 `group_by[]` 的方括号被 curl 当成通配。

## Console 迁移：哪些不变、哪些要改

官方写明不变的有：Admin API Key、`anthropic-version`、`starting_at`/`ending_at`、桶宽取值（`1m`、`1h`、`1d`）、方括号写法、翻页字段名，以及 token 和成本字段名。需要改的主要是这些：

- **参数名和默认值**：`bucket_width`（默认 `1d`）改成 `time_bucket_width`，**没有默认值**。要保留按天的行就显式传 `time_bucket_width=1d`；不传则返回整个时间段的汇总。
- **返回结构**：旧接口的 `data` 是按时间从旧到新的桶（含空桶），每桶里有 `results`；新接口的 `data` 是按 `order_by` 排好序的行，每行有自己的 `starting_at`/`ending_at`，维度在 `group`、指标在 `usage` 或 `cost`，没有用量的组合**不出行**。
- **分页**：`limit` 从「每页几个时间桶」变成「每页几行」（1～1000，默认 20）。
- **时间范围**：`starting_at` 不早于 2026-01-01 且在最近 365 天内；单次最多 31 天；用了 `time_bucket_width` 就必须传 `ending_at`；`1m` 桶单次最多 24 小时。更长的区间要拆成多次请求。
- **按人统计**：`account_ids[]`、`service_account_ids[]` 和对应的 `group_by` 改为 `actor_ids[]`（同样的带前缀 ID）加 `group_by[]=actor` 或 `actor_type`。
- **成本报表**：`group_by[]=description` 没有了，改按 `model`、`cost_type`、`token_type`、`context_window`、`service_tier`、`inference_geo`、`speed` 分组；`context_window[]` 改名 `context_windows[]`。
- **默认工作区**：旧接口里是 `workspace_id: null`，新接口返回默认工作区真实的 `wrkspc_` ID。

成本金额注意：新接口的 `amount` 是折扣后、抵扣额度前的成本，`list_amount` 是按目录价的成本，币种固定 `USD`，金额是以「美分」为单位、带 6 位小数的字符串，官方举例 `"41280.000000"` 等于 412.80 美元。

## Enterprise 迁移：主要差别

Enterprise 的 Key、最早日期、365 天回溯和 31 天跨度、多数筛选和维度名、`data_refreshed_at`、游标规则和组织级限流都沿用，**唯一新增的请求头就是这个 beta header**。需要改的：

- `usage_report`/`cost_report` 每个桶最多只给前 100 个分组；新接口返回所有有数据的组合。
- `user_usage_report`/`user_cost_report` 的「每个用户一行」，改为 `group_by[]=actor&actor_types[]=user_actor`；不加这个筛选还会多出非用户身份的行和一行 `actor: null`（无法归属的用量）。
- `user_ids[]` 改为 `actor_ids[]`；Claude Tag 的 `product` 值从 `claude-tag` 变为 `claude_tag`。
- `exclude_deleted_users` 必须配合 `group_by[]=actor`，否则返回 400。
- `1m` 桶单次最多 24 小时，用了 `time_bucket_width` 必须传 `ending_at`。

## 迁移后数据对不上：先查这几处

1. **数据延迟**：旧 Usage and Cost API 一般 5 分钟内出数；新接口通常 4 小时内刷新，最长可能 24 小时。每个响应都有 `data_refreshed_at`，这个时间之后的用量是缺失或不完整的。如果你原来靠旧接口做近实时告警，切换前要评估这个差别。
2. **数值还会被修正**：官方说明在月底后约 7 天内数值仍可能变化（例如 10 月 1 日的数据到 11 月 7 日左右才稳定）。要做最终对账，只查已结束至少 7 天的月份；要多次调用结果一致，把 `ending_at` 设在已看到的 `data_refreshed_at` 之前。
3. **筛选写错不报错**：新接口里拼错的 `models[]` 名称、不存在的 API Key 或工作区 ID 不会报错，而是**什么都匹配不到**，返回空结果。旧接口遇到未知 ID 会报错，所以迁移后结果为空时先检查筛选值。
4. **空桶要自己补零**：新接口没有用量的桶不出行，画时间序列时要补零。
5. **`inference_geo`、`service_tier`**：旧接口对无值的用量写 `"not_available"` 和 `"standard"`，新接口写 `null`。

## 用官方方法核对新旧报表

官方给的复现旧版日报的做法：传 `time_bucket_width=1d` 和原来相同的 `group_by[]`，用 `limit=1000` 翻完所有页，再按 `starting_at` 把行归组、缺的日期补零；加 `order_by=time&order=asc` 可以让日期按从早到晚返回。

建议的核对顺序：

1. 选一个已结束至少 7 天的完整时间段，同时用旧接口和新接口取数。
2. 先比总量（token 总数、成本总额），再比按模型、工作区、API Key 或 actor 分组的结果。
3. 确认下游 SQL、看板和告警没有依赖已删除的字段（如成本报表的 `description`）或旧的 `null` 默认工作区写法。
4. 新旧并行一段时间、核对无误后再切换；旧接口仍受支持，可以保留作回退。

## 常见问题

**不迁移会怎样？**官方目前只说旧接口是 legacy、仍受支持，没有公布停用日期；以后如有变化，以发版说明为准。

**想查 Claude Code 每个人的成本怎么写？**官方答案是调用成本接口，带 `products[]=claude_code&group_by[]=actor`。

**这两个接口能用模型调用的普通 Key 吗？**不能。Console 组织要用 Admin API Key 或 `org:admin` OAuth token，Enterprise 要用 `read:analytics` 范围的 Key；第三方中转平台发的 Key 也不是这类组织管理凭据。

如果你还需要一个 OpenAI 兼容 / Claude 中转 API 入口来调用模型，可以[注册 OpenLux 并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-usage-cost-analytics-api-migration&utm_content=footer)。

## 官方一手来源

- https://platform.claude.com/docs/en/release-notes/overview#october-29-2026
- https://platform.claude.com/docs/en/manage-claude/usage-cost-analytics-api

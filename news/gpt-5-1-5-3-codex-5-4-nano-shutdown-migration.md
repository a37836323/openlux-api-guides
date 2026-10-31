---
layout: default
title: "gpt-5.1、gpt-5.3-codex、gpt-5.4-nano 将于 2027 年 4 月 1 日下线：换成 gpt-6-sol、gpt-6-luna 要改哪些参数"
description: "OpenAI 已公告 gpt-5.1、gpt-5.3-codex、gpt-5.4-nano 将于 2027 年 4 月 1 日下线，官方替代为 gpt-6-sol 和 gpt-6-luna。本文按官方弃用页、模型页和 GPT-6 迁移指南说明默认推理强度、Chat Completions 工具调用、采样参数和缓存参数要怎么改。"
permalink: /news/gpt-5-1-5-3-codex-5-4-nano-shutdown-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# gpt-5.1、gpt-5.3-codex、gpt-5.4-nano 将于 2027 年 4 月 1 日下线：换成 gpt-6-sol、gpt-6-luna 要改哪些参数

OpenAI 在 2026 年 10 月 1 日公告：`gpt-5.1`（含快照 `gpt-5.1-2025-11-13`）、`gpt-5.3-codex`、`gpt-5.4-nano`（含快照 `gpt-5.4-nano-2026-03-17`）已弃用，将于 **2027 年 4 月 1 日**从 API 移除。官方给的替代是：gpt-5.1 和 gpt-5.3-codex 换 `gpt-6-sol`，gpt-5.4-nano 换 `gpt-6-luna`。依据见 [OpenAI 弃用公告页](https://developers.openai.com/api/docs/deprecations)。

只改模型名不够。最容易出问题的是三处：GPT-6 默认推理强度从 `none` 变成 `medium`；Chat Completions 里带工具的请求只有在 `reasoning_effort` 为 `none` 时才能用；`temperature` 等采样参数在开启推理时必须删掉。下面按「查用量 → 对照差异 → 逐项修改 → 验证」的顺序说明。

## 哪些模型在这一批，官方让换成什么

| 下线日期 | 旧模型 ID（含快照） | 官方替代 | 旧模型推理强度可选值 |
|---|---|---|---|
| 2027-04-01 | `gpt-5.1`、`gpt-5.1-2025-11-13` | `gpt-6-sol` | none（默认）、low、medium、high |
| 2027-04-01 | `gpt-5.3-codex` | `gpt-6-sol` | low、medium、high、xhigh |
| 2027-04-01 | `gpt-5.4-nano`、`gpt-5.4-nano-2026-03-17` | `gpt-6-luna` | none（默认）、low、medium、high、xhigh |

注意区分：`gpt-5.1-codex`、`gpt-5.1-codex-max`、`gpt-5.1-codex-mini`、`gpt-5.1-chat-latest` 不在这一批，它们属于弃用页里 2026 年 4 月公告的那一批，已于 2026 年 7 月 23 日下线；项目里如果还有这些名字，同样要换掉。

官方没有写下线后具体返回什么错误码，只说到期后「模型将不再可访问」。所以不要等报错再改，按下面的步骤提前切换。

## 先查清楚项目里哪些地方在用

1. **搜代码和配置**：在代码、环境变量、部署配置里搜 `gpt-5.1`、`gpt-5.3-codex`、`gpt-5.4-nano`，快照 ID 也一起搜。搜 `gpt-5.1` 时会同时搜到 `gpt-5.1-codex` 等名字，要逐个确认是不是这一批。
2. **别漏了工具里的设置**：命令行编程工具、聊天客户端、自动化平台里手动填写的模型名，不在代码仓库里，同样要改。
3. **用接口确认下线日期**：弃用页说明，`GET /v1/models` 和 `GET /v1/models/{model}` 返回的模型对象里有可选字段 `shutdown_date`，有下线日期时是 `YYYY-MM-DD` 字符串，没有公告时为 `null`。可以把它加进巡检脚本，以后再有弃用也能提前发现。

## 换模型前先对照：旧模型和替代模型的差别

以下内容来自各模型的官方页面（[gpt-5.1](https://developers.openai.com/api/docs/models/gpt-5.1)、[gpt-5.3-codex](https://developers.openai.com/api/docs/models/gpt-5.3-codex)、[gpt-5.4-nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano)、[gpt-6-sol](https://developers.openai.com/api/docs/models/gpt-6-sol)、[gpt-6-luna](https://developers.openai.com/api/docs/models/gpt-6-luna)）：

| 项目 | gpt-5.1 | gpt-5.3-codex | gpt-5.4-nano | gpt-6-sol | gpt-6-luna |
|---|---|---|---|---|---|
| 默认推理强度 | none | 页面未写 | none | medium | medium |
| 支持 none | 是 | 否 | 是 | 是 | 是 |
| Chat Completions | 支持 | 不支持 | 支持 | 支持 | 支持 |
| Responses | 支持 | 支持 | 支持 | 支持 | 支持 |
| Batch | 支持 | 不支持 | 支持 | 支持 | 支持 |
| 最大输入 token | 页面未单列（上下文 400K） | 272K | 272K | 922K | 922K |

gpt-6-sol 和 gpt-6-luna 的推理强度可选 `none`、`low`、`medium`、`high`、`xhigh`、`max`，所以原来用到的档位都还能用。价格和计费规则以官方模型页为准；模型页写明，输入超过 272K token 的请求整单按更高倍率计费，原来受 272K 限制、换模型后打算塞更长上下文的，先看清这一条。

## 改模型名之外必须改的四件事

以下要求出自 OpenAI 的 [GPT-6 迁移指南](https://developers.openai.com/api/docs/guides/latest-model)（Migration quickstart 一节）。

**1. 把推理强度显式写回原来的有效值。** 官方要求「保留当前实际生效的推理强度」。gpt-5.1 和 gpt-5.4-nano 默认是 `none`，如果你从没设过推理强度，换成 gpt-6-sol / gpt-6-luna 后会按默认的 `medium` 推理，延迟和输出 token 都会变。想保持原来的行为，就显式写上 `none`：Responses 用 `reasoning.effort`，Chat Completions 用 `reasoning_effort`。gpt-5.3-codex 原来设的是哪档，就在 gpt-6-sol 上设同一档。

```json
{
  "model": "gpt-6-sol",
  "reasoning": { "effort": "none" },
  "input": "..."
}
```

**2. Chat Completions 里调用工具：要么设 none，要么换 Responses。** gpt-6-sol 和 gpt-6-luna 的模型页都写明，Chat Completions 只有在 `reasoning_effort` 为 `none` 时才支持函数调用；需要「推理 + 工具」的，官方要求改用 Responses API。原来在 gpt-5.1 上用 Chat Completions、同时开了 low 以上推理又带 `tools` 的请求，必须二选一。gpt-5.3-codex 原本就只支持 Responses，这一条不受影响。

**3. 开启推理时删掉采样参数。** 推理强度不是 `none` 时，要删除 `temperature`、`top_p`、`top_logprobs`；Chat Completions 还要删 `logprobs`，Responses 还要把 `message.output_text.logprobs` 从 `include` 里去掉。设为 `none` 的请求不受这一条限制。

**4. 提示缓存参数改名。** 从 GPT-5.5 及更早模型迁来时，官方要求把 `prompt_cache_retention` 换成 `prompt_cache_options.ttl`，取值 `"30m"`。按[提示缓存文档](https://developers.openai.com/api/docs/guides/prompt-caching)的模型差异表，旧模型用 `in_memory` / `24h`，GPT-5.6 及以后用 `"30m"`（默认）或 Responses 里的 `"12h"`，其他值返回 `400 invalid_request_error`；而且 GPT-5.6 及以后会单独收缓存写入费用，旧模型没有这一项。

## 想直接换 gpt-6.1-sol 时多注意一条

gpt-6-sol 的模型页提示有更新的 [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)。如果你跳过官方推荐的 gpt-6-sol、直接换 `gpt-6.1-sol`：迁移指南写明 GPT-6.1 Sol 不支持 `none`，原来用 `none` 的要改成 `low`；而且它在 Chat Completions 里不能调用工具，带工具的请求要走 Responses。迁移指南还提醒，已经在用 gpt-6-sol 的，换 6.1 Sol 前要再看一遍迁移说明。

## 改完怎么验证

1. **最小请求**：用新模型发一条不带工具的请求，确认返回 200、响应里的 `model` 是新模型。
2. **逐类回放**：把项目里每种请求形态（Chat Completions 带工具、Responses 带工具、结构化输出、流式、Batch）各挑几条真实样本，用新模型跑一遍，确认没有 400。出现 400 时，按上面四件事逐项对照：先看推理强度，再看是不是 Chat Completions 带了工具，最后看采样参数和缓存参数。
3. **比较效果和用量**：在相同推理强度下比较输出质量、延迟和 token 用量。官方建议原来用 `minimal` 的先从 `low` 开始，在代表性任务上比较后再定。
4. **确认没换到另一个快下线的模型**：对新模型调用 `GET /v1/models/{model}`，查看 `shutdown_date`。

## 通过 OpenLux 中转调用时

迁移步骤和直连 OpenAI 相同，区别只在地址和 Key：Base URL 填 `https://api.openlux.ai/v1`，请求头用 `Authorization: Bearer <你的 Key>`，Key 在 OpenLux 控制台「令牌」页创建。切换前先请求 `/v1/models`，能列出模型说明地址和 Key 都正确，再确认列表里有 `gpt-6-sol`、`gpt-6-luna`。具体在售模型和价格以 OpenLux 价格页为准。

需要一个同时提供 OpenAI 兼容和 Responses 接口的入口，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-5-1-5-3-codex-5-4-nano-shutdown-migration&utm_content=footer)。

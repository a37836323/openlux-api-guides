---
layout: default
title: "gpt-4o、gpt-4o-mini、gpt-4.1 将于 2027 年 1 月 14 日下线：换成 gpt-6-luna 要改哪些参数"
description: "OpenAI 已公告 gpt-4o、gpt-4o-mini、gpt-4.1、gpt-4.1-mini 将于 2027 年 1 月 14 日下线，官方替代为 gpt-6-luna。本文按官方弃用页和 GPT-6 迁移指南说明推理强度、temperature/logprobs、Chat Completions 函数工具、max_completion_tokens 与微调模型要怎么改，以及如何验证。"
permalink: /news/gpt-4o-gpt-4-1-shutdown-gpt-6-luna-migration/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# gpt-4o、gpt-4o-mini、gpt-4.1 将于 2027 年 1 月 14 日下线：换成 gpt-6-luna 要改哪些参数

如果你的项目还在用 `gpt-4o`、`gpt-4o-mini`、`gpt-4.1` 或 `gpt-4.1-mini`，现在就该排迁移了。OpenAI 在 2026 年 10 月 14 日发出弃用通知，[官方弃用页](https://developers.openai.com/api/docs/deprecations)写明这几个模型将于 **2027 年 1 月 14 日** 从 API 移除，四个模型的官方推荐替代都是 `gpt-6-luna`。

难点不在改模型名。GPT-4o 和 GPT-4.1 是不带推理步骤的模型，`gpt-6-luna` 是推理模型，默认推理强度为 `medium`。原样替换后，`temperature`、`logprobs` 和 Chat Completions 里的函数工具都可能出问题，延迟和 token 用量也可能变化。本文按官方文档说明要改哪些地方、怎么验证。适用于直接调用 OpenAI API，或通过 OpenAI 兼容中转调用的项目。

## 哪些模型在这一批，官方让换成什么

下表按官方弃用页「2026-10-14: GPT-4 series model deprecations」一节整理：

| 模型 | 本批涉及的快照 | 下线日期 | 官方推荐替代 |
|---|---|---|---|
| GPT-4o | `gpt-4o-2024-08-06`、`gpt-4o-2024-11-20` | 2027-01-14 | `gpt-6-luna` |
| GPT-4o mini | `gpt-4o-mini-2024-07-18` | 2027-01-14 | `gpt-6-luna` |
| GPT-4.1 | `gpt-4.1-2025-04-14` | 2027-01-14 | `gpt-6-luna` |
| GPT-4.1 mini | `gpt-4.1-mini-2025-04-14` | 2027-01-14 | `gpt-6-luna` |

几点补充：

- 代码里写的往往是不带日期的 `gpt-4o`、`gpt-4o-mini`、`gpt-4.1`、`gpt-4.1-mini`。这些别名的官方模型页状态都已标为 Deprecated，默认快照就是上表里的快照（例如 `gpt-4o` 默认是 `gpt-4o-2024-08-06`），所以也要一起迁移。
- 官方写明：基于这些模型的微调模型，与底座模型同一天下线。
- `gpt-4o-2024-05-13` 和 `gpt-4.1-nano` 不在这一批，它们已于 2026 年 10 月 23 日下线，见[上一批下线的迁移说明](https://a37836323.github.io/openlux-api-guides/news/openai-legacy-models-oct-23-shutdown-migration/)。

## 先查清楚项目里哪些地方在用

1. **全局搜索模型名**：在代码、环境变量、配置文件、数据库里的默认模型设置中搜 `gpt-4o`、`gpt-4.1`，包括带日期的快照名和以 `ft:` 开头的微调模型名。
2. **用接口查下线日期**：官方弃用页建议调用 `GET /v1/models`，看每个模型的可选字段 `shutdown_date`（`YYYY-MM-DD` 格式，没公布就是 `null`）；查单个模型用 Retrieve a model 接口。这适合在直连 OpenAI 时做自动巡检，提前发现下一批要下线的模型。
3. **区分 gpt-4o 系列的其他模型**：`gpt-4o-transcribe`、`gpt-4o-mini-tts` 这类语音模型有各自的弃用时间和替代模型，不按本文的 `gpt-6-luna` 处理，要单独查弃用页。

官方弃用页没有写下线后请求会返回什么报错原文，所以不要等到报错再改。

## 换成 gpt-6-luna 前要知道的差别

以下来自 [GPT-6 Luna 模型页](https://developers.openai.com/api/docs/models/gpt-6-luna)和 [GPT-6 使用与迁移指南](https://developers.openai.com/api/docs/guides/latest-model)：

| 项目 | gpt-6-luna 的官方说明 | 对迁移的影响 |
|---|---|---|
| 推理强度 | 支持 `none`、`low`、`medium`（默认）、`high`、`xhigh`、`max` | 不写就按 `medium` 推理，延迟和用量会变 |
| Chat Completions | 支持 | 原有接口可以继续用 |
| Chat Completions 函数调用 | 只在 `reasoning_effort` 为 `none` 时支持 | 要推理又要工具，得改用 Responses |
| 采样参数 | 推理强度不是 `none` 时要去掉 `temperature`、`top_p`、`top_logprobs`，Chat Completions 还要去掉 `logprobs` | GPT-4o 时代常写的参数要清理 |
| 输入类型 | 文本、图片；输出文本 | 原来的看图场景可以继续 |
| Batch | 支持 | 批处理任务可以迁过去 |
| Fine-tuning | 不支持 | 微调模型不能在 Luna 上重新训练 |

## 改模型名之外必须改的四件事

**1. 决定推理强度。** GPT-4o、GPT-4.1 本身没有推理步骤。如果想贴近原来不带推理步骤的用法，可以先显式写 `none`（Chat Completions 用 `reasoning_effort`，Responses 用 `reasoning.effort`）；如果想利用推理提升质量，再试 `low` 或 `medium`。官方迁移指南的建议是先保留现有的实际推理强度，再用代表性任务对比结果。

**2. 清理采样参数。** 迁移指南写明：推理强度不是 `none` 时，删除 `temperature`、`top_p` 和 `top_logprobs`；Chat Completions 还要删 `logprobs`，Responses 要从 `include` 里去掉 `message.output_text.logprobs`。如果原来写了 `temperature: 0` 之类的设置，开推理前要先删掉。

**3. 检查函数工具。** GPT-6 Luna 在 Chat Completions 里只在 `reasoning_effort: "none"` 时支持函数调用。原来用 Chat Completions 加 `tools` 的 GPT-4o 项目，有两条路：保持 Chat Completions 并显式设 `none`；或者按[迁移到 Responses API 的官方指南](https://developers.openai.com/api/docs/guides/migrate-to-responses)改用 Responses，再开推理。最小改法示例：

```jsonc
{
  "model": "gpt-6-luna",
  "reasoning_effort": "none",
  "messages": [{"role": "user", "content": "..."}],
  "tools": [/* 原来的工具定义 */]
}
```

**4. 改输出上限和缓存参数。** [Chat Completions 接口参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)写明 `max_tokens` 已弃用，改用 `max_completion_tokens`，后者的上限包含可见输出和推理 token。开推理后，原来给 GPT-4o 设的偏小上限要重新评估。另外，迁移指南写明从 GPT-5.5 或更早的模型迁移时，要把 `prompt_cache_retention` 换成 `prompt_cache_options.ttl`，设为 `"30m"`。

## 微调过 gpt-4o-mini 或 gpt-4.1 的项目

这类项目要早做计划：

- 微调模型与底座模型同一天下线，也就是 2027 年 1 月 14 日。
- GPT-6 Luna 模型页把 Fine-tuning 列为不支持，所以不能把训练数据直接拿到 Luna 上再训一遍。
- 官方弃用页的自助微调时间表还写明：2027 年 1 月 6 日起，现有活跃客户也不能再创建新的微调任务。

可行的做法是把微调模型学到的格式和规则改写进提示词，用 Structured Outputs（Luna 模型页列为支持）约束输出格式，再拿原来的评测集对比 Luna 在 `none`、`low` 等档位下的效果。

## 改完怎么验证

1. **模型列表**：请求 `GET /v1/models`，确认 `gpt-6-luna` 在列表里。
2. **最小请求**：用新模型名发一条短文本请求，确认正常返回。
3. **带工具的请求**：如果走 Chat Completions 加 `tools`，确认请求里有 `reasoning_effort: "none"`，并能正常返回工具调用。
4. **回归对比**：用原来的代表性样本跑一遍，比较结果、延迟和 token 用量，再决定推理强度要不要调高。

全部通过，且日志和配置里不再出现本批模型名，就算迁移完成。

## 通过 OpenLux 中转调用时

OpenAI 兼容接口的 Base URL 填 `https://api.openlux.ai/v1`，Key 在 OpenLux 控制台「令牌」页创建。按上面第 1 步请求 `/v1/models`，能列出模型就说明地址和 Key 都对；Key 无效会返回 401 `Invalid token`。OpenLux 价格接口当前列出的 `gpt-6-luna` 支持 `openai`（Chat Completions）和 `openai-response`（Responses）两种接口类型，换模型时按上面四件事检查请求参数即可。

还没有账号可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-4o-gpt-4-1-shutdown-gpt-6-luna-migration&utm_content=footer)。

---
layout: default
title: "gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）"
description: "Gemini 官方弃用页把 gemini-3.1-flash-lite 的最早关停日期定为 2027-05-07，替代模型是 gemini-3.5-flash-lite：按官方模型页、新特性页和思考指南说明两者差异，以及 thinking_budget 与 thinking_level 同用 400、temperature 等采样参数被忽略、预填 model 回合 400 的改法和验证方法。"
permalink: /news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[Gemini API 弃用页、模型页与新特性页](https://ai.google.dev/gemini-api/docs/deprecations)

# gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）

先说结论：Gemini API 官方弃用页（[Gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations)）已经给 `gemini-3.1-flash-lite` 标了关停日期 2027 年 5 月 7 日，推荐替代模型是 `gemini-3.5-flash-lite`。官方说明这类日期是“最早可能”关停的日期，不是一定当天下线，但到期后再改就被动了。迁移本身不复杂：两个模型的上下文、输出上限和思考档位基本一致，**真正要改的是三类请求写法**——`thinking_budget` 与 `thinking_level` 混用、`temperature` 等采样参数、以及最后一轮是 `model` 的预填写法。

本文适用于直接调用 Gemini API（generateContent 或 Interactions），以及通过 OpenAI 兼容接口调用这两个模型的代码。价格以官方价格页为准，本文不写具体数字。

## 两个模型差在哪：先看对照表

下表来自两个模型的官方模型页（[gemini-3.1-flash-lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)、[gemini-3.5-flash-lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)）和思考指南。

| 项目 | gemini-3.1-flash-lite | gemini-3.5-flash-lite |
|---|---|---|
| 输入上限 | 1,048,576 tokens | 1,048,576 tokens |
| 输出上限 | 65,536 tokens | 65,536 tokens |
| 输入类型 | 文本、图片、视频、音频、PDF | 文本、图片、视频、音频、PDF |
| 输出类型 | 仅文本 | 仅文本 |
| 思考档位 | minimal（默认）、low、medium、high | minimal（默认）、low、medium、high |
| Computer Use | 不支持 | 支持 |
| Live API、图片/音频生成 | 不支持 | 不支持 |
| Batch、Flex、Priority | 支持 | 支持 |
| 关停日期 | 最早 2027-05-07 | 弃用页未列出 |

几点说明：

- 3.1 Flash-Lite 的档位表出自官方的 Gemini 3 开发者指南（该页已标注弃用、即将移除），3.5 Flash-Lite 的档位出自现行的[思考指南](https://ai.google.dev/gemini-api/docs/thinking)。两者默认都是 `minimal`，所以**只换模型名，默认思考强度不会变**。
- 官方明确写了 `minimal` 并不保证完全不思考，思考 token 也会计入输出上限并计费。
- 3.5 Flash-Lite 多了 Computer Use，3.1 Flash-Lite 的模型页把它列为不支持。

## 第一类改动：thinking_budget 和 thinking_level 不能同时出现

Gemini 3 开发者指南（针对 Gemini 3 系列，该页已标注弃用）写明：`thinking_budget` 仍然为向后兼容而保留，但**同一请求里不能同时带 `thinking_level` 和旧的 `thinking_budget`，否则返回 400**。官方推荐改用 `thinking_level`。

3.5 Flash-Lite 的新特性页（[What's new in Gemini 3.6 Flash and 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6)）在迁移清单里给的档位建议是：

1. 抽取、路由、分类这类任务，保持默认 `minimal`，吞吐最高。
2. 子代理、工具调用、多步骤任务，设成 `medium` 或 `high`，官方的说法是这样可以避免工具调用过早结束。
3. 复杂程度不一的文档解析，`minimal` 和 `high` 两种都试一下再定。

所以迁移时先在代码里搜一遍 `thinking_budget`、`thinkingBudget`：要么整段删掉改成 `thinking_level`，要么保持原样但确认没有同时再加 `thinking_level`。

## 第二类改动：temperature、top_p、top_k 会被忽略

新特性页写的 API 变化适用于 3.6 Flash、3.5 Flash-Lite 以及之后所有的 Gemini 模型：

- `temperature`、`top_p`、`top_k` 这三个采样参数现在会被 API **忽略**，官方说之后的模型代次会对它们返回 400。
- 官方建议直接从所有请求里删掉这三个参数。需要输出稳定时，在 system instruction 里写清楚明确的规则。

这一条最容易被忽略：在 3.5 Flash-Lite 上带着这些参数不会报错，但设置不会生效。如果你的代码靠调低 `temperature` 让输出稳定，迁移时要改成在 system instruction 里写规则。

另外新特性页写明 `candidate_count` 在 Gemini 3 及之后的模型上不支持，清单要求删除。

## 第三类改动：最后一轮是 model 的预填会返回 400

新特性页原文的意思是：**如果请求里最后一个非空回合是 `model` 回合，API 返回 400**。

有些代码习惯在 `contents` 最后放一个 `role: "model"` 的半句话（比如先写一个 `{`），引导模型接着输出 JSON。换到 3.5 Flash-Lite 后这种写法要改：

- 想固定格式：用结构化输出（3.5 Flash-Lite 模型页标注支持 Structured outputs），在请求里给出 JSON Schema。
- 想固定口吻或规则：写进 `system_instruction`。

改完后确认 `contents` 里最后一个非空回合不是 `model` 回合。

## 迁移步骤：按官方清单逐项做

3.5 Flash-Lite 的官方迁移清单有四步（另有一个可选的自动迁移技能），下面按顺序列出并补上该检查的位置，第 5 步是我们建议加上的：

1. **改模型名**：把 `gemini-3.1-flash-lite` 换成 `gemini-3.5-flash-lite`。代码、配置文件、环境变量、批处理任务的 JSONL 里都要搜一遍。
2. **按任务定思考档位**：抽取、路由、分类保持 `minimal`；代理和工具调用设 `medium` 或 `high`。
3. **删废弃参数、核对函数调用**：删掉 `temperature`、`top_p`、`top_k`、`candidate_count`，处理掉 `thinking_budget` 和 `thinking_level` 的重复；函数调用部分按 3.6 Flash 的同一套规则检查（清单提到多模态内容放进函数响应里、函数调用前出现文本导致 MALFORMED_FUNCTION_CALL 时参考官方的函数调用说明）。
4. **保留思维签名**：用无状态方式自己管理对话历史时，下一轮要把带签名的思考块原样传回去；用有状态方式时由服务端自动管理。
5. **灰度验证（建议）**：先拿一小部分流量切到新模型，对比输出质量和 token 用量，再全量切换。

## 通过 OpenAI 兼容接口调用时怎么设档位

Gemini 的 [OpenAI 兼容说明](https://ai.google.dev/gemini-api/docs/openai)里，`reasoning_effort` 和 Gemini 思考档位有一张映射表，其中 Gemini 3.1 Flash-Lite 一列是：`minimal`→`minimal`、`low`→`low`、`medium`→`medium`、`high`→`high`。不传 `reasoning_effort` 时使用模型自己的默认档位。

需要注意两点：

- 这张表里**没有 3.5 Flash-Lite 这一列**。想精确指定档位，可以按官方示例在 `extra_body` 的 `google.thinking_config.thinking_level` 里直接写档位。
- 官方说 `reasoning_effort` 和 `extra_body` 里的思考设置功能重叠，**不能同时使用**，二选一。

## 换完以后怎么验证

用 generateContent 发一个最小请求，看三个地方：

1. 返回 200，并且有正常的回答文本。
2. 响应里的 `modelVersion` 显示实际使用的模型版本，确认已经是 3.5 Flash-Lite。
3. `usageMetadata` 里的 `thoughtsTokenCount` 是思考 token 数，`candidatesTokenCount` 是回答 token 数。用同一批样本对比切换前后，判断思考档位设得是否合适。

如果通过 OpenLux 这类中转调用，Gemini 原生接口的 Base URL 填 `https://api.openlux.ai`（不带 `/v1`），请求路径是 `/v1beta/models/gemini-3.5-flash-lite:generateContent`，Key 放在 `x-goog-api-key` 请求头里；OpenAI 兼容接口的 Base URL 填 `https://api.openlux.ai/v1`，用 `Authorization: Bearer`。返回 401 `Invalid token` 说明 Key 错了或没带。我们没有逐项验证中转是否原样返回 `modelVersion`，以实际响应为准。

## 常见报错和现象对照

| 现象 | 可能原因 | 改法 |
|---|---|---|
| 400，请求里同时有 thinking_level 和 thinking_budget | 两个参数不能同用 | 删掉 thinking_budget，只留 thinking_level |
| 400，contents 最后一条是 model 回合 | 预填写法不再支持 | 改用结构化输出或 system_instruction |
| 调了 temperature，输出没有变化 | 采样参数被忽略 | 删除参数，在 system instruction 里写规则 |
| 代理任务工具调用过早结束 | 默认 minimal 档位，官方建议这类任务调高 | 改成 medium 或 high |
| OpenAI 兼容接口同时传了 reasoning_effort 和 extra_body 思考设置 | 官方说明两者不能同时使用 | 二选一 |
| 401 Invalid token | Key 错误或没带 | 到控制台令牌页重新创建并核对请求头 |

## 小结

`gemini-3.1-flash-lite` 到 `gemini-3.5-flash-lite` 属于同级替换：上下文、输出上限、默认思考档位都没变，还多了 Computer Use。要改的就是三件事——不要让 `thinking_budget` 和 `thinking_level` 同时出现、删掉已经不生效的采样参数、去掉最后一轮是 `model` 的预填。距离最早关停日期还有半年，建议现在就先灰度一部分流量。

需要一个能同时调用 Gemini、GPT、Claude 的 API Key，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration&utm_content=footer)

## 同专题文章

- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)
- [Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些](https://a37836323.github.io/openlux-api-guides/news/gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

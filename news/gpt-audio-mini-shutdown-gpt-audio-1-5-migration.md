---
layout: default
title: "gpt-audio、gpt-audio-mini 将于 2027 年 1 月 20 日下线：换成 gpt-audio-1.5 要改哪些"
description: "OpenAI 将于 2027-01-20 移除 gpt-audio、gpt-audio-mini 等旧音频模型，替代为 gpt-audio-1.5；gpt-4o-audio-preview 已于 2026-05-07 关停。按官方弃用页、模型页、Audio in Chat Completions 指南和接口参考，说明接口不变、mini 无对应替代、voice 与音频格式取值、多轮音频 ID 有效期和迁移验证方法。"
permalink: /news/gpt-audio-mini-shutdown-gpt-audio-1-5-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# gpt-audio、gpt-audio-mini 将于 2027 年 1 月 20 日下线：换成 gpt-audio-1.5 要改哪些

结论先说：OpenAI 在 2026-07-20 宣布，Chat Completions 里的旧音频模型 `gpt-audio`（快照 `gpt-audio-2025-08-28`）、`gpt-audio-mini`（快照 `gpt-audio-mini-2025-12-15`），以及 `gpt-4o-audio`、`gpt-4o-mini-audio`，将于 2027-01-20 从 API 移除，官方替代统一是 `gpt-audio-1.5`。更早的 `gpt-4o-audio-preview` 已在 2026-05-07 关停，还在用它的请求要立即迁移。

好消息是接口不用换：`gpt-audio-1.5` 和旧模型一样只走 Chat Completions（`/v1/chat/completions`），`modalities`、`audio`、`input_audio` 的写法相同。大多数代码改一个模型名就能跑，但有几处要单独核对：mini 用户没有对应的 mini 替代、`gpt-audio-1.5` 只有一个不带日期的模型名、模型页列出的功能项和旧模型不完全一样，以及 `voice` 的取值要以接口参考为准。

本文只讲 Chat Completions 音频对话。`gpt-realtime` 系列（同一批下线，替代是 `gpt-realtime-2.1` / `gpt-realtime-2.1-mini`）走的是 Realtime 会话，不在本文范围；`tts-1` 等语音合成模型的迁移见 [tts-1、gpt-4o-mini-tts 下线迁移](https://a37836323.github.io/openlux-api-guides/news/tts-1-gpt-4o-mini-tts-shutdown-gpt-realtime-migration/)。

依据：OpenAI 官方 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[gpt-audio-1.5 模型页](https://developers.openai.com/api/docs/models/gpt-audio-1.5)、[gpt-audio 模型页](https://developers.openai.com/api/docs/models/gpt-audio)、[gpt-audio-mini 模型页](https://developers.openai.com/api/docs/models/gpt-audio-mini)、[gpt-4o-audio-preview 模型页](https://developers.openai.com/api/docs/models/gpt-4o-audio-preview)、[Audio in Chat Completions 指南](https://developers.openai.com/api/docs/guides/audio-chat-completions) 和 [Chat Completions 接口参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。

## 一、哪些模型受影响、换成什么

| 模型 / 快照 | 下线日期 | 官方替代 | 当前状态 |
|---|---|---|---|
| `gpt-audio`、`gpt-audio-2025-08-28` | 2027-01-20 | `gpt-audio-1.5` | 模型页标为 Deprecated |
| `gpt-audio-mini`、`gpt-audio-mini-2025-12-15` | 2027-01-20 | `gpt-audio-1.5` | 模型页标为 Deprecated |
| `gpt-4o-audio`、`gpt-4o-mini-audio` | 2027-01-20 | `gpt-audio-1.5` | 2026-07-20 公告所列 |
| `gpt-audio-mini-2025-10-06` | 2026-07-23 | `gpt-audio-1.5` | 已关停 |
| `gpt-4o-audio-preview` | 2026-05-07 | `gpt-audio-1.5` | 已关停（模型页列出的三个快照均标为 Shut down） |
| `gpt-4o-mini-audio-preview` | 2026-05-07 | 当时给的是 `gpt-audio-mini` | 已关停；`gpt-audio-mini` 本身也将下线，应直接换 `gpt-audio-1.5` |

弃用页对下线后的说法是：到关停时间，模型或接口将不再可访问（no longer be accessible）。官方没有写下线后具体返回什么报错，所以不要靠「等报错再改」，先按上表在代码和配置里全局搜一遍左列的名字，日期快照也要搜到。

## 二、新旧模型对照：哪些一样，哪些不一样

| 对比项 | gpt-audio / gpt-audio-mini | gpt-audio-1.5 |
|---|---|---|
| 支持的接口 | 只有 Chat Completions | 只有 Chat Completions |
| Responses、Realtime、Batch | 模型页标为 Not supported | 模型页标为 Not supported |
| 输入 / 输出 | 文本、音频 / 文本、音频 | 文本、音频 / 文本、音频 |
| 上下文窗口 | 128,000 | 128,000 |
| 最大输出 | 16,384 | 16,384 |
| 知识截止 | 2023-10-01 | 2024-09-30 |
| 模型页列出的功能 | gpt-audio：streaming、function_calling；gpt-audio-mini：function_calling、prompt_caching | streaming、function_calling |
| 快照 | 各有带日期的快照 | 只有 `gpt-audio-1.5` 一个名字 |

从这张表能看出三件事：

1. **接口和参数结构不变**，不需要像 TTS 那样改成 Realtime 会话，也不能换到 Responses API（`gpt-audio-1.5` 模型页把 Responses 标为不支持；Audio in Chat Completions 指南也写明这种音频对话用 Chat Completions）。
2. **mini 没有一对一替代**。`gpt-audio-mini` 的模型页把它描述为 GPT Audio 的低成本版本，而替代是完整版的 `gpt-audio-1.5`，费用会怎么变以官网价格页为准，迁移前先按自己的调用量估算。
3. **无法锁定日期快照**。`gpt-audio-1.5` 模型页只列了这一个名字，需要稳定行为的业务要靠自己的回归样本来盯输出变化。

## 三、迁移步骤

**第 1 步：改模型名。** 把请求里的 `model` 换成 `gpt-audio-1.5`，其他字段先保持不变。

**第 2 步：核对输出音频参数 `audio`。** 接口参考说明：请求 `modalities` 里含 `audio` 时，`audio` 必填，`voice` 和 `format` 都是必填字段。

- `format`：接口参考的说明文字写的是 `wav`、`mp3`、`flac`、`opus`、`pcm16` 之一（枚举里另有 `aac`）。官方示例用的是 `wav`。
- `voice`：接口参考的说明文字和枚举列表不完全一致。两处都出现的是 `alloy`、`ash`、`ballad`、`coral`、`echo`、`sage`、`shimmer`、`marin`、`cedar`，用这几个最稳妥；`fable`、`nova`、`onyx`、`verse` 只在其中一处出现，用之前先用一条请求验证。
- 自定义声音：可以传 `{ "id": "voice_1234" }` 这种对象；接口参考说明自定义声音必须由音频样本创建，用文本提示创建的声音只在 Live 里支持。

**第 3 步：核对输入音频 `input_audio`。** 用户消息里的音频片段写成 `{"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"} }`，接口参考写明 `format` 目前只支持 `wav` 和 `mp3`。如果上游传来的是别的格式，要先转码再发。

**第 4 步：检查多轮对话里引用旧音频的地方。** 响应的 `message.audio` 里有 `id`、`data`、`expires_at`、`transcript`。下一轮可以在 assistant 消息里写 `"audio": {"id": "..."}` 引用上一轮的音频回复，接口参考写明 `expires_at` 是这段音频在服务端不再可用于多轮对话的时间，所以引用只在它之前有效；会话跨度可能超过这个时间的，不要依赖音频 ID。

**第 5 步：如果用了函数调用或流式输出，单独回归一次。** 两项在 `gpt-audio-1.5` 模型页都列为支持；模型换了，上线前用真实样本跑一遍工具调用和流式输出。

## 四、按现象排查

| 现象 | 先查什么 |
|---|---|
| 调用 `gpt-4o-audio-preview` 或 `gpt-audio-mini-2025-10-06` 失败 | 这两个已关停，直接换 `gpt-audio-1.5` |
| 想把音频对话搬到 Responses API | `gpt-audio-1.5` 不支持 Responses，继续用 Chat Completions |
| `voice` 报参数错误 | 改用接口参考说明文字和枚举里都有的声音，例如 `alloy` |
| 输入音频报格式错误 | `input_audio.format` 只能是 `wav` 或 `mp3`，并确认 `data` 是 Base64 |
| 多轮对话里引用上一轮音频失败 | 看上一轮 `message.audio.expires_at` 是否已过，过期后不能再按 ID 引用 |
| 返回只有文字没有音频 | 检查 `modalities` 是否为 `["text", "audio"]`，且带了 `audio` 参数 |
| 原来用 mini 控制成本 | 没有 mini 替代，按官网价格页重新估算 |

## 五、改完怎么验证

用官方指南里的最小请求确认新模型能出音频（指南各语言示例都用 `gpt-audio-1.5`、`voice: "alloy"`、`format: "wav"`）：

```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{ "model": "gpt-audio-1.5", "modalities": ["text", "audio"], "audio": { "voice": "alloy", "format": "wav" }, "messages": [ { "role": "user", "content": "Is a golden retriever a good family dog?" } ] }'
```

成功标准：

1. 返回 200，响应里的 `model` 是 `gpt-audio-1.5`；
2. `choices[0].message.audio.data` 有 Base64 内容，解码保存成 `.wav` 能正常播放；
3. `choices[0].message.audio.transcript` 有文字；
4. 再发一条带 `input_audio`（`wav` 或 `mp3`）的请求，模型能回答录音内容；
5. 代码和配置里全局搜索第一节左列的模型名，结果为零。

## 六、常见问题

**现在就要换吗？** `gpt-audio` 和 `gpt-audio-mini` 的模型页已标为 Deprecated，弃用页给的移除日期是 2027-01-20。还在用 `gpt-4o-audio-preview` 的，它已经在 2026-05-07 关停，要马上换。其余的建议提前切换，留出回归时间。

**`gpt-realtime` 也在这一批里，能不能一起换成 `gpt-audio-1.5`？** 不能混用。弃用页给 `gpt-realtime` 的替代是 `gpt-realtime-2.1`，给 `gpt-realtime-mini` 的是 `gpt-realtime-2.1-mini`，它们走 Realtime 会话；`gpt-audio-1.5` 只支持 Chat Completions。

**通过 OpenAI 兼容中转调用要改什么？** 只改模型名和上面的参数，Base URL 不变。改之前先请求 `/v1/models`，确认 `gpt-audio-1.5` 在服务商的模型列表里，再发验证请求。

如需通过 OpenAI 兼容中转调用模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-audio-mini-shutdown-gpt-audio-1-5-migration&utm_content=footer)，在售模型和价格以价格页为准。

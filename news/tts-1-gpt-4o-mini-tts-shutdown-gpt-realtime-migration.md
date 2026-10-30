---
layout: default
title: "tts-1、gpt-4o-mini-tts 将于 2027 年 1 月 6 日下线：换成 gpt-realtime-2.1-mini 为什么不能只改模型名"
description: "OpenAI 将于 2027-01-06 移除 tts-1、tts-1-hd、gpt-4o-mini-tts，推荐替代 gpt-realtime-2.1-mini，但它不支持 /v1/audio/speech。按官方弃用公告、Text to speech 指南和 Realtime 文档，说明改用 Realtime WebSocket 的步骤、音色/语速/输出格式差异和验证方法。"
permalink: /news/tts-1-gpt-4o-mini-tts-shutdown-gpt-realtime-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# tts-1、gpt-4o-mini-tts 将于 2027 年 1 月 6 日下线：换成 gpt-realtime-2.1-mini 为什么不能只改模型名

结论先说：OpenAI 在 2026-10-01 的[弃用公告](https://developers.openai.com/api/docs/deprecations#2026-10-01-text-to-speech-models)里写明，`tts-1`、`tts-1-hd`、`gpt-4o-mini-tts`（含快照 `gpt-4o-mini-tts-2025-03-20`、`gpt-4o-mini-tts-2025-12-15`）将于 **2027 年 1 月 6 日**从 API 移除，推荐替代是 `gpt-realtime-2.1-mini`。这次不是换个模型名就行：[Text to speech 指南](https://developers.openai.com/api/docs/guides/text-to-speech)明确说这是「API 工作流的变化」，`gpt-realtime-2.1-mini` **不支持** `/v1/audio/speech`，只能走 Realtime API（WebRTC、WebSocket 或 SIP 连接）。

本文适用于：现在用 `/v1/audio/speech` 做朗读、配音、生成语音文件的服务端程序。在下线日期之前，现有的 Speech API 调用仍可继续使用，有时间先把迁移做完并验证。

## 哪些模型受影响

| 现在用的模型 | 官方移除日期 | 官方推荐替代 | 替代模型支持的接口 |
|---|---|---|---|
| `tts-1` | 2027-01-06 | `gpt-realtime-2.1-mini` | 仅 `v1/realtime` |
| `tts-1-hd` | 2027-01-06 | `gpt-realtime-2.1-mini` | 仅 `v1/realtime` |
| `gpt-4o-mini-tts`（`-2025-03-20`、`-2025-12-15`） | 2027-01-06 | `gpt-realtime-2.1-mini` | 仅 `v1/realtime` |

`tts-1` 和 `gpt-4o-mini-tts` 的模型页都已标为 Deprecated。[gpt-realtime-2.1-mini 模型页](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini)的接口表里，Speech generation（`v1/audio/speech`）、Chat Completions、Responses 都是 Not supported，只有 Realtime 是 Supported。所以把请求里的 `model` 直接改成 `gpt-realtime-2.1-mini` 再发到 `/v1/audio/speech`，是走不通的。官方没有给出下线后旧模型请求的报错原文，本文不做猜测。

## 先判断：你的代码要改哪几处

按下面三个问题逐个排查：

1. **调用的是不是 `/v1/audio/speech`**：SDK 里一般是 `audio.speech.create`。是的话，整段调用都要换成 Realtime 会话。
2. **有没有依赖 mp3、aac、flac 等文件格式**：Speech API 默认返回 mp3；Realtime 返回的是 base64 编码的音频块，格式只有 PCM、G.711 μ-law、G.711 A-law 三种（见下一节），需要文件的要自己转码。
3. **用的音色、语速、风格指令是什么**：部分音色和语速范围在 Realtime 里没有，需要换（见下一节）。

## Speech API 与 Realtime 的参数对照

下表的左列出自 [Speech API 参考](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create)和 Text to speech 指南，右列出自 [Realtime 会话指南](https://developers.openai.com/api/docs/guides/realtime-conversations)和 [Realtime 客户端事件参考](https://developers.openai.com/api/reference/resources/realtime/client-events)。

| 项目 | Speech API（tts-1 / gpt-4o-mini-tts） | Realtime（gpt-realtime-2.1-mini） |
|---|---|---|
| 调用方式 | 一次 HTTP 请求，返回音频文件 | 建立 WebSocket/WebRTC 会话，发事件、收事件 |
| 文本放在哪 | `input`，最长 4096 字符 | `response.create` 的 `instructions` 或会话里的消息 |
| 风格控制 | `instructions`（`tts-1`、`tts-1-hd` 不支持） | 会话或单次回复的 `instructions` |
| 内置音色 | 13 个；`tts-1` 系列只支持其中 9 个 | `alloy`、`ash`、`ballad`、`coral`、`echo`、`sage`、`shimmer`、`verse`、`marin`、`cedar` |
| 语速 | `speed`，0.25～4.0 | `session.audio.output.speed`，0.25～1.5 |
| 输出格式 | mp3（默认）、opus、aac、flac、wav、pcm | `audio/pcm`（只支持 24 kHz）、`audio/pcmu`、`audio/pcma` |
| 计费单位 | `tts-1` 按字符；`gpt-4o-mini-tts` 按文本输入 / 音频输出 token | 按文本、音频 token 计费，具体价格以官网价格页为准 |

迁移时最容易漏的三点：

- **`fable`、`nova`、`onyx` 不在 Realtime 的音色列表里**。原来用这三个音色的，要换成 Realtime 支持的音色，官方推荐 `marin` 或 `cedar`。
- **音色一旦出过声就不能改**：Realtime 会话里模型输出过一次音频后，这个会话的 `voice` 就不能再修改。需要不同音色时，在第一次出声前设好，或换新会话。
- **语速上限从 4.0 降到 1.5**：原来 `speed` 设到 1.5 以上的，需要调整预期。官方也说明可以在指令里让模型说快或说慢。

## 迁移步骤：用 WebSocket 在服务端生成语音

服务端程序（没有浏览器）按 [WebSocket 连接指南](https://developers.openai.com/api/docs/guides/voice-websockets?api=realtime)的方式连接；如果是浏览器或手机端播放，官方建议用 WebRTC。

**第一步：建立连接。** 连接 `wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1-mini`，请求头带 `Authorization: Bearer <你的 API Key>`。标准 API Key 只放在服务端。收到 `session.created` 事件说明会话已建立。单个 Realtime 会话最长 60 分钟。

**第二步：用 `session.update` 设定输出。** 只要音频输出时，把 `output_modalities` 设为 `["audio"]`，在 `audio.output` 里设格式和音色：

```json
{
  "type": "session.update",
  "session": {
    "type": "realtime",
    "model": "gpt-realtime-2.1-mini",
    "output_modalities": ["audio"],
    "audio": {
      "output": {
        "format": { "type": "audio/pcm", "rate": 24000 },
        "voice": "marin"
      }
    }
  }
}
```

**第三步：发 `response.create` 让模型念指定文本。** 官方「不带上下文的回复」示例的做法是把 `input` 设为空数组，在 `instructions` 里写「Say exactly the following:」加上要念的文字：

```json
{
  "type": "response.create",
  "response": {
    "input": [],
    "instructions": "Say exactly the following:\n今天的会议改到下午三点。"
  }
}
```

原来 `gpt-4o-mini-tts` 里写在 `instructions` 的语气要求（例如「语气轻快」），可以一并写进这里的指令。注意 `gpt-realtime-2.1-mini` 是推理模型，念出来的内容是模型生成的，需要用下面的转写结果核对。

**第四步：收集音频块。** 监听 `response.output_audio.delta` 事件，其中 `delta` 是 base64 编码的音频数据，逐块解码后拼接，或者直接转发给播放端。官方特别说明 `response.output_audio.done` 和 `response.done` 里**不含音频数据**，只有转写文本，只等这两个事件会拿不到声音。需要 mp3 等文件格式时，把拼好的数据自己转码。转码参数按你设的输出格式填：`audio/pcm` 只支持 24 kHz 采样率；官方 Realtime 指南里的 PCM 示例（音频输入方向）用的是 24 kHz 单声道 PCM16，其余细节以 Realtime 参考为准。

## 怎么验证迁移成功

1. **连接**：收到 `session.created`，且没有 `error` 事件。
2. **配置生效**：`session.update` 之后服务端会回 `session.updated`，核对其中的 `voice`、`output_modalities` 和输出格式是不是你设的值。
3. **有声音**：每次 `response.create` 都至少收到一个 `response.output_audio.delta`，解码后的字节数大于 0。
4. **内容正确**：把 `response.output_audio_transcript.done` 里的转写文本和原文逐字对比，数字、人名、专有名词要特别看。
5. **完成标准**：同一批原文用旧的 Speech API 和新流程各跑一遍，确认新流程的音色、语速可接受，转写与原文一致，再切换线上流量；切换后不再有请求发往 `/v1/audio/speech`。

## 常见问题

**能不能继续用 `/v1/audio/speech`，只换别的模型？** 弃用公告给出的替代只有 `gpt-realtime-2.1-mini`，而它不支持这个接口。Text to speech 指南也只说现有集成可以用到下线日期为止。

**只是想「生成一段音频文件」，也要上 Realtime 吗？** 弃用公告和 Text to speech 指南给这三个模型指定的迁移路径都是 Realtime API。服务端用 WebSocket、自己把音频块写成文件即可，不需要做成对话界面。官方音频总览里另有 Chat Completions 的音频输出，但弃用公告没有把它列为替代，本文不展开。

**通过中转调用怎么办？** 先确认中转是否同时提供旧模型和替代模型。以 OpenLux 为例，价格接口（`https://www.openlux.ai/api/pricing_new`）10 月 31 日列出的在售模型里有 `tts-1`、`tts-1-hd`、`gpt-4o-mini-tts`，接口类型标为 Text to speech，暂未列出 `gpt-realtime-2.1-mini`。下线日期前后的可用情况，以 OpenAI 公告和价格页为准。

一手来源：[OpenAI 弃用公告：Text-to-speech models](https://developers.openai.com/api/docs/deprecations#2026-10-01-text-to-speech-models)、[Text to speech 指南](https://developers.openai.com/api/docs/guides/text-to-speech)、[gpt-realtime-2.1-mini 模型页](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini)、[Realtime 会话指南](https://developers.openai.com/api/docs/guides/realtime-conversations)、[Realtime WebSocket 连接指南](https://developers.openai.com/api/docs/guides/voice-websockets?api=realtime)、[Realtime 客户端事件参考](https://developers.openai.com/api/reference/resources/realtime/client-events)、[Speech API 参考](https://developers.openai.com/api/reference/resources/audio/subresources/speech/methods/create)。

如需通过中转调用 OpenAI 语音模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=tts-1-gpt-4o-mini-tts-shutdown-gpt-realtime-migration&utm_content=footer)，在售模型和支持的接口以价格页为准。

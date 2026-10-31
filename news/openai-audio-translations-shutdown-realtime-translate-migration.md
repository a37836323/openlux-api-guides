---
layout: default
title: "OpenAI /v1/audio/translations 将于 2027 年 2 月 26 日下线：换成 gpt-realtime-translate 为什么不能只改模型名"
description: "OpenAI 将于 2027-02-26 下线 /v1/audio/translations（whisper-1 录音翻译成英文），替代是 /v1/realtime/translations 上的 gpt-realtime-translate，但只改模型名不能迁移。按官方弃用公告、转写指南、接口参考和 Realtime 翻译指南，说明新旧差异、迁移步骤、常见问题和验证方法。"
permalink: /news/openai-audio-translations-shutdown-realtime-translate-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# OpenAI /v1/audio/translations 将于 2027 年 2 月 26 日下线：换成 gpt-realtime-translate 为什么不能只改模型名

结论先说：OpenAI 已宣布 `/v1/audio/translations`（用 `whisper-1` 把录音翻译成英文的接口）在 2027-02-26 下线，官方给出的替代是 `/v1/realtime/translations` 上的 `gpt-realtime-translate`。新旧两边不是同一种调用方式：旧接口是上传一个音频文件、拿回一段英文文本；新接口要先建立翻译会话、持续推送音频流、再读取翻译事件。官方转写指南原话是：只在 `/v1/audio/translations` 请求里改模型 ID，不算完成迁移。

本文适用于还在调用 `/v1/audio/translations` 的项目。依据是 OpenAI 官方的 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[文件转写指南](https://developers.openai.com/api/docs/guides/speech-to-text)、[Create translation 接口参考](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)、[Realtime 翻译指南](https://developers.openai.com/api/docs/guides/realtime-translation) 和 [gpt-realtime-translate 模型页](https://developers.openai.com/api/docs/models/gpt-realtime-translate)。

## 一、官方时间线和影响范围

| 日期 | 事件 | 涉及内容 |
|---|---|---|
| 2026-08-26 | OpenAI 宣布弃用转写类模型 | `whisper-1`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`、`gpt-4o-transcribe-diarize`，以及 `/v1/audio/translations` 接口 |
| 2027-02-26 | 上述模型和接口下线 | 翻译接口的替代是 `v1/realtime/translations` |

转写指南写明，这个接口在 2027-02-26 之前仍可使用。也就是说现在不用急着停掉旧代码，但要在下线前把新流程接好、测完。如果你同时用 `/v1/audio/transcriptions` 做原语言转写，那部分的替代模型是 `gpt-transcribe`，与本文的翻译迁移分开处理。

## 二、为什么只改模型名不行：新旧接口对照

| 对比项 | 旧：`/v1/audio/translations` | 新：`/v1/realtime/translations` |
|---|---|---|
| 调用方式 | 一次 HTTP 请求，`multipart/form-data` 上传文件 | WebSocket 或 WebRTC 会话，持续推送音频 |
| 模型 | 只支持 `whisper-1` | `gpt-realtime-translate` |
| 输入 | flac、mp3、mp4、mpeg、mpga、m4a、ogg、wav、webm 文件 | base64 编码的 PCM16、24 kHz、单声道音频块 |
| 输出语言 | 只输出英文 | 由 `session.audio.output.language` 指定目标语言 |
| 输出内容 | 文本（`json`、`text`、`srt`、`verbose_json`、`vtt`） | 译文音频增量、译文文本增量、原语言文本增量 |
| 可选参数 | `prompt`（英文）、`temperature` | 文档只写了目标语言一项配置 |
| 计费方式 | 以官方价格页为准 | 模型页写明按音频时长计费，不按文本 token |

另外两点容易踩空：

- 模型页标明 `gpt-realtime-translate` 只支持 `v1/realtime/translations`，不支持 `v1/realtime`、Chat Completions 和 Responses。把它填进普通 Realtime 会话或聊天接口都不对。
- Realtime 翻译指南说明，这个模型是「同声传译」，不是对话助手：翻译会话不走对话和回复的生命周期，官方原话是「You don't call `response.create`」（不调用 `response.create`）。要工具调用或对话能力，官方指向的是 `gpt-realtime-2.1` 的普通 Realtime 会话。

## 三、先判断你属于哪种用法

**用法 1：会议、通话、直播等实时音频。** 这正是新模型的设计场景，按第四节接入即可。指南建议每个目标语言开一个会话；两人通话按方向各开一个；多人房间大约需要「正在说话的音轨数 × 目标语言数」个会话，每位说话人的音轨保持独立。

**用法 2：已经录好的音频文件，只要英文文本。** 官方指定的迁移路径仍是 Realtime 翻译，文档没有给出文件上传式的替代接口。要走官方路径，就需要在服务端把文件解码成 24 kHz 单声道 PCM16，再分块推送进翻译会话（指南说明 WebSocket 适合「已经拿到原始音频」的服务端场景），最后把 `session.output_transcript.delta` 拼成全文。另一种做法是先用 `gpt-transcribe` 转写原语言文字，再交给文本模型翻译——这是组合做法，不是官方迁移指引，译文质量需要自己评估。

**用法 3：依赖 `srt`、`vtt` 字幕或 `verbose_json` 的时间分段。** 旧接口可以直接返回这些格式；Realtime 翻译指南列出的服务端事件只有音频和文本增量，没有写时间戳或字幕格式。依赖字幕文件的项目要先确认新流程怎么生成时间轴，再安排切换时间。

## 四、迁移步骤（以服务端 WebSocket 为例）

1. **连接。** 地址是 `wss://api.openai.com/v1/realtime/translations?model=gpt-realtime-translate`，服务端用 `Authorization: Bearer <你的 Key>` 鉴权。浏览器端不要放标准 Key：官方做法是在服务端向 `/v1/realtime/translations/client_secrets` 申请短期 client secret，浏览器拿它走 WebRTC 的 `/calls`。
2. **设置目标语言。** 连上后发：

```json
{ "type": "session.update", "session": { "audio": { "output": { "language": "es" } } } }
```

官方示例用的是 `es`（西班牙语）。要保持旧接口「输出英文」的效果，就填英文对应的语言代码；指南没有列出完整的支持语言清单，上线前用短音频确认。

3. **推送音频。** 反复发送 `session.input_audio_buffer.append`，`audio` 字段放 base64 编码的 PCM16（24 kHz、单声道）。官方示例每块 4800 字节，约 100 毫秒。句子之间的静音也要照常推送，不要只推有声片段。
4. **读取事件。** `session.output_transcript.delta` 是译文文本，`session.input_transcript.delta` 是原语言文本，`session.output_audio.delta` 是 24 kHz PCM16 的译文音频；出错时读 `error` 事件里的 `error.code` 和 `error.message`。
5. **正常结束。** 停止推送后发 `{"type":"session.close"}`，然后继续读事件，直到收到 `session.closed` 再关闭连接。指南提醒：提前关连接可能丢掉还在输出的译文。官方示例给尾部输出留了 15 秒等待时间，可按需调整。

## 五、按现象快速定位

| 现象 | 原因 | 处理 |
|---|---|---|
| 把 `model` 改成新模型后仍请求 `/v1/audio/translations` | 该接口只支持 `whisper-1` | 改连 `/v1/realtime/translations` |
| 在 `v1/realtime` 或 Responses 里用 `gpt-realtime-translate` | 模型页标明只支持翻译接口 | 换成翻译专用地址 |
| 照普通 Realtime 写法发了 `response.create` | 翻译会话没有回复生命周期 | 去掉，只推音频、读事件 |
| 译文末尾缺一截 | 没等 `session.closed` 就断开 | 先发 `session.close`，收到 `session.closed` 再关 |
| 输出语言不对 | 没发或写错 `session.audio.output.language` | 连接后先发 `session.update` 设好目标语言 |
| 收不到译文或译文断续 | 先对照官方输入要求排查 | 核对是否为 PCM16、24 kHz、单声道，句间静音是否也照常推送 |

## 六、改完怎么验证

1. 选一段 30 秒到 1 分钟、语言与线上一致的样本录音，用旧接口跑一次，保存英文结果作对照。
2. 用新流程推送同一段音频，确认依次收到 `session.created`、文本增量事件，结束时收到 `session.closed`，过程中没有 `error` 事件。
3. 把 `session.output_transcript.delta` 拼成全文，与旧结果逐句对比，重点看专有名词和数字。
4. 下游如果依赖 `srt` / `vtt` 或时间分段，确认新流程能产出同样结构的数据，下游解析不报错。
5. 在 2027-02-26 之前完成切换，留出回退时间。

## 七、通过中转调用怎么办

先确认中转是否同时提供旧模型和替代模型，以及是否支持 Realtime 翻译这类 WebSocket 接口。以 OpenLux 为例，价格接口（`https://www.openlux.ai/api/pricing_new`）10 月 31 日列出的在售模型里有 `whisper-1`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`，接口类型标为 Speech to text，暂未列出 `gpt-realtime-translate`。实际可调用的模型以 `/v1/models` 返回和价格页为准。

一手来源：[OpenAI 弃用公告（2026-08-26 转写模型）](https://developers.openai.com/api/docs/deprecations)、[文件转写指南（Translations 小节）](https://developers.openai.com/api/docs/guides/speech-to-text)、[Create translation 接口参考](https://developers.openai.com/api/reference/resources/audio/subresources/translations/methods/create)、[Realtime 翻译指南](https://developers.openai.com/api/docs/guides/realtime-translation)、[gpt-realtime-translate 模型页](https://developers.openai.com/api/docs/models/gpt-realtime-translate)。

如需通过中转调用 OpenAI 语音模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-audio-translations-shutdown-realtime-translate-migration&utm_content=footer)，在售模型和支持的接口以价格页为准。

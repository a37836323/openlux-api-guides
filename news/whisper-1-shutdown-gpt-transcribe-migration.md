---
layout: default
title: "whisper-1 将于 2027 年 2 月 26 日下线：换成 gpt-transcribe 要改哪些参数（language、时间戳、字幕格式）"
description: "OpenAI 将于 2027-02-26 移除 whisper-1、gpt-4o-transcribe 等转写模型，文件转写替代为 gpt-transcribe。按官方弃用页、Speech to text 指南、模型页和接口参考，说明 language 改 languages、keywords 与 prompt 限制、时间戳和字幕格式仅 whisper-1 支持、流式与用量字段，以及迁移验证方法。"
permalink: /news/whisper-1-shutdown-gpt-transcribe-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# whisper-1 将于 2027 年 2 月 26 日下线：换成 gpt-transcribe 要改哪些参数（language、时间戳、字幕格式）

结论先说：OpenAI 在 2026-08-26 宣布，`whisper-1`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`（含 `gpt-4o-mini-transcribe-2025-12-15`）和 `gpt-4o-transcribe-diarize` 将于 2027-02-26 从 API 移除，官方替代是 `gpt-transcribe`（录好的音频文件）或 `gpt-live-transcribe`（麦克风、通话等实时音频）。

只做文件转写的，接口不用换：`gpt-transcribe` 仍走 `/v1/audio/transcriptions`。但从 `whisper-1` 迁过来不能只改模型名，至少有四处要核对：单个 `language` 换成数组 `languages`；`timestamp_granularities` 只支持 `whisper-1`；官方没有写明 `gpt-transcribe` 支持哪些 `response_format`；`prompt` 的写法和限制变了。本文按 whisper-1 用户最常用的参数逐项说明。

不在本文范围：说话人分离（diarize）的迁移见 [gpt-4o-transcribe-diarize 下线迁移](https://a37836323.github.io/openlux-api-guides/news/gpt-4o-transcribe-diarize-shutdown-diarized-json-migration/)；把外语音频翻成英文的 `/v1/audio/translations` 见 [audio/translations 下线迁移](https://a37836323.github.io/openlux-api-guides/news/openai-audio-translations-shutdown-realtime-translate-migration/)。

依据：OpenAI 官方 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[Speech to text 指南](https://developers.openai.com/api/docs/guides/speech-to-text)、[gpt-transcribe 模型页](https://developers.openai.com/api/docs/models/gpt-transcribe) 和 [Create transcription 接口参考](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)。

## 一、哪些模型受影响、换成什么

| 模型 / 接口 | 下线日期 | 官方替代 |
|---|---|---|
| `whisper-1` | 2027-02-26 | `gpt-transcribe` 或 `gpt-live-transcribe` |
| `gpt-4o-transcribe` | 2027-02-26 | `gpt-transcribe` 或 `gpt-live-transcribe` |
| `gpt-4o-mini-transcribe`、`gpt-4o-mini-transcribe-2025-12-15` | 2027-02-26 | `gpt-transcribe` 或 `gpt-live-transcribe` |
| `gpt-4o-transcribe-diarize` | 2027-02-26 | `gpt-transcribe` 或 `gpt-live-transcribe` |
| `/v1/audio/translations` | 2027-02-26 | `/v1/realtime/translations` |
| `gpt-4o-mini-transcribe-2025-03-20` | 2027-01-20（另一条公告） | `gpt-4o-mini-transcribe-2025-12-15`，它本身也在 2027-02-26 下线 |

怎么选：Speech to text 指南把 `gpt-transcribe` 定为转写「录好的、保持原语言」音频的推荐模型；音频还在从麦克风、通话或媒体流里持续进来时，走 Realtime 转写，推荐 `gpt-live-transcribe`。原来用 `whisper-1` 上传文件的，对应的就是 `gpt-transcribe`。

`gpt-transcribe` 模型页只标了两个支持的接口：`v1/audio/transcriptions` 和 Realtime 转写会话；`v1/audio/translations`、Batch、Chat Completions、Responses 都标为不支持。模型页也只列了 `gpt-transcribe` 一个名字，没有带日期的快照。

## 二、参数对照：whisper-1 和 gpt-transcribe 哪里不一样

| 参数 | whisper-1 | gpt-transcribe | 迁移时怎么改 |
|---|---|---|---|
| `language` / `languages` | 单个 `language`，ISO-639-1 | 数组 `languages`，取代 `language` | 改成数组，两个字段不要同时传 |
| `keywords` | 无 | 支持，作为术语提示 | 可选，把专有名词放这里 |
| `prompt` | 最多 224 token | 支持，与 `keywords`、`languages` 配合 | 超过模型长度上限会被整单拒绝 |
| `timestamp_granularities[]` | 支持，需 `verbose_json` | 指南写明只支持 `whisper-1` | 见第四节 |
| `response_format` | 示例里有 `verbose_json`、`text` | 官方未列出；指南说明返回含 `text` 和 `languages` 的 JSON | 按默认 `json` 解析 |
| `stream` | 不支持，传了会被忽略 | 支持 | 可选，见第五节 |
| 文件大小、格式 | 25 MB；mp3、mp4、mpeg、mpga、m4a、wav、webm | 同一接口，同样的说明 | 不变 |

## 三、迁移步骤

**第 1 步：全局搜模型名。** 在代码、配置和环境变量里搜 `whisper-1` 以及上表其它模型名，把文件转写请求的 `model` 改成 `gpt-transcribe`。弃用页只说到期后模型将从 API 移除，没有写会返回什么报错，不要等报错再改。

**第 2 步：`language` 改成 `languages`。** 指南原话是：对 `gpt-transcribe`，`languages` 取代单个 `language` 字段，不要两个都传。`languages` 是数组，可以写多个可能出现的语言。语言代码可以用 ISO 639-1（如 `en`、`fr`）、部分 ISO 639-3（如 `cmn`、`yue`），以及 `zh-cn`、`zh-tw`、`zh-hk` 这类区域代码；格式不对或不支持的代码会被拒绝。识别结果里的 `languages` 是检测到的语言，空数组表示没能可靠判断语言。

**第 3 步：整理 `prompt`，把术语挪到 `keywords`。** 指南建议：`prompt` 写对录音的背景描述，`keywords` 写预计会听到的原词，`languages` 写预期语言。有三条限制要注意：

- `keywords` 是提示，不保证出现在结果里；
- 每个关键词只占一行，不能含 `<`、`>`、回车、换行，否则整个请求被拒；
- `prompt` 超过模型长度上限也会整单拒绝。官方没有给出 `gpt-transcribe` 的具体上限，原来按 `whisper-1` 写的长提示词，迁移后先用真实请求测一下。

**第 4 步：注意 SDK 里的写法。** 官方 Python 示例里 `prompt` 是普通参数，`keywords` 和 `languages` 放在 `extra_body` 里：

```python
transcription = client.audio.transcriptions.create(
    model="gpt-transcribe",
    file=audio_file,
    prompt="A customer support call about a premium plan and account AC-42.",
    extra_body={
        "keywords": ["premium plan", "AC-42", "billing"],
        "languages": ["en", "fr"],
    },
)
```

用 curl 时数组字段每项一个 `-F`，例如 `-F 'languages[]=en' -F 'keywords[]=billing'`。

**第 5 步：核对用量字段。** 接口参考里转写结果的 `usage` 有两种：按 token（`type: "tokens"`）或按时长（`type: "duration"`），官方没有写明 `gpt-transcribe` 返回哪一种。原来按 `whisper-1` 写的对账逻辑，先看一条真实响应的 `usage.type` 再改。

## 四、要时间戳或 SRT/VTT 字幕怎么办

这是 whisper-1 用户迁移时最需要提前评估的一点：

- 接口参考写明，`timestamp_granularities`（`word`、`segment`）需要 `response_format` 设为 `verbose_json` 才生效；
- Speech to text 指南写明，`timestamp_granularities[]` 只支持 `whisper-1`，现有集成可以继续用 `whisper-1` 取词级或段级时间戳，直到 2027-02-26；
- 指南还说明字幕格式（subtitle formats）的示例用的是已弃用模型；接口参考对 `response_format` 只写了「支持的格式取决于模型」，没有列出 `gpt-transcribe` 支持哪些。

官方目前没有给出 `gpt-transcribe` 的时间戳或字幕替代方案。所以依赖时间戳、`srt`、`vtt` 或 `verbose_json` 的业务（字幕生成、按时间跳转、按段对齐），建议：

1. 先保留 `whisper-1` 跑这部分功能，并在 2027-02-26 之前留出改造时间；
2. 用一条真实请求测 `gpt-transcribe` 对你需要的 `response_format` 的实际返回，以返回结果为准，不要假设与 `whisper-1` 一致；
3. 关注弃用页和 Speech to text 指南的后续更新。

## 五、可选：用流式拿中间结果

`whisper-1` 不支持流式，传了 `stream=true` 也会被忽略；`gpt-transcribe` 支持。对已录好的文件开启 `stream=true` 后，会先收到 `transcript.text.delta` 事件，最后是 `transcript.text.done`，对 `gpt-transcribe` 来说最终事件里带 `languages`。原来等整段结果再处理的代码不用改；想更早展示文字的，可以改成按事件读取。

另外，`include` 里的 `logprobs` 在接口参考中只列了 `gpt-4o-transcribe`、`gpt-4o-mini-transcribe` 和 `gpt-4o-mini-transcribe-2025-12-15`，不含 `gpt-transcribe`，依赖置信度的逻辑要另行评估。

## 六、按现象排查

| 现象 | 先查什么 |
|---|---|
| 改成 `gpt-transcribe` 后报参数错误 | 是否同时传了 `language` 和 `languages`（指南要求只传 `languages`）；语言代码是否是支持的格式，不支持的会被拒绝 |
| 带 `keywords` 后整单报错 | 关键词里是否有 `<`、`>` 或换行 |
| 长 `prompt` 时报错、短的正常 | `prompt` 超过模型长度上限，缩短后重试 |
| 原来的时间戳没了 | `timestamp_granularities` 只支持 `whisper-1`，见第四节 |
| 想同时做翻译 | `gpt-transcribe` 不支持 `/v1/audio/translations`，按翻译迁移文章改 |
| 文件上传失败 | 是否超过 25 MB，格式是否在支持列表内 |

## 七、改完怎么验证

1. 用一段已知内容的短录音，按第三节第 4 步的写法发一次 `gpt-transcribe` 请求，确认返回里有 `text` 和 `languages`；
2. 拿同一批真实音频，分别用 `whisper-1` 和 `gpt-transcribe` 转写，人工核对专有名词、数字和语言是否正确；
3. 检查 `usage.type` 和对账逻辑；
4. 用到时间戳或字幕的接口单独确认是否仍走 `whisper-1`，并记下 2027-02-26 的截止时间。

成功标准：业务里不再有直接调用待下线模型的文件转写请求（必须保留时间戳功能的除外，且已排期），`gpt-transcribe` 请求返回正常，转写质量抽检通过。

如果你经第三方中转平台调用，先用 `/v1/models` 确认平台已上架 `gpt-transcribe` 再切换。

想用一个 Key 调用多家模型，可以在 [OpenLux 注册](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=whisper-1-shutdown-gpt-transcribe-migration&utm_content=footer)。

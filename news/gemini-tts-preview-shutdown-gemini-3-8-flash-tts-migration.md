---
layout: default
title: "Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些"
description: "Google 将 gemini-3.1-flash-tts-preview、gemini-2.5-flash-preview-tts、gemini-2.5-pro-preview-tts 的最早下线日期定为 2026-11-17，替代为 gemini-3.8-flash-tts 或 flash-lite-tts。按官方弃用页、发布说明、语音生成指南和模型页，说明两款怎么选、默认输出改为 WAV、文本按原文朗读、speech_metadata 写法和迁移验证方法。"
permalink: /news/gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[Gemini API Deprecations](https://ai.google.dev/gemini-api/docs/deprecations)

# Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些

结论先说：Google 在 Gemini API [弃用页面](https://ai.google.dev/gemini-api/docs/deprecations) 里把 `gemini-3.1-flash-tts-preview`、`gemini-2.5-flash-preview-tts`、`gemini-2.5-pro-preview-tts` 三个语音合成预览模型的下线日期定为 2026-11-17，替代是 9 月 22 日发布的 `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts`。弃用页说明这些日期是「最早可能下线的日期」，确切时间会提前通知，所以不要等到当天再改。

这次迁移不只是换模型名。按 [Gemini 3.8 Flash TTS 模型页](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts) 的迁移说明，有两处行为变了：一是输入文本会被当作逐字稿原样朗读，原来写在文本里的「Say cheerfully:」「Speaker 1:」这类指示可能被念出来；二是非流式请求的默认输出从无文件头的 PCM（`audio/l16`）改成了带 RIFF 头的 WAV。很多老代码会自己给 PCM 补 WAV 头，这部分要删掉。

本文只讲语音合成（TTS）。同一天下线的 `gemini-3.1-flash-live-preview`、`gemini-2.5-flash-native-audio-preview-12-2025` 替代是 `gemini-3.8-live`，走的是 Live API，不在本文范围；`gemini-3.8-flash-tts` 的模型页也写明它不支持 Live API。

依据：Google 官方 [弃用页面](https://ai.google.dev/gemini-api/docs/deprecations)、[Gemini API 发布说明](https://ai.google.dev/gemini-api/docs/changelog)、[语音生成指南](https://ai.google.dev/gemini-api/docs/speech-generation) 和 [gemini-3.8-flash-tts 模型页](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-tts)。

## 一、哪些模型受影响、换成什么

| 旧模型 | 发布时间 | 最早下线日期 | 官方替代 |
|---|---|---|---|
| `gemini-3.1-flash-tts-preview` | 2026-02-26 | 2026-11-17 | `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts` |
| `gemini-2.5-flash-preview-tts` | 2025-05-20 | 2026-11-17 | `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts` |
| `gemini-2.5-pro-preview-tts` | 2025-05-20 | 2026-11-17 | `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts` |

先在代码、配置文件和环境变量里全局搜这三个名字。发布说明对 Flash-Lite TTS 的描述是「为替代 `gemini-3.1-flash-tts-preview` 而做」，Flash TTS 则是新的旗舰档。

## 二、Flash TTS 和 Flash-Lite TTS 怎么选

两者共用同一套请求结构，官方说切换只需要改一个参数（模型名）。区别主要在定位和语言覆盖：

| 对比项 | gemini-3.8-flash-tts | gemini-3.8-flash-lite-tts |
|---|---|---|
| 官方定位 | 最高保真：表演感、复杂对话、方言、长篇朗读 | 快、成本低：大批量生产、实时语音代理、朗读功能 |
| 语言 | 130 多种 | 100 多种 |
| 单人 / 多人 | 支持 / 支持 | 支持 / 支持 |
| 声音设计、声音复刻 | 支持 | 支持 |
| 输入 / 输出 | 只收文本，只出音频 | 只收文本，只出音频 |

注意语言差异：语音生成指南列出了一批只有 Flash TTS 支持、Flash-Lite 不支持的语言，包括泰语、瑞典语、芬兰语、斯瓦希里语、缅甸语、立陶宛语、斯洛文尼亚语等。如果你的内容用到这些语言，只能选 Flash TTS。

`gemini-3.8-flash-tts` 模型页给出的限制是输入 8,192 token、输出 16,384 token；缓存、函数调用、结构化输出、思考、搜索接地等能力都标为不支持。Flash-Lite TTS 的 token 限制以官方页面为准。

## 三、默认输出变成 WAV：老代码要删掉手动补头

这是最容易出问题的一处。官方迁移说明的原意是：旧模型默认返回无文件头的原始 PCM（`audio/l16`），所以很多代码会自己写一个 WAV 头再存文件；Gemini 3.8 TTS 的非流式请求默认就返回带标准 RIFF 头的 WAV（`audio/wav`），要把手动补头的代码删掉。

| 请求方式 | 3.8 TTS 默认输出 | 怎么处理 |
|---|---|---|
| 非流式（unary） | WAV，24 kHz、单声道、16 位有符号小端 PCM，带 44 字节 RIFF 头 | 解码后直接存 `.wav`，不要再补头 |
| 流式（`stream: true`） | 无文件头的原始 PCM（`audio/l16`），24 kHz、单声道、16 位 | 按 PCM 处理，分块可以直接拼接 |
| 需要裸 PCM、mu-law 或 A-law | 显式指定格式 | Interactions API 在 `response_format.mime_type` 里设 `audio/l16`、`audio/mulaw`、`audio/alaw`；generateContent 对应的取值是 `AUDIO_L16` 等 |

Interactions API 还可以在 `response_format` 里设 `sample_rate`，例如 `24000`、`16000`、`8000`。如果要把多段音频拼成一段，官方建议要么直接请求原始 PCM，要么先去掉每段的 44 字节 WAV 头再拼接。

## 四、提示写法变了：文本按原文朗读

3.8 TTS 把 `text` 字段当作逐字稿，写进去的舞台说明会被念出来。迁移时按官方说明改四处：

1. 整段的语气、语速、音量、情绪，从文本里挪到 `speech_metadata.style`，例如 `"whispered urgently"`。
2. 说话人标签从文本里挪到 `speech_metadata.speaker`。Interactions API 把 `speech_metadata` 作为注解挂在每个文本块上，generateContent 则挂在每个 part 上。
3. 尖括号标签只用于一瞬间的声音事件，例如 `<short pause>`、`<laugh>`、`<sigh>`；即使正文是中文，标签也用英文。持续性的风格（比如整段耳语）放 `style`，不要用标签。
4. 原来写在提示里的长段「Audio Profile」「Director's Notes」人设，官方建议改成用声音设计（Voice design）做一个自定义声音，再用它的 `voice_...` ID，`style` 少写或不写。

另外，指南提醒不要在 `style` 里改年龄、性别或口音，也不要写「保持音色一致」这类元指令，这类写法反而会让声音漂移。想强调某个词，可以把它写成大写。

## 五、请求怎么写：官方 Interactions API 示例

语音生成指南的示例都用 Interactions API，SDK 版本要求是 Python `google-genai` 2.25.0 及以上、JavaScript `@google/genai` 2.24.0 及以上。单人朗读的写法（摘自官方示例）：

```python
interaction = client.interactions.create(
    model="gemini-3.8-flash-tts",
    input=[{
        "type": "user_input",
        "content": [{
            "type": "text",
            "text": "Have a wonderful day!",
            "annotations": [
                {"type": "speech_metadata", "style": "cheerful and friendly"}
            ],
        }],
    }],
    response_format={"type": "audio"},
    generation_config={"speech_config": [{"voice": "Kore"}]},
)
```

要点：单人时 `speech_config` 是数组 `[{"voice": "Kore"}]`；多人时是对象，写成 `{"speakers": [{"speaker": "Joe", "voice": "Puck"}, {"speaker": "Jane", "voice": "Kore"}]}`，并且每一轮文本都要在 `speech_metadata` 里写 `speaker`，和配置里的名字对应。SDK 里用 `interaction.output_audio` 取最后一段音频，原始 REST 响应里的 base64 音频在 `steps[].content[].data`。

预置声音有 Kore、Puck、Charon、Zephyr 等 30 个，更多声音可以通过 `GET /v1beta/voices` 查询。多人模式最多 2 个说话人，而且只能用预置声音；要在对话里用自定义或复刻的声音，官方做法是每个说话人分开生成，再拼接 PCM。

如果你现有代码用的是 generateContent，模型页的迁移说明同时给了 generateContent 的对应写法（`speech_metadata` 挂在每个 part 上、输出格式取值 `AUDIO_L16` 等），具体字段以官方页面为准。

## 六、迁移后怎么验证

1. 全局搜索第一节表格里的三个旧模型名，全部换成 `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts`。
2. 升级 SDK 到上面的最低版本。
3. 删掉为 PCM 手动补 WAV 头的代码；需要 PCM 的场景显式指定 `audio/l16`。
4. 把文本里的语气指示、说话人标签挪到 `speech_metadata`，再用一段带说话人和语气的样例生成一次。
5. 成功标准：非流式请求返回的文件能直接用播放器打开、开头没有被念出来的指示文字；多人对话里两个声音按 `speaker` 正确分配；流式请求拼接后的 PCM 能按 24 kHz、单声道、16 位正常播放。

## 七、常见问题

**下线日期一定是 11 月 17 日吗？** 弃用页写的是最早可能的下线日期，确切日期会提前通知。建议按 11 月 17 日之前完成迁移来安排。

**只改模型名够不够？** 不够。官方迁移说明列出的两处行为变化要一起处理：默认输出改为带 RIFF 头的 WAV，手动补 WAV 头的代码要删掉；文本按原文朗读，写在文本里的指示要挪到 `speech_metadata`。

**`gemini-3.8-flash-tts` 能用在 Live API 实时对话里吗？** 不能。模型页标明它不支持 Live API；实时语音对话看 `gemini-3.8-live`。

**通过中转调用要注意什么？** 先确认服务商的在售模型列表里有 `gemini-3.8-flash-tts` 或 `gemini-3.8-flash-lite-tts`，再用一段短文本发验证请求，按第六节的成功标准检查输出。

如需通过中转调用 Gemini、GPT、Claude 等模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration&utm_content=footer)，在售模型和价格以价格页为准。

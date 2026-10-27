---
layout: default
title: "gpt-4o-transcribe-diarize 将于 2027-02-26 下线：换成 gpt-transcribe 后拿不到 diarized_json 说话人标签怎么办"
description: "gpt-4o-transcribe-diarize 将于 2027-02-26 下线，官方替代 gpt-transcribe 的文档没有写 diarized_json 说话人标签。按只要文字、依赖说话人 A/B 分段、按名字标注或实时转写三种情况给出迁移做法，附 languages 参数、25 MB 限制和验证步骤。"
permalink: /news/gpt-4o-transcribe-diarize-shutdown-diarized-json-migration/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/deprecations)

# gpt-4o-transcribe-diarize 将于 2027-02-26 下线：换成 gpt-transcribe 后拿不到 diarized_json 说话人标签怎么办

结论先说：截至 2026 年 10 月 28 日，OpenAI 官方文档里，`diarized_json` 说话人分段（每段带 `speaker`、`start`、`end`）只在 `gpt-4o-transcribe-diarize` 上有说明；官方推荐的替代模型 `gpt-transcribe`，其模型页和转写指南都没有写说话人标签；Realtime 转写会话则明确不支持说话人标签。所以只把 `model` 改成 `gpt-transcribe`，官方文档没有说明还能拿到 `speaker` 字段。下线前可以继续用原模型，迁移方案要看你到底依赖哪部分功能。

本文适用于调用 `/v1/audio/transcriptions` 做录音转写、并用到说话人分段的项目。依据是 OpenAI 官方的 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[文件转写指南](https://developers.openai.com/api/docs/guides/speech-to-text)、[gpt-transcribe 模型页](https://developers.openai.com/api/docs/models/gpt-transcribe) 和 [API 更新日志](https://developers.openai.com/api/docs/changelog)。OpenAI 开发者社区里已有多位开发者讨论同一问题，官方人员在 10 月 19 日回复称已把反馈转给团队，目前没有给出新的方案。

## 一、官方时间线与替代模型

| 日期 | 事件 | 官方原文要点 |
|---|---|---|
| 2026-07-28 | 发布 `gpt-transcribe` 与 `gpt-live-transcribe` | 前者用于文件转写，后者用于低延迟流式转写；都支持转写上下文、关键词提示和多种预期语言 |
| 2026-08-26 | 宣布弃用转写模型 | `whisper-1`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`、`gpt-4o-transcribe-diarize` 被列入弃用 |
| 2027-02-26 | 上述模型下线 | 弃用页给出的替代是 `gpt-live-transcribe` 或 `gpt-transcribe` |

弃用页同时写明 `/v1/audio/translations` 也在同一天下线，替代是 `v1/realtime/translations`。转写指南提醒：只改翻译请求里的模型 ID 不算完成迁移。

## 二、先弄清你用到了哪些说话人功能

迁移前对照下表，确认代码里实际用到哪几项。右列是在 `gpt-transcribe` 官方文档里能否找到对应说明，「未写明」表示文档里没有提到，不等于确认不支持。

| 现在用到的功能 | `gpt-4o-transcribe-diarize` 的官方写法 | `gpt-transcribe` 文档 |
|---|---|---|
| 按说话人分段 | `response_format=diarized_json`，返回带 `speaker`、`start`、`end` 的 `segments` | 未写明 |
| 默认说话人标签 | 没给已知说话人时，按大写字母 `A`、`B` 依次标注 | 未写明 |
| 按名字标注说话人 | `known_speaker_names[]` 加 `known_speaker_references[]`，最多 4 段 2～10 秒的参考音频 | 未写明 |
| 超过 30 秒的音频 | 需把 `chunking_strategy` 设为 `"auto"` 或语音活动检测配置 | 未写明 |
| 流式返回 | `stream=true` 时每段完成发一个 `transcript.text.segment` 事件 | 支持 `stream=true`，未写说话人事件 |
| 上下文提示 | 不支持 prompt | 支持 `prompt`、`keywords`、`languages` |

按你的情况看下面对应的分支。

## 三、分支 1：只需要文字，不需要区分说话人

这种情况可以直接迁移。官方快速入门的最小请求只有文件和模型两项：

```bash
curl https://api.openai.com/v1/audio/transcriptions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -F file=@audio.mp3 \
  -F model=gpt-transcribe
```

要同步改三处：

1. **读取结果的代码**：`gpt-transcribe` 默认返回 JSON，包含 `text` 和检测到的语言数组 `languages`（如 `[{"code": "fr"}]`，检测不可靠时为空数组）。原来从 `segments` 里拼文字的代码要改成读 `text`。
2. **语言参数**：转写指南写明，`gpt-transcribe` 用 `languages` 取代单数的 `language`，两个字段不要同时传。
3. **上下文提示**：原来的 diarize 模型不支持 prompt；换成 `gpt-transcribe` 后可以用 `prompt`、`keywords` 提供领域词汇和上下文。

文件限制不变：单个文件最大 25 MB，支持 mp3、mp4、mpeg、mpga、m4a、wav、webm；更大的录音先压缩或切成不超过 25 MB 的片段。

## 四、分支 2：依赖「说话人 A / B」分段

社区帖里的开发者就是这种情况：没用已知说话人参考音频，只依赖 `diarized_json` 返回的标准说话人分段。官方目前没有给出替代写法，可选做法有两种：

**做法一：下线前继续用原模型，同时准备迁移。** 在 2027-02-26 之前，`gpt-4o-transcribe-diarize` 仍可按原写法调用：`response_format=diarized_json`，超过 30 秒的音频设置 `chunking_strategy`。定期查看 [弃用页面](https://developers.openai.com/api/docs/deprecations) 和 [更新日志](https://developers.openai.com/api/docs/changelog)，看官方是否补充说话人功能的替代说明。

**做法二：拆成「说话人分离 + 转写」两步。** 社区回复中有开发者提出：用一个独立的说话人分离工具（回复里举的例子是开源的 pyannote-audio）先得到每位说话人的时间段，再把音频交给 `gpt-transcribe` 转写。这是社区建议，不是 OpenAI 官方方案，第三方工具的效果需要自己评估。落地时注意：

1. 按时间段切音频时，转写指南提醒不要从句子中间切开，否则会丢失上下文。
2. 下游代码如果依赖 `A`、`B` 这样的标签和秒级 `start` / `end`，新流程要输出同样的结构，避免改动下游。
3. 每段单独请求时，可以用 `prompt`、`keywords` 传入领域词汇，减少专有名词转错。

## 五、分支 3：用了已知说话人参考音频，或需要实时区分说话人

- **按名字标注说话人**：`known_speaker_names[]` / `known_speaker_references[]` 在 `gpt-transcribe` 文档里没有对应参数。迁移后按名字标注这一步，要在你自己的说话人分离流程里解决。
- **实时场景**：转写指南写明，说话人标签只能通过 `/v1/audio/transcriptions` 获取，Realtime 转写会话不支持。用 `gpt-live-transcribe` 走 Realtime 转写会话时，同样不在支持范围内。

## 六、按现象快速定位

| 现象 | 原因 | 处理 |
|---|---|---|
| 换成 `gpt-transcribe` 后代码取不到 `segments` | 默认 JSON 只有 `text` 和 `languages` | 只要文字就改读 `text`；要说话人按分支 2 处理 |
| 同时传了 `language` 和 `languages` | 官方要求二者只传一个 | 改用 `languages` |
| 实时转写里找不到说话人字段 | Realtime 转写会话不支持说话人标签 | 说话人分段放到录音文件转写流程里做 |
| 文件超过 25 MB | 超出上传上限 | 压缩或切成不超过 25 MB 的片段 |

## 七、改完怎么验证

1. 选一段有两位以上说话人、时长超过 30 秒的样本录音，分别跑旧流程（`gpt-4o-transcribe-diarize` + `diarized_json`）和新流程。
2. 对比两边的全文文字、说话人数量和分段时间点；下游系统用新结果跑一遍，确认解析不报错。
3. 只用文字的项目，确认新请求返回 200 且 `text` 非空，`languages` 与录音语言一致。
4. 把切换完成时间定在 2027-02-26 之前，留出回退余量。

通过 OpenAI 兼容中转调用时，可用的模型以中转的 `/v1/models` 返回为准。截至本文写作时，OpenLux 价格接口列出的转写模型是 `whisper-1`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`（这三个同样在 2027-02-26 下线），没有列出 `gpt-4o-transcribe-diarize` 和 `gpt-transcribe`。

## 官方来源

- [Deprecations（2026-08-26 转写模型弃用表）](https://developers.openai.com/api/docs/deprecations)
- [File transcription 指南（说话人分段、语言参数、文件限制）](https://developers.openai.com/api/docs/guides/speech-to-text)
- [gpt-transcribe 模型页](https://developers.openai.com/api/docs/models/gpt-transcribe)、[gpt-4o-transcribe-diarize 模型页](https://developers.openai.com/api/docs/models/gpt-4o-transcribe-diarize)
- [Create transcription API 参考（TranscriptionDiarized 字段）](https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create)
- [API 更新日志](https://developers.openai.com/api/docs/changelog)
- [OpenAI 开发者社区讨论帖](https://community.openai.com/t/gpt-4o-transcribe-diarize-deprecation-diarize-json/1407710)

需要一个 OpenAI 兼容地址来调用 GPT、Claude 等模型，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-4o-transcribe-diarize-shutdown-diarized-json-migration&utm_content=footer)。

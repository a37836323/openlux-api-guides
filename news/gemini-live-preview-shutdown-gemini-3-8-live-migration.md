---
layout: default
title: "gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）"
description: "gemini-3.1-flash-live-preview 与 gemini-2.5-flash-native-audio-preview-12-2025 最早 2026-11-17 下线，官方替代 gemini-3.8-live。按官方迁移说明整理：删掉 thinkingLevel、函数调用默认改为 NON_BLOCKING、proactive_audio:false 会报错、情感对话移除，附排查表和验证步骤。"
permalink: /news/gemini-live-preview-shutdown-gemini-3-8-live-migration/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[Google Gemini API 文档](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)

# gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）

如果你的语音 Agent 还在用 `gemini-3.1-flash-live-preview` 或 `gemini-2.5-flash-native-audio-preview-12-2025`，需要在 **2026 年 11 月 17 日**前换成 `gemini-3.8-live`。Google 在 [Gemini API 弃用页](https://ai.google.dev/gemini-api/docs/deprecations) 上把这两个 Live 模型的下线日期列为 11 月 17 日，替代模型是 `gemini-3.8-live`。该页同时说明，表里的日期是模型「最早可能」下线的时间，所以不要指望到期后还能继续调用。

只把模型名改掉并不够。按 [gemini-3.8-live 模型页的迁移说明](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live)，下面几处行为变了，最容易出问题的是这三处：

- `thinking_level` 不再支持，要从 setup 里删掉；
- 函数调用默认改成异步（`NON_BLOCKING`），模型可能在工具结果回来之前就继续说话；
- proactive audio 一直开启，显式写 `proactive_audio: false` 会报错。

本文按官方文档整理改动清单、排查表和验证步骤。下文的文档内容都出自 Google 官方页面，链接放在每一节里。

## 哪些模型受影响、换成什么

弃用页列出的 11 月 17 日 Live 相关下线项如下：

| 将下线的模型 | 官方替代 | 最早下线日期 |
|---|---|---|
| `gemini-3.1-flash-live-preview` | `gemini-3.8-live` | 2026-11-17 |
| `gemini-2.5-flash-native-audio-preview-12-2025` | `gemini-3.8-live` | 2026-11-17 |

`gemini-3.8-live` 在 [2026 年 9 月 15 日的更新日志](https://ai.google.dev/gemini-api/docs/changelog) 里与 `gemini-3.8-live-extended-thinking` 一起正式发布（GA），前者是低延迟的默认选择，后者额外支持后台推理。模型页上 `gemini-3.8-live` 的版本标注为 Stable，输入上限 131,072 token、输出上限 65,536 token。

需要注意，模型页的迁移步骤是**按 `gemini-3.1-flash-live-preview` 写的**。从 `gemini-2.5-flash-native-audio-preview-12-2025` 迁移时，官方没有单独的步骤说明，但下面这些改动是 `gemini-3.8-live` 本身的规则，无论从哪个模型迁移都适用，建议逐条对照。

## 迁移清单：逐项对照官方说明

按模型页「Migrating」一节整理：

| 项目 | 3.1 Flash Live 预览版 | gemini-3.8-live | 你要做什么 |
|---|---|---|---|
| 模型名 | `gemini-3.1-flash-live-preview` | `gemini-3.8-live` | 改模型字符串 |
| 思考等级 | `thinkingLevel` 可选 minimal/low/medium/high，默认 minimal | 不支持 `thinking_level` | 从 setup 删掉 `thinking_level` 或整个 `thinking_config` |
| 函数调用 | 只能同步，发回工具结果后模型才回复 | 默认异步 `NON_BLOCKING` | 需要旧行为时在函数声明上写 `behavior: BLOCKING` |
| proactive audio | 不支持 | 一直开启 | 删掉 `proactive_audio: false`，它会报错 |
| 情感对话 | 不支持 | 迁移说明写明已移除 | 删掉 `enable_affective_dialog` |
| turn coverage | — | 默认 `TURN_INCLUDES_AUDIO_ACTIVITY_AND_ALL_VIDEO` | 只在需要时才发视频帧，控制上下文和费用 |
| 输出模态 | 音频 | 迁移说明写明只支持音频 | 要文字就开 output audio transcription |

其中「3.1 Flash Live 预览版」一列的思考等级和函数调用说明来自 [Live API 能力页](https://ai.google.dev/gemini-api/docs/live-api/capabilities) 的模型对比表。

## 改法一：删掉 thinkingLevel

3.1 Flash Live 预览版允许在 setup 里写 `thinkingLevel`，默认是 `minimal`。能力页和模型页都写明，`gemini-3.8-live` 不支持 `thinkingLevel`，「必须在 setup 里省略」。它采用的是交错推理（interleaved reasoning），不需要你设思考等级。

官方页面只说「不支持、需省略」，没有写明保留这个字段会返回什么错误。所以迁移时直接删掉最稳妥：

1. 在建立连接的 config 里搜 `thinking_level`、`thinkingLevel`、`thinking_config`、`thinkingConfig`；
2. 如果只用来设等级，就把整个 `thinking_config` 删掉；
3. 如果你还想看思考摘要，能力页说明可以通过 `includeThoughts: true` 开启。

如果业务确实需要可调的推理强度，官方提供的是另一个模型 `gemini-3.8-live-extended-thinking`：它支持 `thinkingLevel` 取 `low`、`medium`、`high`，**不支持 `minimal`**。所以从 3.1 预览版的默认值 `minimal` 迁过去时，要改成 `low` 起步。能力页给出的 Python 写法是：

```python
model = "gemini-3.8-live-extended-thinking"
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    thinking_config=types.ThinkingConfig(thinking_level="low", include_thoughts=True),
)
```

Extended Thinking 版还有一个差别：后台推理进行中时，`turnComplete: true` 不代表会话空闲，要看 `interaction_status` 是 `IN_PROGRESS` 还是 `IDLE`。另外它的函数调用只能异步，不支持阻塞模式和调度选项。

## 改法二：函数调用默认变成异步

这是行为差异最大的一处。在 3.1 Flash Live 预览版上，函数调用只能同步：模型收到工具调用后会一直等，直到你用 `send_tool_response` 发回结果才继续回复。到了 `gemini-3.8-live`，模型页写明「异步执行（`behavior: NON_BLOCKING`）现在是默认的函数调用模式」。

按 [Live API 工具使用文档](https://ai.google.dev/gemini-api/docs/live-api/tools) 的说明，非阻塞意味着函数在后台运行时，你仍然可以和模型继续交互。对语音 Agent 来说，常见现象是：工具还没返回，模型已经接着说话了；或者工具结果回来时，模型正在说别的事。

处理分两种情况：

1. **需要保持旧的「等结果再说」行为**：在函数声明上显式加 `behavior: BLOCKING`。模型页说明这是为了向后兼容保留的写法。
2. **接受异步**：在返回的 `FunctionResponse` 里用 `scheduling` 指定模型拿到结果后怎么做。工具文档代码里的取值是 `INTERRUPT`（马上打断并告诉你结果）、`WHEN_IDLE`（等当前的话说完）、`SILENT`（先不说，留到后面用）。能力页和模型页把第一个写作 `INTERRUPTED`，与工具文档代码不一致，写代码时以 SDK 示例里的枚举为准。官方 Python 示例：

```python
function_response = types.FunctionResponse(
    id=fc.id,
    name=fc.name,
    response={"result": "ok", "scheduling": "INTERRUPT"},
)
```

无论哪种情况，Live API 都不会自动处理工具结果，必须在客户端手动调用 `session.send_tool_response`。官方示例都把每个调用的 `id` 和 `name` 原样带回响应里，建议照做。

## 改法三：proactive audio、情感对话与 turn_complete

- **proactive audio 一直开启**：模型页写明，在 `gemini-3.8-live` 上设置 `proactive_audio: false` 会返回错误。如果旧代码为了保险显式关掉了它，要删掉这一行。
- **情感对话已移除**：迁移说明要求删除所有 `enable_affective_dialog` 设置。如果你从 2.5 原生音频预览版迁移、并且开过这个选项，也按这一条处理。
- **`send_client_content` 的语义**：可以在整个会话中使用，需显式标注 `user` 或 `model` 角色。设置 `turn_complete=true` 会**无条件打断**正在进行的生成；不带 `turn_complete` 发送时，服务端会等后续消息再回复。如果你在模型说话时追加文字上下文，又习惯每次都带 `turn_complete=true`，换模型后可能出现模型话说一半被打断的情况。
- **视频帧默认会送进模型**：turn coverage 默认包含所有视频，所以摄像头或屏幕共享场景要按需发帧，否则上下文和费用都会增加。

## 症状排查表

| 换模型后的现象 | 先查哪里 | 改法 |
|---|---|---|
| 设置了 `proactive_audio: false` 后报错 | config 里的 `proactivity` | 删掉该设置（3.8 Live 上它一直开启，官方写明关掉会报错） |
| setup 里还带着思考等级（官方要求省略） | `thinking_level` / `thinking_config` | 删掉；要可调推理改用 extended-thinking 版 |
| 工具还没返回，模型就继续说话 | 函数声明有没有写 `behavior` | 写 `behavior: BLOCKING`，或在响应里设 `scheduling` |
| 工具结果回来后模型没有提及 | `FunctionResponse` 的 `scheduling` | `SILENT` 会让模型先不说，改成 `INTERRUPT` 或 `WHEN_IDLE` |
| 模型话说一半被打断 | 发送 `send_client_content` 时是否带 `turn_complete=true` | 只在确实要结束本轮时才带 |
| 迁到 extended-thinking 版后 `minimal` 不生效 | `thinkingLevel` 取值 | 改成 `low` / `medium` / `high` |
| 收不到文字回复 | `response_modalities` | 输出只有音频，开启 `output_audio_transcription` 拿文字 |

## 迁移后的验证步骤

1. **最小连接**：用官方示例的写法建立会话，模型名 `gemini-3.8-live`、`response_modalities` 设为 `["AUDIO"]`，确认能打印出会话已建立。
2. **配置清理**：在代码库里搜索 `gemini-3.1-flash-live-preview`、`gemini-2.5-flash-native-audio-preview-12-2025`、`thinking_level`、`enable_affective_dialog`、`proactive_audio`，确认没有遗留。
3. **工具调用回归**：挑一个耗时较长的工具（例如查订单），分别用 `BLOCKING` 和默认的非阻塞各跑一次，确认对话节奏符合业务预期，结果确实被模型播报出来。
4. **打断回归**：在模型说话时追加一条文字上下文，确认没有因为 `turn_complete=true` 把正常的回答截断。
5. **转写**：如果业务要文字记录，开启 `output_audio_transcription`，确认每一轮都能拿到文字。能力页还提到 `input_audio_transcription` 可以带 `custom_vocabulary`，最多 1,000 个词，建议控制在 100 个左右。

以上五步都通过，再切换生产流量。下线日期之前留出回滚时间：迁移有问题时仍可短暂切回旧模型排查，但 11 月 17 日之后就不能再依赖它了。

## 常见问题

**Q：只改模型名能跑通吗？**
如果原来没设 `thinking_level`、没关 proactive audio、也没用函数调用，可能可以。但函数调用默认改为异步这一点会改变对话行为，有工具的 Agent 一定要做第 3 步回归。

**Q：`gemini-3.8-live` 支持哪些工具？**
模型页列出支持函数调用和 Google 搜索 grounding；不支持代码执行、URL context、文件搜索、Google 地图 grounding、结构化输出、缓存和 Batch API。原来依赖这些能力的流程要另外设计。

**Q：上下文窗口多大？**
能力页写明原生音频输出模型的上下文窗口是 128k token。长会话的压缩与恢复，参见官方 [Live API 会话管理文档](https://ai.google.dev/gemini-api/docs/live-api/session-management)。

如果你想用同一个 Key 调用 Gemini、GPT、Claude 等多个模型，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-live-preview-shutdown-gemini-3-8-live-migration&utm_content=footer)。各模型支持哪些接口类型，以 OpenLux 价格页的标注为准。

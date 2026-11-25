---
layout: default
title: "Gemini API 回答一直重复、表格横线刷屏或 JSON 里一串换行怎么办：按官方排错指南改提示词、Schema 与工具调用"
description: "Gemini API 回答一直重复、Markdown 表格分隔线变成一长串横线、结构化输出里一串 \\n 或反复调用工具怎么办：按 Google 官方排错指南的六种重复情况对号入座，改表格格式规范、转义序列、字段顺序与必填、系统指令，并检查 temperature、frequencyPenalty 与 thinking_level。"
permalink: /news/gemini-api-repetitive-output-table-loop-fix/
date: 2026-11-24
---

> 更新日期：2026-11-24 · 一手来源：[Google Gemini API 排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting)

# Gemini API 回答一直重复、表格横线刷屏或 JSON 里一串换行怎么办：按官方排错指南改提示词、Schema 与工具调用

Gemini API 的回答越写越长、同一句话反复出现、Markdown 表格的分隔线变成一长串 `-`，或者结构化输出里冒出一大串换行，Google 官方 [排错指南的「重复 token」一节](https://ai.google.dev/gemini-api/docs/troubleshooting#repetitive-tokens) 把它们归为六种情况，并分别给了原因和解决办法。最重要的一点：**调 temperature 只对较早的模型有用，Gemini 3 和 Gemini 4 要靠提示词和系统指令来改**。

本文适用于用 Google AI Studio 的 Key 调用 Gemini 原生接口，也适用于经中转平台调用 Gemini 模型。下面的改法都写在提示词、系统指令或 Schema 里，换哪个入口都一样生效。回答被截断见《[换成 gemini-4-argon 后回答被截断、返回空文本或报 400](https://a37836323.github.io/openlux-api-guides/news/gemini-4-argon-output-truncated-continuation-token-fix/)》，函数调用返回 `MALFORMED_FUNCTION_CALL` 见《[Gemini 函数调用返回 MALFORMED_FUNCTION_CALL 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-malformed-function-call-fix/)》。

## 先对号入座：六种重复现象和官方给的原因

下表按官方排错指南整理，「怎么改」一列是指南里的解决办法，后面几节分别展开。

| 你看到的现象 | 官方说的原因 | 怎么改 |
|---|---|---|
| Markdown 表格分隔线是一长串 `-` | 模型想把长表格在视觉上对齐，而 Markdown 本来就不需要对齐 | 在提示里给出表格格式规范和示例 |
| Markdown 表格里反复出现同样的 token | 同样是想对齐表格 | 加一句「表头后面立刻加 ' \|'」的指令 |
| 结构化输出里一串换行 `\n` | 输入里有 `\u`、`\t` 这类转义序列 | 输入改成 UTF-8 字符，并限定允许的转义序列 |
| 结构化输出里文字反复出现 | 提示里写的字段顺序和 Schema 不一致 | 提示里不要指定字段顺序，所有输出字段设为必填 |
| 反复调用同一个工具 | 模型丢了思考上下文，或被强制调用一个不可用的接口 | 系统指令里要求每次静默思考先用一句话回顾进度 |
| 普通文本绕圈子、来回说同样的话 | 模型卡在一个解决不了的请求上 | 开启思考时不要规定它怎么思考；要求简洁、不要重复 |

如果重复一直持续到输出上限，返回的 `finishReason` 会是 `MAX_TOKENS`。按官方 [generateContent API 参考](https://ai.google.dev/api/generate-content)，它的含义是「达到了请求里指定的最大 token 数」。看到 `MAX_TOKENS` 且正文里有大段重复，就按上表排查，不要只把上限调大。

## 表格横线刷屏：在提示里写明表格格式

官方给的表格格式规范有四条，大意如下，可以直接放进系统指令：

1. **分隔线**：表头下面必须有分隔线，每一列只用三个 `-`，更长的横线可能导致错误；只允许 `|:---|`、`|---:|` 或 `|---|` 这三种写法。
2. **不要对齐列**：一律用 `|---|`，几列就重复几次，例如三列是 `|---|---|---|`。
3. **简洁**：单元格内容简短。
4. **不要用空格补齐**：表头和单元格不要为了和别的内容一样宽而填很多空格，两边各一个空格就够，排版交给渲染器。

官方还建议在规范里附一个小表格做示例。如果表格里反复出现同样的 token，指南给的指令是：

```text
FOR TABLE HEADINGS, IMMEDIATELY ADD ' |' AFTER THE TABLE HEADING.
```

如果你用的是较早的模型，指南还提到可以把 temperature 调到 0.8 或更高；Gemini 3 和 4 不要指望这一招（原因见后文）。

## 结构化输出里一串换行或重复文字：改输入和 Schema

**一串 `\n`**：官方说的原因是输入里带了 `\u`、`\t` 之类的转义序列。改法两步：先把输入里的这类转义换成对应的 UTF-8 字符，再在提示里加上官方给的这句：

```text
In quoted strings, the only allowed escape sequences are \\, \n, and \". Instead of \u escapes, use UTF-8.
```

**同样的文字反复出现**：原因是提示里描述的字段顺序和 Schema 里的不一样。官方的办法是「提示里不要指定字段顺序」，并把所有输出字段设为必填。这和官方 [结构化输出文档](https://ai.google.dev/gemini-api/docs/structured-output) 的建议一致：尽量把属性标为 `required`，某个字段可能为空时用 `["string", "null"]` 这种写法允许 `null`，因为可选属性、`enum` 和 `anyOf` 分支会让输出语法的分支变多。

另外，结构化输出文档提醒：输出的 JSON 语法正确，不代表取值正确，程序里仍要自己校验字段值。

## 工具反复调用或文字绕圈子：改系统指令

**反复调用工具**：指南建议在系统指令末尾加上这句，并让模型同时检查任务是否已经完成：

```text
When thinking silently: ALWAYS start the thought with a brief (one sentence) recap of the current progress on the task.
```

同时检查有没有强制模型去调用一个实际上不可用的接口。如果模型连续调用工具太多次被系统终止，API 参考里对应的 `finishReason` 是 `TOO_MANY_TOOL_CALLS`。

**普通文本来回重复**：指南说这是模型卡在了一个它解决不了的请求上。开启思考时，不要在提示里规定模型该怎么思考；可以加上「Be concise」「Don't repeat yourself」这类要求。既然原因是请求解决不了，也可以回头检查请求本身是否缺少完成任务所需的信息。

## 先检查这几个参数，别越调越乱

- **temperature、top_p、top_k**：按排错指南的参数表，Gemini 3.6 及以后和 Gemini 4 会忽略这几个参数，更早的 Gemini 3 模型建议保持默认值；指南说以后的版本传这些参数会返回 400，官方要求从请求里删掉。所以「调高 temperature 治重复」只适用于较早的模型。
- **frequencyPenalty**：API 参考写明，较大的负值会让模型开始反复输出一个常见 token，直到达到 `max_output_tokens` 上限。请求里如果设了负的 `frequencyPenalty`，先删掉再试。
- **candidate count**：参数表注明 Gemini 3 和 4 不支持。
- **思考**：排错指南说 Gemini 3.x 默认开启思考，会增加延迟和 token 用量。按官方 [思考指南](https://ai.google.dev/gemini-api/docs/thinking)，想降低成本或延迟，用 `thinking_level` 调到 `low` 或 `medium`，而不是把 `max_output_tokens` 设得很小，后者会截断回答。

## 改完怎么验证

1. 用出问题的同一段输入重跑，看 `finishReason` 是否从 `MAX_TOKENS` 变回 `STOP`（API 参考里 `STOP` 是「模型自然停止或遇到停止序列」）。
2. 表格类输出：检查分隔线每列只有三个 `-`，单元格没有大段空格。
3. 结构化输出：用程序解析 JSON，字段齐全、没有成串的 `\n`，再校验取值。
4. 工具调用：数一下同一工具连续被调用的次数，确认任务完成后模型会停下来给出回答。
5. 多跑几次同类输入。重复问题不一定每次都出现，只跑一次不能说明已经改好。

## 走中转时要注意什么

上面的办法都在提示词、系统指令和 Schema 里，经中转平台调用 Gemini 模型同样适用，不需要为此改 Base URL 或 Key。以 OpenLux 为例：走 Gemini 原生格式时 Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，参数名按官方文档写；走 OpenAI 兼容格式时 Base URL 填 `https://api.openlux.ai/v1`，采样、思考等参数的写法以你所用接口的文档为准。排查时先按官方文档的写法确认问题是否消失，再对比不同入口的结果。

想用一个 Key 同时调用 Gemini、GPT、Claude 等模型，可以在 [OpenLux 注册](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-repetitive-output-table-loop-fix&utm_content=footer)，在控制台创建令牌后按本站接入教程配置。

## 同专题文章

- [Gemini API 用工具检索报 400「tool_search tool must be specified when using defer_loading」怎么办：defer_loading、tool_search 与无状态回传逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-tool-search-defer-loading-fix/)
- [Gemini API 函数调用报 400「content block is missing a thought_signature」怎么办：思维签名的回传规则与改法](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-missing-thought-signature-function-call-fix/)
- [Gemini API 返回空、finishReason 是 SAFETY 或 RECITATION、报「Request blocked due to safety violations」怎么办：提示被拦、回答被拦与安全设置逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-safety-recitation-blocked-empty-response-fix/)
- [Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱](https://a37836323.github.io/openlux-api-guides/news/gemini-4-carbon-api-price-november-30/)
- [Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)
- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

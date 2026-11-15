---
layout: default
title: "Gemini API 返回空、finishReason 是 SAFETY 或 RECITATION、报「Request blocked due to safety violations」怎么办：提示被拦、回答被拦与安全设置逐项排查"
description: "Gemini API 返回 200 却没有正文、finishReason 是 SAFETY/RECITATION/PROHIBITED_CONTENT，或 Interactions API 报 400 Request blocked due to safety violations：按官方文档区分提示被拦与回答被拦，打印 promptFeedback、finishReason、safetyRatings，再决定改写输入还是调整 safetySettings。"
permalink: /news/gemini-api-safety-recitation-blocked-empty-response-fix/
date: 2026-11-16
---

> 更新日期：2026-11-16 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/safety-settings?generate-content=true)

# Gemini API 返回空、finishReason 是 SAFETY 或 RECITATION、报「Request blocked due to safety violations」怎么办：提示被拦、回答被拦与安全设置逐项排查

Gemini API 请求成功（HTTP 200）却拿不到正文，或者 `finishReason` 是 `SAFETY`、`RECITATION`、`PROHIBITED_CONTENT`，基本都是**内容被拦了**，不是网络或 Key 的问题。按 Google 官方 [安全设置文档](https://ai.google.dev/gemini-api/docs/safety-settings?generate-content=true)，`generateContent` 的拦截结果分两处报告：提示被拦看 `promptFeedback.blockReason`，回答被拦看候选里的 `finishReason` 和 `safetyRatings`，而且**被拦的内容不会返回**。如果你用的是新的 Interactions API，被拦时不会返回 200，而是直接报 HTTP 400。

本文适用于用 Google AI Studio 的 Key 调用 Gemini 原生接口（`generateContent` 或 Interactions API），也适用于经中转平台走 Gemini 原生格式。回答被截断（`MAX_TOKENS`、`CONTINUATION`）见《[换成 gemini-4-argon 后回答被截断、返回空文本或报 400](https://a37836323.github.io/openlux-api-guides/news/gemini-4-argon-output-truncated-continuation-token-fix/)》，函数调用返回 `MALFORMED_FUNCTION_CALL` 见《[Gemini 函数调用返回 MALFORMED_FUNCTION_CALL 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-malformed-function-call-fix/)》。

## 第一步：分清是提示被拦，还是回答被拦

下表的字段含义出自官方 [generateContent API 参考](https://ai.google.dev/api/generate-content)。

| 你看到的现象 | 去看哪个字段 | 官方含义 | 先做什么 |
|---|---|---|---|
| 一个候选都没有 | `promptFeedback.blockReason` | 有值就表示提示被拦，不返回任何候选 | 改写提示 |
| 有候选但没有正文 | `candidates[].finishReason` | 模型停止生成的原因，如 `SAFETY`、`RECITATION` | 按下一节对照处理 |
| `finishReason` 是 `SAFETY` | `candidates[].safetyRatings` | 每个类别最多一条评级，写明类别和概率 | 看是哪个类别、哪一档概率 |
| 想知道更具体的原因 | `candidates[].finishMessage` | 只在 `finishReason` 有值时才填，说明停止原因 | 和 `finishReason` 一起打印 |
| 流式中间块里 `finishReason` 为空 | `finishReason` | 为空表示模型还没停止生成 | 不是错误，等最后一块 |

API 参考里还有两句话很关键：候选「要么全部返回，要么一个都不返回」；只有**提示本身有问题**时才会一个候选都没有，这时去看 `prompt_feedback`。所以先判断有没有候选，就能分出是输入还是输出出了问题。

## 第二步：把拦截原因打印出来

不要只读正文。官方 Python SDK（google-genai）的 [参考文档](https://googleapis.github.io/python-genai/genai.html) 把 `response.text` 标为 `str | None`，说明它只拼接第一个候选里的文本部分。被拦时没有正文可拼，所以要先查拦截字段：

```python
resp = client.models.generate_content(model="<模型 ID>", contents="...")
if resp.prompt_feedback and resp.prompt_feedback.block_reason:
    print("提示被拦：", resp.prompt_feedback.block_reason)
elif resp.candidates:
    c = resp.candidates[0]
    print(c.finish_reason, c.finish_message, c.safety_ratings)
```

用 REST 时直接看返回 JSON 里的 `promptFeedback`、`candidates[0].finishReason`、`candidates[0].finishMessage` 和 `candidates[0].safetyRatings` 这几个字段即可，字段名是驼峰写法，SDK 里是下划线写法。

## 第三步：按 finishReason / blockReason 对症处理

下表的含义出自 API 参考的 `FinishReason` 和 `BlockReason` 枚举，处理办法出自官方 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting)；指南没写具体办法的，只给出改写或删减输入这类建议。

| 值 | 出现在 | 官方含义 | 怎么改 |
|---|---|---|---|
| `SAFETY` | 提示或回答 | 因安全原因被标记 | 看 `safetyRatings`；对照请求里的安全设置，或改写内容 |
| `RECITATION` | 回答 | 因复述（与某些数据相似）被标记 | 让提示和上下文尽量独特；见下文关于 temperature 的说明 |
| `LANGUAGE` | 回答 | 使用了不支持的语言 | 换成支持的语言 |
| `BLOCKLIST` | 提示或回答 | 含禁用词表里的术语 | 去掉相关术语 |
| `PROHIBITED_CONTENT` | 提示或回答 | 可能含有禁止内容 | 改写输入 |
| `SPII` | 回答 | 可能含有敏感个人身份信息 | 去掉或脱敏个人信息 |
| `OTHER` | 提示或回答 | 原因未知 | 排错指南说可能违反服务条款或不受支持，改写输入 |
| `IMAGE_SAFETY` 等 `IMAGE_*` | 回答 | 生成的图片被拦 | 改写图片生成提示 |
| `PUP_LIMITED_DISABLED` | 回答 | 账号因违反禁止使用政策被限制或停用 | 账号层面的问题，改请求解决不了 |

关于 `RECITATION`：排错指南说，在仍支持采样参数的早期模型上，也可以调高 temperature（早期 Gemini 3 模型官方建议保持默认值）；但 **Gemini 4 和 3.6 及以后的模型会忽略 `temperature`、`top_p`、`top_k`**，返回弃用警告头，官方说以后会改成报 400，建议直接删掉这几个参数。对这些新模型，只能从提示和上下文入手。

另外，排错指南的「已知问题」里写明：用不支持的语言提问，可能得到意外的回答或被拦的回答。

## 第四步：要不要调 safetySettings

很多人一看到 `SAFETY` 就去把阈值调到最低，但先看两个事实（均出自官方安全设置文档）：

1. **2.5 及以后的模型，不设阈值时默认是 Off**。如果你的代码里没传 `safetySettings` 仍然被拦，降低阈值帮不上；先检查框架或封装层有没有替你传了更严的阈值。
2. **核心危害的内置防护（例如危害儿童安全的内容）总是拦截，不能调整**。

可调整的只有四个类别：骚扰、仇恨言论、色情露骨、危险内容（对应 `HarmCategory` 枚举）。阈值档位如下：

| AI Studio 名称 | API 值 | 含义 |
|---|---|---|
| Off | `OFF` | 关闭安全过滤 |
| Block none | `BLOCK_NONE` | 不论不安全概率高低都显示 |
| Block few | `BLOCK_ONLY_HIGH` | 只拦高概率 |
| Block some | `BLOCK_MEDIUM_AND_ABOVE` | 拦中、高概率 |
| Block most | `BLOCK_LOW_AND_ABOVE` | 拦低、中、高概率 |

官方强调拦截按**概率**而不是**严重程度**判断，所以 `safetyRatings` 里看到的是 `HIGH`、`MEDIUM` 这类概率档。REST 里按类别设置的写法是：

```json
"safetySettings": [
  {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"}
]
```

每个类别只能设一条。官方还提醒：使用较宽松安全设置的应用，可能会按服务条款接受审查。

## Interactions API：被拦直接报 400

官方说明当前推荐新的 Interactions API。按 [安全设置文档](https://ai.google.dev/gemini-api/docs/safety-settings) 和 [API errors](https://ai.google.dev/gemini-api/docs/api-errors)，它的行为和 `generateContent` 不同：

- 输入或输出被过滤时，请求失败并返回 **HTTP 400**，被拦内容不返回。报错示例：`Request blocked due to safety violations (harmful content). Please modify your input and retry.`
- 错误码 `safety` 表示输入或回答被安全过滤拦下；`jailbreak`、`prohibited_content`、`blocklist` 只针对输入，报错信息以 `Input blocked:` 开头。
- 后台模式（`background=true`）下，`status` 变成 `failed`，错误码和信息在 `errors` 列表里；流式请求里，错误以 `error` 事件送达。
- 「生成被拦」类错误码还有 `recitation`、`language`、`spii`、`image_safety`、`content_blocked` 等，官方统一建议**修改输入后再试**。

排错指南的重试原则是只重试 `429`、`408`、`5xx` 这类临时错误，`400` 不要原样重试，所以自动重试逻辑里要把这类拦截排除掉。

## 通过中转调用时怎么查

以 OpenLux 为例，Gemini 原生格式的 Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，鉴权用请求头 `x-goog-api-key` 或查询参数 `?key=`；模型名只用价格页在售的模型 ID，支持原生格式的模型在价格接口 `https://www.openlux.ai/api/pricing_new` 的 `supported_endpoint_types` 里带 `gemini`。

如果你平时走 OpenAI 兼容格式：Google 的 [OpenAI 兼容文档](https://ai.google.dev/gemini-api/docs/openai) 没有说明被拦时 `finish_reason` 怎么对应，`extra_body` 里的 `safety_settings` 也只列在图片接口下。所以排查拦截问题时，建议用原生格式发同一个请求，再按上文看 `promptFeedback`、`finishReason` 和 `safetyRatings`。

## 排查顺序小结

1. 先看有没有候选：没有就查 `promptFeedback.blockReason`，是提示被拦。
2. 有候选就打印 `finishReason`、`finishMessage`、`safetyRatings`，不要只读 `text`。
3. `SAFETY`：确认代码里有没有设过严的阈值；默认已是 Off 时只能改写内容，核心危害不能调整。
4. `RECITATION`：让提示更独特；新模型不要再靠调 temperature。
5. `PROHIBITED_CONTENT`、`BLOCKLIST`、`SPII`、`OTHER`：改写或脱敏输入；`PUP_LIMITED_DISABLED` 是账号问题。
6. Interactions API 的 400 拦截不要自动重试，改输入后再发；拿到正常正文且 `finishReason` 为 `STOP` 才算修好。

如果你想用一把令牌同时调用 Gemini、GPT 和 Claude，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-safety-recitation-blocked-empty-response-fix&utm_content=footer)。

## 同专题文章

- [Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱](https://a37836323.github.io/openlux-api-guides/news/gemini-4-carbon-api-price-november-30/)
- [Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)
- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)
- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

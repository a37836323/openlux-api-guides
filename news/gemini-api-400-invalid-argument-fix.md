---
layout: default
title: "Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查"
description: "Gemini API 报 400 INVALID_ARGUMENT、invalid_request 或 parameter_unknown 的排查方法：读懂 message 与 reason，核对字段、API 版本、新模型的预填充与思考参数规则、思维签名、Schema 复杂度，并附最小请求验证与中转调用检查。"
permalink: /news/gemini-api-400-invalid-argument-fix/
date: 2026-11-09
---

> 更新日期：2026-11-09 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/api-errors?generate-content=true)

# Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查

Gemini API 返回 **400 `INVALID_ARGUMENT`**（Interactions API 里对应 `invalid_request` 或 `parameter_unknown`），按 Google 官方 [API errors](https://ai.google.dev/gemini-api/docs/api-errors) 页的说明，意思是请求体格式不对或带了无效参数：常见是字段拼错、缺了必填字段、带了接口不认识的参数，或者在旧版本接口上用了新版本才有的功能。400 是客户端错误，官方排错指南明确说**不要重试**，原样再发一次结果还是一样，要先找到是哪一个字段出了问题。

本文适用于用 `generateContent` 或 Interactions API 直接调用 Gemini，也适用于通过中转平台以 Gemini 原生格式调用。Key 无效、403 项目受限见《[Gemini API 报 401、403 PERMISSION_DENIED 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)》，模型名不对见《[Gemini API 报 404 model_not_found 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)》。

## 先对照报错：同样是 400，原因差很多

下表出自官方 [API errors（generateContent 版）](https://ai.google.dev/gemini-api/docs/api-errors?generate-content=true)、[API errors（Interactions 版）](https://ai.google.dev/gemini-api/docs/api-errors) 和 [安全设置](https://ai.google.dev/gemini-api/docs/safety-settings) 页。

| 接口 | 状态或 `code` | 官方含义 | 先查什么 |
|---|---|---|---|
| generateContent | 400 `INVALID_ARGUMENT` | 请求体格式不对：字段拼错或缺少必填字段 | 对照 API 参考检查请求结构；确认没在旧版本接口上用新功能 |
| Interactions | 400 `invalid_request` | 请求体格式不对或参数无效 | 对照 API 参考检查语法和参数 |
| Interactions | 400 `parameter_unknown` | 请求里有接口不认识的参数 | 删掉这个参数再发 |
| generateContent | 400 `INVALID_ARGUMENT`，`reason` 为 `API_KEY_INVALID` | 报错原文 `API key not valid. Please pass a valid API key.` | 这是 Key 的问题，不是参数问题，按 401/403 那篇查 |
| generateContent | 400 `FAILED_PRECONDITION` | 所在国家或地区不提供免费层，项目也没开计费 | 在 Google AI Studio 给项目开通付费 |
| Interactions | 400 `safety`、`jailbreak`、`prohibited_content`、`blocklist` | 输入或回复被安全过滤拦下 | 修改输入后再发 |

两点补充：官方 [计费说明](https://ai.google.dev/gemini-api/docs/billing) 写明，请求以 400 或 500 失败时不收取 token 费用，但**仍然计入配额**，所以写错参数的请求在循环里自动重试，会白白消耗限流额度。另外，官方 generateContent 错误格式的示例里，Key 无效返回的就是 400 `INVALID_ARGUMENT` 而不是 401，只看状态码容易查错方向，一定要连 `reason` 和 `message` 一起看。

## 第一步：读懂返回体，找到出错的字段

generateContent 失败时，返回体是带 gRPC 状态的 `error` 对象，官方列出的字段如下：

| 字段 | 含义 |
|---|---|
| `code` | HTTP 状态码，如 400 |
| `message` | 给人看的错误描述，通常会点出出错的字段 |
| `status` | 大写的 gRPC 状态，如 `INVALID_ARGUMENT` |
| `details` | 附加信息，如 `ErrorInfo` 里的 `reason` |

Interactions API 的 `error` 只有 `code`（小写下划线形式）和 `message` 两个字段。官方示例里，传了不支持的工具类型时，`message` 会写明是 `tools[0]` 的 `type` 不对，并列出支持的取值。流式请求出错时，错误不走 HTTP 状态码，而是在 SSE 流里收到一个 `event_type` 为 `"error"` 的事件，结构相同。

所以排查的第一步是**把 `message` 完整打印出来**，不要只记录状态码。多数 400 的 `message` 已经告诉你是哪个字段、哪个位置。

## 原因一：字段写错、带了未知参数，或 API 版本不对

`message` 指向某个字段时，先按官方 [API 参考](https://ai.google.dev/api/generate-content) 核对：

1. **字段名和层级**：拼写、大小写，以及字段是不是放在 API 参考规定的那一层。
2. **必填字段**：官方给出的 `INVALID_ARGUMENT` 典型场景就是「有拼写错误，或缺少必填字段」。
3. **未知参数**：Interactions API 返回 `parameter_unknown` 时，官方建议直接删掉这个参数。从别的厂商代码迁过来时，最容易把对方特有的参数原样带过来。
4. **参数取值范围**：官方 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting) 列出 `candidateCount` 为 1～8 的整数，且 Gemini 3 和 Gemini 4 不支持；最大输出 token 数要按各模型页面的上限填。

**API 版本**也是常见原因。官方错误表的修复建议里专门写了：在旧版本接口上使用新版本的功能可能导致错误。按官方 [API 版本说明](https://ai.google.dev/gemini-api/docs/api-versions)，`v1` 是稳定版，`v1beta` 包含尚在开发中的功能；所有模型两个版本都支持，但部分功能只在 `v1beta` 提供，例如语音输出（Speech Config）、Live API、Agents API、Webhooks API 和 Context Caching。官方 SDK 默认就用 `v1beta`；如果你自己拼了 `/v1/...` 的地址又用了这些功能，先换成 `/v1beta` 再试。

## 原因二：换了新模型，旧写法不再被接受

很多 400 出现在「只改了模型名，其它没动」的时候。官方在新模型说明里列出了几条会直接报 400 的变化：

| 旧写法 | 适用范围 | 官方说明 | 怎么改 |
|---|---|---|---|
| 请求最后一轮是 `model` 角色（预填充回复开头） | Gemini 3.6 Flash、Gemini 3.5 Flash-Lite 及之后的模型 | 最后一个非空轮次是 `model` 时返回 400 | 删掉预填充；要控制格式就用 system instruction 或结构化输出 |
| `thinking_level` 和 `thinking_budget` 同时传 | Gemini 3.5 更新说明与 Gemini 4 思考文档 | 同一请求里两者同时出现返回 400 | 只保留 `thinking_level` |
| 非流式 REST 调用 `generateContent` 时 `max_output_tokens` 大于 32,768 且不带 `continuation_token` | gemini-4-argon（long decode 文档） | 返回 400 | 改用流式或最新版 SDK；REST 非流式的续写写法以 long decode 文档为准 |
| 续写时 `max_output_tokens` 没有高于已用量 | gemini-4-argon | 返回 400 `INVALID_ARGUMENT` | 调高 `max_output_tokens` 再续写 |

另外，官方 [Gemini 3.6 更新说明](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6) 写明：`temperature`、`top_p`、`top_k` 已弃用，Gemini 3.6 及之后、Gemini 4 会忽略自定义值并在响应头里返回弃用警告，**以后的模型代际传这几个参数会返回 400**。现在还没报错，不代表以后不报，官方要求从所有请求里删掉它们。

思考参数的出处是 [Gemini 3.5 更新说明](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.5) 和 [思考](https://ai.google.dev/gemini-api/docs/thinking?generate-content=true) 页；gemini-4-argon 的输出上限见 [long decode](https://ai.google.dev/gemini-api/docs/long-decode?generate-content=true) 和本站《[换成 gemini-4-argon 后回答被截断或报 400](https://a37836323.github.io/openlux-api-guides/news/gemini-4-argon-output-truncated-continuation-token-fix/)》。

## 原因三：函数调用缺少思维签名，或回传了不支持的文件类型

用函数调用做多轮对话时，按官方 [思维签名](https://ai.google.dev/gemini-api/docs/thought-signatures) 页：在当前这一轮里，**每一步的第一个 `functionCall` 部分都必须带上 `thought_signature`**；漏掉任何一步，请求就会以 400 失败。Gemini 3 模型的报错原文形如：

`Function call FC1 in the 1. content block is missing a thought_signature.`

看到这句，检查你回传历史时是不是只挑了函数名和参数、把模型返回里的 `thought_signature` 丢掉了。把模型上一轮返回的 `functionCall` 部分连同签名原样放回 `contents`，再接上你的 `functionResponse`。

另一种情况在 [函数调用](https://ai.google.dev/gemini-api/docs/function-calling?generate-content=true) 页：函数结果里可以放图片、PDF、音频等媒体块，但如果某个块的 MIME 类型不受支持，API 返回 400 `INVALID_ARGUMENT`，`message` 会写出是哪个字段，并列出可接受的类型。照着列表换格式即可。

如果是模型生成的函数调用本身无法解析，对应的是 `MALFORMED_FUNCTION_CALL`（Interactions 错误码 `malformed_function_call`），官方把它归为生成错误，和本文的请求参数问题不是一回事，见《[Gemini 函数调用返回 MALFORMED_FUNCTION_CALL 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-malformed-function-call-fix/)》。

## 原因四：JSON Schema 或函数声明太复杂

用结构化输出或函数调用时，官方说明 API 会把你的 JSON Schema 编译成约束生成的状态机，这个状态机对总状态数、分支数和嵌套深度有上限。**超过上限，请求会被以 400 `INVALID_ARGUMENT` 拒绝**；函数声明在 `any` 模式或参数结构复杂时同理。官方 [结构化输出](https://ai.google.dev/gemini-api/docs/structured-output) 页给出的简化办法：

| 做法 | 具体怎么做 |
|---|---|
| 把非结构性规则移到描述里 | 复杂约束改写进字段 `description` 或系统指令，返回后在代码里校验 |
| 拍平嵌套、限制递归 | 减少多层嵌套对象；用 `$defs` / `$ref` 递归时让递归引用可选或可为 null |
| 减少分支 | 能 `required` 的字段就设为必填，可空用 `null`；精简 `enum` 和 `anyOf` |
| 缩短属性名、去掉边界 | 属性名越长占用状态越多；`minItems`、`maxItems`、`minimum`、`maximum` 改成在提示词里说明或在代码里校验 |

改的时候一次只动一处，每改一处重新发一次，能更快确认是哪一部分超了限。

## 原因五：输入或回复被安全过滤拦下（Interactions API）

按官方安全设置页，在 Interactions API 里，如果安全过滤拦下了输入或模型回复，这次调用会以 HTTP 400 失败，被拦的内容不会返回。看 `code` 区分原因：`safety` 表示输入或回复被安全过滤拦下；`jailbreak`、`prohibited_content`、`blocklist` 表示输入因对应原因被拦，`message` 以 `Input blocked:` 开头。这类 400 改参数没有用，需要修改输入内容。后台执行的交互会把状态置为 `failed`，同样的 `code` 和 `message` 出现在 `errors` 列表里。

## 怎么确认修好了

改完后发一个最小的推理请求验证。按官方 [快速入门](https://ai.google.dev/gemini-api/docs/get-started?generate-content=true) 的 REST 写法，只保留一轮用户输入（Key 从环境变量读取）：

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{"contents": [{"role": "user", "parts": [{"text": "Hello"}]}]}'
```

成功标准：返回 HTTP 200 并带有模型输出。最小请求通过、完整请求仍报 400，就把完整请求里的字段一个个加回去，加到哪一个开始报错，问题就在哪。注意官方排错指南的提醒：`models.list` 这类只读接口返回 200 只能说明 Key 存在，不能证明推理请求能用。

## 通过中转调用时怎么查

通过中转平台调用时，请求带的是中转平台的令牌，不经过你自己的 Google Cloud 项目，所以 `FAILED_PRECONDITION`（免费层地区限制）和 `API_KEY_INVALID` 这两项不用按 Google 的办法查，先看令牌和地址。以 OpenLux 为例：

- **Gemini 原生格式**：Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，鉴权用请求头 `x-goog-api-key` 或查询参数 `?key=`。
- **令牌**：在 OpenLux 控制台的「令牌」页创建（`https://www.openlux.ai/console/token`）；令牌无效时返回 401 `Invalid token (request id: ...)`，不是 400。
- **模型和接口格式**：模型名只用价格页在售的模型 ID；某个模型支持哪些接口格式，看价格接口里的 `supported_endpoint_types`，其中 `gemini` 表示支持 Gemini 原生格式。
- **验证地址和令牌**：用 OpenAI 兼容地址列模型，能列出来就说明地址和令牌都对，再按上文逐项查请求体。

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

## 排查顺序小结

1. 打印完整的 `message`、`status` 和 `reason`，不要只看 400。
2. `reason` 是 `API_KEY_INVALID` 就去查 Key；`FAILED_PRECONDITION` 就去开计费。
3. 按 `message` 指出的字段核对拼写、层级、必填项，删掉 `parameter_unknown` 指出的参数。
4. 用了只在 `v1beta` 提供的功能，确认地址是 `/v1beta`。
5. 换过新模型：去掉预填充的 `model` 轮次，不要同时传 `thinking_level` 和 `thinking_budget`，删掉 `temperature`、`top_p`、`top_k`。
6. 函数调用多轮：原样回传 `thought_signature`；结构化输出或函数声明复杂时按上表简化 Schema。
7. 用最小请求验证，再把字段逐个加回去定位。

需要用一个令牌调用 Gemini、Claude、GPT 等模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-400-invalid-argument-fix&utm_content=footer)，在控制台创建令牌后按上文的地址接入。

## 同专题文章

- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)
- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

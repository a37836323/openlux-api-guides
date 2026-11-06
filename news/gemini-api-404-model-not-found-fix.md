---
layout: default
title: "Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查"
description: "Gemini API 报 404 model_not_found 或 not_found 时，按官方错误码、模型页、弃用页和 API 版本说明逐项排查：模型名写错或用了显示名、旧模型已关停、Base URL 少了 /openai/ 或方法名、只在 v1beta 的功能用了 v1，以及走中转时怎么核对模型 ID。"
permalink: /news/gemini-api-404-model-not-found-fix/
date: 2026-11-06
---

> 更新日期：2026-11-06 · 一手来源：[Google AI for Developers：Gemini API errors / Troubleshooting / Models / Deprecations / OpenAI compatibility / API versions](https://ai.google.dev/gemini-api/docs/api-errors)

# Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查

Gemini API 返回 **404**，按 Google 官方 [API errors](https://ai.google.dev/gemini-api/docs/api-errors) 页，分两种：错误码 `model_not_found` 表示「指定的模型没找到」，官方建议核对模型名，或者换用别的模型；错误码 `not_found` 表示「请求的资源没找到」，官方建议核对资源路径和参数。也就是说，404 基本只有两个方向：**模型名不对**，或者**请求地址拼错了**。它不是临时故障，原样重试不会好。

本文适用于用 Google AI Studio 的 Key 直接调用 Gemini API（原生格式或 OpenAI 兼容格式），也适用于通过中转平台调用。Key 报 401、403 见《[Gemini API 报 401、403 PERMISSION_DENIED 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)》，429 见《[Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)》。

## 先对照报错：是模型的问题，还是地址的问题

下表出自官方 API errors 页和 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting)。Interactions API 的报错是一个 `error` 对象，只有 `code`（小写下划线形式）和 `message` 两个字段；表里没列的错误码，会退回成 HTTP 状态的小写下划线写法。

| HTTP 状态 | `code` | 官方含义 | 先查什么 | 要不要重试 |
|---|---|---|---|---|
| 404 | `model_not_found` | 指定的模型没找到 | 模型名拼写、模型是否已关停、是不是用了显示名 | 不要，先改模型名 |
| 404 | `not_found` | 请求的资源没找到 | Base URL、API 版本、路径里的模型段、资源 ID | 不要，先改地址 |
| 400 | `invalid_request` | 请求体格式错误或参数无效 | 对照 API 参考检查参数 | 不要，先改请求 |
| 501 | `unimplemented` | 该操作或功能未实现、不支持 | 换成支持的功能 | 不要 |

官方排错指南的重试建议是：只对临时错误（如 `429`、`408`、`5xx`）重试，对 `400`、`402`、`403` 这类客户端错误不要重试。404 不在可重试的列表里，自动重试逻辑里应把它排除，否则只会白白消耗请求。

## 原因一：模型名写错，或用了显示名

官方 [模型页](https://ai.google.dev/gemini-api/docs/models) 每个模型都有一行 **Model code**，请求里要填的是它，不是页面标题。例如页面上的「Gemini 3.8 Flash」，模型代码是 `gemini-3.8-flash`；「Nano Banana 2」的模型代码是 `gemini-3.1-flash-image`，两者名字差得很远，最容易填错。

另外注意模型名的写法：

- 模型资源名的格式是 `models/{model}`。官方 [Models API](https://ai.google.dev/api/models) 说明，`baseModelId`（如 `gemini-1.5-flash` 这种不带 `models/` 的部分）才是传给生成请求的值。原生 REST 路径是 `/v1beta/models/{model}:generateContent`，如果你在 `{model}` 里又带了 `models/`，路径就会变成 `models/models/...`。
- 官方把模型版本分成 stable、preview、latest、experimental 四类：stable 如 `gemini-3.6-flash`，一般不变，生产环境推荐用；latest 如 `gemini-flash-latest`，每次新版本发布都会换成新模型，换之前会提前 2 周发邮件；experimental 的可用性随时可能变化。官方也提醒，2025 年 9 月之前发布的模型命名方式可能不同，要用确切的模型字符串。

## 原因二：模型已经关停

官方 [弃用页](https://ai.google.dev/gemini-api/docs/deprecations) 说明：模型一旦「关停」（shutdown），就会完全下线，端点不再可用。已经关停的模型列在各系列的 Deprecated models 表里，下面摘几项常见的：

| 模型 | 关停日期 | 官方推荐替换 |
|---|---|---|
| `gemini-2.0-flash`、`gemini-2.0-flash-001` | 2026 年 6 月 1 日 | `gemini-3.6-flash` |
| `gemini-2.0-flash-lite`、`gemini-2.0-flash-lite-001` | 2026 年 6 月 1 日 | `gemini-3.1-flash-lite` |
| `gemini-3-pro-preview` | 2026 年 3 月 9 日 | `gemini-3.1-pro-preview` |
| `gemini-3.1-flash-lite-preview` | 2026 年 5 月 25 日 | `gemini-3.1-flash-lite` |
| `gemini-2.5-flash-preview-09-2025` | 2026 年 2 月 17 日 | `gemini-3.6-flash` |

还有两种情况不算关停，但要知道：

- `gemini-3.7-flash`、`gemini-3.5-flash` 已不能在 AI Studio 里选，但端点不会关，API 请求会自动转到 `gemini-3.8-flash`、`gemini-3.6-flash`。
- `gemini-2.5-pro`、`gemini-2.5-flash` 已弃用，官方写明 API 访问**只限过去实际用过的老用户**；从 2026 年 12 月 1 日起，请求会自动转到 `gemini-3.8-flash`、`gemini-3.5-flash-lite`，并按新模型计费。新项目调这两个模型调不通，直接换成官方推荐的模型。

官方模型页说明，预览模型弃用前最少只提前 2 周通知；代码里写死预览版模型名的，要定期对照弃用页。

## 原因三：Base URL 或 API 版本不对

模型名没问题还报 404，多半是地址拼错，对应 `not_found`。按调用方式逐项核对：

- **原生格式**：生成内容的路径是 `/v1beta/models/{model}:generateContent`，流式是 `:streamGenerateContent`。冒号和方法名不能少，也不能写成斜杠。
- **OpenAI 兼容格式**：官方 [OpenAI 兼容文档](https://ai.google.dev/gemini-api/docs/openai) 给的 Base URL 是 `https://generativelanguage.googleapis.com/v1beta/openai/`，模型填 `gemini-3.8-flash` 这样的模型代码。少了 `/openai/` 这一段，SDK 拼出来的路径就不是官方文档里的地址。
- **API 版本**：官方 [API 版本说明](https://ai.google.dev/gemini-api/docs/api-versions) 写明，所有模型在 `v1` 和 `v1beta` 都可用，所以换版本解决不了模型名的问题；但部分功能只在 `v1beta` 里，例如 Live API、语音输出、Context Caching、Agents API、Webhooks。用 `v1` 调这些功能失败时，改回 `v1beta`。官方 SDK 默认就是 `v1beta`，如果你手动设成了 `v1`，要留意这一点。
- **流式查询结果**：官方示例里，流式请求取不到已完成的 interaction 时，会收到 `code` 为 `not_found`、内容是 `Failed to get completed interaction: Result not found.` 的错误事件。这时要查的是 interaction ID 和路径参数，不是模型名。

## 怎么验证：先列模型，再发最小请求

第一步，用模型列表接口确认模型代码。原生格式：

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models" \
  -H "x-goog-api-key: $GEMINI_API_KEY"
```

返回的每个模型有 `name`（如 `models/...`）、`baseModelId` 和 `supportedGenerationMethods`。确认你要用的模型在列表里，且 `supportedGenerationMethods` 里有你要调的方法（如 `generateContent`）。也可以用 `GET /v1beta/models/{model}` 只查一个模型。OpenAI 兼容格式对应的是 `GET https://generativelanguage.googleapis.com/v1beta/openai/models`，鉴权用 `Authorization: Bearer`。

第二步，用同一个模型代码发一次最小生成请求。注意官方排错指南的提醒：`models.list` 这类只读接口只校验 Key 是否存在，返回 200 不代表你的项目能做推理。所以：

- 列表里有这个模型、生成请求仍报 404：回头查路径和 API 版本。
- 列表里没有这个模型：换成模型页或弃用页推荐的模型。
- 生成请求返回 HTTP 200 并带有模型输出：问题解决。

## 通过中转调用时怎么查

通过中转平台调用时，能用哪些模型取决于中转平台，不取决于你自己的 Google 项目。以 OpenLux 为例：

- **Gemini 原生格式**：Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，鉴权用请求头 `x-goog-api-key` 或查询参数 `?key=`。
- **OpenAI 兼容格式**：Base URL 填 `https://api.openlux.ai/v1`，鉴权用 `Authorization: Bearer`。
- **模型名**：只用价格页在售的模型 ID；每个模型支持哪些接口格式，看价格接口 `https://www.openlux.ai/api/pricing_new` 里的 `supported_endpoint_types`（`gemini` 表示原生格式，`openai` 表示 OpenAI 兼容格式）。
- **地址拼错时的报错**：返回 404 `Invalid URL (...)`，括号里是实际请求的方法和路径。例如 Anthropic 格式的 Base URL 多写了 `/v1`，会看到 `Invalid URL (POST /v1/v1/messages)`。看到这类报错，对照括号里的路径改 Base URL。

用 OpenAI 兼容地址列模型，能列出来就说明地址和令牌都对，再从列表里复制模型 ID：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

## 排查顺序小结

1. 看 `error.code`：`model_not_found` 查模型名，`not_found` 查地址；两者都不要自动重试。
2. 对照模型页的 Model code，确认没有用显示名，路径里没有多出 `models/`。
3. 查弃用页：模型已关停就换成官方推荐的替换模型；`gemini-2.5-pro`、`gemini-2.5-flash` 新项目直接换。
4. 核对 Base URL：原生格式看 `:generateContent`，OpenAI 兼容格式看 `/v1beta/openai/`；只在 `v1beta` 的功能不要用 `v1` 调。
5. 先列模型，再用同一个模型代码发最小请求，返回 200 且有输出才算修好。

如果你想用一把令牌同时调用 Gemini、GPT 和 Claude，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-404-model-not-found-fix&utm_content=footer)。

## 同专题文章

- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

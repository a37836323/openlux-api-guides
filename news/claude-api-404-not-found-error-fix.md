---
layout: default
title: "Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查"
description: "Claude API 报 404 not_found_error：按官方 Errors 文档先核对完整请求地址（Base URL 多写或少写 /v1、/v1/v1/messages），再查 URL 里的文件 ID、批处理 ID 是否过期或不在当前工作区，最后核对模型 ID 格式与官方退役表，并用 Models API 验证。"
permalink: /news/claude-api-404-not-found-error-fix/
date: 2026-11-08
---

> 更新日期：2026-11-08 · 一手来源：[Anthropic 官方文档 Errors](https://platform.claude.com/docs/en/api/errors)

# Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查

Claude API 返回 404 `not_found_error`，意思是「请求的资源不存在」。Anthropic 官方 [Errors 文档](https://platform.claude.com/docs/en/api/errors) 给的处理只有一句：检查接口路径，以及请求 URL 里的资源 ID。所以排查顺序是：先看完整请求地址对不对（最常见的是 Base URL 多写或少写了 `/v1`），再看 URL 里的文件 ID、批处理 ID 是否还在当前工作区，最后核对请求体里的模型 ID 是否写对、是否已经退役。

本文适用于用官方 SDK、curl 或各类客户端直接调用 Claude API（`/v1/messages` 等接口），以及把这些请求改发到 Anthropic 兼容中转地址的情况。

## 先看清楚报错长什么样

官方说明，Claude API 的错误一律以 JSON 返回，顶层 `error` 对象里一定有 `type` 和 `message`，响应里还带一个 `request_id`：

```json
{
  "type": "error",
  "error": {
    "type": "not_found_error",
    "message": "The requested resource could not be found."
  },
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"
}
```

用官方 SDK 时不会拿到原始 JSON，而是抛出异常：Python 是 `anthropic.NotFoundError`，TypeScript 是 `Anthropic.NotFoundError`，Go 统一是 `*anthropic.Error`，要按 `StatusCode` 判断。官方建议按异常类型处理，不要匹配错误文字。

动手排查前先记下三样东西：完整请求地址、`error.message` 原文、`request_id`（每个响应头里都有 `request-id`）。后面每一步都靠它们判断。

## 404 先按这张表对号入座

| 现象 | 最可能的原因 | 怎么改 |
|---|---|---|
| 所有请求都 404，换模型也一样 | 请求地址拼错：Base URL 多写或少写 `/v1`，或者路径写成了别家接口 | 按下一节把完整地址拼出来核对，应为 `<主机>/v1/messages` |
| 只有带文件 ID 的请求失败，或下载文件内容报 404 | 文件已过期、已删除，或 Key 不属于上传文件的那个工作区 | 用同一工作区的 Key 查 `GET /v1/files/{file_id}`，必要时重新上传 |
| 查批处理或取结果报错 | 批处理 ID 写错、属于别的工作区，或结果已过 29 天下载期 | 用创建它的工作区的 Key 查询；超过 29 天的结果无法再下载，需要的话只能重新提交 |
| 只有某个模型失败，其他模型正常 | 模型 ID 写错、用了别的平台的 ID 格式，或模型已退役 | 用 Models API 查这个 ID，并对照官方退役表换模型 |

## 第一步：核对完整请求地址和 Base URL

官方示例里，Messages 接口的完整地址是 `https://api.anthropic.com/v1/messages`。SDK 让你填的是「Base URL」，由 SDK 在后面接上 `/v1/messages` 这类路径。官方 Python SDK 文档里 `base_url`（或环境变量 `ANTHROPIC_BASE_URL`）的示例也只写到主机和端口，没有带 `/v1`。

最容易出错的就是这一层：

- **多写了 `/v1`**：Base URL 填成 `https://主机/v1`，SDK 再接 `/v1/messages`，实际请求就成了 `/v1/v1/messages`，服务器找不到这个路径。
- **把完整地址当 Base URL**：填成 `https://主机/v1/messages`，结果路径重复得更厉害。
- **协议模式选错**：本文说的是 Anthropic 原生接口 `/v1/messages`；如果客户端选的是 OpenAI 兼容模式，它请求的是 `/v1/chat/completions`，Base URL 要按那种模式的规则填，不能照搬本文。

核对方法很简单：打开 SDK 或客户端的调试日志，或在报错里找实际请求的 URL，把它和 `<主机>/v1/messages` 逐字比对，确认 `/v1` 恰好出现一次。

## 第二步：核对 URL 里的文件 ID 和批处理 ID

如果 404 只出现在带资源 ID 的请求上，问题通常不在地址，而在 ID 本身。

**文件（Files API）**：官方写明，文件按工作区隔离，上传到哪个工作区，就只有能访问该工作区的 Key 能用它。文件过期（到达 `expires_at`）后：

- 下载内容 `GET /v1/files/{file_id}/content` 返回 404；
- 在 Messages 请求里引用这个文件，会在推理前直接失败；
- 元数据 `GET /v1/files/{file_id}` 最多还能再读 30 天，`expires_at` 显示为过去的时间。

文件被 `DELETE /v1/files/{file_id}` 删除后无法恢复，只能重新上传拿新的 `file_id`。所以遇到 404，先确认用的是上传时那个工作区的 Key，再查一次元数据看是否已过期。

**批处理（Message Batches）**：官方说明批处理同样按工作区隔离，只能看到当前请求所在工作区里创建的批处理；结果在创建后 29 天内可以下载，之后批处理本身还能查看，但结果不能再下载。

另外，Files API 已经正式可用，不再需要 beta 请求头；继续带旧的 `files-api-2025-04-14` 头也能用，只是返回的是 beta 版的响应结构。

## 第三步：核对请求体里的模型 ID

模型 ID 写在请求体里，不在 URL 中，但它写错或已经退役时请求同样会失败。官方的模型生命周期说明是：模型退役后不再可用，发给退役模型的请求会失败（文档没有写明具体状态码，以 `error.message` 为准）。

按官方的 ID 规则逐项看：

- **4.6 代及以后**用不带日期的 ID，例如 `claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5`。官方特别说明，这种 ID 就是固定版本本身，不是会自动指向新版的别名。
- **4.6 代以前**的 ID 带日期，例如 `claude-sonnet-4-5-20250929`；Claude API 上这些模型另有简短别名（如 `claude-sonnet-4-5`），指向该版本最新的日期快照。
- **别的平台的格式不能拿来用**：Amazon Bedrock 的 ID 带 `anthropic.` 前缀（如 `anthropic.claude-opus-5-5`），Google Cloud（Google 托管）上旧模型用 `@` 分隔日期（如 `claude-haiku-4-5@20251001`），这些格式发到 Claude API 都对不上。

官方模型退役表里，下面这些已经退役或即将退役，需要换成推荐的替代模型：

| 模型 ID | 状态 | 官方推荐替代 |
|---|---|---|
| `claude-sonnet-4-5-20250929` | 已弃用，2026-11-30 退役 | `claude-sonnet-5-5` |
| `claude-opus-4-1-20250805` | 2026-08-05 已退役 | `claude-opus-4-8` |
| `claude-opus-4-20250514` | 2026-06-15 已退役 | `claude-opus-4-8` |
| `claude-sonnet-4-20250514` | 2026-06-15 已退役 | `claude-sonnet-5-5` |
| `claude-3-7-sonnet-20250219` | 2026-02-19 已退役 | `claude-sonnet-5-5` |
| `claude-3-haiku-20240307` | 2026-04-20 已退役 | `claude-haiku-4-5-20251001` |

想知道自己的代码里还有哪些地方在用旧模型，官方给的办法是：在 Claude Console 的 Usage 页点 Export，下载 CSV，按 API Key 和模型查看用量。

## 第四步：用 Models API 验证地址、Key 和模型 ID

官方的 Models API 可以直接确认一个模型 ID 能不能用：

- `GET /v1/models` 列出当前可用（active 和 deprecated）的模型；在 `lifecycle` 参数里明确加上 `retired`，才会列出已退役的模型。
- `GET /v1/models/{model_id}` 查单个模型，可以传模型 ID 或别名，返回解析后的 ID。

```bash
curl https://api.anthropic.com/v1/models/claude-sonnet-5-5 \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2026-10-21"
```

成功标准：返回的 JSON 里 `type` 为 `model`、`id` 是你要用的模型。查不到时，回到第三步换成官方模型列表里的 ID。如果连 `GET /v1/models` 都 404，说明问题在地址，回到第一步。

## 走 OpenLux 中转时怎么填

如果你把 Claude 请求改发到 OpenLux 的 Anthropic 兼容入口，Base URL 填 `https://api.openlux.ai`，**不要带 `/v1`**，由 SDK 或客户端自己拼出 `/v1/messages`。多写了 `/v1` 时，OpenLux 会返回 404，报错原文是 `Invalid URL (POST /v1/v1/messages)`，看到它直接去掉 Base URL 末尾的 `/v1` 即可。

`/v1/messages` 同时接受 `x-api-key` 和 `Authorization: Bearer` 两种鉴权头。Key 在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建。模型 ID 只填价格页在售的完整 ID（如 `claude-opus-5-5`、`claude-sonnet-5-5`），不要自己简写；官方已经退役的模型，建议按上表换成替代模型。

验证地址和 Key 可以先请求一次模型列表：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对；返回 401 是 Key 错了或没带上，不是 404 的问题。

## 求助时带上什么

按上面四步还解决不了，提问或联系支持时带上：

1. `request_id`（报错 JSON 里或响应头 `request-id`）；
2. 实际请求的完整 URL（把 Key 去掉）；
3. 请求体里的 `model` 值，以及涉及的 `file_id` 或批处理 ID；
4. `error.type` 和 `error.message` 原文。

官方说明，联系支持时附上 request ID 能更快定位具体请求。

## 参考资料

- Anthropic 官方文档：[Errors](https://platform.claude.com/docs/en/api/errors)（HTTP 错误码、错误结构、request ID、SDK 异常类型）
- Anthropic 官方文档：[Model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions)（ID 格式、别名、Bedrock 与 Google Cloud 格式）
- Anthropic 官方文档：[Model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations)（退役状态、退役日期与替代模型、用量导出）
- Anthropic 官方文档：[Models overview](https://platform.claude.com/docs/en/models/overview)、[Get a Model](https://platform.claude.com/docs/en/api/models/retrieve)（Models API 查询模型）
- Anthropic 官方文档：[Files API](https://platform.claude.com/docs/en/build-with-claude/files)、[Batch processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing)（工作区隔离、过期与结果保留期）
- Anthropic 官方文档：[Python SDK](https://platform.claude.com/docs/en/api/sdks/python)（`base_url` 与 `ANTHROPIC_BASE_URL`、异常类型）

想用一个 Key 同时调用 Claude 和其他模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-404-not-found-error-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的方法填 Base URL 和模型 ID。

## 同专题文章

- [Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)
- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁](https://a37836323.github.io/openlux-api-guides/news/claude-api-prompt-is-too-long-400-fix/)
- [Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)
- [Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了](https://a37836323.github.io/openlux-api-guides/news/claude-prompt-cache-miss-diagnostics-fix/)
- [Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: "fast" 的请求会报错，留在 4.8 还是换 Opus 5.5](https://a37836323.github.io/openlux-api-guides/news/claude-opus-4-8-fast-mode-removal-opus-5-5-migration/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

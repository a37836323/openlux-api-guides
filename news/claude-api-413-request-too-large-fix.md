---
layout: default
title: "Claude API 报 413 request_too_large 怎么办：128 MB 请求上限、图片和 PDF 改用 file_id"
description: "Claude API 返回 413 request_too_large 时，按官方请求大小上限（第一方 Messages 128 MB、Bedrock 20 MB 等）定位原因，把 base64 图片和 PDF 改为 Files API 的 file_id 引用，或压缩、拆分后再发送。"
permalink: /news/claude-api-413-request-too-large-fix/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[Claude API 官方文档](https://platform.claude.com/docs/en/api/errors)

# Claude API 报 413 request_too_large 怎么办：128 MB 请求上限、图片和 PDF 改用 file_id

调用 Claude Messages API 时返回 HTTP 413、错误类型是 `request_too_large`，意思只有一个：**这次请求的字节数超过了该接口允许的最大值**。它和上下文窗口、token 数、调用频率无关，换模型、重试都不会好；要做的是把请求体变小，或者把大文件从请求体里挪出去。

Anthropic 在 2026 年 10 月 28 日的[发布说明](https://platform.claude.com/docs/en/release-notes/overview)中写明：第一方 Claude API 上 Messages API 和 Token Counting API 的最大请求大小从 32 MB 提高到 128 MB。按官方 [Claude API 错误说明](https://platform.claude.com/docs/en/api/errors)，超过上限会收到 413 `request_too_large`，而且在第一方 Claude API 上，这个错误由 Cloudflare 在请求到达 API 服务器之前直接返回。

本文适用于直接调用 `/v1/messages`、`/v1/messages/count_tokens`、Batch 或 Files 接口时遇到 413 的情况，内容只来自官方文档。

## 先看各接口的请求大小上限

官方 [API 概览](https://platform.claude.com/docs/en/api/overview#request-size-limits) 列出的第一方 Claude API 上限如下：

| 接口 | 最大请求大小 |
|---|---|
| Messages、Token Counting | 128 MB |
| Message Batches API | 256 MB |
| Files API（单个文件） | 500 MB |
| Sessions、Agents、Environments（Managed Agents） | 32 MB |

云平台各有自己的上限，官方同一页的说明是：Amazon Bedrock 为 20 MB，Claude Models on Google Cloud（Google 托管）为 30 MB；Claude Platform on AWS、Claude Models on Google Cloud（Anthropic 托管）和 Microsoft Foundry 的 Messages、Token Counting 请求最高 32 MB，具体以各平台文档的当前数值为准。

所以第一步是确认请求实际发到了哪里：同样一个 40 MB 的请求，发到第一方 Claude API 不会因为大小触发 413，发到 Bedrock 或上限为 32 MB 的平台就会。

## 为什么请求会变得这么大

官方文档点名的几种情况：

1. **图片用 base64 直接塞进请求体。** 图片限制按 base64 编码后的大小计算：Claude API 单张最大 10 MB，Bedrock 单张最大 5 MB。base64 编码会让体积比原文件增加约三分之一。
2. **多轮对话反复重发同一批图片。** 官方 [Vision 文档](https://platform.claude.com/docs/en/build-with-claude/vision) 的原意是：多轮对话和 Agent 流程每次请求都会重发完整历史，图片如果是 base64，每一轮都会把全部图片字节再带一遍，请求会随对话变长而越来越大。
3. **PDF 用 base64 发送。** 官方 [PDF 文档](https://platform.claude.com/docs/en/build-with-claude/pdf-support) 写明，请求大小上限和页数上限针对的是整个请求，PDF 之外一起发送的内容也算在内。
4. **把工具结果里的截图、长文本一并回传。** `tool_result` 里的图片同样是请求体的一部分。

## 修复步骤

**第 1 步：确认 413 来自哪一层。** 看报错 JSON 的 `error.type` 是否是 `request_too_large`，再看请求的 Base URL 是第一方 Claude API 还是某个云平台或代理，对照上表找到适用的上限。

**第 2 步：量一下请求体有多大。** 在发送前把请求体序列化成 JSON，看字节数是否接近或超过上限，并找出体积最大的内容块（通常是 base64 的图片或 PDF）。

**第 3 步：把大文件改成 Files API 的 `file_id`。** 官方 [Files API 文档](https://platform.claude.com/docs/en/build-with-claude/files) 的做法是先上传一次文件拿到 `file_id`，之后在消息里引用它，而不是每次重发文件内容。图片用 `image` 块，PDF 和纯文本用 `document` 块：

```json
{
  "type": "image",
  "source": { "type": "file", "file_id": "file_011CPMxVD3fHLUhvTqtsQA5w" }
}
```

Vision 文档明确说，用 `file_id` 引用图片可以让请求体保持很小，不管对话历史里累积了多少张图片。文件也可以用 `url` 来源引用网上可访问的地址。

**第 4 步：不能用 Files API 时，压缩或拆分。** Amazon Bedrock 和 Claude Models on Google Cloud（Google 托管）目前图片和 PDF 都只支持 base64 来源，这时只能缩小图片尺寸或体积、把长 PDF 拆成几段分别发送，或者在多轮对话里不再重复携带已经处理过的大图片。

## 不报 413 也可能被拒：图片和 PDF 的其他上限

请求没超 128 MB，也可能撞上下面这些限制，报错类型不同，不要混在一起排查：

| 限制项 | 官方数值 | 说明 |
|---|---|---|
| 单个请求图片数 | 200k 上下文窗口的模型最多 100 张，其他模型最多 600 张 | 请求大小上限可能先于张数上限触发 |
| 单张图片尺寸 | 最大 8000×8000 像素 | 单张大小 Claude API 最大 10 MB（base64 编码后） |
| 单个请求超过 20 张图片 | 每张图适用更严格的尺寸限制，官方建议两边都不超过 3000 像素 | 返回 `invalid_request_error`，消息提到 many-image requests；之前轮次重发的图片和 `tool_result` 里的图片都计入 |
| PDF 页数 | 每个请求最多 600 页，请求的上下文窗口小于 1M token 时为 100 页 | 与请求大小上限一样针对整个请求 |
| Files API 单文件 | 500 MB | 超出返回 413 |

官方还提醒：即使用了 Files API，含有很多大图片或大 PDF 的请求也可能在达到数量上限之前失败，建议先降低图片分辨率、拆分文档。

## 改完怎么验证

- 用同样的业务输入重发请求，确认不再返回 413，响应正常带回 `content`。
- 对多轮对话，连续跑到原来出错的轮数之后，确认请求体没有随轮数线性膨胀。
- 换成 `file_id` 后，用 `GET /v1/files/{file_id}` 查看文件元数据，确认文件存在、没有到期（设置了 `expires_at` 的文件到期后，引用它的 Messages 请求会在推理前失败）。
- 第一方 API 的 413 在请求到达 API 服务器之前就被返回，排查重点是你这边记录的请求字节数；其他错误可保留响应里的 `request_id`，联系支持时一并提供。

## 经代理或中转服务调用时

官方的 128 MB 是第一方 Claude API 的数值。如果你通过云平台、企业网关或第三方中转服务调用，中间每一层都可能有自己的请求体上限，Files API 是否可用、`file_id` 能否透传，也以该服务的说明为准。遇到 413 时，先按上面的方法缩小请求体；如果请求明显低于官方上限仍然报 413，再向你使用的服务方确认它的请求体上限。

如果需要一个同时提供 Claude、GPT 等模型的 OpenAI 兼容 / Anthropic 兼容接口，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-413-request-too-large-fix&utm_content=footer)。

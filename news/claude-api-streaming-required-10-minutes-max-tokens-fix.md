---
layout: default
title: "Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查"
description: "Anthropic SDK 报 Streaming is required for operations that may take longer than 10 minutes 是 SDK 发请求前的本地检查：非流式、默认超时且 max_tokens 过大时触发。本文按官方文档讲触发条件、改用流式并用 get_final_message 拿完整结果、显式 timeout 的风险、调小 max_tokens 或用 Message Batches，以及流式中途断开怎么续写。"
permalink: /news/claude-api-streaming-required-10-minutes-max-tokens-fix/
date: 2026-11-21
---

> 更新日期：2026-11-21 · 一手来源：[Claude API 官方文档](https://platform.claude.com/docs/en/api/errors)

# Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查

用 Anthropic 官方 SDK 调 Claude 时报 `ValueError: Streaming is required for operations that may take longer than 10 minutes`，这条报错**不是 API 返回的**，而是 SDK 在发请求之前自己做的检查：你用的是非流式调用、没有自己设置超时，而 `max_tokens` 又大到 SDK 估计这次请求可能超过 10 分钟，于是直接拒绝发送。最稳的改法是改用流式调用，再用 SDK 的 `get_final_message()` / `finalMessage()` 拿回和非流式一模一样的完整 `Message`；其次是显式设置 `timeout`、调小 `max_tokens`，或者把不急的任务交给 Message Batches API。

本文适用于 Python SDK（`anthropic`）和 TypeScript SDK（`@anthropic-ai/sdk`）。直接用 curl 或自己写 HTTP 请求不会看到这句报错，但长请求同样可能遇到 504 `timeout_error` 或连接被中途断开，处理思路一样。依据是 Anthropic 官方的 [Claude API errors 文档](https://platform.claude.com/docs/en/api/errors)、[Python SDK 文档](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)、[TypeScript SDK 文档](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/typescript) 和 [Streaming messages 文档](https://platform.claude.com/docs/en/build-with-claude/streaming)。

## 先确认：这句报错什么时候会出现

Python SDK 的报错原文是：

```text
ValueError: Streaming is required for operations that may take longer than 10 minutes. See https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python#long-requests for more details
```

官方 Python SDK 文档写明：非流式请求预计超过约 10 分钟时，SDK 会抛出 `ValueError`；传 `stream=True`，或者在客户端、单次请求上自己设置 `timeout`，都会关掉这个报错。

具体怎么"预计"，可以看 [SDK 源码 `_base_client.py`](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/_base_client.py) 里的 `_calculate_nonstreaming_timeout`：预计耗时按 `3600 × max_tokens ÷ 128000` 秒估算，超过 600 秒（10 分钟）就报错。换算下来，**`max_tokens` 大于 21333 时**就会触发。源码里还给少数旧的 Claude Opus 4 / 4.1 模型 ID 单独设了 8192 的非流式上限，超过也会报同一句话。

同时满足下面三条才会触发（以当前 Python SDK 源码为准）：

1. 调用 `messages.create()` 时没有传 `stream=True`；
2. 这次调用没有单独传 `timeout`；
3. 客户端的 `timeout` 仍是默认的 10 分钟。

`messages.parse()`（结构化输出）也会做同样的检查。TypeScript SDK 文档的说法一致：非流式请求预计超过约 10 分钟会抛错，传 `stream: true` 或自己设置 `timeout` 即可关闭；另外 TypeScript 在大 `max_tokens`、非流式时会按公式动态计算默认超时，最长 60 分钟。

## 按现象判断问题出在哪一层

超时相关的报错有好几种，来源不同，处理也不同：

| 你看到的现象 | 出在哪一层 | 先做什么 |
|---|---|---|
| `ValueError: Streaming is required for operations that may take longer than 10 minutes` | SDK 本地检查，请求根本没发出去 | 改流式，或显式设置 `timeout` |
| Python `APITimeoutError`、TypeScript `APIConnectionTimeoutError` | 客户端等到超时，SDK 默认还会再重试 2 次 | 改流式；确实要非流式就调大 `timeout` 并考虑 `max_retries` |
| HTTP 504，错误体 `error.type` 是 `timeout_error`（也可能是 500 带 `timeout_error`） | 服务端处理超时 | 长请求改用流式 Messages API 或 Message Batches API |
| 流式先返回 200，中途收到 `event: error` | 流中途出错，例如 `overloaded_error` | 按错误类型处理，保存已收到的内容再续写 |
| 等了很久没有任何响应，连接被断开 | 网络断开了空闲连接 | 改流式；自己写 HTTP 集成可设置 TCP keep-alive |

如果是 529 `overloaded_error` 或 429 限流，请看本站的 [Claude API 报 529 overloaded_error 怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)。

## 做法一（推荐）：改成流式，但照样拿完整结果

很多人不愿意改流式，是因为不想重写"逐段拼接"的代码。官方 Streaming 文档专门说明：SDK 可以在内部用流式，最后返回一个和 `client.messages.create()` 完全相同的 `Message` 对象，"尤其适合大 `max_tokens` 的请求"。

Python（来自官方文档）：

```python
client = anthropic.Anthropic()

with client.messages.stream(
    max_tokens=128000,
    messages=[{"role": "user", "content": "Write a detailed analysis..."}],
    model="claude-opus-5-5",
) as stream:
    message = stream.get_final_message()
```

TypeScript（来自官方文档）：

```typescript
const stream = client.messages.stream({
  max_tokens: 128000,
  messages: [{ role: "user", content: "Write a detailed analysis..." }],
  model: "claude-sonnet-5"
});
const message = await stream.finalMessage();
```

拿到的 `message` 和原来非流式的返回值结构一样，后面读取 `content`、`stop_reason`、`usage` 的代码不用改。如果你不需要最终的 `Message` 对象，也可以用 `client.messages.create(..., stream=True)`，它只返回事件迭代器、占用内存更少，但要自己处理事件。

## 做法二：显式设置 timeout（知道风险再用）

官方文档写明，在客户端或单次请求上覆盖 `timeout` 就不会再报这条 `ValueError`。Python 写法：

```python
client.with_options(timeout=1800.0).messages.create(...)
```

但这只是关掉了本地检查，长请求本身的风险还在，官方文档列了两条：

- 如果实际耗时超过你设的 `timeout`，客户端会断开连接并重试，**收不到这次的响应**；而且超时默认会重试 2 次，最坏情况要等 3 轮才失败。可以用 `max_retries` 调整。
- 有些网络会在一段时间后断开空闲连接，非流式请求在等待期间没有数据往来，可能失败或超时而收不到任何响应。SDK 已经设置了 TCP keep-alive 来减轻这个问题，但不能保证所有网络都有效。

所以只有在你确定请求不会太久、网络稳定时，才用这个办法；否则还是回到做法一。

## 做法三：调小 max_tokens，或改用 Message Batches

如果你其实不需要那么长的输出，把 `max_tokens` 降到 21333 以内，Python SDK 就不会触发这条检查。注意 `max_tokens` 设小后，回答可能在中途被截断，`stop_reason` 会是 `max_tokens`，处理方法见本站的 [Claude API stop_reason 是 max_tokens、回答被截断怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)。

如果任务不需要实时返回（例如批量生成长报告），官方建议考虑 Message Batches API：提交后轮询结果，不需要一直保持一条不断的连接，可以降低网络问题的影响。

## 流式中途断了怎么续上

改成流式后，请求可能先返回 200，再在事件流里收到错误，官方示例：

```text
event: error
data: {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded" } }
```

官方 Streaming 文档的恢复办法分两种：

- **Claude 4.6 及之后的模型**：保存已收到的内容，新请求里加一条 user 消息，把已收到的部分放进去并让模型从断点继续，例如"Your previous response was interrupted and ended with [previous_response]. Continue from where you left off."。这些模型不支持把半截回答放进 assistant 消息预填（会报 400，见 [prefill 报错排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)）。
- **Claude 4.5 及更早的模型**：可以把已收到的部分作为新 assistant 消息的开头，接着生成。

另外，`tool_use` 和 thinking 内容块不能只恢复一半，只能从最近的文本块续写。

## 怎么确认已经改好

按下面的标准逐条核对：

1. 用同样大的 `max_tokens` 重新运行，不再出现 `Streaming is required...` 的 `ValueError`；
2. 拿到的 `message.stop_reason` 是 `end_turn` 这类正常结束，而不是请求中途抛异常；
3. 打印 `message._request_id`（Python、TypeScript SDK 都提供），记下 `req_` 开头的请求 ID。官方错误文档说明，联系支持时附上这个 ID 可以更快定位问题。

如果改流式后仍然频繁中断，再按上面的表格区分是 `overloaded_error`、`timeout_error` 还是网络断开。

## 经中转 API 调用 Claude 时要注意什么

这条 `ValueError` 是 SDK 在本地判断的，和请求发到哪个地址无关，所以经中转调用时一样会出现，改法也一样。用 OpenLux 这类中转时：

- Python SDK 把 `base_url` 设为 `https://api.openlux.ai`（**不带 `/v1`**，SDK 会自己拼 `/v1/messages`），也可以用环境变量 `ANTHROPIC_BASE_URL`；多写了 `/v1` 会返回 404 `Invalid URL (POST /v1/v1/messages)`。
- Key 在 OpenLux 控制台「令牌」页创建；Key 无效会返回 401 `Invalid token`。
- 模型名用价格页里在售、且 `supported_endpoint_types` 包含 `anthropic` 的模型 ID。
- 中间多了一层网络，长时间没有数据往来的非流式请求同样有被断开的风险，长输出任务更建议直接用流式。

想用 Claude 兼容接口测试上面的流式写法，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-streaming-required-10-minutes-max-tokens-fix&utm_content=footer)

## 同专题文章

- [Claude 桌面版怎么接入 Claude 中转 API：开发者模式、Configure Third-Party Inference、网关地址、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-desktop-relay-api-third-party-inference-gateway-setup/)
- [Claude Agent SDK 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、env 选项与模型设置（Python / TypeScript）](https://a37836323.github.io/openlux-api-guides/news/claude-agent-sdk-relay-api-base-url-env-setup/)
- [Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？](https://a37836323.github.io/openlux-api-guides/news/claude-external-key-webhook-events/)
- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)
- [Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-image-400-size-dimension-limit-fix/)
- [Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？](https://a37836323.github.io/openlux-api-guides/news/claude-api-sampling-parameters-text-watermark/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

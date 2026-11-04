---
layout: default
title: "Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理"
description: "Claude API 报 529 overloaded_error 是 API 暂时过载：怎么和 429 限流、月度消费上限、500 api_error、504 timeout_error 区分，SDK 默认重试 2 次与 max_retries 设置，流式请求中途收到 overloaded_error 怎么续写，以及用 request-id 排查。"
permalink: /news/claude-api-529-overloaded-error-retry-fix/
date: 2026-11-02
---

> 更新日期：2026-11-02 · 一手来源：[Claude API 官方文档](https://platform.claude.com/docs/en/api/errors)

# Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理

Claude API 返回 HTTP 529、错误类型是 `overloaded_error`，按 [Claude API 官方错误文档](https://platform.claude.com/docs/en/api/errors) 的说法，意思是「API 暂时过载」，并且官方提醒：所有用户整体流量高的时候都可能出现 529。也就是说，它一般不是你的 Key、请求格式或账户余额出了问题，处理方法是**按指数退避重试**，而不是去改请求参数。

容易出错的地方有三个：把 429、自设消费限额返回的 400 也当成「过载」一直重试；流式请求先返回 200、中途才收到 `overloaded_error`，代码没处理；以及不知道官方 SDK 默认已经重试过两次。本文适用于直接调用 Claude Messages API、用官方 SDK，或经 Anthropic 兼容中转调用的场景。

## 先看错误体里的 error.type，不要只看状态码

官方文档写明，API 出错时总是返回 JSON，顶层 `error` 对象里一定有 `type` 和 `message`，响应体里还有 `request_id`。格式如下（官方示例）：

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

几种容易混在一起的报错，按官方错误文档和速率限制文档整理如下：

| 状态码 | error.type / 特征 | 官方含义 | 重试有没有用 | 该怎么做 |
|---|---|---|---|---|
| 529 | `overloaded_error` | API 暂时过载 | 有用 | 指数退避后重试 |
| 500 | `api_error` | Anthropic 系统内部意外错误 | 有用 | 指数退避重试；一直出现就带 request ID 联系支持 |
| 504 | `timeout_error` | 请求在处理过程中超时 | 官方建议先改请求方式 | 长请求改用流式或 Message Batches API |
| 429 | `rate_limit_error`，带 `retry-after` 头 | 触发速率限制 | 有用 | 按 `retry-after` 的秒数等待后再试 |
| 429 | `rate_limit_error`，没有 `retry-after`，`error.details.error_code` 为 `enforced_spend_limit_reached` | 达到所在等级的月度消费上限 | 没用 | 等到下月 1 日 00:00 UTC 恢复，或申请更高等级 |
| 400 | `invalid_request_error`，message 以 `You have reached your specified API usage limits` 开头 | 达到你自己设置的消费限额 | 没用 | 在控制台调高或取消限额 |

判断顺序很简单：先看状态码是不是 529、`error.type` 是不是 `overloaded_error`；是就按下一节重试，不是就按表里对应的行处理。

## 529 的处理：官方 SDK 默认已经重试两次

官方错误文档写明：官方 SDK 会对连接错误、限流和 5xx 服务端错误这类临时故障自动重试，**默认 2 次**，使用指数退避，响应里有 `retry-after` 头时会遵守它。Python SDK 文档列出的默认重试范围是：连接错误、408、409、429 和 >=500 的错误，529 属于 >=500，在 Python SDK 里抛出的是 `InternalServerError`。

所以，如果你在日志里看到 SDK 抛出了 529，说明第一次请求和默认的 2 次重试都没有成功。可以按需要调大重试次数（官方示例）：

```python
from anthropic import Anthropic

client = Anthropic(max_retries=5)  # 对所有请求生效；默认 2，设成 0 关闭自动重试

client.with_options(max_retries=5).messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}],
)  # with_options 只对这一次请求生效
```

TypeScript、PHP 用 `maxRetries`，Java 用 `.maxRetries()`，C# 用 `MaxRetries`，Go 用 `option.WithMaxRetries()`，这是官方错误文档列出的写法。

两点注意：

1. 如果你在 SDK 外面再包了一层自己的重试循环，实际请求次数是两层次数相乘，排查时要算进去，也可以把 SDK 的 `max_retries` 设为 0 只保留一层。
2. 官方文档建议按异常类型捕获错误（例如 Python 的 `anthropic.RateLimitError`、`anthropic.APIStatusError`），不要靠匹配报错文字判断。

## 流式请求先返回 200、中途才报 overloaded_error

用 `"stream": true` 时，错误可能出现在 API 已经返回 200 之后。官方错误文档说明，这种情况**不走上面的标准错误处理机制**；流式文档给出的事件格式是：

```text
event: error
data: {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"} }
```

流式文档的原话是：高峰期你可能在事件流里收到 `overloaded_error`，在非流式场景下它通常对应 HTTP 529。因此，自己解析 SSE 的代码要单独处理 `event: error`，不能只检查 HTTP 状态码。

官方流式文档给出的恢复办法（Error recovery 一节）：

1. 保存出错之前已经收到的全部内容；
2. 发一个新的请求继续：Claude 4.6 及以后的模型，新加一条 user 消息，里面放已收到的部分回答，并要求模型从断开的地方接着写（官方示例提示词的意思是：你上一次的回答被中断了，结尾是这段已收到的内容，请从断开的地方继续）；Claude 4.5 及更早的模型，是把已收到的部分作为新 assistant 消息的开头；
3. 继续接收流式结果。

官方同时说明：`tool_use` 和 `thinking` 块不能部分恢复，只能从最近的 text 块继续。另外，Claude 4.6 及以后的模型不支持预填 assistant 消息，带预填会返回 400，所以新模型一定要用 user 消息续写的方式。

## 和 429 区分：看有没有 retry-after、有没有 enforced_spend_limit_reached

429 和 529 都可以「等一下再试」，但原因不一样。速率限制文档说明：

- 超过 RPM、ITPM、OTPM 任一限制时返回 429，并说明是哪个限制；响应里有 `retry-after` 时，按它给出的秒数等待再重试，更早重试会失败。
- 达到等级的月度消费上限时，同样是 429 和 `rate_limit_error`，但**没有** `retry-after` 头，`error.details.error_code` 是 `enforced_spend_limit_reached`；这时重试（包括 SDK 的自动重试）会一直失败，直到额度恢复。
- 组织用量突然大幅增加时，可能因为「加速限制」（acceleration limits）收到 429。官方建议逐步增加流量、保持稳定的使用模式。
- API 响应里带有 `anthropic-ratelimit-requests-remaining`、`anthropic-ratelimit-tokens-remaining` 等响应头，可以用来看离限额还有多远。

如果你在一批任务里同时看到 429 和 529，先按 429 降低并发、按 `retry-after` 等待，再看 529 是否还持续出现。

## 和 504、客户端超时区分

504 `timeout_error` 是请求在处理中超时。官方建议长请求使用流式 Messages API 或 Message Batches API，尤其是超过 10 分钟的请求；不用流式时不要设置很大的 `max_tokens`，因为有些网络会断开空闲连接，导致请求失败或超时而收不到响应。

Python SDK 的相关默认行为（官方文档）：

- 默认请求超时 10 分钟，可以用 `timeout` 参数修改；超时抛出 `APITimeoutError`，并且默认也会重试 2 次；
- 预计会超过约 10 分钟的非流式请求，SDK 会直接抛 `ValueError`，传 `stream=True` 或自己设置 `timeout` 可以关闭这个检查。

所以，如果你看到的是 `APITimeoutError` 或连接被断开，问题在超时设置或网络，跟 529 过载不是一回事。

## 记下 request-id，一直报错时用它找原因

官方文档说明每个响应都有 `request-id` 响应头，错误响应体里的 `request_id` 是同一个值。Python 和 TypeScript SDK 在返回对象上提供 `_request_id` 属性；用 curl 时加 `-i` 可以看到响应头（官方示例）：

```bash
curl -sS -i https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello, Claude"}]}'
```

成功的标准：返回 200，响应头里有 `request-id`。如果 500 `api_error` 退避重试后仍然持续出现，官方建议带上 request ID 联系支持。

## 经中转调用 Claude 时怎么判断

经 Anthropic 兼容中转调用时，你看到的 529 可能来自上游，也可能是中转自己的处理结果；中转是否原样转发上游的状态码和错误正文，各家实现不同。排查时先看响应体里的 `error.type` 和 `message`，再按上面的表格处理。

以 OpenLux 为例，Anthropic Messages 协议的 Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端自己拼 `/v1/messages`），`x-api-key` 和 `Authorization: Bearer` 两种鉴权头都可以。另外两种常见报错和过载无关，不要靠重试解决：

- 401 `Invalid token`：Key 填错或没带，到控制台「令牌」页重新复制；
- 404 `Invalid URL (POST /v1/v1/messages)`：Base URL 多写了 `/v1`，去掉即可。

还没有令牌的话，可以先 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-529-overloaded-error-retry-fix&utm_content=footer)，在「令牌」页创建后按上面的方法配置并验证。

## 同专题文章

- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁](https://a37836323.github.io/openlux-api-guides/news/claude-api-prompt-is-too-long-400-fix/)
- [Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了](https://a37836323.github.io/openlux-api-guides/news/claude-prompt-cache-miss-diagnostics-fix/)
- [Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: "fast" 的请求会报错，留在 4.8 还是换 Opus 5.5](https://a37836323.github.io/openlux-api-guides/news/claude-opus-4-8-fast-mode-removal-opus-5-5-migration/)
- [Claude 的 usage_report / cost_report 被标为 legacy，如何迁移到 Analytics API 并正确传 beta header？](https://a37836323.github.io/openlux-api-guides/news/claude-usage-cost-analytics-api-migration/)
- [Claude API 报 413 request_too_large 怎么办：128 MB 请求上限、图片和 PDF 改用 file_id](https://a37836323.github.io/openlux-api-guides/news/claude-api-413-request-too-large-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

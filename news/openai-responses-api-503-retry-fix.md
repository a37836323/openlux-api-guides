---
layout: default
title: "OpenAI Responses API 间歇性报 503 怎么办：server_is_overloaded、服务端错误与重试设置"
description: "OpenAI Responses API 间歇性返回 503 的处理：按 error.code 区分 server_is_overloaded、其他服务端错误与 429 slow_down，遵守 Retry-After，用带抖动的指数退避并限制次数和总时长，避免 SDK 与应用层重试叠加，流式请求不自动重放，持续出现时查状态页并带请求 ID 联系支持。"
permalink: /news/openai-responses-api-503-retry-fix/
date: 2026-10-26
---

> 更新日期：2026-10-26 · 一手来源：[OpenAI 官方文档：Error codes](https://developers.openai.com/api/docs/guides/error-codes)

# OpenAI Responses API 间歇性报 503 怎么办：server_is_overloaded、服务端错误与重试设置

调用 OpenAI Responses API 时偶尔返回 503、重试一两次又成功，按官方文档的处理方式是：先看响应体里的 `error.code` 区分原因，有 `Retry-After` 就至少等这么久再重试，没有就用带随机抖动的指数退避，并且同时限制重试次数和总耗时；如果持续出现，去 [OpenAI 状态页](https://status.openai.com/) 看有没有进行中的事故，再带上请求 ID 联系官方支持。本文依据 OpenAI 官方的 [Error codes 文档](https://developers.openai.com/api/docs/guides/error-codes)、[Rate limits 文档](https://developers.openai.com/api/docs/guides/rate-limits) 和官方 Python SDK 的 [README](https://github.com/openai/openai-python) 整理，适用于直接调用 api.openai.com 的开发者；官方这套错误处理规则对其他 OpenAI API 接口同样适用。

背景：OpenAI 开发者社区里，有开发者反馈从 2026 年 10 月 25 日 22:00 UTC 左右开始，Responses API 间歇性 503 明显增多，涉及 gpt-6-luna、gpt-6-sol，另一位开发者补充 GPT-5.6 系列也有同样现象；他们的请求大多在第二、三次重试时成功。截至本文写作时，该帖下还没有官方答复，所以下面只讲官方文档给出的通用处理方法，不对这次现象的原因下结论。

## 先看响应体：503 不只一种

官方文档特别提醒：不同错误可能共用同一个 HTTP 状态码，选择处理方式前要先检查错误体。把常见情况按官方说法整理如下：

| 你看到的错误 | 官方说明的含义 | 官方建议的处理 |
|---|---|---|
| 503，type 为 `service_unavailable_error`，code 为 `server_is_overloaded` | 所请求的模型暂时没有足够容量处理请求 | 有 `Retry-After` 先等够再重试；没有就逐次加大重试间隔；持续出现就查状态页 |
| 503，但错误体不是上面这种（例如社区帖里的 “OpenAI is experiencing server issues. upstream connect error …”） | 错误码文档没有单列这段文字；Python SDK 对 503 抛出 `InternalServerError`，官方对它的说明是服务端问题 | 稍等几秒重试；查状态页；持续出现就按「持续性错误」准备材料联系支持 |
| 500 The server had an error while processing your request | 服务端问题 | 短暂等待后重试，持续出现就联系官方并查状态页 |
| 429，code 为 `slow_down` | 请求量上涨太快，即使没超过 RPM、TPM 也可能出现 | 遵守 `Retry-After`，降低请求速率后再逐步加量 |
| 没有 HTTP 状态码，SDK 抛 `APIConnectionError` 或 `APITimeoutError` | 请求没连上服务，或请求超时 | 检查网络、代理、证书、防火墙；超时可稍等后重试 |

第二行要特别说明：官方没有解释 “upstream connect error” 这类文字的具体含义，本文也不做推测，只按官方对服务端错误的通用建议处理。

## 503 和 429 slow_down 要分开处理

官方在 Rate limits 文档的「Update existing error handlers」一节说明过一次错误码调整：以前有些接口在「流量上涨太快」和「模型过载」两种情况下都返回 503 加 `slow_down`；现在流量上涨太快改为返回 429 加 `slow_down`，模型过载仍是 503，但 code 改为 `server_is_overloaded`。

这对代码的影响：

1. SDK 里 429 和 503 是两个异常类。Python、TypeScript、Ruby 分别是 `RateLimitError` 和 `InternalServerError`，Java 是 `RateLimitException` 和 `InternalServerException`。只捕获其中一个的旧代码，要两个都处理。
2. 两者的应对不同：`slow_down` 需要你主动降速再逐步加量；`server_is_overloaded` 是模型侧容量不足，按 `Retry-After` 和退避重试即可。
3. 官方建议在应用还可能收到旧错误码期间，保留对旧错误码的兼容处理。
4. 额度、账单、花费上限类错误（例如 `credit_balance_exhausted`、`project_spend_limit_exceeded`）也可能是 429，官方明确说重试不能恢复，要先处理额度或限额。

## 重试怎么设置：官方给出的规则

官方 Rate limits 文档对重试的要求可以归纳为下面几条：

- 有 `Retry-After` 时，把它当作最短等待时间，至少等这么久；官方在重试说明里还建议再加一点随机延迟，避免多个客户端同时重试。
- 没有 `Retry-After` 或值无效时，用指数退避加随机抖动。
- 同时限制重试次数和重试总时长；如果服务端要求的等待超过你允许的上限，就停止重试、把请求延后处理，而不是提前重试。
- 失败的请求也会计入每分钟限额，不停地立刻重发没有用。
- 官方 SDK 会按自身的重试设置自动重试符合条件的 429 和 503。如果你在应用层也写了重试，要么关掉 SDK 重试，要么把 SDK 的重试次数算进总预算，否则两层循环会把请求数成倍放大。

官方 Python SDK 的 README 写明：连接错误、408、409、429 和大于等于 500 的错误默认自动重试 2 次，使用较短的指数退避；可以用 `max_retries` 在客户端或单次请求上调整，设为 0 表示关闭重试；默认超时为 10 分钟，超时会抛 `APITimeoutError`，同样默认重试 2 次。另外，只有请求体可以安全重发时才会重试。

一个按上述规则分流的最小示例（Python）：

```python
import openai
from openai import OpenAI

client = OpenAI(max_retries=2)  # 默认值就是 2，0 表示关闭 SDK 重试

try:
    response = client.responses.create(model="gpt-6-luna", input="Hello world")
    print(response.output_text)
except openai.RateLimitError as e:
    # 429：slow_down 要降速；额度、账单类错误要先处理，不要重试
    print(e.status_code, e.code, e.request_id)
except openai.InternalServerError as e:
    # 503 等服务端错误：SDK 重试用完后才会走到这里
    print(e.status_code, e.code, e.request_id)
except openai.APIConnectionError as e:
    print("连接失败：", e)
```

如果你像社区那位开发者一样在应用层另外做了固定 30 秒间隔的重试，按官方规则可以改成：优先读 `Retry-After`，没有时用指数退避加抖动，并设置最多几次、最长多久的上限。

## 流式请求要额外注意

官方说明：上面这些 HTTP 错误响应只在流开始之前返回。流已经开始后发生的错误，可能以流事件的形式到达。官方明确要求：已经消费了部分输出之后，不要自动重放请求。

实际处理上可以这样分：

1. 流开始前拿到 503：按上一节的规则重试。
2. 流中途出错：记录已收到的内容和错误事件，不要由重试代码自动重发。之后是提示用户还是重新发起，由业务自己决定，官方文档没有给出统一方案。

## 持续出现时：查状态页并准备支持材料

如果重试之后仍然频繁 503，按官方建议：

1. 打开 [status.openai.com](https://status.openai.com/)，看是否有正在进行的事故或维护。官方建议有事故时关注更新，等事故解决后再重试。
2. 记录请求 ID。Python SDK 的响应对象有 `_request_id` 属性，来自响应头 `x-request-id`；请求失败时可以从 `openai.APIStatusError` 异常的 `request_id` 读取。
3. 通过官方帮助中心联系支持，提供官方要求的信息：使用的模型、收到的错误信息和错误码、发送的请求数据和请求头、带时区的请求时间，以及其他有助于排查的细节。发给支持或发到社区时，记得去掉 API Key 等敏感信息。

## 改完后怎么验证

- 日志：每次失败都能记下 HTTP 状态码、`error.type`、`error.code`、`Retry-After`（如有）和请求 ID，并能看出走的是 429 分支还是 503 分支。
- 重试次数：确认 SDK 重试与应用层重试加起来有明确上限，单个请求的最长等待时间符合业务预期。
- 分类正确：`slow_down` 会触发降速；额度、账单类错误不会被重试；`server_is_overloaded` 和其他 5xx 会按退避重试。
- 流式：模拟流中途中断时，不会自动重放已经输出过内容的请求。
- 成功标准：偶发的 503 能在有限次数内恢复；持续性的 503 能带着请求 ID 和时间戳被上报，而不是被无限重试掩盖。

## 参考资料

- 官方文档：[Error codes](https://developers.openai.com/api/docs/guides/error-codes)
- 官方文档：[Rate limits](https://developers.openai.com/api/docs/guides/rate-limits)
- 官方仓库：[openai-python README](https://github.com/openai/openai-python)
- 官方状态页：[status.openai.com](https://status.openai.com/)

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-responses-api-503-retry-fix&utm_content=footer)。

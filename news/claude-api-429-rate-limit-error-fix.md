---
layout: default
title: "Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分"
description: "Claude API 报 429 rate_limit_error 怎么办：超过 RPM、ITPM、OTPM 速率限制、加速限制和月度消费上限（enforced_spend_limit_reached）怎么区分，用 retry-after 和 anthropic-ratelimit-* 响应头确认撞的是哪条线，SDK 默认重试 2 次与 max_retries，以及用提示缓存、削峰、批处理和提额减少 429。"
permalink: /news/claude-api-429-rate-limit-error-fix/
date: 2026-11-07
---

> 更新日期：2026-11-07 · 一手来源：[Claude API 官方文档](https://platform.claude.com/docs/en/api/rate-limits)

# Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分

Claude API 返回 429、错误体里 `error.type` 是 `rate_limit_error`，意思是你的组织撞到了某条限制，不是请求写错了，也不是服务过载。按 [Claude API 官方速率限制文档](https://platform.claude.com/docs/en/api/rate-limits) 和 [错误码文档](https://platform.claude.com/docs/en/api/errors)，429 有几种来源：超过每分钟请求数（RPM）、每分钟输入 token（ITPM）或每分钟输出 token（OTPM）；用量突然大涨触发的加速限制；以及所在使用等级的月度消费上限。带 `retry-after` 的按它等一等就能恢复，月度消费上限那种重试多少次都没用。

先看一个字段就能分出大类：响应里有没有 `retry-after` 头，错误体里有没有 `error.details.error_code: "enforced_spend_limit_reached"`。本文适用于直接调用 Claude Messages API、用官方 SDK，或经 Anthropic 兼容中转调用的场景。

## 先分清是哪一种 429

| 情况 | 识别特征 | 重试有没有用 | 怎么处理 |
|---|---|---|---|
| 超过 RPM、ITPM 或 OTPM | 429 `rate_limit_error`，报错会说明超了哪个限制，可能带 `retry-after` | 有用；带 `retry-after` 时要等够它给的秒数 | 等待后重试；长期解决看下文的缓存、削峰和申请提额 |
| 加速限制（acceleration limits） | 429，组织用量刚刚大幅上涨时出现 | 带 `retry-after` 就按它等待；根本办法是放缓流量 | 官方建议逐步增加流量，保持稳定的使用模式 |
| 等级的月度消费上限 | 429 `rate_limit_error`，**没有** `retry-after`，`error.details.error_code` 为 `enforced_spend_limit_reached` | 没用，SDK 自动重试也会一直失败 | 等到下个月 1 日 00:00 UTC 恢复，或申请更高等级 |
| Claude Code 工作区的消费限额 | 429，带 `retry-after` | 按 `retry-after` 等待 | 调高该工作区的限额 |
| 快速模式（`speed: "fast"`）的专用限流 | 429，带 `retry-after`，响应里有 `anthropic-fast-*` 头 | 有用 | 按 `retry-after` 等待；快速模式的限额与普通限额分开 |

还有一种情况容易被误认成 429：你**自己**在 Billing 页设置的消费限额用完时，官方返回的是 **400** `invalid_request_error`，消息以 `You have reached your specified API usage limits` 开头（工作区限额是 `You have reached your specified workspace API usage limits`），并写明何时恢复。这时要去调高或取消自设限额，而不是改重试逻辑。

另外，529 `overloaded_error` 是 API 整体过载，和你的组织限额无关，处理方式见 [Claude API 报 529 overloaded_error 怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)。

## 速率限制是怎么算的：RPM、ITPM、OTPM 与令牌桶

官方文档对 Messages API 速率限制的几条说明，直接决定你该怎么排查：

- **按模型分别计算**。每个模型（或模型组）各有一套 RPM、ITPM、OTPM。有些行是多个模型共用一个额度，例如 Opus 4.8、4.7、4.6、4.5 共用一组，Opus 5.5 和 Opus 5 各自单独计算。所以换到另一组模型后不再 429，并不说明原模型出了故障，只是换了一个额度池。
- **令牌桶算法**。额度是持续补充、补到上限为止，不是每分钟整点清零。
- **可能按更短的时间窗口执行**。官方举例：60 RPM 可能按每秒 1 个请求来执行，短时间的突发请求即使一分钟总量没超，也可能触发 429。
- **ITPM 只算未命中缓存的输入**。计入 ITPM 的是 `input_tokens`（最后一个缓存断点之后的 token）和 `cache_creation_input_tokens`（写入缓存的 token）；`cache_read_input_tokens`（从缓存读取的 token）**不计入**。
- **OTPM 按实际生成的 token 实时计算**。`max_tokens` 不参与 OTPM 计算，把它调小并不能缓解 OTPM 限流。
- **`inference_geo` 共用一个额度**。`"us"` 和 `"global"` 从同一个限额池里扣。
- **新组织可能先在 Evaluation 等级**，限额低于文档里的标准值，随使用历史积累自动提高。

你所在组织的等级和当前限额，在 Claude Console 的 Rate limits 页（`platform.claude.com/usage/limits`）查看；Usage 页还有「Rate Limit - Input Tokens」和「Rate Limit - Output Tokens」两张图，能看出每小时的峰值离限额还有多远、缓存命中率是多少。

## 用响应头确认撞的是哪条线

每个响应都带限流相关的响应头，出现 429 前后对比这些值，比猜更快：

| 响应头 | 含义 |
|---|---|
| `retry-after` | 还要等多少秒才能重试，更早重试会失败；不是每个 429 都带，消费上限的 429 一定不带 |
| `anthropic-ratelimit-requests-remaining` | 被限流前还剩多少个请求 |
| `anthropic-ratelimit-input-tokens-remaining` | 被限流前还剩多少输入 token（四舍五入到千） |
| `anthropic-ratelimit-output-tokens-remaining` | 被限流前还剩多少输出 token（四舍五入到千） |
| `anthropic-ratelimit-*-reset` | 对应额度完全补满的时间，RFC 3339 格式 |
| `anthropic-ratelimit-tokens-*` | 当前生效的**最严格**那条 token 限制，例如撞的是工作区限额，这里显示的就是工作区的值 |

如果组织里设了多个工作区，再看 `anthropic-workspace-id` 响应头，它是这把 API Key 实际归属的工作区 ID。工作区可以单独设置比组织更低的 RPM、ITPM、OTPM；没设置时与组织限额相同；组织级限额始终同时生效。所以「组织额度还很多却一直 429」时，先查请求落在哪个工作区、那个工作区有没有单独限额。

用 curl 加 `-i` 可以直接看到这些头（示例与官方错误码文档一致）：

```bash
curl -sS -i https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2026-10-21" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello, Claude"}]}'
```

## 重试怎么写：官方 SDK 已经重试过两次

官方错误码文档写明：SDK 会对连接错误、限流和 5xx 这类临时故障自动重试，**默认 2 次**，使用指数退避，响应里有 `retry-after` 时会遵守它。Python SDK 文档列出的默认重试范围是连接错误、408、409、429 和 >=500，429 在 Python 里抛出的是 `anthropic.RateLimitError`。

也就是说，你的代码捕获到 `RateLimitError` 时，SDK 已经重试过了。可以用 `max_retries` 调整次数，用 `with_raw_response` 读取正常响应的限流头：

```python
import anthropic

client = anthropic.Anthropic(max_retries=5)

try:
    raw = client.messages.with_raw_response.create(
        model="claude-sonnet-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello, Claude"}],
    )
    print(raw.headers.get("anthropic-ratelimit-input-tokens-remaining"))
    message = raw.parse()
except anthropic.RateLimitError as e:
    print(e.status_code, e.response.headers.get("retry-after"))
    print(e.response.text)
```

写重试逻辑时注意三点：

1. **有 `retry-after` 就至少等这么久**，提前重试只会再拿一次 429。
2. **没有 `retry-after` 且是 `enforced_spend_limit_reached`，不要重试**，直接告警或停任务，否则 SDK 的自动重试加上你自己的重试只会白白堆积失败请求。
3. **应用层再套一层重试时，把 SDK 的重试次数算进去**，避免一次失败被放大成十几次请求，反而更容易触发限流。

## 从根上减少 429：缓存、削峰、批处理与提额

等待重试只能解决偶发的 429。如果每天固定时段都报，按下面的顺序处理：

1. **用提示缓存把输入挪出 ITPM**。缓存读取的 token 不计入 ITPM。官方示例：ITPM 限额 2,000,000、缓存命中率 80% 时，每分钟实际可以处理 10,000,000 个输入 token（200 万未缓存加 800 万缓存读取）。适合缓存的是重复出现的系统提示、长文档、工具定义和对话历史；命中率在 Console 的 Usage 页查看。
2. **削平突发**。限额可能按秒级执行，同一时刻并发打出大量请求最容易触发 429。给并发设上限、让请求均匀发出，能减少这类 429。
3. **避免流量突然翻倍**。官方对加速限制的建议是逐步增加流量、保持稳定的使用模式；新功能上线或批量任务启动时，分批放量。
4. **不急的任务改走 Message Batches API**。批处理有自己的一套限额（RPM、队列中批处理请求数、单批请求数），与 Messages API 的限额分开计算。
5. **检查工作区限额**。如果你给某个工作区设了较低的限额，那个工作区会先撞线，即使组织总额度还有余量。
6. **申请更高限额**。在 Console 的 Rate limits 页点 **Request tier increase**；紧急情况可联系 Anthropic 支持。等级的月度消费上限也通过这里提高。

## 经中转调用 Claude 时怎么判断

经 Anthropic 兼容中转调用时，你看到的 429 可能来自上游，也可能来自中转自身的限制；响应里是否带 `retry-after`、`anthropic-ratelimit-*` 这些头，取决于中转是否原样转发，以实际返回为准。排查时先看错误体里的 `error.type` 和 `message`，再对照上面的表格。

以 OpenLux 为例，Anthropic Messages 协议的 Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端自己拼 `/v1/messages`），`x-api-key` 和 `Authorization: Bearer` 两种鉴权头都可以。下面两种报错和限流无关，重试解决不了：

- 401 `Invalid token`：Key 填错或没带，到控制台「令牌」页（`https://www.openlux.ai/console/token`）重新复制；
- 404 `Invalid URL (POST /v1/v1/messages)`：Base URL 多写了 `/v1`，去掉即可。

## 怎么确认已经修好

- 连续跑一段业务高峰流量，日志里不再出现 429，或者出现后按 `retry-after` 等待一次就成功；
- 正常响应里 `anthropic-ratelimit-input-tokens-remaining`、`anthropic-ratelimit-output-tokens-remaining` 在高峰时也没有降到 0；
- 开了提示缓存的，响应 `usage` 里 `cache_read_input_tokens` 不为 0，Usage 页的缓存命中率上升；
- 遇到 `enforced_spend_limit_reached` 时，程序会停下并告警，而不是一直重试。

如果你想用一把令牌同时调用 Claude、GPT 和 Gemini，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-429-rate-limit-error-fix&utm_content=footer)，在「令牌」页创建后按上面的方法配置并验证。

## 同专题文章

- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁](https://a37836323.github.io/openlux-api-guides/news/claude-api-prompt-is-too-long-400-fix/)
- [Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)
- [Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了](https://a37836323.github.io/openlux-api-guides/news/claude-prompt-cache-miss-diagnostics-fix/)
- [Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: "fast" 的请求会报错，留在 4.8 还是换 Opus 5.5](https://a37836323.github.io/openlux-api-guides/news/claude-opus-4-8-fast-mode-removal-opus-5-5-migration/)
- [Claude 的 usage_report / cost_report 被标为 legacy，如何迁移到 Analytics API 并正确传 beta header？](https://a37836323.github.io/openlux-api-guides/news/claude-usage-cost-analytics-api-migration/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

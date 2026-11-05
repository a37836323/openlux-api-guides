---
layout: default
title: "Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设"
description: "Gemini API 返回 503 UNAVAILABLE、500 或 504 时，按 Google 官方错误码页与排错指南区分服务过载、服务端错误和超时，说明 Flex/Priority 档位下 503 的差别、SDK 超时怎么设、流式错误事件和退避重试怎么写。"
permalink: /news/gemini-api-503-unavailable-500-504-fix/
date: 2026-11-04
---

> 更新日期：2026-11-04 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/api-errors)

# Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设

Gemini API 返回 **503**（排错指南里写作 `503 UNAVAILABLE`，Interactions API 的错误码是 `service_unavailable`），按 Google 官方 [API errors](https://ai.google.dev/gemini-api/docs/api-errors) 页的说明，是服务暂时过载或不可用，做法是等一会儿再用指数退避重试。**500**（`api_error`）是服务端发生了意外错误，官方建议重试，持续出现再联系支持。**504**（`deadline_exceeded`）是请求没能在截止时间内完成，官方建议去掉或调大客户端的截止时间设置，改用服务端默认值——也就是先查超时设置，而不是用同样短的超时反复重试。

本文适用于用 Gemini API Key 直接调用，以及经 OpenAI 兼容或 Gemini 原生格式的中转调用。429 `RESOURCE_EXHAUSTED`（限流、配额、消费限额）是另一类问题，见《[Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)》。

## 先确认是哪一类：5xx、499 和 4xx 对照

下表的错误码和建议都出自官方 API errors 页与 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting) 的重试一节。Interactions API 的报错是一个 `error` 对象，里面有 `code`（小写下划线形式）和 `message`，程序里按 `code` 分支处理。

| HTTP 状态 | `code` | 官方含义 | 官方建议 | 要不要重试 |
|---|---|---|---|---|
| 500 | `api_error` | 服务端发生意外错误 | 重试；持续出现就联系支持 | 要，设次数上限 |
| 501 | `unimplemented` | 操作或功能未实现、不支持 | 检查 API 能力，或换成支持的功能 | 先改请求 |
| 503 | `service_unavailable` | 服务暂时过载或宕机 | 等待后指数退避重试 | 要，设次数上限 |
| 504 | `deadline_exceeded` | 请求没在截止时间内完成 | 去掉或调大客户端截止时间，用服务端默认值 | 先调超时 |
| 499 | `cancelled` | 客户端在请求完成前取消了它 | 无需处理，通常是客户端断开 | 先查自己的超时和断连 |
| 429 | `rate_limit_exceeded` 等 | 超出速率或配额 | 退避重试或等配额重置 | 见 429 那篇 |
| 400 / 402 / 403 | `invalid_request`、`payment_required`、`permission_denied` 等 | 请求写错、预付余额用完、权限或项目受限 | 改请求、充值、查权限 | 官方明确说不要重试 |

官方排错指南的原则是：只对临时性错误（`429`、`408`、`5xx`）重试，`400`、`402`、`403` 这类客户端错误不要重试，因为重试也不会成功。

## 503：服务过载，先看用的是哪个服务档位

默认（Standard）档位下，503 的官方解释就是「服务暂时过载或宕机」，按下一节的方法退避重试即可。如果你在请求里设了 `service_tier`，要分开看：

- **Flex**：官方 [Flex inference](https://ai.google.dev/gemini-api/docs/flex-inference) 文档写明，Flex 用的是可被抢占的算力，标准流量突增时 Flex 请求可能被抢占或驱逐；容量不够或系统拥塞时返回 503（系统当前已满载）或 429。系统**不会**在 Flex 满载时自动把请求升级到 Standard（为了避免意外费用），客户端必须自己写指数退避重试；Flex 请求可能在队列里等待，官方建议把客户端超时调到 10 分钟以上。所以用 Flex 时 503 较多，要么接受排队和重试，要么把对时延敏感的请求改回 Standard。
- **Priority**：官方 [Priority inference](https://ai.google.dev/gemini-api/docs/priority-inference) 文档写明，超过 Priority 限额时，溢出的请求会自动降级到 Standard 处理，而不是直接报 503 或 429，降级的请求按 Standard 价格计费。可以看响应头 `x-gemini-service-tier` 判断是否经常被降级到 `standard`；对 `DEADLINE_EXCEEDED` 这类标准错误仍要自己写重试。

## 500 和 501：服务端错误与不支持的功能

500（`api_error`）官方只给了两步：重试；如果一直出现，联系支持。排查时把报错的 `message`、发生时间、模型名和是否流式记下来，便于提交给支持或中转方。

501（`unimplemented`）表示你调用的操作或功能不被支持，官方给的建议不是重试，而是检查 API 能力或换用支持的功能；排错指南还提醒，要用对 API 版本（`/v1` 或 `/v1beta`），处于 Beta 阶段的功能只在 `/v1beta` 下可用，并确认所用模型在 [模型页](https://ai.google.dev/gemini-api/docs/models) 上、支持你要的功能。

## 504、499 与超时：先分清是谁的超时

504 `deadline_exceeded` 的官方建议是去掉或调大客户端的截止时间设置。官方 SDK 的超时单位是**毫秒**，Python 写法（出自 Flex 文档）：

```python
from google import genai

client = genai.Client(http_options={"timeout": 900000})
```

JavaScript SDK 则是在请求的第二个参数里传 `{timeout: 900000}`。超时设多长，官方针对几种场景给了参考：

- **Flex 请求**：可能排队，建议 10 分钟以上，并保证客户端超时覆盖服务端愿意等待的时间。
- **gemini-4-argon 难题**：[迁移说明](https://ai.google.dev/gemini-api/docs/latest-model) 写明难的提示词可能要跑几分钟，建议用后台执行，或把 HTTP 客户端超时设到至少 15 分钟。
- **长视频与多步推理**：[视频理解](https://ai.google.dev/gemini-api/docs/video-understanding) 文档提醒，同步、非流式请求在高负载下遇到后端重试时，可能超出连接或鉴权令牌的有效时间，表现为意外的 `401 Unauthorized` 或超时报错，建议改用流式或后台执行。

如果报的是 499 `cancelled`，含义是客户端在完成前取消了请求，官方说通常是客户端断开了连接，可以先查自己代码、代理或 SDK 的超时设置。

对于本来就要跑很久的任务，官方 [后台执行](https://ai.google.dev/gemini-api/docs/background-execution) 文档写明：普通 HTTP 请求一般 60 秒左右就会断开，可以在 Interactions API 创建请求时设 `"background": true`，接口会立刻返回 interaction ID，之后轮询状态或流式读取进度。注意后台执行要求 `store` 为 `true`（默认值），同时传 `background=True` 和 `store=False` 会返回 400。

## 流式请求中途报错怎么处理

官方 API errors 页写明，Interactions API 的流式（SSE）请求出错时，错误是作为一条 `event_type` 为 `"error"` 的事件在流里发过来的，里面同样有 `code` 和 `message`。所以解析器不能只看 HTTP 状态码，要处理 `error` 事件，再按上面的表决定是否重试。

后台执行的流式读取如果被网络中断，官方给的办法是记下每条事件的 `event_id`，重新获取流时把它作为 `last_event_id` 传回去，从断点继续，不用整个请求重来。

## 重试怎么写：SDK 已经会重试

官方排错指南写明，Gemini 官方 SDK（例如 Python SDK）默认会对超时、网络问题和 `429`、`5xx` 自动做指数退避重试；以 Python SDK 为例，临时错误最多重试 4 次，初始间隔约 1 秒，最大间隔 60 秒。所以用 SDK 时，外面再加重试也要设上限，避免次数层层叠加。

直接调 REST 或自己写重试时，按官方的四条做：

1. **指数退避**：第一次等约 1 秒，之后 2 秒、4 秒、8 秒递增。
2. **加随机抖动**：在等待时间上加随机量，避免所有客户端同一时刻一起重试。
3. **只重试临时错误**：`429`、`408`、`5xx`；`400`、`402`、`403` 不重试。
4. **设最大次数**：防止无限循环；超过上限就把错误交给上层处理或提示用户稍后再试。

504 是例外：先按官方建议调大或去掉客户端截止时间，再决定是否重试。

## 经中转调用时怎么排查

经 OpenLux 这类中转调用时，请求不经过你自己的 Google 项目，AI Studio 里看不到这些请求，排查要从中转这一侧入手：

1. **先确认地址和 Key 都对**。OpenAI 兼容格式填 `https://api.openlux.ai/v1`；Gemini 原生格式填 `https://api.openlux.ai`，实际请求路径是 `/v1beta/models/<模型>:generateContent`，Key 放在 `x-goog-api-key` 请求头或查询参数 `?key=`。用下面的请求能列出模型，就说明地址和 Key 都没问题：

   ```bash
   curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
   ```

2. **排除不是 5xx 的情况**：返回 401 `Invalid token` 是 Key 错或没带，到控制台 [令牌页](https://www.openlux.ai/console/token) 重新创建；返回 404 `Invalid URL (...)` 时，对照括号里的实际请求路径，检查 Base URL 是否多写或少写了一层。
3. **模型名用在售的 ID**，例如 `gemini-3.8-flash`、`gemini-4-argon`，以价格页为准，不要自己拼写。
4. **客户端超时和重试仍由你这一侧负责**：上面关于客户端超时、退避重试的做法同样适用。持续出现 5xx 时，记下报错原文、时间和模型名，联系中转方排查。
5. **官方专有功能先确认**：本文中转部分只核实过 OpenAI 兼容和 Gemini 原生 `generateContent` 两个入口；`service_tier`（Flex / Priority）、Interactions API 的后台执行等功能能否经中转使用，请先向中转方确认，不要直接照搬上文的官方用法。

## 怎么算解决了

- `/v1/models` 能列出模型，同一个请求重新发送后正常返回内容。
- 偶发的 503、500 在退避重试几次内成功，且重试次数有上限，不会无限循环。
- 长任务不再出现 504 或 499：客户端超时已按场景调大，或已改用流式、后台执行。
- 用 Flex 的话，503 比例在可接受范围内；用 Priority 的话，通过 `x-gemini-service-tier` 响应头确认降级频率。

想直接用 Gemini 原生格式或 OpenAI 兼容格式调用 Gemini 模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-503-unavailable-500-504-fix&utm_content=footer)。

## 同专题文章

- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)
- [Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些](https://a37836323.github.io/openlux-api-guides/news/gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

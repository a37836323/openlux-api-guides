---
layout: default
title: "OpenAI API 报 429 先看 error.code：限流、余额用完、消费上限与月度用量上限怎么区分"
description: "OpenAI API 返回 429 有 6 种：Rate limit reached、slow_down、credit_balance_exhausted、组织/项目消费上限与月度用量上限。按 error.code 判断能否重试，附 Build/Launch/Grow 三档用量等级与旧错误处理代码的改法。"
permalink: /news/openai-api-429-error-code-usage-tier-fix/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[OpenAI API 文档](https://developers.openai.com/api/docs/guides/error-codes)

# OpenAI API 报 429 先看 error.code：限流、余额用完、消费上限与月度用量上限怎么区分

OpenAI API 返回 429，不一定是调用太快。OpenAI 官方[错误码页](https://developers.openai.com/api/docs/guides/error-codes)现在列出了 6 种 429：两种属于限流，可以按 `Retry-After` 等待后重试；另外 4 种是余额、消费上限或月度用量上限，需要人去改设置或充值，**一直重试也不会好**。所以第一步不是加重试，而是看响应里的 `error.code`。

本文适用于直接调用 OpenAI 官方 API（Responses、Chat Completions 等）时遇到的 429。官方在 2026 年 10 月 6 日把用量等级从五档简化为 Build、Launch、Grow 三档（见[官方更新日志](https://developers.openai.com/api/docs/changelog)），下面一并说明。

## 六种 429 对照表

以下内容整理自官方错误码页和 [Spend limits 文档](https://developers.openai.com/api/docs/guides/spend-limits)：

| 报错 | error.code | 原因 | 怎么处理 | 重试有用吗 |
|---|---|---|---|---|
| Rate limit reached for requests | （官方未写固定 code） | 短时间内请求数或 token 数超过分配的速率限制 | 降低频率；有 `Retry-After` 就至少等这么久，没有就用带随机抖动的指数退避 | 有用，但要限次数 |
| Slow down | `slow_down`（type 为 `rate_limit_error`） | 请求量**增长得太快**，即使没超过 RPM/TPM 也可能出现 | 按 `Retry-After` 等待，先降流量再逐步加回 | 有用，同时要放慢增长 |
| Credit balance exhausted | `credit_balance_exhausted` | 组织的预付余额用完 | 到账单设置页充值 | 没用 |
| Organization spend limit reached | `organization_spend_limit_exceeded` | 组织达到自己设置的月度硬性消费上限 | 调高或取消组织消费上限，或等下个月重置 | 没用 |
| Project spend limit reached | `project_spend_limit_exceeded` | 项目达到自己设置的月度硬性消费上限 | 在项目设置里调高或取消，或等下个月重置 | 没用 |
| Organization usage limit reached | `organization_usage_limit_exceeded` | 组织达到 OpenAI 分配的月度用量上限 | 在组织限额页申请更高额度，或联系支持 | 没用 |

官方在速率限制文档里写得很明确：`Retry-After` 不代表额度、账单这类需要用户处理的错误能靠重试解决，也不要重试这类错误。

## 第一步：拿到 error.code 和响应头

用代码调用时，把失败响应的 HTTP 状态码、JSON 里的 `error.code` 和响应头都记进日志。官方[速率限制文档](https://developers.openai.com/api/docs/guides/rate-limits)列出的相关响应头：

| 响应头 | 含义 |
|---|---|
| `Retry-After` | 临时限流时重试前至少要等的秒数（不一定每次都有） |
| `x-ratelimit-limit-requests` / `x-ratelimit-limit-tokens` | 当前请求数、token 数的上限 |
| `x-ratelimit-remaining-requests` / `x-ratelimit-remaining-tokens` | 还剩多少请求数、token 数 |
| `x-ratelimit-reset-requests` / `x-ratelimit-reset-tokens` | 多久后恢复 |
| `x-ratelimit-*-project-tokens` | 有项目级 token 限额时可能出现 |

判断方法：

1. `error.code` 是上表后 4 种之一：直接跳到「额度类」处理，先停掉自动重试。
2. `error.code` 是 `slow_down`，或报错文字是 Rate limit reached：按「限流类」处理。
3. 状态码是 503、code 是 `server_is_overloaded`：这不是 429，是模型临时过载，按 `Retry-After` 重试，持续出现就看 [OpenAI 状态页](https://status.openai.com/)。

如果你买了 ChatGPT Plus 却在 API 里看到额度类报错，可以再看本站的 [ChatGPT Plus 与 API 额度排查](https://a37836323.github.io/openlux-api-guides/news/chatgpt-plus-api-insufficient-quota/)，那篇讲的是两套计费的区别。

## 限流类：Rate limit reached 与 slow_down

官方错误码页给出的常见原因：脚本循环或并发请求过多、多人或多个应用共用同一个 Key、所在等级限额较低、项目被设了限额。处理步骤：

1. **按 `Retry-After` 等待**：有这个头就至少等这么久，再加一点随机延迟，避免多个客户端同时重试；没有这个头就用指数退避加随机抖动。
2. **限制重试次数和总时长**。官方 SDK 会自动重试符合条件的 429 和 503；如果你在业务代码里也写了重试，要关掉 SDK 重试或把它算进总次数，避免两层重试把请求数翻倍。官方还提醒：失败的请求也计入每分钟限额，不停重发不会更快。
3. **检查是谁在用**：限额按组织和项目计算，不按用户。同组织其他人的调用也会占用额度。
4. **把 `max_tokens` 设得接近真实输出长度**：官方说明限额按 `max_tokens` 和按字符估算的 token 数中较大的那个计算，设得过大会白白占用 TPM。
5. **不需要实时结果的任务改用 [Batch API](https://developers.openai.com/api/docs/guides/batch)**，它不占同步请求的速率限额。
6. **`slow_down` 要放慢增长**：官方的经验值是流量到达每分钟 100 万输入 token 后，每 15 分钟增长不超过 50%。

## 额度类：余额、消费上限、月度用量上限

这 4 种按官方 Spend limits 文档「Restore API traffic」一节处理：

1. `credit_balance_exhausted`：组织预付余额用完，到 [账单设置](https://platform.openai.com/settings/organization/billing) 充值。
2. `organization_spend_limit_exceeded` 或 `project_spend_limit_exceeded`：先在 [用量页](https://platform.openai.com/settings/organization/usage) 对比当前消费和上限。组织上限在 Organization limits 页的 Spend 区域修改，项目上限在 Project settings → Limits 修改。不改的话，下个月度周期会自动重置。
3. `organization_usage_limit_exceeded`：这是 OpenAI 按用量等级分配的月度上限，和你自己设的消费上限是两回事，需要在 [组织限额页](https://platform.openai.com/settings/organization/limits) 申请更高的批准额度，或联系支持。

两个容易误会的点：

- 消费上限的执行不是即时的，实际记录的消费可能略超过设定值。
- 只设「消费提醒」（spend alert）不会拦截请求，只有打开 Enforce a hard limit 的硬性上限才会返回 429。

## 用量等级改为三档：Build、Launch、Grow

10 月 6 日起付费等级只有三档，组织累计充值金额达到门槛后自动升级。官方速率限制文档中的表格：

| 等级 | 升级条件（累计充值） | 月度用量上限 |
|---|---|---|
| Free | 位于支持的国家和地区 | $100 / 月 |
| Build | $5 | $500 / 月 |
| Launch | $100 | $5,000 / 月 |
| Grow | $500 | $200,000 / 月 |

同一页的标准速率限制：Build 档 Astra、Sol、Terra 为 5,000 RPM / 1,000,000 TPM，Luna 为 5,000 RPM / 2,000,000 TPM；Launch 档分别为 10,000 RPM / 4,000,000 TPM 与 10,000 RPM / 10,000,000 TPM；Grow 档分别为 15,000 RPM / 40,000,000 TPM 与 30,000 RPM / 180,000,000 TPM。你的组织实际适用的数值，以 Settings → Organization → Limits 页面显示的 Rate limits 为准，在 Usage Tiers 区域可以点 Upgrade tier 升级。

## 老代码要改的地方

官方速率限制文档「Update existing error handlers」一节说明了错误返回的变化：

- 以前有些接口把过快增长和模型过载都返回成 503 加 `slow_down`。现在过快增长返回 **429 加 `slow_down`**，模型过载仍是 503，但 code 改为 `server_is_overloaded`。
- 视频请求在创建任务前被拒，以前是 429 加 `rate_limit_exceeded`，现在分别是 429 加 `slow_down` 和 503 加 `server_is_overloaded`。
- Python、TypeScript、Ruby SDK 对 429 抛 `RateLimitError`，对 503 抛 `InternalServerError`（Java 是 `RateLimitException` 和 `InternalServerException`）。两种都要处理，并读取 `error.code` 决定是重试还是停下。官方建议：只要程序还可能收到旧的返回，就保留对旧状态码和 code 的处理。
- 流式请求中，上述 HTTP 错误只会在流开始前返回；流开始后出错会以流事件形式到达，已经收到部分输出时不要自动重放整个请求。

## 怎么确认已经修好

- 额度类：充值、调高上限或获批新额度后，用同一个 Key 发一个最小请求能返回 200，日志里不再出现对应的 `error.code`。
- 限流类：观察一段时间，`x-ratelimit-remaining-requests` 和 `x-ratelimit-remaining-tokens` 不再降到 0，429 只在突发高峰偶尔出现，并能在有限次数的重试内恢复。
- 错误处理：在单元测试里模拟几种 429 和 503 响应，确认程序能按 `error.code` 走对分支，额度类错误不会进入重试循环。

## 不想自己管等级和额度时

上面的等级、消费上限和用量上限都是 OpenAI 官方组织账号的规则。如果你只想用一个 Key 调用 GPT、Claude 等模型，也可以用 OpenAI 兼容的中转 API：Base URL 填 `https://api.openlux.ai/v1`，Key 在 OpenLux 控制台「令牌」页创建，先请求 `/v1/models`，能列出模型就说明地址和 Key 都正确。

注册入口：[注册 OpenLux 账号](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-429-error-code-usage-tier-fix&utm_content=footer)

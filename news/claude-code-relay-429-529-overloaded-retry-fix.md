---
layout: default
title: "Claude Code 走中转报 429、Repeated 529 Overloaded 或一直 Retrying 怎么办：限流、过载与重试变量逐项排查"
description: "Claude Code 走中转时一直 Retrying、报 Request rejected (429) 或 Repeated 529 Overloaded errors 怎么办。按 Claude Code 官方错误页和 Claude API 错误页，说明 429 与 529 的区别、用 /status 和 /v1/models 确认凭据、降低并发、/model 换模型，以及 CLAUDE_CODE_MAX_RETRIES、RETRY_WATCHDOG、529 退避变量怎么设。"
permalink: /news/claude-code-relay-429-529-overloaded-retry-fix/
date: 2026-11-08
---

> 更新日期：2026-11-08 · 一手来源：[Claude Code Error reference](https://code.claude.com/docs/en/errors)

# Claude Code 走中转报 429、Repeated 529 Overloaded 或一直 Retrying 怎么办：限流、过载与重试变量逐项排查

先说结论：Claude Code 走中转时一直显示 `Retrying in Ns · attempt x/y`，或者最后报 `API Error: Request rejected (429)`、`API Error: Repeated 529 Overloaded errors`，先分清是哪一类。429 是请求太多、碰到了限流，要降低并发，并确认用的是哪个凭据。529 是服务端容量满了，官方明确说它不是你的用量上限，等一会儿或用 `/model` 换个模型就行。重试次数和退避时间可以用 `CLAUDE_CODE_MAX_RETRIES` 等环境变量调整，但凭据用错、额度类的 429 靠重试解决不了。

本文适用于用 `ANTHROPIC_BASE_URL` 把 Claude Code CLI 接到中转（LLM 网关）的情况。报错原文和处理办法来自 Claude Code 官方 [Error reference](https://code.claude.com/docs/en/errors)，429 和 529 的定义来自 Claude API 官方 [Errors](https://platform.claude.com/docs/en/api/errors) 页。下文以 OpenLux 为例，Base URL 是 `https://api.openlux.ai`，不带 `/v1`。还没接入的读者，先看 [Claude Code 怎么接入 Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)。

## 先按提示原文对号入座

官方说明，Claude Code 遇到临时故障会先用指数退避自动重试，默认最多 10 次，之后才显示错误。重试时转圈处显示 `Retrying in Ns · attempt x/y`。遇到限流类错误时，标签会直接写明原因；其他错误先显示 `API error`，从第 3 次重试起（v2.1.198 及以上）改为写明具体原因。

| 提示原文 | 官方给出的含义 | 先做什么 |
|---|---|---|
| `Retrying in Ns · attempt x/y` | 正在自动重试，请求还没失败 | 先等；同一原因反复出现再往下查 |
| `API Error: Request rejected (429) · this may be a temporary capacity issue...` | 触发了 API Key 或项目上配置的速率限制；`ANTHROPIC_BASE_URL` 设为自定义地址时，句末写的是网关主机 | 用 `/status` 确认凭据，降低并发 |
| `API Error: Request rejected (429) · Too Many Requests` | Claude Code 和 API 之间的代理、负载均衡或网关自己返回了 HTML 格式的 429 页面，`·` 后面是这个页面的标题 | 确认是哪一层限的流，见第三步 |
| `API Error: Server is temporarily limiting requests (not your usage limit)` | API 的短时节流，和套餐额度无关；v2.1.199 起会先自动重试再显示 | 稍等再试，持续出现就看状态页 |
| `API Error: Repeated 529 Overloaded errors...` | API 容量已满，所有用户都可能遇到；不算你的用量上限 | 等几分钟再试，或用 `/model` 换模型 |
| `Opus is experiencing high load, please use /model to switch to Sonnet` | 容量按模型分别计算，当前模型负载高 | 按提示 `/model` 换模型 |
| `You've hit your session limit` / `weekly limit` | 订阅套餐的滚动用量额度用完了 | 本意是走中转的话，用 `/status` 查当前凭据 |

## 429 和 529 到底差在哪

按 Claude API 官方错误页：

- **429 `rate_limit_error`**：组织触发了速率限制，或用量等级的月度消费上限已到。官方特别说明，消费上限导致的 429 **没有 `retry-after` 响应头**，在恢复访问前会一直失败，重试没用。另外，用量短时间内猛增也可能因为「加速限制」收到 429，官方建议逐步提高流量。
- **529 `overloaded_error`**：API 暂时过载，在所有用户流量都很高时出现，与你自己的请求量无关。

走中转时还要多想一层：Claude Code 只看得到中转返回的状态码。429 可能是中转对你的令牌限的流，也可能是中转转发了上游的限流；Claude Code 的提示只会告诉你是哪个网关主机返回的。如果 429 长时间不消失，要去中转控制台查看，或者联系服务方。

## 第一步：确认请求走的是中转、用的是哪个凭据

官方给 429 的第一条建议是运行 `/status`，确认当前生效的凭据是你预期的那个。官方举的例子是：环境里残留一个 `ANTHROPIC_API_KEY`，请求就可能用上一个低等级的 Key，而不是你以为在用的那个。走中转时同样要看：

1. 在 Claude Code 里运行 `/status`，确认 Base URL 是中转地址，凭据一行是你为中转设置的变量。
2. 在启动 `claude` 的同一个终端里，用 OpenLux 的模型列表接口验证地址和令牌：

```bash
curl -sS -w '\n%{http_code}\n' https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer 你的OpenLux令牌"
```

返回 200 并列出模型，说明地址和令牌都对；返回 401 `Invalid token` 说明令牌错了，这不是限流问题，按 [Claude Code 走中转报 401 的排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-401-invalid-api-key-fix/) 处理。

## 第二步：429 先降并发

官方给 429 的另外两条建议是：到服务商控制台查看当前生效的限额，需要时申请更高等级；降低并发，避免同时跑很多个并行子代理（subagent），批量脚本跑大量任务时可以用 `/model` 换成更小的模型。结合 API 错误页里「加速限制」的说明，可以按下面的顺序处理：

1. 减少同时运行的 Claude Code 会话和子代理数量，看 429 是否消失。
2. 批量任务分批跑，让流量逐步上来，不要一下子全开。
3. 降了并发还是每次都 429，就不是瞬时限流了：去中转控制台看这个令牌的限额和用量，或联系服务方。

## 第三步：529 和高负载提示怎么处理

官方对 `Repeated 529 Overloaded errors` 的处理建议有三条：

- 看状态页。直连官方时看 status.claude.com；用自定义 `ANTHROPIC_BASE_URL` 时，Claude Code 的提示会写出网关主机，这时应该看中转服务方的状态。
- 等几分钟再试。官方强调 529 不是你的用量上限，也不消耗你的额度。
- 运行 `/model` 换一个模型，因为容量是按模型分别计算的。

如果 `·` 后面是 `Too Many Requests` 这类网页标题，说明 429 来自中间某一层的 HTML 页面，不是 API 的 JSON 错误。你如果在 Claude Code 和中转之间自己加了代理，先绕开它对照一次。v2.1.281 之前的版本会把整页 HTML 打印出来，升级后提示会简短很多。

## 第四步：按场景调重试变量

下面这些变量都来自官方 Error reference 的 Tune retry behavior 一节，可以在 shell 里导出，也可以写进 settings 文件的 `env` 块：

| 变量 | 默认值 | 作用 |
|---|---|---|
| `CLAUDE_CODE_MAX_RETRIES` | 10 | 重试次数，上限 15（v2.1.186 起）；脚本里调低能让失败更快暴露 |
| `CLAUDE_CODE_RETRY_WATCHDOG` | 未设置 | 设为 `1` 时，429/529 无限重试，其他临时错误重试 300 次；消费上限类 429 仍然立即失败（v2.1.199 起） |
| `CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS` | 未设置 | 开了上一项后，每个请求等待 429/529 恢复的最长时间（v2.1.295 起） |
| `CLAUDE_CODE_OVERLOADED_RETRY_BASE_DELAY_MS` | 500 | 529 重试的起始退避时间，最大 32000（v2.1.292 起） |
| `CLAUDE_CODE_OVERLOADED_RETRY_MAX_DELAY_MS` | 32000 | 529 重试的退避上限，最大 64000（v2.1.296 起） |

两种常见用法：

- **交互使用、想早点知道失败**：把 `CLAUDE_CODE_MAX_RETRIES` 调小，例如 `export CLAUDE_CODE_MAX_RETRIES=3`，不用每次等满 10 次。
- **无人值守的长任务**：设 `CLAUDE_CODE_RETRY_WATCHDOG=1`，遇到 429/529 一直等着重试；可以同时设 `CLAUDE_CODE_RETRY_WATCHDOG_MAX_WAIT_MS`，给每个请求等待 429/529 的时间封顶。

改了变量后要重新启动 Claude Code 才会生效。注意这些变量只能改「怎么重试」：凭据用错、额度用完这类 429，重试多少次都不会好，还是要回到第一步、第二步。

## 改完怎么验证

1. `/status` 里的 Base URL 和凭据都是中转那一套，curl `/v1/models` 返回 200。
2. 降低并发后，再跑原来的任务，转圈处不再反复出现 `Retrying ... attempt x/y`，或者偶尔出现但能自己恢复。
3. 529 换模型后能正常回复，符合官方说的「容量按模型计算」；过一段时间再切回原模型试试。
4. 如果报错变成了连接失败或超时，那是另一类问题，按 [Claude Code 走中转报 Unable to connect to API、Request timed out 的排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/) 处理；直接调 API 时遇到 429，可以参考 [Claude API 报 429 rate_limit_error 怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)。

## 开始使用

凭据确认无误、并发降下来、重试变量按场景设好之后，Claude Code 走中转偶尔遇到限流或过载也能自己恢复。还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-429-529-overloaded-retry-fix&utm_content=footer)，在控制台「令牌」页创建后，按接入篇配置 `ANTHROPIC_BASE_URL`。

## 同专题文章

- [Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-401-invalid-api-key-fix/)
- [Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/)
- [Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-model-picker-missing-models-fix/)
- [Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/)
- [Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)

[查看「Claude Code 接入与报错」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-code/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

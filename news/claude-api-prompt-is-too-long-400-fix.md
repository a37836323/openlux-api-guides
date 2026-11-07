---
layout: default
title: "Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁"
description: "Claude API 返回 400 invalid_request_error、提示 prompt is too long，是输入超过了模型上下文窗口：先区分 413 和 stop_reason 截断，再查各模型窗口大小、用 count_tokens 数 token，最后换 1M 模型或用 compaction、context editing 减输入。"
permalink: /news/claude-api-prompt-is-too-long-400-fix/
date: 2026-11-03
---

> 更新日期：2026-11-03 · 一手来源：[Claude API 官方文档（Context windows）](https://platform.claude.com/docs/en/build-with-claude/context-windows)

# Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁

调用 Claude Messages API（`/v1/messages`）返回 400 `invalid_request_error`、提示 `prompt is too long`，意思是**这次请求的输入本身已经超过了模型的上下文窗口**。按 Anthropic 官方 [Context windows 文档](https://platform.claude.com/docs/en/build-with-claude/context-windows)，这种情况在所有模型上都会直接报 400。解决办法只有两类：换上下文窗口更大的模型，或者把输入减下来。在 Claude 4.5 及更新的模型上，调 `max_tokens` 解决不了这个错误，因为超的是输入。

本文适用于直连 Anthropic 或经 OpenLux 等中转、用 Anthropic Messages 格式调用 Claude 的场景。下面先区分几种长得像的错误，再给数 token、减输入和验证的步骤。

## 先确认是不是这个错误

400 不只表示参数错。官方 [错误文档](https://platform.claude.com/docs/en/api/errors) 写明，组织或工作区达到你设置的消费上限时也会返回 400，所以要看 `error.message`，不要只看状态码。

| 现象 | 含义 | 改法 |
|---|---|---|
| 400 `invalid_request_error`，message 含 `prompt is too long` | 输入 token 超过模型上下文窗口 | 本文下面的步骤 |
| 413 `request_too_large` | 请求字节数超限（Messages API 上限 128 MB），和 token 数无关 | 图片、PDF 改用 file_id，见 [Claude API 报 413 的排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-413-request-too-large-fix/) |
| 200 正常返回，`stop_reason` 是 `model_context_window_exceeded` | 输出把上下文窗口用满，回答被截断 | 见下文「回答被截断」一节 |
| 200 正常返回，`stop_reason` 是 `max_tokens` | 输出达到你设的 `max_tokens` | 调大 `max_tokens` 或续写 |
| 用 Claude 4.5 之前的模型，输入没超窗口却报校验错误 | 旧模型上「输入 + `max_tokens`」超过窗口也会报错 | 调小 `max_tokens`，或加 beta 头（见下文） |

确认是第一行后，记下响应里的 `request_id`，方便后面对照。

## 各模型的上下文窗口有多大

按官方文档，下列模型的上下文窗口是 **1M token**，单次请求最多输出 128k token（`max_tokens`）：

| 模型 | 上下文窗口 | 说明 |
|---|---|---|
| Claude Opus 5.5、Opus 5、Opus 4.8、Opus 4.7、Opus 4.6 | 1M | 默认就是 1M，不需要 beta 头 |
| Claude Sonnet 5.5、Sonnet 5、Sonnet 4.6 | 1M | 同上 |
| Claude Haiku 5.5 | 1M | 官方说明提示词超过 100,000 token 时计价更高，以官方价格页为准 |
| Claude Fable 5.1、Fable 5、Mythos 5.1、Mythos 5 | 1M | 同上 |
| 其它 Claude 模型（包括已弃用的 Sonnet 4.5、Haiku 4.5） | 200k | 超过 200k 的输入只能换模型或减输入 |

另外，单次请求最多 600 张图片或 PDF 页（200k 窗口的模型是 100），图片和大文档多时可能先碰到请求大小上限。

所以第一件事是看你调用的模型 ID。如果你用的是 200k 窗口的模型，而输入在 200k 到 1M 之间，直接换成 1M 窗口的模型就能解决。

## 哪些内容会算进上下文

官方文档列得很清楚，很多人只算了用户消息，漏了下面几项：

- `system` 提示词；
- `messages` 里的每一条，包括 `tool_result`、图片和文档；
- `tools` 里的工具定义；
- 本轮输出，包括思考内容。

两个容易误判的地方：

1. **提示缓存不减少占用**。用了 prompt caching 后，输入会拆成 `input_tokens`、`cache_read_input_tokens`、`cache_creation_input_tokens` 三项，三项都计入上下文窗口。缓存改变的是计费方式，不是占用多少。
2. **历史思考块是否计入，取决于模型**。在 Opus 4.5 及之后的 Opus、Sonnet 4.6 及之后的 Sonnet、Haiku 5.5、Fable、Mythos 等模型上，API 默认保留之前轮次的思考块，它们和其它输入一样计入窗口；更早的 Opus、Sonnet 以及 Haiku 4.5 及以前的模型会自动剥掉历史思考块。因此从旧模型换到新模型后，同样长度的多轮对话占用可能更多。

## 排查步骤：先数清楚再动手

**第 1 步：用 token 计数接口数一次。** 官方 [Token counting 文档](https://platform.claude.com/docs/en/build-with-claude/token-counting) 提供 `POST /v1/messages/count_tokens`，参数和创建消息一样（支持 system、tools、图片、PDF），返回 `input_tokens`。Python 写法：

```python
import anthropic

client = anthropic.Anthropic()
r = client.messages.count_tokens(
    model="claude-sonnet-5-5",
    system=system_prompt,
    messages=messages,
    tools=tools,
)
print(r.input_tokens)
```

这个接口免费，但有单独的每分钟请求数限制，和创建消息的限额互不影响。官方说明结果是**估算值**，实际输入可能有少量差异。

**第 2 步：和窗口对比。** `input_tokens` 已经超过模型窗口，就是本文的错误；离窗口很近，即使这次没报错，回答也可能因为窗口用满被截断。

**第 3 步：找出大头。** 分别去掉 tools、早期对话、大段工具结果后再数，看哪一块占得最多，再按下一节处理。

如果 count_tokens 走中转时调不通，可以先看之前成功请求返回的 `usage`：把 `input_tokens`、`cache_read_input_tokens`、`cache_creation_input_tokens` 三项相加，看每轮增长多少。

## 怎么把输入减下来

按官方文档给出的方向，从改动小到大：

1. **换 1M 窗口模型**：当前是 200k 窗口的模型时最直接。
2. **长对话和 Agent 用服务端压缩（compaction）**：官方把它作为长对话的首选办法，服务端会自动总结较早的对话，让对话越过窗口上限继续下去。目前是 beta，支持 Claude 4.6 及之后的模型，用法见 [Compaction 文档](https://platform.claude.com/docs/en/build-with-claude/compaction)。
3. **用 context editing 清理旧内容**：官方提供两种策略，清理旧的工具结果（tool result clearing），以及清理早期轮次的思考块（thinking block clearing）。
4. **减少工具定义的占用**：工具很多时，参考官方的 Manage tool context，或用 tool search tool 延迟加载工具定义。

自己在客户端删历史要小心，官方错误文档里有两条相关规则：

- 工具调用周期内，回传工具结果时必须**原样**带上对应的思考块（包括 signature）。最近一条 assistant 消息里的 `thinking` 或 `redacted_thinking` 块被修改、重排或过滤，会报另一种 400。
- Claude 5.1 及之后的模型会做前缀检查：思考块生成之后，它前面的 system、tools 或更早的消息被改动，再传回这个思考块就会报 400，提示思考块签名无效、`The block is bound to a different conversation`。也就是说，在这些模型上删掉早期对话，后面保留的思考块可能就过不了检查。官方给的处理是带 `thinking-binding-controls-2026-08-01` beta 头并设置 `prefix_mismatch_behavior: "drop_block"`（重试及之后每次请求都要带），或者删掉报错指出的那个思考块及其后所有思考块再重试一次。

所以长对话优先用上面的 compaction 或 context editing，由服务端处理，少自己动历史。

## 回答被截断：model_context_window_exceeded 与 max_tokens

如果没有报 400，但回答只出了一半，要看 `stop_reason`（官方 [Stop reasons 文档](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)）：

- **Claude 4.5 及更新的模型**：「输入 + `max_tokens`」超过窗口时 API 照常接受请求，生成到窗口上限就停，`stop_reason` 为 `model_context_window_exceeded`。官方的说法是回答仍然有效，但被上下文窗口限制了，应当按截断处理。这个值目前在 SDK 的 `beta` 命名空间里才有类型定义，用强类型语言判断时要注意。
- **更早的模型**（例如 `claude-opus-4-1-20250805`、`claude-sonnet-4-20250514`）：「输入 + `max_tokens`」超过窗口会直接返回校验错误。可以调小 `max_tokens`，或加 `model-context-window-exceeded-2025-08-26` beta 头启用上面的新行为。
- **`max_tokens`**：输出达到你设的上限。如果最后一个内容块是没写完的 `tool_use`，官方建议调大 `max_tokens` 重新请求，拿到完整的工具调用。

## 走中转调用时的注意事项

- OpenLux 的 Anthropic Messages 地址是 `https://api.openlux.ai`，**不带 `/v1`**，SDK 自己拼 `/v1/messages`。多写一个 `/v1` 会返回 404 `Invalid URL (POST /v1/v1/messages)`；Key 无效返回 401 `Invalid token`。这两种不是上下文问题，先排除。
- 模型 ID 只用价格页在售的，例如 1M 窗口的 `claude-sonnet-5-5`、`claude-opus-5-5`，200k 窗口的 `claude-sonnet-4-5-20250929`。
- 本文没有核实网关是否原样透传 `prompt is too long` 报错原文，也没有核实是否提供 `/v1/messages/count_tokens`。判断时以 400 和 message 内容为准，再用 count_tokens 或 `usage` 复核。

## 怎么确认已经修好

- 同样的请求用 count_tokens 再数一次，`input_tokens` 低于所选模型的上下文窗口，并给输出留出余量；
- 正式请求返回 200，`stop_reason` 是 `end_turn` 或 `tool_use`，不再是 `model_context_window_exceeded` 或 `max_tokens`；
- 多轮对话继续跑几轮，`usage` 里三项输入相加后没有逼近窗口；如果仍然逐轮逼近，就要上 compaction 或 context editing。

想用 Claude Opus 5.5、Sonnet 5.5 等 1M 上下文模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-prompt-is-too-long-400-fix&utm_content=footer)。

## 同专题文章

- [Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)
- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)
- [Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了](https://a37836323.github.io/openlux-api-guides/news/claude-prompt-cache-miss-diagnostics-fix/)
- [Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: "fast" 的请求会报错，留在 4.8 还是换 Opus 5.5](https://a37836323.github.io/openlux-api-guides/news/claude-opus-4-8-fast-mode-removal-opus-5-5-migration/)
- [Claude 的 usage_report / cost_report 被标为 legacy，如何迁移到 Analytics API 并正确传 beta header？](https://a37836323.github.io/openlux-api-guides/news/claude-usage-cost-analytics-api-migration/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

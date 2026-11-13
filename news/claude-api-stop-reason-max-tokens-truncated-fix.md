---
layout: default
title: "Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查"
description: "Claude API 回答被截断、stop_reason 为 max_tokens 时怎么办：区分 max_tokens 与上下文窗口满、思考占用 max_tokens、大 max_tokens 改流式、续写不能用预填充、tool_use 被截断要调大上限重发。"
permalink: /news/claude-api-stop-reason-max-tokens-truncated-fix/
date: 2026-11-12
---

> 更新日期：2026-11-12 · 一手来源：[Anthropic Claude 官方文档](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)

# Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查

**直接结论**：Claude Messages API 返回 HTTP 200，但回答在中间断掉、或者只有思考没有正文时，先看响应里的 `stop_reason`。如果是 `"max_tokens"`，说明输出撞到了你在请求里设置的 `max_tokens` 上限，不是报错，也不是网络问题。处理办法只有两类：**调大 `max_tokens`**，或者**让模型接着写**。开了思考（thinking）的模型还要多一步：思考也算在 `max_tokens` 里。

本文适用于直接调用 Claude Messages API（`/v1/messages`）或通过兼容这个协议的中转调用的情况，依据是 Anthropic 官方文档 [Handling stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)、[Troubleshooting thinking](https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting) 和 [Claude API errors](https://platform.claude.com/docs/en/api/errors)。

## 先分清：被截断不是报错，看 stop_reason

官方文档说明，`stop_reason` 是每个成功的 Messages API 响应都会带的字段，它告诉你模型为什么停下，和 4xx/5xx 错误是两回事。所以回答不完整时，HTTP 状态码通常是 200，日志里也看不到异常，要主动读这个字段。

| stop_reason | 什么时候出现 | 官方建议的处理 |
|---|---|---|
| `end_turn` | 模型自然写完 | 直接用结果 |
| `max_tokens` | 输出达到请求里的 `max_tokens` | 调大 `max_tokens`，或让模型续写 |
| `model_context_window_exceeded` | 输出把模型的上下文窗口填满了 | 当作被截断处理 |
| `tool_use` | 模型要调用工具 | 执行工具，回传结果 |
| `pause_turn` | 服务端工具循环达到迭代上限 | 把这次的 assistant 内容原样发回去继续 |
| `refusal` | 模型拒绝回答 | 看 `stop_details`，换模型重试 |

如果你用的是流式（stream），注意 `stop_reason` 在开头的 `message_start` 事件里是 `null`，**只在 `message_delta` 事件里给出**。只看第一个事件就判断“没有停止原因”，是很常见的误读。

## 第一步：确认是 max_tokens，而不是上下文窗口满了

两种截断的修法不同：

- `max_tokens`：是你自己设的输出上限太小。调大它通常就能解决。
- `model_context_window_exceeded`：输入加输出已经填满模型的上下文窗口，再调大 `max_tokens` 也没用，要缩短输入（裁剪历史、减少附件）。官方说明，Sonnet 4.5 及更新的模型直接返回这个值；更早的模型需要加 `model-context-window-exceeded-2025-08-26` beta 请求头才会返回。

官方给出的判断写法很简单（Python）：

```python
if response.stop_reason in ["max_tokens", "model_context_window_exceeded"]:
    # 回答不完整，给用户加提示或继续生成
    ...
```

**建议**：不管哪种截断，都不要把半截回答当成完整结果直接交给下游；至少在末尾标注“回答因长度限制被截断”，这也是官方文档推荐的做法。

## 第二步：开了思考的模型，思考也在吃 max_tokens

官方排错页专门写了这个症状：响应以 `stop_reason: "max_tokens"` 结束，**正文被截断甚至完全没有正文**。原因是思考产生的 token 计入 `max_tokens`，一段很长的思考可能在正文写完之前就把额度用光了。

很多较新的 Claude 模型默认开启思考，部分模型（官方表格里标为 Always on 的，如 Claude Opus 5.5）思考关不掉。因此从旧模型换到新模型后，原来够用的 `max_tokens` 可能突然不够了。官方给的两个修法：

1. **调大 `max_tokens`**，给思考和正文都留出空间；
2. **调低 `effort`**（`output_config.effort`），让模型少花 token 在思考上。

不要试图发 `thinking: {"type": "disabled"}` 来省 token：在思考常开的模型上，这会直接返回 400 `invalid_request_error`。

## 第三步：调大 max_tokens 时，大值要配合流式

`max_tokens` 设得很大但不用流式，可能遇到另一个问题。官方错误页的 Long requests 一节说明：

- 长时间请求（尤其超过 10 分钟的）建议用流式 Messages API 或 Message Batches API；
- 不要在非流式请求里设很大的 `max_tokens`，有些网络会断开空闲连接，导致请求失败或超时却拿不到响应；
- 官方 SDK 会检查非流式请求是否预计超过 10 分钟超时。

所以把 `max_tokens` 调大后，如果 SDK 报错要求改用流式，或请求长时间无响应后超时，就改成流式调用。官方 SDK 可以替你收完整个流再返回完整消息（Python）：

```python
with client.messages.stream(model=..., max_tokens=..., messages=messages) as stream:
    message = stream.get_final_message()
print(message.stop_reason)
```

## 第四步：不想调大上限，就让模型续写

如果输出确实很长、一次写不完，官方示例的做法是：把已经拿到的正文作为 assistant 消息放回对话，再追加一条 user 消息让它接着写，循环几次直到 `stop_reason` 不再是 `max_tokens`：

```python
messages = [
    {"role": "user", "content": prompt},
    {"role": "assistant", "content": full_response},
    {"role": "user", "content": "Please continue from where you left off."},
]
```

注意最后一条必须是 user 消息。官方错误页写明，Claude 4.6 及之后的模型**不支持 assistant 预填充**，对话以 assistant 消息结尾会返回 400：`This model does not support assistant message prefill. The conversation must end with a user message.` 旧教程里“把半截回答放在最后一条 assistant 消息里让模型接着写”的做法，在新模型上不能用。

官方示例最多续写 3 次（`max_attempts=3`），每次把新拿到的正文拼到 `full_response` 后面。自己实现时也要设上限，避免一直续写下去；拼接后检查接缝处是否重复或缺字。

## 第五步：工具调用被截断，只能调大 max_tokens 重发

如果被截断的响应里，最后一个内容块是不完整的 `tool_use`（工具参数 JSON 写了一半），官方说明这种情况**要用更大的 `max_tokens` 重新发送请求**，才能拿到完整的工具调用。不要尝试解析或补全半截参数，也不要把这个不完整的 `tool_use` 当作正常调用去执行。

判断方法：`stop_reason == "max_tokens"` 且 `response.content[-1].type == "tool_use"`。

## 验证方法：怎样算修好了

1. 用同一个输入重发请求，打印 `stop_reason` 和 `usage.output_tokens`；
2. `stop_reason` 变成 `end_turn`（或工具场景下的 `tool_use`）即说明不再被截断；
3. 如果仍是 `max_tokens`，且 `usage.output_tokens` 正好等于你设的上限，说明上限还是不够，继续调大或降低 `effort`；
4. 流式调用时，在 `message_delta` 事件里取 `stop_reason`，不要从 `message_start` 取。

通过中转调用 Anthropic 协议时，Base URL 填到域名即可（例如 `https://api.openlux.ai`，不带 `/v1`，客户端会自己拼 `/v1/messages`）。排查时先打印一次原始响应，确认 `stop_reason` 的实际值，再按上面的分支处理。

## 常见误区速查

| 现象 | 实际原因 | 正确做法 |
|---|---|---|
| HTTP 200 但回答断在一半 | `stop_reason` 为 `max_tokens` | 调大 `max_tokens` 或续写 |
| 只有思考块，没有正文 | 思考把 `max_tokens` 用光 | 调大 `max_tokens` 或调低 `effort` |
| 续写请求返回 400 prefill | 新模型不支持 assistant 预填充 | 最后追加一条 user 消息 |
| 调大上限后请求超时 | 非流式长请求被断开 | 改用流式或 Batches |
| 工具参数是半截 JSON | `tool_use` 被截断 | 调大 `max_tokens` 重发 |
| 流式里读到 `stop_reason: null` | 读的是 `message_start` | 从 `message_delta` 读 |

需要一个兼容 Anthropic Messages 协议的接口来测试上面的写法，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-stop-reason-max-tokens-truncated-fix&utm_content=footer)

## 同专题文章

- [Claude API 报 400「thinking blocks cannot be modified」或「Invalid signature in thinking block」怎么办：原样回传思考块、redacted_thinking 与改了历史逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-thinking-blocks-cannot-be-modified-fix/)
- [Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」怎么办：漏回结果、中间插了消息、文本放在结果前逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-tool-use-without-tool-result-fix/)
- [Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-404-not-found-error-fix/)
- [Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)
- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁](https://a37836323.github.io/openlux-api-guides/news/claude-api-prompt-is-too-long-400-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

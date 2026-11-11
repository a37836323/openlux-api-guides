---
layout: default
title: "Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」怎么办：漏回结果、中间插了消息、文本放在结果前逐项排查"
description: "Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」时，按官方格式要求逐项检查：每个 tool_use 是否都回了 tool_result、调用和结果之间是否插了消息、tool_result 是否排在文字前面、tool_use_id 是否对应，以及服务端工具混用、max_tokens 截断和裁剪历史的处理。"
permalink: /news/claude-api-tool-use-without-tool-result-fix/
date: 2026-11-11
---

> 更新日期：2026-11-11 · 一手来源：[Anthropic 官方文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)

# Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」怎么办：漏回结果、中间插了消息、文本放在结果前逐项排查

这条报错的意思是：上一条 assistant 消息里有 `tool_use` 块，但紧接着的那条 user 消息里没有找到与之对应的 `tool_result` 块。Anthropic 官方 [Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls) 文档在「格式要求」里点名了这条报错，并说遇到它就检查工具结果的格式。它属于 400 `invalid_request_error`，也就是请求体本身有问题，原样重试不会好，要改的是你发出去的 `messages` 历史。

本文适用于用官方 SDK、curl 或自己写的 Agent 循环调用 Claude Messages API（`/v1/messages`）并使用客户端工具（client tools）的情况。对照官方文档的格式要求，要逐项检查四处：是否漏回了某个工具的结果、工具调用和结果之间是否插了别的消息、`tool_result` 前面是否放了文本、`tool_use_id` 是否和调用的 `id` 一致。

## 先看清楚报错和你发出去的历史

官方 [Errors 文档](https://platform.claude.com/docs/en/api/errors) 说明，错误一律以 JSON 返回，顶层 `error` 里有 `type` 和 `message`，响应里还带 `request_id`。这条报错的 `type` 是 `invalid_request_error`，HTTP 状态码是 400。用官方 SDK 时会抛出对应的异常类型，而不是返回原始 JSON。

动手前先做一件事：把这次请求实际发出去的 `messages` 打印出来，只看最后两三条。这条报错通常能在「最后一条带 `tool_use` 的 assistant 消息」和「它后面那条 user 消息」之间找到原因。同时记下 `request_id`，方便之后对照。

## 按这张表对号入座

| 你在历史里看到的情况 | 官方说法 | 怎么改 |
|---|---|---|
| assistant 调了 2 个工具，user 只回了 1 个 `tool_result` | 是，官方：漏掉 `tool_result` 会报这条错 | 每个 `tool_use` 都回一个结果；没执行的也回，并设 `is_error: true` |
| assistant 的工具调用后面，先插了一条别的消息再回结果 | 是，官方：两者之间不能有任何消息 | 结果必须放在紧接着的下一条 user 消息里 |
| 同一条 user 消息里，先放 text，再放 `tool_result` | 是，官方示例标明这样会返回 400 | `tool_result` 放在 content 数组最前面，文字放在所有结果后面 |
| `tool_result` 的 `tool_use_id` 和 `tool_use` 的 `id` 不一致 | 官方要求用 `tool_use_id` 把结果和调用一一对应 | 原样使用 `tool_use` 块里的 `id` |
| 每个结果单独发一条 user 消息 | 官方未列为报错，但会让 Claude 减少并行调用 | 所有结果放进同一条 user 消息 |

## 第一步：每个 tool_use 都要有一个 tool_result

官方要求：收到 `stop_reason` 为 `tool_use` 的响应后，从每个 `tool_use` 块里取出 `name`、`id`、`input`，执行工具，然后发一条 `role` 为 `user` 的新消息，里面放 `tool_result` 块，`tool_use_id` 填对应 `tool_use` 的 `id`。

Claude 默认可能在一次响应里调用多个工具（[Parallel tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use)）。如果你的循环只处理了第一个 `tool_use` 块，后面的结果就漏了。官方的说法是：不管你并发还是顺序执行，都要为每个 `tool_use` 块回一个 `tool_result`，并且全部放在下一条 user 消息里。

如果你决定不执行某个调用（比如顺序执行时前一个调用失败了），官方建议仍然为它回一个结果，标上 `is_error: true` 并简短说明：

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_02",
  "is_error": true,
  "content": "Not executed: the preceding write_file call failed."
}
```

工具执行本身抛错（网络错误等）时也一样：把错误信息放进 `content`，加上 `is_error: true` 回给 Claude，而不是跳过不回。官方说明 `content` 是可选的，空结果可以只带 `tool_use_id`。

## 第二步：工具调用和结果之间不能插消息

官方格式要求的第一条：工具结果块必须紧跟在对应的工具调用之后，assistant 的工具调用消息和 user 的工具结果消息之间**不能有任何消息**。

下面这些写法都会违反这条规则：

- 工具还在执行时，用户又发了一句话，程序把这句话先追加进历史，再追加工具结果。
- 程序把「正在调用工具…」之类的提示当成一条消息写进了历史。
- 执行工具前先把 Claude 的回复拆开存了两次。

改法是把顺序固定下来：assistant 消息（原样保留 Claude 返回的 `content`，包括 `tool_use` 块）之后，下一条一定是装着全部 `tool_result` 的 user 消息。用户中途追加的话，等这一轮结束后再作为新的 user 消息发送；官方在 [Stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons) 里也是这样建议的。

## 第三步：tool_result 放在 content 最前面，文字放后面

官方格式要求的第二条：在装工具结果的 user 消息里，`tool_result` 块必须排在 content 数组**最前面**，任何文字都要放在所有工具结果之后。官方给的错误示例：

```json
{
  "role": "user",
  "content": [
    { "type": "text", "text": "Here are the results:" },
    { "type": "tool_result", "tool_use_id": "toolu_01" }
  ]
}
```

把两项顺序对调（先 `tool_result`，后 text）就是只调用客户端工具时的正确写法。用 LangChain 等框架拼消息时也要留意：LangChain 的 GitHub 上已有用户报告（[langchain-ai/langchain#41783](https://github.com/langchain-ai/langchain/issues/41783)）混合用户消息和工具消息时文字可能被放到 `tool_result` 前面，这时要看框架最终发出去的请求体。

另外，官方在 Stop reasons 文档里提醒：不要在每次工具结果后面都附一段文字。历史里每次工具结果后都跟着用户文字，会让 Claude 学到这个模式而提前结束回合。

## 第四步：同时用了服务端工具时，只回 tool_result

如果你同时启用了 web search 这类服务端工具，同一次响应里可能既有你的客户端 `tool_use`，又有还没有结果的 `server_tool_use`。官方规则是：回复的 user 消息里**只能**放客户端工具的 `tool_result`，并且要保留相同的 `tools` 数组。

这种情况下报错会不一样，按原文区分：

- 在 `tool_result` 后面加了文字：直接调用的服务端工具会让请求返回 400，报错里点名那个服务端工具，例如 `` `web_search` tool use with id ... was found without a corresponding `web_search_tool_result` block ``。
- 续写请求里去掉了正在等待的服务端工具：报 400，报错结尾是 ``but no `web_search` tool was provided``。
- 漏回 `tool_result` 或把它放在别的内容后面：仍然是本文这条 `tool_use ids were found without tool_result blocks immediately after`。

另外，`stop_reason` 为 `pause_turn` 时不需要回 `tool_result`：官方说明这时要把这次响应原样作为 assistant 消息发回去让 Claude 继续，客户端工具等你执行时一定是 `tool_use` 而不是 `pause_turn`。

## 其他容易漏掉的情况

- **回复被 `max_tokens` 截断**：官方说明，如果 `stop_reason` 是 `max_tokens`，且最后一个块是不完整的 `tool_use`，应该调高 `max_tokens` 重新发请求拿到完整的调用，而不是去执行这个半截调用。
- **裁剪历史**：按条数裁剪上下文时，把「带 `tool_use` 的 assistant 消息」和「紧随其后的 `tool_result` 消息」当成一组，要么都保留，要么都删，避免留下没有结果的调用。
- **带思考块回传**：使用工具时，官方要求把 assistant 回合里的 `thinking` 和 `redacted_thinking` 块原样传回；按类型过滤内容块时别把它们和 `tool_use` 一起丢掉，否则会触发另一种 400。
- **想彻底不手写这些格式**：官方 SDK 提供 Tool Runner，会自动处理工具执行、结果格式和对话管理。

## 修好后怎么验证

1. 让 Claude 在一轮里调用两个工具（例如问一个需要查两处信息的问题），确认响应里有 2 个 `tool_use` 块。
2. 打印你准备发出的 `messages`：最后一条是 user 消息，content 里依次是 2 个 `tool_result`，`tool_use_id` 与上一条 assistant 消息里的两个 `id` 一一对应，前面没有 text。
3. 发送后不再返回 400，`stop_reason` 变为 `end_turn` 或继续下一次 `tool_use`，说明格式正确。

如果你通过 Anthropic 兼容的中转地址调用，排查方法相同：问题出在你自己拼出的消息历史里，先在发请求前打印检查。OpenLux 的 Anthropic Messages 地址填 `https://api.openlux.ai`（不带 `/v1`，SDK 会自己拼 `/v1/messages`）。

## 参考资料

- Anthropic 官方文档：[Handle tool calls](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)（`tool_result` 字段、格式要求、本报错原文、`is_error`）
- Anthropic 官方文档：[Parallel tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use)（每个调用都回结果、放进同一条消息、未执行的调用怎么回）
- Anthropic 官方文档：[Handling stop reasons](https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons)（服务端工具混用、`max_tokens` 截断、`pause_turn`）
- Anthropic 官方文档：[Errors](https://platform.claude.com/docs/en/api/errors)（400 `invalid_request_error`、错误格式、`request_id`、思考块不能修改）

想用一个 Key 同时调用 Claude 和其他模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-tool-use-without-tool-result-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的方法检查工具调用历史。

## 同专题文章

- [Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-404-not-found-error-fix/)
- [Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)
- [Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-401-authentication-error-fix/)
- [Claude API 报 400「prompt is too long」怎么办：上下文窗口多大、怎么数 token、历史怎么裁](https://a37836323.github.io/openlux-api-guides/news/claude-api-prompt-is-too-long-400-fix/)
- [Claude API 报 529 overloaded_error 怎么办：和 429、500、504 怎么区分，重试与流式中途报错怎么处理](https://a37836323.github.io/openlux-api-guides/news/claude-api-529-overloaded-error-retry-fix/)
- [Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了](https://a37836323.github.io/openlux-api-guides/news/claude-prompt-cache-miss-diagnostics-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

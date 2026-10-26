---
layout: default
title: "Claude API 带 web_fetch 工具报 400 怎么办：组织未开启、域名名单冲突与续轮缺少结果块"
description: "Claude Messages API 带 web fetch 工具返回 400 的排查：组织在 Console Capabilities 页关闭 web fetch、allowed_domains/blocked_domains 写法不合法或与组织名单冲突、混合工具续轮缺少 web_fetch 工具或 tool_result 后多加内容、新版本需 allowed_callers；并区分 200 响应里的 web_fetch_tool_result_error 错误码。"
permalink: /news/claude-api-web-fetch-400-error-fix/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[Anthropic 官方文档：Web fetch tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool)

# Claude API 带 web_fetch 工具报 400 怎么办：组织未开启、域名名单冲突与续轮缺少结果块

在 Messages API 请求里加了 web fetch 工具后直接返回 400 `invalid_request_error`，按官方文档，常见原因分三类：一是组织管理员在 Claude Console 的 Capabilities 页关掉了 web fetch；二是工具上的 `allowed_domains` / `blocked_domains` 写法不合法，或者和组织级域名名单冲突；三是混合使用服务端工具和自己的工具时，续轮请求的结构不对（少了 `web_fetch` 工具定义，或在 `tool_result` 后面多加了内容）。本文依据 Anthropic 官方的 [Web fetch tool 文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool)、[Server tools 文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools) 和 [2026 年 10 月 20 日的发布说明](https://platform.claude.com/docs/en/release-notes/overview) 整理，适用于直接调用 Claude API（Messages API）的开发者。

如果你用的是 Claude Managed Agents，遇到的是 `url_not_allowed`、`url_not_in_prior_context` 这类工具结果错误或创建 session 时的 400，请看本站另一篇：[Claude Managed Agents 报 url_not_allowed 怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-managed-agents-web-fetch-url-not-allowed-fix/)。

## 先分清：是请求 400，还是工具结果里的错误

web fetch 是服务端工具，由 API 在请求过程中抓取网页，你不需要自己返回 `tool_result`。官方文档说明，抓取本身失败时（比如网页打不开、域名被拦），API 仍然返回 200，错误写在响应体的 `web_fetch_tool_result_error` 里，Claude 收到错误后会继续这一轮回答。所以排查第一步是看 HTTP 状态码：

| 你看到的现象 | 属于哪一层 | 去看本文哪一节 |
|---|---|---|
| HTTP 400，`invalid_request_error`，提示 web fetch 未启用 | 组织设置 | 「原因一」 |
| HTTP 400，错误信息与域名条目有关 | 工具参数或组织级域名名单 | 「原因二」 |
| HTTP 400，信息里有 `but no web_fetch tool was provided` 或 `found without a corresponding web_fetch_tool_result block` | 续轮请求结构 | 「原因三」 |
| 校验错误，提示设置 `allowed_callers` | 工具版本与模型不匹配 | 「原因四」 |
| HTTP 200，但内容里有 `web_fetch_tool_result_error` 和 `error_code` | 抓取失败，不是请求错误 | 「200 里的 error_code」 |

## 原因一：组织在 Console 里关掉了 web fetch

官方 2026 年 10 月 20 日的发布说明写明：组织管理员现在可以在 Claude Console 的 [Capabilities 页](https://platform.claude.com/settings/capabilities) 关闭整个组织的 web fetch。关闭后，带 web fetch 工具的 Messages API 请求会返回 400 `invalid_request_error`，错误信息说明 web fetch 未启用。

处理步骤：

1. 确认你用的 API Key 属于哪个组织，再请这个组织的管理员打开 Capabilities 页查看 web fetch 是否开启。
2. 如果组织出于安全考虑决定不开，就从请求的 `tools` 里去掉 web fetch；需要网页内容时，可以考虑由你的程序自行获取，再作为普通输入发给 Claude。
3. 开启后，同一页还可以设置 web fetch 的允许或禁止域名，这会影响下一节的检查。

成功标准：同一个请求去掉 web fetch 工具能正常返回，加回工具后不再报「未启用」。

## 原因二：域名名单写法不对或与组织名单冲突

工具对象上可以写 `allowed_domains` 或 `blocked_domains`。按 Server tools 文档的「Domain filtering」一节，下面这些写法会出问题：

| 写法 | 官方规则 | 改法 |
|---|---|---|
| `"https://example.com"` | 域名不应带 http/https 协议 | 写成 `example.com` |
| `"*.example.com"`、`"ex*.com"` | 通配符不能出现在域名部分，只能出现在域名后的路径里；格式不合法的域名在请求时就会被 400 拒绝 | 写 `example.com`，子域名会自动包含 |
| 同时写了 `allowed_domains` 和 `blocked_domains` | 同一个请求里只能二选一 | 保留其中一个 |
| 请求级 `allowed_domains` 里有组织允许名单之外的域名 | 请求级允许名单必须是组织级允许名单的子集，否则返回校验错误 | 只保留组织允许的域名，或请管理员把域名加进组织名单 |
| 请求级 `allowed_domains` 里有组织禁止的域名 | 返回 400，错误信息会点名冲突的条目 | 按错误信息删掉这些条目 |

另外两条规则不会导致 400，但容易让人以为配置没生效：

- `example.com` 自动覆盖 `docs.example.com`；反过来写 `docs.example.com` 则只允许这个子域名。
- web fetch 只按域名匹配，带路径的条目（如 `example.com/blog`）永远匹配不上 web fetch 的 URL。路径匹配只对 web search 有效。

官方还提醒，域名里的 Unicode 字符可能被用来做同形字绕过，名单里应只用 ASCII 域名。

## 原因三：混合工具续轮时请求结构不对

当 Claude 在同一组并行调用里既调用 web fetch、又调用你自己定义的工具时，Server tools 文档说明，API 会先不执行 web fetch，直接返回 `stop_reason: "tool_use"`，响应里有 `server_tool_use` 块但没有对应的结果块。你需要执行自己的工具，再发一条只包含 `tool_result` 块的用户消息。这里有两种官方列出的 400：

1. **续轮请求里没有 web fetch 工具定义**：错误信息以 ``but no `web_fetch` tool was provided`` 结尾。续轮必须带上和上一轮相同的 `tools` 数组。
2. **在 `tool_result` 后面又加了文本等内容**：API 会认为助手这一轮已结束，留下未完成的 web fetch 调用，返回 400，信息形如 ``web_fetch tool use with id ... was found without a corresponding web_fetch_tool_result block``。

正确的续轮消息只放 `tool_result`：

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01PjgRJLbXrXEMZwDNYLnBqk",
      "content": "命令输出"
    }
  ]
}
```

要补充新的问题，等这一轮完成后再另发一条用户消息。官方还说明，如果用户消息把内容放在结果前面、只回了部分 `tool_use` ID、或者一个 `tool_result` 都没有，会更早报客户端工具的错误（`tool_use ids were found without tool_result blocks immediately after`）。

另一种暂停是 `stop_reason: "pause_turn"`：服务端循环运行较久时会暂停，这时要把助手内容原样放回 `messages` 再发一次，同样要带上相同的工具，否则文档说明 API 会返回校验错误。

## 原因四：工具版本、模型和附带参数不匹配

web fetch 目前有 `web_fetch_20250910`（基础抓取）、`web_fetch_20260209`、`web_fetch_20260309`、`web_fetch_20260318` 几个版本，较新的版本支持动态过滤，并依赖代码执行。按官方文档，需要注意：

- `_20260209` 及之后的版本默认只允许从代码执行中调用；在不支持程序化工具调用的模型上，必须设置 `"allowed_callers": ["direct"]`，否则 API 返回校验错误并提示设置它。
- 用这些新版本时不需要自己加 `code_execution` 工具；如果加了，要用 `code_execution_20260120` 或更新版本，旧版本会被拒绝。
- `use_cache` 需要 `web_fetch_20260309` 或更新版本，`response_inclusion` 需要 `web_fetch_20260318` 或更新版本。
- `url_sources` 过滤器里用 `tool_reference` 列出的工具名，必须在请求的 `tools` 数组里存在，否则请求失败。

不确定时，可以先退回最简单的写法验证：

```json
{
  "type": "web_fetch_20250910",
  "name": "web_fetch",
  "max_uses": 5
}
```

## 200 里的 error_code：抓取失败怎么看

如果状态码是 200，但响应里有 `web_fetch_tool_result_error`，说明请求本身合法、是抓取环节失败。官方列出的 `error_code` 如下：

| error_code | 官方含义 |
|---|---|
| `invalid_tool_input` | 工具输入无效，比如 URL 格式错误或不是 HTTP(S) |
| `url_too_long` | URL 超过 250 个字符 |
| `url_not_allowed` | 被域名过滤规则（含组织设置）或 Anthropic 侧限制拦截，例如内网地址、`robots.txt`、看起来带有凭据的 URL |
| `url_not_in_prior_context` | URL 没有在对话里出现过，或只出现在被 `url_sources` 排除的来源里 |
| `url_not_accessible` | 抓取失败（目标网站返回 HTTP 错误） |
| `too_many_requests` | 超过频率限制 |
| `unsupported_content_type` | 内容类型不支持，只支持文本、HTML 和 PDF |
| `max_uses_exceeded` | 超过 `max_uses` 次数，失败的抓取也计入 |
| `unavailable` | 内部错误 |

其中 `url_not_in_prior_context` 要特别注意：Claude 只能抓取用户消息、你的工具结果、以往 web search / web fetch 结果里出现过的 URL，只写在 system 提示词里的 URL 不算。要让它抓 system 里的地址，就把 URL 也放进用户消息。另外，web fetch 不支持依赖 JavaScript 渲染的网页。

## 一份排查清单

1. 记下 HTTP 状态码和完整错误信息。400 走上面四类原因；200 看 `error_code`。
2. 去掉 web fetch 工具重发同一请求，能成功说明问题在工具或组织设置。
3. 请管理员确认 Capabilities 页 web fetch 已开启，并核对组织级域名名单。
4. 检查 `allowed_domains` / `blocked_domains`：不带协议、域名不带通配符、二者不同时出现、请求级允许名单在组织允许名单之内。
5. 换回 `web_fetch_20250910` 的最简写法，排除版本和 `allowed_callers` 问题。
6. 有自定义工具时，检查续轮请求：`tools` 与上一轮一致，用户消息里只有 `tool_result`。

成功标准：请求返回 200，响应里出现 `web_fetch_tool_result`，`usage.server_tool_use.web_fetch_requests` 有计数。官方文档说明 web fetch 本身不额外收费，只按抓取内容进入上下文后的 token 计费，可以用 `max_content_tokens` 控制单次抓取的内容长度。

## 参考资料

- 官方文档：[Web fetch tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool)
- 官方文档：[Server tools（Domain filtering、pause_turn 与混合工具续轮）](https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools)
- 官方发布说明：[Claude Platform release notes](https://platform.claude.com/docs/en/release-notes/overview)（2026 年 10 月 20 日条目）

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-web-fetch-400-error-fix&utm_content=footer)。

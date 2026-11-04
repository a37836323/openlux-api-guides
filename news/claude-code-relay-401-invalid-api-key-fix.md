---
layout: default
title: "Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查"
description: "Claude Code 用 ANTHROPIC_BASE_URL 走中转时报 401、Invalid API key · Fix external API key、Invalid auth token 或一直提示 Not logged in · Please run /login 的排查：先用 curl 测令牌，再按官方说明选 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY、查凭据优先级与残留变量、用 /status 确认，VS Code 扩展与 apiKeyHelper 的特殊情况。"
permalink: /news/claude-code-relay-401-invalid-api-key-fix/
date: 2026-11-05
---

> 更新日期：2026-11-05 · 一手来源：[Claude Code 官方文档](https://code.claude.com/docs/en/errors.md)

# Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查

Claude Code 用 `ANTHROPIC_BASE_URL` 指向中转（LLM 网关）后，报 `401`、`Invalid API key · Fix external API key`，或者明明配了 Key 还提示 `Not logged in · Please run /login`，绝大多数是这几种情况：令牌本身不对、放错了环境变量、被另一份凭据抢先使用、变量没传进 Claude Code 进程、令牌里混进了看不见的字符。本文按 Claude Code 官方的 [Error reference](https://code.claude.com/docs/en/errors.md#authentication-errors) 和 [LLM 网关接入文档](https://code.claude.com/docs/en/llm-gateway-connect.md) 整理，适用于 Claude Code 命令行和 VS Code 扩展。

有一点要先记住：官方明确说，`ANTHROPIC_BASE_URL` 指向网关时，`401` 后面的文字是**网关自己的报错**，不是 Anthropic 的，这时运行 `/login` 不会有任何改变，要修的是网关要求的那份凭据。

## 先按报错原文对号入座

| 你看到的报错 | 官方说明的原因 | 先做什么 |
|---|---|---|
| `Please run /login · API Error: 401 ...`，后面是网关的话（OpenLux 返回 `Invalid token (request id: ...)`） | 网关拒绝了这份凭据 | 用下一节的 curl 测令牌；不要指望 `/login` |
| `Invalid API key · Fix external API key` | `ANTHROPIC_API_KEY` 或 `apiKeyHelper` 给的 Key 被拒，或 Claude Code 发送前就拦下了 | 查拼写、查是否被旧 `.env` 覆盖 |
| `Invalid auth token · Fix external auth token · ... contains a line break at character 41` | `ANTHROPIC_AUTH_TOKEN` 里有换行、零宽空格、弯引号等字符，请求根本没发出去 | 在报告的位置附近手动重新输入 |
| `Not logged in · Please run /login` | 这个会话里没有任何可用凭据 | 确认变量在启动 `claude` 的那个终端里已 export |
| curl 能通，Claude Code 仍要求登录 | 项目 `.claude/settings.json` 的 `env` 要等首次向导和信任提示之后才生效 | 把 `ANTHROPIC_AUTH_TOKEN` 放到 shell 或 `~/.claude/settings.json` |
| 设了 `ANTHROPIC_API_KEY` 却被无视，也不再询问 | 交互模式下这个 Key 要批准一次，之前点过拒绝就会被一直忽略 | `/config` 里打开 `Use custom API key` |
| 启动时警告两个凭据来源，结尾是 `auth may not work as expected`（旧版为 `Auth conflict`） | 网关凭据和已保存的登录同时存在 | 用网关就 `/logout`，不用就撤掉变量 |
| `Your apiKeyHelper script is failing` | 脚本没输出可用的 Key，请求带的是占位凭据，于是 401 | 直接运行脚本看哪里失败 |

## 第一步：在同一个终端用 curl 测令牌

官方建议在打开 Claude Code 之前，先直接对网关发一个 1 token 的请求，这样出错就能确定是网关或令牌的问题，而不是 Claude Code 配置的问题。OpenLux 的 Anthropic 地址是 `https://api.openlux.ai`，**不带 `/v1`**（Claude Code 自己会拼 `/v1/messages`）；令牌在控制台「令牌」页创建：`https://www.openlux.ai/console/token`。

```bash
export ANTHROPIC_BASE_URL=https://api.openlux.ai
export ANTHROPIC_AUTH_TOKEN=sk-你的令牌
curl -sS -w '\n%{http_code}\n' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5-5", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

怎么看结果：

| 返回 | 说明 |
|---|---|
| 以 `{"id":"msg_` 开头、带 `"content"` | 地址和令牌都没问题，问题在 Claude Code 这一侧，看第二、三步 |
| 报模型不存在 | 官方说明这同样证明地址和令牌可用（网关先鉴权再检查模型），换成价格页上在售的模型名即可 |
| `401` + `Invalid token` | 令牌被拒：重新复制，或在控制台确认令牌没被删除、停用，必要时新建一个 |
| `404` + `Invalid URL (POST /v1/v1/messages)` | 不是鉴权问题，是 `ANTHROPIC_BASE_URL` 多写了 `/v1`，去掉即可 |

## 第二步：选对变量，确认没有别的凭据抢先

官方说明三种凭据走不同的请求头：`ANTHROPIC_AUTH_TOKEN` 放在 `Authorization: Bearer`，`ANTHROPIC_API_KEY` 放在 `x-api-key`，`apiKeyHelper` 两个头都带。网关不读的头里放了凭据，就会 `401`。OpenLux 的 `/v1/messages` 两种头都接受，所以两个变量都能用；官方的建议是拿不准时先用 `ANTHROPIC_AUTH_TOKEN`，因为它设好就立即生效，而 `ANTHROPIC_API_KEY` 在交互模式下要先批准一次。

同时存在多份凭据时，Claude Code 按这个顺序取用（摘自官方 Authentication precedence）：

1. `CLAUDE_CODE_USE_BEDROCK` / `CLAUDE_CODE_USE_VERTEX` / `CLAUDE_CODE_USE_FOUNDRY` 指定的云厂商凭据
2. `ANTHROPIC_AUTH_TOKEN`
3. `ANTHROPIC_API_KEY`
4. `apiKeyHelper` 脚本输出
5. `CLAUDE_CODE_OAUTH_TOKEN`
6. Anthropic profile 与联合身份凭据
7. `/login` 保存的订阅登录

所以常见的坑是：终端里残留一个旧的 `ANTHROPIC_API_KEY` 或 `CLAUDE_CODE_USE_*` 变量，排在你新配的令牌前面或把请求引向别处。官方给的检查方法是在同一个终端运行 `env | grep ANTHROPIC`（PowerShell 用 `Get-ChildItem Env:ANTHROPIC*`），并提醒 direnv、dotenv 插件和 IDE 终端可能会从项目的 `.env` 里悄悄加载旧 Key。另外，shell 里的 export 和 settings 文件的 `env` 设了同一个变量时，**以 settings 文件为准**。

## 第三步：确认变量真的进了 Claude Code

从刚才测过 curl 的同一个终端启动 `claude`，运行 `/status`，看 Status 页：

- `Anthropic base URL` 这一行显示 `https://api.openlux.ai`。没有这一行，说明变量没进会话。
- `Auth token` 或 `API key` 一行写的是你设的那个变量。如果显示的是 `Login method` 加 claude.ai 账号，说明用的还是订阅登录。

要长期生效，官方建议写进 `~/.claude/settings.json` 的 `env`（Windows 为 `%USERPROFILE%\.claude\settings.json`）：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openlux.ai",
    "ANTHROPIC_AUTH_TOKEN": "sk-你的令牌"
  }
}
```

不要写进项目的 `.claude/settings.json`：官方提醒这个文件会提交到仓库、被所有人看到；而且项目级 `env` 要在首次向导和信任提示之后才生效，这正是「curl 通了还让登录」的原因之一。

**VS Code 扩展**：官方说明要把变量写进 VS Code 用户设置的 `claudeCode.environmentVariables`。`~/.claude/settings.json` 里的值能传给扩展启动的进程，但扩展自己的登录检查读不到，所以只写那里仍可能弹登录。**桌面应用**不读 `ANTHROPIC_BASE_URL`，要在它的第三方推理配置里填地址。

## 第四步：剩下几种特殊情况

- **令牌里有看不见的字符**：报错会写出变量名和字符位置（如 `contains a line break at character 41`）。官方建议在该位置附近手动重新输入，不要再从同一个文档或聊天记录里复制。
- **用了 `apiKeyHelper`**：脚本必须只往 stdout 打印 Key 本身（一段可打印 ASCII，最长 16,384 个字符），并以退出码 0 结束；打印了登录横幅或日志行也算失败。它的优先级高于 `/login`，设置还在时运行 `/login` 没用。
- **`ANTHROPIC_API_KEY` 被无视**：只要该变量存在，`/config` 里就会出现 `Use custom API key` 开关，打开即可。非交互模式（`-p`）下只要有这个变量就会直接使用。
- **curl 能通，但 Claude Code 每个请求都 401**：官方提到这时要检查网关和它的上游是否接受 tool search 相关字段（`defer_loading`、`tool_reference` 与对应的 `anthropic-beta` 头），v2.1.304 起网关后默认开启。可以用 `ENABLE_TOOL_SEARCH=false claude` 启动对比；关掉后恢复正常，多半就是这个原因，需要网关侧放行这些字段。

## 改完怎么验证

1. 第一步的 curl 返回 `msg_` 开头的 JSON（或报模型不存在）。
2. 在同一终端启动 `claude`，`/status` 里能看到 `Anthropic base URL` 和对应的 `Auth token` / `API key` 行，启动时没有凭据冲突警告。
3. 随便发一句话，正常回复、没有 `401` 就算接通。

还没接过的可以先看本站的 [Claude Code 中转接入教程](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)，连不上或超时看 [Unable to connect to API 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/)。

## 开始使用

需要一个能直接填进 `ANTHROPIC_BASE_URL` 的 Claude 中转地址，可以[注册 OpenLux 获取 API 令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-401-invalid-api-key-fix&utm_content=footer)。

## 同专题文章

- [Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/)
- [Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-model-picker-missing-models-fix/)
- [Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/)
- [Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)

[查看「Claude Code 接入与报错」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-code/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查"
description: "Claude Code 接中转后报 400「Extra inputs are not permitted」：按报错点名的 context_management、output_config、thinking、system 角色或工具字段逐项处理，升级版本、设置 CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS，以及这个变量管不到的情况。"
permalink: /news/claude-code-relay-400-extra-inputs-not-permitted-fix/
date: 2026-11-02
---

> 更新日期：2026-11-02 · 一手来源：[Claude Code 官方文档](https://code.claude.com/docs/en/llm-gateway-protocol)

# Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查

先说结论：Claude Code 把 `ANTHROPIC_BASE_URL` 指向的中转当成 Anthropic 官方 API，会把发给官方的预发布（beta）请求头和对应的请求体字段一起发过去。中转或它背后的上游不认其中某个字段时，就会返回 400，最常见的报错是 `context_management: Extra inputs are not permitted`。处理方法要看报错里**点名的是哪个字段**：大部分情况先把 Claude Code 升级到最新版，再设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`；少数字段这个变量管不到，要单独处理。

本文的成因、变量名和版本号都来自 Claude Code 官方的 [网关兼容指南（Gateway compatibility guide）](https://code.claude.com/docs/en/llm-gateway-protocol) 和 [Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect) 里的排错表。适用于用 `ANTHROPIC_BASE_URL` 接中转的 Claude Code 命令行和 VS Code 扩展。如果你还没接通（报 401、404 或一直要求登录），先看 [Claude Code 怎么接入 Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)。

## 为什么直连官方正常，走中转才报 400

官方文档对这件事的解释有三点：

- **字段成对发送**：带请求体字段的预发布能力，会和一个 `anthropic-beta` 请求头成对发送。中转去掉了请求头却保留了请求体，或者把 Anthropic 格式的请求转给字段格式不同的上游，就会产生 400。请求头和请求体字段都没有发出时，这项功能会静默关闭，不报错。
- **转发到云厂商时更常见**：官方特别指出，中转对外是 Anthropic 格式、背后转发到 Amazon Bedrock 时，`context_management` 报错很常见。
- **不认识的模型名按新模型处理**：模型名 Claude Code 不认识时（比如中转自定义的别名），它会按当前模型发送全部字段，包括自适应推理（adaptive reasoning）、effort 和上下文管理。

另外，Claude Code 的很多自动重试是靠识别上游报错原文触发的。中转如果把上游报错包装成自己的格式，即使状态码还是 400，自动重试也可能不生效。

## 先看报错点名的是哪个字段

下表里提到的「自动重试」，前提都是中转把上游的 400 报错原样返回给 Claude Code。

| 报错里出现的内容 | 对应的能力 | 怎么处理 |
|---|---|---|
| `context_management`、`Extra inputs are not permitted` | 上下文管理 | v2.1.304 及以后会自动去掉这对字段重试；旧版本设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` |
| `output_config`，常伴随 `Extra inputs are not permitted` | 结构化输出、任务预算、effort | 上面这个变量会去掉结构化输出的 format 和任务预算，但**不去掉 effort**；只想去掉 format 可设 `CLAUDE_CODE_DISABLE_STRUCTURED_OUTPUTS=1`（需 v2.1.288 及以后） |
| `output_config.effort` 被拒、提示模型不支持 effort，或 `Unexpected value(s)` 里列出 `effort-2025-11-24` | effort | Claude Code 会自动重试，并在本次运行内不再给这个模型发 effort；第三种报错的自动处理需要 v2.1.310 及以后。如果你在 `ANTHROPIC_BETAS` 里手动写了这个值，要删掉 |
| `thinking`、`adaptive`，如 `Input tag 'adaptive' found` | 自适应推理 | 需要中转升级上游；Opus 4.6、Sonnet 4.6 可设 `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1` |
| `Unexpected role "system"` | 对话中途的 system 消息 | Claude Code 会自动去掉中途的 system 消息重试，把其中的文字改放进 user 消息 |
| `messages.N: system content must contain at least one block` | 按轮设置 effort（Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1） | 设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` |
| 点名 `strict`、`defer_loading` 等工具字段 | 预发布工具字段、MCP 工具搜索 | 设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`；只想关工具搜索可设 `ENABLE_TOOL_SEARCH=false` |
| `Input tag 'advisor_20260301'` | advisor 工具 | 升级到 v2.1.276 及以后；停在 v2.1.275 时设 `CLAUDE_CODE_DISABLE_ADVISOR_TOOL=1` |
| 每次请求都 400、说工具 input schema 或 `pattern` 不合法，版本在 v2.1.265～v2.1.267 | Artifact 工具的正则 | 升级到 v2.1.268 及以后 |

## 第一步：查版本并升级

表里好几项在新版本里已经能自动重试，所以先确认版本：

```bash
claude --version
claude update
```

用官方原生安装方式装的会在后台自动更新，`claude update` 可以立即更新。用 Homebrew 安装的执行 `brew upgrade claude-code`（安装的是 latest 渠道就执行 `brew upgrade claude-code@latest`），用 npm 安装的执行 `npm install -g @anthropic-ai/claude-code@latest`。官方提醒，Homebrew 的 `claude-code` 跟随 stable 渠道，通常比最新版晚一周左右。升级后重新打开 Claude Code，再试一次刚才报错的操作。

## 第二步：设置 CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS

升级后还报错，或者报错点名的是 `context_management`、`strict`、`defer_loading`、`output_config.format` 这类字段，就设置这个变量。和接中转时一样，可以先在终端里导出试一下：

```bash
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
claude
```

确认有效后，写进 `~/.claude/settings.json` 的 `env` 块，和中转地址、令牌放在一起长期生效（令牌换成你自己的，不要写进项目的 `.claude/settings.json`，那个文件会提交到仓库）：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openlux.ai",
    "ANTHROPIC_AUTH_TOKEN": "你的OpenLux令牌",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1"
  }
}
```

按官方说明，这个变量会停止发送这些内容：上下文管理和 `context_management` 字段；`strict`、`defer_loading` 等预发布工具字段（`name`、`description`、`input_schema`、`cache_control` 这些标准字段照常发送）；`output_config.format`（需 v2.1.287 及以后）；`output_config.task_budget`；MCP 工具搜索，也就是所有 MCP 工具改为一开始就全部加载。

它**不会**去掉的有：扩展上下文、交错思考（interleaved thinking）和 effort 的 beta 值；顶层的 `output_config.effort`；自适应推理的 `thinking` 字段；对话中途的 `role: "system"` 消息；以及你自己通过 `ANTHROPIC_BETAS` 或 `CLAUDE_CODE_EXTRA_BODY` 加进去的请求头值和字段。所以设了变量还报 `thinking`、`adaptive` 或 effort 相关的 400，要回到上面的表格单独处理。

## 第三步：处理这个变量管不到的情况

- **thinking 或 adaptive 报错**：说明上游的模型版本不接受自适应推理。Claude Code 会对 Opus 4.6、Sonnet 4.6、Haiku 5.5、Fable 5 及之后的模型发送 `thinking: {"type": "adaptive"}`。根本办法是中转升级上游；用 Opus 4.6、Sonnet 4.6 时也可以设置 `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1`。官方特别说明，`ANTHROPIC_DEFAULT_*_MODEL_SUPPORTED_CAPABILITIES` 这类能力声明变量只在 Bedrock、Vertex 等云厂商配置下生效，用 `ANTHROPIC_BASE_URL` 接中转时设了也没用。
- **自己加过 beta 值**：检查 shell 和 `settings.json` 里有没有 `ANTHROPIC_BETAS`、`CLAUDE_CODE_EXTRA_BODY`。这两个变量里的内容 Claude Code 会原样发送，不受上面开关控制。
- **换成云厂商格式**：官方排错表还提到，有些 beta 不受这个开关控制，这时可以设置对应的 `CLAUDE_CODE_USE_*` 变量，让 Claude Code 只发送该云厂商接受的内容。这只适用于中转方明确提供 Bedrock、Agent Platform 等云厂商格式入口的情况。OpenLux 提供的是 Anthropic Messages 入口（`https://api.openlux.ai`），不需要走这条路。

## 和这类 400 容易混淆的报错

| 现象 | 原因 | 处理 |
|---|---|---|
| 400，用中转自己的话说上下文超限，如 `ContextWindowExceededError` | 中转限制的上下文比模型原生窗口小，并改写了报错，Claude Code 认不出来，不会自动压缩 | 先用 `/compact` 恢复；长期可把 `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 设成中转的上限（官方说明它不能低于 100,000） |
| 每个请求都返回 500 | 中转可能不接受默认发送的工具搜索字段 | 设置 `ENABLE_TOOL_SEARCH=false` 再试 |
| 403，返回的是 HTML 页面 | 中转前面的防火墙拦下了请求体，curl 测试能过、真实会话过不了 | 由中转方给 `/v1/messages` 关闭请求体检查 |
| 401 或 404 `Invalid URL (POST /v1/v1/messages)` | 令牌错误，或 Base URL 多写了 `/v1` | Base URL 填 `https://api.openlux.ai`，见接入篇 |
| 不报错，但每轮输入 token 都很高 | 中转没有原样转发 `cache_control`，提示缓存一直没命中 | 由中转方原样转发 `cache_control` |

## 改完怎么验证

1. 在设置好变量的同一个终端运行 `claude`，输入 `/status`：能看到 `Anthropic base URL` 这一行显示中转地址，`Auth token` 或 `API key` 这一行显示你设置的变量名，说明配置生效了。
2. 重做之前报 400 的操作。如果之前是用 MCP 工具或让 Claude 读写文件时报错，就再做一次同样的操作，连续几轮都不再出现 400 就算解决。
3. 想单独确认地址和令牌没问题，可以用官方给的最小请求测试：返回以 `{"id":"msg_` 开头的 JSON，说明地址和令牌正常；报模型不存在也说明地址和令牌是通的，只是这个模型名不对。注意这条请求不带预发布字段，所以它通过并不说明 400 已经解决，第 2 步才是判断标准。

```bash
curl -sS -w '\n%{http_code}\n' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-4-6", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

## 如果你自己运营中转

官方兼容指南给中转运营方的要求是：原样转发 `anthropic-version` 和 `anthropic-beta` 请求头，不要按单个值做白名单，因为 Claude Code 每次发版都可能增加新值；请求头和对应的请求体字段一起转发；做内容审查时只读不改请求体；上游的报错正文原样返回，因为 Claude Code 的自动重试要靠识别这些报错原文；`cache_control` 出现在哪里都要原样保留。

还没有令牌的话，可以先 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-400-extra-inputs-not-permitted-fix&utm_content=footer)，在「令牌」页创建后按上面的步骤配置 Claude Code。

## 同专题文章

- [Claude Code 走中转报 429、Repeated 529 Overloaded 或一直 Retrying 怎么办：限流、过载与重试变量逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-429-529-overloaded-retry-fix/)
- [Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-401-invalid-api-key-fix/)
- [Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/)
- [Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-model-picker-missing-models-fix/)
- [Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)

[查看「Claude Code 接入与报错」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-code/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

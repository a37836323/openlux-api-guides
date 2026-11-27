---
layout: default
title: "Claude 桌面版怎么接入 Claude 中转 API：开发者模式、Configure Third-Party Inference、网关地址、Key 与模型设置"
description: "Claude 桌面版（Claude Desktop）接 Claude 中转 API：不登录 Anthropic 账号，开开发者模式进 Developer → Configure Third-Party Inference，Inference provider 选 Gateway，Gateway base URL 填 https://api.openlux.ai（不带 /v1）、Gateway API key 填令牌，Apply Changes 后重启；附模型自动发现与 inferenceModels、诊断报告核对、Auto 模式与 401、404、证书报错排查。"
permalink: /news/claude-desktop-relay-api-third-party-inference-gateway-setup/
date: 2026-11-25
---

> 更新日期：2026-11-25 · 一手来源：[Claude 官方文档](https://claude.com/docs/third-party/claude-desktop/gateway)

# Claude 桌面版怎么接入 Claude 中转 API：开发者模式、Configure Third-Party Inference、网关地址、Key 与模型设置

结论先说：Claude 桌面版（Claude Desktop）可以不登录 Anthropic 账号，改走官方的「第三方推理」模式（Claude Desktop on 3P），把请求发到你指定的网关。做法是：打开开发者模式 → **Developer → Configure Third-Party Inference…** → **Inference provider** 选 **Gateway** → **Gateway base URL** 填 `https://api.openlux.ai`（不带 `/v1`）→ **Gateway API key** 填 OpenLux 令牌 → **Apply Changes** → **Save & Restart**，重启后在登录页选择用这份配置启动。

依据是 Claude 官方文档 [Deploy Claude Desktop on 3P with an LLM gateway](https://claude.com/docs/third-party/claude-desktop/gateway)、[In-app configuration](https://claude.com/docs/third-party/claude-desktop/in-app-configuration) 和 [Installation and setup](https://claude.com/docs/third-party/claude-desktop/installation)。中转在官方文档里叫「LLM gateway」。

## 适用范围和前提

- **适用对象**：Claude 桌面版的 Chat、Cowork、Code 三种会话。官方说明这三种会话都由 Claude Code 执行，请求发给你配置的网关。
- **对网关的要求**：官方要求网关实现 Anthropic Messages API 的 `POST /v1/messages`，并支持流式输出和工具调用；`GET /v1/models` 可选，实现了就能自动列出模型。OpenLux 的 Anthropic 入口正是 `/v1/messages`，也提供 `/v1/models`。本文没有用真实令牌在桌面版里逐项测过流式和工具调用，配置完请按第五步自己验证。
- **不要先登录**：官方单机配置步骤写明，启动后**不要登录或注册 Anthropic 账号**，直接在登录界面打开开发者模式。
- **公司已统一下发配置的电脑不要自己改**：官方说明，设备上有组织下发的配置时，配置窗口是只读的。
- **要准备的东西**：在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建一个令牌；从价格接口 `https://www.openlux.ai/api/pricing_new` 选 `supported_endpoint_types` 含 `anthropic` 的 Claude 模型。2026-11-25 查询时，`claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5` 都含 `anthropic`。

官方列出的系统要求（以 Cowork 为准）：

| 系统 | 最低版本 | 安装包 |
|---|---|---|
| macOS | macOS 14（Sonoma）及以上，Apple 芯片或 Intel | `.dmg` |
| Windows | Windows 10 build 19041（2004 版）及以上，含 Windows 11 | `.msix`（旧的 `.exe` 安装包没有 Cowork） |
| Linux（测试版） | Ubuntu 22.04 及以上，或 Debian 12 及以上 | `.deb` |

## 要填的几项

| 配置窗口里的字段 | 对应配置键 | 填什么 |
|---|---|---|
| Inference provider | `inferenceProvider` | **Gateway** |
| Gateway base URL | `inferenceGatewayBaseUrl` | `https://api.openlux.ai`，不带 `/v1` |
| Gateway API key | `inferenceGatewayApiKey` | OpenLux 令牌 |
| Credential kind | `inferenceCredentialKind` | **Static API key**（默认） |
| Gateway auth scheme | `inferenceGatewayAuthScheme` | **Bearer**（默认）或 **x-api-key**，OpenLux 的 `/v1/messages` 两种请求头都接受，保持默认即可 |
| 模型列表 | `inferenceModels` | 留空走自动发现，或填完整模型 ID（见第四步） |

为什么不带 `/v1`：官方示例的网关地址只写到域名（`https://llm-gateway.example.corp`），并要求网关提供 `/v1/messages`，路径由客户端自己拼。多写 `/v1` 会变成 `/v1/v1/messages`，OpenLux 会返回 404 `Invalid URL (POST /v1/v1/messages)`。

## 第一步：先用 curl 验证地址和令牌

先在终端直接给中转发一个只要 1 个 token 的请求，这样之后出问题能分清是地址、令牌的问题，还是桌面版配置的问题。请求格式来自 Claude Code 官方的 [网关接入文档](https://code.claude.com/docs/en/llm-gateway-connect)。

macOS / Linux：

```bash
curl -sS -w '\n%{http_code}\n' -X POST "https://api.openlux.ai/v1/messages" \
  -H "Authorization: Bearer 你的OpenLux令牌" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5-5", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

Windows PowerShell：

```powershell
Invoke-RestMethod -Method Post -Uri "https://api.openlux.ai/v1/messages" `
  -Headers @{ "Authorization" = "Bearer 你的OpenLux令牌"; "anthropic-version" = "2023-06-01" } `
  -ContentType "application/json" `
  -Body '{"model": "claude-sonnet-5-5", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

怎么看结果：返回以 `{"id":"msg_` 开头、带 `"content"` 的 JSON，说明地址和令牌都对；返回 401 `Invalid token`，说明令牌错了或已删除。也可以用同一个令牌请求 `https://api.openlux.ai/v1/models`，能列出模型同样说明地址和令牌没问题。桌面版自动发现模型请求的也是这个路径；如果桌面版里列不出模型，按第四步手动填模型 ID。

## 第二步：打开开发者模式和配置窗口

1. 从 [claude.com/download](https://claude.com/download) 安装桌面版并启动，停在登录界面，不要登录。
2. 打开菜单：macOS 在顶部菜单栏；Windows 和 Linux 在登录界面左上角的应用菜单 ☰。
3. 依次点 **Help → Troubleshooting → Enable Developer Mode**。
4. 菜单里出现 **Developer** 后，点 **Developer → Configure Third-Party Inference…**，打开配置窗口。

官方提醒：如果是在应用进入第三方配置之前打开的开发者模式，应用按新配置重启后 **Developer** 菜单会消失。需要再改配置时，再点一次 **Help → Troubleshooting → Enable Developer Mode**，之后就会一直保留。

## 第三步：填 Connection 并应用

1. 在窗口左侧先选 **Connection**，把 **Inference provider** 设为 **Gateway**。
2. 在 **Gateway credentials** 卡片里按上表填 **Gateway base URL**、**Gateway API key**，**Credential kind** 保持 **Static API key**，**Gateway auth scheme** 保持 **Bearer**。
3. 窗口会边填边校验，并能对你填的地址做连接测试。
4. 点 **Apply Changes**，再点 **Save & Restart**。应用重启后，登录界面会多出一个用这份配置进入第三方模式的选项，选它即可。

几点官方说明：

- 配置写在本机的本地配置文件里，只对这台电脑、这个系统账户生效，之后随时可以在同一个窗口修改。
- 想回到普通的 Claude 桌面版，在登录界面选 Anthropic 登录即可。
- 不要把 `configLibrary/` 目录下的文件拷到别的电脑或别的系统账户：Key 是按当前系统账户加密保存的，换个环境会提示 **Claude can't read your saved key**，要重新输入 Key 并重启。

## 第四步：模型怎么选

官方说明有两种方式：

- **自动发现（不设 `inferenceModels`）**：桌面版读取网关 `GET /v1/models` 的返回来填模型选择器，只显示 ID 能认出是 Claude 的模型。
- **手动列出（设 `inferenceModels`）**：用你的网关接受的完整模型 ID，例如 `claude-sonnet-5-5`。列表里全部是完整 ID 时，桌面版会跳过 `/v1/models` 请求。

关于上下文窗口，官方说明：通过网关时，会话读不到上游真实的上下文窗口，只能按模型 ID 推断——认得的原生 1M 模型按 1M 算，其他按 200K 算；认不出的 ID 也按 200K 算，接近时自动压缩对话。所以模型名请直接用价格接口里的 Claude 官方 ID，不要自己起别名。

## 第五步：确认配置真的生效

1. 新建一个 Chat 会话发一句话，能正常回复就说明请求已经走到中转。
2. 需要排查时，点 **Help → Troubleshooting → Generate Diagnostic Report**，再点 **Export to file**。在导出的 `.zip` 里看三个文件：`managed-config.txt` 显示配置从哪里读到、每项的值（密钥已打码）；`provider-status.txt` 显示提供方设置是否完整有效；`deployment-mode.txt` 显示应用是否运行在第三方模式。
3. 应用日志位置：macOS `~/Library/Logs/Claude-3p/main.log`，Windows `%LOCALAPPDATA%\Claude-3p\Logs\main.log`，Linux `~/.config/Claude-3p/logs/main.log`。

## 和登录版相比要知道的差别

- **实验功能默认关闭**：官方说明，网关模式下桌面版默认关掉 MCP 工具搜索和 Claude Code 的其他实验性 beta 功能，因为严格的网关会拒收这些请求头和字段。设环境变量 `ENABLE_TOOL_SEARCH=true` 解除不了，要用 `toolSearchEnabled` 配置键；官方提醒只有网关能接受这些字段时才开，否则请求会报 400。
- **云端环境和远程控制不可用**：官方网关文档说明，启用网关配置后，环境选择器不再提供 Anthropic 托管的云端环境，Remote Control 也不可用。
- **Auto 模式的服务端审核**：Auto 模式默认请求网关背后的模型提供方做安全审核，需要网关原样转发相关请求头和字段。如果 Auto 模式每一轮都失败、而 Manual 模式的新会话正常，官方给的办法是：在 **Connection** 里关掉 **Server-side Auto mode checks**（显示已关时先打开再关上，窗口才会保存），再点 **Apply Changes**；或者改用 Manual 模式新建会话。

## 常见报错怎么查

| 现象 | 原因 | 处理 |
|---|---|---|
| 重启后登录界面没有出现第三方配置的选项 | 配置没有被读到，比如应用还在运行时写入了配置，或 `inferenceProvider` 缺失、拼错 | 完全退出应用再打开；导出诊断报告看 `managed-config.txt` 和 `provider-status.txt` |
| Code 显示 `Credentials rejected`，或中转返回 401 `Invalid token` | 令牌错误、复制不完整或已删除（官方排错页列出：静态 Key 收到 401 时，Code 直接显示这句） | 用第一步的 curl 单独测；在控制台重新创建令牌 |
| 404 `Invalid URL (POST /v1/v1/messages)` | **Gateway base URL** 多写了 `/v1` | 改成 `https://api.openlux.ai` |
| 模型选择器是空的或缺模型 | `/v1/models` 请求失败且 `inferenceModels` 为空，或模型 ID 认不出是 Claude | 先用 curl 测 `/v1/models`；在 `inferenceModels` 里手填完整 ID |
| `Model isn't available` | 官方列出 404 时 Code 显示这句；常见是模型 ID 不在中转在售列表里 | 换成价格接口里含 `anthropic` 端点的 ID |
| `SSL certificate verification failed (UNABLE_TO_VERIFY_LEAF_SIGNATURE)` | Claude Code 找不到签发网关证书的 CA，常见于公司网络的 TLS 代理 | 按官方 [网络代理文档](https://claude.com/docs/third-party/claude-desktop/network-proxy) 处理 TLS 拦截代理；窗口里连接测试通过也不能排除这一项 |
| `Your context window is full` | 对话压缩请求失败：超时或 504、524；或 401、402、403 表示令牌失效或额度用完 | 检查令牌和余额后点 **Try again**；也可以新开会话 |

命令行版 Claude Code 的配置方法见 [Claude Code 怎么接入 Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)。

## 开始使用

在 OpenLux 控制台创建令牌，先跑一遍第一步的 curl，再到桌面版的配置窗口里填网关地址和令牌：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-desktop-relay-api-third-party-inference-gateway-setup&utm_content=footer)

## 同专题文章

- [Claude API 报 400「"thinking.type.enabled" is not supported for this model」或「adaptive thinking is not supported on this model」怎么办：按模型选 adaptive 还是 enabled，budget_tokens 换成 effort](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-thinking-type-enabled-not-supported-fix/)
- [Claude API 在浏览器里直接调用报 CORS 错误或 401「CORS requests are not allowed for this Organization」怎么办：dangerouslyAllowBrowser、请求头与改走后端](https://a37836323.github.io/openlux-api-guides/news/claude-api-browser-cors-requests-not-allowed-fix/)
- [Claude Agent SDK 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、env 选项与模型设置（Python / TypeScript）](https://a37836323.github.io/openlux-api-guides/news/claude-agent-sdk-relay-api-base-url-env-setup/)
- [Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？](https://a37836323.github.io/openlux-api-guides/news/claude-external-key-webhook-events/)
- [Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-streaming-required-10-minutes-max-tokens-fix/)
- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

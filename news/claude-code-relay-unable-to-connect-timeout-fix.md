---
layout: default
title: "Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查"
description: "Claude Code 用 ANTHROPIC_BASE_URL 走中转时报 Unable to connect to API、Connection refused、ENOTFOUND、Request timed out、证书错误或回复中途断开的排查：先在同一终端用 curl 测 /v1/messages，再查残留 Base URL、代理变量、NODE_EXTRA_CA_CERTS，按官方说明调 API_TIMEOUT_MS 与流式看门狗，每次都 Connection dropped 时排查 tool search 字段。"
permalink: /news/claude-code-relay-unable-to-connect-timeout-fix/
date: 2026-11-03
---

> 更新日期：2026-11-03 · 一手来源：[Claude Code 官方文档：Error reference](https://code.claude.com/docs/en/errors)

# Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查

先说结论：Claude Code 走中转时报 `Unable to connect to API`、`Connection refused`、`Request timed out` 这类错误，先在启动 `claude` 的同一个终端里用 curl 直接请求中转的 `/v1/messages`。curl 也失败，问题在地址、网络或代理；curl 成功而 Claude Code 失败，多半是残留的 `ANTHROPIC_BASE_URL`、代理变量或证书设置没对上。超时类报错再按场景调 `API_TIMEOUT_MS` 等变量，每次请求都 `Connection dropped` 时还要排查 tool search 相关字段。

本文适用于用 `ANTHROPIC_BASE_URL` 把 Claude Code CLI 接到中转（LLM 网关）的情况，报错原文和处理办法都来自 Claude Code 官方的 [Error reference](https://code.claude.com/docs/en/errors)、[Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect) 和 [Enterprise network configuration](https://code.claude.com/docs/en/network-config)。以 OpenLux 为例时，Base URL 是 `https://api.openlux.ai`，不带 `/v1`。还没接入的读者先看 [Claude Code 怎么接入 Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)。

要先知道一点：官方说明 Claude Code 遇到临时故障会用指数退避自动重试，默认最多 10 次，然后才显示错误。所以你看到报错时，能重试的已经重试过了；报错前一段时间没反应，往往就是在重试。

## 先按报错原文对号入座

官方从 v2.1.227 起把连接错误改成「说明 + 括号里的错误码」的写法，旧版本显示为 `Unable to connect to API (ECONNREFUSED)` 这种形式。

| 报错原文 | 官方给出的含义 | 先做什么 |
|---|---|---|
| `Connection refused — a firewall or proxy may be blocking it (ConnectionRefused)` | Base URL 地址上没有服务应答：地址写错，或 VPN、防火墙挡住了到中转的路径 | 跑第一步的 curl；查有没有残留的旧 `ANTHROPIC_BASE_URL` |
| `Can't reach the API server — check your internet or DNS (ENOTFOUND)` | 域名解析不出来 | 核对 Base URL 里的域名拼写和本机 DNS |
| `No internet route — check your connection or VPN (EHOSTUNREACH)` | 没有到目标的网络路由 | 检查网络和 VPN |
| `Couldn't connect through your proxy (ERR_PROXY_TUNNEL)` | 代理拒绝建立隧道 | 检查代理凭据，确认代理允许访问中转域名 |
| `Connection dropped (ECONNRESET)` | 连接被断开 | 偶发的会自动重试；每次都断，看本文 tool search 一节 |
| `Request timed out` | 在请求截止时间内没收到响应，默认 10 分钟 | 看第三步 |
| `SSL certificate verification failed` 或 `Self-signed certificate detected` | 网络里有代理用自己的证书拦截 TLS，Claude Code 不信任它 | 用 `NODE_EXTRA_CA_CERTS` 指定 CA 证书 |
| `Socket is closed` | 流式回复还在传时连接被关闭，最常见的是 Windows 上的企业代理 | 升级到 v2.1.214 或更新版本 |
| `API Error: Connection lost mid-response. The response above may be incomplete.` | 回复中途断开，已完成的部分保留了 | 回复 `continue` 让它接着写 |

## 第一步：在同一个终端用 curl 直接测中转

官方建议在打开 Claude Code 之前，先用 shell 里的变量直接给网关发一个只要 1 个 token 的请求：失败了就说明问题在网关或网络，而不是 Claude Code 的配置。下面是按官方命令换成 OpenLux 地址和在售模型 ID 的写法（令牌换成你自己的，不要贴到截图或聊天里）：

```bash
export ANTHROPIC_BASE_URL=https://api.openlux.ai
export ANTHROPIC_AUTH_TOKEN=你的OpenLux令牌
curl -sS -w '\n%{http_code}\n' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5-5", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

结果怎么看：

- 返回以 `{"id":"msg_` 开头、带 `"content":[...]` 的 JSON：地址和令牌都没问题，往下查 Claude Code 这一侧。
- 返回提示模型不存在的错误：官方说明这同样证明地址和令牌可用，因为网关先验证了令牌才拒绝模型名。
- 返回 `401`：令牌被拒，按接入篇检查令牌，这不是连接问题。OpenLux 对无效令牌返回 `Invalid token`。
- 返回 `404`，内容是 `Invalid URL (POST /v1/v1/messages)`：Base URL 多写了 `/v1`，改成 `https://api.openlux.ai`。
- curl 本身报连接被拒、解析失败或超时：和 Claude Code 里的报错是同一个原因，先解决地址、DNS、VPN 或代理。

Windows PowerShell 里官方建议用 `curl.exe`，以免调用到同名的 `Invoke-WebRequest` 别名。

## 第二步：curl 能通、Claude Code 不通时查这几处

官方说，curl 成功而 Claude Code 失败，原因通常在运行环境和网络之间，而不是网络本身。按顺序查：

1. **残留的 Base URL**。运行 `echo $ANTHROPIC_BASE_URL`（PowerShell 用 `echo $env:ANTHROPIC_BASE_URL`），再看各个 settings 文件的 `env` 块。设置了它，Claude Code 就把模型请求发到这个地址；如果它指向一个已经不运行的本地代理或旧网关，就会报 `Connection refused`。删掉旧值后，从新开的终端启动 Claude Code。
2. **代理变量**。Claude Code 读取标准的 `HTTPS_PROXY`、`HTTP_PROXY`、`NO_PROXY`（小写也认），按 `https_proxy`、`HTTPS_PROXY`、`http_proxy`、`HTTP_PROXY` 的顺序取第一个有值的。官方写明**不支持 SOCKS 代理**；代理地址缺少 `http://` 这类协议头、解析不了时，Claude Code 会在启动时报错并指出是哪个变量。
3. **证书**。公司网络有 TLS 检查代理时，官方说 curl 能通、Claude Code 报证书错误，是因为 Claude Code 的运行时没有信任 curl 所用的那个 CA。按官方做法导出公司的 CA 证书，用 `NODE_EXTRA_CA_CERTS=/path/to/ca-bundle.pem` 指过去。官方明确提醒不要设置 `NODE_TLS_REJECT_UNAUTHORIZED=0`，那会完全关掉证书校验。
4. **系统层面**。Linux 和 WSL 检查 `/etc/resolv.conf` 里有没有连不上的 DNS 服务器（WSL 可能从宿主继承了坏的解析配置）；macOS 上卸载或断开的 VPN 可能留下 `utun` 网卡或路由规则；Docker Desktop 这类容器软件可能拦截出站流量，退出后再试可以排除。

查完后在 Claude Code 里运行 `/status`：Status 页的 `Anthropic base URL` 应显示中转地址，`Proxy` 一行显示正在使用的代理（无法解析的值会标成无效并被忽略）。

## 第三步：超时类报错怎么调

几个变量管的是不同阶段，调之前先分清：

| 变量 | 默认值 | 管什么 |
|---|---|---|
| `API_TIMEOUT_MS` | 600000（10 分钟） | 每次请求等**响应头**的时间，不限制流式回复开始后持续多久 |
| `CLAUDE_CODE_MAX_RETRIES` | 10 | 重试次数，想在脚本里更快看到失败可以调低 |
| `CLAUDE_STREAM_IDLE_TIMEOUT_MS` | 不设置 | 同时设置两个流式看门狗的超时，低于 5 分钟会被提到 5 分钟，字节级看门狗最多 30 分钟 |
| `CLAUDE_STREAM_FIRST_BYTE_TIMEOUT_MS` | 不设置 | 首字节截止时间，走 `ANTHROPIC_BASE_URL` 中转时这个截止时间默认不运行 |

按现象处理：

- **`Request timed out`**：先重试一次。网络或代理本身慢，就调大 `API_TIMEOUT_MS`。官方特别提到：把 `API_TIMEOUT_MS` 设成 `0` 会关掉这个请求超时，但 v2.1.305 之前的版本这样设会让每个请求都失败，遇到就升级或改回正数；另外设成 `0` 也关不掉首字节截止时间和空闲超时。
- **一直等、没有任何回复**：官方网络配置页说明，走 `ANTHROPIC_BASE_URL` 中转时不跑首字节截止时间，收不到响应头的请求会在 5～6 分钟后由空闲超时结束。想让它更早失败并重试，可以把 `API_TIMEOUT_MS` 设成低于 `300000` 的正数；但要比你预期的最长等待时间长，否则每次重试都会再次超时。
- **流式中途长时间没数据**：经过自定义 `ANTHROPIC_BASE_URL` 时，字节级看门狗在 300 秒收不到任何字节（包括 SSE 心跳）时中止连接，中转定期发心跳就不会触发它。但官方也说明，还有一个事件级看门狗按「解析出的响应事件」计时，只有心跳、长时间没有实际内容时，它最终仍会中止连接。

## 第四步：流式中断和「回复可能不完整」

- **`Waiting for API response · will retry in … · check your network`**：表示一段时间没收到数据，请求还没失败，数据恢复后横幅自己消失。走中转时如果它在思考过程中时有时无，官方建议升级到 v2.1.309 或更新版本：这些版本在 `ANTHROPIC_BASE_URL` 指向非 Anthropic 地址时，45 秒没数据才显示横幅，旧版本是 20 秒。每次重试都出现，就按网络问题查。
- **`The response above may be incomplete`**：Claude 已经写完一段文字或一个工具调用之后连接出问题，为了避免同一个工具调用执行两次，Claude Code 不会整个重发，而是保留已完成的部分。交互模式下回复 `continue` 即可接着写；`-p` 非交互模式下，只有文字、没有工具调用的回复会自动续写，最多连续 3 次。
- **`Streaming response ended before any complete data was received. Retrying without streaming.`**：流式回复结束了却没有可用数据，Claude Code 改用非流式重发，同一个请求实际发了两次。官方说常见原因是中间的代理或网关吞掉或改写了流式响应体，处理办法是让代理原样转发流式响应体和响应头。如果你在 Claude Code 和中转之间自己加了一层代理，可以先绕过它对照一次。
- **`Socket is closed`**：v2.1.214 之前不会重试，运行 `claude update` 升级后再发一次；升级后还在同一个代理后面反复失败，按第二步查代理。

## 每次请求都 Connection dropped 或 500：查 tool search 字段

这是走中转才有的情况。官方说明从 v2.1.304 起，`ANTHROPIC_BASE_URL` 指向网关时默认开启 MCP 工具搜索（tool search），请求里会带 `defer_loading` 工具字段、`tool_reference` 内容块和对应的 `anthropic-beta` 请求头，并期望网关原样转发。官方在 `Unable to connect to API` 和 `API Error: 500` 两条里都写了：如果每个请求都以 `Connection dropped` 或 500 结束，要检查网关和它的上游是否接受这些字段。

使用方可以这样处理：

1. 先升级。官方说明 v2.1.305 起，请求收到 `400` 或 `422` 后，Claude Code 可以去掉 tool search 重试，成功时 MCP 工具改为一开始全部加载，界面上不显示任何提示。官方只写了 `400`、`422` 两种情况，网关直接断开连接或返回 500 时不要指望它，继续看下一条。
2. 想确认是不是它引起的，可以用 `ENABLE_TOOL_SEARCH=false` 启动做对照，官方把这个值列为不使用 tool search 的配置。设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` 也会让 tool search 保持关闭，但它还会去掉其他预发布字段。
3. 关掉之后 MCP 工具定义一开始就全部放进上下文，会占用更多上下文；对照确认原因后，把报错原文和请求时间发给中转方排查。

如果报错里直接点名了 `defer_loading` 或 `tool_reference`，那属于 400 字段不被接受，按 [Claude Code 走中转报 400「Extra inputs are not permitted」](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/) 一文处理。

## 改完怎么验证

1. 在已经导出变量的同一个终端运行 `claude`，发一条简短消息，能正常回复就说明连通。
2. 运行 `/status`，确认 `Anthropic base URL` 显示中转地址、`Auth token` 或 `API key` 一行显示你设置的变量，`Proxy` 一行和你预期的一致。
3. 想看配置有没有加载，用 `claude --debug` 启动。官方说明调试日志写到 `~/.claude/debug/<session-id>.txt`，不输出到终端；证书文件读不到时，日志里会有 `Failed to read` 或 `Failed to load` 的原因。
4. 偶发的超时、断连属于正常重试范围，能自己恢复就不用改配置；同一个报错每次都出现，再按上面的步骤改。

## 开始使用

curl 能通、`/status` 显示中转地址、发消息正常回复，就说明连接问题已经解决。还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-unable-to-connect-timeout-fix&utm_content=footer)，在控制台「令牌」页创建后按上面的步骤配置。

## 同专题文章

- [Claude Code 走中转报 429、Repeated 529 Overloaded 或一直 Retrying 怎么办：限流、过载与重试变量逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-429-529-overloaded-retry-fix/)
- [Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-401-invalid-api-key-fix/)
- [Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-model-picker-missing-models-fix/)
- [Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/)
- [Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)

[查看「Claude Code 接入与报错」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-code/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查"
description: "Open WebUI 接中转 API 后回复是 {}、报 Unexpected token 'd' is not valid JSON、流式 Markdown 乱码、偶发 Model not found、管理员连接 502 或 CERTIFICATE_VERIFY_FAILED 时，按官方 Connection Errors 排错页和环境变量文档逐项排查反向代理、nginx 代理缓冲、c-ares DNS 解析、前后端连接差异、CA 证书与流式空闲超时，并用 /v1/models 和流式请求确认中转本身正常。"
permalink: /news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/
date: 2026-11-07
---

> 更新日期：2026-11-07 · 一手来源：[Open WebUI 文档：Connection Errors / Environment Variable Configuration / Custom CA Store](https://docs.openwebui.com/troubleshooting/connection-error/)

# Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查

Open WebUI 接上中转 API 以后，地址和 Key 都验证通过了，聊天时却出现回复只有 `{}`、报 `Unexpected token 'd', "data: {"id"... is not valid JSON`、流式回复里冒出 `##`、`**`、偶尔提示 Model not found，或者后台日志里有 `CERTIFICATE_VERIFY_FAILED`，先别急着换地址和 Key：[Open WebUI 官方 Connection Errors 排错页](https://docs.openwebui.com/troubleshooting/connection-error/)把这几种现象分别归到了 Open WebUI 前面的反向代理、Open WebUI 后端的 DNS 解析和网络，以及公司网络的 HTTPS 证书，并写了各自的原因和修法。本文按它逐项排查。

本文适用于已经在 Settings > Admin > Connections 里加好 OpenAI 兼容连接、URL 填 `https://api.openlux.ai/v1` 的读者，以 OpenLux 为例。还没配置的，先看本站的 [Open WebUI 接入中转 API 教程](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-api-openai-compatible-setup/)；Verify Connection 报 401、模型列表一直转圈、手填的模型 ID 不对这几种情况，那篇已经写过，这里不重复。环境变量名称以撰文时的官方文档为准。

## 先分清问题出在哪一段

一次聊天要经过两段网络：浏览器到 Open WebUI（中间常有 nginx 等反向代理），Open WebUI 后端到中转。先按现象判断是哪一段，再动配置。

| 现象 | 出问题的一段 | 官方给的方向 |
|---|---|---|
| 回复是 `{}`，或报 `Unexpected token 'd', "data: {"id"... is not valid JSON` | 浏览器到 Open WebUI（反向代理、HTTPS、CORS、WebSocket） | 补齐反向代理所需的环境变量和请求头 |
| 流式时出现 `##`、`**`、少字，关掉流式就正常 | 浏览器到 Open WebUI（nginx 代理缓冲） | 关闭 `proxy_buffering` |
| 刚才还能用的模型突然提示 Model not found，模型列表自己变空，日志有 `ClientConnectorDNSError` | Open WebUI 后端的 DNS 解析 | 不开 c-ares 解析器 |
| 管理员加的连接报 502 或 `Connect call failed ('127.0.0.1', ...)`，同一地址作为用户直连却正常 | Open WebUI 后端的网络 | 后端连接用后端实际能访问的地址 |
| 后台日志有 `[SSL: CERTIFICATE_VERIFY_FAILED]` | Open WebUI 后端到中转（证书） | 让 Open WebUI 信任公司网络的 CA 证书 |
| 流式回复中途停住，界面一直等 | Open WebUI 后端到中转（上游不再发数据） | 设流式空闲超时 |

官方的隔离方法是：绕开反向代理，直接访问 Open WebUI 再试一次（原文 “Try connecting directly to Open WebUI without the proxy to isolate the issue”）。直连正常、走域名不正常，问题就在反向代理这一段；直连也不正常，再看后端到中转那一段。

## 回复是 `{}` 或报 Unexpected token 'd'：先查反向代理和 HTTPS 配置

官方把空回复 `{}`、`Unexpected token 'd', "data: {"id"... is not valid JSON`、浏览器控制台或日志里的 WebSocket 连接失败、CORS 报错、HTTPS 下的混合内容警告归为同一类：Open WebUI 放在反向代理或 HTTPS 后面时，CORS、TLS、WebSocket 或 Cookie 没配好。官方要求在这种部署下设置这些环境变量：

- `WEBUI_URL`：填你实际访问的 HTTPS 域名。它是持久化配置，首次启动后改环境变量不生效，可以在 Settings > Admin > General > WebUI URL 里改。
- `CORS_ALLOW_ORIGIN`：把用户可能访问的所有地址都写进去（域名、IP、localhost，http 和 https 带端口），用分号分隔。日志里出现 `https://yourdomain.com is not an accepted origin` 这类提示，就是少写了这个地址。
- `WEBUI_SESSION_COOKIE_SECURE=true`、`WEBUI_AUTH_COOKIE_SECURE=true`：用 HTTPS 时打开，不用 HTTPS 时关掉。

官方还写明 Open WebUI v0.5.0 起必须有 WebSocket 支持。反向代理里要正确设置 `Upgrade` 和 `Connection` 请求头，并带上 `X-Forwarded-Proto`。用 HAProxy 3.x 这类默认开 HTTP/2 的代理时，实例可能卡住不响应，官方给的修法是 HAProxy 加 `option h2-workaround-bogus-websocket-clients` 或让后端连接走 HTTP/1.1，nginx 则确认写了 `proxy_http_version 1.1;`。

这一类属于浏览器到 Open WebUI 这一段的配置，先不要去改中转的地址和 Key。改完后按官方的检查顺序验证：浏览器访问域名没有证书警告；开发者工具 Network 标签按 WS 过滤，能看到 WebSocket 连接建立；控制台没有 CORS 报错；发一条消息，流式回复正常。

## 流式回复里出现 `##`、`**` 或少字：关掉 nginx 代理缓冲

如果流式回复的 Markdown 渲染错乱，比如直接显示 `##`、`**`，粗体符号位置不对，或者随机少几个词，而关掉流式就正常，官方说这通常是 nginx 的代理缓冲造成的：缓冲打开时，nginx 会把 SSE 流重新切块，把一个 Markdown 标记拆到两块里，解析就出错了。

官方给的修法是在 Open WebUI 的 location 里关掉缓冲（下面按官方示例保留关键几行，`proxy_pass` 换成你自己的上游）：

```nginx
location / {
    proxy_pass http://your-open-webui-upstream;
    proxy_buffering off;
    proxy_cache off;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

官方提示关掉缓冲后流式速度也会明显变快。用其他反向代理的：HAProxy 确认 SSE 端点没开 `option http-buffer-request`；Traefik 检查压缩和缓冲中间件；Caddy 默认一般没问题，但要检查有没有缓冲类插件。

## 偶发 Model not found、模型列表自己变空：检查 DNS 解析方式

刚才还能用的模型，过一会儿聊天就提示 Model not found，再过一会儿又好了；或者模型列表自己清空、重启后恢复；日志里有 `ClientConnectorDNSError` 或 `Cannot connect to host ...`，而在同一个容器里用命令行解析这个域名是正常的。官方说明这是 DNS 解析失败被显示成了模型不存在：域名解析不出来时，Open WebUI 分不清是解析失败还是提供方没有这个模型。

原因在可选的 c-ares 解析器。默认情况下 Open WebUI 用操作系统解析域名；打开 `AIOHTTP_CLIENT_ASYNC_DNS_RESOLVER=true` 后改用 c-ares。官方列出的问题包括：在部分 Windows 主机上找不到可用的 DNS 服务器，所有外部域名都解析不了；在 Docker 里可能间歇性解析不了容器名，而 Docker 自己的 DNS 仍在正常应答；使用 Tailscale MagicDNS（DNS 服务器 `100.100.100.100`）的主机上，查询会卡 10 到 20 秒后失败，关掉时验证正常的连接，打开后会显示 “Server Connection Error”。

处理方法：

1. 检查启动参数或 `.env` 里有没有 `AIOHTTP_CLIENT_ASYNC_DNS_RESOLVER=true`，有就删掉或改为 `false`。
2. 官方说明这个变量只在启动时读取一次，改完要重启 Open WebUI。
3. 重启后反复切换几次模型、发几条消息，确认不再出现 Model not found。

如果从来没开过这个变量，模型 ID 也和价格接口、`/v1/models` 返回的一致，那就按下文「用命令行确认中转本身正常」检查网络。

## 管理员连接报 502、用户直连却正常：后端用的是另一套网络

官方说明，Open WebUI 有两种连接方式：用户的 Direct Connections 从浏览器发出，管理员在后台配置的连接（包括 OpenAI API 连接）从 Open WebUI 后端发出。两边的网络和 DNS 不同，同一个地址可能一边能用、一边不能用。官方列出的现象是：管理员配置的连接报 502 Bad Gateway，而用户连接正常；后端日志出现 `Connect call failed ('127.0.0.1', ...)`。

官方举的例子是：同一个域名，在 Docker 容器里可能被解析成 `127.0.0.1`，请求根本没到达目标。出现上面的现象，就要在 Open WebUI 所在的服务器或容器里检查网络和 DNS，命令见文末「用命令行确认中转本身正常」。浏览器里能打开、能用，不代表后端也能连上。

## 报 CERTIFICATE_VERIFY_FAILED：让 Open WebUI 信任公司网络的 CA

官方 Custom CA Store 页（社区贡献内容，页首注明不受 Open WebUI 团队支持）说明：运行时报 `[SSL: CERTIFICATE_VERIFY_FAILED]`，多半是所在网络会拦截 HTTPS 流量（例如公司网络），需要把对应的证书加进 Open WebUI 的信任库。

官方环境变量文档提供了 `AIOHTTP_CLIENT_SSL_CERT_FILE`：指向一个自定义 CA 证书包，作为所有开启了证书校验的出站 HTTPS 连接的默认 CA，用来在整个应用里信任公司或内部 CA，而不用关掉校验。用 Docker 部署时，证书包要挂载进容器，变量写容器里的路径。Custom CA Store 页给出的做法是把宿主机的整套系统证书包只读挂载进去，并提醒要挂整套证书包而不是单个证书，否则容器里的公共根证书都会消失；该页用的变量是 `SSL_CERT_FILE`。

不建议用关闭校验的方式绕过。官方文档里 `AIOHTTP_CLIENT_SESSION_SSL=false`、`REQUESTS_VERIFY=false` 这类变量的说明对象是 Ollama 向量、语音、Tika、重排序等服务，并警告关闭校验会降低安全性，只应在信任的内部网络里用；连公网上的中转不属于这种情况。

## 流式回复中途卡住：设流式空闲超时

官方环境变量文档说明，`AIOHTTP_CLIENT_TIMEOUT` 默认不设超时，客户端会一直等；`AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT` 默认也不设，上游在流式中途停止发数据时，连接会一直挂到总超时为止。

想让卡住的请求尽快失败，可以设 `AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT`。它限制的是两个数据块之间的最长间隔，不是整段回复的时长，持续输出的长回答不会被截断。官方建议设成比你预期最慢的 token 间隔略大一点（文档举例为 `60`），非数字、0 或负数都按不设处理。设了以后，超过这个间隔没收到数据的请求会被中止，可以重新发送；如果经常卡住，再用下一节的命令看中转直接返回是否正常。

## 用命令行确认中转本身正常

上面几类问题都排除了，或者分不清是哪一段，就在 **Open WebUI 所在的服务器或容器里**（不是你自己的电脑）直接请求中转。`$OPENLUX_API_KEY` 换成你的 Key，不要把 Key 贴进截图或聊天：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明这台机器的网络、DNS、证书、地址和 Key 都没问题；返回 401（`Invalid token`）说明 Key 不对；连不上、解析失败或报证书错误，回到前面对应的小节。

再按官方排错页的思路发一次流式请求，确认流式数据能正常返回，`your-model` 换成价格接口 `https://www.openlux.ai/api/pricing_new` 里在售、端点类型含 `openai` 的模型 ID：

```bash
curl -s -N https://api.openlux.ai/v1/chat/completions -H "Authorization: Bearer $OPENLUX_API_KEY" -H "Content-Type: application/json" -d '{"model":"your-model","stream":true,"messages":[{"role":"user","content":"hello"}]}'
```

能持续看到以 `data:` 开头的数据行、内容完整输出，说明中转的流式输出正常，问题在 Open WebUI 或它前面的反向代理。最终以在 Open WebUI 里选中这个模型、发一条消息能完整返回为准。

## 参考资料

- Open WebUI 文档：[Connection Errors](https://docs.openwebui.com/troubleshooting/connection-error/)（HTTPS、CORS、WebSocket，流式乱码，DNS 解析与 Model not found，前后端连接区别）
- Open WebUI 文档：[Environment Variable Configuration](https://docs.openwebui.com/reference/env-configuration/)（`AIOHTTP_CLIENT_ASYNC_DNS_RESOLVER`、`AIOHTTP_CLIENT_SSL_CERT_FILE`、`AIOHTTP_CLIENT_TIMEOUT`、`AIOHTTP_CLIENT_STREAM_IDLE_TIMEOUT`）
- Open WebUI 文档：[Custom CA Store](https://docs.openwebui.com/troubleshooting/custom-ca/)（社区贡献，公司网络拦截 HTTPS 时的证书处理）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=open-webui-relay-stream-unexpected-token-dns-certificate-fix&utm_content=footer)，在「令牌」页创建 Key 后填进 Open WebUI 的连接设置。

## 同专题文章

- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)
- [Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-stream-stall-tool-call-fix/)
- [n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)
- [n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

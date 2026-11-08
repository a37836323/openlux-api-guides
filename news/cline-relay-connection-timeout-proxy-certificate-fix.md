---
layout: default
title: "Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置"
description: "Cline 接中转 API 后连不上、请求超时或报 SSL/TLS 证书错误怎么办：先用 curl 分清网络问题和地址、Key 填错，再按 Cline 官方文档分别设置 VS Code 扩展的 http.proxy、CLI 的 https_proxy 与 NODE_EXTRA_CA_CERTS、JetBrains 的 HTTP Proxy，以及证书导入与日志查看。"
permalink: /news/cline-relay-connection-timeout-proxy-certificate-fix/
date: 2026-11-04
---

> 更新日期：2026-11-04 · 一手来源：[Cline Networking and Proxies](https://docs.cline.bot/troubleshooting/networking-and-proxies)

# Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置

Cline 填好中转的 Base URL 和 Key 后还是连不上、请求超时，或者报 SSL/TLS 证书错误，先分清一件事：这是**网络问题**，还是地址、Key 填错。按 [Cline 官方文档「Networking and Proxies」](https://docs.cline.bot/troubleshooting/networking-and-proxies)，网络设置要看你用的是哪种 Cline：VS Code 扩展用 VS Code 自己的代理设置，Cline 不用另外配置；命令行版（CLI）读标准的 `https_proxy`、`http_proxy` 环境变量；JetBrains 插件用 IDE 的 HTTP Proxy 设置。设错了地方，改了也不生效。

本文适用于已按 [Cline 接入中转 API 教程](https://a37836323.github.io/openlux-api-guides/news/cline-relay-api-openai-compatible-setup/) 填好 OpenLux 地址的读者，设置项名称以撰文时的官方文档为准，界面可能随版本变化。

## 先判断是不是网络问题

Cline 的 [OpenAI Compatible 配置页](https://docs.cline.bot/provider-config/openai-compatible)排错部分把这类情况叫 **Connection Errors**，官方让检查三项：Base URL 是否正确、本机能否访问到服务商的 API、有没有防火墙或网络问题拦截。所以先用 curl 在**同一台电脑**上请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

按结果分支：

| curl 的结果 | 说明 | 下一步 |
|---|---|---|
| 返回模型列表 | 地址、Key、网络都通 | 问题在 Cline 用的代理或证书设置，按下文对应的 Cline 版本检查 |
| 返回 401 `Invalid token` | 网络是通的，Key 错了或没带上 | 不是本文的问题，回 OpenLux「令牌」页重新复制 Key |
| 返回 404 | 网络是通的，地址层级不对 | OpenAI Compatible 的 Base URL 填 `https://api.openlux.ai/v1`；Anthropic 服务商的自定义地址填 `https://api.openlux.ai`，不带 `/v1` |
| 一直卡住直到超时 | 本机到接口的网络不通 | 所在网络要走代理的话，先按下一节用代理测通 |
| 报证书错误 | 网络里有代理或安全设备改写了证书 | 按「证书错误」一节处理 |

## 用 curl 带代理测通

公司网络需要代理时，官方给的测试方法是先单独用 curl 验证代理（示例里的 `proxy.company.com:8080` 换成你们的代理地址和端口）：

```bash
export https_proxy=http://proxy.company.com:8080
curl -vv https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

Windows PowerShell 写法是 `$env:https_proxy="http://proxy.company.com:8080"`，然后用 `curl.exe` 执行同样的请求。需要自定义证书时，按官方示例加上 `--cacert` 指定 CA 证书文件；也可以用 `-x proxy.company.com:8080` 直接给 curl 指定代理。

注意：`-vv` 会把请求头原样打出来，里面有你的 Key。把输出发给同事或贴到工单之前，先删掉 `Authorization` 那一行。

带代理能通、不带代理不通，说明 Cline 也必须走这个代理；带代理也不通，先找网络管理员确认代理地址、端口、是否需要认证，以及防火墙是否放行 `api.openlux.ai`。官方的 Connection Timeouts 排查就是这三步：核对代理地址和端口、确认代理是否需要认证、确认防火墙没有拦截 AI 服务商的 API 地址。

## VS Code 扩展：用 VS Code 的代理设置

Cline 文档写明，VS Code 扩展依赖 VS Code 自己的代理设置。[VS Code 网络文档](https://code.visualstudio.com/docs/setup/network)说明：VS Code 本身和 Chromium 的代理支持相同，会读取系统的代理和证书设置；但文档同时写明，扩展还享受不到这套完整的代理支持，`http.proxy`、`http.proxyStrictSSL`、`http.proxyAuthorization` 这几个设置只在扩展和 VS Code 命令行这两种场景下生效。

所以 Cline 扩展连不上时，打开 VS Code 设置搜索 `http.proxy`：

1. 需要走代理：把 `http.proxy` 设成公司代理地址，例如 `http://proxy.company.com:8080`，改完再试。
2. 不需要代理、curl 直连就通：看看 `http.proxy` 里是否还留着已经不用的旧代理地址，有的话清掉。
3. 改完在 Cline 里点 **Verify** 或发一条简单任务，确认能返回。

## CLI：用环境变量设置代理

Cline 命令行版读取标准的 HTTP 代理环境变量，要在运行 `cline` 之前设置。官方写法（macOS / Linux）：

```bash
export https_proxy=http://proxy.company.com:8080
export http_proxy=http://proxy.company.com:8080
export no_proxy=localhost,127.0.0.1,.local
cline
```

Windows 命令提示符用 `set https_proxy=...`，PowerShell 用 `$env:https_proxy="..."`。几个要点都来自官方文档：

- **代理要认证**：把用户名和密码写进 URL，如 `http://username:password@proxy.company.com:8080`。官方提醒，把凭据放在环境变量里有安全风险。
- **只支持 HTTP 代理**：不支持 SOCKS、PAC 脚本，也不支持用户名密码之外的认证方式。手上只有 SOCKS 或 PAC 地址时，要向网络管理员要 HTTP 代理地址。
- **长期生效**：macOS / Linux 把上面的 `export` 写进 `~/.bashrc`、`~/.zshrc` 或 `~/.profile`；Windows 在系统「环境变量」里添加到用户变量或系统变量，然后重启终端或 IDE。
- **看日志**：日志在 `~/.cline/data/logs/cline.log`（或 `CLINE_LOG_PATH` 指定的文件），可以用 `cline doctor log` 打开，查看是否用上了代理、有哪些网络错误。

## JetBrains 插件：用 IDE 的 HTTP Proxy

官方步骤：

1. 打开设置（Windows / Linux：File > Settings；macOS：IntelliJ IDEA > Preferences）。
2. 进入 `Appearance & Behavior > System Settings > HTTP Proxy`，选 **Manual proxy configuration**。
3. 填 **Host name**、**Port number**，**No proxy for** 填 `localhost,127.0.0.1`；代理需要认证就勾选 **Proxy authentication** 填写账号。
4. 点 **Check connection**，再点 **OK**。
5. **重启 IDE**。官方写明代理改动不会动态生效，不重启等于没改。

然后在 Cline 面板发一条简单消息测试；失败就看 IDE 的 Event Log，以及 `~/.cline/cline-core-service.log`（每个打开的项目的 Cline 进程都写这一个文件）。JetBrains 同样只支持 HTTP 代理。

## 证书错误怎么处理

公司的 HTTPS 代理常会改写证书，客户端不信任这张证书就会报 SSL/TLS 错误。按官方说法分版本处理：

| Cline 版本 | 处理方法 | 依据 |
|---|---|---|
| CLI | 设 `NODE_EXTRA_CA_CERTS` 指向公司 CA 证书，确认路径正确、文件是 PEM 格式 | Cline Networking and Proxies |
| VS Code 扩展 | 首选把代理的证书加入操作系统信任链；Linux 还要加进 NSS 库 | VS Code 网络文档 |
| JetBrains | 加入系统信任库，或在 Settings > Tools > Server Certificates 点「+」导入 | Cline Networking and Proxies |

CLI 示例（macOS / Linux）：`export NODE_EXTRA_CA_CERTS=/path/to/ca-certificate.pem`，Windows 用 `set NODE_EXTRA_CA_CERTS=C:\path\to\ca-certificate.crt`，路径换成证书的实际位置。证书文件向网络管理员要，不要从不明来源下载。

Cline 文档还提到可以在 VS Code 里关掉 `http.proxyStrictSSL`，但官方注明不建议在生产环境这么做；VS Code 文档对 `--ignore-certificate-errors` 启动参数的评价是危险、不推荐。如果要用，只当临时排查手段，确认是证书问题后改回去，换成导入证书的做法。

## 改完怎么验证

1. 在 Cline 所在的同一个环境（同一个终端，或 IDE 使用的同一套代理）里，用上面的 curl 请求 `https://api.openlux.ai/v1/models`，确认能列出模型。
2. 在 Cline 里点 **Verify** 或发一条简单任务，能正常返回就算修好。
3. 仍然失败时，按版本看日志：CLI 看 `cline doctor log`，JetBrains 看 Event Log 和 `cline-core-service.log`；日志里的错误变成 401 或模型不存在，说明网络已经通了，回到 [接入教程](https://a37836323.github.io/openlux-api-guides/news/cline-relay-api-openai-compatible-setup/) 核对 Key 和 Model ID。

## 参考资料

- Cline 文档：[Networking and Proxies](https://docs.cline.bot/troubleshooting/networking-and-proxies)（VS Code、CLI、JetBrains 代理设置，证书与日志）
- Cline 文档：[OpenAI Compatible](https://docs.cline.bot/provider-config/openai-compatible)（Base URL 设置与 Connection Errors 排查）
- VS Code 文档：[Network Connections in Visual Studio Code](https://code.visualstudio.com/docs/setup/network)（代理支持、`http.proxy` 适用范围、证书处理）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cline-relay-connection-timeout-proxy-certificate-fix&utm_content=footer)，在「令牌」页创建 Key 后按接入教程在 Cline 里填写。

## 同专题文章

- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-stream-stall-tool-call-fix/)
- [n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)
- [n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

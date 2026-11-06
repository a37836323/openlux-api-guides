---
layout: default
title: "Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查"
description: "Continue 接中转 API 报 fetch failed、unable to verify the first certificate 或 401 时，按官方文档查日志、用 requestOptions.caBundlePath 指定 CA 证书、配置 VS Code 代理或 requestOptions.proxy，并用 .env 解决 IDE 读不到 secrets 中 Key 的问题。"
permalink: /news/continue-relay-fetch-failed-certificate-401-fix/
date: 2026-11-06
---

> 更新日期：2026-11-06 · 一手来源：[Continue 官方文档](https://docs.continue.dev/troubleshooting)

# Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查

Continue 接中转 API 后发消息就报错，先看报错属于哪一类：`fetch failed` 后面跟着 `unable to verify the first certificate`、`self signed certificate in certificate chain` 这类字样的，是 HTTPS 证书链校验失败，按 [Continue 官方排错文档](https://docs.continue.dev/troubleshooting)在这条模型的 `requestOptions.caBundlePath` 里指定 CA 证书；请求压根出不去的，查 VS Code 的代理设置或 `requestOptions.proxy`；能连上但返回 401 的，多半是 Key 没被带上，尤其是用 secrets 引用 Key、却只在终端里 `export` 了变量的情况，官方写明 IDE 扩展读不到 shell 环境变量。

本文适用于在 VS Code 或 JetBrains 里用 Continue 扩展、已经按 OpenAI 兼容方式（`provider: openai` 加 `apiBase`）接了中转的读者，以 OpenLux 为例。还没配置的，先看本站的 [Continue 接入中转 API 教程](https://a37836323.github.io/openlux-api-guides/news/continue-relay-api-openai-compatible-setup/)。设置项名称以撰文时的 Continue 官方文档为准。

## 先按报错对号入座

| 报错或现象 | 大概率原因 | 先看哪一节 |
|---|---|---|
| `fetch failed`，并带 `unable to verify the first certificate`、`self signed certificate in certificate chain`、`certificate verify failed` 或 `CERT_UNTRUSTED` | 证书链校验失败，常见于公司代理、私有 CA | 证书错误 |
| 只有 `fetch failed`、连不上、一直等到超时 | 网络出不去，或代理没配对 | 代理设置 |
| 返回 401 | Key 填错、有空格，或 secrets 没取到值 | 401：Key 没被带上 |
| 改了 `config.yaml` 没反应 | 配置没重新加载，或改错了文件 | 改了配置不生效 |
| 能聊天，但 Agent 模式不可用、不调用工具 | Continue 没识别出这个模型支持工具调用 | Agent 模式与工具调用 |

官方对第一行的解释是：出现这些证书错误，说明**地址是能连到的**，只是 TLS 证书链没法验证。所以证书错误和「连不上」是两回事，不要混着排查。

## 第一步：先从日志里拿到完整报错

聊天框里显示的报错往往不全。[官方排错文档](https://docs.continue.dev/troubleshooting)给了三个看日志的地方：

- **VS Code 控制台**：按 `Ctrl+Shift+P`（macOS 为 `Cmd+Shift+P`），运行 `Developer: Toggle Developer Tools`，切到 `Console` 标签；想看更细的，把「Default levels」下拉改成「Verbose」。
- **VS Code 的 Continue Console**：打开设置，勾选「Continue: Enable Console」，重新加载窗口，再从命令面板运行「Continue: Focus on Continue Console View」，可以看到发给模型的提示词日志。
- **JetBrains**：打开 `~/.continue/logs/core.log`，最新的记录在文件末尾。

拿到报错后先确认失败的主机名是不是 `api.openlux.ai`，以及请求的是哪个路径。官方建议复现一次，确认到底是哪个主机名失败，再往下查。

## 证书错误：用 caBundlePath 指定 CA 证书

官方说明，这类错误通常来自自建模型服务、企业代理，或使用私有 CA、证书链不完整的内部地址。在公司网络里，出口代理会替换 HTTPS 证书时，就会碰到这种情况。官方给的修法是在**这条模型**下加 `requestOptions.caBundlePath`，指向根证书或中间证书的 PEM 文件：

```yaml
models:
  - name: OpenLux claude-sonnet-5-5
    provider: openai
    model: claude-sonnet-5-5
    apiBase: https://api.openlux.ai/v1
    apiKey: <你的 OpenLux Key>
    requestOptions:
      caBundlePath: /path/to/ca-chain.pem
```

几点按官方文档补充：

- `requestOptions` 是**模型级**属性，[config.yaml 参考](https://docs.continue.dev/reference)没有把它列为顶层字段。接了几条模型，就要在每条下面都写，官方 FAQ 的原话是加到 `models` 里的每一项。`caBundlePath` 也可以写成多个证书路径的数组。
- 公司要求双向 TLS（客户端证书）时，再加 `requestOptions.clientCertificate`，子字段是 `cert`（证书文件路径）、`key`（私钥文件路径）和可选的 `passphrase`。
- Windows 上证书装在系统证书库里的，官方提到 win-ca 扩展可能有帮助，但仍认为 `caBundlePath` 最可靠。
- `requestOptions.verifySsl: false` 会关掉证书校验，官方只把它当作**临时判断**是不是证书问题的手段，并明确写了正常使用时不要一直关着。

找证书的步骤，官方给的是 curl 加 openssl，换成 OpenLux 的地址就是：

```bash
curl -v https://api.openlux.ai/v1/models
openssl s_client -showcerts -connect api.openlux.ai:443 -servername api.openlux.ai </dev/null
```

从输出里把需要的根证书或中间证书存成 PEM 文件，填进 `caBundlePath`，再用 `curl --cacert /path/to/ca-chain.pem https://api.openlux.ai/v1/models` 确认。这里不带 Key 返回 401 是正常的，说明 TLS 已经握手成功、请求到了服务端。

## 代理设置：VS Code 的 Proxy Support 和 requestOptions.proxy

如果报错只有 `fetch failed`、没有证书字样，或者一直等到超时，先确认这台电脑能不能直接访问 `https://api.openlux.ai/v1/models`。需要走代理时，有两个地方可以配：

| 位置 | 官方说明 | 什么时候用 |
|---|---|---|
| VS Code 设置里的「Proxy Support」 | 官方 FAQ：只要它不是 `off`，VS Code 就会自己把请求转发到代理 | 编辑器已经配了全局代理 |
| 模型下的 `requestOptions.proxy` | 「Proxy URL for HTTP requests」 | 只想让这条模型走指定代理 |
| 模型下的 `requestOptions.noProxy` | 不走代理的主机名列表 | 内网地址需要直连 |
| 模型下的 `requestOptions.timeout` | 每次请求模型的超时时间 | 网络慢、回复长时 |

官方文档没有写 `timeout` 的单位，本文不给具体数值，改之前先在日志里看清是不是超时。有的代理会替换 HTTPS 证书，配完代理后如果出现上一节的证书错误，两节要一起处理。

## 401：Key 没被带上

OpenLux 在 Key 错误或没带 Key 时都返回 401。在 Continue 里常见三种原因：

1. **直接写在 `apiKey` 里，但复制错了**：多了空格、少了字符，或者 Key 已经在控制台删掉。回 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）重新复制。
2. **用 secrets 引用，但只在终端里设了环境变量**：[官方 FAQ](https://docs.continue.dev/faqs) 的「Local Config」一节给了用 secrets 引用 Key 的写法：`apiKey:` 后面写 `secrets.变量名`，外面用 `$` 加两层花括号包住（原样写法见官方 FAQ，变量名可以自己起，例如 `OPENLUX_API_KEY`），并写明 **VS Code、JetBrains 扩展读不到 shell 里的环境变量**，进程环境变量只对 Continue CLI 有效。在 IDE 里用，要把变量写进 `.env` 文件。
3. **`.env` 写法不对**：官方要求 dotenv 格式、值不要加引号、改完后重启 IDE。

官方列出的 `.env` 查找顺序是：

| 顺序 | 文件位置 |
|---|---|
| 1 | `<工作区根目录>/.env` |
| 2 | `<工作区根目录>/.continue/.env` |
| 3 | `~/.continue/.env` |
| 4 | 进程环境变量（仅 CLI） |

例如在 `~/.continue/.env` 里写一行 `OPENLUX_API_KEY=你的Key`，不要加引号。官方提醒不要把 `.env` 提交到代码仓库；放在工作区根目录的，记得加进 `.gitignore`。

## 改了配置不生效

- 官方 FAQ 的做法是在命令面板运行「Reload Window」，重新加载窗口。
- 确认改的是 Continue 正在用的那份配置：按[官方配置文档](https://docs.continue.dev/customize/deep-dives/configuration)，本地用户级配置在 `~/.continue/config.yaml`（Windows 为 `%USERPROFILE%\.continue\config.yaml`），也可以打开聊天输入框右上方的配置下拉菜单，点「Local Config」旁的齿轮图标打开。
- 改了 `.env` 要按官方要求重启 IDE。
- 实在乱了，官方说明扩展的数据都在 `~/.continue` 下，可以删掉这个目录再卸载重装来彻底重置。删之前先备份里面的 `config.yaml`。

## Agent 模式与工具调用

能正常聊天、但 Agent 模式用不了或模型从不调用工具，官方 FAQ 归因为模型能力配置。Continue 按服务商和模型名自动识别能力，[能力配置文档](https://docs.continue.dev/customize/deep-dives/model-capabilities)写明这种识别不一定覆盖自定义地址和新模型，并点名代理服务可能改变模型能力。处理办法：

- 在这条模型下加 `capabilities: [tool_use]`，Agent 模式需要它；要传图片再加 `image_input`。
- 官方同时强调模型本身得真的支持工具调用。OpenLux 上每个模型支持哪些接口，看价格接口 `https://www.openlux.ai/api/pricing_new` 里的 `supported_endpoint_types`；工具调用经中转是否完整可用，本文没有实测，以自己的测试结果为准。
- 官方 FAQ 举过一个例子：经 OpenRouter 调用不支持函数调用的模型时，会返回 `HTTP 404 Not Found`。所以加了 `tool_use` 之后反而报错的，先换一个确定支持工具调用的模型再试。

## 最后用 curl 确认地址和 Key

各项改完后，在同一台电脑的终端里请求一次模型列表（`$OPENLUX_API_KEY` 换成你的 Key，不要贴进截图或聊天）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明网络、证书、地址和 Key 都没问题，剩下的就在 Continue 的配置里；返回 401 说明 Key 不对；连不上或报证书错误，回到前两节。最终以 Continue 里选中这条模型、发一条消息能正常返回为准。

## 参考资料

- Continue 文档：[Troubleshooting](https://docs.continue.dev/troubleshooting)（日志位置、SSL 证书错误的诊断步骤）
- Continue 文档：[FAQs](https://docs.continue.dev/faqs)（证书、VS Code 代理、secrets 与 `.env`、Reload Window、Agent 模式）
- Continue 文档：[config.yaml Reference](https://docs.continue.dev/reference)（`requestOptions` 各字段、`capabilities`）
- Continue 文档：[Model Capabilities](https://docs.continue.dev/customize/deep-dives/model-capabilities)（能力自动识别与手动添加）
- Continue 文档：[Configuration](https://docs.continue.dev/customize/deep-dives/configuration)（本地 config.yaml 位置与打开方式）
- Continue 文档：[OpenAI 配置](https://docs.continue.dev/customize/model-providers/top-level/openai)（OpenAI 兼容服务改 `apiBase`）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=continue-relay-fetch-failed-certificate-401-fix&utm_content=footer)，在「令牌」页创建 Key 后写进 Continue。

## 同专题文章

- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)
- [Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-stream-stall-tool-call-fix/)
- [n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)
- [n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)
- [Dify 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-api-openai-compatible-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

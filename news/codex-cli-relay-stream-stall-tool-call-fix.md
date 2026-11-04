---
layout: default
title: "Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查"
description: "Codex CLI 接中转后文字出来却一直转圈、最后报流中断，或第一轮正常、第二轮和工具调用出错时，按 Codex 官方网关兼容要求逐项排查：Responses 端点、response.completed 事件、工具调用结果回传、模型名与模型目录，并给出 curl 流式自测方法。"
permalink: /news/codex-cli-relay-stream-stall-tool-call-fix/
date: 2026-11-04
---

> 更新日期：2026-11-04 · 一手来源：[OpenAI Codex 文档：Gateway compatibility requirements](https://developers.openai.com/codex/enterprise/gateway-compatibility)

# Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查

先说结论：Codex CLI 接中转，能回第一句话不代表就接通了。OpenAI 官方的 Codex 文档 [Gateway compatibility requirements](https://developers.openai.com/codex/enterprise/gateway-compatibility) 写明，网关必须接受 `POST /v1/responses`、把流式事件逐条转发并带上最后的 `response.completed`、在后续轮次里接收之前的消息和工具调用结果，并且「能用 Chat Completions 或 Anthropic Messages 不等于兼容 Responses」。所以「字出来了但一直转圈」「第一轮正常、第二轮或调工具就报错」，多数要按这几条逐项查。

本文适用于已经在 `~/.codex/config.toml` 里配好自定义提供方、能发出请求的 Codex CLI 用户。还没配的，先看本站的 [Codex CLI 接入中转教程](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-api-config-toml-setup/)。本文不保证任何中转（包括 OpenLux）满足官方全部要求，下面给的是你自己可以做的检查步骤。

## 先对号入座：现象和该查的方向

下表左两列来自官方 [Connect to a gateway](https://developers.openai.com/codex/enterprise/connect-to-a-gateway) 的排错表，右列是本文对应的小节。

| 现象 | 官方建议先查 | 本文小节 |
|---|---|---|
| 预期的提供方没生效 | 顶层配置项是不是写进了提供方的表里 | 第一类 |
| API Key 鉴权失败 | 存令牌的环境变量有没有传到 Codex 进程 | 第一类 |
| 提示模型找不到 | 模型名是否正确，网关有没有这个模型的路由 | 第一类、第四类 |
| 模型能力和预期不一样 | 模型目录信息和背后的实际模型是否一致 | 第四类 |
| 流式卡住，或后续轮次失败 | 代理是否缓冲，有没有最后的 `response.completed` 事件 | 第二类、第三类 |

## 第一类：一句都回不了

这一类和接入配置有关，按官方说法逐条核对：

- **顶层配置写错位置**：官方要求 `model`、`model_provider` 等顶层项写在第一个 `[...]` 表头之前。写在 `[model_providers.xxx]` 下面，就成了这张表的字段，提供方不会生效。
- **配置写在项目目录里**：[Advanced Configuration](https://developers.openai.com/codex/config-advanced) 写明项目里的 `.codex/config.toml` 会忽略 `model_provider`、`model_providers`、`openai_base_url`，启动时会打印警告，要写进用户级 `~/.codex/config.toml`（Windows 为 `%USERPROFILE%\.codex\config.toml`）。
- **环境变量没传到进程**：官方提醒在终端里设置的变量，从桌面启动的应用不一定拿得到。CLI 要在导出变量的同一个终端里启动 `codex`。
- **自查命令**：官方建议先查看当前选用的 profile 并运行 `codex doctor`；进入 Codex 后用 `/status` 看当前的模型和提供方是不是你配的那个。

## 第二类：文字出来了，但一直转圈或最后报流中断

官方对流式的要求有四条：逐条转发 SSE 事件、不要把整段回答攒完再发；保留事件类型和内容，包括成功结束时的 `response.completed`；把错误和失败事件也转发出来，让客户端分得清「失败了」和「卡住了」；负载均衡和反向代理这一路也要验证。官方原话是只有文字、没有完整结束的流是不够的。

所以要分清两种情况：

1. **中转本身没有把流走完**：用下一节的 curl 测，看最后有没有 `response.completed`。
2. **你自己在中间加了代理**：比如公司代理或自建反向代理，按官方要求整条链路都要测。curl 直连中转正常、经过代理就卡住，问题在代理的缓冲或超时。

Codex 这边相关的配置项有三个（[Configuration Reference](https://developers.openai.com/codex/config-reference)），写在提供方表里：`stream_idle_timeout_ms` 是流式空闲超时，默认 300000 毫秒；`stream_max_retries` 是流式中断重试次数，默认 5；`request_max_retries` 是 HTTP 请求重试次数，默认 4。这几个参数针对的是中断和空闲超时；如果流里本来就没有 `response.completed`，应先按上面的要求查中转或代理，不要只靠调参数。

## 用 curl 单独测一次 Responses 流式

OpenAI [流式文档](https://developers.openai.com/api/docs/guides/streaming-responses) 写明，在 Responses 请求里设 `stream` 为 true 就会通过 SSE 返回事件，常见事件有 `response.created`、`response.output_text.delta`、`response.completed` 和 `error`。接 OpenLux 时 Responses 入口是 `https://api.openlux.ai/v1`，实际路径是 `/v1/responses`：

```bash
export OPENLUX_API_KEY=你的OpenLux令牌
curl -N https://api.openlux.ai/v1/responses \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-6-sol","input":"Reply with exactly: gateway-ok","stream":true}'
```

怎么看结果：

- 先看到 `response.created`，接着 `response.output_text.delta` 一条条出来，最后是 `response.completed`：这一段是通的。
- 内容一次性整段出来：可能是中间有缓冲，对应官方「不要攒完再发」那条。
- 有内容但没有 `response.completed`，或卡住直到超时：对应官方「只有文字、没有完整结束的流不够」。
- 返回 `401`：令牌不对或没带上，回 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）重新复制。
- 返回 `404`：核对请求地址是不是 `https://api.openlux.ai/v1/responses`。在 Codex 里遇到 404，同样检查 `base_url` 是否为 `https://api.openlux.ai/v1`，没有多写或少写一层 `/v1`。

## 第三类：第一轮正常，第二轮或调用工具后出错

官方对多轮和工具调用的要求是：网关要接收下一轮需要的之前消息、工具调用和工具结果；函数调用项和对应的 `function_call_output` 要原样保留，包括把两者对上的标识；整个闭环是 Codex 收到调用、执行工具、提交结果、再拿到最终回答。官方还特别说明，网关接受了某个请求字段，不代表背后的模型真的支持这个能力。

接 OpenLux 时，先排除一个原因：**选了不支持 Responses 的模型**。Codex 的 `wire_api` 只支持 `responses`，模型必须走得通 `/v1/responses`。OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里每个模型的 `supported_endpoint_types` 列出它支持的协议，含 `openai-response` 的才适合配进 Codex：

| 模型（2026-11-04 价格接口） | supported_endpoint_types | 能否配进 Codex |
|---|---|---|
| `gpt-6-sol`、`gpt-6.1-sol`、`gpt-5.6-sol` | `openai`、`openai-response` | 可以 |
| `gpt-6-luna`、`gpt-6-astra` | `openai-response`、`openai` | 可以 |
| `claude-opus-5-5`、`claude-sonnet-5-5` | `anthropic`、`openai` | 不适合 |
| `deepseek-v4-pro` | `openai`、`anthropic` | 不适合 |
| `gemini-3.8-flash` | `gemini`、`openai` | 不适合 |

列表会变，以你查询时的价格接口为准。验证方法按官方 Connect to a gateway 的思路：先发 `Reply with exactly: gateway-ok`，回 `gateway-ok` 再往下；然后让 Codex 做一个需要执行命令的小任务（比如列出当前目录的文件），如果弹出执行确认就批准，看它能否执行完并给出最终回答；最后再追问一句，确认第二轮也正常。

## 第四类：能用，但推理档位、上下文或联网表现不对

- **模型名要用 Codex 认识的名字**：官方要求每个模型名都对应到预期的上游模型，并且要用 Codex 能识别的准确名称。查法是运行 `codex --version`，到对应的 `rust-v版本号` 标签下看模型条目的 `slug`。
- **自定义提供方拿不到内置调整**：官方说明普通网关连接不会自动获得 Codex 内置提供方的模型信息调整；目录信息只影响客户端行为，不会给模型加能力。
- **API Key 方式默认不拉远程模型目录**：[Model catalogs](https://developers.openai.com/codex/model-catalogs) 写明只靠 API Key 不会触发远程目录发现，需要在提供方表里设 `model_catalog_url`；设了 `model_catalog_json` 本地文件时以本地文件为准、不再远程拉取。
- **别问模型「你是谁」**：官方明确说不要靠问模型名字来确认路由，能回复也不代表是哪条路由处理的；要以网关侧的记录为准。
- **联网搜索**：官方连接示例在首次测试时设了 `web_search = "disabled"`；Advanced Configuration 写明 `supports_standalone_web_search` 对自定义提供方默认是 false，单开它也不会启用功能。先关掉联网把基本对话、工具调用测通，再单独处理联网。

## 求助时带上什么

官方建议求助时附上去掉令牌和敏感提示词的报错原文。可以一起带上：`codex --version` 的输出、`/status` 里的模型和提供方、上面 curl 测试最后几行事件、出错发生在第几轮以及是不是刚调用过工具。会话记录默认在 `~/.codex/sessions`，分享前先检查里面有没有敏感内容。

还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=codex-cli-relay-stream-stall-tool-call-fix&utm_content=footer)。

## 同专题文章

- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)
- [n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)
- [n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)
- [Dify 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-api-openai-compatible-setup/)
- [LobeHub（LobeChat）怎么接入 OpenAI 兼容 / Claude 中转 API：代理地址、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/lobehub-lobechat-relay-api-proxy-url-setup/)
- [VS Code 怎么接入 OpenAI 兼容 / Claude 中转 API：Custom Endpoint、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/vscode-copilot-byok-custom-endpoint-relay-api-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

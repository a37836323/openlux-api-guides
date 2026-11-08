---
layout: default
title: "Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查"
description: "Dify 用 OpenAI-API-compatible 插件接中转后，工作流 LLM 节点报 InvokeConnectionError、InvokeRateLimitError、InvokeServerUnavailableError、QuotaExceededError、LLMModeRequiredError 或超时时，按 Dify 官方错误类型、处理错误、LLM 节点和环境变量文档，说明各错误含义、哪些能重试、重试与失败分支怎么设、迭代节点错误模式和自部署超时变量。"
permalink: /news/dify-relay-llm-node-invoke-error-retry-fix/
date: 2026-11-09
---

> 更新日期：2026-11-09 · 一手来源：[Dify Docs](https://docs.dify.ai/zh/self-host/use-dify/debug/error-type)

# Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查

模型供应商已经保存成功，工作流跑着跑着 LLM 节点却失败了，先看报错里的错误类型。Dify 官方 [错误类型](https://docs.dify.ai/zh/self-host/use-dify/debug/error-type) 文档把它们分成两层：一层是 **LLM 节点自身的配置错误**（如 `LLMModeRequiredError`、`VariableNotFoundError`），改节点配置就好；另一层是 **系统级错误**（`InvokeConnectionError`、`InvokeServerUnavailableError`、`InvokeRateLimitError`、`QuotaExceededError`），问题出在 Dify 到模型服务这一段。前者重试没用，后者里连接失败、限流和服务暂时不可用可以靠节点的「重试」和「失败分支」兜住，配额超限则要去补额度。

本文适用于已按 [Dify 接中转 API 教程](https://a37836323.github.io/openlux-api-guides/news/dify-relay-api-openai-compatible-setup/) 用 OpenAI-API-compatible 插件接好中转、在工作流或 Chatflow 里调用模型的读者。保存模型时就报 401、404 属于接入配置问题，请看那篇。文中的环境变量只适用于自部署版，Dify 云版无法修改。

## 先看报错属于哪一类

下表的「官方含义」一列逐条来自 Dify 官方错误类型文档，「先做什么」是据此给出的排查顺序：

| 错误类型 | 官方含义 | 重试有没有用 | 先做什么 |
|---|---|---|---|
| `LLMModeRequiredError` | 所选模型未配置有效的 API 凭据 | 没用 | 到「集成」→「模型供应商」检查这个模型的 Key |
| `ModelNotExistError` | LLM 节点配置中未选择模型 | 没用 | 在节点里重新选模型 |
| `VariableNotFoundError` | 提示词引用了工作流里不存在的变量 | 没用 | 核对提示词里双花括号引用的变量名拼写和上游节点 |
| `NoPromptFoundError` | 提示词字段完全为空 | 没用 | 补上提示词 |
| `InvokeConnectionError` | 与外部服务的网络连接失败 | 偶发时有用 | 在运行 Dify 的服务器上测通中转地址 |
| `InvokeServerUnavailableError` | 外部服务返回 503 或暂时停机 | 有用 | 开节点重试，过一会儿再跑 |
| `InvokeRateLimitError` | 达到 API 或模型供应商的速率限制 | 拉开间隔才有用 | 开重试并加大间隔，降低同时调用数 |
| `QuotaExceededError` | 使用配额已超限 | 没用 | 到提供 Key 的服务处核对额度 |

前四种都是工作流配置问题，改完再跑即可，下面主要讲后四种。

## 第一步：配置类错误先改掉

- **`LLMModeRequiredError`**：模型对应的凭据无效，检查「模型供应商」里这个模型的 Key 是否被删除或改动过。官方 [模型供应商](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers) 文档写明：自定义模型依赖它自己的 Key，删掉它仅有的一个 Key 会连模型一起删除。重新配置 Key 后再跑。
- **`ModelNotExistError`**：节点里没有选中模型。用「环境变量」统一管理模型时，要确认绑定的 LLM 类型变量还指向存在的模型。
- **结构化输出失败**：官方 [LLM 节点](https://docs.dify.ai/zh/self-host/use-dify/nodes/llm) 文档说明，「结构化输出」旁显示「模型不支持」时，Dify 会把 JSON Schema 放进提示词，但模型的回复仍可能不符合 Schema，导致节点运行失败。需要稳定输出时，换一个没有这个提示的模型。

## 第二步：InvokeConnectionError，先确认服务器到中转地址是通的

这个错误表示 Dify 连不上模型服务。自部署时，请求是从运行 Dify 的服务器发出的，所以要在**那台服务器**上测，而不是在自己电脑上：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

- 能列出模型：地址和 Key 都没问题，偶发的连接失败交给第三步的重试处理。
- 连接超时或无法解析域名：是服务器网络、防火墙或出口代理的问题，先在服务器上解决。
- 返回 401：Key 错了或没带上，回到模型供应商里重新填写。

另外，官方 Docker 排错文档提醒：容器里的 `127.0.0.1` 指向容器自己，访问宿主机上的服务要填宿主机的局域网 IP。如果你在 Dify 和中转之间又加了一层本机转发，地址不要写 `127.0.0.1`。

## 第三步：限流和服务暂时不可用，在 LLM 节点打开重试

`InvokeRateLimitError` 和 `InvokeServerUnavailableError` 多数是暂时的。官方 LLM 节点文档的「错误处理」一节写明，可以为失败的 LLM 调用设置**最大重试次数、重试间隔和退避乘数**。建议这样用：

1. 在 LLM 节点的错误处理设置里打开重试，设置最大重试次数和重试间隔。
2. 限流时，间隔太短的重试很可能再次撞上限流，所以把重试间隔设长一些，并用退避乘数让每次等待逐步变长。
3. 一个工作流里同时有很多 LLM 调用时，也可以减少同时发出的请求数，降低撞上限流的概率。

`QuotaExceededError` 表示配额已用完，重试只会继续失败，要去提供这个 Key 的服务处核对额度或更换 Key。

## 第四步：重试也失败时，用默认值或失败分支兜底

官方 [处理错误](https://docs.dify.ai/zh/self-host/use-dify/build/predefined-error-handling-logic) 文档说明，LLM、HTTP、代码和工具节点失败时有三种行为可选：

| 选项 | 节点失败后 | 适合场景 |
|---|---|---|
| 无（默认） | 整个工作流停止，返回原始错误消息 | 调试阶段，想看清哪里出错 |
| 默认值 | 用你设定的备用值代替输出，工作流继续 | 给用户一句「暂时不可用，请稍后再试」 |
| 失败分支 | 转到单独的处理流程（橙色分支） | 发告警、记日志、改用备用模型 |

使用默认值或失败分支时，下游可以读到两个变量：`error_type`（错误类型）和 `error_message`（错误详情）。可以按 `error_type` 决定给用户看什么，或者在失败分支里接一个用另一个模型的 LLM 节点作为备用。注意默认值的类型必须和节点输出类型一致，输出是字符串，默认值也要是字符串。

调试时建议先保持「无」，拿到完整的原始错误消息、确认是哪一类错误后，再换成默认值或失败分支。

## 第五步：迭代和循环里批量调用模型时

批量处理时一条失败可能拖垮整批。官方文档写明两类节点的行为不同：

- **循环节点**：任一子节点失败就立即停止，整个循环终止并返回错误。
- **迭代节点**：可以选错误处理模式。`terminated`（默认）遇到失败立即停止；`continue-on-error` 跳过失败项继续，失败项在输出数组里为 `null`；`remove-abnormal-output` 继续处理，但最终输出里去掉失败项，输出数组会比输入短。

用后两种模式时，下游要能处理 `null` 或数量变少的结果，并单独记录哪些条目失败、事后补跑。

## 自部署版：这几个时间上限要一起看

长文本生成「卡住」或中途被终止时，可以对照官方 [环境变量](https://docs.dify.ai/en/self-host/deploy/configuration/environments) 文档检查下面几项（默认值以文档为准）：

| 变量 | 默认值 | 官方说明 |
|---|---|---|
| `TEXT_GENERATION_TIMEOUT_MS` | `60000` | 前端流式生成界面的超时：流停顿超过这个时间，界面会暂停渲染 |
| `PLUGIN_DAEMON_TIMEOUT` | `600.0` | API 侧对插件守护进程所有请求（安装、执行、列表）的超时，单位秒 |
| `PLUGIN_MAX_EXECUTION_TIMEOUT` | `600` | 插件守护进程侧的插件执行超时，单位秒，应与 `PLUGIN_DAEMON_TIMEOUT` 保持一致 |
| `WORKFLOW_MAX_EXECUTION_TIME` | `3600` | 单次工作流运行的最长时间，超过即终止 |
| `APP_MAX_EXECUTION_TIME` | `3600` | 应用执行的最长时间，与上一项要一起调大 |

说明两点：一是 Dify 的常见问题页把 `TEXT_GENERATION_TIMEOUT_MS` 写成「控制每个节点的运行时间」，环境变量文档则写的是前端流式界面超时，两处说法不同。如果是界面不动了、后台还在生成，先看这一项。二是 OpenAI-API-compatible 是从插件市场安装的插件，单次调用要很久时，插件的两项执行超时可能先到；需要调整时按官方说明两项保持一致。改完 `.env` 后按官方部署说明重启服务生效。

## 怎么确认已经修好

1. 在 Dify 服务器上，上面的 curl 能列出模型。
2. 单独运行出错的 LLM 节点，能正常返回结果。
3. 设好兜底后，再遇到上面几类错误时，工作流不再整体停止，而是返回你设定的默认值，或执行失败分支里的步骤；下游能读到 `error_type` 和 `error_message`。

## 参考资料

- Dify 官方文档：[错误类型](https://docs.dify.ai/zh/self-host/use-dify/debug/error-type)（LLM 节点错误与系统级错误）
- Dify 官方文档：[处理错误](https://docs.dify.ai/zh/self-host/use-dify/build/predefined-error-handling-logic)（无、默认值、失败分支，迭代与循环，`error_type` / `error_message`）
- Dify 官方文档：[大语言模型节点](https://docs.dify.ai/zh/self-host/use-dify/nodes/llm)（错误处理与重试、结构化输出）
- Dify 官方文档：[模型供应商](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)、[常见问题](https://docs.dify.ai/zh/self-host/deploy/troubleshooting/common-issues)、[Docker 问题](https://docs.dify.ai/en/self-host/deploy/troubleshooting/docker-issues)、[环境变量](https://docs.dify.ai/en/self-host/deploy/configuration/environments)

还没有中转 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=dify-relay-llm-node-invoke-error-retry-fix&utm_content=footer)，在「令牌」页创建 Key 后按接入教程配进 Dify。

## 同专题文章

- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)
- [Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-stream-stall-tool-call-fix/)
- [n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)
- [n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

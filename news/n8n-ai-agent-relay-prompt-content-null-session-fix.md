---
layout: default
title: "n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查"
description: "n8n 用 AI Agent 节点接 OpenAI 兼容中转 API 时，报 400 Invalid value for 'content': expected a string, got null、No prompt specified、A Chat Model sub-node must be connected、Error in sub-node Simple Memory 或 No sessionId，按 n8n 官方常见问题逐项检查 Prompt 来源、Chat Model 子节点、工具、Simple Memory 与会话 ID，并给出验证步骤。"
permalink: /news/n8n-ai-agent-relay-prompt-content-null-session-fix/
date: 2026-11-14
---

> 更新日期：2026-11-14 · 一手来源：[n8n 官方文档](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/common-issues/)

# n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查

n8n 的 OpenAI Chat Model 已经按中转地址接通，单独测试也能回话，但放进 AI Agent 节点后却报 `400 Invalid value for 'content': expected a string, got null`、`No prompt specified`、`A Chat Model sub-node must be connected`，或者记忆节点报 `No sessionId`。按 n8n 官方 [AI Agent 常见问题页](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/common-issues/) 的说明，这几类报错的原因都在工作流本身：Prompt 取到了空值、Prompt 来源选错、没接 Chat Model 子节点、记忆节点版本旧或拿不到会话 ID。所以先按下面的顺序检查节点设置，不要一上来就换 Key 或改 Base URL。

本文适用于自建或云端 n8n 中，用 AI Agent 节点加 OpenAI Chat Model 子节点调用 OpenAI 兼容中转 API 的读者。还没接通（401、404、模型列表拉不出来）的，先看 [n8n 接入中转 API 的设置篇](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)；如果报错出在 OpenAI Chat Model 子节点、提示 `Bad request - please check your parameters`，看 [n8n OpenAI Chat Model 报错排查篇](https://a37836323.github.io/openlux-api-guides/news/n8n-openai-chat-model-bad-request-error-fix/)。参数名称以撰文时的 n8n 官方文档为准，界面文字可能随版本变化。

## 先按报错对号入座

| 报错或现象 | 官方说明的原因 | 怎么改 |
|---|---|---|
| `Internal error` / `Error: 400 Invalid value for 'content': expected a string, got null.` | Prompt 输入里有 null | 检查 Prompt 表达式或上游的 `chatInput` 字段 |
| `No prompt specified` | Agent 在等上一个节点自动传入 Prompt，但没拿到 | 把 Prompt 改为 Define below，自己写提示内容 |
| `A Chat Model sub-node must be connected` | AI Agent 节点没有接 Chat Model | 点 Chat Model 连接口，接上配好中转凭据的 OpenAI Chat Model |
| `Error in sub-node Simple Memory` | 工作流或模板里的 Simple Memory 是旧版本（原名 Window Buffer Memory） | 删掉 Simple Memory 节点后重新添加 |
| 报错含 `No sessionId` | 记忆节点拿不到会话 ID | 检查 Chat 触发器输出里有没有 `sessionId`，没有就手动指定 |
| 想让多个记忆节点分开存，结果记忆混在一起 | 多个 Simple Memory 默认共用同一个记忆实例 | 给不同记忆节点设不同的会话 ID |

以下逐项说明。每改完一处，重新执行一次工作流，看报错是否变化。

## 400 Invalid value for 'content'：Prompt 取到了空值

官方给出的完整报错形如：

```
Internal error
Error: 400 Invalid value for 'content': expected a string, got null.
```

这表示 Agent 发给模型的用户消息内容是 null。官方列了两种情况：

1. **Prompt 设为 Define below**：Prompt（User Message）里的表达式没有取到值，比如字段名拼错，或这条数据里该字段为空。修法是让表达式引用真实存在的字段，并确认它解析出的是有效文本，而不是 null。
2. **Prompt 设为从 Chat 触发器自动获取**：上游传来的数据里有 null。修法是去掉输入节点 `chatInput` 字段里的空值。

经中转转到不同上游模型时，报错措辞可能和上面不完全相同；只要报错指向 `content` 为空或缺失，就按这两种情况查。官方给出的原因都在 Prompt 输入这一侧，所以先查 Prompt，不要先换模型或地址。

## No prompt specified：Prompt 来源选错了

AI Agent 的 Prompt 参数有两种取法。官方文档两处用词不同：常见问题页叫 **Connected Chat Trigger Node** 和 **Define below**，Tools Agent 页叫 **Take from previous node automatically** 和 **Define below**。以你界面上的选项为准。

- 选「自动从上一个节点获取」时，节点要求上一个节点输出名为 `chatInput` 的字段。通常配合 Chat Trigger（On Chat Message）使用。
- 选 **Define below** 时，在 **Prompt (User Message)** 里写固定文字或表达式。

官方说明，`No prompt specified` 出现在 Agent 等着上一个节点自动传入 Prompt 的时候，通常是在使用 Chat Trigger 时。另外，「自动获取」要求上一个节点输出 `chatInput` 字段，所以 Agent 前面不是 Chat Trigger 时（比如 Webhook 或定时触发），也要先确认上游有没有这个字段。

官方修法是把 Prompt 改为 **Define below**，再用表达式引用上游节点的输出字段，或直接写固定文字。改完后要确认表达式能取到值，否则会变成上一节的 400。

## A Chat Model sub-node must be connected：先接上模型

AI Agent 自己不调用模型，要靠 Chat Model 子节点。没有接模型就执行，会报这个错误。官方给的操作是：节点打开时，点界面底部的 **+ Chat Model** 按钮；节点关闭时，点节点下方的 **Chat Model +** 连接口，然后从列表里选模型节点。

接中转 API 时，选 **OpenAI Chat Model**（Tools Agent 文档列出的支持模型里有它），凭据里的 Base URL 填 `https://api.openlux.ai/v1`（只带一个 `/v1`），API Key 填在 OpenLux 控制台「令牌」页创建的 Key，模型填价格页里的在售 ID。

模型的接口类型也要和 **Use Responses API** 开关对上。以撰文时价格接口的 `supported_endpoint_types` 为例：

| 模型 ID | 支持的接口 | Use Responses API |
|---|---|---|
| gpt-6-luna、gpt-5.6-sol | openai、openai-response | 开或关都可以 |
| claude-sonnet-5-5 | anthropic、openai | 关闭 |
| gemini-3.8-flash | gemini、openai | 关闭 |
| qwen3.8-max | openai | 关闭 |

各模型支持哪些接口可能调整，以价格页为准。

## 工具和 Agent 版本：至少接一个工具

官方 AI Agent 页写明：**必须至少给 AI Agent 节点接一个工具子节点**。工具可以是 Call n8n Workflow、Code、HTTP Request、Calculator，或各类应用节点。

另外，AI Agent 的「Agent 类型」设置从 n8n 1.82.0 起已弃用，所有 AI Agent 节点都按 Tools Agent 工作；带这个设置的 v1 节点**将在 n8n 3.0 移除**。如果你复制的是老模板，里面还是 v1 节点，官方建议更新到最新版本。

Tools Agent 用的是 LangChain 的工具调用接口，所以所选模型要支持工具调用（function calling）。模型是否支持，以模型厂商文档为准。几个与此相关的选项：

- **Max Iterations**：模型最多运行几次来得出答案，默认 10。Agent 反复调用工具、迟迟不结束时，每一轮都会再调用一次模型，可以适当调小。
- **Return Intermediate Steps**：打开后在输出里带上 Agent 每一步做了什么，排查「为什么没调用工具」时很有用。
- **System Message**：在对话开始前发给 Agent 的说明，可以写清什么情况下该用哪个工具。

## Simple Memory 报错与 No sessionId

带记忆的对话型工作流，报错常出在 Simple Memory。官方说明了以下几点：

1. **Error in sub-node Simple Memory**：大多是工作流或模板里用的是旧版 Simple Memory（原名 Window Buffer Memory）。删掉这个节点再重新添加，就能保证是最新版本。
2. **No sessionId**：多数情况下 `sessionId` 会从 **On Chat Message** 触发器自动拿到。出现这个报错时，先看 Chat 触发器的输出里有没有 `sessionId`。如果不是用 On Chat Message 触发的，要手动管理会话 ID；测试时可以先用固定值（如 `my_test_session`），正式启用前改成真正的会话管理。
3. **多个记忆节点共用一份记忆**：工作流里有多个 Simple Memory 节点时，它们默认共用同一个记忆实例，用 Chat Memory Manager 覆盖全部消息这类操作时要小心。想分开，就给不同的记忆节点设不同的会话 ID。
4. **子节点里的表达式只取第一条数据**：官方提示，子节点处理多条输入时，表达式总是解析成第一条数据的值。如果用表达式设置会话键，批量处理多条数据时它们会落到同一个会话。
5. **队列模式（queue mode）不要用 Simple Memory**：n8n 以队列模式运行时，这个节点在已启用的生产工作流里不能正常工作，因为不能保证每次调用都落到同一个 worker。
6. **Chat 触发器的 Load Previous Session**：只要不选 Off，就必须把 Chat 触发器和 Agent 都接到记忆子节点上，官方建议两者接同一个记忆节点。

另外，Simple Memory 的 **Context Window Length** 表示带上多少轮之前的对话。轮数越多，每次发给模型的内容越长；如果模型报上下文超长，可以先调小这个值。

## 改完怎么验证

1. **先单独确认地址和 Key**：在能访问 n8n 所在网络的机器上执行

   ```
   curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的Key"
   ```

   能列出模型，说明地址和 Key 都对；返回 401 说明 Key 有误，先回设置篇处理。
2. **再测 Agent**：用 Chat 触发器的聊天窗口发一句简单的话，或手动执行工作流。AI Agent 节点输出里有模型回答，且没有上面几种报错，就算通过。
3. **测工具**：提一个必须用到工具才能回答的问题，打开 Return Intermediate Steps，在输出里确认 Agent 确实调用了工具。
4. **测记忆**：同一会话里连问两句，第二句引用第一句的内容，回答能接上就说明会话 ID 和记忆都正常。

还有一点：AI Agent 的 **Enable Streaming** 默认打开，但只有支持流式响应的触发器才能逐字输出，比如 Chat Trigger，或把 **Response Mode** 设为 **Streaming** 的 Webhook。用其他触发器时看不到逐字输出，属于这条限制。

## 参考资料

- n8n 文档：[AI Agent node common issues](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/common-issues/)（400 Invalid value for 'content'、Simple Memory 报错、A Chat Model sub-node must be connected、No prompt specified）
- n8n 文档：[AI Agent](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/)（至少接一个工具、Agent 类型弃用与 v1 移除）
- n8n 文档：[Tools Agent](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/tools-agent/)（Prompt 取法、支持的 Chat Model、Max Iterations、Return Intermediate Steps、Enable Streaming）
- n8n 文档：[Simple Memory](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.memorybufferwindow/) 与 [Simple Memory common issues](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.memorybufferwindow/common-issues/)（队列模式、Context Window Length、No sessionId、共用记忆实例）
- n8n 文档：[Chat Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.chattrigger/)（Load Previous Session 与记忆节点连接）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=n8n-ai-agent-relay-prompt-content-null-session-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤配置 n8n。

## 同专题文章

- [Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办](https://a37836323.github.io/openlux-api-guides/news/cline-cli-relay-api-auth-baseurl-setup/)
- [Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置](https://a37836323.github.io/openlux-api-guides/news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/)
- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)
- [VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查](https://a37836323.github.io/openlux-api-guides/news/vscode-byok-relay-model-not-showing-utility-model-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改"
description: "OpenAI Agent Builder 将于 2026-11-30 停用，ChatKit 继续可用。按官方弃用页、迁移指南、ChatKit 与自托管指南、Agents SDK 文档，说明导出 Agents SDK 代码或改建 Workspace Agent、ChatKit 从 workflow ID 改为自托管，以及换 OpenAI 兼容地址后 404、追踪 401、response_format 400 的改法。"
permalink: /news/agent-builder-shutdown-agents-sdk-chatkit-migration/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改

结论先说：OpenAI 在 2026-06-03 宣布弃用 Agent Builder，产品计划于 **2026-11-30 停用**；ChatKit 本身继续可用。官方给了两条迁移路：把工作流导出成 **Agents SDK** 代码放进自己的应用，或在 ChatGPT 里改建 **Workspace Agent**。如果你的网页聊天窗口是「ChatKit 前端 + Agent Builder 托管工作流」，后端那一半要在停用前换成自己的服务。

本文适合三类人：在 Agent Builder 里搭了工作流、要在月底前搬走的；用 ChatKit 嵌入聊天、会话里传了 `workflow` ID 的；搬到 Agents SDK 后想改用 OpenAI 兼容地址、结果报 404、401 或 400 的。

依据：OpenAI 官方 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[Migrate from Agent Builder](https://developers.openai.com/api/docs/guides/agent-builder/migrate-from-agent-builder)、[ChatKit 指南](https://developers.openai.com/api/docs/guides/chatkit)、[自托管 ChatKit 指南](https://developers.openai.com/api/docs/guides/custom-chatkit)，以及 Agents SDK 的 [模型文档](https://openai.github.io/openai-agents-python/models/) 和 [配置文档](https://openai.github.io/openai-agents-python/config/)。

## 一、哪些东西 11 月 30 日一起停

| 项目 | 时间 | 官方去向 |
|---|---|---|
| Agent Builder | 2026-11-30 停用 | Agents SDK 或 ChatGPT Workspace Agents；ChatKit 继续可用 |
| 可复用提示词（`v1/prompts` 与 prompt 对象） | 2026-11-30 停用 | 把提示词内容放进自己的代码 |
| Evals 平台 | 2026-10-31 起已有评测只读，2026-11-30 控制台和 API 停用 | 官方给的迁移方向是 Promptfoo |

三件事同一天到期，迁移时别把 Agent Builder 里的提示词搬进 prompt 对象，否则月底还要再搬一次。prompt 参数的改法见 [可复用提示词停用迁移](https://a37836323.github.io/openlux-api-guides/news/openai-reusable-prompt-object-shutdown-migration/)。

## 二、先判断你属于哪种情况

| 你现在的用法 | 停用后受影响的部分 | 本文对应小节 |
|---|---|---|
| 只在 Agent Builder 里调试、预览工作流 | 工作流本身 | 第三节导出 |
| 后端调用 `/v1/chatkit/sessions`，请求体里带 `"workflow": {"id": ...}` | 这个托管工作流 | 第三节 + 第四节 |
| 前端用 ChatKit，`apiURL` 指向你自己的服务 | 不依赖 Agent Builder，一般不受影响 | 无需迁移 |
| 想交给不写代码的同事维护 | 工作流本身 | 第三节 Workspace Agent |

ChatKit 指南写明：托管工作流这条路只留给已经在用的团队，过渡期内可以继续用；新项目和迁移都应改成自托管接入。官方没有写停用后带 `workflow` ID 的会话请求会返回什么错误，按「到期不可用」来排期即可。

## 三、导出工作流：Agents SDK 还是 Workspace Agent

导出步骤（来自官方迁移指南）：

1. 在 Agent Builder 打开工作流；
2. 点顶部导航的 **Code**；
3. 在代码对话框里选 **Agents SDK**；
4. 选 **TypeScript** 或 **Python**，把导出内容完整复制下来。

拿到代码后有两条路：

- **继续用 Agents SDK**：把代码放进自己的应用，安装并配置对应语言的 Agents SDK，在自己的运行环境里测试，然后部署。运行配置、工具、鉴权、权限和部署都要自己验证。
- **改建 Workspace Agent**：需要 ChatGPT Business、Enterprise 或 Edu 工作区和建 Agent 的权限。在 ChatGPT 新建 Workspace Agent，把导出代码贴进对话，请它转换，再逐项检查它提示需要修改的地方，点 **Preview** 用原工作流的典型输入对比结果，确认后再点 **Create**。

两点要心里有数：官方明确说导出**不会转换工作流图，也不保证每个行为原样保留**；确定性很强的工作流不一定能忠实地迁到 Workspace Agent。所以无论走哪条路，都要拿原工作流的真实输入逐条对比控制流、触发条件、工具调用和权限。

## 四、ChatKit 从托管工作流改成自托管

原来的接法是：你的服务端带 `OpenAI-Beta: chatkit_beta=v1` 头调用 `https://api.openai.com/v1/chatkit/sessions`，请求体传 `workflow` ID 和 `user`，拿到 `client_secret` 交给前端。

自托管 ChatKit 的接法（来自官方自托管指南）：

1. 安装 Python SDK：`pip install openai-chatkit`；
2. 继承 `ChatKitServer`，重写异步的 `respond` 方法：读取线程历史，交给 Agents SDK 的 `Runner.run_streamed` 运行，再把事件流回前端；
3. 用 Web 框架暴露一个接口（官方示例是 FastAPI 的 `/chatkit`），调用 `server.process(...)`，流式结果按 `text/event-stream` 返回；
4. 实现 `Store` 保存线程和消息（开发时可用内存存储，生产要持久化）；支持上传还要实现 `FileStore`；
5. 前端 ChatKit 的 `apiURL` 改成你自己的接口地址，需要带鉴权头时用 `fetch` 选项。

第 2 步里运行的 Agent，正好可以用第三节导出的 Agents SDK 代码。完整服务端说明见 [chatkit-python 服务端文档](https://github.com/openai/chatkit-python/blob/main/docs/server.md)。

## 五、换成 OpenAI 兼容地址后报错的对照表

搬到 Agents SDK 后，如果把模型请求改到其他 OpenAI 兼容地址，下面几种报错最常见，原因都写在 Agents SDK 文档里：

| 现象 | 原因 | 改法 |
|---|---|---|
| 模型请求报 404 | Agents SDK 默认走 Responses API，对方地址或该模型不支持 | 调 `set_default_openai_api("chat_completions")`，或给 Agent 用 `OpenAIChatCompletionsModel` |
| 模型能回答，但日志里追踪上传报 401 | 追踪默认上传到 OpenAI，需要 platform.openai.com 的 Key | `set_tracing_disabled(True)`；或 `use_for_tracing=False` 后用 `set_tracing_export_api_key` 单独配 OpenAI Key |
| 400，提示 `response_format.type` 只允许 `text`、`json_object` | 对方不支持 `json_schema` 结构化输出 | 换支持 JSON Schema 的模型，或去掉结构化输出并自行校验 |
| 改成 Chat Completions 后多轮上下文或提示词丢了 | 该路径会静默丢掉 `previous_response_id`、`conversation_id`、`prompt` 等 Responses 专有字段 | 用 `OpenAIProvider(use_responses=False, strict_feature_validation=True)` 让问题直接报错，再逐项改写 |
| 文件检索、网页搜索等托管工具或 `ToolSearchTool` 报错 | 很多兼容服务不提供托管文件检索和网页搜索；`ToolSearchTool` 等 Responses 专有工具功能在 Chat Completions 上会被拒绝 | 不要发送对方不支持的工具，改成自己实现的函数工具，或留在支持 Responses 的模型上 |

## 六、经 OpenLux 调用时怎么配

OpenLux 的 OpenAI 兼容地址是 `https://api.openlux.ai/v1`，Key 在控制台「令牌」页创建（`https://www.openlux.ai/console/token`）。每个模型支持哪些接口，看价格页或价格接口里的 `supported_endpoint_types`：标了 `openai-response` 的（如 GPT 系列）可以保持 Agents SDK 默认的 Responses；只标 `openai` 的（如 Claude、DeepSeek 经 OpenAI 兼容协议调用时）要切到 Chat Completions。按 Agents SDK 配置文档，Python 写法如下：

```python
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_default_openai_api, set_tracing_disabled

client = AsyncOpenAI(base_url="https://api.openlux.ai/v1", api_key="你的 OpenLux Key")
set_default_openai_client(client, use_for_tracing=False)
set_default_openai_api("chat_completions")  # 模型只支持 openai 时加这行
set_tracing_disabled(True)  # 或改用 set_tracing_export_api_key 配 OpenAI 的 Key
```

OpenLux 的 Key 不是 platform.openai.com 的 Key，不能用来上传追踪。导出代码里如果用了文件检索、网页搜索等托管工具，经中转能否使用没有官方保证，上线前请单独用最小请求验证；做不到就改成自己实现的函数工具。

## 七、改完怎么验证

1. 先确认地址和 Key：`curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的Key"` 能列出模型，说明两者都对；返回 401 `Invalid token` 是 Key 错或没带；
2. 用导出的 Agent 跑一次最小输入，确认有正常回答、没有 404；
3. 拿原工作流的 5～10 条真实输入，对比分支走向、工具调用和最终输出；
4. ChatKit 场景下，前端打开聊天窗口发消息，确认请求打到你自己的 `apiURL`，不再调用 `/v1/chatkit/sessions`；
5. 搜索代码库，确认没有残留的 `workflow` ID、prompt 对象 ID 和 Evals 调用。

成功标准：11 月 30 日前，生产环境不再依赖 Agent Builder 托管工作流，迁移后的 Agent 在真实输入上的表现与原工作流一致，日志里没有 404、追踪 401 之类的报错。

想用一个 Key 调用 GPT、Claude 等多家模型来跑迁移后的 Agent，可以在 [OpenLux 注册](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=agent-builder-shutdown-agents-sdk-chatkit-migration&utm_content=footer)。

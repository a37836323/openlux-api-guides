---
layout: default
title: "n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置"
description: "n8n 接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：新建 OpenAI 凭据，Base URL 改为 https://api.openlux.ai/v1，API Key 填令牌、Organization ID 留空；OpenAI Chat Model 节点选凭据和模型 ID，Claude、Gemini 关闭 Use Responses API；附 401、404、少写 /v1 的排查。"
permalink: /news/n8n-relay-api-openai-compatible-setup/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[n8n 官方文档](https://docs.n8n.io/integrations/builtin/credentials/openai/)

# n8n 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：Base URL、Key 与模型设置

直接回答：在 n8n 里新建一个 **OpenAI** 凭据，把 **Base URL** 从默认的 `https://api.openai.com/v1` 改成 `https://api.openlux.ai/v1`，**API Key** 填 OpenLux 令牌，**Organization ID** 留空；然后在 AI Agent 或 Basic LLM Chain 下挂 **OpenAI Chat Model** 子节点，选这个凭据，再选模型或按 ID 填模型名。调 Claude、Gemini 这类非 GPT 模型时，把节点里的 **Use Responses API** 关掉。

本文以 OpenAI Chat Model 节点为例，用的是自建或 n8n Cloud 里自己添加的 OpenAI 凭据，不涉及 n8n Cloud 的 Gateway credits。

## 适用版本与依据

- 凭据怎么建见 n8n 官方文档 [OpenAI credentials](https://docs.n8n.io/integrations/builtin/credentials/openai/)，这一页只写了 API Key 和 Organization ID。
- **Base URL** 字段的说明来自 n8n 官方仓库的[凭据源码](https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/credentials/OpenAiApi.credentials.ts)：默认值 `https://api.openai.com/v1`，说明为 "Override the default base URL for the API"。
- 官方文档在 [Message an Assistant](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-langchain.openai/assistant-operations/) 的 Base URL 选项里写明，它可用于“提供 OpenAI-compatible API 的其他 LLM 提供方”。
- 字段名和默认值按 2026-10-31 官方仓库 master 分支代码核对，界面以你安装的版本为准。

前提：已在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建好 Key。

## 第一步：新建 OpenAI 凭据

在 n8n 的 Credentials 里新建，类型选 **OpenAI**，按下表填写：

| 字段 | 填什么 | 说明 |
|---|---|---|
| API Key | OpenLux 令牌 | 以 `Authorization: Bearer` 请求头发出 |
| Organization ID (optional) | 留空 | 只有多组织的 OpenAI 账号才需要 |
| Base URL | `https://api.openlux.ai/v1` | 必须带一次 `/v1`，不要多也不要少 |
| Add Custom Header | 关闭 | 中转接入不需要额外请求头 |

按源码，凭据的测试请求是 `GET {Base URL}/models`。Base URL 少写 `/v1` 时，请求的是 `https://api.openlux.ai/models`，而 OpenLux 的模型列表在 `/v1/models`，所以填好后要以下文验证步骤能列出模型为准。

n8n 的 **Anthropic** 凭据也有 Base URL 字段；走 Anthropic 协议时填不带 `/v1` 的 `https://api.openlux.ai`，本文不展开。

## 第二步：在 OpenAI Chat Model 节点里选模型

1. 添加 **AI Agent** 或 **Basic LLM Chain** 节点，在 Chat Model 位置挂 **OpenAI Chat Model** 子节点。
2. **Credential** 选刚建的凭据。
3. **Model** 有两种方式：
   - **From List**：节点请求 `{Base URL}/models`。按源码，Base URL 不是 `api.openai.com` 时不再只保留 `gpt-` 开头的模型，会列出返回的全部模型。
   - **ID**：直接粘贴模型 ID，例如 `gpt-6-luna`、`claude-sonnet-5-5`。模型名只用 OpenLux 价格页在售的 ID，大小写、点和连字符都要一致。
4. 按源码，节点自己的 Base URL 选项从 1.1 版起已隐藏，新节点用凭据里的地址。

## 第三步：Use Responses API 开还是关

[OpenAI Chat Model 官方文档](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/)：打开 **Use Responses API** 走 Responses API，否则走 Chat Completions。当前源码里 1.3 版节点这个开关**默认打开**，添加节点后先确认。

OpenLux 上每个模型支持哪些接口，看价格页的接口标注（价格接口里的 `supported_endpoint_types`）。2026-10-30 的情况：

| 模型系列 | 支持的 OpenAI 协议接口 | Use Responses API |
|---|---|---|
| GPT（如 gpt-6-luna） | Chat Completions、Responses | 开关均可 |
| Claude（如 claude-sonnet-5-5） | Chat Completions | 关闭 |
| Gemini、DeepSeek | Chat Completions | 关闭 |
| Qwen | 只有 Chat Completions | 关闭 |

官方文档写明，Web Search、File Search、Code Interpreter 等内置工具要打开 Responses API 并配合 AI Agent 节点。它们走中转是否可用本文没有核实，不要依赖。

## 怎么验证配置成功

1. 先在终端用同一个 Key 列模型（把 `<你的Key>` 换成令牌）：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer <你的Key>"
```

返回模型列表，说明地址和 Key 都对；返回 401 先查 Key。

2. 回到 n8n：凭据测试通过，且 Chat Model 节点的 From List 能列出模型。
3. 用 Basic LLM Chain 发一句简单的问题，有正常文本输出就算接通。

## 常见报错与改法

| 现象 | 原因 | 改法 |
|---|---|---|
| 401，`Invalid token` | Key 填错或没填 | 重新复制令牌，保存后再测 |
| 404，`Invalid URL`，报错里的路径出现 `/v1/v1` | Base URL 多写了一个 `/v1`，比如写成 `.../v1/v1` | Base URL 只保留一个 `/v1` |
| 模型列表拉不出来或调用出错，Base URL 是 `https://api.openlux.ai` | 少了 `/v1`，请求的是 `/models`、`/chat/completions`，不是 OpenLux 的 `/v1/models`、`/v1/chat/completions` | 改成 `https://api.openlux.ai/v1` |
| 提示模型不存在 | ID 拼错，或者该模型不在售 | 按价格页复制准确 ID |
| GPT 正常，换成 Claude 或 Gemini 后出错 | Use Responses API 开着，而这些模型在价格页只标了 Chat Completions | 关闭 Use Responses API 再试 |

另外，节点的 **Max Retries** 按源码默认是 2，请求失败时可能自动重试，日志里同一请求出现多次时先考虑这一点；**Timeout** 单位是毫秒，长回答被提前中断时可以调大。

## 注册与获取 Key

还没有账号可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=n8n-relay-api-openai-compatible-setup&utm_content=footer)，在控制台「令牌」页创建 Key，再按上面的步骤填进 n8n。

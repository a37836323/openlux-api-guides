---
layout: default
title: "Open WebUI 怎么接入 OpenAI 兼容 / Claude 中转 API：URL、Key 与模型设置"
description: "Open WebUI 接入 OpenAI 兼容或 Claude 中转 API：在 Settings > Admin > Connections 添加连接，URL 带 /v1、填 Key、用 Verify Connection 验证，Model IDs、Prefix ID、环境变量与 ConfigVar 不生效、模型列表转圈、工具调用空回复等报错处理。"
permalink: /news/open-webui-relay-api-openai-compatible-setup/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[Open WebUI 官方文档](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)

# Open WebUI 怎么接入 OpenAI 兼容 / Claude 中转 API：URL、Key 与模型设置

在 Open WebUI 里接中转 API，做法是用管理员账号打开 **Settings > Admin > Connections**，在 **Manage OpenAI API Connections** 列表旁点 **➕ Add Connection**，URL 填中转站的 OpenAI 兼容地址（写到 `/v1`），API Key 填中转站的 Key，保存后在聊天页的模型选择器里选模型。[Open WebUI 官方 OpenAI-Compatible 文档](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)写明，Open WebUI 支持“任何实现了 OpenAI 兼容 API 的服务器或提供方”，主要协议是 OpenAI Chat Completions。

Claude 模型也走同一个入口：[官方 Anthropic 接入文档](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-anthropic)说明 Open WebUI 没有单独的 Anthropic 提供方类型，Claude 是通过 OpenAI 兼容端点、加在同一个 OpenAI 连接列表里的。本文以 OpenLux 为例，设置项名称以撰文时的官方文档为准；官方文档没有写明这些设置项从哪个版本开始提供，界面可能随版本变化。

## 适用范围和前提

先确认四件事：

1. **有管理员权限**。连接在管理后台的 **Admin > Connections** 里添加，官方 Connect a Provider 页把管理员权限列为前提。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。官方建议多用户部署时用权限最小、只用于推理的 Key，不要用管理用的主 Key。
3. **知道要用的模型 ID**。只能用中转站在售的模型 ID，OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，例如 `gpt-6-astra`、`claude-opus-5-5`、`gemini-3.8-flash`。
4. **了解数据去向**。官方 Connect a Provider 页提醒：选了哪个端点，推理就在哪里执行，云端模型会收到提示词和上下文。

## 地址怎么填：带 /v1

| 要用的模型 | 连接类型 | URL | 依据 |
|---|---|---|---|
| GPT 系列 | OpenAI 兼容连接 | `https://api.openlux.ai/v1` | 官方 OpenAI 页的 URL 示例是 `https://api.openai.com/v1`，写到 `/v1` |
| Claude 系列 | 同一个 OpenAI 兼容连接 | `https://api.openlux.ai/v1` | 官方 Anthropic 页的 URL 是 `https://api.anthropic.com/v1`，并注明要带 `/v1`；Open WebUI 没有原生 Anthropic 类型 |
| Gemini 等其他模型 | 同一个 OpenAI 兼容连接 | `https://api.openlux.ai/v1` | 价格接口里这些模型的端点类型列有 `openai` |

价格接口里 `claude-opus-5-5`、`claude-sonnet-5-5` 等 Claude 模型的端点类型同时列有 `anthropic` 和 `openai`，`gemini-3.8-flash` 列有 `gemini` 和 `openai`，所以一个连接就能覆盖这几类模型；实际能用哪些，以 `/v1/models` 的返回为准。

注意：官方说明 Open WebUI 是按 URL 里是否包含 `api.anthropic.com` 来识别 Anthropic 的。中转地址不含这个域名，Anthropic 页里那套专用的模型列表转换不适用，模型列表来自中转站自己的 `/models`。

## 在管理后台添加连接

按官方 OpenAI-Compatible 文档的 Step 1：

1. 进入 **Settings > Admin > Connections**，找到 **Manage OpenAI API Connections**。
2. 点 **➕ Add Connection**。
3. **Connection Type** 选 **External**（官方 OpenAI 页的写法）。
4. **URL** 填 `https://api.openlux.ai/v1`，**API Key** 填 OpenLux 的 Key。
5. 点 URL 旁的 **Verify Connection**。官方说明“保存连接不会测试它”，要点这个按钮才会用 Bearer Token 请求 `/models`，成功时提示 **Server connection verified**。
6. 需要时填 **Model IDs**（见下一节），然后点 **Save**。

每个连接旁有开关，可以临时停用而不删除配置。如果 Open WebUI 跑在 Docker 里，访问的是外网地址 `api.openlux.ai`，不涉及官方提到的把 `localhost` 换成 `host.docker.internal` 那条提示；那条只针对模型服务装在宿主机上的情况，本地 Ollama 连接问题可以看本站的 [Open WebUI 连不上 Ollama 排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-ollama-docker-connection-refused/)。

## Model IDs、Prefix ID 和 Provider 怎么设

这三项在连接的 **Advanced** 里，官方 OpenAI 页的说明如下：

- **Model IDs**：留空时自动发现提供方的所有模型；一旦填了，填的列表就替换掉拉取结果，Open WebUI 不再对这个连接调用 `/models`，只显示你填的 ID。中转站模型很多时，建议只填自己要用的几个，例如 `gpt-6-astra`、`claude-opus-5-5`。输入 ID 后点 **+** 再保存；重复的 ID 会提示 **Model ID is already added**。
- **Prefix ID**：同时接了多个提供方、且有同名模型时用。前缀和模型 ID 用点号连接，例如前缀 `openlux` 加 `gpt-6-astra` 显示为 `openlux.gpt-6-astra`，发往上游前会去掉前缀。官方提醒前缀不要带斜杠，`groq/` 会变成 `groq/.qwen3.6`。
- **Provider**：保持 **Default**。官方说明 Default 始终可用，其他选项是给 Azure OpenAI、llama.cpp、LM Studio、LiteLLM 这几类特定服务器用的。

## 用环境变量配置

也可以在启动容器时用环境变量写入连接。官方环境变量文档里的相关项：

| 变量 | 作用（官方说明） |
|---|---|
| `OPENAI_API_BASE_URL` | OpenAI 基础 API 地址，默认 `https://api.openai.com/v1` |
| `OPENAI_API_KEY` | OpenAI API Key |
| `OPENAI_API_BASE_URLS` / `OPENAI_API_KEYS` | 多个地址、多个 Key，均用分号分隔 |
| `ENABLE_OPENAI_API` | 是否启用 OpenAI API，默认 `True` |

例如在 `.env` 或 docker-compose 的环境变量里写（Key 换成自己的，不要提交到代码仓库）：

```
OPENAI_API_BASE_URL=https://api.openlux.ai/v1
OPENAI_API_KEY=你的OpenLux Key
```

这几项都是 **ConfigVar**：[官方环境变量文档](https://docs.openwebui.com/reference/env-configuration)说明，首次启动后它们的值会存进数据库，之后重启容器不再读取外部环境变量；在管理后台保存过的值也优先于环境变量。所以改了环境变量不生效时，要么在后台直接改，要么设 `RESET_CONFIG_ON_START=true`（下次启动用环境变量覆盖数据库配置），或设 `ENABLE_PERSISTENT_CONFIG=false`（始终用环境变量，后台改动重启后丢失）。

## 验证是否接通

**在 Open WebUI 里验证**：先点 **Verify Connection**，看到 **Server connection verified** 再保存；然后打开新对话，在模型选择器里选刚加的模型（如 `claude-opus-5-5`），发一条简单问题，能正常返回就算接通。

**用命令行确认地址和 Key**：界面里报错又分不清原因时，在终端请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴进截图或聊天）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Open WebUI 的配置上；返回 401 说明 Key 错了或没带上。顺便在返回列表里找一下要用的模型 ID，确认拼写一致。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| Verify Connection 报 401 | Key 填错、复制时带了空格 | 重新从 OpenLux「令牌」页复制；用上面的 curl 单独验证 |
| 404 或模型列表为空 | URL 少写了 `/v1`，或多写了 `/chat/completions` | URL 只填到 `https://api.openlux.ai/v1` |
| 选模型后提示模型不存在 | Model IDs 里手填的 ID 不是在售 ID，或大小写、点号不一致；或加了 Prefix ID 后又手动带前缀 | 对照价格接口和 `/v1/models` 的返回重新填写 |
| 模型选择器一直转圈、设置页打不开 | 某个连接地址不可达，官方说明默认每个端点等 10 秒 | 在 Connections 里改正或删掉不可达地址；可设 `AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST` 调整超时 |
| 后台进不去、没法改回错误地址 | 错误配置已存进数据库并优先于环境变量 | 设 `RESET_CONFIG_ON_START=true` 后重启，或 `ENABLE_PERSISTENT_CONFIG=false` |
| 改了环境变量不生效 | 这些变量是 ConfigVar，首次启动后读数据库 | 在后台修改，或用上一行的两个变量 |
| 开了工具后偶尔返回空消息 | 官方排错页说明：流式工具调用缺少 `index` 字段时，Open WebUI 会丢掉这次调用 | 按下文自查；确认是这个问题就把模型 **Advanced Params** 里的 **Function Calling** 设为 **Legacy** |

404 那一行是按 OpenLux 入口的地址规则推出来的，Open WebUI 官方文档没有直接写出地址填错时的报错内容。

关于空消息：[官方连接排错页](https://docs.openwebui.com/troubleshooting/connection-error)给了自查方法，向 `/v1/chat/completions` 发一个带 `tools`、`"stream": true` 的请求，看返回的 `delta.tool_calls` 里有没有 `"index"`，没有就是这个问题。官方点名的已知情况是 Google 的 OpenAI 兼容层；经中转调用各家模型时是否有同样现象，本文未核实，以自查结果为准。另外，官方 Anthropic 页转述 Anthropic 的说法：OpenAI 兼容接口主要用于评估和测试，PDF 处理、引用、扩展思考、提示缓存等 Claude 原生功能建议走原生 `/v1/messages`。Open WebUI 的聊天走的是 Chat Completions 协议，这些功能经中转能否使用，本文未核实，不要预设可用。

## 参考资料

- Open WebUI 文档：[OpenAI-Compatible](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)（添加连接、Verify Connection、Model IDs、必需端点）
- Open WebUI 文档：[OpenAI](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai)（Connection Type、Model IDs、Prefix ID、Provider）
- Open WebUI 文档：[Anthropic (Claude)](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-anthropic)（没有原生 Anthropic 类型、兼容性说明）
- Open WebUI 文档：[Connect a Provider](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider)（数据去向提示）
- Open WebUI 文档：[Environment Variable Configuration](https://docs.openwebui.com/reference/env-configuration)（OPENAI_API_* 与 ConfigVar）
- Open WebUI 文档：[Connection Errors](https://docs.openwebui.com/troubleshooting/connection-error)（模型列表加载、工具调用空回复）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=open-webui-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤添加到 Open WebUI。

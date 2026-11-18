---
layout: default
title: "Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查"
description: "Cherry Studio 智能体（工作）接中转 API 时选不到模型、提示必须启用 API 网关或任务一直等待：按官方文档给服务商配 Anthropic 端点、选支持 Anthropic 协议的模型、确认运行模式、启动 API 网关，并用状态面板和调用链排查 401、404。"
permalink: /news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/
date: 2026-11-17
---

> 更新日期：2026-11-17 · 一手来源：[Cherry Studio 官方文档](https://cherry-ai.com/docs/zh-cn/advanced-basic/agent-workspace/create-agent/)

# Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查

在 Cherry Studio 的【工作】（也就是智能体）里用中转 API，常见三类问题：创建智能体时模型下拉里找不到中转站的模型；提示必须启用 API 网关；任务发出去后一直等待、不往下走。按 [Cherry Studio 官方文档「创建智能体与模型分工」](https://cherry-ai.com/docs/zh-cn/advanced-basic/agent-workspace/create-agent/)，智能体的模型选择器会**按运行模式过滤不兼容的模型**；官方「模型服务配置」页又写明 **Cherry 智能体需要 Anthropic 兼容（`/v1/messages`）类型的服务商**。所以排查顺序是：先看服务商有没有配 Anthropic 端点、模型是否加入列表，再看运行模式，最后看 API 网关和右侧【状态】面板。

本文适用于已经在「设置 → 模型服务」接好中转、普通对话能正常回复，但智能体用不了的读者，以 OpenLux 为例。普通对话也不通的话，先看[Cherry Studio 接入中转 API 的基础设置](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-relay-api-custom-provider-setup/)。界面名称以撰文时的官方文档为准，旧版本按钮位置可能不同。

## 先分清是哪一类问题

| 现象 | 先查哪里 | 官方依据 |
|---|---|---|
| 添加或编辑智能体时，模型列表里没有中转站的模型 | 服务商是否配了 Anthropic 端点、模型是否加入列表、服务商是否启用 | 模型服务配置页的服务商类型表；创建智能体页「选择器会按运行模式过滤不兼容模型」 |
| 提示必须启用 API 网关，或弹出【启用并启动】 | 【设置】→【API 网关】的运行状态和端口 | 智能体工作区页「智能体运行依赖 Cherry Studio 的 API 网关」 |
| 任务一直等待，没有继续运行 | 右侧【状态】：权限请求、后台命令、子任务、服务商重试 | 常见问题页；权限、记忆与后台任务页 |
| 刚绑定的技能、MCP、知识库没生效 | 新发一条消息 | 智能体工作区页「变化会从下一条消息开始生效」 |
| 普通对话也不通 | 回到【模型服务】查地址、Key、启用开关 | 模型服务设置页 |

## 第一步：给中转服务商配上 Anthropic 端点

官方「模型服务配置」页把服务商按协议分类：OpenAI 兼容走 `/v1/chat/completions`，Anthropic 兼容走 `/v1/messages`，并在 Anthropic 兼容一行注明「Cherry 智能体需要此类型」；Anthropic 服务商页也写明「智能体需要 Anthropic 协议端点」；全部服务商快速参考里，「使用智能体」一栏推荐的是要支持 Anthropic 协议的服务商。

如果你当初添加自定义服务商时只填了 OpenAI 端点，智能体里就可能看不到这些模型。按官方「自定义服务商」页的步骤：【设置】→【模型服务】→【+ 添加服务商】，在弹窗的【端点设置】里，默认就可以同时添加 OpenAI 和 Anthropic 两个端点。已有服务商里找不到补填位置时，可以按这个步骤重新添加一个服务商，两个端点一起填。

| 端点 | API 地址填写 | 说明 |
|---|---|---|
| Anthropic | `https://api.openlux.ai` | 不带 `/v1`。内置 Anthropic 服务商的默认地址 `https://api.anthropic.com` 就是不带 `/v1` 的根地址；OpenLux 的 Anthropic 入口同样填根地址，请求路径是 `/v1/messages` |
| OpenAI | `https://api.openlux.ai` | 填根地址，Cherry Studio 自动补 `/v1/chat/completions` |
| 末尾加 `#` | 不要加 | 官方说明 `#` 表示不再自动拼接版本路径，只有中转站明确要求无版本路径时才用 |

API 密钥两个端点用同一个 OpenLux Key 即可，在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。

## 第二步：选支持 Anthropic 协议的模型，并加入列表

光有 Anthropic 端点还不够，模型本身也要支持这个协议。OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里每个模型都列了 `supported_endpoint_types`。撰文时：

- `claude-sonnet-5-5`、`claude-opus-5-5`、`deepseek-v4.1-flash` 列有 `anthropic` 和 `openai`，可以用在智能体里；
- `gpt-5.6-sol` 只有 `openai`、`openai-response`，`qwen3.8-max` 只有 `openai`，不支持 Anthropic 协议。

以价格接口当时的返回为准。确认模型后，按官方「模型服务设置」页操作：

1. 在服务商配置页点【获取模型列表】，在弹出的「模型管理」里点模型右侧的 `+`；拉不到就手动添加模型 ID。官方强调：**只有加入列表的模型才会出现在各处的模型选择器里**。
2. 核对模型名称下方显示的实际 API 模型 ID，名称相近的版本不会被合并。
3. 打开服务商右上角的**启用开关**，否则模型不会出现在选择列表里。
4. 点【检测】，选一个刚加的模型测试连接。

官方「创建智能体」页还建议，主模型选「一个已验证能稳定调用工具的模型」。智能体要读写文件、调用工具，先在普通对话里确认这个模型能正常回复，再放进智能体。

## 第三步：确认运行模式，模式选错只能新建

创建智能体时，第一步【基础信息】要先选运行模式，再选页面列出的兼容模型。官方说明运行模式决定模型分工、权限模式和部分工具，**创建后不能切换**。

| 运行模式 | 官方描述 | 模型配置 | 注意事项 |
|---|---|---|---|
| 【增强：Claude Agent】 | 能力面完整，适合复杂、多步骤任务 | 主模型、Plan 模型、Small 模型 | 支持全部五种权限模式和心跳检测；Plan、Small 默认与主模型相同 |
| 【快速：Pi】 | 响应快、开销低，适合日常文件和编码任务 | 只配置主模型 | 不提供【仅规划】，新建时默认【智能批准】 |
| 【DeepSeek Harness】 | 兼容多种模型服务，支持目标驱动执行 | 只配置主模型 | 不提供【智能批准】和心跳检测 |

官方没有逐个模式写明各自需要哪种协议，所以最稳妥的做法是先把 Anthropic 端点配好（第一步）。如果是旧智能体的模式和你想用的模型不匹配，官方建议**新建一个智能体**，而不是继续改旧的。

## 第四步：提示必须启用 API 网关

官方「智能体工作区」页说明，智能体运行依赖 Cherry Studio 的 API 网关；网关未启用时，应用会提示【启用并启动】。处理方法：

1. 直接点提示里的【启用并启动】；或打开【设置】→【API 网关】，点【启动】，状态变成【运行中】即可。
2. 启动不了先看端口：端口被其他程序占用时服务无法正常启动。网关**停止时**才能改端口，换一个未占用的端口再启动。
3. 端口正常仍起不来，检查本机安全软件是否拦截。

两点容易误会：只用 Cherry Studio 智能体时，不需要把网关的 URL 或密钥复制给任何程序，保持默认的本机使用即可；网关本身不提供模型，官方原话是「仍需要至少一个可用服务商和模型」，网关的密钥也不是 OpenLux 的 Key，不要混填。

## 第五步：任务一直等待或中途失败

官方常见问题的处理顺序是：打开右侧【状态】，看是否有**待处理的权限请求、后台命令、子任务或服务商重试**。

- **在等你批准**：【逐次确认】模式下，编辑文件或执行命令前都会询问；【智能批准】模式下部分模型可能仍会逐次询问；检测到系统或全局软件包安装时，除【完全访问】外都需要有人实时审批。
- **服务商在重试或报错**：到【设置】→【通用】开启【启用开发者模式】，重启 Cherry Studio 后重新发一条最小测试消息，在右侧【调用链】里看「模型请求」和「HTTP 请求」节点的状态和响应。

调用链里常见的中转报错可以这样对照：

| 调用链里看到 | 含义 | 处理 |
|---|---|---|
| 401 `Invalid token (request id: ...)` | Key 错了或没带上 | 重新复制 Key 填进服务商，多个 Key 用英文逗号分隔 |
| 404 `Invalid URL (POST /v1/v1/messages)` | Anthropic 端点地址多写了 `/v1` | 改成 `https://api.openlux.ai` |
| 模型不存在类报错 | 模型 ID 和在售 ID 不一致 | 对照价格接口和模型名下方的实际 API 模型 ID 重新添加 |

调用链可能包含请求头和提示词，官方提醒分享截图前必须删掉 API Key、Authorization 等信息。另外，智能体的模型、技能、MCP、知识库改动会从**下一条消息**开始生效，改完新发一条再看。

## 怎样算接通

1. 终端请求模型列表，能列出模型说明地址和 Key 都对（`$OPENLUX_API_KEY` 换成你自己的 Key）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

2. 【模型服务】里用支持 Anthropic 的模型点【检测】通过。
3. 【设置】→【API 网关】显示【运行中】。
4. 在【工作】里新建智能体，模型下拉能看到这个模型；新建任务，发一句不涉及文件的短任务（例如「用一句话介绍你能做什么，不要读写任何文件」），右侧【状态】里任务正常完成、没有失败的工具调用。

## 参考资料

- Cherry Studio 文档：[创建智能体与模型分工](https://cherry-ai.com/docs/zh-cn/advanced-basic/agent-workspace/create-agent/)（运行模式、模型过滤、创建后不可切换）
- Cherry Studio 文档：[模型服务配置](https://cherry-ai.com/docs/zh-cn/pre-basic/providers/)（服务商类型，Cherry 智能体需要 Anthropic 兼容类型）
- Cherry Studio 文档：[Anthropic](https://cherry-ai.com/docs/zh-cn/pre-basic/providers/anthropic/)（智能体需要 Anthropic 协议端点、默认 API 地址）
- Cherry Studio 文档：[自定义服务商](https://cherry-ai.com/docs/zh-cn/pre-basic/providers/zi-ding-yi-fu-wu-shang/)（端点设置可同时添加 OpenAI 和 Anthropic 端点）
- Cherry Studio 文档：[模型服务设置](https://cherry-ai.com/docs/zh-cn/pre-basic/settings/providers/)（API 地址规则、模型列表、启用开关、检测）
- Cherry Studio 文档：[智能体工作区](https://cherry-ai.com/docs/zh-cn/advanced-basic/agent-workspace/)、[API 网关](https://cherry-ai.com/docs/zh-cn/advanced-basic/developer-tools/api-gateway/)
- Cherry Studio 文档：[权限、记忆与后台任务](https://cherry-ai.com/docs/zh-cn/advanced-basic/agent-workspace/permissions-memory-background/)、[调用链与开发者模式](https://cherry-ai.com/docs/zh-cn/advanced-basic/developer-tools/trace/)、[常见问题](https://cherry-ai.com/docs/zh-cn/question-contact/questions/)

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤配置 Cherry Studio 智能体。

## 同专题文章

- [Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-embedding-knowledge-base-rag-setup/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)
- [n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查](https://a37836323.github.io/openlux-api-guides/news/n8n-ai-agent-relay-prompt-content-null-session-fix/)
- [Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办](https://a37836323.github.io/openlux-api-guides/news/cline-cli-relay-api-auth-baseurl-setup/)
- [Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置](https://a37836323.github.io/openlux-api-guides/news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/)
- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

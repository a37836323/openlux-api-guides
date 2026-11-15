---
layout: default
title: "LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置"
description: "LobeHub（LobeChat）接中转 API 后输入框没有图片上传按钮、技能用不了或深度思考用不了，按官方文档在「配置模型」里打开支持视觉识别、支持技能使用、支持深度思考，自部署用 OPENAI_MODEL_LIST 的 <上下文窗口:vision:fc> 扩展能力，附验证方法与常见问题。"
permalink: /news/lobehub-relay-vision-skills-model-capabilities-fix/
date: 2026-11-15
---

> 更新日期：2026-11-15 · 一手来源：[LobeHub 官方文档](https://lobehub.com/zh/docs/self-hosting/advanced/model-list)

# LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置

LobeHub 接上中转 API 后能正常聊天，但选中模型后输入框里**没有图片上传按钮**、**技能用不了**，或者推理模型**用不了深度思考**——能正常聊天，说明地址和 Key 已经接通，这时要查的是 LobeHub 里这个模型的能力配置。按 LobeHub 官方文档，图片上传按钮只在选中支持视觉的模型时出现；每个模型能用哪些能力，由模型配置里的能力开关决定。解决办法：网页版在服务商的模型列表里点 **配置模型**，打开 **支持视觉识别**、**支持技能使用**、**支持深度思考** 等开关；自部署实例也可以在 `OPENAI_MODEL_LIST` 里用 `<上下文窗口:vision:fc:reasoning>` 写扩展能力。

本文适用于 LobeHub（原 LobeChat）云端版和自部署版，在 **应用设置 → AI 服务商** 里给 OpenAI、Anthropic 或自定义服务商填了中转代理地址的情况。地址、Key 的基础接入步骤见指南站[《LobeHub（LobeChat）怎么接入 OpenAI 兼容 / Claude 中转 API》](https://a37836323.github.io/openlux-api-guides/news/lobehub-lobechat-relay-api-proxy-url-setup/)，本文只讲接通之后的能力配置。依据是 LobeHub 官方文档 [Model List 与扩展能力配置](https://lobehub.com/zh/docs/self-hosting/advanced/model-list)、[视觉与图像理解](https://lobehub.com/zh/docs/usage/getting-started/vision)、[多模型服务商](https://lobehub.com/zh/docs/usage/providers)，以及官方仓库 lobehub/lobehub 的界面文案和源码。

## 先判断：是能力没打开，还是接入本身有问题

先用下表分清是哪一类。能聊天但缺功能，看前四行；连聊天都不行，先回去查地址和 Key。

| 现象 | 可能的原因 | 先看哪里 |
|---|---|---|
| 选中模型后输入框没有图片上传按钮 | 模型没开「支持视觉识别」 | 配置模型 → 支持视觉识别 |
| 给模型加不了技能，或技能用不了 | 模型没开「支持技能使用」（function calling） | 配置模型 → 支持技能使用 |
| 推理模型用不了深度思考 | 模型没开「支持深度思考」 | 配置模型 → 支持深度思考 |
| 环境变量里写了 `<vision:fc>` 但不生效 | 尖括号里第一个值不是上下文窗口 | 改成 `<上下文窗口:vision:fc>` |
| 模型回复为空、点「检查」不通过 | 地址或 Key 问题，不是能力问题 | OpenAI 服务商地址是否带 `/v1`、Key 是否有多余空格 |

## 为什么中转来的模型能力常常是关的

按官方源码，LobeHub 判断模型能力靠模型资料和配置，而不是实际调用模型去测。具体分三种情况：

1. **点「获取模型列表」拉回来的模型**：官方源码 `packages/model-runtime/src/utils/modelParse.ts` 里，每个能力按这个顺序取值——接口返回的模型字段，然后是 LobeHub 内置模型资料里 ID 完全相同的模型，然后是按模型 ID 关键词推断，三者都没有就是 `false`。中转返回的模型 ID 如果和 LobeHub 内置资料对不上，关键词规则也没覆盖到，能力就是关的。关键词推断也可能标错，所以最终以你自己核对过的设置为准。
2. **点「添加模型」手动创建的模型**：官方源码里「创建自定义 AI 模型」弹窗没有给表单预设值，能力开关默认都是关的，需要自己打开。
3. **自部署用 `OPENAI_MODEL_LIST` 加的模型**：可以在尖括号里显式声明能力（写法见下文），不必依赖 LobeHub 的推断。

还要注意，这些开关**只是让 LobeHub 开放对应功能**，不会给模型增加能力。官方界面对「支持视觉识别」的说明是：此配置将仅开启应用中的图片上传配置，是否支持识别完全取决于模型本身。所以开之前，先在模型厂商的官方模型说明里确认它支持图片输入或工具调用。

## 网页版：在「配置模型」里打开能力开关

按官方界面操作，步骤如下：

1. 打开 **应用设置 → AI 服务商**，选中你填了中转地址的服务商（如 OpenAI）。
2. 在 **模型列表** 里找到要用的模型，点它的铅笔图标 **配置模型**，打开「自定义模型配置」。列表里没有这个模型，就点 **添加模型** 手动创建，**模型 ID** 必须和中转在售的 ID 完全一致（创建后不能改）。
3. 按模型实际能力打开对应开关，保存。
4. 回到对话，选中这个模型再试。

弹窗里和本文有关的设置项，名称和说明都按 LobeHub 官方中文界面文案：

| 设置项 | 官方说明（摘要） | 打开后的效果 |
|---|---|---|
| 支持视觉识别 | 仅开启应用中的图片上传配置，能否识别取决于模型本身 | 输入框出现图片上传入口 |
| 支持技能使用 | 仅开启模型使用技能的能力，是否真能用取决于模型本身 | 可以给模型添加技能 |
| 支持深度思考 | 仅开启模型深度思考的能力，效果取决于模型本身 | 开放深度思考相关功能 |
| 支持联网搜索 | 仅开启模型内置搜索引擎的联网搜索能力 | 只对自带搜索的模型有意义 |
| 最大上下文窗口 | 设置模型支持的最大 Token 数 | 按模型厂商公布的数字填 |
| 扩展参数 | 选择模型支持的扩展参数，配置错误可能导致请求失败 | 如推理强度等控制项 |
| 模型类型 | 不同模型类型拥有差异化的使用场景与能力 | 对话模型选「对话」 |

**扩展参数** 要谨慎：官方提示配置错误可能导致请求失败。只选模型厂商文档里明确支持的参数，不确定就留空。

关于联网搜索：LobeHub 官方《网络搜索》文档说明，输入框下方的 **Web Search** 有 Smart Search 和 Provider Search 两种模式，界面提示 Provider Search 可能出现非预期行为、不推荐使用；自部署实例的 Smart Search 还要配置服务端搜索提供商（默认 SearXNG）。所以「支持联网搜索」开关只在模型本身带搜索时才需要打开。

## 自部署：用 OPENAI_MODEL_LIST 写扩展能力

自部署实例想统一配置，可以按官方 Model List 文档在环境变量里写能力。语法是：

```text
id=displayName<maxToken:vision:reasoning:search:fc:file:imageOutput>
```

规则要点（均出自官方文档）：

- 用英文逗号分隔多个模型；`+` 增加模型，`-` 隐藏模型，`-all` 先隐藏全部内置模型。
- 尖括号里**第一个值必须是上下文窗口（maxToken）**，后面的能力用冒号分隔，顺序无所谓。官方故障排查写明：应写 `<8192:fc:vision>`，不能写 `<fc:vision>`。
- 能力关键字：`fc` 函数调用（即技能使用）、`vision` 视觉识别、`reasoning` 深度思考、`search` 联网搜索、`imageOutput` 图像生成、`video` 视频理解、`file` 文件上传（官方注明比较 hack，不建议日常使用）。

接 OpenLux 时，按指南站接入篇的地址写法（OpenAI 服务商带 `/v1`），可以这样写（把尖括号里的上下文窗口换成模型厂商公布的数字；模型是否支持看图、工具调用，以厂商官方说明为准，这里只演示写法）：

```bash
OPENAI_API_KEY=你的OpenLux Key
OPENAI_PROXY_URL=https://api.openlux.ai/v1
OPENAI_MODEL_LIST=-all,+gpt-6-astra=GPT-6 Astra<上下文窗口:vision:fc>,+claude-sonnet-5-5=Claude Sonnet 5.5<上下文窗口:vision:fc>
```

模型 ID 只用 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里在售的 ID。上面两个 ID 在价格接口里都带 `openai` 端点类型，所以能放在 OpenAI 服务商下；只支持其他端点类型的模型不要放进来。

## 验证：怎么确认已经改好

1. **先排除接入问题**：在终端运行下面的命令，能列出模型就说明地址和 Key 都对：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的Key"
```

2. **视觉**：在对话里选中改好的模型，输入框出现图片上传入口；发一张小截图，问「图片里的文字写的是什么」，能答出内容就算成功。官方建议单张图片 5 MB 以内。
3. **技能**：在助理里启用一个技能，提一个需要用到它的问题，看模型是否发起调用。
4. **自部署**：改完环境变量后要重新部署，让容器带着新变量启动；模型没出现在选择器里，按官方建议执行 `docker logs lobehub | grep -i "model"` 看日志（容器名换成你自己的）。

成功标准：图片能上传且回答和图片内容一致；技能能被调用；模型选择器里能看到你配置的模型和展示名。

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 开了「支持视觉识别」，上传图片后报错或模型说看不到图 | 开关只开放上传入口，可能是模型本身不支持图片输入 | 对照厂商官方模型说明，换支持图片输入的模型 |
| 环境变量里的模型没出现在选择器里 | 语法错误（逗号缺失、尖括号不匹配）、用了 `-all` 但没用 `+` 加回、服务商被 `ENABLED_OPENAI=0` 关闭 | 按官方故障排查逐项检查 |
| 扩展能力写了但不生效 | 第一个值不是上下文窗口，或 LobeHub 版本太旧（扩展配置从 0.147.8 起支持） | 改成 `<数字:能力>`，升级到新版本 |
| 模型返回空响应 | OpenAI 服务商代理地址少了 `/v1` | 填 `https://api.openlux.ai/v1` |
| Anthropic 服务商返回 404 | 地址多写了 `/v1`，请求变成 `/v1/v1/messages` | 改成 `https://api.openlux.ai` |
| 获取模型列表后，有的模型能力标错 | 能力按内置资料和 ID 关键词推断，可能多标或漏标 | 在「配置模型」里按厂商说明手动改 |

官方故障排查还提醒：LobeHub 无法开启 API 本身不提供的能力。开关打开后仍然不行，就不要再改 LobeHub，应换模型或确认该模型在中转是否支持相应接口。

## 参考资料

- [LobeHub 官方文档：Model List 与扩展能力配置](https://lobehub.com/zh/docs/self-hosting/advanced/model-list)
- [LobeHub 官方文档：视觉与图像理解](https://lobehub.com/zh/docs/usage/getting-started/vision)
- [LobeHub 官方文档：在 LobeHub 中使用多模型服务商](https://lobehub.com/zh/docs/usage/providers)
- [LobeHub 官方文档：模型服务商环境变量](https://lobehub.com/zh/docs/self-hosting/environment-variables/model-provider)
- [LobeHub 官方文档：网络搜索](https://lobehub.com/zh/docs/usage/agent/web-search)
- [官方源码：模型能力推断 modelParse.ts](https://github.com/lobehub/lobehub/blob/main/packages/model-runtime/src/utils/modelParse.ts)
- [官方界面文案：modelProvider.json（中文）](https://github.com/lobehub/lobehub/blob/main/locales/zh-CN/modelProvider.json)

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=lobehub-relay-vision-skills-model-capabilities-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤配置。

## 同专题文章

- [n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查](https://a37836323.github.io/openlux-api-guides/news/n8n-ai-agent-relay-prompt-content-null-session-fix/)
- [Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办](https://a37836323.github.io/openlux-api-guides/news/cline-cli-relay-api-auth-baseurl-setup/)
- [Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置](https://a37836323.github.io/openlux-api-guides/news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/)
- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)
- [VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查](https://a37836323.github.io/openlux-api-guides/news/vscode-byok-relay-model-not-showing-utility-model-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

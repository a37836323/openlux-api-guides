---
layout: default
title: "Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查"
description: "Chatbox 用自定义提供方接中转 API 后，图片发不出去、模型说看不到图片、文件上传没反应或知识库用不了时，按模型能力勾选、视觉模型、OCR 设置、文档解析器、嵌入模型和 MCP 工具调用逐项排查，并用 /v1/models 和小图验证。"
permalink: /news/chatbox-relay-image-file-vision-knowledge-base-fix/
date: 2026-11-11
---

> 更新日期：2026-11-11 · 一手来源：[Chatbox 官方帮助中心](https://chatboxai.app/zh/guide/faq/troubleshooting)

# Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查

先说结论：Chatbox 用自定义提供方接中转后，文字能聊、一发图片或文件就不对，先查 Chatbox 自己的几项设置，再怀疑 Key：新建模型时没有勾选能力，Chatbox 会把它当成纯文本模型；选的模型本身不支持视觉；用自己的 Key 时没有在「设置 → 默认模型」里配置图片文字识别（OCR）；文档解析器选了需要额外条件的选项；知识库没有配置嵌入模型。下面按现象逐项排查，最后给出验证方法。

本文依据 Chatbox 官方帮助中心的 [功能故障](https://chatboxai.app/zh/guide/faq/troubleshooting) 页，以及官方文档的 [模型配置](https://docs.chatboxai.app/guides/providers)、[导入第三方提供方配置](https://docs.chatboxai.app/guides/providers/import-config)、[本地知识库教程](https://docs.chatboxai.app/guides/knowledge-base) 和 [MCP](https://docs.chatboxai.app/guides/mcp) 页。适用于已经按「OpenAI API 兼容」模式添加了自定义提供方、文字对话正常的情况；还没接通的话，先看站内接入篇《Chatbox 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型》，那篇已经讲了 401、404、模型不存在和 Temperature 报错。

## 先按现象找原因

| 现象 | 可能的原因 | 先做什么 |
|---|---|---|
| 发图片后模型说「看不到图片」或只回答文字部分 | 新建模型时没勾选视觉能力，或模型本身不支持视觉 | 按第一步、第二步检查能力勾选和模型 |
| 用非视觉模型时，图片里的文字没被识别 | 用自己的 Key 时没设置图片文字识别（OCR） | 按第三步在「设置 → 默认模型」里配置 |
| 文件拖进对话没反应或解析失败 | 文件超过限制、文档解析器条件不满足 | 按第四步核对大小、个数和解析器 |
| 知识库建不了或问答没有用上文档 | 没配置嵌入模型（以及重排模型） | 按第五步给知识库选模型 |
| 配了 MCP 但模型从不调用工具 | 模型没标工具调用能力，或模型本身不支持 | 按第六步检查 |

## 第一步：确认新建模型时勾选了能力

官方 [模型配置](https://docs.chatboxai.app/guides/providers) 第 6 步写的是：添加至少一个模型，勾选模型对应的能力配置，这一项可选，**不配置视为纯文本模型**。也就是说，自定义提供方里手动新建的模型，默认按纯文本对待，即使它在厂商那边支持看图。

官方的 [导入配置格式](https://docs.chatboxai.app/guides/providers/import-config) 把能力列为三种：`vision`（视觉）、`reasoning`（推理）、`tool_use`（工具调用），并说明这些能力「决定了 Chatbox 如何调用这些模型」。处理方法：

1. 打开「设置 → 模型提供方」，进入你添加的中转提供方。
2. 在「模型」列表里编辑对应模型，按模型的真实能力勾选视觉；支持工具调用的再勾工具调用。
3. 保存后点「检查」，回到对话重新选中这个模型，新开一个对话再发图片。

不要给不支持视觉的模型勾视觉，能力以模型厂商的官方文档为准。

## 第二步：确认模型本身支持视觉

[功能故障](https://chatboxai.app/zh/guide/faq/troubleshooting) 页的「图片上传不工作」一节说明：部分模型支持直接理解图片，部分不支持。官方举的例子如下，括号里是 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 中对应的模型 ID（端点类型都含 `openai`，可以用「OpenAI API 兼容」模式调用）：

| 官方列举 | 模型 | OpenLux 模型 ID |
|---|---|---|
| 支持视觉 | GPT 5.5 | `gpt-5.5` |
| 支持视觉 | Claude Opus 4.8 / Claude Sonnet 4.6 | `claude-opus-4-8` / `claude-sonnet-4-6` |
| 支持视觉 | Gemini 3.5 Flash | `gemini-3.5-flash` |
| 不支持视觉 | DeepSeek V4 Pro | `deepseek-v4-pro` |
| 不支持视觉 | GLM-5.2 | `glm-5.2` |

表里只是官方举的例子，其他模型是否支持视觉，看模型厂商的文档。本文没有用真实 Key 在 Chatbox 里逐个测试图片请求。需要模型直接理解图片内容时，官方的建议是切换到支持视觉的模型。

## 第三步：用自己的 Key 时配置图片文字识别（OCR）

官方说明：Chatbox AI 为非视觉模型提供自动 OCR，把图片中的文字识别出来再以文本形式发给模型；但默认 OCR 要登录 Chatbox AI 服务才会启动。**如果使用自己配置的 API Key，需要在「设置 → 默认模型」中设置图片文字识别（OCR）。**

所以用中转 Key、又选了非视觉模型时：

1. 打开「设置 → 默认模型」，找到图片文字识别（OCR），指定一个可用的模型。
2. 回到对话再发图片。

注意 OCR 只把图片里的文字转给模型，模型看不到画面本身。要分析图表、照片内容，仍然要用支持视觉的模型（见第二步）。另外，官方还要求确认图片是 JPG、PNG 等常见格式，大小在限制范围内。

## 第四步：文件上传不工作，核对限制和文档解析器

[功能故障](https://chatboxai.app/zh/guide/faq/troubleshooting) 页列出的文件上传限制和检查项：

| 项目 | 官方说明 |
|---|---|
| 单个文件大小 | 小于 50MB |
| 对话中一次上传个数 | 最多 20 个 |
| 文档解析器 | 内置解析、Chatbox AI、MinerU，默认 Chatbox AI |
| 解析器为 MinerU 时 | 需要添加 MinerU API 密钥 |
| 账户点数 | 官方列为第一项检查：电脑端看「最近使用」，手机端看「设置 → Chatbox AI」 |

解析器在「设置 → 文档解析器」里改。官方没有单独写只用自己的 Key、没有 Chatbox AI 点数时默认解析器能否工作；如果你没有 Chatbox AI 账号或点数，可以检查这里的解析器选项，换成内置解析再试。官方 [知识库教程](https://docs.chatboxai.app/guides/knowledge-base) 也提醒：由于本地解析的限制，排版复杂的 PDF 可能解析失败，可以先用其他软件把 PDF 提取成文本文件再导入。

## 第五步：知识库要配置嵌入模型

知识库从 Chatbox 1.15 开始提供，在「设置 → 知识库」创建。官方教程写明创建时要选知识库用的模型，免费用户也可以选自己的 API：

- **嵌入模型**：把文档转换为向量，必需。
- **重排模型**：教程里标为可选，配置后搜索结果更准确。
- **视觉模型**：可选，配置后可以往知识库里加图片，图片中的文字会被提取入库。

功能故障页对使用 API 的用户说得更严：要确认已正确配置嵌入模型和重排模型，缺少相关配置知识库功能将无法正常使用。所以排查时两个都配上最稳妥。

导入配置格式里，模型类型分 `chat`、`embedding`、`rerank` 三种，嵌入和重排模型要按对应类型添加。OpenLux 价格接口里也有嵌入和重排模型（如 `text-embedding-3-small`、`qwen3-rerank`），但它们的端点类型不是 `openai`，本文没有核实它们在 Chatbox 知识库里能否直接调用，接入前先在价格页看清端点类型。知识库建好后，要在对话输入框的工具栏里选中它，问答才会用到。

## 第六步：MCP 工具从不被调用

MCP 从 Chatbox 1.14 开始支持，在「设置 → MCP」点「添加服务器」配置。如果服务器已经加好，但模型从不调用工具：

1. 在模型编辑里确认勾选了工具调用能力。官方只说能力决定 Chatbox 如何调用模型，没有直接写不勾选会不会带上工具，这一条是按第一步的规则推出来的检查项。
2. 确认模型本身支持工具调用，以模型厂商文档为准。官方 [模型与能力](https://chatboxai.app/zh/guide/concepts/models) 页也提醒，工具调用需要应用支持，Chatbox 目前支持部分工具功能。

## 第七步：验证是否修好

1. 先确认地址和 Key 本身没问题（把 `$OPENLUX_API_KEY` 换成你自己的 Key）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，剩下的问题在 Chatbox 的模型设置里；返回 401 说明 Key 错了或没带上。

2. 新开一个对话，选中已勾选视觉能力的视觉模型，发一张 JPG 或 PNG 小图，问「图里画的是什么」。能描述画面内容，说明图片已作为图片发给模型。
3. 换成非视觉模型、配置好 OCR 后，发一张带文字的图片，模型能复述图中文字，说明 OCR 生效。
4. 知识库导入一个纯文本文件，在输入框工具栏选中知识库后提问文档里的内容，回答能引用到文档，说明知识库可用。

如果小图在视觉模型上仍然不行，可以换一个官方列出的视觉模型对比；只在某个模型上出问题，就按该模型厂商文档核对图片输入要求。

## 参考资料

- Chatbox 官方帮助中心：[功能故障](https://chatboxai.app/zh/guide/faq/troubleshooting)（图片上传、文件上传、知识库、OCR、文档解析器）
- Chatbox 官方帮助中心：[模型与能力](https://chatboxai.app/zh/guide/concepts/models)（视觉、推理、工具调用）
- Chatbox 官方文档：[模型配置](https://docs.chatboxai.app/guides/providers)（不配置能力视为纯文本模型）、[导入第三方提供方配置](https://docs.chatboxai.app/guides/providers/import-config)（capabilities 与模型类型）
- Chatbox 官方文档：[本地知识库教程](https://docs.chatboxai.app/guides/knowledge-base)、[MCP](https://docs.chatboxai.app/guides/mcp)

还没有 Key 的话，可以先 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=chatbox-relay-image-file-vision-knowledge-base-fix&utm_content=footer)，在「令牌」页创建 Key 后填进 Chatbox。价格以官网价格页为准。

## 同专题文章

- [Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置](https://a37836323.github.io/openlux-api-guides/news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/)
- [VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查](https://a37836323.github.io/openlux-api-guides/news/vscode-byok-relay-model-not-showing-utility-model-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

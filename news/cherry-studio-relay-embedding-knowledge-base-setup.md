---
layout: default
title: "Cherry Studio 知识库怎么接中转 API 的嵌入模型：添加 text-embedding-3、选嵌入模型与重建知识库，资料一直处理中怎么办"
description: "Cherry Studio 知识库接中转 API 嵌入模型的设置步骤：在模型服务里添加 text-embedding-3、创建知识库时选嵌入模型、换模型要重建，以及资料一直处理中、知识库入口不可用、召回无结果的排查。"
permalink: /news/cherry-studio-relay-embedding-knowledge-base-setup/
date: 2026-11-21
---

> 更新日期：2026-11-21 · 一手来源：[Cherry Studio 官方文档](https://cherry-ai.com/docs/zh-cn/knowledge-base/create/)

# Cherry Studio 知识库怎么接中转 API 的嵌入模型：添加 text-embedding-3、选嵌入模型与重建知识库，资料一直处理中怎么办

在 Cherry Studio 里让知识库走中转 API 做向量检索，分三步：先在「设置 → 模型服务」里给中转服务商**添加一个嵌入模型**（如 `text-embedding-3-small`），再在创建知识库时把「嵌入模型」选成它（已有知识库在右上角「设置」里改），最后用「召回测试」验收。按 [Cherry Studio 官方文档「创建知识库」](https://cherry-ai.com/docs/zh-cn/knowledge-base/create/)，嵌入模型默认是「不使用」，这时知识库只用 BM25 关键词检索；选了云端嵌入模型，才变成关键词加向量的混合检索。

本文以 OpenLux 为例，适用于已经按 [Cherry Studio 怎么接入 OpenAI 兼容 / Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-relay-api-custom-provider-setup/) 配好对话模型的桌面端用户。界面名称以撰文时的官方文档为准，旧版本的按钮位置可能不同。

## 先判断：你的知识库要不要嵌入模型

官方文档把嵌入方式分成三种：

| 选择 | 检索方式 | 适合场景 | 前置条件 |
|---|---|---|---|
| 不使用（默认） | 仅 BM25 关键词检索 | 第一次体验、条款编号和专有名词多 | 无 |
| 云端嵌入模型 | BM25 + 向量混合检索 | 用户问法和资料原文差异大 | 对应模型服务能正常调用 |
| 本地嵌入模型 | BM25 + 本地向量检索 | 希望在本机完成向量化 | 先在「设置 → 本地模型」下载 |

官方建议先用「不使用」导入资料、做召回测试；原文关键词能命中、换种说法就找不到时，再加嵌入模型。用中转 API 的就是第二种「云端嵌入模型」。官方也提醒，云端嵌入模型的计费和数据处理取决于服务商。

## 第一步：在中转服务商里添加嵌入模型

嵌入模型和对话模型放在同一个服务商下，不用另建服务商。

1. 打开「设置 → 模型服务」，选中你给中转站建的服务商（如 `OpenLux`）。API 地址按官方「模型服务设置」的规则填**根地址** `https://api.openlux.ai`，不要写成完整接口路径。
2. 点「获取模型列表」，在弹出的「模型管理」里找到嵌入模型，点右侧 `+` 加入。官方说明只有加入列表的模型才会出现在各处的模型选择器里。
3. 列表里没有时，点「+」手动填模型 ID。官方说明可以点模型右侧的设置按钮编辑模型的名称、类型等数据。
4. 核对模型名下方显示的**实际 API 模型 ID**，再确认服务商右上角的启用开关已打开。

OpenLux 在售的嵌入模型以价格接口 `https://www.openlux.ai/api/pricing_new` 为准，撰文时有下面三个。向量维度和最大输入来自 [OpenAI 嵌入指南](https://developers.openai.com/api/docs/guides/embeddings)：

| 模型 ID | 默认向量维度 | 最大输入 |
|---|---|---|
| `text-embedding-3-small` | 1536 | 8192 token |
| `text-embedding-3-large` | 3072 | 8192 token |
| `text-embedding-ada-002` | 1536 | 8192 token |

**建库前就定好用哪个**：官方「模型与检索设置」写明，不同嵌入模型生成的向量不能混用，已有向量的知识库换嵌入模型要走「重建知识库」流程。

## 第二步：创建知识库并选择嵌入模型

按官方「创建知识库」的步骤：

1. 打开左侧导航「知识库」，点列表上方的新增按钮。
2. 输入能说明范围的名称，官方建议「对象 + 用途」，如「员工差旅制度」。
3. 「嵌入模型」选第一步加入的模型，例如 `OpenLux` 下的 `text-embedding-3-small`。
4. 点「创建」，进入空白知识库后点添加资料按钮，先导入一两份答案明确的文件或笔记。

**已有知识库加嵌入模型**：进入知识库，点右上角「设置」，在「嵌入模型」里选。官方区分两种情况：

| 原来的知识库 | 选了嵌入模型后会怎样 | 要做什么 |
|---|---|---|
| 只用 BM25（嵌入模型为「不使用」） | 可以直接建立向量索引 | 等索引完成后重新做召回测试 |
| 已经有向量，要换成另一个嵌入模型 | 界面进入「重建知识库」流程 | 官方建议先确认新模型可用，并保留完整备份 |

官方还提醒，精简备份不包含完整知识库数据文件，迁移或删除前要用完整备份。

## 第三步：等资料就绪，再做召回测试

资料添加后要等状态变成「就绪」。官方「添加与整理资料」页列出的处理办法：

- **长时间处理中**：可能是文件较大、解析器或模型不可用，检查原文件、文档处理和嵌入模型。
- **显示错误**：复制、读取、切分或索引失败，打开错误信息，按失败阶段处理。
- 切分、解析器或嵌入设置改了以后，旧资料不会自动套用新设置，要对资料执行「重新索引」。

资料就绪后，进入知识库的「召回测试」，输入 3～5 个答案明确、接近日常说法的问题。**成功标准**：正确来源排在前几条，片段同时包含回答所需的条件和结论。Top K 默认 6（可选 1～50），官方建议第一次先保留 6；「相似度阈值」只有选了重排模型才会显示，从 0.0 开始。

召回合格后，在普通对话输入区左下角点添加按钮，选「知识库」并勾选目标库。官方写明的使用前提：聊天模型支持工具调用、至少一条资料已就绪、当前消息没有同时附加文件。

## 用命令行确认 Key 和嵌入接口

Cherry Studio 里报错、又分不清是地址、Key 还是模型的问题时，在终端测两次（`$OPENLUX_API_KEY` 换成自己在「令牌」页 `https://www.openlux.ai/console/token` 创建的 Key，不要贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对；返回 401 说明 Key 错了或没带上。再按 OpenAI 嵌入指南的请求格式测一次嵌入接口：

```bash
curl https://api.openlux.ai/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -d '{"input": "测试文本", "model": "text-embedding-3-small"}'
```

返回里 `data[0].embedding` 是一串数字，说明嵌入模型可用，问题在 Cherry Studio 里的配置。

## 常见问题和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 创建知识库时嵌入模型下拉里没有中转的模型 | 嵌入模型没加入服务商的模型列表，或服务商没启用 | 回第一步加入模型、打开启用开关；手动添加的模型在设置按钮里核对类型 |
| 创建按钮不可用 | 名称为空，或所选模型已不可用 | 官方建议检查名称和模型；模型服务没配好时可先选「不使用」完成创建 |
| 资料一直处理中或显示错误 | 官方列出的原因有文件打不开、解析器或 OCR 不可用、模型服务未配置；走中转时常见的是 Key、地址或嵌入模型 ID 不对 | 打开错误信息，判断失败在读取、解析还是嵌入阶段；嵌入阶段失败就用上面两条 curl 分别验证 Key 和嵌入接口 |
| 报 401 | Key 错了或没带上 | 重新复制 Key，用 `/v1/models` 单独验证 |
| 报 404 | API 地址写成了 `https://api.openlux.ai/v1` 或完整接口路径，被重复拼接 | 改回根地址 `https://api.openlux.ai`（这一行是按官方「自动补路径」规则推出的，官方没写具体报错） |
| 换了嵌入模型要求重建 | 新旧模型的向量不能混用 | 先保留完整备份，再按「重建知识库」流程操作 |
| 对话里知识库入口不可用 | 聊天模型不支持工具调用，或消息带了附件 | 换支持工具调用的模型，移除附件，确认至少有一条资料就绪 |
| 召回测试完全没有结果 | 资料未就绪、正文不含答案、嵌入未完成或阈值过高 | 按官方顺序依次检查资料状态、正文、嵌入是否完成、阈值和 Top K |

## 参考资料

- Cherry Studio 文档：[创建知识库](https://cherry-ai.com/docs/zh-cn/knowledge-base/create/)（嵌入方式三选一、创建步骤、更换模型）
- Cherry Studio 文档：[模型与检索设置](https://cherry-ai.com/docs/zh-cn/knowledge-base/emb-models-info/)（检索链路、Top K、阈值、重建知识库）
- Cherry Studio 文档：[添加与整理资料](https://cherry-ai.com/docs/zh-cn/knowledge-base/sources/)（资料状态、重新索引）
- Cherry Studio 文档：[在对话中使用](https://cherry-ai.com/docs/zh-cn/knowledge-base/chat/)（使用前提）
- Cherry Studio 文档：[知识库常见问题](https://cherry-ai.com/docs/zh-cn/knowledge-base/troubleshooting/)
- Cherry Studio 文档：[模型服务设置](https://cherry-ai.com/docs/zh-cn/pre-basic/settings/providers/)（API 地址规则、添加模型）
- OpenAI：[嵌入指南](https://developers.openai.com/api/docs/guides/embeddings)（向量维度、最大输入、请求格式）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cherry-studio-relay-embedding-knowledge-base-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤添加嵌入模型。

## 同专题文章

- [n8n 知识库（RAG）怎么接中转 API 的嵌入模型：Embeddings OpenAI 节点、Base URL、text-embedding-3 与 Dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-embeddings-openai-vector-store-setup/)
- [Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-embedding-knowledge-base-setup/)
- [Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-tab-autocomplete-not-working-fix/)
- [Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-embedding-knowledge-base-rag-setup/)
- [Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

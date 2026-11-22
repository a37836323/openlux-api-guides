---
layout: default
title: "n8n 知识库（RAG）怎么接中转 API 的嵌入模型：Embeddings OpenAI 节点、Base URL、text-embedding-3 与 Dimensions 设置"
description: "n8n 知识库（RAG）接中转 API 的嵌入模型：OpenAI 凭据 Base URL 填 https://api.openlux.ai/v1，Embeddings OpenAI 节点选 text-embedding-3-small/large；中转地址下模型下拉框会混进对话模型，写入和查询要用同一模型和维度，Dimensions 与向量库维度一致；附 401、404、维度不一致、超出 token 上限的排查。"
permalink: /news/n8n-relay-embeddings-openai-vector-store-setup/
date: 2026-11-23
---

> 更新日期：2026-11-23 · 一手来源：[n8n 官方文档](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.embeddingsopenai/)

# n8n 知识库（RAG）怎么接中转 API 的嵌入模型：Embeddings OpenAI 节点、Base URL、text-embedding-3 与 Dimensions 设置

**直接回答：** 在 n8n 里给向量库（Vector Store）挂一个 **Embeddings OpenAI** 子节点，凭据选 Base URL 为 `https://api.openlux.ai/v1` 的 OpenAI 凭据，Model 选 `text-embedding-3-small`（或 `text-embedding-3-large`），写入文档和查询文档两边用**同一个嵌入模型、同一个维度**。模型下拉框里会出现对话模型，不要选错；向量库的维度要和嵌入输出长度一致。

本文适用于自建 n8n 或 n8n Cloud 里自己添加的 OpenAI 凭据，不涉及 n8n Cloud 的 Gateway credits。对话模型（OpenAI Chat Model）怎么接，见本站的 n8n 接入篇，这里只讲嵌入模型和知识库。

## 适用版本与依据

- 节点选项（Model、Base URL、Batch Size、Strip New Lines、Timeout）来自 n8n 官方文档 [Embeddings OpenAI](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.embeddingsopenai/)。
- 写入、查询的流程和“查询时要接写入时用的同一个嵌入模型”来自 n8n 官方文档 [Retrieve relevant context](https://docs.n8n.io/build/integrate-ai/understand-ai-components/retrieve-relevant-context/)。
- Dimensions、Encoding Format 两个选项、各项默认值、模型下拉框的过滤规则，按 n8n 官方仓库 master 分支 [节点源码](https://github.com/n8n-io/n8n/blob/master/packages/@n8n/nodes-langchain/nodes/embeddings/EmbeddingsOpenAI/EmbeddingsOpenAi.node.ts) 于 2026-11-23 核对；界面以你安装的版本为准。
- 默认向量长度、8192 token 输入上限、`dimensions` 参数来自 OpenAI 官方 [嵌入指南](https://developers.openai.com/api/docs/guides/embeddings) 和 [Embeddings API 参考](https://developers.openai.com/api/reference/resources/embeddings/methods/create)。

**前提：** 已在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建好 Key。2026-11-23 查 OpenLux 价格接口，在售的嵌入模型是 `text-embedding-3-small`、`text-embedding-3-large`、`text-embedding-ada-002`，以价格页为准。

## 第一步：准备指向中转的 OpenAI 凭据

Embeddings OpenAI 节点用的是 n8n 的 **OpenAI** 凭据类型（官方文档列出它和 OpenAI Chat Model 等节点共用这一类凭据）。新建或复用一个 OpenAI 凭据，按下表填写：

| 字段 | 填什么 | 说明 |
|---|---|---|
| API Key | OpenLux 令牌 | 以 `Authorization: Bearer` 请求头发出 |
| Organization ID (optional) | 留空 | 只有多组织的 OpenAI 账号才需要 |
| Base URL | `https://api.openlux.ai/v1` | 默认值是 `https://api.openai.com/v1`，改成中转地址，`/v1` 只写一次 |

按源码，凭据保存时会用这个 Base URL 请求 `/models` 做测试；测试不通过先回头核对 Key 和地址，不要往下走。

## 第二步：搭写入工作流（Insert Documents）

按 n8n 官方 RAG 文档，写入数据的顺序是：

1. 先放取数据的节点（读文件、表单上传等）。
2. 加一个 Vector Store 节点（例如 Simple Vector Store），操作选 **Insert Documents**。
3. 给它挂上 **Embeddings OpenAI** 子节点，选第一步的凭据。
4. 再挂一个 **Default Data Loader** 子节点负责切块，官方建议多数场景用 Recursive Character Text Splitter。

注意：官方说明 Simple Vector Store 只建议开发时用，数据存在内存里，n8n 重启就没了，而且同一实例的所有用户都能按 Memory Key 读到。正式使用请换成 PGVector、Qdrant、Pinecone 等持久化向量库。

## 第三步：Embeddings OpenAI 节点怎么填

| 选项 | 默认值 | 建议 |
|---|---|---|
| Model | 新版节点 `text-embedding-3-small` | 从下拉框选 `text-embedding-3-small` 或 `text-embedding-3-large` |
| Dimensions | 不加就不发送；加上后默认 1536 | 只对 text-embedding-3 系列有效，见下文 |
| Batch Size | 512（最大 2048） | 单个请求最多送多少个分块 |
| Strip New Lines | 开 | 去掉输入文本里的换行 |
| Timeout | -1（不限时） | 想避免请求一直挂着，可填一个秒数 |
| Encoding Format | Float | 保持默认 |
| Base URL（只有旧版节点有） | `https://api.openai.com/v1` | 新版（1.2）节点不显示这一项，改用凭据里的 Base URL；旧工作流里如果填过，它会覆盖凭据地址 |

**模型下拉框会混进对话模型。** 源码里的规则是：Base URL 是 OpenAI 官方地址时，下拉框只保留名字带 `embed` 的模型；换成中转地址后不再过滤，`/v1/models` 返回的全部模型都会列出来。一定要选名字里带 `embedding` 的那个：OpenLux 价格接口里嵌入模型的接口类型是 `Embedding`，对话模型没有这一类型，选成对话模型的话，向量化这一步会报错。

**维度怎么定。** 按 OpenAI 嵌入指南，`text-embedding-3-small` 默认输出 1536 维，`text-embedding-3-large` 默认 3072 维；`dimensions` 参数可以把向量截短（例如向量库最多只支持 1024 维时填 1024），代价是损失一些精度。API 参考写明 `dimensions` 只支持 text-embedding-3 及之后的模型，所以用 `text-embedding-ada-002` 时不要加 Dimensions 选项。

还有一个容易踩的地方：用 `text-embedding-3-large` 时，如果加了 Dimensions 选项却没改值，实际发送的是 1536，不是 3072。向量库建表或建索引时填的维度，要和这里最终的输出长度一致。

## 第四步：查询时接同一个嵌入模型

官方 RAG 文档写明：用 AI Agent 查询时，把向量库作为工具挂上，再“接上写入数据时用的同一个嵌入模型”。直接用 Vector Store 节点的 **Get Many** 操作查询也一样，节点上同样要挂 Embeddings OpenAI。

查询侧的 Model 和 Dimensions 必须与写入侧完全相同。写入后再换模型或改维度，旧向量和新问题的向量不在同一个空间里，检索结果会失准甚至报维度错误；这时应清空后用新设置重新写入。Simple Vector Store 的 Insert Documents 有 **Clear Store** 开关，打开后写入前会先清掉这个 Memory Key 下的数据。

## 怎么验证接通了

先在命令行确认地址和 Key（把 `$OPENLUX_KEY` 换成你的令牌）：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_KEY"

curl https://api.openlux.ai/v1/embeddings \
  -H "Authorization: Bearer $OPENLUX_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-3-small", "input": "测试文本"}'
```

第一条能列出模型，第二条返回里有 `embedding` 数组，说明地址和 Key 都对。然后在 n8n 里跑一次写入工作流，再用 Get Many 输入一个文档里明确有答案的问题，返回的分块里有对应原文，就算接好了。

## 常见报错与处理

| 现象 | 常见原因 | 怎么改 |
|---|---|---|
| 401 `Invalid token` | Key 填错、没带上或令牌已删除 | 回控制台重新复制令牌，更新凭据 |
| 404，报错形如 `Invalid URL (POST /v1/v1/...)` | Base URL 写成了 `.../v1/v1` | 改回 `https://api.openlux.ai/v1` |
| 凭据测试不过、下拉框加载不出模型 | Base URL 少了 `/v1`，或写错域名 | 按第一步核对，`/v1` 只写一次 |
| 写入时向量化失败 | Model 选成了对话模型 | 改选 `text-embedding-3-small` 等嵌入模型 |
| 用 ada-002 报参数错误 | 加了 Dimensions 选项 | 删掉 Dimensions，或换 text-embedding-3 系列 |
| 向量库报维度不一致 | 库的维度和嵌入输出长度不同，或写入、查询用了不同模型 | 统一模型和 Dimensions，必要时重建索引，参见本站 Pinecone 维度不匹配一文 |
| 单块或单批太大被拒 | 单个输入超过 8192 token，或一次请求的输入合计超过 300,000 token | 调小 Data Loader 的分块大小，或调小 Batch Size |
| 重启后查不到数据 | Simple Vector Store 只存在内存里 | 换持久化向量库后重新写入 |

最后一行的 token 上限来自 OpenAI API 参考对 `input` 的说明：每个输入不超过 8192 token，单个请求所有输入合计不超过 300,000 token，数组最多 2048 项。按这个上限推算，默认 Batch Size 512 时，平均每块超过约 586 token（300,000 ÷ 512），一批就可能超出单次请求合计上限。

## 开始使用

在 OpenLux 控制台创建令牌后，按上面的步骤把凭据和 Embeddings OpenAI 节点配好即可：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=n8n-relay-embeddings-openai-vector-store-setup&utm_content=footer)

## 同专题文章

- [Cherry Studio 知识库怎么接中转 API 的嵌入模型：添加 text-embedding-3、选嵌入模型与重建知识库，资料一直处理中怎么办](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-relay-embedding-knowledge-base-setup/)
- [Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-embedding-knowledge-base-setup/)
- [Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-tab-autocomplete-not-working-fix/)
- [Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-embedding-knowledge-base-rag-setup/)
- [Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

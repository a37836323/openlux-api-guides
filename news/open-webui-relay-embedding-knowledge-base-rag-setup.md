---
layout: default
title: "Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办"
description: "Open WebUI 知识库改用中转 API 的 OpenAI 嵌入模型：设置 > 文档里切换引擎、RAG_OPENAI_API_BASE_URL 与 Key、text-embedding-3 维度与 pgvector、换模型后重建索引，以及 'NoneType' object has no attribute 'encode'、429 等报错处理。"
permalink: /news/open-webui-relay-embedding-knowledge-base-rag-setup/
date: 2026-11-18
---

> 更新日期：2026-11-18 · 一手来源：[Open WebUI 官方文档](https://docs.openwebui.com/features/chat-conversations/rag/)

# Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办

结论先说：Open WebUI 的知识库和文档问答（RAG）默认用本机跑的 `sentence-transformers/all-MiniLM-L6-v2` 做嵌入。想改用中转 API 上的 OpenAI 嵌入模型，要在 **设置 > 文档（管理员）** 里把嵌入引擎换成 OpenAI，地址填 `https://api.openlux.ai/v1`，Key 填 OpenLux 令牌，模型填 `text-embedding-3-small` 这类在售 ID；**换完必须重建索引**，否则旧文档检索会乱。

本文适用于自己部署的 Open WebUI，聊天模型已经能用（聊天连接的配置见本站《Open WebUI 怎么接入 OpenAI 兼容 / Claude 中转 API》）。文中设置项和环境变量都来自 Open WebUI 官方文档：[RAG 功能说明](https://docs.openwebui.com/features/chat-conversations/rag/)、[环境变量参考](https://docs.openwebui.com/reference/env-configuration/)、[RAG 排错](https://docs.openwebui.com/troubleshooting/rag/)；嵌入模型的维度来自 [OpenAI 嵌入指南](https://developers.openai.com/api/docs/guides/embeddings)。本文没有用真实 Key 在 Open WebUI 里跑通过，请按文末的验证步骤自己确认。

## 聊天连接和嵌入连接是两套配置

很多人以为在「连接」里配好中转，知识库就自动走中转了。官方环境变量文档把两者分开：

| 用途 | 环境变量 | 默认值（官方） |
|---|---|---|
| 聊天用的 OpenAI 地址 | `OPENAI_API_BASE_URL` | `https://api.openai.com/v1` |
| 聊天用的 Key | `OPENAI_API_KEY` | 无 |
| 嵌入引擎 | `RAG_EMBEDDING_ENGINE` | 留空，即本机 SentenceTransformers；可选 `ollama`、`openai`、`azure_openai` |
| 嵌入模型 | `RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| 嵌入用的地址 | `RAG_OPENAI_API_BASE_URL` | 跟随 `OPENAI_API_BASE_URL` |
| 嵌入用的 Key | `RAG_OPENAI_API_KEY` | 跟随 `OPENAI_API_KEY` |

也就是说：引擎不改成 `openai`，就一直用本机模型；改成 `openai` 但没单独填嵌入地址和 Key，就沿用聊天那一套的环境变量。为避免混淆，建议嵌入的地址和 Key 单独填一遍。

## 第一步：确认中转上有可用的嵌入模型

OpenLux 价格接口（`https://www.openlux.ai/api/pricing_new`）里，端点类型标为 `Embedding` 的 OpenAI 嵌入模型有：

| 模型 ID | 默认向量维度（OpenAI 官方） | 说明 |
|---|---|---|
| `text-embedding-3-small` | 1536 | Open WebUI 排错页在「生产、有 API 预算」场景推荐它 |
| `text-embedding-3-large` | 3072 | 维度更高，向量库要能存得下（见第四步） |
| `text-embedding-ada-002` | — | 价格接口同样在售，本文以前两个为例 |

OpenAI 嵌入指南写明这三个模型单次输入上限都是 8192 token，请求路径是 `/v1/embeddings`。模型是否在售以价格接口当时的返回为准。

## 第二步：在后台把嵌入引擎换成 OpenAI

官方文档的说法是：在 **设置 > 文档（管理员）** 里更换 RAG 嵌入模型，引擎可选内置 SentenceTransformers、Ollama、OpenAI 或 Azure OpenAI。具体字段名称以你所用版本的界面为准，要填的就是三项：

1. 嵌入引擎：选 **OpenAI**。
2. 地址和 Key：地址填 `https://api.openlux.ai/v1`（官方默认值跟随 `OPENAI_API_BASE_URL`，即 `https://api.openai.com/v1`，写到 `/v1` 这一层）；Key 填在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建的令牌。
3. 嵌入模型：填 `text-embedding-3-small`，大小写、连字符要和价格接口一致。

保存后，上传一个小文档到知识库，能处理完成、没有报错，再进行下一步。

如果你用 Docker 环境变量配置，对应写法是：

```yaml
environment:
  RAG_EMBEDDING_ENGINE: openai
  RAG_EMBEDDING_MODEL: text-embedding-3-small
  RAG_OPENAI_API_BASE_URL: https://api.openlux.ai/v1
  RAG_OPENAI_API_KEY: 你的 OpenLux 令牌
```

注意：这几个变量在官方文档里都标为 ConfigVar。官方说明首次启动后，它们的值会存进数据库，之后重启**不再读环境变量**，以后台保存的值为准。所以已经启动过的实例，改环境变量常常「不生效」，直接在后台改最省事。

## 第三步：换了嵌入模型，一定要重建索引

官方 RAG 文档写得很明确：不同嵌入模型产生的向量在不同的向量空间里，互不兼容；换模型后不重建索引，对旧向量的检索结果会很差甚至没有意义。

- 知识库里的文档：到 **设置 > 文档（管理员）** 点 **Reindex**（排错页写作 Reindex Knowledge and Memory Vectors）。它会对每个知识库重新解析文件、重新切块、用当前嵌入模型重新嵌入，用户的记忆也会一起重建；官方提醒用付费嵌入模型时要考虑时间和费用。
- 直接传进聊天、没加入任何知识库的文件：重建索引**不处理**它们，官方说唯一办法是重新上传。

## 第四步：用 pgvector 等向量库时，先核对维度

默认向量库是 ChromaDB（slim 镜像默认 pgvector）。如果你用的是需要预先定义维度的向量库，官方环境变量文档里有几条要注意：

| 向量库 | 相关变量（默认值） | 官方说明 |
|---|---|---|
| pgvector | `PGVECTOR_INITIALIZE_MAX_VECTOR_LENGTH`（1536） | 初始化时的最大向量长度 |
| pgvector | `PGVECTOR_USE_HALFVEC`（False） | 上一项超过 2000 维时必须打开，因为 vector 类型上限 2000 维 |
| MariaDB Vector | `MARIADB_VECTOR_INITIALIZE_MAX_VECTOR_LENGTH`（1536） | 必须和嵌入模型维度一致；表建好后再改需要迁移数据，配置值和已有表不一致时后端会拒绝启动 |

默认值 1536 正好对应 `text-embedding-3-small`。要用 3072 维的 `text-embedding-3-large`，在 pgvector 上就得把维度设为 3072 并打开 halfvec。官方没写已建好的表怎么改维度，稳妥做法是第一次上传文档前就定好。拿不准就先用 `text-embedding-3-small`。

## 常见报错和处理

| 现象 | 官方给的原因 | 处理 |
|---|---|---|
| 上传文档报 `400: 'NoneType' object has no attribute 'encode'` | 嵌入模型没配好、没下载完整，或外部嵌入服务连不上 | 到 设置 > 文档 > 嵌入模型 再保存一次；用下一节的 curl 确认 Open WebUI 所在服务器能访问中转地址 |
| 批量导入时日志出现 `429 Rate limit reached` | 默认开启异步嵌入（`ENABLE_ASYNC_EMBEDDING` 为 true），会并发发请求 | 设 `RAG_EMBEDDING_CONCURRENT_REQUESTS` 为 5 或 10（默认 0 表示不限），或后台的 Embedding Concurrent Requests；仍不行就把 `ENABLE_ASYNC_EMBEDDING` 设为 False 改成顺序处理 |
| 换模型后答非所问、找不到原文 | 旧文档还是旧模型的向量 | 按第三步重建索引；聊天里单独上传的文件要重新上传 |
| 改了 `RAG_*` 环境变量没变化 | ConfigVar 首次启动后以数据库为准 | 在后台修改 |
| 想提速，把批量大小调大后出错 | `RAG_EMBEDDING_BATCH_SIZE` 默认 1，官方提醒只有接口支持批量时才能调大 | 先用下文的 curl 把 `input` 改成字符串数组发一次，确认返回的向量条数和输入条数一致，再调大 |
| 401、`Invalid token` | Key 错、复制不完整或没填 | 重新复制令牌，用 curl 单独验证 |
| 404 | 地址少了 `/v1`，或多写了 `/embeddings` 等路径 | 地址只填 `https://api.openlux.ai/v1` |

## 验证：先在服务器上用 curl 测通

在运行 Open WebUI 的服务器上执行（Docker 部署要保证容器也能访问这个地址）。第一条能列出模型，说明地址和令牌都对：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

第二条按 OpenAI 嵌入指南的请求格式发一次嵌入：

```bash
curl https://api.openlux.ai/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -d '{"input": "测试文本", "model": "text-embedding-3-small"}'
```

成功的标准：返回里有 `data[0].embedding` 数组，长度和第一步表格里的维度一致。两条都通过后，再回 Open WebUI 上传一个你知道答案的小文档，提一个只有文档里才有的问题，回答带出处就说明整条链路通了。

如果模型能查到文档却不用，可能不是嵌入的问题：官方排错页说明默认的原生函数调用模式下，模型要自己调用知识库工具，需要选工具调用能力强的模型，并确认模型的 Builtin Tools 里 Knowledge Base 没被关掉。

## 参考资料

- Open WebUI RAG 功能说明：https://docs.openwebui.com/features/chat-conversations/rag/
- Open WebUI 环境变量参考：https://docs.openwebui.com/reference/env-configuration/
- Open WebUI RAG 排错：https://docs.openwebui.com/troubleshooting/rag/
- OpenAI 嵌入指南：https://developers.openai.com/api/docs/guides/embeddings

还没有 OpenLux 账号的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=open-webui-relay-embedding-knowledge-base-rag-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤配置。

## 同专题文章

- [Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-embedding-knowledge-base-setup/)
- [Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-tab-autocomplete-not-working-fix/)
- [Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)
- [n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查](https://a37836323.github.io/openlux-api-guides/news/n8n-ai-agent-relay-prompt-content-null-session-fix/)
- [Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办](https://a37836323.github.io/openlux-api-guides/news/cline-cli-relay-api-auth-baseurl-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

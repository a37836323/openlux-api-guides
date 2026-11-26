---
layout: default
title: "LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置"
description: "LangChain OpenAIEmbeddings 接中转 API 的嵌入模型：base_url 填 https://api.openlux.ai/v1，按官方建议设 check_embedding_ctx_length=False 发送原文，model 选 text-embedding-3-small/large，写入和查询用同一模型和 dimensions；附 401、404 /v1/v1、少写 /v1、批量超限、维度不一致的排查。"
permalink: /news/langchain-openaiembeddings-relay-api-base-url-setup/
date: 2026-11-27
---

> 更新日期：2026-11-27 · 一手来源：[LangChain 官方 OpenAIEmbeddings API 参考](https://reference.langchain.com/python/langchain-openai/embeddings/base/OpenAIEmbeddings)

# LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置

**直接回答：** 用 `langchain-openai` 的 `OpenAIEmbeddings` 接 OpenAI 兼容的中转嵌入接口，要改三处：`base_url` 填 `https://api.openlux.ai/v1`，`api_key` 填 OpenLux 令牌，`model` 填 `text-embedding-3-small`（或 `text-embedding-3-large`）。另外按 LangChain 官方对 OpenAI 兼容服务的建议，加上 `check_embedding_ctx_length=False`，让它直接发送原始文本，不先切成 token 再发送。写入向量库和查询时，要用同一个模型、同一个维度。

本文只讲 Python 版 `OpenAIEmbeddings` 做 RAG 的嵌入部分。对话模型 `ChatOpenAI` 怎么接，见本站的 LangChain 接入篇。

## 适用版本与依据

- `base_url` 的读取顺序、`check_embedding_ctx_length`、`chunk_size`、`embedding_ctx_length`、`dimensions`、`skip_empty`、`max_retries` 等参数的含义和默认值，来自 LangChain 官方 [OpenAIEmbeddings API 参考](https://reference.langchain.com/python/langchain-openai/embeddings/base/OpenAIEmbeddings)（2026-11-27 核对）。
- 安装方式、向量库写入和检索示例，来自 LangChain 官方 [OpenAIEmbeddings 集成文档](https://docs.langchain.com/oss/python/integrations/embeddings/openai)。
- 默认向量长度和 `dimensions` 的作用，来自 OpenAI 官方 [嵌入指南](https://platform.openai.com/docs/guides/embeddings)；单条 8192 token、单请求合计 300,000 token、数组最多 2048 项的上限，来自 OpenAI [Embeddings API 参考](https://platform.openai.com/docs/api-reference/embeddings/create)。

**前提：**

- 已安装 `langchain-openai`：`pip install -qU langchain-openai`。
- 已在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建好 Key。

2026-11-27 查 OpenLux 价格接口，在售的嵌入模型有 `text-embedding-3-small`、`text-embedding-3-large`、`text-embedding-ada-002`，接口类型都标为 `Embedding`。具体以价格页为准。

## 第一步：填 base_url 和 Key

官方 API 参考写明，`base_url`（也可写作 `openai_api_base`）在“经代理或服务模拟器转发”时才需要填，读取顺序是先匹配到的生效：

| 顺序 | 写法 | 谁读取 |
|---|---|---|
| 1 | 构造时传 `base_url=`（或 `openai_api_base=`） | LangChain |
| 2 | 环境变量 `OPENAI_API_BASE` | LangChain，初始化时读取 |
| 3 | 环境变量 `OPENAI_BASE_URL` | 底层 `openai` SDK |

Key 可以用 `api_key=` 传入，也可以设环境变量 `OPENAI_API_KEY`。最直接的写法：

```python
import os
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    base_url="https://api.openlux.ai/v1",
    api_key=os.environ["OPENLUX_API_KEY"],
    check_embedding_ctx_length=False,
)
```

`base_url` 写到 `/v1` 为止，后面的 `/embeddings` 由 SDK 自己拼上，不要多写一个 `/v1`，也不要漏掉。如果你在同一台机器上还设过 `OPENAI_API_BASE`，构造时显式传的 `base_url` 优先生效。

## 第二步：为什么要加 check_embedding_ctx_length=False

`check_embedding_ctx_length` 默认是 `True`。按官方说明，这时 LangChain 会先检查每段输入的 token 数，把超过 `embedding_ctx_length`（默认 8191）的文本自动拆开，发给接口的是 token 而不是原文。

API 参考在“OpenAI 兼容 API（如 OpenRouter、Ollama、vLLM）”的提示里写明：用非 OpenAI 的服务时，设 `check_embedding_ctx_length=False`，直接发送原始文本，因为很多服务不支持 token 输入。中转平台也属于这种情况，建议照做。

设成 `False` 后有一个代价：LangChain 不再替你检查长度、自动拆分超长文本。所以文档要先用文本切分器（Text Splitter）切成小块，保证每块不超过 OpenAI 规定的单条 8192 token。

官方提示里还提到，可以把 `encoding_format` 设为 `'float'`，避免 base64 编码带来的问题。它不是 `OpenAIEmbeddings` 的独立参数；按 API 参考，`model_kwargs` 用来传“`create` 调用支持、但没有单独列出的参数”，所以可以这样写：`model_kwargs={"encoding_format": "float"}`。能正常返回向量时，不用加。

另一个参数 `tiktoken_enabled=False` 会改用 HuggingFace `transformers` 分词。官方说明对非 OpenAI 服务更推荐 `check_embedding_ctx_length=False`，因为它完全跳过分词，所以不用改这一项。

## 第三步：选模型和维度

| 参数 | 默认值 | 建议 |
|---|---|---|
| `model` | 需自己填 | `text-embedding-3-small` 或 `text-embedding-3-large`，只填价格接口里在售的嵌入模型 |
| `dimensions` | `None`（不发送） | 只对 text-embedding-3 及之后的模型有效；向量库有维度上限时再填 |
| `chunk_size` | 1000 | 每批最多送多少段文本，长文本多时调小 |
| `skip_empty` | `False` | 遇到空字符串时，是跳过还是报错 |
| `max_retries` | 2 | 生成时的最大重试次数 |
| `request_timeout` | — | 请求超时时间，想避免请求一直挂着时设一个秒数 |

**维度怎么定。** 按 OpenAI 嵌入指南，`text-embedding-3-small` 默认输出 1536 维，`text-embedding-3-large` 默认输出 3072 维。`dimensions` 可以把向量截短，例如向量库最多只支持 1024 维时填 1024。`text-embedding-ada-002` 不支持 `dimensions`，用它时不要传这个参数。向量库建表或建索引时填的维度，要和最终输出的长度一致。

**批量大小。** OpenAI API 参考规定，单个请求所有输入合计不超过 300,000 token。`chunk_size` 默认每批 1000 段，平均每段超过 300 token 时（300,000 ÷ 1000），一批就可能超过这个上限。文档切得较长时，把 `chunk_size` 调小，例如 200。

## 第四步：写入和查询用同一个 embeddings

官方集成文档给的流程是：用 `embeddings` 建向量库并写入文本，再 `as_retriever()` 检索。向量库在背后调用 `embed_documents(...)` 给文档生成向量，调用 `embed_query(...)` 给问题生成向量：

```python
from langchain_core.vectorstores import InMemoryVectorStore

vectorstore = InMemoryVectorStore.from_texts(
    ["OpenLux 提供 OpenAI 兼容的接口地址"],
    embedding=embeddings,
)
retriever = vectorstore.as_retriever()
print(retriever.invoke("OpenLux 的接口地址是什么")[0].page_content)
```

查询时用的 `model` 和 `dimensions`，必须和写入时完全相同。写入后再换模型或改维度，旧向量和新问题的向量不在同一个空间里，检索结果会不准，甚至报维度错误。这种情况下，要清空后用新设置重新写入。`InMemoryVectorStore` 顾名思义把数据存在内存里，程序退出就没了，正式使用请换成持久化的向量库。

## 怎么验证接通了

先在命令行确认地址和 Key（把 `$OPENLUX_API_KEY` 换成你的令牌）：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，就说明地址和 Key 都对。然后在 Python 里跑一次：

```python
vec = embeddings.embed_query("测试文本")
print(len(vec))
```

不传 `dimensions` 时，`text-embedding-3-small` 应打印 1536；传了就应等于你填的值。再跑上一节的检索示例，返回的正是写入的那段原文，就算接好了。

## 常见报错与处理

| 现象 | 常见原因 | 怎么改 |
|---|---|---|
| 401 `Invalid token` | Key 填错、没传上，或者令牌已删除 | 回控制台重新复制令牌；确认 `api_key` 或 `OPENAI_API_KEY` 读到的是 OpenLux 令牌 |
| 404 `Invalid URL (POST /v1/v1/embeddings)` | `base_url` 写成了 `.../v1/v1` | 改回 `https://api.openlux.ai/v1` |
| 拿不到向量，程序在处理返回结果时报错（报错内容不一定提到地址） | `base_url` 少了 `/v1`：2026-11-27 核对，这时 `https://api.openlux.ai/embeddings` 返回的是网页 HTML，不是 JSON | 补上 `/v1` |
| 报 401，但报错信息是 OpenAI 官方的（如 `Incorrect API key provided`） | 请求还是发到了 OpenAI 官方：没传 `base_url`，环境变量也没设，或者设在了别的进程里 | 按第一步的顺序表核对，最稳妥的做法是构造时显式传 `base_url` |
| 地址和 Key 都对，向量化仍然报错 | 可能是 `check_embedding_ctx_length` 还是默认的 `True`，发出的是 token，而官方提示很多兼容服务不支持 token 输入 | 设为 `False` 再试 |
| 单块或单批太大被拒 | 单段超过 8192 token，或一批合计超过 300,000 token | 先用切分器把文本切小，再调小 `chunk_size` |
| 用 ada-002 报参数错误 | 传了 `dimensions` | 删掉 `dimensions`，或者换 text-embedding-3 系列 |
| 向量库报维度不一致 | 库的维度和输出长度不同，或者写入、查询用了不同模型 | 统一模型和 `dimensions`，必要时重建索引 |

## 开始使用

在 OpenLux 控制台创建令牌后，按上面的步骤配好 `OpenAIEmbeddings` 即可：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=langchain-openaiembeddings-relay-api-base-url-setup&utm_content=footer)

## 同专题文章

- [LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/langchain-chatopenai-relay-api-base-url-setup/)
- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)
- [如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？](https://a37836323.github.io/openlux-api-guides/news/how-to-access-pardig-satweave-weather-datasets/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

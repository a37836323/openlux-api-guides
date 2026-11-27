---
layout: default
title: "LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置"
description: "LangChain（Python）接 OpenAI 兼容中转 API：ChatOpenAI 传 base_url=https://api.openlux.ai/v1、api_key 和在售模型 ID，init_chat_model 加 model_provider=\"openai\"，或设 OPENAI_BASE_URL；附 base_url 读取优先级、/v1/models 验证、Responses API 自动切换与 reasoning_content 丢失等限制，以及 401、404、模型不存在排查。"
permalink: /news/langchain-chatopenai-relay-api-base-url-setup/
date: 2026-11-26
---

> 更新日期：2026-11-26 · 一手来源：[LangChain 官方文档](https://docs.langchain.com/oss/python/integrations/chat/openai)

# LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置

结论先说：LangChain（Python）接 OpenAI 兼容的中转 API，用 `langchain-openai` 包里的 `ChatOpenAI` 就行，给它三样东西：`base_url="https://api.openlux.ai/v1"`、`api_key=<你的 OpenLux 令牌>`、`model=<价格接口里在售的模型 ID>`。用 `init_chat_model` 时多加一个 `model_provider="openai"`。如果不想改代码，也可以只设环境变量 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。

依据是 LangChain 官方文档 [ChatOpenAI 集成页](https://docs.langchain.com/oss/python/integrations/chat/openai) 的「Credentials」一节（base URL 的读取顺序）和「API scope」提示，以及 [Models 页](https://docs.langchain.com/oss/python/langchain/models) 的「Base URL and proxy settings」一节。

## 适用范围和前提

- **适用对象**：Python 版 LangChain，模型对象来自 `ChatOpenAI` 或 `init_chat_model(..., model_provider="openai")`。安装命令按官方写法：`pip install -U langchain-openai`；用 `init_chat_model` 还要装 `langchain` 包本身。
- **官方是否支持自定义地址**：支持。官方原话是，如果请求要经过代理或服务模拟器，可以设置 base URL；Models 页也写明，实现了 OpenAI Chat Completions API 的服务商，可以通过 `base_url` 参数接入。
- **要准备的东西**：在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建一个令牌；从价格接口 `https://www.openlux.ai/api/pricing_new` 选一个 `supported_endpoint_types` 含 `openai` 的模型。2026-11-26 查询时，`gpt-6.1-sol`、`claude-opus-5-5`、`gemini-3.5-flash`、`deepseek-v4.1-flash` 都含 `openai`，具体以查询时为准。

## base_url 的三种写法和优先级

官方给出的读取顺序是「先匹配到的生效」：

| 优先级 | 写法 | 由谁读取 | 适合场景 |
|---|---|---|---|
| 1 | 代码里传 `base_url=`（或 `openai_api_base=`） | LangChain | 同一程序要同时连官方和中转 |
| 2 | 环境变量 `OPENAI_API_BASE` | LangChain，在初始化时读取 | 老项目沿用的变量名 |
| 3 | 环境变量 `OPENAI_BASE_URL` | 底层 `openai` SDK | 不改代码，整台机器或容器都走中转 |

三种写法填的都是 `https://api.openlux.ai/v1`，写到 `/v1` 为止。OpenLux 的 OpenAI 兼容入口实际请求的路径是 `/v1/chat/completions` 和 `/v1/models`，后面的 `/chat/completions` 由 SDK 自己拼。

常见的坑：代码里传了 `base_url`，环境里又留着旧的 `OPENAI_API_BASE`，以为改了环境变量就生效。按上表，代码里的参数优先，环境变量不起作用。排查时先确认实际生效的是哪一层。

## 配置步骤

**写法一：直接用 ChatOpenAI**

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-6.1-sol",
    base_url="https://api.openlux.ai/v1",
    api_key=os.environ["OPENLUX_API_KEY"],
)
print(llm.invoke("用一句话介绍你自己").content)
```

`OPENLUX_API_KEY` 是你自己起的变量名，用来避免把令牌写进代码。

**写法二：用 init_chat_model**

官方示例的写法是 `model_provider="openai"` 加 `base_url` 和 `api_key`：

```python
import os
from langchain.chat_models import init_chat_model

llm = init_chat_model(
    "claude-opus-5-5",
    model_provider="openai",
    base_url="https://api.openlux.ai/v1",
    api_key=os.environ["OPENLUX_API_KEY"],
)
```

**写法三：只设环境变量**

```bash
export OPENAI_BASE_URL=https://api.openlux.ai/v1
export OPENAI_API_KEY=你的OpenLux令牌
```

之后代码里的 `ChatOpenAI(model="...")` 不用再传地址和 Key。注意：这样设置以后，这个变量由底层 `openai` SDK 读取，同一环境里其他基于 `openai` SDK、又没有显式传地址的程序也会走中转。

## 用 /v1/models 和最小请求验证

先绕开 LangChain，确认地址和令牌本身没问题：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的OpenLux令牌"
```

能列出模型，说明地址和令牌都对；返回 401 就是令牌错了或没带上。然后在 Python 里跑上面写法一的 `invoke`，能打印出一句回复，就说明 LangChain 这一层也配好了。最后把 `model` 换成你要用的模型 ID 再跑一次，确认这个模型名在售。

## 用中转时要知道的几个限制

- **非标准字段会丢**：官方说明 `ChatOpenAI` 只按 OpenAI 官方 API 规范处理，第三方服务商返回的非标准字段（例如 `reasoning_content`、`reasoning`、`reasoning_details`）不会被提取或保留。如果你的程序要读 DeepSeek 这类模型的思考内容，`ChatOpenAI` 拿不到；官方建议这类扩展了接口格式的服务商改用专用集成包。
- **有些功能会自动改走 Responses API**：官方说明，用到内置工具（如联网、文件搜索）、会话状态管理、推理输出，或设置了 `reasoning` 参数、`use_responses_api=True` 时，`ChatOpenAI` 会改走 Responses API，也就是请求 `/v1/responses`。在 OpenLux 价格接口里，GPT 系列标了 `openai-response`，而 Claude、Gemini、DeepSeek 没有标 `openai-response`。用这几类模型时不要打开这些选项，保持走 Chat Completions。
- **流式默认不带用量**：官方说明，设了 `OPENAI_BASE_URL` 时，`stream_usage` 默认关闭，因为很多非 OpenAI 端点不支持流式返回 token 用量。需要用量统计时，显式传 `stream_usage=True`。
- **重试次数**：官方 Models 页「Connection resilience」一节写明 `ChatOpenAI` 默认最多重试 2 次。网络错误、429 和 5xx 会自动重试，401、404 不会重试。网络不稳时可以调大 `max_retries` 和 `timeout`。

## 常见报错

| 现象 | 原因 | 怎么改 |
|---|---|---|
| 401，`Invalid token` | 令牌错了、没带上，或者实际生效的是环境里的另一个 Key | 用上面的 curl 单独验证令牌；代码里显式传 `api_key` |
| 404，`Invalid URL`，路径里有两个 `/v1` | `base_url` 写成了 `.../v1/v1`，或者在 `/v1` 后面又手动拼了路径 | `base_url` 只写到 `https://api.openlux.ai/v1` |
| 拿不到正常回复，请求路径不对 | `base_url` 少写了 `/v1`，只填了 `https://api.openlux.ai`，SDK 会请求 `/chat/completions` 而不是 `/v1/chat/completions` | 补上 `/v1`。不带 `/v1` 的写法是给 Anthropic Messages 客户端用的，不适用于 ChatOpenAI |
| 模型不存在 | `model` 填了官方文档示例里的名字，中转上没有这个 ID | 从价格接口复制在售 ID，确认它的 `supported_endpoint_types` 含 `openai` |
| 改了环境变量不生效 | 代码里传的 `base_url` 优先级更高 | 按上面的优先级表检查，去掉多余的那一层 |
| 读不到思考内容 | `ChatOpenAI` 不保留 `reasoning_content` 等非标准字段 | 这是官方说明的行为，不是中转故障 |

## 开始使用

在 OpenLux 控制台创建令牌，先跑一遍 `/v1/models` 的 curl，再把地址、令牌和模型 ID 填进 `ChatOpenAI`：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=langchain-chatopenai-relay-api-base-url-setup&utm_content=footer)

## 同专题文章

- [Hugging Face Chat UI 怎么接入 OpenAI 兼容中转 API：OPENAI_BASE_URL、Key 与模型设置（npm / Docker）](https://a37836323.github.io/openlux-api-guides/news/huggingface-chat-ui-relay-api-openai-base-url-setup/)
- [LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/langchain-openaiembeddings-relay-api-base-url-setup/)
- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

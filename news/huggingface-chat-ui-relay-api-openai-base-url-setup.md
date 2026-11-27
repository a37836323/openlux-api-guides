---
layout: default
title: "Hugging Face Chat UI 怎么接入 OpenAI 兼容中转 API：OPENAI_BASE_URL、Key 与模型设置（npm / Docker）"
description: "Hugging Face Chat UI 自部署时怎么接 OpenAI 兼容中转 API：OPENAI_BASE_URL 填带 /v1 的地址、OPENAI_API_KEY 填令牌，npm 与 Docker 两种写法，MODELS 打开图片和工具，以及模型不加载、401、404、403 的排查。"
permalink: /news/huggingface-chat-ui-relay-api-openai-base-url-setup/
date: 2026-11-28
---

> 更新日期：2026-11-28 · 一手来源：[Hugging Face Chat UI 官方文档](https://huggingface.co/docs/chat-ui/index)

# Hugging Face Chat UI 怎么接入 OpenAI 兼容中转 API：OPENAI_BASE_URL、Key 与模型设置（npm / Docker）

结论先说：Hugging Face 开源的 Chat UI（HuggingChat 的同款界面）只需要两个环境变量就能接中转 API——`OPENAI_BASE_URL` 填带 `/v1` 的地址，`OPENAI_API_KEY` 填中转的令牌。官方文档写明它「connects to any OpenAI-compatible API endpoint」，并且会自动从 `${OPENAI_BASE_URL}/models` 拉取模型列表，不需要手动登记模型。

本文依据 [Chat UI 官方文档](https://huggingface.co/docs/chat-ui/index)（首页、Configuration Overview、Running Locally、Running on Docker、Common Issues、MCP Tools 各页），适用于自己部署 Chat UI 的场景（源码 `npm` 运行或官方 Docker 镜像）。hf.co/chat 上的 HuggingChat 是官方托管的在线版，不在本文范围。

## 要填的配置一览

Chat UI 通过环境变量配置：默认值在 `.env`，自己的设置写在 `.env.local` 或直接作为环境变量传入。接 OpenLux 时这样填：

| 环境变量 | 填什么 | 说明 |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.openlux.ai/v1` | 必须带 `/v1`；Chat UI 会请求 `${OPENAI_BASE_URL}/models` |
| `OPENAI_API_KEY` | OpenLux 控制台「令牌」页创建的 Key | 在 [令牌页](https://www.openlux.ai/console/token) 创建 |
| `MONGODB_URL` | 开发时可不填；生产填自己的 MongoDB 连接串 | 不填时用内置数据库，数据存到 `./db` |
| `MODELS` | 可选，JSON5 数组 | 只用来改某个模型的显示名、图片、工具等属性 |
| `TASK_MODEL` | 可选，填一个模型 ID | 标题生成等内部任务用哪个模型；不填就用当前对话模型 |

为什么是 `https://api.openlux.ai/v1`：官方表格里各家的写法都带版本路径，例如 Hugging Face 是 `https://router.huggingface.co/v1`、OpenRouter 是 `https://openrouter.ai/api/v1`、Ollama 是 `http://127.0.0.1:11434/v1`。OpenLux 的 OpenAI 兼容入口同样是 `https://api.openlux.ai/v1`，拼上 `/models` 后正好是模型列表接口。

## 方式一：源码运行（npm）

按 Running Locally 页的步骤：

1. 克隆 `huggingface/chat-ui` 仓库并进入目录。
2. 在项目根目录新建 `.env.local`，写入：

```ini
OPENAI_BASE_URL=https://api.openlux.ai/v1
OPENAI_API_KEY=你的OpenLux令牌
```

3. 安装并启动开发模式：

```bash
npm install
npm run dev -- --open
```

开发模式下不设 `MONGODB_URL` 也能跑，Chat UI 会用内置的 MongoDB，把数据存在 `./db` 目录。

正式部署时，官方建议用独立的 MongoDB（本机 Docker 起一个，或用 MongoDB Atlas），然后执行 `npm run build` 和 `npm run preview`，服务默认监听 `http://localhost:4173`。

## 方式二：官方 Docker 镜像

官方提供两个镜像：`ghcr.io/huggingface/chat-ui-db` 自带 MongoDB（推荐快速上手），`ghcr.io/huggingface/chat-ui` 需要外部 MongoDB。带内置数据库的写法：

```bash
docker run -p 3000:3000 \
  -e OPENAI_BASE_URL=https://api.openlux.ai/v1 \
  -e OPENAI_API_KEY=你的OpenLux令牌 \
  -v chat-ui-data:/data \
  ghcr.io/huggingface/chat-ui-db
```

官方建议用 `--env-file .env.local` 代替 `-e` 传 Key，避免令牌留在 shell 历史里。用外部 MongoDB 时改用 `ghcr.io/huggingface/chat-ui` 镜像，再加 `-e MONGODB_URL=...`；MongoDB 跑在宿主机上时，官方示例用 `host.docker.internal` 访问。

## 选模型、开图片与工具

启动后，模型下拉框里的内容来自 `https://api.openlux.ai/v1/models` 的返回。选模型时注意：

- Chat UI 走 OpenAI 兼容接口，请选 OpenLux 价格页上标注支持 `openai` 的模型。例如 2026-11-28 价格接口里，`gpt-6.2-astra`、`claude-sonnet-5-5`、`deepseek-v4.1-flash`、`gemini-3.5-flash`、`qwen3.8-max` 都带 `openai` 类型；以价格页当前在售为准。
- 想让某个模型显示「上传图片」，在 `MODELS` 里把它的 `multimodal` 设为 `true`；前提是该模型本身支持看图。
- 想用 MCP 工具，但模型没有声明支持工具调用，可把 `supportsTools` 设为 `true`。工具服务器由管理员用 `MCP_SERVERS` 配置，或由用户在界面里「MCP Servers → Add Server」添加。

`MODELS` 写在 `.env.local` 里，`id` 必须和 `/models` 返回的 ID 完全一致（下面只演示写法，模型能不能看图、调工具以模型本身为准）：

```ini
MODELS=`[
  { "id": "claude-sonnet-5-5", "name": "Claude Sonnet 5.5", "multimodal": true, "supportsTools": true }
]`
```

另外，对话标题默认由当前对话模型生成。如果不想让大模型做这类小任务，可以用 `TASK_MODEL` 指定一个轻量的在售模型，例如 `TASK_MODEL=gemini-3.5-flash-lite`。

## 验证地址和 Key 是否正确

Chat UI 界面里没有模型时，先在命令行直接请求模型列表，把问题范围缩小到「地址和 Key」还是「Chat UI 本身」：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer 你的OpenLux令牌"
```

成功标准：返回 JSON，里面能看到模型 ID 列表。能列出来，说明 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY` 都填对了；再重启 Chat UI，让它重新读取环境变量。

## 常见报错与排查

| 现象 | 原因 | 改法 |
|---|---|---|
| 模型下拉框是空的，curl 返回 401 `Invalid token` | Key 填错、多了空格或令牌已删除 | 去令牌页重新复制 Key，改 `OPENAI_API_KEY` 后重启 |
| curl 返回 404 `Invalid URL (GET /v1/v1/models)` | `OPENAI_BASE_URL` 写成了 `.../v1/v1`，或手动拼了 `/v1/models` | 只填到 `https://api.openlux.ai/v1` |
| 模型列表加载不出来，curl 拿到的是一段网页 HTML | `OPENAI_BASE_URL` 少了 `/v1`，请求落到了网站首页 | 补上 `/v1` |
| 打开对话提示 403「You don't have access to this conversation」 | 用 HTTP 访问但 Cookie 按 HTTPS 设置 | 官方推荐用 Nginx、Caddy 反向代理上 HTTPS；必须用 HTTP 时设 `COOKIE_SECURE=false`，并让 `PUBLIC_ORIGIN` 和实际访问地址一致 |
| 选了模型但没有图片上传按钮 | 模型没被标为多模态 | `MODELS` 里给该模型加 `"multimodal": true` |
| 启用了 MCP 服务器，模型从不调用工具 | 模型没有声明支持工具 | `MODELS` 里加 `"supportsTools": true`，并换一个支持工具调用的模型 |
| 生产环境报数据库连接错误 | `MONGODB_URL` 不对、Atlas 没放行 IP 或账号没有读写权限 | 按官方 Common Issues 逐项检查 |

官方 Common Issues 对「Models not loading」给的检查顺序是：`OPENAI_BASE_URL` 是否正确且能访问 → `OPENAI_API_KEY` 是否有效 → 接口是否能在 `${OPENAI_BASE_URL}/models` 返回模型。上面的 curl 正好对应这三步。

## 小结

Chat UI 接中转 API 的关键只有一处：`OPENAI_BASE_URL` 填 `https://api.openlux.ai/v1`，不多不少一个 `/v1`。Key 放进 `.env.local` 或 `--env-file`，模型会自动出现在下拉框；要图片和工具，再用 `MODELS` 给对应模型打开 `multimodal`、`supportsTools`。

还没有 OpenLux 账号的话，可以先 [注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=huggingface-chat-ui-relay-api-openai-base-url-setup&utm_content=footer)，在令牌页创建 Key 后按上面的步骤填入。

## 同专题文章

- [LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/langchain-openaiembeddings-relay-api-base-url-setup/)
- [LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/langchain-chatopenai-relay-api-base-url-setup/)
- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

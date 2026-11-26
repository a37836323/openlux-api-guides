---
layout: default
title: "GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置"
description: "GitHub Copilot CLI 接入 OpenAI 兼容或 Claude 中转 API 的步骤：在 ~/.copilot/providers.json 配置 openai / anthropic 类型提供方、baseUrl 是否带 /v1、apiKey 与模型 ID，或用 COPILOT_PROVIDER_* 环境变量，并给出 /v1/models 验证方法和 401、404、模型看不到、配置不生效等报错处理。"
permalink: /news/github-copilot-cli-relay-api-providers-json-setup/
date: 2026-11-22
---

> 更新日期：2026-11-22 · 一手来源：[GitHub Docs](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-llm-models)

# GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置

GitHub Copilot CLI 支持自带模型提供方（官方叫 BYOK）。在 `~/.copilot/providers.json` 里写一个 `openai` 类型（OpenAI 兼容接口）或 `anthropic` 类型（Claude Messages 接口）的提供方，再登记模型，就能在终端里用中转 API 的模型。走自己的提供方时**不需要登录 GitHub**，但 `/delegate`、GitHub MCP 服务器和 GitHub 代码搜索会用不了。本文的设置项名称和规则都来自 GitHub 官方文档 [Adding LLM models to GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-llm-models) 和 [配置目录参考](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference#providersjson)，下面以 OpenLux 为例。

## 开始前要知道的几点

- **模型要求**：官方要求所选模型和端点同时支持**工具调用**（function calling）和**流式输出**，不支持时 CLI 会报错；官方建议上下文窗口至少 128k token。所以请选对话模型，不要选嵌入、图片或语音模型。
- **两种配置方式**：一是 `providers.json` 文件，可以写多个提供方和模型；二是旧的 `COPILOT_PROVIDER_*` 环境变量，只能配一个提供方。建议只用其中一种，原因见后面的报错对照。
- **Key 是明文保存**：`providers.json` 里的 Key 按明文存。官方特别说明，在 JSON 里写 `$MY_API_KEY` 这类内容会被当成普通文字，**不会**去读环境变量。不要把这个文件提交到代码仓库。
- **版本差异**：本文按 GitHub 文档 2026 年 11 月的版本写。你本机版本的说明可以运行 `copilot help providers` 查看（官方文档提供了这条命令）。

## 需要准备的配置项

| 项目 | OpenAI 兼容（`openai` 类型） | Claude（`anthropic` 类型） |
|---|---|---|
| `baseUrl` | `https://api.openlux.ai/v1`（官方要求带 API 前缀 `/v1`） | `https://api.openlux.ai`（不带 `/v1`，与官方示例 `https://api.anthropic.com` 写法一致） |
| `apiKey` | OpenLux 控制台「令牌」页创建的令牌 | 同左 |
| `wireApi` | 默认 `completions`；GPT 模型也可以填 `responses` | 不填（官方说明 Anthropic 类型会忽略这一项） |
| 模型 `id` 示例 | `gpt-6.1-sol` | `claude-sonnet-5-5` |

令牌在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。模型名要用 OpenLux 价格页上在售的模型 ID。每个模型支持哪些接口，看价格页的端点标注：GPT 系列标了 OpenAI 和 Responses，Claude 系列标了 Anthropic 和 OpenAI，所以 Claude 也可以走 `openai` 类型。

## 第一步：先用 /v1/models 验证地址和令牌

在写配置之前，先在终端里确认令牌可用：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer 你的OpenLux令牌"
```

返回模型列表，就说明地址和令牌都没问题。返回 401 `Invalid token`，说明令牌填错或没带上，这时改 CLI 配置没有用，要先把令牌弄对。

## 第二步：写 ~/.copilot/providers.json

这个文件放在 CLI 配置目录里，通常是 `~/.copilot/providers.json`，没有就新建一个。如果文件里已经有提供方和模型，要在原来的内容上追加，不要整个覆盖。下面的例子同时配了 OpenAI 兼容和 Claude 两个提供方：

```json
{
  "providers": [
    {
      "name": "openlux",
      "type": "openai",
      "baseUrl": "https://api.openlux.ai/v1",
      "apiKey": "在这里填 OpenLux 令牌"
    },
    {
      "name": "openlux-claude",
      "type": "anthropic",
      "baseUrl": "https://api.openlux.ai",
      "apiKey": "在这里填 OpenLux 令牌"
    }
  ],
  "models": [
    { "id": "gpt-6.1-sol", "provider": "openlux" },
    { "id": "claude-sonnet-5-5", "provider": "openlux-claude" }
  ]
}
```

官方对这个文件的要求：

- 文件必须是合法 JSON，**不能写注释，也不能有多余的逗号**。JSON 不合法，或者提供方、模型条目有错，CLI 会直接报配置错误。
- 每个提供方必填的只有 `name` 和 `baseUrl`；`name` 不能包含 `/`。
- 每个模型的 `provider` 必须和某个提供方的 `name` 完全一致。
- 模型的 `id` 默认就是发给提供方的模型名。如果你想用自己起的别名，要把真实模型名写进 `wireModel`，再把 `modelId` 设成 CLI 认识的模型 ID，CLI 才能按这个模型的能力和上限工作。
- CLI 不认识的模型，输入上限默认按 128000 token 算，可能超过模型实际能接收的长度。可以在模型条目里按模型官方说明填 `maxPromptTokens` 和 `maxOutputTokens`（正整数）。填大了也不会让模型真的能处理更多内容。

## 第三步：启动并选择模型

改完文件后**重启 CLI**，然后用「提供方名/模型 ID」启动：

```bash
copilot --model openlux/gpt-6.1-sol
```

会话里也可以输入 `/model`，在模型选择器里切换。配置好的模型会和你 GitHub 账号自带的模型列在一起。想把某个模型设成默认，用 `/model --global`。发一句简单的话，能正常回复，并且能按要求调用工具（比如读取当前目录的文件），就说明接通了。

## 用环境变量配置（单个提供方）

如果只想临时用一个提供方，又不想把 Key 写进文件，可以用官方的旧方式：环境变量。

```bash
export COPILOT_PROVIDER_TYPE=openai
export COPILOT_PROVIDER_BASE_URL=https://api.openlux.ai/v1
export COPILOT_PROVIDER_API_KEY=你的OpenLux令牌
export COPILOT_MODEL=gpt-6.1-sol
copilot
```

用自定义提供方时，`COPILOT_MODEL` 必须填，也可以改用 `--model` 参数。如果要走 Claude 接口，把类型改成 `anthropic`，Base URL 改成不带 `/v1` 的 `https://api.openlux.ai`。官方还说明：只要设置了这些提供方环境变量，不管你有没有登录 GitHub，模型请求都会走它们。

## 常见报错对照

| 现象 | 常见原因 | 处理 |
|---|---|---|
| 401 `Invalid token` | 令牌错了，或者在 JSON 里写了 `$变量名`（官方说明它会被当成普通文字） | 把令牌原文填进 `apiKey`，先用第一步的 curl 验证 |
| 404 `Invalid URL (POST /v1/v1/messages)` | `anthropic` 类型的 `baseUrl` 多写了 `/v1` | 改成 `https://api.openlux.ai` |
| `openai` 类型请求失败 | `baseUrl` 少了 `/v1`，或者填成了完整的 `/v1/chat/completions` | 只填到 `https://api.openlux.ai/v1` |
| 模型不存在 | `id` 或 `wireModel` 不是在售模型 ID，大小写或版本号不对 | 对照价格页或 `/v1/models` 返回的列表 |
| 选择器里看不到配置好的模型 | 模型的 `provider` 和提供方的 `name` 对不上，或者改完没重启 | 核对名称后重启 CLI |
| 启动时报配置错误 | JSON 里有注释、多余逗号，或条目缺 `name`、`baseUrl` | 改成合法 JSON |
| 改了环境变量或文件没效果 | 两种方式同时存在。官方两处说法不完全一致：配置目录参考说 `providers.json` 写了提供方或模型，就优先于 `COPILOT_PROVIDER_*` 变量；排错一节说用 `COPILOT_PROVIDERS_CONFIG` 显式指定的文件优先于环境变量，没有显式指定时，环境变量配置的提供方优先于默认的 `providers.json` | 只留一种配置方式：用文件就取消这些环境变量，用环境变量就移走 `providers.json` 里的条目 |
| 报请求太大 | CLI 按默认上限发了超出模型能力的内容 | 在模型条目里填 `maxPromptTokens`、`maxOutputTokens` |
| 选了某个模型后一直报错 | 模型不支持工具调用或流式（官方说明这种情况会报错） | 换成对话模型，比如 GPT、Claude 系列 |

官方排错一节的总原则是：请求失败时，依次检查 API 地址、凭据、模型名和接口类型（`wireApi`）。

## 不登录 GitHub 时会少哪些功能

官方说明，用自己的提供方时 CLI 直接连你配置的提供方，不需要 GitHub 账号或令牌。但没登录 GitHub 时，下面三项用不了：

- `/delegate`：要用 GitHub 服务器上的 Copilot 云端代理；
- GitHub MCP 服务器：要登录后才能调用 GitHub API；
- GitHub 代码搜索。

需要这些功能时，可以再用 `/login` 登录 GitHub。官方说明两者可以同时用：选你配置的模型回答问题，同时用上 `/delegate`、代码搜索这些 GitHub 托管的功能；用环境变量配置提供方时，不管登没登录 GitHub，模型请求都走这些变量指定的提供方。另外，官方提到设置 `COPILOT_OFFLINE=true` 后，CLI 不再连 GitHub 服务器、不发遥测，只请求你配置的提供方。但提供方是远程地址时，提示词和代码上下文仍然会通过网络发给它。

## 开始使用

想在 Copilot CLI 里用 OpenAI 兼容或 Claude 接口调用 GPT、Claude 模型，可以先注册 OpenLux 账号，在「令牌」页创建令牌后按上面的步骤配置：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=github-copilot-cli-relay-api-providers-json-setup&utm_content=footer)

## 同专题文章

- [LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/langchain-openaiembeddings-relay-api-base-url-setup/)
- [LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/langchain-chatopenai-relay-api-base-url-setup/)
- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)
- [如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？](https://a37836323.github.io/openlux-api-guides/news/how-to-access-pardig-satweave-weather-datasets/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

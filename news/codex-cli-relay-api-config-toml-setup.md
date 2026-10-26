---
layout: default
title: "Codex CLI 怎么接入 OpenAI 兼容中转 API：config.toml 自定义 provider、Key 与模型设置"
description: "Codex CLI 接入 OpenAI 兼容中转 API 的配置步骤：在 ~/.codex/config.toml 定义自定义 model provider，base_url 带 /v1、env_key 放令牌、wire_api 只支持 responses，用 profile 文件按需切换，以及 401、模型不存在、项目配置被忽略等报错处理。"
permalink: /news/codex-cli-relay-api-config-toml-setup/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[OpenAI Codex 官方文档](https://developers.openai.com/codex/config-advanced)

# Codex CLI 怎么接入 OpenAI 兼容中转 API：config.toml 自定义 provider、Key 与模型设置

先说结论：Codex CLI 接中转，要在用户配置文件 `~/.codex/config.toml` 里加一个自定义模型提供方（model provider）：`base_url` 填中转地址，`env_key` 填存放令牌的环境变量名，再用 `model_provider` 选中它、用 `model` 指定模型。接 OpenLux 时，`base_url` 填 `https://api.openlux.ai/v1`。另外要注意，Codex 目前只走 Responses 协议，模型要选支持 Responses 端点的那些。

本文的配置项名称都来自 OpenAI 官方 Codex 文档 [Advanced Configuration](https://developers.openai.com/codex/config-advanced) 和 [Configuration Reference](https://developers.openai.com/codex/config-reference)，适用于 Codex CLI。官方 [认证说明](https://developers.openai.com/codex/auth) 写明 Codex cloud 只能用 ChatGPT 登录，所以云端任务不在本文范围。

## 开始前要知道的三点

- **只支持 Responses 协议**：Configuration Reference 写明 `wire_api` 支持的值是 `responses`，不填时默认也是它。所以中转必须提供 `/v1/responses`。OpenLux 的 Responses 入口是 `https://api.openlux.ai/v1`，实际请求路径是 `/v1/responses`。
- **只能写在用户级配置**：项目目录里的 `.codex/config.toml` 会忽略 `model_provider`、`model_providers`、`openai_base_url`，Codex 启动时会打印警告。所以要写进 `~/.codex/config.toml`。
- **提供方 ID 不能用保留名**：`openai`、`ollama`、`lmstudio` 是内置提供方的保留 ID，自定义提供方不能用，本文用 `openlux`。

## 需要准备的配置项

| 配置项 | 填什么 | 说明 |
|---|---|---|
| `model_providers.openlux.base_url` | `https://api.openlux.ai/v1` | 提供方的 API 基础地址，带 `/v1` |
| `model_providers.openlux.env_key` | `OPENLUX_API_KEY` | 存放令牌的环境变量**名**，不是令牌本身 |
| `model_providers.openlux.wire_api` | `responses` | 可以省略，默认就是它 |
| `model_provider` | `openlux` | 选用上面定义的提供方，默认值是 `openai` |
| `model` | 如 `gpt-5.6-sol` | 用 OpenLux 在售且支持 Responses 端点的模型 ID |

`OPENLUX_API_KEY` 是本文起的变量名，可以换成别的，只要 `env_key` 和你导出的变量名一致就行。令牌在 OpenLux 控制台的「令牌」页创建：`https://www.openlux.ai/console/token`。价格以官网价格页为准，本文不写具体数字。

## 第一步：先用 /v1/models 验证地址和令牌

先在终端导出令牌（换成你自己的），再请求模型列表：

```bash
export OPENLUX_API_KEY=你的OpenLux令牌
curl -sS https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

结果怎么判断：

- 返回 JSON，里面有一串模型 ID：地址和令牌都对，记下你要用的 ID。
- 返回 `401`：令牌错误、没带上、复制不完整，或者已经被删除，回控制台重新复制或创建。

列表里的模型不一定都能在 Codex 里用，因为 Codex 只发 Responses 请求。OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里，每个模型的 `supported_endpoint_types` 列出它支持的协议，含 `openai-response` 的才适合配进 Codex。按 2026-10-27 的价格接口，`gpt-6.1-sol`、`gpt-5.6-sol`、`gpt-5.5`、`gpt-5.3-codex` 都在其中；而 `claude-opus-5-5` 只列了 `anthropic` 和 `openai`，不适合配在 Codex 里。

## 第二步：写 ~/.codex/config.toml

官方说明 Codex 的用户级配置在 `~/.codex/config.toml`。按官方 Advanced Configuration 里自定义提供方的写法，加入下面几行：

```toml
model = "gpt-5.6-sol"
model_provider = "openlux"

[model_providers.openlux]
name = "OpenLux"
base_url = "https://api.openlux.ai/v1"
env_key = "OPENLUX_API_KEY"
wire_api = "responses"
```

几点说明：

- `model` 和 `model_provider` 是顶层配置，要写在所有 `[...]` 表头之前。按 TOML 语法，写在 `[model_providers.openlux]` 后面会被当成这张表的字段。
- `env_key` 只写变量名。Codex 启动时从环境里读这个变量，所以要在启动 `codex` 的同一个终端里导出，或者写进 `~/.bashrc`、`~/.zshrc` 这类启动文件。
- 官方另有 `experimental_bearer_token` 可以直接写令牌，但文档明确不推荐，建议用 `env_key`。
- **不要**在这个提供方里写 `requires_openai_auth = true`。官方说明开启它后提供方改用 OpenAI 登录（ChatGPT 或 OpenAI API Key），并且会忽略 `env_key`。

可选项：同一张表里还能设置 `request_max_retries`（HTTP 请求重试次数，默认 4）、`stream_max_retries`（流式中断重试次数，默认 5）和 `stream_idle_timeout_ms`（流式空闲超时，默认 300000 毫秒）。默认值能用就不用改。

## 第三步：只在需要时走中转（profile 文件）

如果平时还用 ChatGPT 登录跑 Codex，只想偶尔切到中转，可以用 profile 文件。官方说明从 0.134.0 版起，`[profiles.*]` 表和 `profile = "..."` 写法都不再支持；改为运行 `codex --profile 名字` 时，先读 `~/.codex/config.toml`，再用 `~/.codex/名字.config.toml` 覆盖，文件里写顶层配置项。

做法：`[model_providers.openlux]` 这张表留在 `~/.codex/config.toml`（没被 `model_provider` 选中时不影响默认用法），把下面两行放进 `~/.codex/openlux.config.toml`：

```toml
model = "gpt-5.6-sol"
model_provider = "openlux"
```

之后用 `codex --profile openlux` 启动就走中转，直接运行 `codex` 还是原来的设置。

## 第四步：在 Codex 里确认生效

在已经导出 `OPENLUX_API_KEY` 的同一个终端里运行 `codex`（或 `codex --profile openlux`），发一条简短消息。能正常回复，说明地址、令牌和模型都已生效。如果启动时提示项目配置里的某些键被忽略，说明提供方写进了项目的 `.codex/config.toml`，按第二步移到用户级文件。

关于内置提供方：官方提供了 `openai_base_url`，用来改内置 `openai` 提供方的地址（官方示例是数据驻留地址），并说明不要自己写 `[model_providers.openai]`。接第三方中转时，本文用独立的自定义提供方，令牌单独放在 `OPENLUX_API_KEY` 里，不用改动内置提供方和原有登录。

## 常见报错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `401`，鉴权失败 | 启动 `codex` 的终端里没有这个环境变量，或令牌错误、已删除 | 在同一终端重新 `export`；先跑第一步的 curl 确认令牌 |
| 令牌没被使用，仍要求 OpenAI 登录 | 提供方里写了 `requires_openai_auth = true`，此时 `env_key` 被忽略 | 删掉这一行 |
| 改了配置但没生效，启动有警告 | `model_provider` 或 `model_providers` 写在项目 `.codex/config.toml` 里 | 移到 `~/.codex/config.toml` |
| 请求路径不对导致失败（如 404） | `base_url` 少了 `/v1` | 填 `https://api.openlux.ai/v1`；官方示例的 `base_url` 也写到 `/v1` 这一层，如 `https://api.mistral.ai/v1` |
| 模型不存在 | 模型 ID 拼错、不在在售列表，或该模型不支持 Responses | 用 `/v1/models` 返回的完整 ID，并确认 `supported_endpoint_types` 含 `openai-response` |
| 想用 Chat Completions 协议 | Configuration Reference 列出的 `wire_api` 可用值只有 `responses` | 改回 `responses` 或删掉这一行 |
| 提供方 ID 冲突 | 用了 `openai`、`ollama` 或 `lmstudio` | 换一个 ID，如 `openlux` |
| 流式输出中途断开 | 网络中断，或空闲超过 `stream_idle_timeout_ms` | 先查网络；需要时调大 `stream_idle_timeout_ms` 或 `stream_max_retries` |

## 开始使用

按上面四步走完，curl 能列出模型、`codex` 发消息能正常回复，就说明接入成功。还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=codex-cli-relay-api-config-toml-setup&utm_content=footer)。

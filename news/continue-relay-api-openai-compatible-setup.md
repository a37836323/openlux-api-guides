---
layout: default
title: "Continue 怎么接入 OpenAI 兼容 / Claude 中转 API：apiBase、Key 与模型设置"
description: "Continue 接入 OpenAI 兼容 / Claude 中转 API 的方法：在 config.yaml 里用 provider: openai，apiBase 填 https://api.openlux.ai/v1，配置 apiKey 与模型 ID；附 gpt-5 系列默认走 /responses、Agent 模式 tool_use、401/404/模型不存在的排查。"
permalink: /news/continue-relay-api-openai-compatible-setup/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[Continue 官方文档](https://docs.continue.dev/customize/model-providers/top-level/openai)

# Continue 怎么接入 OpenAI 兼容 / Claude 中转 API：apiBase、Key 与模型设置

在 Continue 里接中转 API，做法是在本地 `config.yaml` 的 `models` 里加一条 `provider: openai` 的模型，把 `apiBase` 改成中转地址、`apiKey` 填自己的 Key、`model` 填中转在售的模型 ID。[Continue 官方 OpenAI 配置页](https://docs.continue.dev/customize/model-providers/top-level/openai)写明：使用 OpenAI 兼容服务商时，修改 `apiBase` 即可（原文 “you can change the `apiBase`”），官方示例的 `apiBase` 写到 `/v1` 这一层。

本文以 OpenLux 为例，适用于在 VS Code 或 JetBrains 里使用 Continue 扩展、想用自己的 Key 调用中转模型的读者。设置项名称以撰文时的官方文档为准，界面可能随版本变化。

## 适用范围和前提

开始之前确认三件事：

1. **能打开本地 config.yaml**。按 [Continue 配置说明](https://docs.continue.dev/customize/deep-dives/configuration)，本地用户级配置保存在用户主目录：macOS / Linux 是 `~/.continue/config.yaml`，Windows 是 `%USERPROFILE%\.continue\config.yaml`。第一次使用 Continue 时会自动生成这个文件。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。
3. **知道要用的模型 ID**。只能填中转站在售的模型 ID，OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，例如 `gpt-5.6-sol`、`claude-sonnet-5-5`。

## 各字段怎么填

| 字段 | 官方含义 | 接 OpenLux 时填写 |
|---|---|---|
| `name` | 在配置里标识模型的名称，不能重复（必填） | 自己起，如 `OpenLux gpt-5.6-sol` |
| `provider` | 模型的服务商（必填） | `openai` |
| `model` | 具体模型名（必填） | 价格接口里的模型 ID，如 `gpt-5.6-sol` |
| `apiBase` | 覆盖默认的 API 地址 | `https://api.openlux.ai/v1` |
| `apiKey` | 官方示例中填服务商 API Key 的字段 | 在「令牌」页创建的 Key |
| `roles` | 这个模型承担的角色，默认 `[chat, edit, apply, summarize]` | 一般保持默认 |

两点说明：

- `apiBase` 带 `/v1`：Continue 官方文档里 OpenAI 兼容的示例都写成 `http://localhost:8000/v1`、`http://my-endpoint/v1` 这种写到 `/v1` 的形式；OpenLux 的 OpenAI 兼容入口也是 `https://api.openlux.ai/v1`。
- Claude 模型也可以走这一条：价格接口里 `claude-sonnet-5-5`、`claude-opus-5-5` 等模型的端点类型同时列有 `anthropic` 和 `openai`，可以用 `provider: openai` 加上面的 `apiBase` 来配置，`model` 填对应的 Claude 模型 ID，是否列出以 `/v1/models` 的返回为准。Continue 的 [Anthropic 配置页](https://docs.continue.dev/customize/model-providers/top-level/anthropic)只给了 `provider: anthropic` 加 `apiKey` 的写法，没有说明自定义 `apiBase` 的格式，所以本文不推荐用 Anthropic 服务商接中转。

## 配置步骤

1. 打开 `config.yaml`：官方给出的入口是点开聊天输入框右上方的配置下拉菜单，在「Local Config」旁边点齿轮图标；也可以直接用编辑器打开上面的文件路径。
2. 按下面的格式写入（文件顶部的 `name`、`version`、`schema` 三行是官方示例自带的，已有就不要重复）：

```yaml
name: My Config
version: 0.0.1
schema: v1
models:
  - name: OpenLux gpt-5.6-sol
    provider: openai
    model: gpt-5.6-sol
    apiBase: https://api.openlux.ai/v1
    apiKey: <你的 OpenLux Key>
```

3. 保存文件。官方说明从 IDE 里保存配置文件后，Continue 会自动刷新以应用改动。
4. 在 Continue 的模型选择处选中刚加的 `OpenLux gpt-5.6-sol`，发一条简单的问题。

想接多个模型，就在 `models` 下按同样格式再加几条，每条的 `name` 不要重复。`config.yaml` 里写着明文 Key，分享配置或截图前先删掉这一行。

## gpt-5 系列默认走 /responses，以及 Agent 模式的工具调用

这两点是 Continue 特有的，接中转时容易遇到：

- **Responses 端点**：官方原文是 “By default, Continue uses OpenAI's `/responses` endpoint for o-series and gpt-5 models”，也就是 o 系列和 gpt-5 模型默认请求 `/responses` 而不是 `/chat/completions`。OpenLux 的 Responses 入口同样在 `https://api.openlux.ai/v1` 下（路径 `/v1/responses`），`apiBase` 不用改。官方给的开关是在这条模型下加 `useResponsesApi: false`，让它改回 `/chat/completions`；官方举的场景是 OpenAI 返回组织未验证（organization must be verified）的错误。用中转时如果 gpt-5 系列模型在 Continue 里报错、而 `/v1/models` 验证正常，可以加这一行再试。注意价格接口里个别模型只列了 `openai-response` 端点（如 `gpt-5.4`），这类模型不要关掉 Responses。
- **Agent 模式**：[config.yaml 参考](https://docs.continue.dev/reference)写明 `capabilities` 里的 `tool_use` 用于开启函数/工具调用，是 Agent 模式所必需的；这个字段会覆盖 Continue 按服务商和模型名做的自动识别。如果所选模型本身支持工具调用，但 Continue 里用不了 Agent 模式，可以在这条模型下加 `capabilities: [tool_use]`；要上传图片则加 `image_input`。

## 验证是否接通

**在 Continue 里验证**：保存后选中这个模型，发一条简单的问题，能正常返回就算接通。

**用命令行确认地址和 Key**：如果 Continue 报错，又分不清是地址、Key 还是模型的问题，可以在终端请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题出在 `config.yaml` 上；返回 401 说明 Key 错了或没带上。顺便在返回列表里找一下 `model` 填的 ID，确认拼写一致。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 401 / 鉴权失败 | `apiKey` 填错、有多余空格，或没写这一行 | 重新从 OpenLux「令牌」页复制；用上面的 curl 单独验证 |
| 模型不存在 | `model` 不是在售 ID，或大小写、点号、连字符不一致 | 对照价格接口和 `/v1/models` 的返回重新填写 |
| 404 或路径不对 | `apiBase` 少写了 `/v1`，或多写了 `/chat/completions` 这类具体路径 | `apiBase` 只写到 `https://api.openlux.ai/v1` |
| gpt-5 系列报错、其他模型正常 | 默认走 `/responses` 端点 | 加 `useResponsesApi: false`（只列 `openai-response` 端点的模型除外） |
| Agent 模式不可用或不调用工具 | 自动识别没认出这个模型支持工具调用 | 模型本身支持工具调用时，加 `capabilities: [tool_use]` |
| 改了配置没生效 | 改错了文件，或 YAML 缩进有误 | 从「Local Config」齿轮图标打开确认是同一个文件，检查缩进后重新保存 |

404 那一行是按 OpenLux 入口的地址规则推出来的，Continue 官方文档没有直接写出多填或少填 `/v1` 时的报错内容。

## 参考资料

- Continue 文档：[OpenAI 配置](https://docs.continue.dev/customize/model-providers/top-level/openai)（OpenAI 兼容服务商改 `apiBase`、`useResponsesApi`、`useLegacyCompletionsEndpoint`）
- Continue 文档：[config.yaml Reference](https://docs.continue.dev/reference)（`models` 各字段、`roles`、`capabilities`）
- Continue 文档：[How to Configure Continue](https://docs.continue.dev/customize/deep-dives/configuration)（配置文件位置与打开方式）
- Continue 文档：[Anthropic 配置](https://docs.continue.dev/customize/model-providers/top-level/anthropic)（Anthropic 服务商写法）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=continue-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤写进 Continue 的 `config.yaml`。

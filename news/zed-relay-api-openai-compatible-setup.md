---
layout: default
title: "Zed 怎么接入 OpenAI 兼容 / Claude 中转 API：API URL、Key 与模型设置"
description: "Zed 编辑器接入 OpenAI 兼容 / Claude 中转 API 的方法：在 LLM Providers 用 Add Provider 添加 OpenAI 兼容（API URL 填 https://api.openlux.ai/v1）或 Anthropic 兼容提供方，Key 存钥匙串；附 settings.json 写法、Responses 模型设置、401/404/模型不存在排查。"
permalink: /news/zed-relay-api-openai-compatible-setup/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[Zed 官方文档](https://zed.dev/docs/ai/use-api-access)

# Zed 怎么接入 OpenAI 兼容 / Claude 中转 API：API URL、Key 与模型设置

在 Zed 编辑器里接中转 API，做法是在 Agent 设置的 LLM Providers 里点 `Add Provider`，添加一个 OpenAI 兼容（或 Anthropic 兼容）的提供方，填入提供方名称、API URL、模型 ID 和上下文窗口，再在提供方设置里填 Key。[Zed 官方 Use API Access 文档](https://zed.dev/docs/ai/use-api-access)写明：有自定义 base URL、模型 ID 和 API Key 时，就可以用 OpenAI 兼容端点（原文 “Use an OpenAI-compatible endpoint when you have a custom base URL, model ID, and API key”）；服务实现了 Anthropic Messages API（`/v1/messages`）时，可以用 Anthropic 兼容端点。

本文以 OpenLux 为例，适用于想用自己的 Key 在 Zed 内置 AI 功能里调用中转模型的读者。设置项名称以撰文时的 Zed 官方文档为准，界面可能随版本变化；官方文档没有写明从哪个版本开始提供这些设置项。

## 适用范围和前提

先确认三件事：

1. **不需要登录 Zed 账号**。[Zed 账号说明](https://zed.dev/docs/authentication)写明，不用 Zed 作为模型提供方时，可以不登录，自带 API Key 使用 AI 功能。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。
3. **知道要用的模型 ID**。只能填中转站在售的模型 ID，OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，例如 `gpt-6-astra`、`claude-opus-5-5`。

还要注意这套配置管哪些功能。按官方说明，这里配置的提供方用于 Zed Agent、Inline Assistant、Git 提交信息生成、对话摘要等 Zed 自己的 AI 功能；External Agents（如 Claude Agent、Codex）和 Terminal Threads 通常在各自的 agent 或命令行工具里单独配置模型和鉴权，[External Agents 文档](https://zed.dev/docs/ai/external-agents)写明给 Zed Agent 配的 Key 不会自动用到 Claude Agent 或 Codex 上。编辑预测（Edit Prediction）也在 `edit_predictions` 下单独设置。

## 选哪种提供方，地址带不带 /v1

| 提供方类型 | 适合的模型 | API URL 填写 | 依据 |
|---|---|---|---|
| OpenAI 兼容（`openai_compatible`） | GPT 系列，以及端点类型含 `openai` 的其他模型 | `https://api.openlux.ai/v1` | Zed 官方示例的 `api_url` 是 `https://example.com/v1`，写到 `/v1` 这一层 |
| Anthropic 兼容（`anthropic_compatible`） | Claude 系列 | `https://api.openlux.ai`（不带 `/v1`） | Zed 官方示例的 `api_url` 是 `https://api.someprovider.com`，只到域名；OpenLux 的 Anthropic 入口由客户端自己拼 `/v1/messages` |

价格接口里 Claude 模型（如 `claude-opus-5-5`、`claude-sonnet-5-5`）的端点类型同时列有 `anthropic` 和 `openai`，两种提供方都可以试；是否列出以 `/v1/models` 的返回为准。

## 在界面里添加提供方

1. 在命令面板执行 `agent: open settings`，打开 **Settings → AI → LLM Providers**。
2. 找到 `Add Provider`：
   - 接 OpenAI 兼容：填提供方名称（如 `openlux`）、API URL `https://api.openlux.ai/v1`、模型 ID（如 `gpt-6-astra`）和上下文窗口。
   - 接 Claude：选 `Anthropic`，填提供方名称（如 `OpenLux Claude`）、API URL `https://api.openlux.ai`、模型 ID（如 `claude-opus-5-5`）和上下文窗口。
3. 在提供方设置里填入 OpenLux 的 Key。官方说明通过 Zed 保存的 Key 存在系统钥匙串里，不写进 `settings.json`。
4. 上下文窗口填所选模型官方文档写的数值，不确定时去模型厂商文档核对，不要凭印象填。

## 用 settings.json 配置

也可以直接写设置文件。下面按 Zed 官方示例的格式改写，`max_tokens` 是上下文窗口，示例数值沿用官方示例，使用时换成所选模型的实际上下文窗口：

```json
{
  "language_models": {
    "openai_compatible": {
      "openlux": {
        "api_url": "https://api.openlux.ai/v1",
        "available_models": [
          { "name": "gpt-6-astra", "display_name": "OpenLux gpt-6-astra", "max_tokens": 128000 }
        ]
      }
    },
    "anthropic_compatible": {
      "OpenLux Claude": {
        "api_url": "https://api.openlux.ai",
        "available_models": [
          { "name": "claude-opus-5-5", "display_name": "OpenLux claude-opus-5-5", "max_tokens": 200000 }
        ]
      }
    }
  }
}
```

几个容易忽略的字段：

- **Key 不要写进 settings.json**，官方原文是 “Do not put API keys in `settings.json`”。可以在界面里填，也可以用环境变量：OpenAI 兼容提供方的变量名是提供方 ID 转成大写下划线再加 `_API_KEY`，上例 `openlux` 对应 `OPENLUX_API_KEY`。Anthropic 兼容提供方官方只给了 `Some Provider` 对应 `SOME_PROVIDER_API_KEY` 这一个例子，建议直接在界面里填。
- **只支持 Responses API 的模型**：官方说明把 `capabilities.chat_completions` 设为 `false`，Zed 就改用 Responses 端点。价格接口里个别模型只列了 `openai-response` 端点（如 `gpt-5.4`），这类模型要加这一项；OpenLux 的 Responses 入口同样在 `https://api.openlux.ai/v1` 下，地址不用改。
- **推理强度**：推理模型可以设 `reasoning_effort`，可选值为 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max`；界面里只提供非 `none` 的选项，要强制关闭推理得在 `settings.json` 里写 `none`。各模型实际接受哪些值，以模型官方文档为准。
- **Anthropic 兼容的提示缓存**：`prompt_caching` 默认是 `false`，打开后会发送 `cache_control` 断点。官方提示提供方拒绝这类请求时就保持关闭；中转是否接受本文未核实，先保持默认，确实需要时再打开，报错就关掉。
- 官方列出的默认能力里 `tools` 为 `true`、`images` 为 `false`，可以在每个模型的 `capabilities` 里改；把 `images` 改为 `true` 之前，先确认模型本身支持图片输入。

## 验证是否接通

**在 Zed 里验证**：用 `agent: new thread` 或点状态栏的 ✨ 图标打开 Agent Panel，点消息编辑框上的模型选择器（macOS 快捷键 `cmd-alt-/`，Linux/Windows 为 `ctrl-alt-/`），选中刚加的模型。官方提醒同一个模型可能由多个提供方提供，要看模型左侧的图标确认选的是你添加的提供方。发一条简单的问题，能正常返回就算接通。

**用命令行确认地址和 Key**：Zed 里报错又分不清原因时，在终端请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Zed 的配置上；返回 401 说明 Key 错了或没带上。顺便在返回列表里找一下填的模型 ID，确认拼写一致。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 401 / 鉴权失败 | Key 填错、有多余空格 | 重新从 OpenLux「令牌」页复制；用上面的 curl 单独验证 |
| 界面里改了 Key 仍然 401 | 设置了同名环境变量，官方说明非空环境变量优先于钥匙串 | 取消该环境变量后重启 Zed |
| 模型不存在 | 模型 ID 不是在售 ID，或大小写、点号、连字符不一致 | 对照价格接口和 `/v1/models` 的返回重新填写 |
| 404 或路径不对 | OpenAI 兼容少写了 `/v1`，或 Anthropic 兼容多写了 `/v1` | OpenAI 兼容填 `https://api.openlux.ai/v1`，Anthropic 兼容填 `https://api.openlux.ai` |
| 只支持 Responses 的模型报错 | Zed 默认走 Chat Completions | 该模型的 `capabilities.chat_completions` 设为 `false` |
| Claude Agent、Codex 里用不到这个 Key | External Agents 自己管鉴权和计费 | 按对应工具的方式单独配置 |
| 远程项目（SSH、开发容器）里找不到 Key | 官方说明 Key 和环境变量从本地 Zed 读取 | 在本机的 Zed 里配置 |

404 那一行是按 OpenLux 入口的地址规则推出来的，Zed 官方文档没有直接写出多填或少填 `/v1` 时的报错内容。

## 参考资料

- Zed 文档：[Use API Access](https://zed.dev/docs/ai/use-api-access)（OpenAI 兼容与 Anthropic 兼容端点、Key 存储与环境变量、适用功能）
- Zed 文档：[Agent Panel](https://zed.dev/docs/ai/agent-panel)（打开面板、切换模型）
- Zed 文档：[LLM Providers](https://zed.dev/docs/ai/llm-providers)（模型接入方式、Edit Prediction 单独配置）
- Zed 文档：[External Agents](https://zed.dev/docs/ai/external-agents)（Claude Agent、Codex 的鉴权说明）
- Zed 文档：[Authentication](https://zed.dev/docs/authentication)（自带 Key 不需要登录）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=zed-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤添加到 Zed。

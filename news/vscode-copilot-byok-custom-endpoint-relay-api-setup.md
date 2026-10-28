---
layout: default
title: "VS Code 怎么接入 OpenAI 兼容 / Claude 中转 API：Custom Endpoint、Key 与模型设置"
description: "VS Code 接入 OpenAI 兼容 / Claude 中转 API：按官方文档用 BYOK 的 Custom Endpoint 提供方，在 chatLanguageModels.json 里填 vendor、apiKey、apiType 和完整接口地址（/v1/chat/completions、/v1/responses、/v1/messages），用 /v1/models 验证；附 401、404、模型不显示、statefulResponses、补全不走 BYOK 等排查。"
permalink: /news/vscode-copilot-byok-custom-endpoint-relay-api-setup/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[VS Code 官方文档](https://code.visualstudio.com/docs/copilot/customization/language-models)

# VS Code 怎么接入 OpenAI 兼容 / Claude 中转 API：Custom Endpoint、Key 与模型设置

想在 VS Code 的 Chat 里用中转 API 调 GPT、Claude 模型，按 VS Code 官方文档，用的是「自带模型 Key（BYOK）」里的 **Custom Endpoint** 提供方：在 Language Models 编辑器里添加，再在 `chatLanguageModels.json` 里写模型 ID 和完整接口地址。它支持 Chat Completions、Responses 和 Anthropic Messages 三种 API 类型，OpenAI 兼容中转和 Claude 中转都能接。

先说清适用范围：官方写明 BYOK 只用于 **Chat 对话和后台辅助任务**；语义搜索、行内补全（代码补全）和依赖 embeddings 的功能仍然需要 GitHub 账号，不会走你接入的模型。本文依据 VS Code 官方文档 [AI language models in VS Code](https://code.visualstudio.com/docs/copilot/customization/language-models)。

## 适用范围和前提

- **不需要 Copilot 套餐也能用**：官方说明在 Local harness 会话里，BYOK 模型不登录 GitHub、没有 Copilot 套餐也可以用。
- **Copilot Business / Enterprise 用户**：组织管理员可以在 GitHub.com 的 Copilot 策略里关闭「Bring Your Own Language Model Key in VS Code」；官方 FAQ 说要由管理员开启这项策略后才能添加自己的 Key。
- **想在 Copilot harness 会话里用**：需要开启 `chat.agentHost.byokModels.enabled`，官方标注为实验功能，可能变化或移除。
- **旧配置已弃用**：官方说明 Custom Endpoint 取代了已弃用的「OpenAI Compatible」提供方，`github.copilot.chat.customOAIModels` 设置也已弃用。网上旧教程让你改这个设置的，按本文的新方式重新配。
- 你需要一个中转 Key：在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建。

## 第一步：在 Language Models 编辑器添加 Custom Endpoint

按官方步骤操作：

1. 在 Chat 的模型选择器里点齿轮图标「Manage Language Models」，或在命令面板运行 **Chat: Manage Language Models**。
2. 选 **Add Models**，在列表里选 **Custom Endpoint**。
3. 填一个分组名（group name），比如 `OpenLux`。它是模型选择器里的分组标签，之后还能改。
4. 填显示名称和 API Key（粘贴在 OpenLux 创建的 Key）。
5. 选 API 类型：**Chat Completions**、**Responses** 或 **Messages**。官方提醒要确认模型支持所选类型。
6. VS Code 会打开 `chatLanguageModels.json`，按下一步改好模型信息并保存。

## 第二步：三种 API 类型怎么选、地址怎么填

官方建议 `url` 直接写**包含接口路径的完整地址**，避免歧义。对应 OpenLux 的入口如下（模型 ID 来自 OpenLux 价格接口在售列表）：

| API 类型 | `apiType` 值 | 模型的 `url` | 适合的模型示例 | 默认鉴权头 |
|---|---|---|---|---|
| Chat Completions | `chat-completions`（默认） | `https://api.openlux.ai/v1/chat/completions` | `gpt-6-astra`、`claude-sonnet-5-5` | `Authorization: Bearer` |
| Responses | `responses` | `https://api.openlux.ai/v1/responses` | `gpt-5.4`（价格接口显示只支持 Responses 端点） | `Authorization: Bearer` |
| Messages | `messages` | `https://api.openlux.ai/v1/messages` | `claude-opus-5-5` | `x-api-key` |

如果 `url` 不写接口路径，官方规则是：地址末尾没有 `/v1` 这类版本段时，VS Code 先补 `/v1`，再补对应接口路径。比如 Responses 类型下 `https://my-host.example.com` 会变成 `https://my-host.example.com/v1/responses`。写完整地址就不用记这个规则。

## 第三步：写 chatLanguageModels.json

下面是按官方 Custom Endpoint 示例结构写的 Chat Completions 配置：

```json
[
  {
    "name": "OpenLux",
    "vendor": "customendpoint",
    "apiKey": "${input:openluxApiKey}",
    "apiType": "chat-completions",
    "models": [
      {
        "id": "gpt-6-astra",
        "name": "GPT-6 Astra (OpenLux)",
        "url": "https://api.openlux.ai/v1/chat/completions",
        "toolCalling": true,
        "vision": false,
        "maxInputTokens": 128000,
        "maxOutputTokens": 16000
      }
    ]
  }
]
```

各字段按官方说明这样填：

| 字段 | 填什么 | 官方说明要点 |
|---|---|---|
| `vendor` | `customendpoint` | 必须是这个值才走 Custom Endpoint |
| `apiKey` | `${input:变量名}` | 官方建议用输入变量存 Key，不要把明文 Key 写进文件 |
| `id` | 价格接口里的准确模型 ID | 这是实际发给 API 的模型名 |
| `name` | 自己认得出的显示名 | 只影响模型选择器显示 |
| `toolCalling` | 模型支持工具调用时设 `true` | 不支持工具调用的模型，在 agent 场景下不会出现在模型选择器里 |
| `vision` | 模型支持图片输入时设 `true` | 不确定就先设 `false` |
| `maxInputTokens` / `maxOutputTokens` | 按该模型文档的上下文窗口填 | 两者之和不能超过模型上下文窗口 |

上面示例里的 128000 / 16000 只是沿用官方示例的写法，请换成你所用模型文档写明的数值。也可以按官方说明加 `contextWindow` 字段填整个上下文窗口（输入加输出），这时可以省略 `maxInputTokens`，VS Code 会用 `contextWindow` 减去 `maxOutputTokens` 得出输入上限。

可选项：模型支持推理强度时，可加 `supportsReasoningEffort`（如 `["low", "medium", "high"]`，以模型文档为准）和 `reasoningEffortFormat`（`chat-completions`、`responses` 或 `messages`），模型选择器里会出现 Thinking Effort 选项。

## 第四步：验证地址和 Key

先在终端单独确认 Key 和地址是对的。`/v1/models` 能列出模型，就说明地址和 Key 都没问题：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的Key"
```

然后回到 VS Code，在 Chat 的模型选择器里找到 `OpenLux` 分组下的模型，发一句简单的话。能正常回复就算接通。官方提示：新加的模型没有立刻出现在选择器里，重启 VS Code。

如果没登录 GitHub，标题生成、提交信息等辅助功能会提示你配置辅助模型：按官方说明把 `chat.utilityModel` 和 `chat.utilitySmallModel` 指向你的 BYOK 模型，或把 `chat.byokUtilityModelDefault` 设为 Main Agent Model。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 返回 401 | Key 填错、复制不完整，或没存进 `apiKey` | 用上面的 curl 单独验证；在 Language Models 编辑器点该提供方的齿轮重新填 Key |
| Messages 类型 401，但同一个 Key 在 curl 里正常 | Messages 类型默认发 `x-api-key` 鉴权头，curl 用的是 Bearer | 可以按官方「Custom authentication headers」，在模型里加 `"requestHeaders": {"Authorization": "Bearer ${apiKey}"}`；写了这类鉴权头后 VS Code 不再发默认头 |
| 返回 404 | `url` 里 `/v1` 重复（如 `/v1/v1/chat/completions`）或接口路径写错 | 按第二步表格写完整地址 |
| 提示模型不存在 | `id` 与在售 ID 不一致，或填成了显示名 | 对照价格接口或 `/v1/models` 返回的 ID 复制 |
| `gpt-5.4` 等模型选 Chat Completions 一直失败 | 价格接口显示它只支持 Responses 端点 | 该模型的 `apiType` 改成 `responses`，`url` 改成 `/v1/responses` |
| Responses 类型多轮工具调用报缺少工具调用 | 官方说明 Responses 默认只发新增历史并带 `previous_response_id`，服务端不保留之前的响应时会出错 | 官方给无状态服务的做法：在该模型里加 `"statefulResponses": false`，改为每次发送完整历史（含工具调用和结果） |
| 模型选择器里看不到模型 | `toolCalling` 没设 `true`，或还没重启 | 确认模型支持工具调用后设为 `true`，再重启 VS Code |
| 代码补全还是原来的模型 | 官方说明行内补全不走 BYOK | 属正常现象，BYOK 只作用于 Chat 和辅助任务 |

## 参考资料

- VS Code 官方文档：[AI language models in VS Code](https://code.visualstudio.com/docs/copilot/customization/language-models)（Bring your own language model key、Add a custom endpoint model、Custom Endpoint configuration reference、Model configuration reference、Frequently asked questions 各节）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=vscode-copilot-byok-custom-endpoint-relay-api-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤填进 VS Code。

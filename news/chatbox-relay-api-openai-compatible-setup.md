---
layout: default
title: "Chatbox 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Host、Key 与模型设置"
description: "Chatbox 接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：按官方指南添加自定义提供商，API 模式选 OpenAI API 兼容，API Host 填 https://api.openlux.ai/v1、API Path 填 /chat/completions，新建模型并检查；附 401、404、模型不存在、Temperature 报错排查。"
permalink: /news/chatbox-relay-api-openai-compatible-setup/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[Chatbox 官方指南](https://chatboxai.app/zh/guide/byok/zenmux)

# Chatbox 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Host、Key 与模型设置

在 Chatbox 里接中转 API，走的是「设置 → 模型提供方 → 添加 → 添加自定义提供商」：API 模式选「OpenAI API 兼容」，填 API Host、API Path 和 API Key，再在「模型」里新建模型、点「检查」。最关键的一条来自 [Chatbox 官方 ZenMux 配置指南](https://chatboxai.app/zh/guide/byok/zenmux)：**完整请求地址中 `/v1/chat/completions` 只能出现一次**。以 OpenLux 为例，API Host 填 `https://api.openlux.ai/v1`，API Path 填 `/chat/completions`，拼起来正好是 `https://api.openlux.ai/v1/chat/completions`。

本文适用于想在 Chatbox（桌面端或移动端）用自己的 Key 调用中转模型的读者。界面名称以撰文时 Chatbox 官方中文指南为准，旧版本的按钮位置可能不同。

## 适用范围和前提

开始前确认三件事：

1. **Chatbox 支持自定义提供方**。官方 [BYOK 说明](https://chatboxai.app/zh/guide/byok)写明可以在设置中配置自己的 API Key；Kimi、ZenMux、腾讯混元等第三方服务的配置指南，都是在「模型提供方」里添加提供方、API 模式选「OpenAI API 兼容」来接入的，中转 API 走同一条路。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。Key 只填进 Chatbox，不要贴到截图或聊天里。
3. **选对模型 ID**。只能填中转站在售的模型 ID。OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，每个模型都标了支持的端点类型。Chatbox 的「OpenAI API 兼容」模式请求的是 Chat Completions，所以要选端点类型里含 `openai` 的模型，例如 `gpt-6-astra`、`claude-opus-5-5`、`claude-sonnet-5-5`、`gemini-3.8-flash`。

关于 Claude 模型：本文是用「OpenAI API 兼容」模式调用 Claude 模型（价格接口显示上面两个 Claude 模型同时支持 `anthropic` 和 `openai` 端点）。Chatbox 官方 [Claude 配置指南](https://chatboxai.app/en/guide/byok/claude)只写了内置 Anthropic 提供方用官方 Key、API Host 保持默认 `https://api.anthropic.com`，没有说明怎样把它改成中转地址，所以本文不展开这种做法。

## 第一步：添加自定义提供方

按官方指南的步骤操作：

1. 打开「设置」→「模型提供方」→「添加」。移动端先点左上角菜单展开侧边栏，再打开「设置」。
2. 选择「添加自定义提供商」。
3. 名称填一个容易识别的名字，例如 `OpenLux`；API 模式选择「OpenAI API 兼容」。
4. 进入提供方设置，填写下一节表格里的三项。

## 第二步：API Host、API Path 和 API Key 怎么填

Chatbox 会把 API Host 和 API Path 拼成完整请求地址。官方 Kimi、ZenMux 指南的写法都是：API Host 带到 `/v1`，API Path 填 `/chat/completions`；腾讯混元指南也要求完整地址以 `/v1/chat/completions` 结尾。照这个规则填 OpenLux：

| 设置项 | 填写内容 | 说明 |
|---|---|---|
| API 模式 | OpenAI API 兼容 | 官方各自定义接口指南的统一选法 |
| API Host | `https://api.openlux.ai/v1` | 带 `/v1`，必须保留 `https://` |
| API Path | `/chat/completions` | 与 API Host 拼成 `https://api.openlux.ai/v1/chat/completions` |
| API Key | 在 OpenLux「令牌」页创建的 Key | 只填 Key 本身 |

两个容易踩的坑：

- **`/v1` 写了两次**：API Host 已经带 `/v1`，API Path 又写成 `/v1/chat/completions`，地址就变成 `.../v1/v1/chat/completions`。
- **`/v1` 一次都没有**：API Host 写成 `https://api.openlux.ai`、API Path 只写 `/chat/completions`，地址缺了 `/v1`。

填好后点保存，并把完整地址在心里拼一遍，确认 `/v1/chat/completions` 恰好出现一次。

## 第三步：新建模型

官方指南的做法是在提供方设置页向下滚动到「模型」，点「新建」，逐项填写：

| 配置项 | 填什么 | 依据 |
|---|---|---|
| 模型 ID | 价格接口里的准确 ID，如 `claude-opus-5-5` | 官方提醒不要把模型展示名填进 ID |
| 显示名称 | 自己能认出来就行，如 `Claude Opus 5.5（OpenLux）` | 只影响界面显示 |
| 模型类型 | 「聊天」 | ZenMux 指南示例 |
| 上下文窗口 | 填该模型文档写明的上限 | 官方要求按模型文档或控制台填写 |
| 最大输出 Token 数 | 不超过该模型的输出上限 | 官方：遇到上下文错误时适当调低 |

官方指南特别说明：截图里的模型 ID 和参数只是示例，实际以提供方给出的完整模型 ID 和参数限制为准。

## 第四步：检查与验证

**在 Chatbox 里检查**：点「检查」，通过后保存配置，在模型选择器里选中新模型，发一条消息能正常回复，就算接通。

**用命令行确认地址和 Key**：如果检查失败、又分不清是地址还是 Key 的问题，可以在终端请求一次模型列表（把 `$OPENLUX_API_KEY` 换成你自己的 Key）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Chatbox 里的填写；返回 401 说明 Key 错了或没带上。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 检查返回 401 / 鉴权失败 | Key 填错、复制不完整，或没填进 API Key | 重新复制 Key；用上面的 curl 单独验证 |
| 检查返回 404 | 完整地址里 `/v1` 重复或缺失 | 按第二步表格改成 Host 带 `/v1`、Path 为 `/chat/completions` |
| 提示模型不存在或不可用 | 模型 ID 与在售 ID 不一致，或填了展示名 | 对照价格接口复制准确 ID 重新新建 |
| 选了 `gpt-5.4` 等模型一直失败 | 价格接口显示这类模型只支持 `openai-response` 端点，没有 `openai` | 换成端点类型含 `openai` 的模型 |
| 设置 Temperature 后报错 | 官方说明较新的模型（如 o 系列推理模型、部分 Claude 模型）不支持 Temperature | 在 Chatbox 设置里把 Temperature 设为「未设置」；Top P 同理 |
| 对话一长就出错 | 超出模型上下文窗口 | 调低「最大上下文消息数」，或开一个新对话 |
| 调用失败但 Key 和地址都对 | 官方没有细分原因 | 按官方建议开启「改善网络兼容性」、降低最大输出 Token 数，或换个模型测试 |

404 和「只支持 `openai-response`」两行是按官方「`/v1/chat/completions` 只出现一次」的规则和 OpenLux 价格接口的端点标注推出来的，Chatbox 官方文档没有直接写这两种情况的报错文字。

## 参考资料

- Chatbox 官方指南：[ZenMux 配置指南](https://chatboxai.app/zh/guide/byok/zenmux)（添加自定义提供商、API Host / API Path、`/v1/chat/completions` 只出现一次、新建模型、改善网络兼容性）
- Chatbox 官方指南：[Kimi For Coding 配置指南](https://chatboxai.app/zh/guide/byok/kimi-for-coding)（不要把展示名填进模型 ID）
- Chatbox 官方指南：[腾讯混元配置指南](https://chatboxai.app/zh/guide/byok/hunyuan)（完整地址以 `/v1/chat/completions` 结尾）
- Chatbox 官方指南：[常见错误与解决方案](https://chatboxai.app/zh/guide/faq/errors)（Temperature 设为「未设置」、上下文超长）、[模型与能力](https://chatboxai.app/zh/guide/concepts/models)（Top P 设为「未设置」）
- Chatbox 官方指南：[自带 API Key (BYOK)](https://chatboxai.app/zh/guide/byok)、[Claude 配置指南](https://chatboxai.app/en/guide/byok/claude)

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=chatbox-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤填进 Chatbox。

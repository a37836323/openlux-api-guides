---
layout: default
title: "LobeHub（LobeChat）怎么接入 OpenAI 兼容 / Claude 中转 API：代理地址、Key 与模型设置"
description: "按 LobeHub 官方文档，在「AI 服务商」里为 OpenAI、Anthropic 填写代理地址和 Key，接入 OpenAI 兼容 / Claude 中转 API；附自部署环境变量、/v1 后缀规则、验证方法和 401、空回复、404 排查。"
permalink: /news/lobehub-lobechat-relay-api-proxy-url-setup/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[LobeHub 官方文档](https://lobehub.com/zh/docs/usage/providers/openai)

# LobeHub（LobeChat）怎么接入 OpenAI 兼容 / Claude 中转 API：代理地址、Key 与模型设置

想在 LobeHub 里用中转 API 调 GPT、Claude 模型，按 LobeHub 官方文档，不用改代码：打开 **应用设置 → AI 服务商**，选 **OpenAI**（或 **Anthropic**），打开服务商，填 API Key，再在 **代理地址** 里填中转的 Base URL，点 **检查** 测试连接，最后在模型列表里启用模型。自己部署的实例，也可以用环境变量 `OPENAI_PROXY_URL`、`ANTHROPIC_PROXY_URL` 统一配置。

最容易出错的是地址末尾的 `/v1`：OpenAI 服务商的默认地址带 `/v1`，Anthropic 服务商的默认地址不带。本文依据 LobeHub 官方文档 [在 LobeHub 中使用 OpenAI](https://lobehub.com/zh/docs/usage/providers/openai) 及同站的服务商、环境变量说明整理。

## 适用版本和前提

- **名称**：LobeHub 的官方 GitHub 仓库原名 `lobehub/lobe-chat`，现在会跳转到 `lobehub/lobehub`，网上搜「LobeChat 中转」找到的就是同一个项目。下面的菜单名称以当前官方文档为准，旧版本界面可能不同。
- **云端版和自部署都能配**：官方更新日志《自定义 AI Provider 管理》写明新的服务商管理在开源版和 LobeHub Cloud 都已上线，可以编辑现有服务商配置，也可以添加连接 OpenAI 兼容端点的自定义服务商。
- **你需要一个中转 Key**：在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建。
- **模型 ID**：只用 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里在售的 ID，本文示例都取自这个接口。

## 第一步：在 OpenAI 服务商里填中转地址（接 GPT 等模型）

按官方步骤操作：

1. 打开 **应用设置 → AI 服务商**，在列表里选 **OpenAI**，打开右侧开关。
2. 填写 API Key，粘贴在 OpenLux 创建的 Key。官方故障排查第一条就是检查 Key 有没有多余的空格。
3. 在 **代理地址** 里填 `https://api.openlux.ai/v1`。官方服务商说明写的是：页面显示「代理地址」时，可以填服务商 API 的 Base URL 或兼容接口地址。
4. 点击 **检查** 测试连接。
5. 在下方模型列表里启用需要的模型；列表里没有的，按页面选项获取或添加模型。配置会自动保存。
6. 在助理设置里选这个服务商和模型，开始对话。

为什么带 `/v1`：官方环境变量文档写明 OpenAI 的默认请求基础 URL 是 `https://api.openai.com/v1`，代理地址就是用来覆盖它的，所以中转地址也要写到 `/v1` 这一层。

## 第二步：用 Anthropic 服务商接 Claude（地址不带 /v1）

Claude 模型走 Anthropic 原生接口时，操作和上一步一样：在 **AI 服务商** 里选 **Anthropic**，打开服务商，填 Key，如需使用代理就填代理地址，点 **检查**，再启用 Claude 模型。

区别在地址：官方文档写明 Anthropic 的默认请求基础 URL 是 `https://api.anthropic.com`，**不带 `/v1`**，客户端自己拼 `/v1/messages`。所以这里填 `https://api.openlux.ai`。

| 服务商 | 官方默认基础地址 | 填 OpenLux 的代理地址 | 实际请求路径 | 模型示例 |
|---|---|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `https://api.openlux.ai/v1` | `/v1/chat/completions` 等 | `gpt-6-astra`、`gpt-6-luna` |
| Anthropic | `https://api.anthropic.com` | `https://api.openlux.ai` | `/v1/messages` | `claude-sonnet-5-5`、`claude-opus-5-5` |

另一种做法：OpenLux 价格接口显示 `claude-sonnet-5-5`、`claude-opus-5-5`、`claude-haiku-5-5` 也支持 OpenAI 兼容端点，所以也可以把这些 ID 加到 OpenAI 服务商的模型列表里，只配一个服务商。两种方式选一种即可，地址按上表对应填。

## 第三步：自部署实例用环境变量配置

如果 LobeHub 是你自己部署的，也可以在部署时用环境变量统一配置。官方《模型服务商》环境变量文档给了这些变量：

| 变量 | 作用 | 官方默认值 |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI 服务商的 API Key | - |
| `OPENAI_PROXY_URL` | 覆盖 OpenAI 请求基础 URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL_LIST` | 控制模型列表：`+` 增加、`-` 隐藏、`-all` 先隐藏全部 | - |
| `ANTHROPIC_API_KEY` | Anthropic 服务商的 API Key | - |
| `ANTHROPIC_PROXY_URL` | 覆盖 Anthropic 请求基础 URL | `https://api.anthropic.com` |

接 OpenLux 时可以这样写（Key 换成你自己的，不要提交到公开仓库）：

```bash
OPENAI_API_KEY=你的OpenLux Key
OPENAI_PROXY_URL=https://api.openlux.ai/v1
OPENAI_MODEL_LIST=-all,+gpt-6-astra,+claude-sonnet-5-5
ANTHROPIC_API_KEY=你的OpenLux Key
ANTHROPIC_PROXY_URL=https://api.openlux.ai
```

`OPENAI_MODEL_LIST` 的语法按官方《Model List》文档：`-all,+模型A,+模型B` 表示先隐藏全部内置模型，只启用你列出的；还可以用 `模型名=展示名` 改显示名称。

## 第四步：验证地址和 Key 是否正确

先在终端单独验证，排除 LobeHub 设置的干扰。`/v1/models` 能列出模型，就说明地址和 Key 都对：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的Key"
```

然后回到 LobeHub：

1. 在服务商页点 **检查**，确认连接测试通过。
2. 新建一个对话，在助理设置里选刚启用的模型，发一句简单的话。
3. 能正常收到回复，就算接通了。

如果 curl 正常而 LobeHub 不正常，就按下一节逐项核对代理地址、模型 ID 和服务商开关。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 返回 401 / 提示 API Key 无效 | Key 填错、复制不完整、带了空格，或填到了别的服务商下 | 用上面的 curl 单独验证；官方建议先检查 Key 有没有多余空格 |
| OpenAI 服务商回复为空、没反应 | 代理地址少了 `/v1` | 官方文档提醒：AI 返回的消息为空时，尝试加上 `/v1` 后重试；填 `https://api.openlux.ai/v1` |
| Anthropic 服务商返回 404 | 代理地址可能多写了 `/v1`，请求路径变成 `/v1/v1/messages` | 改成 `https://api.openlux.ai`，不带 `/v1` |
| 提示模型不可用或不存在 | 模型 ID 与在售 ID 不一致，或用了显示名 | 对照价格接口或 `/v1/models` 返回的 ID 重新添加 |
| 某些模型在 OpenAI 服务商下一直报错 | OpenLux 价格接口显示部分模型（如 `gpt-5.4`）只支持 Responses 端点 | 换成同时支持 OpenAI 兼容端点的模型，如 `gpt-6-astra` |

官方文档在 `/v1` 说明下还列了社区讨论，如「代理服务器地址填了聊天没任何反应」「使用第三方接口报错的原因」，遇到类似现象可以先对照上表核对地址后缀。

## 参考资料

- LobeHub 官方文档：[在 LobeHub 中使用 OpenAI](https://lobehub.com/zh/docs/usage/providers/openai)
- LobeHub 官方文档：[在 LobeHub 中使用多模型服务商](https://lobehub.com/zh/docs/usage/providers)（配置提供商、故障排查）
- LobeHub 官方文档：[在 LobeHub 中使用 Anthropic Claude](https://lobehub.com/zh/docs/usage/providers/anthropic)
- LobeHub 官方文档：[模型服务商环境变量](https://lobehub.com/zh/docs/self-hosting/environment-variables/model-provider)、[Model List](https://lobehub.com/zh/docs/self-hosting/advanced/model-list)
- 文档源文件：[lobehub/lobehub 仓库 docs 目录](https://github.com/lobehub/lobehub/tree/main/docs)

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=lobehub-lobechat-relay-api-proxy-url-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤填进 LobeHub。

---
layout: default
title: "Cline 怎么接入 OpenAI 兼容 / Claude 中转 API：Base URL、Key 与模型设置"
description: "Cline 接入 OpenAI 兼容或 Claude 中转 API：按官方文档选 OpenAI Compatible 填 Base URL、API Key、Model ID，或用 Anthropic 的 Use custom base URL，附验证方法和 401、模型不存在、连接失败的排查。"
permalink: /news/cline-relay-api-openai-compatible-setup/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[Cline 官方文档](https://docs.cline.bot/provider-config/openai-compatible)

# Cline 怎么接入 OpenAI 兼容 / Claude 中转 API：Base URL、Key 与模型设置

在 Cline 里接中转 API，有两条路：一是在「API Provider」里选 **OpenAI Compatible**，填 Base URL、API Key 和 Model ID；二是选 **Anthropic**，勾选「Use custom base URL」后填中转地址。按 [Cline 官方文档 OpenAI Compatible 页](https://docs.cline.bot/provider-config/openai-compatible)的说法，Base URL 是这一步里最关键的设置（原文 “This is a crucial step”），填错了后面都连不上。

本文以 OpenLux 为例，适用于在 VS Code 等编辑器里使用 Cline 扩展、想用自己的 Key 调用中转模型的读者（Cline 把这种用法叫 BYOK，Bring Your Own Key）。设置项名称以撰文时的官方文档为准，界面可能随版本变化。

## 适用范围和前提

开始之前确认三件事：

1. **用的是 BYOK 方式**。Cline 的[授权页](https://docs.cline.bot/getting-started/authorizing-with-cline)列了三种接入方式：Cline 自己的按量计费账号、ClinePass 订阅、以及使用你自己的服务商凭据（BYOK）。接中转 API 属于 BYOK，在 API Key 输入框里粘贴自己的 Key 即可。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。
3. **知道要用的模型 ID**。只能填中转站在售的模型 ID，OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，例如 `gpt-5.6-sol`、`claude-sonnet-5-5`。Cline 文档也提醒：不同 OpenAI 兼容服务商的模型 ID 各不相同，要以服务商自己的资料为准。

## 两种接法怎么选

| 接法 | API Provider 选什么 | Base URL 填写 | 适合的模型 |
|---|---|---|---|
| OpenAI 兼容 | OpenAI Compatible | `https://api.openlux.ai/v1` | 价格接口里支持 `openai` 端点的模型，如 `gpt-5.6-sol`、`claude-sonnet-5-5` |
| Anthropic 兼容 | Anthropic，勾选 Use custom base URL | `https://api.openlux.ai`（不带 `/v1`） | 价格接口里支持 `anthropic` 端点的模型，如 `claude-sonnet-5-5`、`claude-opus-5-5` |

两点说明：

- OpenAI Compatible 的 Base URL 带 `/v1`：Cline 文档自己的 v0 示例就是把 Base URL 设成 `https://api.v0.dev/v1`，写到 `/v1` 这一层；OpenLux 的 OpenAI 兼容入口也是 `https://api.openlux.ai/v1`。文档同时说明，这里**不会**是 `https://api.openai.com/v1`，那是官方 OpenAI 的地址，要用官方 OpenAI 请选单独的 OpenAI 服务商。
- Anthropic 的自定义地址，Cline 文档只写了「勾选 Use custom base URL 并填入地址」，没有说明要不要带 `/v1`。OpenLux 的 Anthropic 入口是不带 `/v1` 的根地址，客户端自己会拼 `/v1/messages`，所以这里填 `https://api.openlux.ai`。

想用的模型在 Anthropic 的下拉列表里找不到时，用 OpenAI Compatible：官方写明它的 Model 一项可以选择或直接输入模型 ID。

## 方法一：用 OpenAI Compatible 接入

按官方文档的设置项操作：

1. 点击 Cline 面板里的设置图标（⚙️），打开设置面板。
2. **API Provider**：选择 `OpenAI Compatible`。
3. **Base URL**：填 `https://api.openlux.ai/v1`。
4. **API Key**：粘贴在 OpenLux「令牌」页创建的 Key。下面的 **Use Azure Identity Authentication** 是给 Azure 托管身份认证用的，用 OpenLux 的 Key 时不需要勾选。
5. **Model**：选择或手动输入模型 ID，例如 `gpt-5.6-sol`。大小写、点号和连字符要和价格接口里的 ID 完全一致。

### Model Configuration 怎么设

同一面板下的 **Model Configuration** 可以调整高级参数，官方列出的项目有：

- Max Output Tokens（最大输出 token）
- Context Window size（上下文窗口大小）
- Image Support（是否支持图片输入）
- Computer Use（官方举例：适用于支持工具/函数调用的模型）
- Input Price、Output Price（按 token 或每百万 token 计）

这些值应按所选模型的官方说明填写，不确定的项不要乱改。价格以 OpenLux 官网价格页为准，本文不写具体数字。

## 方法二：用 Anthropic 服务商加自定义地址

如果想走 Anthropic Messages 协议调用 Claude 模型，按 [Cline 的 Anthropic 配置页](https://docs.cline.bot/provider-config/anthropic)：

1. 点击 Cline 面板里的设置图标（⚙️）。
2. 在「API Provider」下拉框里选择 `Anthropic`。
3. 把 Key 粘贴到「Anthropic API Key」输入框。
4. 在「Model」下拉框里选择 Claude 模型。
5. 勾选 **Use custom base URL**，填入 `https://api.openlux.ai`。

注意第 4 步官方写的是从下拉框选择 Claude 模型，没有提到手动输入；所选模型必须同时在 OpenLux 在售，否则会报模型不存在。想用的模型不在下拉框里时，改用方法一手动填写模型 ID。

同一页还有一个「Claude Code」服务商，那是用 Claude Max/Pro 订阅、通过本机 Claude CLI 调用的方式，不走 API Key，和接中转 API 无关，不要选错。

## 验证是否接通

**在 Cline 里验证**：官方 v0 示例的最后一步是点击 **Verify** 确认连接。保存设置后在 Cline 里发一条简单的任务，能正常返回就算接通。

**用命令行确认地址和 Key**：如果 Cline 报错，又分不清是地址、Key 还是模型的问题，可以在终端请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题出在 Cline 的设置上；返回 401 说明 Key 错了或没带上。顺便在返回列表里找一下你在 Cline 里填的模型 ID，确认拼写一致。

## 常见报错和处理

Cline 文档的排错部分列了四类问题，结合中转场景对应如下：

| 现象 | 可能原因 | 处理 |
|---|---|---|
| Invalid API Key / 401 | Key 填错，或填的不是这个服务商的 Key | 重新从 OpenLux「令牌」页复制；用上面的 curl 单独验证 |
| Model Not Found / 模型不存在 | 模型 ID 不在这个 Base URL 下提供，或拼写不一致 | 对照价格接口和 `/v1/models` 的返回重新填写 |
| 404 或请求路径不对 | OpenAI Compatible 的 Base URL 少了 `/v1`，或 Anthropic 自定义地址多写了 `/v1` | OpenAI Compatible 填 `https://api.openlux.ai/v1`；Anthropic 填 `https://api.openlux.ai` |
| Connection Errors / 连接失败 | Base URL 写错、本机访问不到接口、被防火墙或代理拦截 | 核对地址；VS Code 扩展会使用 VS Code 自带的代理设置，企业网络先在 VS Code 里配置代理 |
| 结果不符合预期 | 模型选得不合适，或 Model Configuration 参数设得不对 | 官方建议换一个模型试试，或逐项检查配置 |

404 那一行是按两个入口的地址规则推出来的，Cline 官方文档没有直接写出多填或少填 `/v1` 时的报错内容。代理那一条出自 Cline 的[网络与代理说明](https://docs.cline.bot/troubleshooting/networking-and-proxies)：VS Code 扩展自动使用 VS Code 内置的代理设置，Cline 本身不需要额外配置。

## 参考资料

- Cline 文档：[OpenAI Compatible](https://docs.cline.bot/provider-config/openai-compatible)（Base URL、API Key、Model ID、Model Configuration、排错）
- Cline 文档：[Anthropic / Claude Code](https://docs.cline.bot/provider-config/anthropic)（Anthropic API Key、Use custom base URL）
- Cline 文档：[Authorization](https://docs.cline.bot/getting-started/authorizing-with-cline)（三种接入方式与 BYOK）
- Cline 文档：[Networking and Proxies](https://docs.cline.bot/troubleshooting/networking-and-proxies)（代理设置）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cline-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤填进 Cline。

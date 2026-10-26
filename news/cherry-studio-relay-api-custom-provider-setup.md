---
layout: default
title: "Cherry Studio 怎么接入 OpenAI 兼容 / Claude 中转 API：API 地址、Key 与模型设置"
description: "Cherry Studio 接入 OpenAI 兼容或 Claude 中转 API：按官方文档添加自定义服务商，API 地址填根地址、添加模型、打开启用开关并检测，附 401、404、模型不存在的排查。"
permalink: /news/cherry-studio-relay-api-custom-provider-setup/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[Cherry Studio 官方文档](https://docs.cherry-ai.com/pre-basic/providers/zi-ding-yi-fu-wu-shang)

# Cherry Studio 怎么接入 OpenAI 兼容 / Claude 中转 API：API 地址、Key 与模型设置

在 Cherry Studio 里接中转 API，走的是「设置 → 模型服务 → + 添加服务商」这条路：起个名字、填 API 密钥、在端点里填中转站的**根地址**，再添加模型、打开启用开关、点「检测」。最容易出错的是 API 地址：按 [Cherry Studio 官方文档](https://docs.cherry-ai.com/pre-basic/providers/zi-ding-yi-fu-wu-shang) 和[模型服务设置](https://docs.cherry-ai.com/pre-basic/providers/providers)的说明，填根地址即可，Cherry Studio 会自己补上 `/v1/chat/completions`，不要把完整接口路径粘进去。

本文以 OpenLux 为例，适用于想在 Cherry Studio 桌面端用 OpenAI 兼容（Chat Completions）或 Anthropic Messages 协议调用中转模型的读者。界面名称以撰文时的官方文档为准，旧版本的按钮位置可能不同。

## 适用范围和前提

开始之前确认三件事：

1. **客户端支持自定义服务商**。官方文档写明：服务不在内置列表里、但提供 OpenAI 兼容、Anthropic 兼容或 Gemini 兼容任一协议，都可以通过「自定义服务商」添加。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。Cherry Studio 里叫「API 密钥」，官方说明密钥、Key、API Key、令牌指的是同一个东西。
3. **知道要用的模型 ID**。只能填中转站在售的模型 ID，OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，例如 `gpt-5.6-sol`、`claude-sonnet-5-5`。

## 第一步：添加自定义服务商

按官方文档的步骤操作：

1. 点击左侧导航栏的「设置」（齿轮图标）。
2. 选择「模型服务」选项卡。
3. 点击服务商列表下方的「+ 添加服务商」，打开「添加自定义提供商」弹窗。
4. 填写信息：
   - **提供商名称**：起一个容易识别的名字，例如 `OpenLux`。
   - **API 密钥**：粘贴刚创建的 Key。
   - **端点设置**：默认可以添加 OpenAI 和 Anthropic 端点；点「更多设置」还能添加 OpenAI Responses、Gemini、图像生成 Base URL 和图像编辑 Base URL。
5. 点击「添加」保存。

官方文档的 vLLM 示例里还出现过「提供商类型」选 `OpenAI` 的写法；如果你的版本弹窗里是「提供商类型」而不是「端点设置」，OpenAI 兼容接口就选 `OpenAI`。

## 第二步：API 地址怎么填

Cherry Studio 对 API 地址的规则是：服务商给的若是 `https://xxx.com/v1/chat/completions` 这种完整地址，通常只填根地址 `https://xxx.com`，它会自动补上 `/v1/chat/completions`；地址以 `#` 结尾时不再自动拼接版本路径，只用你填的地址。

| 端点 | API 地址填写 | 依据 |
|---|---|---|
| OpenAI（Chat Completions） | `https://api.openlux.ai` | 模型服务设置页：填根地址，自动补 `/v1/chat/completions` |
| Anthropic（Messages） | `https://api.openlux.ai` | 内置 Anthropic 服务商的默认地址就是不带 `/v1` 的根地址 `https://api.anthropic.com`；OpenLux 的 Anthropic 入口也是不带 `/v1` 的根地址 |
| 结尾加 `#` | 不要加 | 官方说明只有中转站明确要求不带 `/v1` 的路径时才加 `#`；OpenLux 使用标准的 `/v1/...` 路径 |

两种端点怎么选：按模型支持的协议来。OpenLux 价格接口里每个模型都列了支持的端点类型，例如`gpt-5.6-sol` 支持 OpenAI 和 OpenAI Responses，`claude-sonnet-5-5` 支持 Anthropic 和 OpenAI。官方文档还提到，Cherry Studio 的智能体（Agent）需要 Anthropic 协议端点，想在 Agent 里用 Claude 模型就配 Anthropic 端点。

另外两点：密钥可以填多个，用**英文逗号**隔开，Cherry Studio 会按列表顺序轮询；地址必须保留 `https://`。

## 第三步：添加模型并打开启用开关

1. 在服务商配置页点「获取模型列表」，Cherry Studio 会拉取服务商支持的模型；在弹出的「模型管理」列表里点模型右侧的 `+` 加入。只有加入列表的模型才会出现在模型选择器里。
2. 拉取不到或列表太长时，点「+」手动填写模型 ID，例如 `gpt-5.6-sol`、`claude-sonnet-5-5`。官方建议只添加实际会用到的模型。
3. 模型名称下方会显示服务商返回的实际 API 模型 ID。名称相近的版本不会被合并，添加前先核对这一行。
4. 打开服务商页面右上角的**启用开关**。官方特别提醒：不打开开关，服务商仍未启用，模型不会出现在选择列表里。已启用的服务商在列表右侧会显示绿色圆点。

## 第四步：检测与验证

**在 Cherry Studio 里检测**：点「检测」按钮、选一个模型，测试是否配置成功；配置了多个密钥时还能选用哪个密钥检测。检测通过后，回到聊天界面选择 `OpenLux` 服务商下的模型，发一条消息能正常回复，就算接通。

**用命令行确认地址和 Key**：如果检测失败、又分不清是地址还是 Key 的问题，可以在终端请求一次模型列表（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Cherry Studio 里的配置；返回 401 说明 Key 错了或没带上。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 检测返回 401 / 鉴权失败 | Key 填错或没填上；填多个 Key 时没用英文逗号分隔（官方要求英文逗号） | 重新复制 Key；多个 Key 只用英文逗号；用上面的 curl 单独验证 |
| 检测返回 404 | API 地址写成了 `https://api.openlux.ai/v1` 或完整接口地址，Cherry Studio 再拼一次路径后请求路径不对 | 改成根地址 `https://api.openlux.ai`，末尾不要加 `#` |
| 提示模型不存在 | 手动填的模型 ID 和在售 ID 不一致 | 对照价格接口和模型名下方的实际 API 模型 ID 重新添加 |
| 检测失败、但 Key 和地址都对 | 模型列表里有填错的或不受支持的模型 | 按官方说明删掉填错的模型，换一个确认在售的模型再检测 |
| 填了 Key 仍无法对话 | 服务商没启用、默认模型不是这个服务商下的模型，或网络代理拦截 | 打开启用开关；在「设置 → 默认模型」选该服务商下可用的模型；企业网络检查代理 |
| 模型选择器里找不到模型 | 模型没加入列表，或模型类型、接口不匹配 | 先同步或手动添加；Agent、绘画、嵌入等页面会按能力筛选模型 |

404 那一行是按官方「自动补 `/v1/chat/completions`」的规则推出来的，官方文档没有直接写出多填 `/v1` 时的报错。

## 参考资料

- Cherry Studio 文档：[自定义服务商](https://docs.cherry-ai.com/pre-basic/providers/zi-ding-yi-fu-wu-shang)
- Cherry Studio 文档：[模型服务设置](https://docs.cherry-ai.com/pre-basic/providers/providers)（API 地址规则、多密钥、检测、启用开关）
- Cherry Studio 文档：[Anthropic](https://docs.cherry-ai.com/pre-basic/providers/anthropic)（默认 API 地址、Agent 需要 Anthropic 协议端点）
- Cherry Studio 文档：[常见问题](https://docs.cherry-ai.com/question-contact/questions)（填了 Key 仍无法对话、列表里没有模型）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cherry-studio-relay-api-custom-provider-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤填进 Cherry Studio。

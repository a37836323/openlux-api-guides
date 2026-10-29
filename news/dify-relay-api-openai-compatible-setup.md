---
layout: default
title: "Dify 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Base URL、Key 与模型设置"
description: "Dify 接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：在模型供应商里安装官方 OpenAI-API-compatible 插件，添加 LLM 模型，API Base URL 填 https://api.openlux.ai/v1（插件会接上 chat/completions），填 Key 与准确模型 ID；附工具调用、Responses API 等选填项和 401、404、user 参数报错排查。"
permalink: /news/dify-relay-api-openai-compatible-setup/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[Dify 官方文档](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)

# Dify 怎么接入 OpenAI 兼容中转 API 调用 GPT、Claude 模型：API Base URL、Key 与模型设置

在 Dify 里接中转 API，走的是官方插件「OpenAI-API-compatible」：在「集成」→「模型供应商」里安装它，点「添加模型」，模型类型选 LLM，填模型名称、API Key 和 API Base URL。最关键的一项是 **API Base URL 要带到 `/v1`**：插件发对话请求时会在这个地址后面接上 `chat/completions`，以 OpenLux 为例填 `https://api.openlux.ai/v1`，实际请求的就是 `https://api.openlux.ai/v1/chat/completions`。

本文适用于 Dify 云版和自部署版中已能使用插件市场的读者。步骤依据 [Dify 官方文档「模型供应商」](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers) 和 Dify 官方（langgenius）维护的 [OpenAI-API-compatible 插件](https://marketplace.dify.ai/plugins/langgenius/openai_api_compatible)，字段名以撰文时插件 0.0.73 版为准，旧版本的界面可能不同。

## 适用范围和前提

开始前确认三件事：

1. **有管理权限**。官方文档写明，只有工作空间所有者和管理员可以管理模型供应商；填入的 Key 对整个工作空间生效。
2. **已有 API Key**。在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。Key 只填进 Dify，不要贴到截图或聊天里。
3. **选对模型 ID**。只能填中转站在售的模型 ID。OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，每个模型都标了支持的端点类型。这个插件默认走 Chat Completions，所以优先选端点类型含 `openai` 的模型，例如 `claude-sonnet-5-5`、`gpt-5.6-sol`、`deepseek-v4-pro`、`gemini-3.8-flash`。

关于 Claude 模型：本文是用 OpenAI 兼容接口调用 Claude 模型（价格接口显示 `claude-sonnet-5-5` 同时支持 `anthropic` 和 `openai` 端点）。Dify 的 Anthropic 供应商能否改成中转地址，本文依据的官方材料没有写，所以不展开。

## 第一步：安装 OpenAI-API-compatible 插件

按官方文档「添加供应商」的步骤：

1. 打开「集成」→「模型供应商」，在「安装模型供应商」区域或 [Dify Marketplace](https://marketplace.dify.ai/) 里找到 **OpenAI-API-compatible**（作者 langgenius，插件说明为「兼容 OpenAI API 的模型供应商」）。
2. 安装完成后，它会出现在模型供应商列表里。这类供应商不自带固定模型列表，要自己逐个添加模型，对应官方文档的「添加自定义模型」。

## 第二步：添加模型，必填项怎么填

在 OpenAI-API-compatible 卡片上点「添加模型」，模型类型选 **LLM**，按下表填写。字段名来自插件的配置定义文件 [openai_api_compatible.yaml](https://github.com/langgenius/dify-official-plugins/blob/main/models/openai_api_compatible/provider/openai_api_compatible.yaml)：

| 字段 | 填写内容 | 说明 |
|---|---|---|
| 模型名称 | 价格接口里的准确 ID，如 `claude-sonnet-5-5` | 插件提示「输入模型全称」，不要填展示名 |
| 模型显示名称 | 如 `Claude Sonnet 5.5（OpenLux）` | 选填，只影响界面显示 |
| API Key | 在 OpenLux「令牌」页创建的 Key | 插件以 `Authorization: Bearer` 头发送 |
| API Base URL | `https://api.openlux.ai/v1` | 必填；插件示例为 `https://api.openai.com/v1`，同样带 `/v1` |
| 对话类型 | 对话 | 默认就是「对话」；选「补全」会改走 `completions` 接口 |
| 模型上下文长度 | 按该模型官方文档填写 | 必填，插件默认 4096 |
| 最大 token 上限 | 不超过该模型的输出上限 | 插件默认 4096 |

两个容易踩的坑：

- **地址填成完整接口**：API Base URL 写成 `https://api.openlux.ai/v1/chat/completions`，插件还会再接一次 `chat/completions`，地址就错了。
- **`/v1` 没写**：写成 `https://api.openlux.ai`，请求会变成 `https://api.openlux.ai/chat/completions`，缺了 `/v1`。

另有一个选填项「API endpoint中的模型名称」：填了它，插件发请求时用它代替「模型名称」。想在 Dify 里用一个好记的名字、实际请求中转站的准确 ID 时可以用它；不需要就留空。

## 第三步：按模型能力调整选填项

插件默认把多数能力设成「不支持」，用到相应功能时再按模型实际能力打开：

| 选填项 | 默认值 | 什么时候改 |
|---|---|---|
| 函数调用类型 | 不支持 | Agent 或工作流需要模型调用工具时改成「工具调用」；插件代码里「工具调用」读取返回中的 `tool_calls`，「函数调用」读取旧式的 `function_call` |
| 流式函数调用 | 不支持 | 模型支持流式返回工具调用时再开 |
| 视觉支持 | 不支持 | 要给模型传图片时再开；只管图片，视频、音频、文档各有单独开关 |
| 思考模式支持 | 仅支持非思考模式 | 控制界面上思考模式开关是否可用 |
| API 类型 | Chat Completions API | 模型只支持 Responses 时改成「Responses API (/responses)」 |
| token 参数名 | 自动（按模型判断） | 自动判断不对、接口要求 `max_completion_tokens` 时手动指定 |

关于 API 类型：OpenLux 价格接口里，`gpt-5.4` 等模型的端点类型只有 `openai-response`，没有 `openai`。这类模型要么在这里选 Responses API（Base URL 不变，仍是 `https://api.openlux.ai/v1`），要么换一个端点类型含 `openai` 的模型。

## 第四步：保存与验证

**在 Dify 里验证**：官方文档写明，Dify 会先验证凭据，再让供应商投入使用。插件的验证代码会用你填的地址、Key 和模型名发一条很短的测试请求，所以地址、Key、模型名任何一项不对都会在保存时报错。保存成功后，在应用的模型选择里选中新模型，发一条消息能正常回复，就算接通。

**用命令行确认地址和 Key**：保存失败又分不清是哪一项的问题时，可以在终端请求一次模型列表（把 `$OPENLUX_API_KEY` 换成你自己的 Key）：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Dify 里的填写；返回 401 说明 Key 错了或没带上。自部署的 Dify 请在运行 Dify 的服务器上执行这条命令，结果才能代表 Dify 发出的请求。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 保存时报 401 / `Invalid token` | Key 填错或复制不完整 | 重新复制 Key；用上面的 curl 单独验证 |
| 保存时报 404 | API Base URL 少了 `/v1`，或填成了带 `/chat/completions` 的完整地址 | 改成 `https://api.openlux.ai/v1` |
| 提示模型不存在或不可用 | 模型名称与在售 ID 不一致 | 对照价格接口复制准确 ID |
| `gpt-5.4` 等模型一直失败 | 该模型只支持 `openai-response` 端点 | API 类型改成 Responses API，或换模型 |
| 报不支持 `user` 参数 | 插件默认会把 Dify 传入的用户标识作为顶层 `user` 参数发出 | 插件说明：部分网关会拒绝它，把「用户标识支持」改成「不支持」 |
| 报不支持 `stream_options` | 插件默认在流式请求里要求返回用量 | 插件说明：仅在接口拒绝该字段时，把「流式中包含用量」改成「禁用」 |
| Agent 不调用工具 | 函数调用类型仍是默认的「不支持」 | 改成「工具调用」 |

404 一行是按插件「Base URL 后接 `chat/completions`」的拼接方式推出来的，Dify 官方文档没有给出这种情况的报错原文；`user`、`stream_options` 两行的处理来自插件配置文件里的字段说明。

## 参考资料

- Dify 官方文档：[模型供应商](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)（添加供应商、添加自定义模型、凭据验证、管理权限）
- Dify Marketplace：[OpenAI-API-compatible 插件](https://marketplace.dify.ai/plugins/langgenius/openai_api_compatible)（插件用途、配置项概览）
- 插件源码：[openai_api_compatible.yaml](https://github.com/langgenius/dify-official-plugins/blob/main/models/openai_api_compatible/provider/openai_api_compatible.yaml)（字段名、默认值与说明）、[llm.py](https://github.com/langgenius/dify-official-plugins/blob/main/models/openai_api_compatible/models/llm/llm.py)（地址拼接、凭据验证、工具调用字段）

配好后想直接试：[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=dify-relay-api-openai-compatible-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的表格填进 Dify。

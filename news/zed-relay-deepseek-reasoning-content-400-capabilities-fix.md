---
layout: default
title: "Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置"
description: "Zed 接 OpenAI 兼容中转 API 后，DeepSeek 思考模型调用工具后续轮报 400、看不到思考过程、图片发不出去、max_completion_tokens 不被接受或提示缓存报错时，按 Zed 官方文档逐项设置 interleaved_reasoning、reasoning_effort、max_tokens_parameter、chat_completions、images 与 prompt_caching，并用最小请求验证。"
permalink: /news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/
date: 2026-11-12
---

> 更新日期：2026-11-12 · 一手来源：[Zed 官方文档](https://zed.dev/docs/ai/use-api-access)

# Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置

Zed 里已经能和中转模型正常对话，但一用 Agent 改代码、调用工具，下一次请求就报 400；或者选了推理模型却看不到思考过程、拖进去的图片模型说看不到——这类问题要先查 Zed 给每个模型设的「能力项」（`capabilities`）和 `reasoning_effort`，再怀疑 Key 和地址。Zed 官方 [Use API Access 文档](https://zed.dev/docs/ai/use-api-access#openai-compatible) 列出了 OpenAI 兼容提供方的默认能力：`tools` 为 true，`images`、`parallel_tool_calls`、`prompt_cache_key`、`interleaved_reasoning`、`max_tokens_parameter` 都是 false，`chat_completions` 为 true。默认值不符合所选模型时，就要在 `settings.json` 里按模型改。

本文适用于在 Zed 的 Zed Agent、Inline Assistant 等自带 AI 功能里，通过 OpenAI 兼容或 Anthropic 兼容提供方接中转 API 的读者。还没接通（401、404、模型不存在）的，先看 [Zed 接入中转 API 的设置篇](https://a37836323.github.io/openlux-api-guides/news/zed-relay-api-openai-compatible-setup/)。设置项名称以撰文时的 Zed 官方文档为准，界面可能随版本变化。

## 先按现象找对应的设置项

| 现象 | 对应设置项（Zed 默认值） | 怎么改 | 依据 |
|---|---|---|---|
| DeepSeek 思考模型调用工具后，后续请求报 400 | `capabilities.interleaved_reasoning`（false） | 改为 true | DeepSeek 思考模式文档、Zed 文档 |
| 选了推理模型，Agent 面板里看不到思考过程 | `reasoning_effort`（未设置） | 设为端点支持的非 `none` 档位 | Zed 文档 |
| 报错指向 `max_completion_tokens` 不被接受 | `capabilities.max_tokens_parameter`（false） | 改为 true，改用 `max_tokens` 传输出上限 | Zed 文档 |
| 只支持 Responses API 的模型调不通 | `capabilities.chat_completions`（true） | 改为 false | Zed 文档 |
| 模型说看不到图片 | `capabilities.images`（false） | 模型本身支持图片输入时改为 true | Zed 文档 |
| Anthropic 兼容提供方打开提示缓存后报错 | `capabilities.prompt_caching`（false） | 改回 false | Zed 文档 |
| 模型选择器旁显示「No tools」 | 模型或提供方不支持工具调用 | 换支持工具调用的模型 | Zed Agent Panel 文档 |

下面逐项说明。改完 `settings.json` 后，建议在 Agent 面板新开一个对话再试，因为出错对话里的历史是按旧设置发送的。

## DeepSeek 思考模型调用工具后报 400：打开 interleaved_reasoning

这是最容易踩的一项。DeepSeek 官方 [Thinking Mode 文档](https://api-docs.deepseek.com/guides/thinking_mode) 写明：

- 思考模式**默认开启**，思考内容通过与 `content` 同级的 `reasoning_content` 字段返回；
- 请求里带了 `tools` 参数时，之前各轮的 `reasoning_content` 要在后续所有请求里**完整回传**，即使某一轮模型没有调用工具；
- 原文还说，如果代码没有正确回传 `reasoning_content`，API 会返回 400 错误。

Zed Agent 是靠工具调用来读文件、改代码的（官方 Agent Panel 文档：Agent Panel 支持工具调用，内置搜索代码、编辑文件、运行终端命令等工具），OpenAI 兼容模型的 `tools` 默认也是 true，所以用 DeepSeek 思考模型时，请求里通常会带上工具。

Zed 文档对 `interleaved_reasoning` 的说明是：对于需要在专门的 `reasoning_content` 字段里收到之前思考内容的 Chat Completions 端点，把 `capabilities.interleaved_reasoning` 设为 true。它的默认值是 false。所以接 DeepSeek 思考模型时，把这一项打开：

```json
{
  "language_models": {
    "openai_compatible": {
      "openlux": {
        "api_url": "https://api.openlux.ai/v1",
        "available_models": [
          {
            "name": "deepseek-v4-pro",
            "max_tokens": 1000000,
            "reasoning_effort": "high",
            "capabilities": {
              "tools": true,
              "images": false,
              "chat_completions": true,
              "interleaved_reasoning": true
            }
          }
        ]
      }
    }
  }
}
```

说明几点：

1. `deepseek-v4-pro` 是 OpenLux 价格接口里在售的模型 ID（同列表里还有 `deepseek-v4.1-flash` 等），以你账号里 `/v1/models` 的返回为准。
2. `max_tokens` 在 Zed 里是**上下文窗口**，示例数值沿用 Zed 官方 DeepSeek 示例，使用时以 DeepSeek 官方文档写的实际数值为准。
3. DeepSeek 文档里思考强度用 `reasoning_effort` 控制，可选 `low`、`high`、`max`，其他值会被映射到这几档；Zed 会在 Chat Completions 请求里发送 OpenAI 风格的 `reasoning_effort`。
4. DeepSeek 文档里关闭思考模式要在 Chat Completions 请求里传 `thinking` 参数，Zed 文档没有提到发送这个参数的设置项，所以本文不建议靠改 `reasoning_effort` 来关思考，按上面打开 `interleaved_reasoning` 即可。

只聊天、不让模型调用工具时，DeepSeek 文档说 `reasoning_content` 不需要回传、传了也会被忽略，所以同一个模型「普通问答正常、一跑 Agent 就 400」，符合这一项的特征。

## 看不到思考过程：设置 reasoning_effort

Zed 文档说明：对推理模型（如 GPT-5），把 `reasoning_effort` 设为端点支持的非 `none` 档位，这样会在 Agent 面板里启用思考，并告诉 Zed 开启思考时发送哪一档。可填的值为 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max`。

- 在 Add Provider 界面添加 OpenAI 兼容提供方时，界面里就能设这一项，只提供非 `none` 的选项；
- 要对某个端点强制关闭推理，只能在 `settings.json` 里写 `"none"`；
- 各模型实际接受哪些档位，以模型官方文档为准。

## 输出上限参数报错：max_tokens_parameter

Zed 文档：如果端点要求用 `max_tokens` 而不是 `max_completion_tokens` 传输出 token 上限，就把 `capabilities.max_tokens_parameter` 设为 true。这一项默认 false，也就是默认用 `max_completion_tokens`。

判断方法：看 Zed 显示的报错原文（也可以执行 `agent: open active thread as markdown` 导出对话，官方建议遇到报错时用它），如果点名 `max_completion_tokens` 不被支持或是未知参数，就打开这一项。同时可以给模型设 `max_output_tokens` 作为输出上限，Zed 官方示例里它和 `max_tokens`（上下文窗口）是两个不同的字段，不要填反。

## 只支持 Responses 的模型：chat_completions 改为 false

Zed 文档：模型只能用 Responses API，或需要 Responses API 来保存推理状态时，把 `capabilities.chat_completions` 设为 false，Zed 就改走 Responses 端点。OpenLux 价格接口里 GPT 系列（如 `gpt-6-astra`、`gpt-6-sol`）的端点类型同时列有 `openai` 和 `openai-response`，Responses 入口同样在 `https://api.openlux.ai/v1` 下，`api_url` 不用改。

## 图片发不出去或模型说看不到图片：images

Zed Agent Panel 文档说明，可以在支持视觉模型的提供方下给提示附图片（@ 引用项目里的图片、拖进消息框或粘贴）。但 OpenAI 兼容和 Anthropic 兼容提供方的 `images` 默认都是 false。所选模型本身支持图片输入时，在该模型的 `capabilities` 里把 `images` 改为 true；模型不支持图片时改了也没用，应换模型。模型是否支持图片，看模型厂商文档，不要凭名字猜。

## Anthropic 兼容提供方：prompt_caching 与 No tools

用 Anthropic 兼容提供方接 Claude 时：

- `prompt_caching` 默认 false，打开后 Zed 会发送 `cache_control` 断点。Zed 文档原话的意思是：提供方拒绝带这些断点的请求时，就保持关闭。打开后开始报错，先改回 false。
- 请求头里的 `X-Api-Key`、`Anthropic-Version` 由 Zed 管理，写在 `custom_headers` 里也覆盖不了，Key 要在提供方设置里填，或用 `<PROVIDER_NAME>_API_KEY` 环境变量。

另外，Agent Panel 文档提到：工具调用需要模型和提供方分别支持，选中不支持的模型时会显示「No tools」标签；MCP 服务器里的部分工具不被支持时，模型选择器旁会出现警告图标。看到这两个提示时，问题在模型能力上，换模型比改 Key 有用。

## 用最小请求验证中转返回了 reasoning_content

Zed 里还是报错、分不清是 Zed 设置还是中转的问题时，在终端发一次最小请求（`$OPENLUX_API_KEY` 换成你自己的 Key，不要把 Key 贴到截图或聊天里）：

```bash
curl https://api.openlux.ai/v1/chat/completions \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"9.11 和 9.8 哪个大？"}]}'
```

判断标准：

- 返回 200，且 `choices[0].message` 里有 `reasoning_content`：思考模式在生效，Zed 里按上文打开 `interleaved_reasoning`；
- 返回 200 但没有 `reasoning_content`：这次没有返回思考内容，把返回结果和 request id 发给中转客服确认；
- 返回 401：Key 错了或没带上；
- 提示模型不存在：模型 ID 不在售或拼写不一致，对照 `/v1/models` 的返回改。

本文没有用真实 Key 在 Zed 里跑通上述配置；打开 `interleaved_reasoning` 后续轮仍报 400 的，把导出的对话 Markdown 里的报错原文和 request id 一并发给中转客服排查。

## 参考资料

- Zed 文档：[Use API Access](https://zed.dev/docs/ai/use-api-access)（OpenAI 兼容与 Anthropic 兼容端点、默认能力、`reasoning_effort`、`interleaved_reasoning`、`max_tokens_parameter`）
- Zed 文档：[Agent Panel](https://zed.dev/docs/ai/agent-panel)（工具调用、No tools 标签、图片附件、导出对话）
- DeepSeek 文档：[Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode)（默认开启思考、`reasoning_content` 回传要求与 400 错误）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=zed-relay-deepseek-reasoning-content-400-capabilities-fix&utm_content=footer)，在「令牌」页创建 Key 后按上面的步骤配置 Zed。

## 同专题文章

- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)
- [VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查](https://a37836323.github.io/openlux-api-guides/news/vscode-byok-relay-model-not-showing-utility-model-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

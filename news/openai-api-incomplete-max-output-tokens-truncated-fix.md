---
layout: default
title: "OpenAI API 回答只出一半或返回空、status 是 incomplete 或 finish_reason 是 length 怎么办：输出上限、推理 token 与上下文逐项排查"
description: "OpenAI API 回答只出一半或返回空文本时怎么办：先看 Responses 的 status: incomplete 与 incomplete_details.reason（max_output_tokens），或 Chat Completions 的 finish_reason: length；按官方文档排查输出上限包含推理 token、推理把额度用光、上下文窗口不够、结构化输出 JSON 不完整，并给出判断代码和修复步骤。"
permalink: /news/openai-api-incomplete-max-output-tokens-truncated-fix/
date: 2026-11-15
---

> 更新日期：2026-11-15 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/reasoning)

# OpenAI API 回答只出一半或返回空、status 是 incomplete 或 finish_reason 是 length 怎么办：输出上限、推理 token 与上下文逐项排查

先说结论：用 OpenAI API 时，回答写到一半就停了，或者干脆什么都没返回，先看响应里的结束原因。Responses API 返回 `status: "incomplete"`、`incomplete_details.reason` 是 `max_output_tokens`，或者 Chat Completions 返回 `finish_reason: "length"`，说明这次生成**撞到了 token 上限**，不是网络断了，也不是模型出错。

OpenAI 官方 [Reasoning models 指南](https://developers.openai.com/api/docs/guides/reasoning) 写明：生成的 token 达到上下文窗口上限或你设置的 `max_output_tokens` 时，就会返回 `incomplete`，而且**可能在产生任何可见输出之前就发生**——你为输入和推理 token 付了费，却拿不到一个字。修法是给输出留够空间：调大 `max_output_tokens`（Chat Completions 是 `max_completion_tokens`），或者让输入变短；用推理模型时还可以降低推理强度。

本文适用于 Responses API 和 Chat Completions，直连 OpenAI 或经 OpenAI 兼容中转调用，判断方法相同。下面的字段和说法都来自 OpenAI 官方文档和 API 参考。

## 先对号入座：怎么确认是被 token 上限截断

不同接口的字段不一样，先按下表看清楚到底是哪种结束原因：

| 接口 | 看哪个字段 | 被长度截断时的值 | 其他常见值 |
|---|---|---|---|
| Responses API | `status` | `incomplete` | `completed` 表示正常结束 |
| Responses API | `incomplete_details.reason` | `max_output_tokens` | `content_filter`、`max_messages`、`steered` |
| Responses API 流式 | 最后一个事件的 `type` | `response.incomplete` | 正常结束是 `response.completed` |
| Chat Completions | `choices[].finish_reason` | `length` | `stop`、`tool_calls`、`content_filter` |

几点说明：

- Chat Completions 的 API 参考写明，`finish_reason` 为 `length` 表示「达到了请求里指定的最大 token 数」；`stop` 是自然结束或遇到停止序列；`content_filter` 是内容被过滤器拦掉。
- Responses API 的 `incomplete_details.reason` 除了 `max_output_tokens`，还可能是 `content_filter` 等其他值。只有 `max_output_tokens` 属于本文说的「长度截断」；`content_filter` 是内容过滤，调大上限没有用。
- 流式调用时，官方流式事件参考里 `response.incomplete` 是「响应以未完成状态结束」时发出的事件。如果你的代码只处理 `response.completed`，收到 `response.incomplete` 时就会表现成「输出到一半没了下文」。

## 原因一：输出上限设得太小，而且上限包含推理 token

很多人以为 `max_output_tokens` 只限制看得到的回答，其实不是。API 参考对两个参数的说明都是「可生成 token 数的上限，**包括可见输出 token 和推理 token**」：

| 接口 | 参数 | 官方说明要点 |
|---|---|---|
| Responses API | `max_output_tokens` | 包含可见输出和推理 token，最小值 16 |
| Chat Completions | `max_completion_tokens` | 包含可见输出和推理 token |
| Chat Completions | `max_tokens` | 已废弃，改用 `max_completion_tokens`，且不兼容 o 系列推理模型 |

官方 [Counting tokens 指南](https://developers.openai.com/api/docs/guides/token-counting) 还补充了一点：GPT-5 等模型会生成用来分隔回答通道、工具调用等结构的**格式 token**，它们不出现在回答内容里，也不一定在用量里单独列出，但同样计入 `output_tokens`（Chat Completions 里是 `completion_tokens`），也同样受上面两个上限约束。官方原话是：不要假设用量和可见输出之间有固定差值，需要一定长度的可见输出时，要在上限里留出余量。

所以，如果你按「回答大概 500 字」去设一个很紧的上限，推理和格式 token 一占，可见回答就会被截断。

## 原因二：推理把额度用光了，返回空文本

这是「返回空」最常见的情况。官方 Reasoning 指南说明：

- 推理 token 在 API 里看不到，但**占用上下文窗口，并按输出 token 计费**。
- 视问题复杂度，模型可能生成几百到几万个推理 token。
- 实际用了多少，看响应 `usage.output_tokens_details.reasoning_tokens`（Chat Completions 是 `usage.completion_tokens_details.reasoning_tokens`）。
- 刚开始用推理模型时，官方建议**至少给推理和输出预留 25,000 个 token**，熟悉自己的提示词大概要多少推理 token 后再调整。

判断方法：`status` 是 `incomplete`、`reason` 是 `max_output_tokens`，同时 `output_text` 为空、`output_tokens` 里绝大部分是 `reasoning_tokens`，就是推理阶段把额度用完了。

除了调大上限，还可以降低推理强度。官方说明 `reasoning.effort`（Chat Completions 是 `reasoning_effort`）控制模型想多少，低强度更快、用的 token 更少，高强度想得更完整。可选值因模型而异，比如官方写明 GPT-6 Astra 不支持 `none`，设成 `none` 会返回 HTTP 400；改之前先查该模型支持哪些值。

## 原因三：输入太长，上下文窗口不够放输出

就算你把 `max_output_tokens` 设得很大，也可能被截断，因为还有一道更硬的限制：上下文窗口。官方 [Conversation state 指南](https://developers.openai.com/api/docs/guides/conversation-state) 写明：

- 上下文窗口是单次请求能用的 token 总数，**输入、输出、推理 token 都算在里面**。
- 输出 token 另有每个模型自己的上限。官方举的例子是 `gpt-4o-2024-08-06` 最多生成 16,384 个输出 token、上下文窗口 128k。各模型的数值查 [模型页](https://developers.openai.com/api/docs/models)，不同快照会不一样。
- 提示词很大时（塞了大量资料、示例或很多轮历史）有超出上下文窗口的风险，可能导致输出被截断；超出部分的 token 可能在响应里被截掉。

所以多轮对话越聊越长、或者一次塞进整份文档时，留给输出的空间会越来越少。处理办法是减少输入：裁掉旧的对话轮次、只保留相关段落，或者把大任务拆成几次请求。

想在发请求前知道输入有多少 token，官方提供了输入 token 计数接口 `POST /v1/responses/input_tokens`（SDK 里是 `client.responses.input_tokens.count`），接受和 `responses.create` 相同的输入格式，图片、文件、工具定义都能算。官方也提醒，tiktoken 这类本地分词器只适合纯文本，算不准图片、文件和工具。这个计数接口经中转是否可用，以中转实际返回为准；用不了时，可以看上一次响应 `usage` 里的 `input_tokens` 估算。

## 结构化输出被截断：JSON 解析报错

用 Structured Outputs（JSON Schema）时，截断的表现往往不是「回答短」，而是**拿到一段不完整的 JSON，解析时报错**。官方 [Structured Outputs 指南](https://developers.openai.com/api/docs/guides/structured-outputs) 在「处理边界情况」里写明，模型拒答、或者达到最大 token 上限导致响应不完整时，输出可能不符合你给的 Schema。

官方示例的做法是：解析之前先检查 `status` 是否为 `incomplete`、`incomplete_details.reason` 是否为 `max_output_tokens`，是的话按「响应不完整」处理，不要直接拿去解析。结构化输出的字段多、嵌套深时，同样要按前两节的方法放宽上限。

## 修复步骤：先判断，再调上限，再验证

按官方 Reasoning 指南的示例思路，在代码里先区分「正常结束」和「被截断」，并区分「有部分输出」和「推理阶段就用完了」：

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-6-astra",
    reasoning={"effort": "medium"},
    input=[{"role": "user", "content": "你的问题"}],
    max_output_tokens=25000,
)

if (
    response.status == "incomplete"
    and response.incomplete_details.reason == "max_output_tokens"
):
    if response.output_text:
        print("输出被截断，部分内容：", response.output_text)
    else:
        print("推理阶段就用完了上限，没有可见输出")
    print(response.usage)
```

然后按这个顺序处理：

1. **看用量**：打印 `usage`，对比 `output_tokens` 和其中的 `reasoning_tokens`，确认 token 主要花在推理还是可见输出上。
2. **放宽输出上限**：Responses 调大 `max_output_tokens`，Chat Completions 调大 `max_completion_tokens`；推理模型起步按官方建议预留至少 25,000。还在用 `max_tokens` 的，按 API 参考改用 `max_completion_tokens`。
3. **降推理强度**：任务不复杂时把 `reasoning.effort` 调低，减少推理 token。
4. **缩短输入**：上限已经很大还被截断，就是上下文窗口不够，按原因三裁剪输入。
5. **处理流式**：把 `response.incomplete` 当作结束事件处理，读取其中的 `incomplete_details`，不要只等 `response.completed`。

**怎么算修好了**：Responses API 返回 `status: "completed"`，Chat Completions 返回 `finish_reason: "stop"`（或调用工具时的 `tool_calls`），并且 `output_text` 是完整的回答。

## 经中转调用时要注意什么

经 OpenAI 兼容中转调用时，结束原因的判断方法不变，额外核对三点：

- **地址和接口**：以 OpenLux 为例，Base URL 填 `https://api.openlux.ai/v1`，Responses 请求路径是 `/v1/responses`，Chat Completions 是 `/v1/chat/completions`，鉴权用 `Authorization: Bearer`。可以先请求 `/v1/models`，能列出模型就说明地址和 Key 都对。
- **模型是否支持 Responses**：每个模型支持哪些接口，看价格接口 `https://www.openlux.ai/api/pricing_new` 里的 `supported_endpoint_types`，含 `openai-response` 的才能走 `/v1/responses`。例如本文示例用的 `gpt-6-astra`，按该接口显示同时支持 `openai` 和 `openai-response`。
- **字段以实际返回为准**：`incomplete_details`、`usage` 里的推理 token 等字段由上游模型返回，经中转后请以你实际收到的响应为准；本文没有用真实 Key 逐个模型测试过。

## 参考资料

- OpenAI 官方文档：[Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)（`incomplete` 与 `max_output_tokens`、预留 25,000 token、推理强度）
- OpenAI 官方文档：[Counting tokens](https://developers.openai.com/api/docs/guides/token-counting)（输出 token 包含格式 token、输入 token 计数接口）
- OpenAI 官方文档：[Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)（上下文窗口与输出上限）
- OpenAI 官方文档：[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)（不完整响应的处理）
- OpenAI API 参考：[Create a response](https://developers.openai.com/api/reference/resources/responses/methods/create)、[Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、[Streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events)

想用一个 Key 调用 GPT、Claude、Gemini 等多家模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-incomplete-max-output-tokens-truncated-fix&utm_content=footer)，创建 Key 后先用 `/v1/models` 核对模型名再调用。

## 同专题文章

- [OpenAI API 开 JSON 模式报 400「'messages' must contain the word 'json'」怎么办：json_object 的提示词要求、Responses 写法与改用 Structured Outputs](https://a37836323.github.io/openlux-api-guides/news/openai-api-400-json-object-must-contain-word-json-fix/)
- [OpenAI API 输入太长报 400、超出上下文窗口怎么办：token 计数、服务器端压缩、truncation 与历史裁剪逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-400-context-window-exceeded-fix/)
- [OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-404-model-not-found-fix/)
- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些](https://a37836323.github.io/openlux-api-guides/news/openai-evals-read-only-shutdown-promptfoo-migration/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

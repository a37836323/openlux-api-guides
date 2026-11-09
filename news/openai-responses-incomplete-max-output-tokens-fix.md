---
layout: default
title: "OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办"
description: "OpenAI Responses API 返回 status: incomplete、incomplete_details.reason 为 max_output_tokens，output_text 只有半截或为空时，按官方推理指南判断原因，调高 max_output_tokens、降低 reasoning.effort、给上下文窗口留空间，并说明 Chat Completions 的 finish_reason: length 与验证方法。"
permalink: /news/openai-responses-incomplete-max-output-tokens-fix/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[OpenAI 推理模型指南](https://developers.openai.com/api/docs/guides/reasoning)

# OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办

如果你用 `gpt-6-astra`、`gpt-6.1-sol`、`gpt-5.6-terra` 这类推理模型调 Responses API，拿到的响应里 `status` 是 `incomplete`、`incomplete_details.reason` 是 `max_output_tokens`，`output_text` 只有半截甚至是空的，那么原因基本可以确定：**这次生成的 token（包括看不见的推理 token）撞到了 `max_output_tokens` 上限或模型的上下文窗口上限**。修法是先按 `status` 判断，再调高 `max_output_tokens`、降低推理强度或缩短输入，而不是反复重试同一个请求。

本文依据 OpenAI 官方的 [推理模型指南](https://developers.openai.com/api/docs/guides/reasoning)、[Responses API 参考](https://developers.openai.com/api/reference/resources/responses/methods/create) 和 [token 计数指南](https://developers.openai.com/api/docs/guides/token-counting)，适用于 Responses API 和 Chat Completions 两种调用方式。

## 先确认是不是这个问题

官方推理指南写明：生成的 token 达到上下文窗口上限或你设的 `max_output_tokens` 时，会收到 `status` 为 `incomplete`、`incomplete_details.reason` 为 `max_output_tokens` 的响应；**这可能发生在任何可见输出产生之前**，也就是说你可能为输入和推理 token 付了费，却拿不到可见回答。

对照下面几个字段看一眼返回体：

| 字段 | 截断时的样子 | 说明 |
|---|---|---|
| `status` | `incomplete` | 正常结束是 `completed`；官方列出的取值还有 `failed`、`in_progress`、`cancelled`、`queued` |
| `incomplete_details.reason` | `max_output_tokens` | 撞到输出上限或上下文窗口上限都是这个值 |
| `output_text`（SDK 便捷属性） | 半截文本或空 | 它只是把 `output` 里所有 `output_text` 拼起来，空不代表请求失败 |
| `usage.output_tokens_details.reasoning_tokens` | 占了 `output_tokens` 的大头 | 推理 token 看不见，但占上下文、按输出 token 计费 |
| Chat Completions 的 `finish_reason` | `length` | 官方定义：达到请求里指定的最大 token 数 |

`incomplete_details.reason` 在参考文档里还有 `content_filter`、`max_messages`、`steered` 三个取值，其中 `steered` 是 WebSocket 上 `response.steer` 事件导致的停止。如果你看到的不是 `max_output_tokens`，就不是本文讲的情况，别按下面的方法调上限。

## 为什么推理模型特别容易“只有推理没有正文”

`max_output_tokens` 的官方定义是“一次响应能生成的 token 数上限，**包括可见输出 token 和推理 token**”，最小值是 16。token 计数指南进一步说明，这个上限还包括用来分隔通道、工具调用等结构的不可见格式 token，所以报告的输出 token 可能比你看到的文字多，即使 `reasoning_tokens` 是 0。

推理模型会先“想”再写。官方说，根据问题复杂度，推理 token 可能从几百到几万不等。如果你沿用以前给非推理模型设的小上限（比如几百、一两千），模型很可能在推理阶段就把额度用完，于是：

- 推理还没结束就到上限：`output` 里没有可见文本，`output_text` 为空；
- 推理结束、正文写到一半到上限：`output_text` 只有半截；
- 输入本身很长：剩给推理和输出的上下文空间不够，同样会以 `max_output_tokens` 结束。

## 修复步骤

**第 1 步：按 `status` 判断，不要只看 `output_text`。** 官方示例的写法是先判断 `status == "incomplete"` 且 `incomplete_details.reason == "max_output_tokens"`，再看有没有部分输出：有就是“正文写到一半”，没有就是“推理阶段用完了”。把这两种情况记进日志，后面调参才有依据。

**第 2 步：调高 `max_output_tokens`。** 官方建议刚开始使用推理模型时，**为推理和输出预留至少 25,000 个 token**，熟悉了自己的提示词通常要用多少推理 token 后再逐步收紧。如果你需要固定长度的可见输出，token 计数指南也提醒要在上限里留出余量，不要假设可见文字和计费 token 之间有固定差值。

**第 3 步：降低 `reasoning.effort`。** 官方说较低的推理强度更快、用的 token 更少。注意各模型支持的取值不同：`gpt-6-astra` 不支持 `none`，设成 `none` 会返回 HTTP 400；`gpt-6.1-sol` 不支持 `none` 和 `minimal`，默认是 `medium`。`gpt-6.1-sol`、`gpt-6-sol`、`gpt-6-luna` 和 GPT-5.6 系列不传时默认都是 `medium`。

**第 4 步：给上下文窗口留空间。** 推理 token 也占上下文窗口，各模型的窗口长度以 [模型页](https://developers.openai.com/api/docs/models) 为准。对话历史很长时，先精简历史或拆分任务。另外注意 `truncation` 参数：默认 `disabled` 时，输入超过上下文窗口会直接返回 400；设为 `auto` 时会从对话开头丢弃条目来放进窗口——这两种都不是 `incomplete`，排查时别混在一起。

**第 5 步：用 usage 回看实际用量。** `usage.output_tokens_details.reasoning_tokens` 告诉你这次推理用了多少。连续几次都接近上限，说明上限对这类任务偏小，应该继续加大或降低推理强度。

## Chat Completions 和兼容客户端要注意什么

如果你走的是 `/v1/chat/completions`：

- 上限参数用 `max_completion_tokens`，它同样**包括可见输出和推理 token**；旧的 `max_tokens` 官方已标为废弃，并且不兼容 o 系列推理模型；
- 推理强度用 `reasoning_effort`，支持的取值同样因模型而异；
- 截断的信号是 `finish_reason: "length"`，正常结束是 `stop`，调用工具是 `tool_calls`。

还有一种容易被忽视的情况：有些客户端或网关在 Responses 和 Chat Completions 两种格式之间做转换。Open WebUI 的 [issue #33445](https://github.com/open-webui/open-webui/issues/33445) 报告，非流式请求经它的 Responses 连接转换回 Chat Completions 格式时，上游明明返回 `status: "incomplete"`，客户端拿到的却是 `finish_reason: "stop"`。如果你的回答“看起来正常结束但明显没说完”，先绕开转换层，直接请求 `/v1/responses` 看原始 `status` 和 `incomplete_details`。

流式调用时，Responses API 会以 `response.incomplete` 事件表示响应以未完成状态结束，不要只等 `response.completed`。

## 经 OpenLux 调用时怎么写

OpenLux 的 OpenAI 兼容和 Responses 接口，Base URL 都填 `https://api.openlux.ai/v1`，用 `Authorization: Bearer` 传 Key（Key 在控制台“令牌”页 `https://www.openlux.ai/console/token` 创建）。模型名以价格接口 `https://www.openlux.ai/api/pricing_new` 里在售的为准，看 `supported_endpoint_types` 是否包含 `openai-response`——撰写时 `gpt-6-astra`、`gpt-6.1-sol`、`gpt-6-luna`、`gpt-5.6-terra` 等都同时支持 `openai` 和 `openai-response`。

下面是在官方示例基础上只改了 Base URL 和上限的 Python 写法：

```python
from openai import OpenAI

client = OpenAI(base_url="https://api.openlux.ai/v1", api_key="你的 OpenLux Key")

response = client.responses.create(
    model="gpt-6-astra",
    reasoning={"effort": "medium"},
    input=[{"role": "user", "content": "你的问题"}],
    max_output_tokens=25000,
)

if response.status == "incomplete" and response.incomplete_details.reason == "max_output_tokens":
    print("Ran out of tokens")
    print(response.output_text or "Ran out of tokens during reasoning")
else:
    print(response.output_text)
print(response.usage.output_tokens_details.reasoning_tokens)
```

我们没有逐项核实 OpenLux 对每个模型是否原样返回 `incomplete_details` 等全部字段，所以请以你实际拿到的返回体为准。如果返回体里没有 `status` 字段，可以对比 `usage` 里的输出 token 数和你设的上限：已经等于或非常接近上限，就很可能是撞了上限。返回 401 `Invalid token` 说明 Key 错了或没带上。

## 怎样算修好了

按下面的顺序验证：

1. 先请求 `GET https://api.openlux.ai/v1/models`，能列出模型说明地址和 Key 都对；
2. 用原来出问题的那条输入，按上面的写法调一次，确认 `status` 为 `completed`、`incomplete_details` 为 `null`；
3. `output_text` 是完整回答，不再是空的或半截；
4. 记下 `reasoning_tokens`，多跑几条典型输入，确认它们离 `max_output_tokens` 还有余量，再决定要不要把上限往回收。

如果调高上限、降低推理强度后仍然经常 `incomplete`，多半是输入太长、上下文窗口不够，回到“修复步骤”的第 4 步处理输入长度。

想用一个 Key 调 GPT、Claude、Gemini 等模型的 Responses 和 Chat Completions 接口，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-responses-incomplete-max-output-tokens-fix&utm_content=footer)。

## 同专题文章

- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些](https://a37836323.github.io/openlux-api-guides/news/openai-evals-read-only-shutdown-promptfoo-migration/)
- [OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改](https://a37836323.github.io/openlux-api-guides/news/agent-builder-shutdown-agents-sdk-chatkit-migration/)
- [gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办](https://a37836323.github.io/openlux-api-guides/news/gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix/)
- [whisper-1 将于 2027 年 2 月 26 日下线：换成 gpt-transcribe 要改哪些参数（language、时间戳、字幕格式）](https://a37836323.github.io/openlux-api-guides/news/whisper-1-shutdown-gpt-transcribe-migration/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

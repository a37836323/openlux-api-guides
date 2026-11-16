---
layout: default
title: "OpenAI API 输入太长报 400、超出上下文窗口怎么办：token 计数、服务器端压缩、truncation 与历史裁剪逐项排查"
description: "OpenAI API 输入超过上下文窗口时请求会报 400。本文按官方文档讲清怎么用计数接口确认 token、Responses API 怎么开服务器端压缩或调用 /responses/compact、truncation auto 的局限，以及 Chat Completions 怎么自己裁剪历史。"
permalink: /news/openai-api-400-context-window-exceeded-fix/
date: 2026-11-17
---

> 更新日期：2026-11-17 · 一手来源：[OpenAI API 参考与官方指南](https://developers.openai.com/api/reference/resources/responses/methods/create)

# OpenAI API 输入太长报 400、超出上下文窗口怎么办：token 计数、服务器端压缩、truncation 与历史裁剪逐项排查

先说结论：OpenAI 官方 [Responses API 参考](https://developers.openai.com/api/reference/resources/responses/methods/create)对 `truncation` 参数的说明是，默认值为 `disabled`，此时**如果输入大小超过模型的上下文窗口，请求会以 400 错误失败**。所以长对话、塞进大段文档或很多工具结果之后突然报 400，先怀疑输入超长。解决分三步：先用计数接口确认输入有多少 token；用 Responses API 的项目开启服务器端压缩（`context_management`）或调用 `/responses/compact`；用 Chat Completions 的项目自己裁剪历史、缩短材料。

本文适用于直接调用 OpenAI API，或通过 OpenAI 兼容中转调用 Responses / Chat Completions 的场景。如果请求是成功的，只是回答只出一半、`status` 是 `incomplete` 或 `finish_reason` 是 `length`，那是输出上限的问题，请看另一篇《OpenAI API 回答只出一半或返回空》。

## 先确认：是输入超长，不是别的 400

官方[错误码页](https://developers.openai.com/api/docs/guides/error-codes)没有为“超出上下文窗口”单列错误码，只在 `BadRequestError` 下提示检查请求数据的编码、格式或大小。因此要结合 `error.message`、`error.param` 和出现时机来判断，具体措辞以接口实际返回为准。

| 现象 | 更可能的原因 | 下一步 |
|---|---|---|
| 请求直接 400，对话越长越容易出现，`error.message` 提到上下文或长度 | 输入超过模型上下文窗口 | 按本文第 1～5 步处理 |
| 请求成功，但 `status: incomplete` 或 `finish_reason: length` | 输出上限不够，不是输入超长 | 调大 `max_output_tokens` / `max_completion_tokens` |
| 400 且 `error.param` 指向某个参数（如 `service_tier`、`max_tokens`） | 参数取值或参数名错误 | 按 `error.param` 改对应参数 |
| 短请求也报 400 | 请求格式问题 | 对照 API 参考检查请求体 |

## 上下文窗口里到底算了哪些 token

官方[对话状态指南](https://developers.openai.com/api/docs/guides/conversation-state)的定义是：上下文窗口是单次请求可以使用的最大 token 数，**包括输入、输出和推理 token**。指南举的例子是 `gpt-4o-2024-08-06` 最多生成 16,384 个输出 token，总上下文窗口为 128k token。也就是说，输入不能把整个窗口用满，还要给输出和推理留位置。

| 计入的内容 | 说明 |
|---|---|
| 你发送的输入 | `input` / `messages`、`instructions`，以及前几轮的对话历史 |
| 格式 token | [token 计数指南](https://developers.openai.com/api/docs/guides/token-counting)说明计数包含表示请求结构的格式 token，例如角色和消息边界 |
| 工具、图片、文件 | 计数接口的示例把 `tools`、`input_image` 和文件一起计数 |
| 输出和推理 token | 推理模型思考用的 token 也占窗口 |
| `previous_response_id` 串联的历史 | 官方说明链上之前所有响应的输入 token 都按输入计费，长链条会越滚越大 |

另外，Responses API 参考在 `truncation: auto` 的说明里提到：在某些模型上，API 会从输入上限里预先扣掉模型的最大输出额度，即使你设了更低的 `max_output_tokens`，裁剪也可能更早开始。

## 第 1 步：发请求前先数 token

官方提供 `POST /v1/responses/input_tokens`，接受和 Responses API 相同的输入格式，把准备发给 `responses.create` 的请求原样交给它即可得到准确计数，返回里的 `input_tokens` 就是输入 token 数。官方 Python 示例：

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.input_tokens.count(
    model="gpt-6-astra",
    input="Tell me a joke.",
)
print(response.input_tokens)
```

拿到数字后和所用模型的上下文窗口对比（以官方模型页为准），再减去你打算留给输出和推理的额度。如果输入已经接近或超过这个值，就要用下面的办法缩小上下文。用 Chat Completions 的项目，也可以把同样的对话内容按 Responses 的输入格式交给计数接口估算。

## 第 2 步（Responses API）：开启服务器端压缩

官方[压缩指南](https://developers.openai.com/api/docs/guides/compaction)：在 Responses 创建请求里设置 `context_management` 和 `compact_threshold`，当渲染后的 token 数超过阈值时，服务器会自动压缩，并在同一个流里返回一个加密的压缩项，然后裁剪上下文继续推理，不需要另外调用 `/responses/compact`。

```python
response = client.responses.create(
    model="gpt-6-astra",
    input=input_items,
    store=False,
    context_management=[{"type": "compaction", "compact_threshold": 200000}],
)
```

要点：

- `type` 目前只支持 `compaction`；`compact_threshold` 最小为 1000。阈值建议低于所用模型的上下文窗口，并给输出留出余量。
- 压缩项是不透明的，不是给人读的，原样带进下一轮即可。
- 无状态串联时，像平常一样把输出项追加到下一轮输入；可以选择丢掉最近一个压缩项之前的内容来降低延迟。
- 用 `previous_response_id` 串联时，每轮只传新的用户消息，**不要手动裁剪**。
- 设置 `store=false` 时服务器端压缩对零数据保留（ZDR）友好。

## 第 3 步（Responses API）：手动调用 /responses/compact

如果想自己控制什么时候压缩，可以用独立的 `/responses/compact` 接口。官方说明它完全无状态：你发送完整的上下文窗口，它返回一个新的、压缩后的上下文窗口，可以直接作为下一次 `/responses` 调用的输入。

```python
compacted = client.responses.compact(
    model="gpt-6-astra",
    input=long_input_items_array,
)
next_input = [*compacted.output, {"type": "message", "role": "user", "content": "继续"}]
```

注意两点：返回内容除了压缩项，还可能包含保留下来的原始项，**不要裁剪 `/responses/compact` 的输出**；发给它的窗口本身仍然必须放得进模型的上下文窗口，所以要在快满之前压缩，而不是等到已经报 400 才压缩。

## 第 4 步：旧办法 truncation: "auto"（已标为弃用）

`truncation` 设为 `auto` 时，如果输入超过模型上下文窗口，模型会**从对话开头丢弃条目**来让请求放得下，从而不再报 400。但官方 API 参考已把请求里的这个参数标为 Deprecated（已弃用），而且被丢弃的是最早的对话内容，开头交代过的信息模型可能就看不到了。新代码优先用第 2、3 步的压缩；只是想先让老代码跑起来时，再临时用它。

## 第 5 步（Chat Completions）：自己裁剪历史和材料

Chat Completions 的官方 API 参考里没有 `truncation`、`context_management` 这类自动处理上下文的参数，超长时只能在发请求前自己处理：

1. **只保留需要的历史**：保留系统提示和最近几轮，较早的轮次由你自己的代码先总结成一段短文本再放回去。
2. **缩短大材料**：长文档、日志、代码不要整篇塞进去，先切成小段，只把和当前问题相关的部分放进请求。
3. **清理工具结果**：工具返回的大段原始数据先截取关键字段再回传。
4. **给输出留位置**：上下文窗口包含输出和推理 token，输入不要贴着窗口上限。
5. **考虑迁移到 Responses API**：需要长对话时，可以改用 Responses API，用第 2、3 步的压缩。

## 怎么验证已经解决

- 计数接口返回的 `input_tokens` 加上你预留的输出额度，低于模型上下文窗口。
- 同样的长对话重放到原来报错的那一轮，请求返回 200，响应 `status` 为 `completed`。
- 开了服务器端压缩的，在 token 数超过阈值的那一轮，响应输出里能看到压缩项。
- 再多跑几轮，确认不会每过几轮又报 400。

## 通过 OpenAI 兼容中转调用时

通过 OpenLux 这类中转调用时，Chat Completions 和 Responses 的 Base URL 都填 `https://api.openlux.ai/v1`，Key 在控制台「令牌」页创建。每个模型支持哪些接口，看价格页或价格接口里的 `supported_endpoint_types`（`openai` 是 Chat Completions，`openai-response` 是 Responses）。上下文窗口大小以模型厂商官方文档为准。token 计数和压缩接口能否经中转使用，以服务商说明为准；不确定时，先在你自己的代码里裁剪历史最稳妥。

## 参考资料

- [OpenAI API 参考：Create a response（truncation、context_management）](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [OpenAI 压缩指南（Compaction）](https://developers.openai.com/api/docs/guides/compaction)
- [OpenAI 对话状态与上下文窗口](https://developers.openai.com/api/docs/guides/conversation-state)
- [OpenAI token 计数指南](https://developers.openai.com/api/docs/guides/token-counting)
- [OpenAI 错误码](https://developers.openai.com/api/docs/guides/error-codes)
- [OpenAI API 参考：Create chat completion](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

需要一个同时支持 Chat Completions 和 Responses 的 OpenAI 兼容地址，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-400-context-window-exceeded-fix&utm_content=footer)。

## 同专题文章

- [OpenAI API 回答只出一半或返回空、status 是 incomplete 或 finish_reason 是 length 怎么办：输出上限、推理 token 与上下文逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-incomplete-max-output-tokens-truncated-fix/)
- [OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-404-model-not-found-fix/)
- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些](https://a37836323.github.io/openlux-api-guides/news/openai-evals-read-only-shutdown-promptfoo-migration/)
- [OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办](https://a37836323.github.io/openlux-api-guides/news/openai-responses-incomplete-max-output-tokens-fix/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

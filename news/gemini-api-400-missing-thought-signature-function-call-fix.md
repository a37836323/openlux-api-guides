---
layout: default
title: "Gemini API 函数调用报 400「content block is missing a thought_signature」怎么办：思维签名的回传规则与改法"
description: "Gemini 4、Gemini 3 函数调用续轮报 400「Function call ... content block is missing a thought_signature」：原因是回传历史时丢了 functionCall 部分的 thoughtSignature。按官方文档讲清当前轮校验规则、并行与顺序调用、SDK 追加完整响应、REST 原样回传、迁移历史用占位签名，以及经中转或 OpenAI 兼容格式调用时怎么排查。"
permalink: /news/gemini-api-400-missing-thought-signature-function-call-fix/
date: 2026-11-25
---

> 更新日期：2026-11-25 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/thought-signatures?generate-content=true)

# Gemini API 函数调用报 400「content block is missing a thought_signature」怎么办：思维签名的回传规则与改法

用 Gemini 4 或 Gemini 3 做函数调用（Function Calling），第一步正常返回 `functionCall`，把函数结果发回去时却报 400，提示 `Function call ... in the ... content block is missing a thought_signature`：原因是你回传的历史里，模型那一轮的 `functionCall` 部分**丢了 `thoughtSignature` 字段**。按 Google 官方 [思维签名文档](https://ai.google.dev/gemini-api/docs/thought-signatures?generate-content=true)，Gemini 4 和 Gemini 3 在函数调用时必须把签名原样传回，否则会返回校验错误。改法只有一条原则：**把模型返回的内容原样放回历史，不要只抄函数名和参数。**

本文适用于用 `generateContent` 接口（REST 或自己拼历史）调用 Gemini 函数调用的情况，也适用于经中转平台调用 Gemini 模型。用官方 Google Gen AI SDK 并把完整响应追加进历史时，SDK 会自动处理签名，一般不会遇到这个错。

## 报错长什么样、哪些模型会报

官方文档给出的报错格式是：

```text
Function call `<Function Call>` in the `<index of contents array>` content block is missing a `thought_signature`.
```

例如 `Function call FC1 in the 1. content block is missing a thought_signature.`，其中序号指的是 `contents` 数组里出问题的那一条。

不同模型的要求不一样（据官方思维签名页「不同模型」一节和[思考文档](https://ai.google.dev/gemini-api/docs/thinking?generate-content=true)）：

| 模型系列 | 有函数调用时签名在哪 | 回传要求 | 漏了会怎样 |
|---|---|---|---|
| Gemini 4、Gemini 3 | 第一个 `functionCall` 部分 | 必须原样回传 | 400 校验错误（Gemini 3 Flash 用 `minimal` 思考等级时也一样） |
| Gemini 2.5 | 响应的第一个部分（不论类型） | 官方写明可选 | 文档未列为必须，不在这条 400 的范围内 |
| Gemini 4、Gemini 3，没有函数调用的回复 | 模型产生思考时，在最后一个部分 | 建议回传，不强制校验 | 不报错，但官方说推理质量可能下降 |

所以同一段代码在 Gemini 2.5 上正常、换到 Gemini 3 或 Gemini 4 后才报这个错，可能是代码一直在丢签名，只是 2.5 不要求回传。

## 官方的校验规则：哪些签名必须带

官方文档把一次用户提问到模型给出最终文字回答的过程叫一个「轮」（turn），中间每次模型发起函数调用叫一「步」（step）。校验规则是：

1. **只校验当前这一轮**，更早的轮不校验。API 从历史最新一条往回找，找到最近一条带普通内容（如 `text`）的用户消息，作为当前轮的起点；只含 `functionResponse` 的用户消息不算新一轮。
2. 当前轮里**每一步的第一个 `functionCall` 部分**都必须带签名；任何一步漏了，就返回 400。
3. **顺序多步调用**：每一步的函数调用都有自己的签名，第三步回传时，要同时带上第一步和第二步的签名。
4. **并行调用**：模型一次返回多个 `functionCall` 时，只有第一个带签名，后面的没有；回传时第一个部分的签名必须原样保留在原来的位置。
5. 签名必须放回**它原来所在的那个部分**里。

## 最常见的五种丢签名写法

对照下面几种情况检查你的代码：

1. **重建历史时只抄了函数名和参数。** 很多代码从响应里取出 `name`、`args`，再自己拼一个新的 `functionCall` 部分放进历史，`thoughtSignature` 就这样丢了。
2. **合并或拆分了部分。** 官方明确要求：不要把带签名的部分和不带签名的部分合并，也不要把两个都带签名的部分合并，签名字符串无法合并。
3. **并行调用的结果交错回传。** 官方常见问题写明：模型返回「FC1 + 签名、FC2」时，期望的回传顺序是「FC1 + 签名、FC2、FR1、FR2」；如果写成「FC1 + 签名、FR1、FC2、FR2」，会返回 400。
4. **历史来自别的模型或由客户端自己构造。** 从其他模型迁过来的对话记录、或者你在客户端确定性执行后自己补进去的函数调用，本来就没有签名（见下文「迁移历史」一节）。
5. **函数结果没带调用 ID。** 这不是签名问题，但官方在同一组规则里要求 `functionResponse` 必须带上对应 `function_call` 的 `id`，自己拼历史时一起检查。

## 改法一：用官方 SDK 时追加完整响应

官方 [函数调用文档](https://ai.google.dev/gemini-api/docs/function-calling?generate-content=true) 第 4 步的写法是把模型响应的整个 `content` 追加进历史，再追加函数结果。Python 示例（摘自官方文档）：

```python
function_response_part = types.Part.from_function_response(
    name=tool_call.name,
    response={"result": result},
    id=tool_call.id,
)
contents.append(response.candidates[0].content)
contents.append(types.Content(role="user", parts=[function_response_part]))
```

关键是 `response.candidates[0].content` 整个放回去，签名就在里面。如果你在这一步之前对 `parts` 做过过滤、改写或重新组装，就要按上面的规则检查签名还在不在。

## 改法二：用 REST 自己拼历史时原样保留 thoughtSignature

直接调 REST 接口时，模型返回的部分长这样（摘自官方文档的顺序调用示例）：

```json
{
  "functionCall": { "name": "check_flight", "args": { "flight": "AA100" } },
  "thoughtSignature": "<Signature A>"
}
```

发下一次请求时，`contents` 里依次放：用户原始问题、模型这一部分（**连同 `thoughtSignature`**）、你的 `functionResponse`。模型第二步再返回 `book_taxi` 和签名 B 后，第三次请求要把签名 A 和签名 B 都带上。官方要求签名「按收到的样子原样传回」，不要解析、截断或重新编码。

另外两点来自官方：没有函数调用的回复，签名在最后一个部分里，建议也传回；流式输出且这次回复没有函数调用时，签名可能出现在一个文本为空的部分里，官方建议一直解析到返回 `finish_reason` 为止，拼接流式结果时不要把空文本部分丢掉。

## 迁移历史或自己构造的函数调用

官方常见问题专门回答了这种情况：从别的模型迁移对话记录，或者需要把客户端自己执行过的函数调用和结果告诉模型，这些 `functionCall` 部分不是 API 生成的，没有签名。官方强烈不建议往请求里注入自定义的函数调用块；实在避免不了时，可以在签名字段里填 `context_engineering_is_the_way_to_go` 或 `skip_thought_signature_validator` 两个占位值之一来跳过校验。

只给这类没有真实签名的部分填占位值。模型自己返回过签名的部分，仍然要传回真实签名。

## 经中转或 OpenAI 兼容格式调用时

官方 [OpenAI 兼容文档](https://ai.google.dev/gemini-api/docs/openai) 说明 Gemini 3 在 Chat Completions 兼容接口里也支持思维签名，但签名能不能在你用的客户端、框架和中转之间完整往返，取决于每一层是否保留了响应里的这部分数据，本文没有逐一验证。排查顺序建议：

1. 打印上一轮的原始响应，确认里面有没有签名；回传时把助手消息整条原样放回，不要只保留 `tool_calls` 里的函数名和参数。
2. 如果兼容格式下拿不到签名、续轮仍报这个错，改用 Gemini 原生格式，按上面改法二自己保留 `thoughtSignature`。

以 OpenLux 为例：原生格式 Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，Key 用 `x-goog-api-key` 请求头或 `?key=` 查询参数传；OpenAI 兼容格式 Base URL 填 `https://api.openlux.ai/v1`。Gemini 模型（如 `gemini-4-hydrogen`、`gemini-3.8-flash`）两种格式都有，以价格页标注为准。Key 错误会返回 401 `Invalid token`。

## 改完怎么验证

1. 用一个会触发两步以上函数调用的问题重跑（如官方示例「查航班 AA100，延误就订车」），确认每次请求都返回 200，最后拿到文字回答。
2. 把最后一次请求的 `contents` 打印出来，核对当前轮每一步的第一个 `functionCall` 部分都有 `thoughtSignature`。
3. 用官方文档的检查写法确认签名存在，例如 Python 里判断 `part.thought_signature` 是否有值。
4. 并行调用时核对顺序是「全部函数调用在前、全部函数结果在后」。

注意：官方思考文档写明，回传的签名会计入后续请求的输入 token。这是保留推理上下文的正常开销，不要为了省 token 删掉函数调用部分的签名。

## 参考资料

- Google 官方：[Thought signatures（generateContent）](https://ai.google.dev/gemini-api/docs/thought-signatures?generate-content=true)
- Google 官方：[Function calling（generateContent）](https://ai.google.dev/gemini-api/docs/function-calling?generate-content=true)
- Google 官方：[Thinking（generateContent）](https://ai.google.dev/gemini-api/docs/thinking?generate-content=true)
- Google 官方：[OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai)
- 相关：《[Gemini API 报 400 INVALID_ARGUMENT 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)》《[Gemini 函数调用返回 MALFORMED_FUNCTION_CALL 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-malformed-function-call-fix/)》

想用一个 Key 同时调用 Gemini、GPT、Claude 等模型，可以在 [OpenLux 注册](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-400-missing-thought-signature-function-call-fix&utm_content=footer)，在控制台创建令牌后按本站接入教程配置。

## 同专题文章

- [Gemini API 回答一直重复、表格横线刷屏或 JSON 里一串换行怎么办：按官方排错指南改提示词、Schema 与工具调用](https://a37836323.github.io/openlux-api-guides/news/gemini-api-repetitive-output-table-loop-fix/)
- [Gemini API 返回空、finishReason 是 SAFETY 或 RECITATION、报「Request blocked due to safety violations」怎么办：提示被拦、回答被拦与安全设置逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-safety-recitation-blocked-empty-response-fix/)
- [Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱](https://a37836323.github.io/openlux-api-guides/news/gemini-4-carbon-api-price-november-30/)
- [Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)
- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)
- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

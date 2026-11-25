---
layout: default
title: "Gemini API 用工具检索报 400「tool_search tool must be specified when using defer_loading」怎么办：defer_loading、tool_search 与无状态回传逐项排查"
description: "Gemini API 用工具检索（defer_loading、tool_search）报 400 怎么办：按官方 Tool retrieval 文档与排错指南对照 tool_search tool must be specified、Server side tool call context must be circulated、missing thought_signature、deferred loading is not supported 四种报错，每轮带完整 tools、store=false 原样回传检索步骤与 signature，并说明只支持 Interactions API 与支持的模型。"
permalink: /news/gemini-api-400-tool-search-defer-loading-fix/
date: 2026-11-26
---

> 更新日期：2026-11-26 · 一手来源：[Google AI for Developers 官方文档](https://ai.google.dev/gemini-api/docs/tool-retrieval)

# Gemini API 用工具检索报 400「tool_search tool must be specified when using defer_loading」怎么办：defer_loading、tool_search 与无状态回传逐项排查

在 Gemini API 里给函数加了 `defer_loading: true`（工具检索，按需加载工具定义），请求却返回 400，报错是 `tool_search tool must be specified when using defer_loading.`、`Server side tool call context must be circulated when using deferred loading functions.`、`Tool call part is missing thought_signature.` 或 `deferred loading is not supported for this model` 之一。按 Google 官方 [Tool retrieval 文档](https://ai.google.dev/gemini-api/docs/tool-retrieval) 和 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting)，这几种 400 都是**请求的写法不满足工具检索的规则**，原样重试不会好，要按报错改请求。

对照官方列出的原因，主要分三类：`tools` 里没有服务端 `{"type": "tool_search"}`（尤其是第二轮回传 `function_result` 时漏了）；自己管理历史（`store=false`）时丢了 `tool_search_call` 步骤或 `signature`；用的模型或接口不支持工具检索。

适用范围：工具检索目前是**预览功能**，只在 **Interactions API** 上提供，需要 `v1beta` API 版本；官方写明 `generateContent` 不支持它。如果你用的是 `generateContent` 的普通函数调用，本文不适用，函数调用的其他 400 见《[Gemini API 报 400 INVALID_ARGUMENT 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)》。

## 先对照：官方列出的四种报错和改法

下表整理自官方 Tool retrieval 文档的 Common errors 一节：

| 报错原文 | 官方说明的原因 | 改法 |
|---|---|---|
| `tool_search tool must be specified when using defer_loading.` 或 `When defer_loading is set on a FunctionDeclaration, a Tool with tool_search must also be provided in the request.` | 有工具设了 `defer_loading: true`，但请求里没有服务端 `tool_search`（例如用了 `execution: "client"`，或后续轮次漏了 `tool_search`） | 每次请求都在 `tools` 里带上 `{"type": "tool_search"}`，或者去掉 `defer_loading` |
| `Server side tool call context must be circulated when using deferred loading functions.` | 无状态请求里漏了 `tool_search_call` 步骤，或模型没先搜索就按名字调用了延迟加载的工具 | 原样回传所有 `tool_search_call` 和 `tool_search_result` 步骤；系统指令里点名的工具不要设为延迟加载 |
| `Tool call part is missing thought_signature.` 或 `Function call is missing a thought_signature in functionCall parts.` | 回传的 `tool_search_call`、`tool_search_result`、`thought` 或 `function_call` 步骤缺少 `signature` 字段 | 把响应里的步骤原样追加到历史，`signature` 不要删、不要改 |
| `deferred loading is not supported for this model` | 目标模型不支持工具检索 | 换成官方支持列表里的模型 |

官方支持工具检索的模型是：`gemini-4-carbon`、`gemini-4-neon`、`gemini-4-hydrogen`、`gemini-4-argon`、`gemini-3.8-flash`、`gemini-3.6-flash`。

## 排错指南里另外列出的 400 情况

官方排错指南的 Tool retrieval errors 一节还列了几种会返回 400 的写法，逐条对照自己的 `tools` 数组：

1. **`tool_search` 声明了不止一个**：一个请求里只能有一个 `tool_search`。
2. **字段放错了位置**：客户端检索（`execution: "client"`）的 `tool_search` 必须有 `name` 和 `description`；服务端检索的 `tool_search` 反过来**不能**设置 `name`、`description`、`parameters`。
3. **`short_description` 用在了没延迟加载的函数上**：`short_description` 只在 `defer_loading: true` 时有效。
4. **`defer_loading` 配了客户端检索**：`defer_loading` 只对服务端检索有效，不能和客户端 `tool_search` 搭配；官方也写明服务端和客户端检索不能在同一请求里混用。
5. **模型调用了没被搜索加载过的延迟工具，你又回传了它的 `function_result`**：官方说这通常是因为该函数名出现在系统指令或别的工具输出里。被点名的工具不要延迟加载。

## 容易漏的一步：第二轮回传结果时也要带 tools

官方明确写了：**API 不会在轮次之间保存工具声明**。即使用 `previous_interaction_id` 串联对话，每次请求（包括只回传 `function_result` 的那一轮）都要把完整的 `tools` 数组再发一遍，包括 `tool_search`、延迟加载的工具和已经加载过的工具。

很多代码第一轮带了 `tools`，第二轮只发 `previous_interaction_id` 和 `function_result`，于是延迟加载的工具没有了配套的 `tool_search`，就会出现第一种报错。官方示例的第二轮写法（Python）是：

```python
followup = client.interactions.create(
    model="gemini-4-hydrogen",
    previous_interaction_id=interaction.id,
    tools=tools,  # 每一轮都带完整 tools
    input=[{
        "type": "function_result",
        "name": fc_step.name,
        "call_id": fc_step.id,
        "result": [{"type": "text", "text": '{"amount": 92.4, "currency": "EUR"}'}],
    }],
)
```

官方还提醒，有些问题**不报错**：多轮对话里模型找不到延迟工具、只调用之前用过的工具、调用请求里没声明的函数，或返回名字以 `retriever:` 开头的内部调用步骤。这些情况同样先检查每次请求是否都带了完整 `tools`。

## 自己管理历史（store=false）时怎么回传

如果用 `store=false` 自己拼历史，官方要求把响应里模型生成的每个步骤**原样**追加到历史：

- `tool_search_call` 和 `tool_search_result` 保持原来的顺序，放在 `function_call` 之前；
- `tool_search_call`、`tool_search_result`、`thought`、`function_call` 上的 `signature` 都要保留；
- 使用能识别 `tool_search_call`、`tool_search_result` 步骤的 SDK 版本，避免序列化时被丢掉。

漏掉 `tool_search_call` 或去掉任一步骤的 `signature`，会在你回传 `function_result` 的那一轮返回 400；漏掉 `tool_search_result` 不报错，但已加载的工具定义会从上下文里消失。官方 Python 示例的做法是把 `interaction.steps` 里的每一步 `model_dump()` 后追加进历史，再追加 `function_result`，第二次请求同样带上 `store=False` 和完整 `tools`。思维签名的一般规则可参考《[Gemini API 函数调用报 400「content block is missing a thought_signature」怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-missing-thought-signature-function-call-fix/)》。

## 改完怎么验证

按官方的服务端检索响应格式，修好后应满足：

1. 第一轮响应的 `steps` 里依次出现 `tool_search_call`、`tool_search_result` 和 `function_call`，搜索步骤由 API 在同一个请求内完成，你只需要执行 `function_call`。
2. 回传 `function_result`（并带上完整 `tools`）后不再返回 400，拿到最终文本（`output_text`）。
3. 判断要不要执行函数时，检查每次响应的 `steps` 里有没有 `function_call`，不要只看 `status`：官方说明返回 `function_call` 时 `status` 不一定是 `requires_action`。

另外几条官方建议能减少出错：大多数轮次都会用到的核心工具不要延迟加载，只延迟长尾工具；延迟工具也要写完整的 `parameters`，否则检索到之后模型也无法调用；相似的工具名按服务加前缀（例如 `billing_get_customer`、`crm_get_customer`）。

## 通过中转平台调用时

工具检索只在 Interactions API 上提供。OpenLux 目前公开说明的 Gemini 原生入口是 `https://api.openlux.ai` 下的 `/v1beta/models/<模型>:generateContent`（Key 放在 `x-goog-api-key` 请求头或 `?key=` 参数里），而官方写明 `generateContent` 不支持工具检索。所以在中转上使用 `tool_search`、`defer_loading` 之前，先向平台确认是否提供 Interactions 接口；不提供时，按官方的模式对比表改用静态加载，把要用的工具完整写在 `tools` 里（官方建议少于 20 个、比较稳定的工具用静态加载）。

## 常见问题

**工具检索要额外收费吗？** 官方说明没有单独费用，按模型的输入、缓存和输出标准价格计费；每次服务端搜索会在请求内多一次模型调用，这部分提示 token 记在 `total_tool_use_tokens` 里，按输入价格计费。

**搜不到工具会报错吗？** 不会。官方写明搜索没有匹配到任何延迟工具时，返回的是一段文本，而不是结构化错误。

**已经加载的工具能卸载吗？** 不能。官方说明加载过的工具会在整个对话剩余部分留在上下文里。

需要一个可同时调用 Gemini、Claude、GPT 的 API 入口，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-400-tool-search-defer-loading-fix&utm_content=footer)

## 同专题文章

- [Gemini API 函数调用报 400「content block is missing a thought_signature」怎么办：思维签名的回传规则与改法](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-missing-thought-signature-function-call-fix/)
- [Gemini API 回答一直重复、表格横线刷屏或 JSON 里一串换行怎么办：按官方排错指南改提示词、Schema 与工具调用](https://a37836323.github.io/openlux-api-guides/news/gemini-api-repetitive-output-table-loop-fix/)
- [Gemini API 返回空、finishReason 是 SAFETY 或 RECITATION、报「Request blocked due to safety violations」怎么办：提示被拦、回答被拦与安全设置逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-safety-recitation-blocked-empty-response-fix/)
- [Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱](https://a37836323.github.io/openlux-api-guides/news/gemini-4-carbon-api-price-november-30/)
- [Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)
- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "OpenAI 12 小时提示缓存怎么开：prompt_cache_options.ttl 报 400、类型报错与命中核对"
description: "OpenAI Responses API 新增 12 小时提示缓存：prompt_cache_options.ttl 设为 12h 报 400、Python SDK 类型报错、cached_tokens 不增加的排查与成本判断。"
permalink: /news/openai-prompt-cache-12h-ttl-setup/
date: 2026-10-25
---

> 更新日期：2026-10-25 · 一手来源：[OpenAI 官方文档 Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

# OpenAI 12 小时提示缓存怎么开：prompt_cache_options.ttl 报 400、类型报错与命中核对

2026 年 10 月 20 日，OpenAI 在 Responses API 上加了 12 小时提示缓存：把 `prompt_cache_options.ttl` 设成 `"12h"`，缓存的最短保留时间就从默认的 30 分钟延长到 12 小时，适合相隔几小时才会再次发送同一段长指令、工具定义或参考资料的场景。

开启后最常见的问题有三类：请求返回 `400 invalid_request_error`；请求能成功，但 pyright / mypy 报类型错误；开了 12h，账单里的缓存读取（`cached_tokens`）却没有增加，费用反而变高。先说结论：

1. 12h 只适用于 GPT-5.6 及之后的模型，而且只能在 Responses API 里用。更早的模型要继续用 `prompt_cache_retention`。
2. openai-python 的类型定义还没跟上，`ttl` 只写了 `"30m"`。这是类型问题，不影响请求本身。
3. 12h 写入的单价是普通输入的 2.5 倍，只有在 12 小时内反复命中才划算；从 30m 升级到 12h 会重新计一次 12h 写入。

本文依据 OpenAI 官方文档 [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) 和 [API Changelog（2026-10-20 条目）](https://developers.openai.com/api/docs/changelog)。具体单价以 OpenAI 官网价格页为准。

## 先对照症状，判断属于哪一类

| 现象 | 可能的原因 | 处理方向 |
|---|---|---|
| 带 `"ttl": "12h"` 的请求返回 `400 invalid_request_error` | 模型早于 GPT-5.6，或者不是在 Responses API 里调用 | 换成 GPT-5.6 及之后的模型并改用 Responses API；旧模型改用 `prompt_cache_retention` |
| 请求成功，但 pyright / mypy 报 `prompt_cache_options` 类型不匹配 | SDK 的类型把 `ttl` 写成了 `Literal["30m"]` | 运行时不用改；类型检查用 `extra_body` 绕过，或等 SDK 修复 |
| 读不到 `cache_write_tokens_details` 字段 | SDK 的 `InputTokensDetails` 类型里还没有这个字段 | 从 `model_extra` 里取，或者直接读原始 JSON |
| 开了 12h，`cached_tokens` 仍然是 0 | 第一次请求只会写入；前缀不足 1,024 个 token；前缀每次都有变化 | 先看 `cache_write_tokens` 有没有值，再排查前缀 |
| 开了 12h 以后输入费用变高 | 12h 写入按 2.5 倍计费；30m 升级到 12h 要重新写入 | 只给真正长期不变的内容设 12h |

## 400 invalid_request_error：先查模型和接口

官方文档对 TTL 的说明是：`prompt_cache_options.ttl` 适用于 GPT-5.6 及之后的模型，默认 `"30m"`，`"12h"` 只在 Responses API 中可用；不支持的取值会返回 `400 invalid_request_error`。官方没有逐条列出哪些组合会触发 400，所以按下面的顺序逐项对照：

1. **确认模型。** 官方文档里 `prompt_cache_options` 只列在 GPT-5.6 及之后的模型下；更早的模型（例如 gpt-5.5、gpt-5.4、gpt-4.1）要用旧参数 `prompt_cache_retention`，取值是 `in_memory` 或 `24h`，各模型支持哪些取值以官方文档为准。官方迁移清单写的是：升级到 GPT-5.6 及之后的模型时，用 `prompt_cache_options.ttl` 替换 `prompt_cache_retention`。
2. **确认接口。** 12h 只在 Responses API（`/v1/responses`）中可用。还在用其他接口的，要么保持默认的 30m，要么迁移到 Responses API 后再开 12h。
3. **确认拼写和位置。** 请求级写法是 `"prompt_cache_options": {"ttl": "12h"}`；只想给某一段内容设 12h，就在那个内容块上写 `"prompt_cache_breakpoint": {"mode": "explicit", "ttl": "12h"}`。官方文档列出的 `ttl` 取值只有 `"30m"` 和 `"12h"` 两个字符串，不要写成其他格式。
4. **确认放断点的位置。** 官方说明顶层 `instructions` 不能放断点，要把这段文字移到 developer 消息的 `input_text` 块里；`additional_tools` 里的项目也不接受 `prompt_cache_breakpoint`。

官方文档给出的混合写法，大致是这样（长期不变的资料设 12h，会话上下文用默认 30m，当前问题不缓存）：

```json
{
  "model": "gpt-6.1-sol",
  "prompt_cache_options": { "mode": "explicit", "ttl": "30m" },
  "input": [
    { "role": "developer", "content": [
      { "type": "input_text", "text": "<长期不变的指令和资料>",
        "prompt_cache_breakpoint": { "mode": "explicit", "ttl": "12h" } } ] },
    { "role": "user", "content": [
      { "type": "input_text", "text": "<本次会话的上下文>",
        "prompt_cache_breakpoint": { "mode": "explicit" } },
      { "type": "input_text", "text": "<当前问题>" } ] }
  ]
}
```

规则是：请求级的 `ttl` 作用于隐式断点，以及没写 `ttl` 的显式断点；断点上自己写的 `ttl` 优先；两处都不写就是 `"30m"`。

## Python SDK 报类型错误：请求其实是成功的

openai-python 仓库的 [issue #4156](https://github.com/openai/openai-python/issues/4156)（2026-10-22，用户反馈）指出，在 v3.36.1 中：

- 请求参数 `PromptCacheOptions.ttl` 的类型是 `Literal["30m"]`，文档字符串还写着目前只支持 30m，所以 pyright / mypy 会拒绝 `"12h"`，但请求在运行时能成功，响应里也会返回 `ttl='12h'`。
- 响应 `Response.prompt_cache_options.ttl` 同样只声明了 `"30m"`。
- `usage.input_tokens_details` 的类型里没有 `cache_write_tokens_details`，只能当成没有类型的字典来读。

截至本文写作时，这个 issue 仍未关闭，也没有对应的修复版本。在 SDK 更新之前，可以按 [openai-python README](https://github.com/openai/openai-python/blob/main/README.md) 里官方说明的方式处理：

- **发送参数：** README 说明，没有写进类型的参数可以用 `extra_body` 传。把 `prompt_cache_options` 放进 `extra_body`，类型检查就不会报错：

```python
response = client.responses.create(
    model="gpt-6.1-sol",
    input=messages,
    extra_body={"prompt_cache_options": {"ttl": "12h"} },
)
```

- **读取字段：** README 说明，类型里没有的响应字段可以通过 Pydantic 模型的 `model_extra` 字典取到。例如 `response.usage.input_tokens_details.model_extra.get("cache_write_tokens_details")`。

SDK 修复类型之后，再改回普通参数。

## 开了 12h 却没有命中：按 usage 字段排查

官方文档列出的核对字段：

- `usage.input_tokens_details.cached_tokens`：按读取计费的 token 数，不包括按写入计费的部分（包括从 30m 升级到 12h 的写入）。
- `usage.input_tokens_details.cache_write_tokens`：本次写入缓存的 token 数。
- `cache_write_tokens_details.ttl_30m_tokens` 和 `ttl_12h_tokens`：两者不重叠，加起来等于 `cache_write_tokens`；即使是 0 也会返回。

所以，第一次请求看到 `cached_tokens` 为 0、`ttl_12h_tokens` 有值，是正常的，说明写入成功了。如果后续请求仍然没有读取，按下面几点检查：

1. **前缀太短。** GPT-5.6 及之后的模型，可缓存的提示至少要 1,024 个 token，OpenAI 系统内部附加的 token 不算在内。
2. **前缀变了。** 官方说明，缓存复用要求整段前缀完全一致。改了 `model`、`tools`、`parallel_tool_calls`、`text.format`、`reasoning.effort`、`text.verbosity`、`context_management` 中的任何一项，都可能让前缀对不上。时间戳、用户信息这类会变的内容要放在最后。
3. **工具列表变了。** 要临时禁用工具，用 `tool_choice: "none"`，不要删掉工具定义；要限制本次能调用哪些工具，用 `allowed_tools`。
4. **只用了隐式断点。** 官方提醒，只靠隐式断点时，写入会一直写到动态内容的末尾，下次问题一变就对不上。在不变内容的末尾加一个显式断点，前缀才能被复用。
5. **从隐式切换到仅显式模式。** 之前隐式写入的缓存，除非显式断点正好落在同一个边界上，否则会错过。
6. **改写了旧消息。** 把消息 A 改成 A+B，原来的缓存终点就丢了。应该追加新消息，或者把新内容放进一个带断点的独立内容块。
7. **跨组织、跨区域。** 缓存不在不同组织之间共享，也不跨区域处理边界共享，而且不能手动清除。

另外，官方说明 12h 是“最短保留时间”：它决定这段时间内能否按读取价计费，但不保证每次请求都能复用缓存或降低延迟；OpenAI 也可能保留得比最短时间更久。

## 什么情况值得开 12h：先算写入成本

根据官方文档，GPT-5.6 及之后的模型：

- `"30m"` 写入按普通输入的 1.25 倍计费，`"12h"` 写入按 2.5 倍计费，这是总价，不是在普通输入价上另加；两种 TTL 的读取价相同。
- 同一个 token 被多个写入覆盖时只计一次，按其中最长的 TTL 计费。
- 已经有 30m 缓存的内容升级到 12h，要重新计一次 12h 写入，之前的 30m 写入不抵扣。
- 已经被有效 12h 缓存覆盖的内容，再次请求按读取计费。读取不会重置 12h 的计时，也不会产生写入费用。
- 每个请求最多产生 4 次缓存写入，隐式断点占 1 次，显式断点最多 3 个。

实际选择时可以这样判断：

1. 同一段内容在 30 分钟内会被反复请求：保持默认 30m 就够了。
2. 同一段内容会间隔几个小时才再次请求（例如每天几次的批处理、长期固定的系统指令和工具定义）：给这一段单独设 12h。
3. 每次都会变化的内容：放在最后一个断点之后，按普通输入计费，不产生写入费用。

成本公式按官方文档：普通输入 = `input_tokens − cached_tokens − cache_write_tokens`；总价 = 普通输入 × 输入价 + 读取 token × 读取价 + 30m 写入 × 1.25 倍输入价 + 12h 写入 × 2.5 倍输入价。已经把两类写入分别算过，就不要再重复加一次 `cache_write_tokens`。

## 验证步骤与成功标准

1. 用同一段不少于 1,024 个 token 的固定前缀，发第一次请求，给它设 12h 断点。
2. 检查响应：`cache_write_tokens_details.ttl_12h_tokens` 大于 0，说明 12h 写入成功。
3. 只改最后一个断点之后的内容，再发第二次请求。
4. 检查响应：`cached_tokens` 大于 0，且 `ttl_12h_tokens` 为 0 或明显变小（官方说明，已被有效 12h 缓存覆盖的内容按读取计费），说明读取命中。
5. 间隔超过 30 分钟（但在 12 小时内）再发一次，`cached_tokens` 仍大于 0 就符合预期。如果没有命中，先排查前缀；同时要知道官方说明最短保留时间不保证每次请求都能复用缓存。
6. 在 OpenAI 控制台的 Prompt Caching 面板看命中率，命中率 = 读取 token 总数 ÷ 输入 token 总数。没有命中时，可以用官方的 Prompt Cache Diagnostics 工具排查原因。

如果第 4 步一直没有读取，回到上一节按顺序排查前缀；如果第 1 步就返回 400，回到“先查模型和接口”。

## 来源

- 官方指南：[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- 官方更新日志（2026-10-20 条目）：[API Changelog](https://developers.openai.com/api/docs/changelog)
- SDK 官方说明：[openai-python README（Undocumented request params / response properties）](https://github.com/openai/openai-python/blob/main/README.md)
- 用户反馈（非官方结论）：[openai-python issue #4156](https://github.com/openai/openai-python/issues/4156)

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-prompt-cache-12h-ttl-setup&utm_content=footer)。

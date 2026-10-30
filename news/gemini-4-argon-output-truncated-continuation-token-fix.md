---
layout: default
title: "换成 gemini-4-argon 后回答被截断、返回空文本或报 400：单次 32K/64K 上限与 continuation_token 续写"
description: "换成 gemini-4-argon 后回答停在 32K/64K、返回空文本或报 400 的排查：按 finishReason 区分 CONTINUATION 与 MAX_TOKENS，SDK 升级与 REST continuationToken 续写循环，thinking_level、显式缓存和续写额度引起的 400，以及长解码下的 token 统计。"
permalink: /news/gemini-4-argon-output-truncated-continuation-token-fix/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/generate-content/long-decode)

# 换成 gemini-4-argon 后回答被截断、返回空文本或报 400：单次 32K/64K 上限与 continuation_token 续写

把模型从 Gemini 3.x 换成 `gemini-4-argon` 后，常见的三种异常是：长回答在 32K 或 64K token 处突然停住；返回的 `text` 是空字符串；带上续写参数或旧的缓存、思考参数后报 400。原因大多不是模型出错，而是 Gemini 4 Argon 改了输出上限的规则：单次请求的输出有上限（流式和 SDK 调用 64K，非流式 REST 调用 32K），超出部分要靠 `continuation_token` 分多次请求接着生成，Google 把这叫「long decode」（长解码）。

本文依据 Google 官方的 [Gemini 4 Argon 新特性与迁移指南](https://ai.google.dev/gemini-api/docs/generate-content/latest-model)、[长解码文档](https://ai.google.dev/gemini-api/docs/generate-content/long-decode) 和 [模型页](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon)，适用于用 `generateContent` / `streamGenerateContent` 调用 Gemini 4 Argon 的场景。Gemini 4 Argon 于 2026 年 10 月 13 日正式发布，见 [Gemini API 更新日志](https://ai.google.dev/gemini-api/docs/changelog)。

## 一、先看 finishReason：按现象对照

排查第一步是打印响应里的 `finishReason`（Python SDK 里是 `candidates[0].finish_reason`）。下表整理自官方长解码文档的排错表和迁移清单：

| 现象 | 原因 | 改法 |
|---|---|---|
| 输出停在 64K 或 32K，`finishReason` 是 `CONTINUATION` | 模型还没写完，但没有人发起下一次续写请求 | 升级 SDK，或自己写续写循环 |
| 输出停在 64K 或 32K，`finishReason` 是 `MAX_TOKENS` | 没设 `max_output_tokens` 或设得太低 | 调到 65,536 以上 |
| `text` 为空，`finishReason` 是 `CONTINUATION` | 这一次请求的额度全用在思考上了，属于正常进度 | 带上 `continuationToken` 继续请求，答案在后面几次返回 |
| `text` 为空，`finishReason` 是 `MAX_TOKENS` | 全部额度都用在思考上了 | 调高 `max_output_tokens`，或调低 `thinking_level` |
| 400：「Continuation token has already used output tokens...」 | 续写时 `max_output_tokens` 没有高于已经用掉的 token 数 | 调高 `max_output_tokens` 后再续写 |
| 设 `thinking_level: "minimal"` 报错，或同时设了 `thinking_level` 和 `thinking_budget` 报错 | Argon 只支持 `low`、`medium`、`high`；两个参数只能二选一 | 只保留 `thinking_level` |
| 创建或使用显式缓存（`cachedContents` / `cached_content`）报错 | Argon 不支持显式缓存，只支持隐式缓存 | 删掉创建和传入显式缓存的代码 |
| 请求跑了 3 或 5 分钟就断开 | 客户端超时太短 | 把 HTTP 读取超时设成 20 分钟 |

## 二、回答被截断：确认你走的是哪种调用方式

官方文档写明：只改模型 ID 不会打开长解码。不做额外设置时，流式调用和通过 SDK 的调用最多输出 64K token，直接用 REST 的非流式调用最多 32K token。另外，思考 token 也算在 `max_output_tokens` 里，难题上模型会把更多额度花在思考上。

按调用方式分三种情况：

1. **用官方 Google GenAI SDK**：升级到 Python `google-genai` 2.30.1、JavaScript `@google/genai` 2.29.1 或更高（Go 1.74.0、Java 1.77.0、.NET 1.26.0、Kotlin 1.6.0）。新版本里 `automatic_continuation` 默认开启，只要把 `max_output_tokens` 设得大于单次上限，SDK 会自动续写并返回一个合并后的结果。旧版本不会自动续写，输出停在 64K。
2. **直接调 REST**：需要自己写续写循环，见第三节。
3. **走 OpenAI 兼容端点**：官方文档在「限制」一节写明，OpenAI 兼容端点不支持长解码，输出停在单次上限。需要超长输出就改用原生 `generateContent` 接口。

`max_output_tokens` 的设置，官方给的起点是：原来低于 32K 的，至少调到 32,768；长代码和智能体任务从 65,536 开始；难的数学、科研、证明类任务在 262,144 到「1,048,576 减去输入 token」之间测试。想省 token 应该调低 `thinking_level`，而不是压低 `max_output_tokens`，后者只会让回答更早被截断。

## 三、REST 续写循环怎么写

官方给的规则有五条：

1. 每次续写都发**同一个请求**：原样带上 `contents`、`system_instruction`、`tools`、`generationConfig`，`max_output_tokens` 也保持不变。
2. **不要**把上一次的部分输出拼进 `contents`，模型状态（包括思考）都在 `continuation_token` 里。
3. 只发**最新一次**拿到的 token，它已经包含之前所有进度。
4. `finishReason` 是 `CONTINUATION` 就继续，其它值就停。
5. 全部结束后，把各次返回的 parts 合成一个 model 回合，再放进对话历史。

第二次及以后的请求，就是在原请求体顶层加一个字段（与 `contents`、`generationConfig` 同级）：

```json
{
  "contents": [{"role": "user", "parts": [{"text": "原来的问题"}]}],
  "generationConfig": {
    "maxOutputTokens": 262144,
    "thinkingConfig": {"thinkingLevel": "high"}
  },
  "continuationToken": "上一次响应里的 continuationToken"
}
```

流式循环还要多一条规则：流式输出过了前 32,768 个 token 之后，每 5,000 个 token 会带一个检查点 token。收到带 token 的分片时，把之前暂存的分片确认下来并保存这个 token；如果连接中途断了，丢掉未确认的分片，从最后一个 token 接着请求；在第一个检查点之前就断开的，重新发原始请求。

## 四、报 400 的几种情况

- **续写时额度不够**：响应以 `MAX_TOKENS` 结束时仍然会带 `continuation_token`。想接着写，就带上这个 token 并把 `max_output_tokens` 调到高于已用量，否则返回 400 `INVALID_ARGUMENT`。也可以不带 token、调高额度后从头再来，但两次都要计费。
- **思考参数**：Argon 不支持 `minimal`；`thinking_budget` 单独使用仍然有效，会映射到最接近的档位并返回警告，但不能和 `thinking_level` 同时设置。建议统一改成 `thinking_level`，默认是 `medium`。
- **显式缓存**：迁移清单写明，显式缓存在 Argon 上不支持，调用会返回错误。删掉 `caches.create` 以及 `GenerateContentConfig` 里的 `cached_content`。隐式缓存默认开启，提示词至少 4,096 token 时才生效。
- **非流式 REST 设了超过 32,768 的上限**：长解码文档「默认输出上限」一节写着，非流式 REST 调用在没带 `continuation_token` 时把 `max_output_tokens` 设得大于 32,768 会返回 400；但同一文档的 REST 示例第一次请求也设了 262,144。两处说法不一致，遇到 400 时可以把它当作一个排查项，以实际返回的错误信息为准。

另外两项需要处理：迁移清单要求从请求里删除 `temperature`、`top_p`、`top_k`、`candidate_count`，其中采样参数传了会被忽略，排错表也列出它们会返回警告；多轮对话和函数调用时要把完整历史（包括思维签名 thought signatures）原样传回。

## 五、token 统计和计费要注意什么

长解码的每一次续写，都会把原始提示词加上已经生成的内容再作为输入发给模型，所以 `prompt_token_count`、`total_token_count` 是各次请求的累加，比实际上下文大得多。官方的处理建议：

- 用 SDK 自动续写时，提示词大小看 `initial_prompt_token_count`；用 REST 或关闭自动续写时，看第一次响应的 `promptTokenCount`。
- 如果你的智能体框架按 token 数决定什么时候压缩上下文，不要用累加后的 `prompt_token_count`，否则会过早压缩。只用一次请求就结束的短测试里两个值相同，所以容易漏测。
- 每次续写都要计费，只包含思考内容的那几次也算。重复的输入部分会被隐式缓存打折，但缓存 15～20 分钟不用就会过期。

## 六、改完怎么验证

1. 先发一个短问题，`thinking_level` 设 `low`，确认返回 200、`finishReason` 是 `STOP`，说明模型名和参数没问题。
2. 再发一个需要长输出的问题，把 `max_output_tokens` 设成 131,072 左右。用 SDK 自动续写时，看最终返回的 `finish_reason` 是否为 `STOP`、文本是否完整；用 REST 循环时，记录每次响应的 `finishReason`，输出超过单次上限时应当是若干次 `CONTINUATION`，最后以 `STOP` 结束（额度用完则是 `MAX_TOKENS`）。
3. 用 REST 时检查自己拼接的文本，排除 `thought` 为 true 的思考部分。

通过 OpenLux 调用时，原生 Gemini 接口的 Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/gemini-4-argon:generateContent`，Key 放在 `x-goog-api-key` 请求头里，Key 在控制台「令牌」页创建。OpenLux 价格接口当前在售的 `gemini-4-argon` 同时标注了 gemini 和 openai 两种接口；按官方说明，需要长解码时应走 gemini 原生接口。中转对 `continuationToken` 的透传本文没有实测，续写不生效时以响应里的 `finishReason` 和错误信息为准排查。

需要一个同时支持 Gemini 原生接口和 OpenAI 兼容接口的地址来测试 gemini-4-argon，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-4-argon-output-truncated-continuation-token-fix&utm_content=footer)。

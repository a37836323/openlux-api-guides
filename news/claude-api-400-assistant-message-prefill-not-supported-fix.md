---
layout: default
title: "Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法"
description: "Claude API 报 400「This model does not support assistant message prefill. The conversation must end with a user message.」的原因与改法：Claude 4.6 及之后模型不支持最后一条 assistant 预填充，按用途改成结构化输出 output_config.format、user 消息续写、system 提示去开场白，以及经中转调用时的注意事项。"
permalink: /news/claude-api-400-assistant-message-prefill-not-supported-fix/
date: 2026-11-19
---

> 更新日期：2026-11-19 · 一手来源：[Claude 官方文档](https://platform.claude.com/docs/en/api/errors)

# Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法

调用 Claude API 返回 400 `invalid_request_error`，报错信息是 `This model does not support assistant message prefill. The conversation must end with a user message.`，意思很明确：**请求里 `messages` 的最后一条是 `assistant` 消息（也就是“预填充”），而你调用的模型不再支持预填充**。解决办法是让对话以 `user` 消息结尾，再按你当初用预填充的目的，换成官方推荐的替代做法。

按 [Claude 官方错误文档](https://platform.claude.com/docs/en/api/errors#common-validation-errors)，Claude 4.6 及之后的模型和 Claude Mythos Preview 都不支持预填充 assistant 消息，带预填充的请求会返回上面这条 400。[官方提示词最佳实践](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#migrating-away-from-prefilled-responses)还补充了两点：更早的模型仍然支持预填充；对话中间出现 assistant 消息不受影响，限制的只是**最后一条**。

本文适用于直接调用 Claude Messages API，或经 Anthropic 兼容中转调用 Claude 的读者；模型名单以撰文时（2026-11-19）的官方文档为准。

## 先确认是不是这个问题

| 你看到的情况 | 判断 |
|---|---|
| 报错原文含 `does not support assistant message prefill` | 就是本文的问题，按下文改 |
| 同一段代码换成旧模型（Claude 4.5 及更早）能跑，换成新模型就 400 | 大概率是预填充，打印请求体看最后一条的 `role` |
| 报错是 `"thinking.type.enabled" is not supported`、`tool_choice ... not supported` 等 | 是别的 400，见官方错误文档的「Common validation errors」，不是预填充问题 |
| 报错是 `Extra inputs are not permitted` | 是请求里有接口不认识的字段，不是预填充问题 |

最直接的检查方法：把实际发出去的请求体打印出来，看 `messages` 数组最后一个元素。只要它的 `role` 是 `assistant`，在新模型上就会触发这条 400。

## 哪些模型不支持预填充

官方说法是从 Claude 4.6 这一代开始取消预填充。把撰文时 [OpenLux 价格接口](https://www.openlux.ai/api/pricing_new)在售的 Claude 模型按这条规则对一下：

| 模型 ID | 最后一条用 assistant 预填充 |
|---|---|
| `claude-opus-4-6`、`claude-sonnet-4-6`、`claude-opus-4-7`、`claude-opus-4-8` | 不支持，返回 400 |
| `claude-opus-5`、`claude-sonnet-5`、`claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5` | 不支持，返回 400 |
| `claude-fable-5`、`claude-fable-5-1`、`claude-fable-5-2` | 不支持，返回 400 |
| `claude-opus-4-5-20251101`、`claude-sonnet-4-5-20250929`、`claude-haiku-4-5-20251001` | 仍支持（官方：earlier models continue to support prefills） |

也就是说，**升级模型时最容易撞上这条报错**：老代码在 4.5 上一直正常，换成 4.6 及之后的模型就 400。退回旧模型能临时恢复，但长期还是按下面的方法把预填充去掉。在售列表会变化，以价格接口为准。

## 按用途改写：官方给的四种替代做法

官方最佳实践把预填充的常见用途分成几类，并逐一给了迁移方法：

| 原来用预填充做什么 | 原来的写法举例 | 官方建议的替代做法 |
|---|---|---|
| 强制输出 JSON / YAML、做分类 | 最后一条 assistant 写 `{` | 用[结构化输出](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)约束格式；分类任务用带 `enum` 字段的工具，或结构化输出 |
| 去掉开场白 | 最后一条 assistant 写 `Here is the requested summary:` | 在 system 提示里直接要求“不要开场白、直接回答”；或让模型把结果写在 XML 标签里、改用结构化输出或工具调用；偶尔漏出的开场白在后处理里删掉 |
| 接着上一次被打断的回答继续写 | 把半截回答作为最后一条 assistant 消息再发一次 | 把续写要求放进 user 消息，并带上被打断回答的结尾；如果是错误处理且对体验没影响，直接重试 |
| 绕开不必要的拒答 | 用 assistant 开头引导模型 | 官方认为新模型拒答更恰当，在 user 消息里把要求写清楚即可 |

另外一类是长对话里用 assistant 预填充“补提醒、补上下文”，官方建议改成写进 user 消息，复杂的智能体系统可以通过工具或上下文压缩来补充上下文。

## 改法一：要 JSON 输出，换成 output_config.format

以前常见的写法是让最后一条 assistant 消息以 `{` 开头，逼模型输出 JSON。现在改成在请求里加 `output_config.format`，类型为 `json_schema`，并让对话以 user 消息结尾。下面是按官方结构化输出文档整理的最小写法（Python SDK）：

```python
response = client.messages.create(
    model="claude-opus-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "从这段文字里提取姓名和邮箱：..."}],
    output_config={
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name", "email"],
                "additionalProperties": False,
            },
        }
    },
)
```

官方文档说明，返回的 JSON 在响应的 text 内容块里；用 Python SDK 的 `client.messages.parse()` 传 Pydantic 模型，SDK 会帮你生成 schema 并返回解析好的 `parsed_output`。

使用时注意官方列出的限制：对象必须写 `additionalProperties: false`；不支持递归 schema、`oneOf`（改用 `anyOf`）、`minimum`/`maximum` 这类数值约束、`minLength`/`maxLength` 这类字符串约束，用了不支持的特性也会返回 400；同一个 schema 第一次使用时会多一点延迟。结构化输出的支持模型名单以官方文档为准，上表里 4.5 及之后的在售模型都在名单内。

如果你需要的是“工具参数一定符合 schema”，官方的做法是给工具定义加 `strict: true`（严格工具调用），和结构化输出可以一起用。

## 改法二：续写被截断的回答，把要求放进 user 消息

很多代码在回答被截断（`stop_reason` 为 `max_tokens`）后，会把半截回答作为最后一条 assistant 消息再发一次，让模型“接着写”。在新模型上这正是预填充，会直接 400。

官方建议的改法是：保留历史里的那条 assistant 回答，**在它后面再追加一条 user 消息**，内容类似“你上一次的回答被打断了，结尾是 `……（贴上结尾一段）`，请从这里接着写”。这样对话以 user 消息结尾，不再触发预填充检查。

如果截断是因为 `max_tokens` 设得太小，更根本的办法是调大上限或改用流式，可参考[Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)。

同理，自己写的聊天界面如果有“继续生成”按钮，并且实现方式是把半截回答当成最后一条 assistant 消息发出去，在新模型上也会报这条 400，要按上面的方式改。

## 改法三：去开场白、控格式，改写 system 提示

用预填充 `Here is the summary:` 之类去掉开场白的，官方建议直接在 system 提示里写明要求，例如“直接回答，不要用‘以下是……’‘根据……’这类开头”。也可以要求模型把正文放进固定的 XML 标签（如 `<summary>…</summary>`），程序只取标签里的内容；偶尔仍有开场白，就在后处理里去掉。

## 经中转调用时要注意什么

预填充限制来自模型本身，经中转调用也一样：只要发给 Claude 新模型的请求最后一条是 assistant，就会收到这条 400，排查方法相同。

- 经 Anthropic 兼容地址调用时，Base URL 填 `https://api.openlux.ai`（不带 `/v1`，SDK 会自己拼 `/v1/messages`），Key 在 OpenLux 控制台「令牌」页创建。
- `output_config` 这类较新的字段能否透传，取决于中转服务；如果加上后报 `Extra inputs are not permitted`，那是字段不被接受，不是预填充问题，可参考[Claude Code 走中转报 400「Extra inputs are not permitted」的排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/)。

## 怎样算改好

1. 打印实际请求体，`messages` 最后一条的 `role` 是 `user`；
2. 同一个请求发给原来报错的模型，返回 200，不再出现 `does not support assistant message prefill`；
3. 用结构化输出的，响应 text 块里的内容能被 `json.loads` 解析，字段与 schema 一致；用续写方案的，拼接后的回答前后能接上。

报其他错误时，可以用 `curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"` 先确认地址和 Key：能列出模型说明两者都对，返回 401 说明 Key 错了或没带上。

## 参考资料

- Claude 文档：[API errors · Common validation errors · Prefill not supported](https://platform.claude.com/docs/en/api/errors#common-validation-errors)（报错原文、受影响模型）
- Claude 文档：[Prompting best practices · Migrating away from prefilled responses](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#migrating-away-from-prefilled-responses)（各类用途的替代做法）
- Claude 文档：[Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)（`output_config.format`、`strict: true`、schema 限制、支持模型）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-400-assistant-message-prefill-not-supported-fix&utm_content=footer)，在「令牌」页创建 Key，用 Anthropic 兼容地址调用 Claude。

## 同专题文章

- [Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？](https://a37836323.github.io/openlux-api-guides/news/claude-external-key-webhook-events/)
- [Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-streaming-required-10-minutes-max-tokens-fix/)
- [Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-image-400-size-dimension-limit-fix/)
- [Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？](https://a37836323.github.io/openlux-api-guides/news/claude-api-sampling-parameters-text-watermark/)
- [Claude API 报 400「thinking blocks cannot be modified」或「Invalid signature in thinking block」怎么办：原样回传思考块、redacted_thinking 与改了历史逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-thinking-blocks-cannot-be-modified-fix/)
- [Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Claude API 报 400「\"thinking.type.enabled\" is not supported for this model」或「adaptive thinking is not supported on this model」怎么办：按模型选 adaptive 还是 enabled，budget_tokens 换成 effort"
description: "Claude API 报 400「\"thinking.type.enabled\" is not supported for this model」或「adaptive thinking is not supported on this model」时，按官方对照表判断模型支持 adaptive 还是 extended 思考，把 budget_tokens 改成 output_config.effort，或在旧模型上保留 enabled，并处理 disabled、between_tools 相近报错。"
permalink: /news/claude-api-400-thinking-type-enabled-not-supported-fix/
date: 2026-11-28
---

> 更新日期：2026-11-28 · 一手来源：[Anthropic 官方文档 Troubleshooting thinking](https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting)

# Claude API 报 400「"thinking.type.enabled" is not supported for this model」或「adaptive thinking is not supported on this model」怎么办：按模型选 adaptive 还是 enabled，budget_tokens 换成 effort

这两个 400 是同一类问题：请求里 `thinking.type` 的写法和你调用的模型对不上。新模型（Claude 4.7 及以后，例如 Claude Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1）不再接受 `{"type": "enabled", "budget_tokens": N}`，要改成 `{"type": "adaptive"}`，思考深度用 `output_config.effort` 控制；旧模型（Claude 4.5 及更早，例如 Sonnet 4.5、Haiku 4.5、Opus 4.5）反过来不认 `adaptive`，只能继续用 `enabled` + `budget_tokens`。

本文依据 Anthropic 官方的 [Troubleshooting thinking](https://platform.claude.com/docs/en/build-with-claude/thinking-troubleshooting)、[Claude API errors](https://platform.claude.com/docs/en/api/errors)、[Extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) 和 [Effort](https://platform.claude.com/docs/en/build-with-claude/effort) 文档整理，适用于调用 Messages API（`/v1/messages`）的场景；通过网关调用时，以网关返回的报错正文对照下表。最常见的触发方式是：代码里写死了一套 `thinking` 参数，然后只改了模型名。

## 先看报错原文，判断是哪个方向

| 报错原文（400 invalid_request_error） | 说明 | 改法 |
|---|---|---|
| `"thinking.type.enabled" is not supported for this model. Use "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.` | 模型不支持手动预算的扩展思考（extended thinking） | 去掉 `budget_tokens`，改发 `thinking: {"type": "adaptive"}`，用 `output_config.effort` 调深浅 |
| `adaptive thinking is not supported on this model` | 模型只支持扩展思考 | 改发 `thinking: {"type": "enabled", "budget_tokens": N}` |
| `"thinking.type.disabled" is not supported for this model. ...` | 该模型思考始终开启，不能关 | 不传 `thinking` 字段；只想不显示思考内容就用 `display: "omitted"` |
| `"thinking.type.between_tools" is not supported for this model.` | 只有 Claude Sonnet 5.5 接受 `between_tools` | 其他模型不要发这个值 |

前两行是本文要解决的主问题，后两行是改参数时常顺带碰到的相近报错，下文也给出处理办法。

## 每个模型该发哪种 thinking：官方对照表摘录

官方排错页给了一张按模型列出的表，下面摘出常用的几行（「400 拒绝」那一列的值发过去就会报错，没列出的值都能接受）：

| 模型 | 支持的思考方式 | 默认 | 发了会 400 的值 |
|---|---|---|---|
| Claude Fable 5.1 / Fable 5 | 只支持 adaptive | 始终开启 | `enabled`、`disabled` |
| Claude Opus 5.5 | 只支持 adaptive | 始终开启 | `enabled`、`disabled` |
| Claude Opus 5 | 只支持 adaptive | 开 | `enabled`（`disabled` 只能在 effort 为 high 及以下时用） |
| Claude Sonnet 5.5 | adaptive、between_tools | 开 | `enabled`、`disabled` |
| Claude Sonnet 5 | 只支持 adaptive | 开 | `enabled` |
| Claude Haiku 5.5 | 只支持 adaptive | 开 | `enabled`（`disabled` 只能在 effort 为 high 及以下时用） |
| Claude Opus 4.8 / 4.7 | 只支持 adaptive | 关 | `enabled` |
| Claude Opus 4.6 / Sonnet 4.6 | adaptive、extended（已弃用） | 关 | 无 |
| Claude Opus 4.5 / Sonnet 4.5 / Haiku 4.5 | 只支持 extended | 关 | `adaptive` |

规律很简单：**4.7 及以后的模型用 adaptive，4.5 及以前的模型用 enabled，4.6 两种都行但 enabled 已弃用。** 完整表格（含 Mythos 系列）以官方页面为准。

## 新模型报 "thinking.type.enabled"：改成 adaptive + effort

官方迁移说明的做法是三步：删掉 `budget_tokens`，把 `thinking.type` 改成 `adaptive`，思考深度改用 `output_config.effort` 控制。官方示例中，原来的请求：

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 16000,
  "thinking": {"type": "enabled", "budget_tokens": 10000}
}
```

改成：

```json
{
  "model": "claude-sonnet-4-6",
  "max_tokens": 16000,
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "high"}
}
```

改的时候注意这几点：

- **effort 不是 token 数。** 可选值是 `low`、`medium`、`high`、`xhigh`、`max`，官方没有给出「budget_tokens 多少对应哪一档」的换算，要在自己的样本上试。并不是每个模型都支持全部五档，`xhigh`、`max` 支持哪些模型见 Effort 文档的表格。
- **默认值不一样。** Claude Opus 5.5 和 Haiku 5.5 默认 `medium`，其他支持 effort 的模型默认 `high`；把 effort 设成默认值和不传效果相同。
- **行为会变，不只是语法变。** 固定预算时模型每轮都先思考；adaptive 由模型自己决定想不想、想多少，effort 低时简单问题可能完全不思考。
- **可以去掉 `interleaved-thinking-2025-05-14` 请求头**，adaptive 会自动在工具调用之间思考。
- **第一次切换会让提示缓存失效。** 思考配置属于缓存前缀，切换模式后的第一个请求缓存读不中是正常的；之后在同一对话里保持思考配置和 effort 不变。
- 不要把 `adaptive` 填进 `effort`：`adaptive` 是思考模式，不是 effort 档位。

## 旧模型报 "adaptive thinking is not supported"：保留 enabled + budget_tokens

如果你调用的是 Claude 4.5 及更早的模型，官方的说法是：这些模型只支持扩展思考，在换到支持 adaptive 的模型之前，继续用 `budget_tokens`。写法要满足官方的预算规则：

1. `budget_tokens` 最少 1,024，小于这个值会被拒绝；
2. `budget_tokens` 必须小于 `max_tokens`，因为思考 token 也算在 `max_tokens` 里（例外是手动模式下的交错思考，预算可以超过 `max_tokens`）；
3. 因为预算必须小于 `max_tokens`，扩展思考不能和 `max_tokens: 0` 的缓存预热一起用。

另外，官方文档写明 Claude Opus 4.5 和 Sonnet 4.5 在 Anthropic 自营平台上已弃用。还在用它们的话，与其两套参数来回切，不如按官方弃用页的推荐换到新模型，一次性改成 adaptive。

## 相近的两个报错：disabled 和 between_tools

很多人改完 `enabled` 又想「把思考关掉省钱」，于是发 `thinking: {"type": "disabled"}`，在 Fable 5.1、Opus 5.5 等「始终开启」的模型上会再报 400。官方给的办法：

- 不传 `thinking` 字段，这些模型不配置也会思考；想省 token 就调低 effort；
- 只是不想在响应里看到思考文字，用 `display: "omitted"`，不要关思考；
- Claude Sonnet 5.5 要关掉回答前的思考，发 `thinking: {"type": "between_tools"}`，而且只能在 effort 为 `high` 及以下时用；`xhigh`、`max` 档要改回 adaptive；
- Claude Opus 5 和 Haiku 5.5 接受 `disabled`，但同样只能配 `high` 及以下的 effort。

## 改完怎么验证，哪些现象是正常的

1. **请求返回 200 不再报 400**，就说明 `thinking` 写法和模型对上了。建议把「模型 → thinking 写法」做成配置表，换模型时一起改，别只改模型名。
2. **adaptive 下有的轮次没有 thinking 块**：官方说明这是正常的，模型判断问题简单就直接回答；想让它多想就调高 effort。
3. **有 thinking 块但 `thinking` 字段是空字符串**：部分模型的 `display` 默认是 `omitted`，只返回签名；要看摘要就设 `display: "summarized"`。这种块仍然完整，多轮对话时要原样传回。
4. **`stop_reason` 是 `max_tokens`、正文被截断**：思考 token 算在 `max_tokens` 里，调大 `max_tokens` 或调低 effort。
5. **改了 effort 思考深度没变化**：effort 只在 adaptive 模式下是主要的思考控制；只支持扩展思考的模型要调 `budget_tokens`。

## 小结：一张表记住怎么写

| 你用的模型 | thinking 怎么写 | 控制深浅 |
|---|---|---|
| 4.7 及以后（Opus 5.5、Sonnet 5.5、Haiku 5.5、Fable 5.1 等） | `{"type": "adaptive"}` 或不传 | `output_config.effort` |
| 4.6（Opus 4.6、Sonnet 4.6） | 推荐 `adaptive`，`enabled` 仍可用但已弃用 | effort（或 budget_tokens） |
| 4.5 及以前（Opus 4.5、Sonnet 4.5、Haiku 4.5） | `{"type": "enabled", "budget_tokens": N}` | budget_tokens（Opus 4.5 还支持 effort） |

想用同一个 Key 在多个 Claude 模型之间切换调试，可以 [注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-400-thinking-type-enabled-not-supported-fix&utm_content=footer)。

## 同专题文章

- [Claude API 在浏览器里直接调用报 CORS 错误或 401「CORS requests are not allowed for this Organization」怎么办：dangerouslyAllowBrowser、请求头与改走后端](https://a37836323.github.io/openlux-api-guides/news/claude-api-browser-cors-requests-not-allowed-fix/)
- [Claude 桌面版怎么接入 Claude 中转 API：开发者模式、Configure Third-Party Inference、网关地址、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-desktop-relay-api-third-party-inference-gateway-setup/)
- [Claude Agent SDK 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、env 选项与模型设置（Python / TypeScript）](https://a37836323.github.io/openlux-api-guides/news/claude-agent-sdk-relay-api-base-url-env-setup/)
- [Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？](https://a37836323.github.io/openlux-api-guides/news/claude-external-key-webhook-events/)
- [Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-streaming-required-10-minutes-max-tokens-fix/)
- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

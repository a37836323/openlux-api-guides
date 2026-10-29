---
layout: default
title: "换成 Claude Opus 5.5 后报 400 怎么改：thinking 关不掉、tool_choice 不能强制，按原来的模型逐项排查"
description: "换成 claude-opus-5-5 后报 400：按官方迁移指南对照 thinking.type.disabled/enabled、tool_choice any/tool、computer_20251124、采样参数与预填充的报错原文和改法，并按原模型（Opus 5、4.8、4.7、4.6、Sonnet 5）列出要改的地方和验证方法。"
permalink: /news/claude-opus-5-5-migration-400-thinking-tool-choice-fix/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[Anthropic Claude Opus 5.5 migration guide](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide)

# 换成 Claude Opus 5.5 后报 400 怎么改：thinking 关不掉、tool_choice 不能强制，按原来的模型逐项排查

结论先说：把模型 ID 换成 `claude-opus-5-5` 之后，原来能跑的请求返回 400，多数是请求里还带着 Opus 5.5 不接受的写法。按 Anthropic 官方 [Claude Opus 5.5 迁移指南](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide)，最常见的是四类：`thinking` 设成 `disabled` 或 `enabled`（手动思考预算）、`tool_choice` 用了 `any` 或 `tool`、传了 `temperature` / `top_p` / `top_k` 或助手预填充、在 Claude API 上声明了 `computer_20251124` 工具。

本文只讲 Messages API 代码。官方说明，用 Claude Managed Agents 的项目除了改模型名，不需要其他改动。下面先用报错原文定位，再按你原来用的模型（Opus 5、Opus 4.8、Opus 4.7、Opus 4.6 及更早、Sonnet 5）列出要改的地方，最后给验证方法。

## 一、先按报错原文定位是哪一类

下表的报错原文都出自官方迁移指南，可以直接拿日志里的文本对照。

| 报错原文 | 触发它的写法 | 改法 |
|---|---|---|
| `"thinking.type.disabled" is not supported for this model.` | `thinking: {"type": "disabled"}` | 删掉 `thinking` 字段，用 `output_config.effort` 调低思考量 |
| `"thinking.type.enabled" is not supported for this model.` | `thinking: {"type": "enabled", "budget_tokens": N}` | 删掉预算，改用 effort |
| `tool_choice: type "tool" and "any" are not supported for this model.` | `tool_choice` 为 `{"type": "any"}` 或 `{"type": "tool", "name": "..."}` | 改成 `auto`，配合严格工具调用或结构化输出 |
| `'claude-opus-5-5' does not support tool types: computer_20251124.` | 在 Claude API 或 Claude Models on Google Cloud（Google managed）上声明 `computer_20251124` | 改用 `computer_toolset_20260801` |
| 400（官方未给报错原文） | 传了 `temperature`、`top_p`、`top_k` | 删除，改用提示词引导 |
| 400（官方未给报错原文） | `messages` 最后一轮是 assistant 预填充 | 改用结构化输出或 system 提示 |

官方在「每个请求都必须满足」一节还写明：不发 `thinking` 字段，和发 `thinking: {"type": "adaptive"}` 是等价的；`tool_choice` 只接受 `{"type": "auto"}`（默认）和 `{"type": "none"}`。

## 二、thinking 报 400：删掉 thinking 字段，用 effort 控制思考量

Opus 5.5 的自适应思考始终开启，关不掉，也不接受手动预算。思考深度只能通过 effort 参数控制，五档 `low`、`medium`、`high`、`xhigh`、`max` 都支持，默认 `medium`。原来为了省 token 而关掉思考的请求，官方建议改成较低的 effort 档位。

官方给的前后对照（节选，改写为 JSON）：

```json
{
  "model": "claude-opus-5-5",
  "max_tokens": 16000,
  "output_config": {"effort": "low"},
  "messages": [{"role": "user", "content": "..."}]
}
```

原来的写法是 `"model": "claude-opus-5"` 加 `"thinking": {"type": "disabled"}`，Opus 5 接受，Opus 5.5 返回 400。

两点要同时改：

- **显式设置 effort**：Opus 5 和 Opus 4.7 默认 `high`，Opus 5.5 默认 `medium`。不写 effort 的请求在 Opus 5.5 上按 `medium` 跑，质量和耗时都可能和原来不同。官方建议在自己的评测集上重新试几个档位，不要直接沿用旧设置。
- **重新评估 `max_tokens`**：`max_tokens` 同时覆盖思考和正文，思考 token 按输出 token 计费，即使思考文本没有返回给你。官方建议在 `xhigh` 或 `max` 档位下从 64k 起步。

## 三、tool_choice 报 400：改成 auto，加严格工具调用

Opus 5.5 不支持强制工具调用，`tool_choice` 的 `any` 和 `tool` 都会返回 400。官方特别说明，token 计数接口同样会拒绝这两种写法。

官方给的改法：

1. 把 `tool_choice` 改成 `{"type": "auto"}`。
2. 在工具定义上加 `"strict": true`（严格工具调用），让模型给出的工具输入符合 `input_schema`；也可以改用结构化输出。
3. 在提示词里写明什么时候该用这个工具。官方示例把用户消息写成「What's the weather in Paris? Use the get_weather tool.」。

加 `strict` 之前先检查 schema：严格工具调用只支持 JSON Schema 的一个子集，schema 里每个 object 都必须写 `additionalProperties: false`，具体限制见官方 JSON Schema limitations 一节。

`auto` 表示由模型决定这一轮是否调用工具，所以下游代码要能处理「这一轮没有 `tool_use` 块」的情况。

## 四、computer_20251124 报 400：按平台处理

计算机使用工具的规则和平台有关：

| 平台 | Opus 5.5 上该怎么声明 |
|---|---|
| Claude API | `computer_toolset_20260801`，不需要 beta 头；`computer_20251124` 返回 400 |
| Claude Models on Google Cloud（Google managed） | 同上 |
| Amazon Bedrock | 继续用 `computer_20251124` |
| 其他平台 | 看官方计算机使用工具文档的平台支持表 |

换成 toolset 时，官方要求去掉 beta 头，条目里不再写 `name` 和显示尺寸。智能体循环也要跟着改：动作名改为读 `tool_use` 块的 `name`（不再是 `input.action`），一轮里可能有多个这样的块，每个结果都要回传 `toolset_name`。

## 五、按你原来用的模型，对照要改的地方

官方迁移清单是累加的：从上往下做，做到写着你当前模型的那一组为止，前面每组都适用。

| 原来的模型 | 在前一行基础上还要做的事 |
|---|---|
| Opus 5 | 改模型 ID；删 `thinking` 的 `disabled` / `enabled`；`tool_choice` 改 `auto`；按第四节处理 `computer_20251124`；显式设置 effort；按 `type` 读取内容块 |
| Opus 4.8 | 原来不写 `thinking` 的请求在 Opus 5.5 上也会思考，要复查 `max_tokens` 和成本；Opus 5.5 不支持 Priority Tier；可缓存的最短提示降到 512 token |
| Opus 4.7 | effort 各档位重新校准，要重新试；删掉上下文窗口 beta 头（1M 上下文已是默认）；想用 fast mode 时在请求里设 `speed: "fast"`，不需要 beta 头 |
| Opus 4.6 及更早 | 删 `temperature`、`top_p`、`top_k`；`budget_tokens` 改成 adaptive 加 effort；思考文本默认不返回；新分词器处理同样文本约用 1 到 1.35 倍 token |
| Opus 4.5 及更早 | 删掉助手预填充（Opus 4.6 起就返回 400）；`output_format` 改成 `output_config.format`；删掉 `effort-2025-11-24`、`interleaved-thinking-2025-05-14`、`fine-grained-tool-streaming-2025-05-14` 等 beta 头；从 `client.beta.messages.create()` 改到 `client.messages.create()` |
| Sonnet 5 | 做第一行（Opus 5）全部；手动思考预算、采样参数、预填充在 Sonnet 5 上本来就返回 400，不用再改 |

## 六、不报错但会悄悄出问题的地方

| 变化 | 表现 | 官方建议 |
|---|---|---|
| 每个回复都可能以 `thinking` 块开头 | 读 `content[0].text` 或把第一个 `content_block_start` 当文本的代码出错 | 按块的 `type` 字段取 `text` 块 |
| 工具循环里思考块要原样回传 | 编辑、重排或漏传思考块会返回 400 | 把 assistant 消息按收到的样子回传，`thinking` 为空的块也要传 |
| `thinking.display` 默认 `omitted` | 思考块里 `thinking` 字段为空，只有 `signature`；向用户流式展示思考的界面，开头会长时间没有输出 | 需要可读摘要时设 `display: "summarized"` |
| 工具调用之间的说明文字改放在 `thinking` 块 | Opus 5 上它们是 `text` 块，界面上的进度提示会消失 | 设 `display` 为 `"summarized"`，或用 beta 的 `"updates"` |
| 拒答类别变多 | 可能返回 `stop_reason: "refusal"`，`stop_details.category` 出现 `"bio"` 等新值 | 处理拒答停止原因，按需配置回退 |

如果你的程序会把同一段对话在 Opus 5.5 和其他模型之间路由，还要注意：官方说明 Opus 5.5 的思考块在 Claude API 上只有 Claude Fable 5.1 和 Claude Mythos 5.1 能读取，切到其他模型时这些轮次会在没有思考块的情况下运行。

## 七、怎样算改好了

1. **最小请求通过**：用 `claude-opus-5-5` 发一条只含用户消息、带 `output_config.effort`、不带 `thinking` 字段的请求，返回 200，按 `type` 能读到 `text` 块。
2. **带工具的请求通过**：`tool_choice` 为 `auto`、工具加了 `strict` 后，该调用时模型调用了工具，`input` 能被标准 JSON 解析器正常解析。
3. **token 计数接口通过**：把改好的请求体发到 `/v1/messages/count_tokens` 预检一遍，`tool_choice` 的限制在这里同样生效。
4. **多轮工具循环通过**：连续几轮回传工具结果，不再出现思考块相关的 400。
5. **日志里不再出现第一节表格里的报错原文**。

## 八、通过 OpenLux 调用时

截至 2026 年 10 月 29 日，OpenLux 价格接口的在售列表里有 `claude-opus-5-5`，端点类型包含 Anthropic Messages 和 OpenAI 兼容。用 Anthropic SDK 时，Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端会自己拼 `/v1/messages`），Key 在 OpenLux 控制台的令牌页创建，价格以官网价格页为准。本文的参数规则和报错原文出自 Anthropic 官方文档，适用于 Messages 格式的请求；经中转返回的错误包装格式可能不同，走 OpenAI 兼容端点时的参数对应关系本文没有核实，以实际响应为准。先用 `/v1/models` 确认列表里有 `claude-opus-5-5`，再按第七节逐项验证。

需要通过 OpenLux 调用 `claude-opus-5-5` 时，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-opus-5-5-migration-400-thinking-tool-choice-fix&utm_content=footer)。

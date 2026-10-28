---
layout: default
title: "Claude Sonnet 4.5 将于 11 月 30 日退役：换成 Sonnet 5.5 后报 400 怎么改（budget_tokens、temperature、预填充、tool_choice）"
description: "Anthropic 已弃用 claude-sonnet-4-5-20250929，Claude API 上 2026-11-30 退役，推荐换成 claude-sonnet-5-5。按官方弃用页和 Sonnet 5.5 迁移指南，对照 budget_tokens、temperature、预填充、tool_choice、computer use 等 400 报错原文逐项改，并给出用量审计和验证步骤。"
permalink: /news/claude-sonnet-4-5-retirement-sonnet-5-5-migration-400-fix/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[Anthropic 模型弃用页与 Claude Sonnet 5.5 迁移指南](https://platform.claude.com/docs/en/about-claude/model-deprecations)

# Claude Sonnet 4.5 将于 11 月 30 日退役：换成 Sonnet 5.5 后报 400 怎么改（budget_tokens、temperature、预填充、tool_choice）

结论先说：Anthropic 在 2026 年 9 月 30 日宣布弃用 `claude-sonnet-4-5-20250929`，Claude API 上的退役日期是 **2026 年 11 月 30 日**，官方推荐的替代模型是 `claude-sonnet-5-5`。按 [Anthropic 模型弃用页](https://platform.claude.com/docs/en/about-claude/model-deprecations) 的说明，退役之后发往该模型的请求会失败，所以要在 11 月 30 日之前把模型 ID 换掉。

麻烦在于：只改模型 ID，原来能跑的 Sonnet 4.5 代码在 Sonnet 5.5 上很可能直接返回 400。官方 [Sonnet 5.5 迁移指南](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) 列出了从 Sonnet 4.5 出发要改的每一项，最常见的是四类：`thinking.budget_tokens`、`temperature` 等采样参数、助手预填充（prefill）、强制工具调用 `tool_choice`。下面按「先找到在用的地方 → 对照报错 → 逐项改 → 验证」的顺序排查。本文只讲 Messages API 代码；官方说明用 Claude Managed Agents 的项目只需改模型名。

## 一、官方时间线与受影响的平台

| 日期 | 事件 | 官方出处要点 |
|---|---|---|
| 2026-09-28 | 发布 Claude Sonnet 5.5（`claude-sonnet-5-5`） | 发布说明列出从 Sonnet 5 迁移的不兼容项 |
| 2026-09-30 | 宣布弃用 `claude-sonnet-4-5-20250929` | 推荐替代为 `claude-sonnet-5-5` |
| 2026-11-30 | Claude API 上退役 | 退役后请求失败 |

几个容易忽略的点，均出自弃用页：

- 弃用（Deprecated）的模型仍可调用，但官方提示它可能不如在役模型稳定；退役（Retired）后不可再用。
- 上面的日期适用于 Anthropic 自己运营的平台：Claude API、Claude Platform on AWS、Claude Models on Google Cloud（Anthropic managed）和 Microsoft Foundry。Amazon Bedrock 和 Claude Models on Google Cloud（Google managed）由合作方自定退役时间，要看各自的模型表。
- 官方承诺对公开发布的模型至少提前 60 天通知退役。

## 二、先找出还在调用 Sonnet 4.5 的地方

弃用页给了一个审计办法：

1. 打开 Claude Console 的 [Usage](https://platform.claude.com/usage) 页面。
2. 点击 **Export**。
3. 在下载的 CSV 里按 API Key 和模型查看用量，找出仍在调用 `claude-sonnet-4-5-20250929` 的 Key。

拿到 Key 列表后，再到对应项目里搜模型字符串。注意配置文件、环境变量和数据库里存的模型名也算。

## 三、换成 Sonnet 5.5 后的 400 报错对照表

以下每一行都出自官方迁移指南。报错原文照抄，方便你用日志里的文本直接搜索。

| 原来在 Sonnet 4.5 上的写法 | 在 Sonnet 5.5 上的结果 | 官方报错原文或说明 | 改法 |
|---|---|---|---|
| `thinking: {"type": "enabled", "budget_tokens": N}` | 400 | `"thinking.type.enabled" is not supported for this model. Use "thinking.type.adaptive" and "output_config.effort" to control thinking behavior.` | 删掉预算，改用 `adaptive` 加 `output_config.effort` |
| 传 `temperature`、`top_p`、`top_k` | 400 | 迁移指南要求删除这三个参数 | 删除，用提示词引导 |
| 最后一轮是 assistant 消息（预填充） | 400 | `This model does not support assistant message prefill. The conversation must end with a user message.` | 按用途改写，见第四节 |
| `tool_choice` 为 `any` 或 `tool` | 400（计 token 接口同样拒绝） | `tool_choice: type "tool" and "any" are not supported for this model.` | 改 `auto`，工具加 `strict: true` |
| `thinking: {"type": "disabled"}` | 400 | 提示改发 `{"type": "between_tools"}` | 用 `between_tools`，且 effort 不高于 `high` |
| 计算机使用工具 `computer_20250124` | 所有平台都不接受 | 迁移指南的计算机使用对照表 | Claude API 用 `computer_toolset_20260801`；Bedrock 用 `computer_20251124` |
| 不带 beta 头使用 `output_format` | 400 | `output_format` 已弃用 | 改成 `output_config.format` |
| 计算机/浏览器使用 toolset 搭配 `fine-grained-tool-streaming-2025-05-14` 头 | 400 | 该头与 toolset 同时出现会报错 | 去掉该头，在需要的工具上设 `eager_input_streaming: true` |

另外两条与 thinking 相关的 400 也写在迁移指南里：`between_tools` 在 `xhigh` 或 `max` effort 下会报错；`between_tools` 带上 `display`、`budget_tokens` 或 `block_binding` 字段也会报错。

## 四、逐项改法

### 1. 思考预算换成 effort

Sonnet 4.5 只能用 `budget_tokens` 开启思考，而且官方说明它没有 effort 参数。到 Sonnet 5.5 上要删掉预算，改成下面这样（官方示例节选）：

```json
{
  "model": "claude-sonnet-5-5",
  "max_tokens": 16000,
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "high"},
  "messages": [{"role": "user", "content": "..."}]
}
```

官方强调预算和 effort 之间没有固定换算关系，建议在两到三个 effort 档位上跑一遍自己的评测再定。Sonnet 5.5 有 `low`、`medium`、`high`、`xhigh`、`max` 五档，Claude API 上默认 `high`；迁移清单要求从 Sonnet 4.5 迁移时**显式设置** effort。官方建议：一般从 `high` 开始；智能体编码和多步工具调用，任务描述清楚的从 `medium` 起；聊天等对延迟敏感的场景从 `medium` 或 `low` 起。

### 2. 删掉采样参数

直接从请求里去掉 `temperature`、`top_p`、`top_k`。弃用页的参数表还补充了一点：API 版本 `2026-10-21` 已移除这三个参数，传了就返回 400；更早的 API 版本在 Claude 4.7 及之后的模型上，只要设为非默认值也会报错。

### 3. 预填充按用途改写

Sonnet 4.5 接受最后一轮是 assistant 的预填充，Sonnet 5.5 不接受。官方按用途给了替代做法：

- 想固定输出格式：用结构化输出，分类任务可用带枚举字段的工具。
- 想跳过开场白：在 system 提示里要求直接回答。
- 想减少不必要的拒绝：在用户消息里把要求写清楚，通常就够了。
- 想续写被打断的回复：把续写要求放进用户消息，例如说明上一次回复在哪里中断、请从那里继续。
- 想提醒上下文：放到用户这一轮里。

### 4. 强制工具调用改成 auto 加 strict

把 `tool_choice` 改成 `{"type": "auto"}`，并在工具定义上加 `"strict": true`，让工具输入符合 schema。官方提醒三件事：模型这时可以不调用工具，所以要在提示词里说明什么时候用它；strict 只支持 JSON Schema 的一个子集，每个 object 都要写 `additionalProperties: false`；一次请求最多 20 个 strict 工具，MCP、计算机使用、浏览器使用的 toolset 条目不接受 `strict`。

### 5. 计算机使用、beta 头与结构化输出

- 计算机使用：Sonnet 4.5 用的 `computer_20250124` 在 Sonnet 5.5 上任何平台都不接受。Claude API 和 Claude Models on Google Cloud（Google managed）改用 `computer_toolset_20260801`；Amazon Bedrock 改用 `computer_20251124`。
- 去掉 `interleaved-thinking-2025-05-14`，官方说明自适应思考会自动在工具调用之间思考。
- 去掉上下文窗口相关的 beta 头：Sonnet 5.5 不用 beta 头就有更大的上下文窗口和更高的输出上限，具体数值见官方模型页。
- `output_format` 改成 `output_config.format`。
- 工具调用的 `input` 用标准 JSON 解析器解析，官方说明转义方式可能和以前不同。

## 五、不报错但行为变了的地方

这些不会让请求失败，但会让程序悄悄出问题：

| 变化 | 影响 | 官方建议 |
|---|---|---|
| 不写 `thinking` 字段也会自适应思考 | 回复可能以 `thinking` 块开头，读 `content[0].text` 的代码会出错 | 按块的 `type` 读取；工具循环里把 `thinking` 块原样回传，空块也要传 |
| 思考文本默认不返回 | `thinking` 块里只有空字段和 `signature` | 需要展示思考摘要就设 `display: "summarized"` |
| `max_tokens` 同时覆盖思考和正文 | 原来的上限可能不够用，思考 token 按输出计费 | 重新评估 `max_tokens` 和成本 |
| 同样文本约多 30% token | 与 Sonnet 4.5 相比，计数和成本上升 | 用 token 计数接口重新计算 |
| 图片走高分辨率档 | 长边最高 2576 像素，单图最多 4784 个视觉 token；一张 2000×1500 的图约是原来的 2.5 倍 token | 重新估算图片预算 |
| 工具调用之间超过一两句的说明改放在 `thinking` 块 | 默认 `display` 下这些块是空的，界面上原本显示的中间说明消失 | 自适应思考下把 `display` 设为 `"summarized"`，或用 beta 的 `"updates"` |

如果想保持「先不思考、直接回答」的旧行为，按官方说法发送 `thinking: {"type": "between_tools"}`，并把 effort 控制在 `high` 或以下。还有一条要留意：对 2026 年 8 月 31 日（UTC）及之后创建的账号，修改过历史对话后再回传 Sonnet 5.5 的思考块会返回 400，官方建议对话只追加、不改写历史。

## 六、怎样算迁移完成

1. **最小请求通过**：用 `claude-sonnet-5-5` 发一条只含用户消息、带 `output_config.effort` 的请求，返回 200，`stop_reason` 正常，按 `type` 能读到 `text` 块。
2. **带工具的请求通过**：`tool_choice` 为 `auto`、工具标了 `strict` 后，模型在该调用时调用了工具，`input` 能被 JSON 解析器正常解析。
3. **计 token 接口通过**：官方说明 `tool_choice` 的限制在 token 计数接口上同样生效，用它预检一遍改好的请求体。
4. **日志里不再出现第三节表中的报错原文**。
5. **用量导出里不再有 Sonnet 4.5**：再按第二节导出一次 Usage CSV，确认各个 Key 都已经没有 `claude-sonnet-4-5-20250929` 的调用。

官方还说明，Sonnet 5.5 拒答的类别比 Sonnet 5 更多，拒答时返回 `stop_reason: "refusal"`；实时网络安全防护对从 Sonnet 4.5 迁移来的代码是新增的。迁移后要确认代码能处理这个停止原因。

## 七、通过 OpenLux 调用时

截至 2026 年 10 月 29 日，OpenLux 价格接口的在售列表里同时有 `claude-sonnet-4-5-20250929` 和 `claude-sonnet-5-5`，两者的端点类型都包含 Anthropic Messages。用 Anthropic SDK 时，Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端会自己拼 `/v1/messages`），Key 在 OpenLux 控制台的令牌页创建，价格以官网价格页为准。官方 11 月 30 日退役后，经 OpenLux 调用 Sonnet 4.5 是否还可用，以 OpenLux 的公告为准；本文的报错原文出自 Anthropic 官方文档，经中转返回的错误包装格式可能不同，以实际响应为准。建议趁现在按上面的清单把代码切到 `claude-sonnet-5-5`。

需要通过 OpenLux 调用 `claude-sonnet-5-5` 时，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-sonnet-4-5-retirement-sonnet-5-5-migration-400-fix&utm_content=footer)。

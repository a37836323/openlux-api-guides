---
layout: default
title: "Claude Haiku 4.5 换成 Haiku 5.5 后报 400：budget_tokens、temperature、预填充与思维块怎么改"
description: "从 Claude Haiku 4.5 换到 Haiku 5.5 后报 400 的排查：budget_tokens 改自适应思考与 effort、删除 temperature/top_p/top_k、替换 assistant 预填充、计算机使用工具换版本、思维块回传保持只追加，以及空回答、max_tokens 截断和 token 变多的处理。"
permalink: /news/claude-haiku-5-5-migration-400-errors-fix/
date: 2026-10-26
---

> 更新日期：2026-10-26 · 一手来源：[Anthropic 官方文档：Claude Haiku 5.5 迁移指南](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide)

# Claude Haiku 4.5 换成 Haiku 5.5 后报 400：budget_tokens、temperature、预填充与思维块怎么改

把 `model` 从 `claude-haiku-4-5` 改成 `claude-haiku-5-5` 之后，原来能跑的请求开始返回 400，或者没报错但拿到的回答是空的、被截断的。原因是 Claude Haiku 5.5（2026 年 10 月 7 日发布）不再接受 Haiku 4.5 时代的几种写法，而且默认开启了自适应思考。先说结论：

1. `thinking: {"type": "enabled", "budget_tokens": N}` 会返回 400，改成 `{"type": "adaptive"}`，用 `output_config.effort` 控制思考多少。
2. `temperature`、`top_p`、`top_k` 可能返回 400，按官方迁移指南直接删掉，改用提示词约束输出。
3. `messages` 最后一条是 assistant（预填充）会返回 400，即使关掉思考也一样，要改成以 user 轮结尾。
4. 计算机使用工具 `computer_20250124` 会返回 400，需要换成新的工具版本。
5. 回传思维块时，如果中途改过 `system`、`tools` 或之前的消息，可能返回 400，对话要保持只追加。

本文适用于直接调用 Messages API 的代码。官方说明：如果用的是 Claude Managed Agents，除了改模型名不需要别的改动。依据是 Anthropic 官方的 [Claude Haiku 5.5 迁移指南](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide)、[发版说明（2026-10-07 条目）](https://platform.claude.com/docs/en/release-notes/overview) 和 [Effort 文档](https://platform.claude.com/docs/en/build-with-claude/effort)。价格以官网价格页为准。

## 先对照报错，找到对应的改法

| 现象 | 原因 | 改法 |
|---|---|---|
| 400，请求里有 `budget_tokens` | Haiku 5.5 不支持手动设定思考预算 | `thinking` 改为 `{"type": "adaptive"}` 或不传，用 `effort` 调节 |
| 400，请求里有 `temperature` / `top_p` / `top_k` | Haiku 5.5 上这些采样参数可能返回 400 | 删掉这三个参数，用提示词约束 |
| 400，最后一条消息是 assistant | Haiku 5.5 不接受预填充，关掉思考也一样 | 以 user 轮结尾，按用途改写（见下文） |
| 400，tools 里有 `computer_20250124` | 旧版计算机使用工具不再接受 | 按平台换成 `computer_toolset_20260801` 或 `computer_20251124` |
| 400，多轮对话中途改过 system 或 tools | 思维块只在它之前的内容不变时有效 | 对话只追加，不改已发送的内容 |
| 400，`thinking` 为 `disabled` 且 effort 是 `xhigh` / `max` | 这两个级别不能关闭思考 | 改用自适应思考，或把 effort 降到 `high` 及以下 |
| 不报错，但读到的回答是空的 | 代码把第一个内容块当成答案，而第一个块是 `thinking` | 按 `type` 取 `text` 块 |
| `stop_reason` 是 `max_tokens`，没有正文 | 思考 token 也计入 `max_tokens` | 调大 `max_tokens` 或降低 effort |

## 第一步：确认模型 ID 填对了

各平台的模型 ID 不同。官方迁移指南给出的对应关系：

| 平台 | Claude Haiku 4.5 | Claude Haiku 5.5 |
|---|---|---|
| Claude API | `claude-haiku-4-5-20251001` 或 `claude-haiku-4-5` | `claude-haiku-5-5` |
| Amazon Bedrock | `anthropic.claude-haiku-4-5` | `anthropic.claude-haiku-5-5` |
| Claude Platform on AWS | `claude-haiku-4-5` | `claude-haiku-5-5` |
| Claude Models on Google Cloud（Google managed） | `claude-haiku-4-5@20251001` | `claude-haiku-5-5` |
| Microsoft Foundry | `claude-haiku-4-5` | `claude-haiku-5-5` |

`claude-haiku-5-5` 是固定 ID，没有日期后缀，也没有另外的别名，不要自己拼 `claude-haiku-5-5-2026xxxx` 之类的写法。

另外，如果组织在 Haiku 4.5 上购买了 Priority Tier，要单独规划容量：官方说明 Haiku 5.5 不支持 Priority Tier。

## budget_tokens 报 400：改用自适应思考和 effort

Haiku 4.5 用 `{"type": "enabled", "budget_tokens": N}` 开启扩展思考，这个写法在 Haiku 5.5 上会返回 400。官方给出的改法是把 `thinking` 换成自适应思考，再用 `output_config.effort` 控制思考深度：

```json
{
  "model": "claude-haiku-5-5",
  "max_tokens": 16000,
  "thinking": { "type": "adaptive" },
  "output_config": { "effort": "medium" },
  "messages": [{ "role": "user", "content": "..." }]
}
```

几个要点：

- Haiku 5.5 默认就开着自适应思考，不传 `thinking` 时回答也可能以 `thinking` 块开头。
- effort 有 `low`、`medium`、`high`、`xhigh`、`max` 五级，Haiku 5.5 的默认值是 `medium`，传 `medium` 和不传效果相同。
- 原来在 Haiku 4.5 上不开思考、或者只给很小预算来省 token 的，官方建议选更低的 effort。低 effort 下模型思考更少，简单请求可能完全不思考。官方对 Haiku 5.5 的建议是：大多数任务从 `medium` 开始，聊天、短工具任务和大批量简单请求用 `low`。
- 也可以发 `thinking: {"type": "disabled"}`，但只在 effort 为 `high` 及以下时可用；在 `xhigh` 或 `max` 下会返回 400。

## temperature、top_p、top_k 报 400：直接删掉

发版说明写明，在 Haiku 5.5 上 `temperature`、`top_p`、`top_k` 都可能返回 400。迁移指南的做法是不再传这三个参数，改用提示词引导模型行为。

排查时注意参数可能不在你的业务代码里：框架或网关的默认配置、封装好的客户端也可能自动带上 `temperature`。最直接的办法是打印最终发出的请求体，确认里面没有这三个字段。

## 末尾 assistant 预填充报 400：按用途改写

预填充是指把 `messages` 的最后一条写成 assistant 消息，让模型接着往下写。Haiku 4.5 在关闭思考时接受这种写法，Haiku 5.5 一律返回 400，关闭思考也不行。解决方法是让 `messages` 以 user 轮结尾，再按预填充原本的用途替换：

| 预填充原来的用途 | 官方建议的替代做法 |
|---|---|
| 固定输出格式（比如先写 `{` 逼模型输出 JSON） | 改用结构化输出；分类任务可以用带 enum 字段的工具 |
| 去掉开场白 | 在 system 提示里要求直接给答案 |
| 让模型续写被中断的回答 | 写进 user 消息，例如说明上一次回答在哪里中断、请从那里继续 |
| 提醒上下文 | 放进 user 轮 |

## computer_20250124 报 400：换成新的工具版本

Haiku 4.5 通过 `computer_20250124` 工具和 `computer-use-2025-01-24` beta 头使用计算机操作。Haiku 5.5 上：

- Claude API 和 Claude Models on Google Cloud（Google managed）：只支持 `computer_toolset_20260801` 工具集。去掉旧的 beta 头，把 tools 里的条目换成 `{"type": "computer_toolset_20260801"}`，并按官方说明调整代理循环：按每个 `tool_use` 块的 `name` 和 `toolset_name` 分派，而不是看 `input.action`；结果里回传 `toolset_name`。
- Amazon Bedrock：改用 `computer_20251124`，配合 `computer-use-2025-11-24` beta 头。

工具集默认开启缩放（zoom），如果你的环境没有实现，加上 `"configs": {"zoom": {"enabled": false} }`。如果请求里还带着 `fine-grained-tool-streaming-2025-05-14` beta 头，要删掉，它和工具集同时出现会返回 400。

## 多轮对话回传思维块报 400：保持对话只追加

Haiku 5.5 的思维块只在它之前发送的内容都没变时有效。如果在同一个对话里改了 `system`、`tools` 或之前的 `messages`，又把思维块回传回去，请求会返回 400。Haiku 4.5 没有这项检查，所以老代码里“每轮改动 system 提示”“中途增删工具”的做法到这里会出问题。

官方补充了一个范围说明：2026 年 8 月 31 日 00:00（UTC）之前创建的账号，只有在请求里设置了 `thinking.block_binding.prefix_mismatch_behavior` 时才会报这个错。

另外两点不报错、但会影响结果：

- Haiku 5.5 的思维块只能在产生它的账号（或与之关联的账号）里使用。用另一个账号回放存下来的对话时，API 会静默丢掉这些思维块，请求照常成功，但模型看不到之前的推理。多客户共用一个对话库的服务要注意按原账号回放。
- 早先轮次的思维块会留在上下文里、按输入 token 计费，而 Haiku 4.5 只保留最近一轮的。多轮对话的输入 token 会因此增加，可以用官方的 thinking block clearing（上下文编辑）清理旧块。

## 不报错但结果不对：空回答、截断与 token 变多

改完上面几项、请求不再 400 之后，还有几处行为变化要检查：

1. **按类型读内容块**。回答可能以 `thinking` 块开头，代码里写死 `content[0].text` 会读到空值或出错。要遍历 `content`，取 `type` 为 `text` 的块。
2. **思考内容默认不返回**。Haiku 5.5 返回的 `thinking` 块默认只有 `signature`，`thinking` 字段为空；Haiku 4.5 返回的是摘要。需要看摘要就设 `thinking: {"type": "adaptive", "display": "summarized"}`。带工具结果回传时，思维块要原样传回。
3. **max_tokens 要留出思考空间**。思考 token 计入 `max_tokens`，原来给 Haiku 4.5 设的小上限可能让请求在 `thinking` 块之后、正文之前就以 `stop_reason: "max_tokens"` 结束。调大上限，或降低 effort。
4. **同样的文本 token 更多**。Haiku 5.5 用的是 Claude 4.7 之后的新分词器，官方说明同样的输入大约多出 30% 的 token，具体看内容；大图片也会按高分辨率档位计算更多视觉 token。用量预估、`max_tokens` 和成本测算要用 `model: "claude-haiku-5-5"` 重新计数，不要沿用 Haiku 4.5 的数字。
5. **处理拒答**。Haiku 5.5 运行安全分类器，可能返回 `stop_reason: "refusal"`，而且没有服务端兜底，代码里要有对应分支。
6. **强制工具调用没有思考**。`tool_choice` 设为 `any` 或指定工具时 Haiku 5.5 可以接受，但回答直接从工具调用开始，不带 `thinking` 块。想让模型先思考再调用工具，用 `{"type": "auto"}` 并在提示里说明什么时候用工具。

## 迁移后怎么验证

按下面的顺序逐项确认，全部满足再切生产流量：

1. 打印实际发出的请求体：`model` 是对应平台的 Haiku 5.5 ID；没有 `budget_tokens`、`temperature`、`top_p`、`top_k`；`messages` 以 user 轮结尾。
2. 用几条典型请求各跑一次，确认都返回 200，响应里能按 `type` 取到 `text` 块。
3. 检查 `stop_reason`：正常是 `end_turn` 或 `tool_use`；如果出现 `max_tokens` 且没有正文，调大上限或降低 effort。
4. 多轮和工具调用场景至少跑通两轮，确认回传思维块后不再出现 400。
5. 用 token counting 接口在 `claude-haiku-5-5` 上重新计算典型提示的 token 数，更新 `max_tokens` 和成本预估。
6. 如果用计算机使用工具，确认 tools 里已没有 `computer_20250124`，Claude API 上也没有残留 `fine-grained-tool-streaming-2025-05-14` 头。

如果项目代码量大，官方迁移指南还提供了 Claude Code 自带的 Claude API 技能：运行 `/claude-api migrate this project to claude-haiku-5-5`，它会替换模型 ID、处理上述参数变化，并列出需要人工确认的事项。改完仍要按上面的清单验证。

## 来源

- 官方迁移指南：[Claude Haiku 5.5 migration guide](https://platform.claude.com/docs/en/models/haiku-5-5/migration-guide)
- 官方发版说明（2026-10-07 条目）：[Claude Platform release notes](https://platform.claude.com/docs/en/release-notes/overview)
- 官方文档：[Effort](https://platform.claude.com/docs/en/build-with-claude/effort)

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-haiku-5-5-migration-400-errors-fix&utm_content=footer)。

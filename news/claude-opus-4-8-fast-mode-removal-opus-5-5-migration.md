---
layout: default
title: "Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: \"fast\" 的请求会报错，留在 4.8 还是换 Opus 5.5"
description: "Anthropic 10 月 30 日宣布 Claude Opus 4.8 快速模式弃用、11 月 30 日移除，之后 claude-opus-4-8 带 speed: fast 的请求会报错。按官方 Fast mode 文档、发布说明和 Opus 5.5 迁移指南，说明留在 4.8 删参数和换 Opus 5.5 继续用快速模式两条路的改法、限流回退与验证方法。"
permalink: /news/claude-opus-4-8-fast-mode-removal-opus-5-5-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[Anthropic Fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode)

# Claude Opus 4.8 快速模式 11 月 30 日移除：带 speed: "fast" 的请求会报错，留在 4.8 还是换 Opus 5.5

Anthropic 在 2026 年 10 月 30 日的发布说明里宣布：Claude Opus 4.8 的快速模式（fast mode）已弃用，**2026 年 11 月 30 日移除**。移除之后，发给 `claude-opus-4-8` 且带 `speed: "fast"` 的请求会返回错误。官方给的出路是迁移到 Claude Opus 5.5。

先说结论，二选一：

- **不在乎输出速度**：继续用 `claude-opus-4-8`，把请求里的 `speed: "fast"` 和 `fast-mode-2026-02-01` beta 头删掉，按标准速度跑。被移除的只是 4.8 的快速模式，官方模型弃用页上 `claude-opus-4-8` 仍是 Active，退役时间写的是不早于 2027 年 5 月 28 日。
- **要继续用快速模式**：模型改成 `claude-opus-5-5`，保留 `speed: "fast"`，beta 头可以不再发。但 Opus 5.5 和 4.8 的请求规则差别不小，只改模型名很可能报 400，下面第四节逐项列出。

本文依据 Anthropic 官方的 [Fast mode 文档](https://platform.claude.com/docs/en/build-with-claude/fast-mode)、[API 发布说明](https://platform.claude.com/docs/en/release-notes/api)、[Opus 5.5 迁移指南](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide) 和 [模型弃用页](https://platform.claude.com/docs/en/about-claude/model-deprecations)，只讲 Messages API。

## 一、先查你的代码有没有用到 Opus 4.8 快速模式

满足下面任意一条，就在这次移除的影响范围内：

1. 请求体里 `model` 是 `claude-opus-4-8`，同时带了 `speed: "fast"`。
2. 请求头里有 `anthropic-beta: fast-mode-2026-02-01`，模型是 `claude-opus-4-8`。按官方文档，Opus 4.8 和 Opus 5 的快速模式还是研究预览，需要这个 beta 头。
3. 用 Claude Managed Agents，智能体的模型对象写成 `{"id": "claude-opus-4-8", "speed": "fast"}`。

最省事的确认办法是看响应：官方说明响应的 `usage` 里有 `speed` 字段，值是 `"fast"` 或 `"standard"`。日志里 `model` 为 `claude-opus-4-8` 且 `usage.speed` 为 `"fast"` 的请求，就是 11 月 30 日之后会出错的那一批。

## 二、两条路怎么选

| 你的情况 | 建议做法 | 要改的地方 |
|---|---|---|
| 只是顺手开了快速模式，对速度不敏感 | 留在 `claude-opus-4-8` | 删 `speed: "fast"` 和 beta 头，其他不动 |
| 流式输出给用户看，依赖快速模式的出字速度 | 换 `claude-opus-5-5` | 模型名 + 第四节的请求规则 |
| 组织有 Priority Tier 承诺 | 换 Opus 5.5 前先单独规划容量 | 官方写明快速模式不能和 Priority Tier 承诺一起用，Opus 5.5 也不支持 Priority Tier |
| 用 Batch API 跑批 | 不受影响 | 官方写明 Batch API 本来就不支持快速模式 |

需要注意，快速模式提升的是**每秒输出 token 数**（官方写的是最高约 2.5 倍），不是首个 token 的等待时间；模型本身的能力不变，只是推理配置更快。官方特别说明快速模式的收益集中在出字速度，不在首字延迟，流式输出时最明显。

## 三、留在 Opus 4.8：删掉快速模式参数

改动只有两处：

1. 请求体删掉 `"speed": "fast"`。
2. 请求头删掉 `fast-mode-2026-02-01`（如果 `anthropic-beta` 里还有别的值，只删这一项）。

改完后请求按标准速度执行，响应的 `usage.speed` 应为 `"standard"`。官方文档说明快速模式的限流额度独立于标准 Opus 限额，关掉之后就不再占用这部分额度，原来针对 `anthropic-fast-*` 响应头写的限流监控可以一并下线。

如果你的代码里有「快速模式 429 时去掉 `speed` 重试」的回退逻辑，这时它已经用不上了，可以保留也可以删。

## 四、换到 Opus 5.5：除了模型名还要改什么

Opus 5.5 上快速模式在 Claude API、Claude Models on Google Cloud（Anthropic 托管）和 Microsoft Foundry 上都是正式可用。按 10 月 15 日的发布说明，Opus 5.5 的快速模式不再需要 beta 头，仍带着 `fast-mode-2026-02-01` 的请求照常可用；Start、Build、Scale 用量等级都有默认的快速模式限额，不用单独申请，Evaluation 等级的组织要升到这三档之后才能用。

快速模式本身的写法不变：

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-opus-5-5", "max_tokens": 1024, "speed": "fast",
       "messages": [{"role": "user", "content": "Hello"}]}'
```

麻烦在模型换代。按迁移指南「从 Claude Opus 4.8 迁移」一节和迁移清单，从 4.8 过来要逐项检查：

1. **思考默认开启、关不掉**：4.8 上不写 `thinking` 就不思考；Opus 5.5 每个请求都走自适应思考。`thinking: {"type": "disabled"}` 和 `thinking: {"type": "enabled", "budget_tokens": N}` 都会返回 400。删掉 `thinking` 字段，用 `output_config.effort` 控制思考量。
2. **effort 默认值变了**：4.8 默认 `high`，Opus 5.5 默认 `medium`，建议显式写上并重新测一遍效果。
3. **`max_tokens` 要重算**：它是思考加正文的总上限，思考 token 按输出 token 计费，原来不思考的请求每次的输出 token 可能变多。用 `xhigh`、`max` 档时官方建议从 64k 起调。
4. **`tool_choice` 不能强制**：`{"type": "any"}` 和 `{"type": "tool", ...}` 返回 400，改成 `auto` 并配合严格工具调用或结构化输出。
5. **computer use 工具版本**：在 Claude API 上 `computer_20251124` 返回 400，要改用 `computer_toolset_20260801`。
6. **读响应按类型取块**：响应可能先出 `thinking` 块，用 `content[0].text` 取正文会出错；工具循环里要把 `thinking` 块原样回传。4.8 把工具调用之间的说明文字放在 `text` 块里，Opus 5.5 改放在 `thinking` 块里，默认显示方式下是空的。

这几条的报错原文和改法，指南站另一篇《[换成 Claude Opus 5.5 后报 400 怎么改](https://a37836323.github.io/openlux-api-guides/news/claude-opus-5-5-migration-400-thinking-tool-choice-fix/)》有逐项对照，这里不重复。另外两条不会报错但值得知道：Opus 5.5 可缓存的最短提示从 4.8 的 1024 token 降到 512 token；它可能返回 `stop_reason: "refusal"`，需要处理。

## 五、快速模式的限流和回退

不管停在哪个模型，只要还在用快速模式，下面几点都适用：

- **独立限流**：超出快速模式限额时返回 429，并带 `retry-after` 头。响应头 `anthropic-fast-input-tokens-limit`、`anthropic-fast-input-tokens-remaining`、`anthropic-fast-output-tokens-limit`、`anthropic-fast-output-tokens-remaining` 等显示当前额度。
- **SDK 自动重试**：官方 SDK 默认对快速模式的 429 重试 2 次，按 `retry-after` 等待。
- **回退到标准速度**：如果宁可降速也不想等，官方建议首个快速请求把 `max_retries` 设为 0，捕获限流错误后去掉 `speed` 重发。注意不同速度的请求不共享提示缓存，回退的那次会缓存未命中。
- **不支持的模型直接报错**：对不支持快速模式的模型发 `speed: "fast"` 会返回错误，超出容量也会返回 429 或 529。

## 六、怎样算改好了

1. 日志里不再有 `model` 为 `claude-opus-4-8` 且带 `speed: "fast"` 的请求。
2. 留在 4.8 的请求：返回 200，`usage.speed` 为 `"standard"`。
3. 换到 5.5 的请求：返回 200，`usage.speed` 为 `"fast"`，按 `type` 能读到 `text` 块；带工具的多轮请求不再出现 400。
4. 用 Console 的 Usage 页导出 CSV，按 API Key 和模型核对，确认没有遗漏的老调用方。

## 七、通过 OpenLux 调用时

截至 2026 年 10 月 31 日，OpenLux 价格接口的在售列表里同时有 `claude-opus-4-8` 和 `claude-opus-5-5`，端点类型都包含 Anthropic Messages 和 OpenAI 兼容。用 Anthropic SDK 时 Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端会自己拼 `/v1/messages`），Key 在 OpenLux 控制台的令牌页创建，价格以官网价格页为准。

本文没有实测 OpenLux 是否把 `speed` 参数和快速模式 beta 头转发给上游，也没有核实走 OpenAI 兼容端点时如何对应 `speed`。判断快速模式是否真的生效，以响应里的 `usage.speed` 为准：没有这个字段或值为 `"standard"`，就说明这次请求按标准速度执行。先用 `/v1/models` 确认列表里有你要用的模型，再按第六节逐项验证。

需要通过 OpenLux 调用 `claude-opus-5-5` 或 `claude-opus-4-8` 时，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-opus-4-8-fast-mode-removal-opus-5-5-migration&utm_content=footer)。

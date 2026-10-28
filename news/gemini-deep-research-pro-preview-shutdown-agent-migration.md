---
layout: default
title: "Gemini Deep Research 突然调不通：deep-research-pro-preview-12-2025 停用后 agent 参数怎么改"
description: "Gemini Deep Research 旧版 agent deep-research-pro-preview-12-2025 已于 2026-10-23 停用。按官方更新日志把 agent 改成 deep-research-preview-04-2026 或 Max 版，并核对 Interactions API、background、store、流式续接等调用条件，附现象对照表和验证步骤。"
permalink: /news/gemini-deep-research-pro-preview-shutdown-agent-migration/
date: 2026-10-29
---

> 更新日期：2026-10-29 · 一手来源：[Google Gemini API 更新日志](https://ai.google.dev/gemini-api/docs/changelog)

# Gemini Deep Research 突然调不通：deep-research-pro-preview-12-2025 停用后 agent 参数怎么改

结论先说：Google 在 2026 年 10 月 8 日的 [Gemini API 更新日志](https://ai.google.dev/gemini-api/docs/changelog) 里宣布，Deep Research 旧版 agent `deep-research-pro-preview-12-2025` 已弃用，停用日期为 **2026 年 10 月 23 日**。如果你的 Deep Research 任务从这几天起开始失败，先检查 `interactions.create` 里的 `agent` 参数：官方给出的迁移做法是把它从 `deep-research-pro-preview-12-2025` 改成 `deep-research-preview-04-2026`，或者 `deep-research-max-preview-04-2026`。

本文适用于通过 Gemini API 的 Interactions 接口调用 Deep Research agent 的项目。依据是 Google 官方的 [更新日志](https://ai.google.dev/gemini-api/docs/changelog)、[弃用页面](https://ai.google.dev/gemini-api/docs/deprecations)、[Deep Research 文档](https://ai.google.dev/gemini-api/docs/deep-research) 和 [Interactions API 文档](https://ai.google.dev/gemini-api/docs/interactions)。官方没有公布停用后请求会返回哪一条具体报错文本，所以下面按「先改 agent ID，再逐项核对调用条件」的顺序排查。

## 一、官方时间线与可选的新 agent

弃用页对「停用」的说明是：模型停用后会完全关闭，对应端点不再可用。弃用页同时提醒，表里的停用日期是「最早可能停用的日期」。

| 日期 | 事件 | 官方要点 |
|---|---|---|
| 2025-12-11 | `deep-research-pro-preview-12-2025` 发布 | 弃用页列出的发布日期 |
| 2026-04-21 | 发布两个新版 Deep Research agent | 新增协作规划、可视化、MCP 服务器集成和 File Search |
| 2026-10-08 | 旧 agent 宣布弃用 | 要求把 `agent` 参数改成新版 ID |
| 2026-10-23 | 旧 agent 停用 | 弃用页给出的推荐替代是 `deep-research-preview-04-2026` |

两个新 agent 的区别，按 Deep Research 文档原意：

| agent ID | 官方定位 | 适合场景 |
|---|---|---|
| `deep-research-preview-04-2026` | 速度和效率优先，适合流式返回给前端界面 | 需要边跑边展示进度的产品 |
| `deep-research-max-preview-04-2026` | 追求最全面的资料收集与综合 | 后台自动跑、对完整度要求高的报告 |

官方对用量的估算是：普通版一次任务约 80 次搜索，Max 版最多约 160 次搜索，输入 token 也更多，并说明这些是按预览期费率估算、可能变化。想平滑替换旧 agent 时，可以先换成弃用页推荐的 `deep-research-preview-04-2026`，再按报告质量决定是否改用 Max。

## 二、第一步：把 agent 参数改成新 ID

先在代码库里全局搜索 `deep-research-pro-preview-12-2025`，包括配置文件、环境变量和数据库里保存的任务模板。找到后只改 `agent` 的值。Deep Research 文档里的最小 Python 写法如下：

```python
interaction = client.interactions.create(
    agent="deep-research-preview-04-2026",
    input="Research the history of Google TPUs.",
    background=True,
)
```

对应的 REST 请求地址是 `https://generativelanguage.googleapis.com/v1beta/interactions`：

```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/interactions" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent": "deep-research-preview-04-2026", "input": "...", "background": true}'
```

如果改完 ID 仍然失败，继续对照下面几项调用条件。

## 三、第二步：核对新版 agent 的调用条件

这些条件都写在官方文档里，旧代码如果是从别处拼凑来的，容易漏掉其中一项：

1. **只能走 Interactions API。** Deep Research 文档写明，这个 agent 不能通过 `generate_content` 调用。用 `generateContent` 接口传 agent ID 是走不通的。
2. **必须后台执行。** 文档要求设置 `background=true`。
3. **后台执行需要存储。** 文档写明使用 `background=True` 时需要 `store=True`；Interactions 文档也说 `store=false` 与后台执行不兼容。`store` 默认就是开启的，所以只要不手动传 `store=false` 即可。存储的交互记录，付费层默认保留 55 天、免费层保留 1 天。
4. **流式要同时开后台。** 想用 `stream=True` 时，`background=True` 也要一起设置。
5. **`agent_config` 的类型字段。** 如果传了 `agent_config`，其中的 `type` 是必填项，值为 `"deep-research"`。其他字段有默认值：`thinking_summaries` 默认 `"none"`，`visualization` 默认 `"auto"`，`collaborative_planning` 默认 `false`。
6. **工具限制。** 不传 `tools` 时默认带 `google_search`、`url_context` 和 `code_execution`。官方写明目前不能提供自定义函数调用工具，但可以接远程 MCP 服务器，也可以用 `file_search` 检索自己的文件库。
7. **不支持结构化输出。** 如果旧代码依赖 JSON Schema 约束返回格式，需要改为在拿到报告文本后自己解析。

## 四、按现象快速定位

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 10 月 23 日前后起，原来正常的 Deep Research 请求开始失败 | `agent` 仍是 `deep-research-pro-preview-12-2025` | 改成 `deep-research-preview-04-2026` 或 Max 版 |
| 用 `generateContent` 调 Deep Research 不成功 | 官方只开放 Interactions API | 改用 `interactions.create` |
| 请求里没有 `background=true`，或传了 `store=false` | 不满足官方要求：agent 必须后台执行，后台执行需要存储 | 设置 `background=true`，去掉 `store=false` |
| 流式只收到最终结果，看不到思考过程 | `thinking_summaries` 默认是 `"none"` | 在 `agent_config` 里设为 `"auto"` |
| 流式连接中途断开 | 官方提醒连接可能断开或过期（文档举例 600 秒超时） | 记录 `interaction_id` 和最后一个 `event_id`，续接 |
| 带自定义函数工具或结构化输出时不能按预期运行 | 官方写明当前不支持这两项 | 去掉函数工具，改用 MCP；改为自己解析报告文本 |
| 状态变成 `failed` | 任务执行失败 | 读取 `interaction.error`，按内容修改请求 |

Gemini 的排错文档还提醒：400 一类的客户端错误不要原样重试，应先修正请求；同时建议确认使用的是受支持的模型和正确的 API 版本。

## 五、长任务的轮询与断线续接

Deep Research 任务通常要跑几分钟，官方写明最长研究时间为 60 分钟，多数任务 20 分钟内完成。创建请求会立即返回一个未完成的交互对象，之后有两种取结果的方式：

**轮询。** 用 `interactions.get(id)` 循环查询，官方示例每 5～10 秒查一次。状态为 `in_progress` 时继续等，`completed` 时从 `steps[-1].content[0].text` 读取最终报告，`failed` 时读取 `interaction.error`。

**流式加续接。** 流式事件包括 `interaction.created`、`step.delta`、`interaction.completed` 和 `interaction.error`。连接断开后，如果状态仍是 `in_progress`，用 `interactions.get` 带上 `stream=True` 和 `last_event_id` 继续接收；REST 写法是 `GET .../interactions/ID?stream=true&last_event_id=LAST_EVENT_ID`。所以代码里一定要保存 `interaction_id` 和最后收到的 `event_id`，否则断线后只能重新发起一次研究。

如果旧代码用了多轮追问，新版本支持用 `previous_interaction_id` 接着上一次交互继续。官方示例中，追问可以改用普通模型（示例为 `gemini-4-argon`）配合 `previous_interaction_id`，不必每次都启动一次完整研究。需要注意，Interactions 文档写明 `tools`、`system_instruction`、`generation_config` 只对当次交互生效，追问时要重新传。

## 六、改完怎么验证

1. 全局搜索代码和配置，确认已经没有 `deep-research-pro-preview-12-2025`。
2. 用新 agent ID 发起一个简单的研究任务，确认创建请求返回了交互 ID，状态为 `in_progress`。
3. 轮询直到状态变为 `completed`，能从 `steps[-1].content[0].text` 读到完整报告，即视为迁移成功。
4. 如果用了流式，手动中断一次连接，再用 `last_event_id` 续接，确认能接着收到后续事件。
5. 抽查报告里的引用来源。官方安全建议提到，agent 可能读到恶意网页内容，应核对返回的 `citations`。

## 七、通过 OpenLux 调用时要注意什么

截至 2026 年 10 月 29 日，OpenLux 价格接口的在售模型列表里没有 Deep Research 系列 agent ID，Deep Research 任务请按本文直接调用 Google 官方的 Interactions API。OpenLux 在售列表里有 `gemini-4-argon` 等 Gemini 模型，Gemini 原生接口的地址填 `https://api.openlux.ai`，请求路径为 `/v1beta/models/<模型>:generateContent`；如前文所说，`generateContent` 不能调用 Deep Research agent，只适合普通的对话与生成请求。Key 在 OpenLux 控制台的令牌页创建，价格以官网价格页为准。

需要调用 OpenLux 在售的 Gemini 模型时，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-deep-research-pro-preview-shutdown-agent-migration&utm_content=footer)。

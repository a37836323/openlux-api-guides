---
layout: default
title: "gpt-3.5-turbo、gpt-4、o1、o3-mini、o4-mini 已于 10 月 23 日下线：调用失败后怎么换成 GPT-5.6"
description: "OpenAI 已于 2026 年 10 月 23 日下线 gpt-3.5-turbo、gpt-4、gpt-4-turbo、o1、o3-mini、o4-mini 等模型。本文按官方弃用页给出替代对照表，并说明换成 gpt-5.6-sol、terra、luna 时推理强度、函数工具、旧 completions 接口和微调模型要怎么改。"
permalink: /news/openai-legacy-models-oct-23-shutdown-migration/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# gpt-3.5-turbo、gpt-4、o1、o3-mini、o4-mini 已于 10 月 23 日下线：调用失败后怎么换成 GPT-5.6

如果你的代码还在调用 `gpt-3.5-turbo`、`gpt-4`、`gpt-4-turbo`、`o1`、`o3-mini`、`o4-mini` 这些老模型，从 2026 年 10 月 23 日起它们已经调不通了。OpenAI 在 4 月 22 日发布弃用公告，[官方弃用页](https://developers.openai.com/api/docs/deprecations)写明：Access to these models was shut down on October 23, 2026。解决办法只有一个：按官方给的对照表换成 GPT-5.6 的 Sol、Terra 或 Luna，同时检查推理强度、接口类型和微调模型。

本文适用于直接调用 OpenAI API，或通过 OpenAI 兼容中转调用的项目。官方弃用页只说下线后模型不可访问，没有写具体返回哪个错误码，所以下面先教你确认原因，再说怎么改。

## 10 月 23 日下线了哪些模型，官方让换成什么

下表按官方弃用页 2026-04-22「Legacy GPT model snapshots」一节整理：

| 下线的模型（含别名） | 官方替代模型 |
|---|---|
| `gpt-3.5-turbo`、`gpt-3.5-turbo-0125`、`gpt-3.5-turbo-completions` | `gpt-5.6-terra` |
| `gpt-4`、`gpt-4-0613`、`gpt-4-completions`、`gpt-4-0613-completions` | `gpt-5.6-sol` |
| `gpt-4-1106-preview` | `gpt-5.6-sol` |
| `gpt-4-turbo`、`gpt-4-turbo-2024-04-09`、`gpt-4-turbo-completions` | `gpt-5.6-sol` |
| `gpt-4o-2024-05-13` | `gpt-5.6-sol` |
| `gpt-4.1-nano`、`gpt-4.1-nano-2025-04-14` | `gpt-5.6-luna` |
| `o1`、`o1-2024-12-17`、`o3-mini`、`o3-mini-2025-01-31` | `gpt-5.6-sol` |
| `o1-pro`、`o1-pro-2025-03-19` | `gpt-5.6-sol`，并设 `reasoning.mode: pro` |
| `o4-mini`、`o4-mini-2025-04-16`、`ft-o4-mini-2025-04-16` | `gpt-5.6-terra` |
| `gpt-image-1` | `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare` |

官方还写明：基于这些模型的微调模型，与底座模型同一天下线。

注意不是所有 `gpt-4o`、`gpt-4.1` 都在这一批：本批只有 `gpt-4o-2024-05-13` 和 `gpt-4.1-nano`。`gpt-4o-2024-08-06`、`gpt-4o-2024-11-20`、`gpt-4o-mini-2024-07-18`、`gpt-4.1-2025-04-14`、`gpt-4.1-mini-2025-04-14` 是另一批，官方计划 2027 年 1 月 14 日下线；`gpt-5`、`o3` 等计划 2026 年 12 月 11 日下线。

## 先确认失败是不是下线造成的

按下面顺序排查，命中一条就可以确定原因：

1. **核对模型名**：把请求里的 `model` 值和上表逐个比对，包括环境变量、配置文件里的默认模型。
2. **看报错类型**：官方错误码页的 Python 库错误类型表里，`NotFoundError` 的含义是请求的资源不存在。如果模型名在上表里，又出现这类「资源/模型不存在」的报错，大概率就是下线导致。
3. **用接口查下线日期**：官方弃用页建议调用 `GET /v1/models`，看每个模型的可选字段 `shutdown_date`（`YYYY-MM-DD` 格式，未公布则为 `null`）；查单个模型用 Retrieve a model 接口。这个字段也适合拿来提前发现下一批要下线的模型。
4. **检查微调模型**：模型名以 `ft:` 开头且底座是上表模型的，也一起下线了。

如果模型名不在上表里，就不是这次下线的问题，按报错原文另行排查。

## 按原来的用途选 Sol、Terra 还是 Luna

官方对照表给的是默认替代，但 [GPT-5.6 Sol 升级指南](https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol)强调不要只做模型名字符串替换，要按每个调用点的角色选型：

| 原来的角色 | 起步目标 | 官方理由 |
|---|---|---|
| 旗舰模型、最难的推理任务 | `gpt-5.6-sol` | Sol 是旗舰档 |
| mini 模型、成本适中的常规任务 | `gpt-5.6-terra` | Terra 相当于 mini 档 |
| nano 模型、分类、抽取、路由、大批量 | `gpt-5.6-luna` | Luna 相当于 nano 档 |
| GPT-4.1 / GPT-4o 的低延迟流程 | 先评估 Luna 和 Terra，质量不够再用 Sol | 换成旗舰会明显改变延迟和成本 |
| 原来用 Pro | Sol 加 `reasoning.mode: "pro"` | GPT-5.6 的 Pro 是模式，不是单独的模型名 |

所以 `gpt-4o-2024-05-13` 虽然在弃用表里对应 Sol，如果它原来跑的是对延迟敏感的流程，按升级指南应先试 Luna、Terra。`o1-pro` 的 Pro 模式要在 Responses API 里设置，不要去找「gpt-5.6-pro」之类的模型名。

## 改模型名之外必须检查的四件事

**1. 推理强度默认值变了。** 升级指南写明 GPT-5.6 支持 `none`、`low`、`medium`、`high`、`xhigh`、`max`，不写时默认 `medium`。官方提醒，原来没写推理设置的调用，换模型后可能变慢、变贵。处理原则：原来显式写了推理强度的（例如 `o1`、`o3-mini`、`o4-mini` 的调用），第一次迁移先保留同样的值；原来没写、实际相当于不推理，又想保持原来的延迟和成本，就显式写 `none`；拿不准原来的效果时不要猜，先用代表性样本对比。Responses 用 `reasoning.effort`，Chat Completions 用 `reasoning_effort`。

**2. Chat Completions 加函数工具时只能用 `none`。** 升级指南把这一条列为最重要的接口检查：GPT-5.6 在 Chat Completions 里使用函数工具，只兼容实际推理强度为 `none`；既要推理又要工具，应迁到 Responses API。必须保留 Chat Completions 和工具的低延迟流程，官方示例是显式写：

```json
{
  "model": "gpt-5.6-luna",
  "reasoning_effort": "none",
  "tools": [{ "type": "function", "function": { "...": "..." } }]
}
```

**3. 旧的 `/v1/completions` 不再支持。** 弃用表里有 `gpt-3.5-turbo-completions`、`gpt-4-completions` 等条目，而 Sol、Terra、Luna 的官方模型页都把 Completions (legacy) `v1/completions` 标为 Not supported。原来走 `/v1/completions`（`prompt` 字段）的代码，换模型时要改成 Chat Completions 或 Responses 的请求格式。

**4. 微调模型没法原样迁移。** 三个替代模型的模型页都把 Fine-tuning 标为 Not supported；弃用页还写明，自助微调将在 2027 年 1 月 6 日停止为现有客户创建新任务。依赖 `ft:gpt-3.5-turbo`、`ft-o4-mini` 的业务，需要重新评估方案，并用原来的测试样本对比新模型输出。

改完后如果出现 `Unsupported parameter: max_tokens`，可以参考[这篇 max_tokens 报错的改法](https://a37836323.github.io/openlux-api-guides/news/openai-unsupported-max-tokens-fix/)。

## 全项目搜一遍旧模型名

升级指南建议搜的不只是代码里的模型字符串。按它的清单，至少检查这些地方：

- 模型名、别名、环境变量、命令行参数、配置默认值、部署设置；
- 路由、兜底模型、模型白名单、枚举、正则、校验规则、能力映射；
- 前端模型选择器、显示名称、上下文上限、价格元数据；
- 推理设置、token 预算、采样参数、超时设置；
- 测试、fixture、快照、评测基线、统计标签、账单表和文档。

升级指南还提醒：改默认模型时，运行配置、环境变量、安装文档、测试和部署示例要一起改，否则线上还会有地方在调旧模型。

## 改完怎么验证

1. **模型列表**：请求 `GET /v1/models`，确认新模型名在列表里。
2. **最小请求**：用新模型名发一条短文本请求，确认返回正常。
3. **看实际模型**：升级指南提醒，用 `gpt-5.6` 别名时要记录返回的 `response.model`，别名和显式写 `gpt-5.6-sol` 在面板、限流和账单里的显示可能不同。
4. **回归对比**：用原来的代表性样本跑一遍，比较结果、延迟和用量，再决定推理强度要不要降一档。

全部通过，且日志里不再出现上表的模型名，就算迁移完成。

## 通过 OpenLux 中转调用时

OpenAI 兼容接口的 Base URL 填 `https://api.openlux.ai/v1`，Key 在 OpenLux 控制台「令牌」页创建。按上面第 1 步请求 `/v1/models`，能列出模型就说明地址和 Key 都对。OpenLux 价格接口当前列出的 `gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna` 支持 `openai`（Chat Completions）和 `openai-response`（Responses）两种接口类型，换模型时按上面四件事检查请求参数即可。

还没有账号可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-legacy-models-oct-23-shutdown-migration&utm_content=footer)。

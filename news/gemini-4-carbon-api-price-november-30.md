---
layout: default
title: "Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱"
description: "Gemini 4 Carbon API 目前与 Argon 同为每百万输入 token 2 美元、输出 token 10 美元；介绍价于 11 月 30 日结束，之后分别为 4 美元和 20 美元。"
permalink: /news/gemini-4-carbon-api-price-november-30/
date: 2026-11-11
---

> 更新日期：2026-11-11 · 一手来源：[DeepMind Blog](https://deepmind.google/blog/gemini-4-carbon-is-now-available/)

# Gemini 4 Carbon API 何时涨价？11 月 30 日后输入、输出 token 多少钱

**结论：**按 Google 官方公告和 Gemini API 价格页，Gemini 4 Carbon（模型 ID `gemini-4-carbon`）付费层标准价目前是每百万输入 token **2 美元**、每百万输出 token **10 美元**，执行到 **2026 年 11 月 30 日**；**12 月 1 日起**改为每百万输入 token **4 美元**、输出 token **20 美元**。输出价**包含思考（thinking）token**。另外要注意：**Gemini 4 Argon 的标准价也在同一天按同样幅度调整**，两者调整前后单价相同；两个模型都**不提供免费层**。

本文适合正在估算 Gemini API 成本、安排上线或在 Argon 与 Carbon 之间分配任务的开发者和技术负责人。下面把官方事实、OpenLux 目录情况和作者建议分开说明。

## 官方公布的价格调整是什么？

Google 于 2026 年 11 月 10 日发布 Gemini 4 Carbon，公告说它面向所有付费开发者和企业，通过 Google AI Studio 的 Gemini API 提供，介绍价与 Gemini 4 Argon 相同；脚注写明介绍期于 2026 年 11 月 30 日结束，之后适用每百万输入 4 美元、输出 20 美元，且该价格只适用于面向公开使用的 Carbon 模型。

Gemini API 价格页对 Carbon 付费层各档列得更细（单位：美元 / 每百万 token）：

| 档位 | 输入（至 11-30 → 12-01 起） | 输出，含思考 token（至 11-30 → 12-01 起） | 上下文缓存（至 11-30 → 12-01 起） |
|---|---:|---:|---:|
| Standard（标准） | 2.00 → 4.00 | 10.00 → 20.00 | 0.10 → 0.20 |
| Batch（批处理） | 1.00 → 2.00 | 5.00 → 10.00 | 0.05 → 0.10 |
| Flex | 1.00 → 2.00 | 5.00 → 10.00 | 0.05 → 0.10 |
| Priority（优先） | 3.60 → 7.20 | 18.00 → 36.00 | 0.18 → 0.36 |

价格页还写明：Carbon 只支持隐式缓存，不支持显式缓存；免费层各项均为「不可用」。价格页只给出日期（「through November 30, 2026」「starting December 1, 2026」），没有写切换的具体时刻和时区，也没有说明跨日长任务如何计费；不要自行假定，临近调整时以价格页和账户计费信息为准。

## Argon 也会涨吗？

会。价格页上 Gemini 4 Argon（`gemini-4-argon`）的标准价写法与 Carbon 完全相同：输入 2 美元执行到 11 月 30 日、12 月 1 日起 4 美元；输出（含思考 token）10 美元执行到 11 月 30 日、12 月 1 日起 20 美元。也就是说：

- 只用 Argon、不打算换 Carbon 的项目，同样要按 12 月 1 日后的新单价重做预算。
- 在 Argon 和 Carbon 之间选择时，单价不是差别所在；差别在于**完成同一任务用掉多少 token**。

## 怎么估算调用成本？

> 估算成本 = 输入 token 数 ÷ 1,000,000 × 输入单价 + 输出 token 数（含思考 token）÷ 1,000,000 × 输出单价

例如，一批调用累计 **100 万输入 token、20 万输出 token**，按标准档：11 月 30 日前为 2 + 2 = **4 美元**，12 月 1 日起为 4 + 4 = **8 美元**。这只是按单价做的算术示例，不代表任何真实工作负载的用量或账单；缓存、批处理、工具和 grounding 等其他计费项另按价格页计算。

估算时要特别注意两点：

1. **思考 token 算在输出里。**价格页说明模型处理的每个 token 都计费，包括思考 token；只按最终回答长度估输出，会低估费用。
2. **Carbon 往往比 Argon 用更多 token。**官方公告说，Argon 仍是大多数软件工程和知识工作的理想选择；Carbon 面向复杂的多步编码调试、开放式科研等任务，会比 Argon 用更多 token 来充分探索、深入推理和反复验证。单价相同，但同一任务的总费用可能更高。

## 哪些情况需要重新核算？

- 预算周期跨过 2026 年 11 月 30 日（无论用 Carbon 还是 Argon）。
- 大量调用长文档、多轮或需要长时间推理的任务，输出里思考 token 占比高。
- 计划把部分 Argon 任务换到 Carbon，或按任务难度在两者之间分流。
- 打算改用 Batch、Flex 或 Priority 档位：这几档单价不同，也都在 12 月 1 日调整。
- 原来在免费层测试：Carbon 和 Argon 都没有免费层，要先开通付费层。

## 上线或迁移前，按这几步验证

1. **核对模型 ID 和当前单价。**打开 Gemini API 价格页，确认 `gemini-4-carbon` / `gemini-4-argon` 的档位和日期；不要只看旧预算表或第三方目录。
2. **用代表性任务对比。**用真实会提交的提示词和输入规模，分别跑 Carbon 和 Argon，处理同样的任务。
3. **记录输入、输出（含思考）token 和结果质量。**按任务汇总后，分别套用 11 月 30 日前和 12 月 1 日起的单价。
4. **拆分跨期预算。**预算周期跨越 12 月 1 日时，两段分别计算，不要把当前单价当长期单价。
5. **上线前再查一次价格页。**部署或调整路由前，复查模型、档位价格和可用状态。

## OpenLux 目录里有 Carbon 吗？

截至 2026 年 11 月 11 日，OpenLux 公开价格接口里有 `gemini-4-argon`（支持 `gemini` 和 `openai` 端点），**没有** Gemini 4 Carbon。这只说明 OpenLux 目录当前的情况，不代表 Google 官方 API 是否提供 Carbon；OpenLux 上的价格以其官网价格页为准，本文的美元单价只指 Google 官方 Gemini API。

**事实边界：**发布日期、可用范围、各档价格、调整日期、思考 token 计费及 Carbon 与 Argon 的定位，来自 Google 官方公告和 Gemini API 价格页；OpenLux 目录情况单独说明；估算示例和验证步骤是作者建议，不代表实测结果。

### 官方一手来源

- Google DeepMind / Google 官方博客：《Gemini 4 Carbon is now available》  
  https://deepmind.google/blog/gemini-4-carbon-is-now-available/
- Gemini API 价格页（Gemini 4 Carbon、Gemini 4 Argon）  
  https://ai.google.dev/gemini-api/docs/pricing

如需创建 API Key，可使用：[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-4-carbon-api-price-november-30&utm_content=footer)

## 同专题文章

- [Gemini API 报 400 INVALID_ARGUMENT 怎么办：请求体写错、未知参数、API 版本、新模型规则与 Schema 太复杂逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-400-invalid-argument-fix/)
- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)
- [Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-401-403-permission-denied-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

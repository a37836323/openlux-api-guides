---
layout: default
title: "gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理"
description: "gemini-3.7-flash、gemini-3.5-flash 于 2026-10-08 弃用，请求被自动转到 gemini-3.8-flash、gemini-3.6-flash：按官方弃用页和新特性页说明 thinking_level minimal 报错、thinking_budget 与 thinking_level 同用返回 400、token 变多、预填 model 回合 400 的原因和改法，以及用 modelVersion 验证。"
permalink: /news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[Gemini API 发布说明与弃用页面](https://ai.google.dev/gemini-api/docs/changelog)

# gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理

结论先说：Google 在 2026-10-08 的 [Gemini API 发布说明](https://ai.google.dev/gemini-api/docs/changelog) 里把 `gemini-3.7-flash` 标为弃用，替代是 `gemini-3.8-flash`；`gemini-3.5-flash` 同时弃用，替代是 `gemini-3.6-flash`。两个旧名字**不会下线**：[弃用页面](https://ai.google.dev/gemini-api/docs/deprecations) 写的下线日期是「N/A」，接口继续可用，但请求会被自动转给替代模型处理；AI Studio 里已经选不到这两个旧模型。官方建议开发者把代码里的模型名改掉。

所以，如果你的程序还写着旧模型名，最近出现了下面这些情况，可以先按自动转发来排查：

- 用 `gemini-3.7-flash` 这个名字、带 `thinking_level: "minimal"` 的请求报错；
- 同样的任务，输出 token 或思考 token 明显变多，账单和耗时一起涨；
- 回答风格、工具调用次数和以前不一样；
- 多轮对话里预填了 `model` 回合的请求返回 400。

本文适用于直接调 Gemini API 或通过 OpenAI 兼容接口调用这两个旧模型名的开发者。下文只引用 Google 官方文档，没有逐项实测。

## 一、哪些模型被转到了哪里

| 你请求的模型名 | 实际转给 | 下线日期 | AI Studio 能否选择 | 官方建议 |
|---|---|---|---|---|
| `gemini-3.7-flash` | `gemini-3.8-flash` | N/A（不下线，自动转发） | 不能 | 把模型名改成 `gemini-3.8-flash` |
| `gemini-3.5-flash` | `gemini-3.6-flash` | N/A（不下线，自动转发） | 不能 | 改成 `gemini-3.6-flash` 或 `gemini-3.8-flash` |

注意别和名字相近的模型混淆：`gemini-3.5-flash-lite` 不在这次弃用范围内，[模型列表](https://ai.google.dev/gemini-api/docs/models) 里仍是稳定版；`gemini-3-flash-preview` 在弃用页上也是单独一项。

## 二、怎么确认你的请求被转走了

生成接口的返回体里有 `modelVersion` 字段，[API 参考](https://ai.google.dev/api/generate-content) 对它的定义是「用于生成本次回答的模型版本」。排查时按这个顺序看：

1. 用旧模型名发一个最短请求，记下返回的 `modelVersion`；
2. 再用新模型名（如 `gemini-3.8-flash`）发同样的请求，对比两次的 `modelVersion`；
3. 对比 `usageMetadata` 里的 `thoughtsTokenCount`（思考 token 数）和 `candidatesTokenCount`（回答 token 数），看改动前后的变化。

如果你走的是中转或 OpenAI 兼容接口，返回体是否原样带回 `modelVersion` 取决于服务方，本文未核实；看不到这个字段时，就以第三、四节的参数核对为准。

## 三、gemini-3.7-flash 转到 3.8-flash 后要改什么

### 1. thinking_level 设成 minimal 会报错

[gemini-3.8-flash 模型页](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash) 写明思考档位只支持 `low`、`medium`、`high`，「`minimal` 不受支持，会返回错误」。[3.8 新特性页](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.8) 也写了同样的话，默认档位是 `medium`。如果你的代码给这个模型名配了 `minimal`（比如沿用了 3.6 Flash 或 3 Flash 预览版的配置，[思考指南](https://ai.google.dev/gemini-api/docs/thinking) 列出这两个模型都支持 `minimal`），改成 `low` 即可。

用 OpenAI 兼容接口的，`reasoning_effort` 会映射成 Gemini 的思考档位。但 [OpenAI 兼容说明](https://ai.google.dev/gemini-api/docs/openai) 的映射表里没有列 3.8 Flash，`minimal` 在这个模型上怎么处理文档没写。稳妥做法是只用 `low`、`medium`、`high`。同一页还说明 `reasoning_effort` 和 `thinking_level`/`thinking_budget` 功能重叠，不能同时设置。

### 2. thinking_budget 换成 thinking_level

3.8 新特性页的迁移清单要求把 `thinking_budget` 换成字符串枚举 `thinking_level`。[Gemini 3 开发者指南](https://ai.google.dev/gemini-api/docs/gemini-3)（该页已标为弃用）说明：`thinking_budget` 目前仍向后兼容，但**同一个请求里同时写 `thinking_level` 和 `thinking_budget` 会返回 400**。迁移时最常见的错误就是只加了新参数、没删旧参数。

### 3. token 变多是设计如此

3.8 新特性页写明：3.8 Flash 在长时间、复杂的任务上「按设计会用更多 token」，它会分更小的步骤推理、反复调用工具并自行验证。日常任务可以调低思考档位来减少消耗；另外，`gemini-3.6-flash` 仍然受支持。所以如果你在意成本而不需要 3.8 的能力，可以把模型名明确改成 `gemini-3.6-flash`，而不是继续让旧名字被转到 3.8。

## 四、gemini-3.5-flash 转到 3.6-flash 后要改什么

[3.6 新特性页](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6) 列出的参数变化适用于 3.6 Flash 及之后所有模型：

- **采样参数**：`temperature`、`top_p`、`top_k` 已弃用并被忽略；官方说以后的模型再传这些参数会返回 HTTP 400，建议现在就删掉。想要输出更稳定，改为在系统指令里写明规则。
- **预填 model 回合**：如果请求里最后一个非空回合是 `model` 回合，接口返回 400。原来靠预填来去掉开场白或强制 JSON 的，改用 `system_instruction` 或结构化输出。
- **`candidate_count`**：Gemini 3 及以后不支持，删掉。
- **思考参数**：用 `thinking_level` 替代 `thinking_budget`，默认档位和 3.5 Flash 一样是 `medium`。

行为上，同一页说 3.6 Flash 完成多步工作流时用的推理步骤、对话轮数和工具调用比 3.5 少；但它更倾向于先跑诊断脚本再动手，常规前端任务可能多出探索步骤；界面样式方面，人工评估者更喜欢旧模型的结果，官方建议给出明确的设计规范。

## 五、两条迁移都要查的地方

3.8 新特性页的迁移清单还有几条与函数调用相关，3.6 新特性页也列了前三条：

1. 多模态素材放进函数返回内容里；
2. 内联指令用 `\n\n` 分隔；
3. 遇到与工具调用前文本有关的 `MALFORMED_FUNCTION_CALL`，按 [函数调用文档](https://ai.google.dev/gemini-api/docs/function-calling) 的处理办法改；
4. 只用 generateContent 接口的，确认每个 `FunctionResponse` 都带上 `call_id` 和 `name`（3.8 清单）；
5. 思维签名的保留方式见 [思维签名文档](https://ai.google.dev/gemini-api/docs/thought-signatures)；Gemini 3 开发者指南写明，无状态调用要在后续请求里带上思考块及其签名。

## 六、修复步骤和验证方法

**修复步骤**

1. 在代码、配置和环境变量里全局搜索 `gemini-3.7-flash` 和 `gemini-3.5-flash`；
2. 按第一节的表格改成新模型名，或者按成本需要改成 `gemini-3.6-flash`；
3. 删掉 `thinking_budget`、`temperature`、`top_p`、`top_k`、`candidate_count` 和预填的 `model` 回合；
4. 3.8 Flash 的思考档位只用 `low`、`medium`、`high`；
5. 有函数调用的，按第五节逐项核对。

**验证方法**（以 OpenLux 的 Gemini 原生接口为例，Key 在请求头 `x-goog-api-key` 里传）：

```bash
curl "https://api.openlux.ai/v1beta/models/gemini-3.8-flash:generateContent" \
  -H "x-goog-api-key: $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"用一句话回答：1+1 等于几？"}]}]}'
```

成功标准：HTTP 200，有正常回答；拿一批真实业务请求对比改动前后的 `usageMetadata.thoughtsTokenCount` 和总 token，确认消耗在可接受范围内。返回 401 `Invalid token` 说明 Key 错了或没带；用 OpenAI 兼容接口的，Base URL 填 `https://api.openlux.ai/v1`，模型名写法相同。

## 七、常见问题

**旧模型名还能用多久？** 弃用页写的是「N/A」，接口不下线、会继续转发。但继续用旧名字，实际行为已经是新模型，官方也建议改名。

**经中转调用旧模型名，会被转到新模型吗？** 本文未核实。截至 11 月 1 日，OpenLux 价格接口里 `gemini-3.7-flash`、`gemini-3.5-flash`、`gemini-3.8-flash`、`gemini-3.6-flash` 都在售，各自的价格和计费以价格页为准。最稳的做法仍是直接写新模型名。

**价格会变吗？** 3.8 新特性页提到 3.8 Flash 和 3.6 Flash 的优惠价执行到 2026-12-31，2027-01-01 起按标准价，具体数字以官方和服务商的价格页为准。

如需通过中转调用 Gemini、GPT、Claude 等模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-3-7-3-5-flash-deprecated-auto-routing-fix&utm_content=footer)，在售模型和价格以价格页为准。

## 同专题文章

- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)
- [Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些](https://a37836323.github.io/openlux-api-guides/news/gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration/)
- [gemini-3.1-flash-image 已弃用：换成 gemini-nano-banana-2.1 要改哪些（512 分辨率、image_size 大写 K、思考档位）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-image-deprecated-nano-banana-2-1-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

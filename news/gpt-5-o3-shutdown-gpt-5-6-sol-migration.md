---
layout: default
title: "GPT-5、o3、gpt-5-pro、o3-pro 将于 12 月 11 日下线：换成 gpt-5.6 系列要改哪些参数"
description: "OpenAI 将于 2026-12-11 下线 gpt-5、gpt-5-mini、gpt-5-nano、gpt-5-pro、o3、o3-pro，替代为 gpt-5.6-sol/terra/luna，Pro 模型改用 reasoning.mode: pro。按官方弃用页、推理指南、提示缓存指南和模型页，说明 minimal 推理强度、Pro 模式、缓存参数和多轮推理默认值的变化与迁移验证方法。"
permalink: /news/gpt-5-o3-shutdown-gpt-5-6-sol-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# GPT-5、o3、gpt-5-pro、o3-pro 将于 12 月 11 日下线：换成 gpt-5.6 系列要改哪些参数

结论先说：OpenAI 在 2026-06-11 宣布，`gpt-5`、`gpt-5-mini`、`gpt-5-nano`、`gpt-5-pro`、`o3`、`o3-pro`（含各自的日期快照）将于 2026-12-11 下线。官方给的替代是 GPT-5.6 三个档位：`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna`；两个 Pro 模型没有新的 Pro 模型 ID，而是改用 `gpt-5.6-sol` 并设置 `reasoning.mode: "pro"`。

大多数请求换个模型名就能跑，但有四处要单独处理：`reasoning_effort: "minimal"` 不在 GPT-5.6 的支持列表里；Pro 模式只在 Responses API 里可用；提示缓存参数从 `prompt_cache_retention` 换成了 `prompt_cache_options.ttl`；多轮对话默认会把上一轮的推理带进下一轮。

本文依据 OpenAI 官方的 [弃用页面](https://developers.openai.com/api/docs/deprecations)、[推理指南](https://developers.openai.com/api/docs/guides/reasoning)、[提示缓存指南](https://developers.openai.com/api/docs/guides/prompt-caching)，以及 [gpt-5.6-sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)、[gpt-5](https://developers.openai.com/api/docs/models/gpt-5)、[gpt-5-pro](https://developers.openai.com/api/docs/models/gpt-5-pro)、[o3](https://developers.openai.com/api/docs/models/o3)、[o3-pro](https://developers.openai.com/api/docs/models/o3-pro) 模型页。

## 一、官方替代对照表

| 下线的模型（2026-12-11） | 官方替代 | 备注 |
|---|---|---|
| `gpt-5`、`gpt-5-2025-08-07` | `gpt-5.6-sol` | 模型页说 Sol 大致对应以前 GPT-5 的无后缀档 |
| `gpt-5-mini`、`gpt-5-mini-2025-08-07` | `gpt-5.6-terra` | Terra 大致对应以前的 mini 档 |
| `gpt-5-nano`、`gpt-5-nano-2025-08-07` | `gpt-5.6-luna` | Luna 大致对应以前的 nano 档 |
| `gpt-5-pro`、`gpt-5-pro-2025-10-06` | `gpt-5.6-sol` + `reasoning.mode: "pro"` | 只能走 Responses API |
| `o3`、`o3-2025-04-16` | `gpt-5.6-sol` | |
| `o3-pro`、`o3-pro-2025-06-10` | `gpt-5.6-sol` + `reasoning.mode: "pro"` | 只能走 Responses API |

另外，`gpt-5.6` 这个别名会路由到 `gpt-5.6-sol`。代码里先全局搜一遍上表左列的名字，日期快照也要搜到。

## 二、换模型名之前先核对这几项

| 对比项 | gpt-5 / o3 | gpt-5.6-sol |
|---|---|---|
| 上下文窗口 | gpt-5 为 400,000（输入最多 272,000）；o3 为 200,000 | 1,050,000（输入最多 922,000） |
| 最大输出 | gpt-5 为 128,000；o3 为 100,000 | 128,000 |
| reasoning effort | gpt-5 支持 minimal、low、medium、high；o3 模型页未列出 | none、low、medium（默认）、high、xhigh、max |
| 接口 | Chat Completions、Responses、Batch | Chat Completions、Responses、Batch |
| 缓存时长参数 | `prompt_cache_retention` | `prompt_cache_options.ttl` |
| 多轮推理默认 | `current_turn`（不带入上一轮推理） | `all_turns`（带入可兼容的上一轮推理） |

## 三、reasoning effort 写了 minimal 怎么办

`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna` 三个模型页的支持列表都是 none、low、medium、high、xhigh、max，没有 `minimal`。官方文档没写传 `minimal` 会怎样，迁移时直接换掉，不要依赖它。

换成什么：官方 GPT-6 迁移指南对同样情况的建议是「原来用 `minimal` 的，先从 `low` 开始」；推理指南对 gpt-5.5 的建议也是延迟敏感场景先用 `low`，确有需要再降到 `none`。这两条不是专门写给 GPT-5.6 的，换完请用自己的样本对比效果和耗时。

写法位置不变：Responses 里是 `reasoning.effort`，Chat Completions 里是 `reasoning_effort`。不写的话 GPT-5.6 默认 `medium`。

## 四、gpt-5-pro、o3-pro 迁移：改用 Pro 推理模式

推理指南写明：GPT-5.6 和 GPT-6 模型在 Responses API 里支持 `standard` 和 `pro` 两种推理模式，默认 `standard`。旧的 `gpt-5-pro`、`o3-pro` 本来也只支持 Responses API，所以接口不用换，改模型名并加上 `mode` 即可：

```json
{
  "model": "gpt-5.6-sol",
  "reasoning": { "mode": "pro", "effort": "high" },
  "input": "你的问题"
}
```

几点要注意：

- `mode` 和 `effort` 互相独立。GPT-5.6 不写 effort 时，两种模式都默认 `medium`；而 `gpt-5-pro` 模型页写的是只支持 `high`。想贴近原来的设定，就像上面这样显式写 `high`，再和 `medium` 对比。
- 官方说 Pro 模式用更高的延迟和 token 消耗换取难题上的效果，token 按所选模型的标准单价计费，具体价格以价格页为准。
- 旧 Pro 模型页建议长任务用后台模式防超时；推理指南没有单独说明 Pro 模式与后台模式的搭配，沿用时请自己验证。
- 官方只说明了 Responses API 里的 Pro 模式，示例也是 Responses 请求；Chat Completions 没有给出写法，原来走 Chat Completions 的项目要先切到 Responses。

## 五、提示缓存参数要换

缓存指南写明：GPT-5.6 及之后的模型用 `prompt_cache_options.ttl` 控制缓存时长，取值 `"30m"`（默认）或 `"12h"`（只在 Responses API 里可用），不支持的取值返回 `400 invalid_request_error`。迁移说明原话是用 `prompt_cache_options.ttl` 替换 `prompt_cache_retention`。

旧模型的 `prompt_cache_retention` 取值是 `"in_memory"` 或 `"24h"`，GPT-5.6 没有 `24h` 这一档：走 Responses API 的最长可设 `"12h"`，走 Chat Completions 的只能用 `"30m"`。另外 GPT-5.6 起缓存写入单独计费，`12h` 比 `30m` 贵，倍数见缓存指南；最小可缓存前缀是 1,024 个可见输入 token。

## 六、多轮对话：上一轮的推理默认会带进来

推理指南写明：GPT-5.6 默认 `reasoning.context: "all_turns"`，会把之前轮次可兼容的推理带入下一轮；更早的模型默认 `current_turn`。要让它生效，需要用 `previous_response_id`、conversation 或完整回放之前的输出项；`store: false` 时推理项默认带 `encrypted_content`，要把每个输出项都回传。

推理内容只能在同一模型家族内复用，旧模型留下的不兼容推理会被丢弃。如果换模型后多轮 token 用量变化明显，又想回到旧行为，可以显式设置 `reasoning.context: "current_turn"` 做对比。

## 七、迁移步骤与验证方法

1. 搜代码和配置：找出第一节表格左列的所有模型名，包括日期快照和环境变量里的模型名。
2. 按对照表换模型名：普通模型换成对应档位，Pro 模型换成 `gpt-5.6-sol` 并加 `reasoning.mode: "pro"`。
3. 把 `minimal` 换成 `low`（或按样本测试改成 `none`）。
4. 把 `prompt_cache_retention` 换成 `prompt_cache_options.ttl`。
5. 用一批真实样本回归，记录报错、耗时和 `usage` 中的 token 数。

成功标准：请求不再返回 400；响应里的 `model` 是新模型；样本结果质量不低于旧模型；耗时和 token 用量在可接受范围内。

## 八、常见问题

**模型页推荐的替代为什么和弃用页不一样？** `gpt-5` 模型页写的是推荐最新的 GPT-6 Astra，`o3` 模型页还写着由 GPT-5 接替。本次下线的替代以弃用页为准，即 GPT-5.6 系列。也可以直接上 GPT-6，但它的迁移规则不同，见官方 [GPT-6 迁移指南](https://developers.openai.com/api/docs/guides/latest-model)。

**现在就要换吗？** 这些模型的模型页目前标为 Deprecated（已弃用），弃用页给的下线日期是 2026-12-11。建议提前切换并留出回归测试时间，不要等到最后一天。

**通过中转调用要改什么？** 只改模型名和上述参数，Base URL 不变。以 OpenLux 为例，Base URL 是 `https://api.openlux.ai/v1`；10-31 查询价格接口时，`gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna` 都标注支持 Chat Completions 和 Responses 两种接口。可以先请求 `/v1/models` 确认模型在列表里。

如需通过中转调用 GPT-5.6 系列，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-5-o3-shutdown-gpt-5-6-sol-migration&utm_content=footer)，在售模型和价格以价格页为准。

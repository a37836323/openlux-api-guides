---
layout: default
title: "迁移到 GPT-6 后报 400 怎么改：reasoning_effort none、temperature 与 Chat Completions 工具调用"
description: "从 GPT-5.x 或 GPT-6 Sol 换到 gpt-6-astra、gpt-6.1-sol、gpt-6.1-terra、gpt-6-luna 后请求报 400 或被拒的排查：reasoning_effort 不能设 none/minimal 的模型、需删除的 temperature/top_p/logprobs、Chat Completions 工具调用改走 Responses，以及缓存参数改写。"
permalink: /news/gpt-6-migration-reasoning-none-temperature-400-fix/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/latest-model)

# 迁移到 GPT-6 后报 400 怎么改：reasoning_effort none、temperature 与 Chat Completions 工具调用

把 `model` 从 GPT-5.x 或 GPT-6 Sol 改成 `gpt-6-astra`、`gpt-6.1-sol`、`gpt-6.1-terra` 或 `gpt-6-luna` 之后请求被拒，先查四处：推理强度是不是还设成 `none` 或 `minimal`；请求里是不是还带着 `temperature`、`top_p`、`top_logprobs`、`logprobs`；是不是在 Chat Completions 里带了 `tools`；以及从 GPT-5.5 或更早版本迁来时有没有留着 `prompt_cache_retention`。OpenAI 推理指南写明：GPT-6 Astra 不支持 `none`，把 `reasoning.effort`（Responses）或 `reasoning_effort`（Chat Completions）设成 `none` 会返回 HTTP 400。其余几项是官方迁移清单要求删除或改写的参数，逐项改完再测。

本文适用于直接调用 OpenAI API，以及使用原样转发这些参数的 OpenAI 兼容中转。依据是 OpenAI 官方的 [GPT-6 使用与迁移指南](https://developers.openai.com/api/docs/guides/latest-model)、[推理指南](https://developers.openai.com/api/docs/guides/reasoning) 和各模型页；GPT-6.1 Terra 于 2026 年 10 月 26 日发布，GPT-6.1 Sol 于 9 月 29 日发布，见 [API 更新日志](https://developers.openai.com/api/docs/changelog)。

## 一、先对照：各 GPT-6 模型的推理档位与工具调用限制

下表按官方模型页和迁移指南整理。默认档位一列，模型页没写的标为「未标注」。

| 模型 ID | 可选推理档位 | 默认档位 | 能否设 `none` | Chat Completions 里调用工具 |
|---|---|---|---|---|
| `gpt-6-astra` | low、medium、high、xhigh、max | 未标注 | 不能，设了返回 HTTP 400 | 不支持，改用 Responses |
| `gpt-6.1-sol` | low、medium、high、xhigh、max | medium | 不能（也不支持 minimal） | 不支持，改用 Responses |
| `gpt-6.1-terra` | none、low、medium、high、xhigh、max | medium | 能 | 工具调用需要 Responses |
| `gpt-6-sol` | none、low、medium、high、xhigh、max | medium | 能 | 仅在 `reasoning_effort: "none"` 时支持函数调用 |
| `gpt-6-luna` | none、low、medium、high、xhigh、max | medium | 能 | 仅在 `reasoning_effort: "none"` 时支持函数调用 |

几个模型页列出的档位里都没有 `minimal`。官方的说法是：原来用 `minimal` 的，先改成 `low`，再用有代表性的任务对比结果。

## 二、分支 1：推理强度还设成 none 或 minimal

如果旧代码为了速度把推理设成了 `none`（GPT-5.5、GPT-6 Sol 等模型支持这个值），换到 GPT-6 Astra 或 GPT-6.1 Sol 后就要改，这两个模型不支持 `none`。

改法：

1. 搜索代码和配置里的 `reasoning_effort`、`reasoning.effort`、`"effort"`，找到取值为 `none` 或 `minimal` 的地方。
2. 目标是 `gpt-6-astra` 或 `gpt-6.1-sol` 时，改成 `low`。官方迁移指南原话是「GPT-6 Astra and GPT-6.1 Sol do not support `none`; use `low` instead」。
3. 注意参数位置：Responses 写成 `"reasoning": {"effort": "low"}`，Chat Completions 写成 `"reasoning_effort": "low"`，两种写法不要混用。
4. 如果确实需要 `none`（例如低延迟分类），官方列出支持它的是 GPT-6.1 Terra、GPT-6 Sol 和 GPT-6 Luna。

Responses 只含必要字段的写法：

```json
{
  "model": "gpt-6-astra",
  "reasoning": { "effort": "low" },
  "input": "用一句话说明这个请求能正常返回"
}
```

如果你的应用会在多轮之间调整推理强度，官方建议在单智能体请求里用 `configuration_update` 输入项来改，并保持请求级 `reasoning.effort` 不变，以保住提示缓存的前缀。推理指南还写明：不要把两个 `configuration_update` 项直接相邻放在对话历史里，API 会拒绝相邻的更新。

## 三、分支 2：temperature、top_p、logprobs 还在请求里

官方迁移清单写的是：推理强度不是 `none` 时，删除 `temperature`、`top_p` 和 `top_logprobs`；Chat Completions 还要删除 `logprobs`；Responses 要从 `include` 里去掉 `message.output_text.logprobs`。

需要特别注意两点：

- GPT-6 Astra 和 GPT-6.1 Sol 不支持 `none`，所以对这两个模型，上面这几个参数无论推理设哪一档都要删。
- GPT-6.1 Terra、GPT-6 Sol、GPT-6 Luna 的默认档位是 `medium`。没有显式设 `none` 时，就适用这条删除要求。

排查时不要只看自己写的请求体。用框架或 SDK 封装调用时，检查它的默认模型参数、预设模板或配置文件里有没有设置 `temperature` 或 `top_p`，建议打印一次实际发出的请求体确认。

## 四、分支 3：在 Chat Completions 里调用工具

GPT-6 Astra、GPT-6.1 Sol、GPT-6.1 Terra 都支持 Chat Completions 端点，但官方写明工具调用需要 Responses API。GPT-6 Sol 和 GPT-6 Luna 只有在 `reasoning_effort: "none"` 时才能在 Chat Completions 里做函数调用，要推理加工具就用 Responses。Responses 迁移指南也写明：从 GPT-5.4 起，Chat Completions 不支持在 `reasoning_effort` 不为 `none` 时调用工具。

所以有两条路：

- 目标是 GPT-6 Sol 或 GPT-6 Luna，且可以不推理：在 Chat Completions 里把 `reasoning_effort` 设为 `none`。
- 其余情况：把带工具的请求迁到 `/v1/responses`。

迁到 Responses 时，按官方 [Responses 迁移指南](https://developers.openai.com/api/docs/guides/migrate-to-responses) 改三处：

1. 请求发到 `/v1/responses`，输入从 `messages` 改为 `input`。
2. 函数定义去掉外层的 `function` 包装，`name`、`description`、`parameters` 直接放在工具对象上。另外 Chat Completions 的函数默认非 strict；Responses 省略 `strict` 时会尝试 strict 模式，想保持非 strict 要显式写 `strict: false`。
3. 模型返回的是 `function_call` 项，你执行后用 `function_call_output` 项回传，两者用同一个 `call_id` 对应。回传漏掉或 `call_id` 对不上的报错，可以看本站的 [No tool output found for function call 排查](https://a37836323.github.io/openlux-api-guides/news/responses-no-tool-output-found-fix/)。

## 五、分支 4：从 GPT-5.5 或更早版本迁来时的缓存参数

官方迁移清单要求：从 GPT-5.5 或更早版本迁移时，把 `prompt_cache_retention` 换成 `prompt_cache_options.ttl`，取值 `"30m"`，并查看提示缓存文档里关于缓存边界和缓存写入计费的变化。需要 12 小时缓存的写法和 400 排查，见本站的 [OpenAI 12 小时提示缓存设置](https://a37836323.github.io/openlux-api-guides/news/openai-prompt-cache-12h-ttl-setup/)。

## 六、按现象快速定位

| 现象 | 先查什么 | 改法 |
|---|---|---|
| 换成 `gpt-6-astra` 后立即 400 | `reasoning_effort` / `reasoning.effort` 是否为 `none` | 改成 `low` |
| 换成 `gpt-6.1-sol` 后被拒 | 推理档位是否为 `none` 或 `minimal` | 改成 `low` |
| 去掉推理设置后仍被拒 | 请求或框架默认参数里的 `temperature`、`top_p`、`top_logprobs`、`logprobs` | 全部删除；Responses 还要清理 `include` |
| 不带工具正常，带 `tools` 就失败 | 是否走 Chat Completions | 迁到 Responses；Sol / Luna 也可设 `none` |
| 多轮调整推理后被拒 | 是否有两个相邻的 `configuration_update` 项 | 去掉多余的一个，让更新项不直接相邻 |

## 七、改完怎么验证

1. 先发不带工具、不带采样参数的请求：只写 `model`、`input` 和 `reasoning.effort: "low"`。返回 200 且 `output` 里有文本，说明模型名和推理档位没问题。
2. 再把原请求的其他参数一个个加回去，哪一个加上后开始报错，就是要改的那一项。
3. 带工具的流程：Responses 返回 `function_call` 项，回传同一 `call_id` 的 `function_call_output` 后拿到模型的回答，才算迁移完成。
4. 通过 OpenLux 调用时，Base URL 填 `https://api.openlux.ai/v1`，Key 在控制台「令牌」页创建。先请求 `/v1/models`，能列出模型说明地址和 Key 都正确；OpenLux 价格接口当前在售的 GPT-6 模型 ID 包括 `gpt-6-astra`、`gpt-6.1-sol`、`gpt-6.1-terra`、`gpt-6-sol`、`gpt-6-luna`，以 `/v1/models` 实际返回为准。中转对上述参数的处理没有逐项核实，遇到报错仍按上面的分支排查，以返回内容为准。

## 官方来源

- [Using GPT-6（迁移清单、限制说明）](https://developers.openai.com/api/docs/guides/latest-model)
- [Reasoning 指南（Astra 设 none 返回 HTTP 400、configuration_update）](https://developers.openai.com/api/docs/guides/reasoning)
- [Migrate to the Responses API（函数定义与工具调用差异）](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [GPT-6 Astra 模型页](https://developers.openai.com/api/docs/models/gpt-6-astra)、[GPT-6.1 Sol 模型页](https://developers.openai.com/api/docs/models/gpt-6.1-sol)、[GPT-6.1 Terra 模型页](https://developers.openai.com/api/docs/models/gpt-6.1-terra)
- [API 更新日志](https://developers.openai.com/api/docs/changelog)

需要一个 OpenAI 兼容地址来测试 GPT-6 系列模型，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-6-migration-reasoning-none-temperature-400-fix&utm_content=footer)。

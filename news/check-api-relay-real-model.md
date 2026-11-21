---
layout: default
title: "中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）"
description: "中转站检测：用 Token 计数、固定题对照、上下文长度、功能探测和账单核对，判断 API 中转站给的是不是官方原模型、有没有降智。"
permalink: /news/check-api-relay-real-model/
date: 2026-11-16
---

> 更新日期：2026-11-16 · 一手来源：[Anthropic 与 OpenAI 官方文档](https://docs.claude.com/en/docs/build-with-claude/token-counting)

# 中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）

做中转站检测、真假检测或降智排查，先说结论：**没有哪一种方法能百分之百证明「是官方原模型」**，但把下面几项组合起来，能可靠地发现常见问题：换成便宜模型、偷偷截短上下文、压低输出长度、乱算 Token。这些检查大多只需要中转站的 API Key 和几条 curl 命令（Claude 的 Token 计数对照还需要一个官方 Key），适用于 OpenAI 兼容和 Anthropic Messages 两种接口，对任何中转站都一样，包括我们自己。

## 「降智」通常是哪几种情况

| 情况 | 你会看到的现象 | 用哪项检查能发现 |
|---|---|---|
| 换成更便宜的模型 | 难题答不出、风格变了，但返回的 `model` 字段照写原模型名 | 检查 1、2 |
| 截短上下文 | 长文档后半部分「看不见」，长对话里忘了前面的内容 | 检查 3 |
| 压低输出上限 | 回答总在差不多的长度被截断，`finish_reason` 是 `length` | 检查 4 |
| 关掉或削弱功能 | 工具调用、图片输入、思考模式不生效或报错 | 检查 5 |
| 多算 Token 或缓存不计价 | 账单里的 Token 数明显比官方计数多 | 检查 1、6 |
| 偷偷加系统提示词 | 回答里出现你没要求的口头禅、自称别的名字 | 检查 2 |

## 检查 1：Token 计数对不对得上（最客观）

不同模型家族用不同的分词器。同一段输入，官方算出的 Token 数和中转站返回的 `usage` 应该基本一致。如果差得多，要么换了模型，要么计费有问题。

- **Claude**：Anthropic 官方提供 Token 计数接口（`/v1/messages/count_tokens`），[官方文档](https://docs.claude.com/en/docs/build-with-claude/token-counting)说明计数是估算值，可能差一点点，不会差很多。用官方 Key 算一次，再拿同样的 `system` 和 `messages` 通过中转站发一次真实请求，对比返回里的 `usage.input_tokens`。
- **GPT**：用 OpenAI 开源的分词库 [tiktoken](https://github.com/openai/tiktoken) 在本地算，不需要官方 Key。对比中转站返回的 `usage.prompt_tokens`。注意：每条消息的格式本身也会多占几个 Token，所以拿一段几千字的长文本来比，差几个 Token 不用在意。

判断方法：两边差在 1～2% 以内算正常；差 10% 以上就值得追问：可能是换了模型，也可能是中转站额外加了系统提示词，或者计费有问题，要结合检查 2、检查 6 一起判断。

## 检查 2：用一组固定题目对照

准备 10～20 道有标准答案、对模型能力有区分度的题，比如多步数学题、需要精确遵循格式的指令、一段需要找 bug 的代码。每道题在官方渠道和中转站各跑 3 次，`temperature` 设为 0，比较正确率。

- 题目要自己出，不要用网上流传的「照妖镜」题。公开题很可能已经被训练过，也可能被中转站专门识别出来特殊处理。
- 问模型「你是谁、你的知识截止日期」**不能作为证据**：模型自我介绍不可靠，系统提示词也能随便改它的回答。
- 正确率明显低于官方，并且多次复现，就是降智最直接的证据。

## 检查 3：上下文长度够不够

做一段长文本，在开头、中间和结尾各藏一句「暗号」，长度接近该模型官方标称上下文的 70%～80%，然后让模型把三句暗号都找出来。只找得到后面的，说明前面被截掉了。同时看 `usage` 里的输入 Token 数是不是跟你发的长度相符。

## 检查 4：输出上限和截断

把 `max_tokens` 设成官方允许的较大值，让模型写一篇很长的文章，看返回的 `finish_reason`（OpenAI）或 `stop_reason`（Anthropic）：

- `stop` / `end_turn`：正常写完。
- `length` / `max_tokens`：被截断。如果每次都在远小于你设定的长度处截断，说明中转站压低了输出上限。

## 检查 5：功能是不是真的生效

按官方文档确认这个模型支持哪些功能，再逐项实测：工具调用（让它调用一个你定义的函数，看返回的参数是否合法）、图片输入、流式输出、思考或推理模式。官方支持、中转站却报错或悄悄忽略的，要问清楚原因。

## 检查 6：账单逐条核对

正规的中转站应该让你逐条查到每次请求的时间、模型、输入和输出 Token 数、缓存 Token 数以及扣费金额。拿检查 1 的数据对一下：

- 账单上的 Token 数和接口返回的 `usage` 是否一致；
- 扣费是否等于 Token 数乘以价格页公布的单价；
- 有缓存的请求，缓存 Token 是否按更低的价格计费。

只显示余额变化、查不到明细的站，出了异常扣费很难说清楚。

## 测完怎么选

- 先小额充值，跑满一两天真实业务后再决定，不要一次充很多。
- 隔一段时间重测一次。同一个站在不同线路、不同时段的表现可能不同。
- 第三方的公开监测和众测榜单可以参考，但它们只是在特定时间、特定样本下的观察，最终以你自己的测试为准。

OpenLux 控制台的「使用日志」可以逐条查到每次请求的模型、Token 数和扣费，欢迎用上面的方法自己测：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=check-api-relay-real-model&utm_content=footer)

## 同专题文章

- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？](https://a37836323.github.io/openlux-api-guides/news/how-to-access-pardig-satweave-weather-datasets/)
- [llama.cpp 升级 v1.0.0 会破坏 C API/ABI 吗？如何固定 libllama/libggml 版本并安排迁移](https://a37836323.github.io/openlux-api-guides/news/llama-cpp-v1-api-abi-migration/)
- [如何用 Hugging Face Jobs 微调 TRELLIS.2？遇到“需要 HF_TOKEN 和 DINOv3 权限”怎么处理](https://a37836323.github.io/openlux-api-guides/news/how-to-finetune-trellis2-with-hugging-face-jobs/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

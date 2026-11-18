---
layout: default
title: "Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？"
description: "Anthropic 说明，指定模型的 API 请求若将 temperature、top_p 或 top_k 设为非默认值，生成文本可能不带文本水印；检查采样参数及水印平台支持情况。"
permalink: /news/claude-api-sampling-parameters-text-watermark/
date: 2026-11-18
---

> 更新日期：2026-11-18 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#text-watermark-claude-opus-4-6-and-4-5-models)

# Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？

**结论：** 按 Anthropic 官方文档，Claude Opus 4.6、Sonnet 4.6、Opus 4.5、Sonnet 4.5、Haiku 4.5 和 Opus 3 这几个型号，只要请求把 `temperature`、`top_p`、`top_k` 中任意一个设成非默认值，输出就**可能**不带 Anthropic 文本水印。如果你的业务需要输出带水印，官方给的改法只有一条：**请求里不要传这三个参数**，并检查框架或 SDK 有没有替你自动加上。

这篇适合因为合规或内容标识要求、需要 Claude 输出带水印的开发者。如果你不依赖水印，这条变化不需要你改任何东西：官方说明水印不改变输出的意思、质量和可读性，不增加 token，也不插入隐藏字符。

## 官方到底说了什么？

Anthropic 在 [Claude 平台发布说明](https://platform.claude.com/docs/en/release-notes/overview#text-watermark-claude-opus-4-6-and-4-5-models)里分两次公布了相关变化：

- **2026 年 11 月 16 日**：Claude Opus 4.6、Opus 4.5、Sonnet 4.5、Haiku 4.5 在受支持的平台上生成的文本带 Anthropic 文本水印；如果请求把 `temperature`、`top_p` 或 `top_k` 设为非默认值，文本可能不带水印。
- **2026 年 11 月 3 日**：Claude Mythos 5、Opus 4.7、Sonnet 4.6 生成的文本带水印；其中只有 Sonnet 4.6 有同样的采样参数提醒。

[Text watermark](https://platform.claude.com/docs/en/build-with-claude/text-watermark) 文档的「Sampling settings」一节写得更直接：需要输出带水印时，请求里省略 `temperature`、`top_p` 和 `top_k`；任意一个设成非默认值，输出都可能不带水印。文档还特别提醒：你用的框架或客户端库可能会替你设置这些参数，需要水印的话要检查它的设置和实际发出的请求体，把它设置的这三个参数删掉。

注意官方用的是「可能不带」，不是「一定不带」，也不是报错——请求照常返回，只是水印不再可靠。

## 哪些型号受采样参数影响？

| 型号 | 带文本水印 | 设非默认 temperature / top_p / top_k 可能丢水印 |
|---|---|---|
| Claude Opus 4.6 | 是 | 是 |
| Claude Opus 4.5 | 是 | 是 |
| Claude Sonnet 4.6 | 是 | 是 |
| Claude Sonnet 4.5 | 是 | 是 |
| Claude Haiku 4.5 | 是 | 是 |
| Claude Opus 3（按申请开通） | 是 | 是 |
| Claude Opus 4.7、Mythos 5 及更新的 5.x 型号 | 是 | 官方采样提醒里没有列出 |

表格依据 Text watermark 文档「Sampling settings」的适用范围，以及帮助中心文章《How Claude marks AI-generated content》的型号列表。没列在采样提醒里的型号，官方没有说会受采样参数影响，本文也不做推断。

## 哪些平台上的输出带水印？

帮助中心文章 [How Claude marks AI-generated content](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content) 列出的范围是：

- **Anthropic 自己的产品**：Claude Platform（API）、Claude、Claude Code、Claude Cowork、Claude Tag。文章说明水印是在模型层面加的，无论文本来自哪个 Claude 产品都会有。
- **云合作伙伴**：通过 AWS、Google Cloud、Microsoft Foundry 调用受支持的型号，输出也带水印；Amazon Bedrock 上的上线可能会晚几天。
- 文章同时说明：部分平台或功能可能不支持某些标记类型。

官方列表里没有第三方转发服务。如果你经由中转或自建代理调用，能确认的只有一点：上面的采样参数规则看的是**最终发到模型的请求**，所以要检查的是转发层和客户端实际发出去的请求体，而不只是你代码里写的参数。

## 需要水印时怎么改：5 步排查

1. **确认型号。** 看响应里的 `model` 字段，确认实际用的是不是上表里受影响的型号，不要只看配置文件。
2. **抓最终请求体。** 在发请求前打印或抓包，看 JSON 里有没有 `temperature`、`top_p`、`top_k`。官方明确提醒框架和客户端库可能自动加这些参数，所以要看实际发出的请求，而不是只搜自己的代码。
3. **直接删掉这三个字段。** 官方写的是「omit」（省略），不是「改成默认值」。文档没有给出默认值的具体数字，所以不要凭经验填一个「看起来像默认」的值，最稳妥的做法是不传。
4. **核对平台。** 对照上一节的平台列表，确认你的调用方式在官方范围内；用 Bedrock 刚上线的型号时，留意可能晚几天。
5. **把检查放进回归测试。** 在测试里断言请求体不含这三个字段，防止以后升级 SDK 或改配置时又被加回去。

**成功标准：** 最终请求体里不含 `temperature`、`top_p`、`top_k`，型号和平台都在官方列表里。普通开发者目前没法自己检测某段文本有没有水印（见下一节），所以只能用这三条来确认配置是对的。

## 为什么没法自己验证有没有水印？

Anthropic 在 [Claude 文本水印的介绍文章](https://www.anthropic.com/news/claude-text-watermark)里说明：目前没有公开的文本水印检测工具；检测 API 处于私有预览，只开放给欧盟法规要求范围内的合格组织（如监管机构、媒体、事实核查机构、研究人员）和部分有合规义务的企业，之后会逐步扩大，可以通过文中的表单登记意向。

即使拿到检测能力，也有几种情况会让水印检测不出来，这和采样参数无关：

- 文本被大幅编辑，或者和其他文字混在一起；
- 篇幅很短，信号不够；
- 事实性段落和代码里的水印本来就更稀疏。

## 水印不能说明什么？

按官方介绍，文本水印不含任何身份信息，不能追溯到具体的人、组织或对话；它不说明文本的所有权或作者归属，也分不清「Claude 写的」和「Claude 大幅修改过的」。所以「没检测到水印」不能证明文本是人写的，「检测到水印」也不能说明是谁写的。

## 检查清单

- [ ] 响应里的 `model` 是否属于受影响型号
- [ ] 最终请求体里没有 `temperature`、`top_p`、`top_k`（包括框架、SDK 或转发层自动加的）
- [ ] 调用平台在官方列表内
- [ ] 回归测试里有对这三个字段的断言

## 官方一手来源

- Claude 平台发布说明（2026-11-16、2026-11-03 条目）：https://platform.claude.com/docs/en/release-notes/overview#text-watermark-claude-opus-4-6-and-4-5-models
- Text watermark：https://platform.claude.com/docs/en/build-with-claude/text-watermark
- How Claude marks AI-generated content：https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content
- How Claude's text watermark works：https://www.anthropic.com/news/claude-text-watermark

[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-sampling-parameters-text-watermark&utm_content=footer)

## 同专题文章

- [Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-image-400-size-dimension-limit-fix/)
- [Claude API 报 400「thinking blocks cannot be modified」或「Invalid signature in thinking block」怎么办：原样回传思考块、redacted_thinking 与改了历史逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-thinking-blocks-cannot-be-modified-fix/)
- [Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)
- [Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」怎么办：漏回结果、中间插了消息、文本放在结果前逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-tool-use-without-tool-result-fix/)
- [Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-404-not-found-error-fix/)
- [Claude API 报 429 rate_limit_error 怎么办：RPM、ITPM、OTPM 限流、月度消费上限与加速限制怎么区分](https://a37836323.github.io/openlux-api-guides/news/claude-api-429-rate-limit-error-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

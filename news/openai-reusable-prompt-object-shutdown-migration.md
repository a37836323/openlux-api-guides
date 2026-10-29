---
layout: default
title: "OpenAI 可复用提示词 11 月 30 日停用：Responses 请求里的 prompt 参数怎么改成代码内提示词"
description: "OpenAI 可复用提示词对象和 v1/prompts 计划于 2026-11-30 停用。本文按官方迁移指南说明如何把 Responses 请求里的 prompt（ID、version、variables）改成代码内提示词：显式写 model 和 input、变量改函数参数、版本交给 git，并给出排查表和验证步骤。"
permalink: /news/openai-reusable-prompt-object-shutdown-migration/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[OpenAI API 文档：Migrate from prompt objects](https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object)

# OpenAI 可复用提示词 11 月 30 日停用：Responses 请求里的 prompt 参数怎么改成代码内提示词

先说结论：OpenAI 已宣布弃用 API 里的可复用提示词对象（reusable prompt objects），`v1/prompts` 计划在 **2026 年 11 月 30 日**停用。如果你的代码在调用 Responses API 时传的是 `prompt`（带提示词 ID、`version`、`variables`），而不是自己写 `model` 和 `input`，就要在停用前把提示词内容搬进自己的代码，改成直接传 `input`（以及需要时传 `instructions`）。官方迁移指南：[Migrate from prompt objects](https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object)。

本文适用于：用 Responses API 调用控制台里保存的提示词的项目。只用 `model` + `input` / `messages` 直接发请求、从没用过提示词对象（包括 `v1/prompts` 接口）的项目，不受这次停用影响。

## 时间线和影响范围

以下内容来自 OpenAI [弃用页面](https://developers.openai.com/api/docs/deprecations#2026-06-03-reusable-prompts)和迁移指南：

| 日期 | 官方说明 | 对你的影响 |
|---|---|---|
| 2026-06-03 | 宣布弃用，平台上弱化提示词创建入口 | 新项目不应再依赖提示词对象 |
| 2026-11-30 | `v1/prompts` API 和可复用提示词对象计划停用 | 仍按提示词 ID 发请求的代码需要在此之前改完 |
| 替代方案 | 把可复用提示词内容移到应用代码里 | 改成自己拼 `input` 消息 |

弃用页面对停用的一般定义是：到停用时间后，相应模型或接口将无法再访问。官方没有写明停用后请求具体返回哪种错误，所以不要等出现报错再改，按上表日期提前迁移。

## 先确认你的代码有没有用到提示词对象

在代码库里搜下面这些特征，命中任何一条都需要迁移：

1. 调用 `responses.create` 时传了 `prompt=`（或 JSON 里有 `"prompt": {...}`）。
2. `prompt` 里有提示词 ID（官方示例中形如 `pmpt_123`），以及 `version`、`variables`。
3. 请求里没有写 `model` 和 `input`。官方迁移指南的“迁移前”示例就是这样：只传 `prompt`，不写 `model`、`input`；“迁移后”的示例则显式写了 `model` 和 `input`。

字段名提醒：Responses API 参考文档里，`prompt` 对象的提示词 ID 字段叫 `id`，另有可选的 `version` 和 `variables`；迁移指南的 Python 和 curl 示例写的是 `prompt_id`。排查时两种写法都要搜一下。

## 迁移步骤：把 prompt 对象改成 input 消息

**第 1 步：把提示词正文搬进代码。** 在控制台（dashboard）里找到线上实际使用的那个提示词版本，把内容复制到代码仓库，按官方建议放进一个小的 `prompts/` 模块，每个提示词写成一个有名字的构建函数，不要把提示词零散地写在各处。

**第 2 步：把 `variables` 换成函数参数。** 官方的说法是让动态值在应用里显式、有类型。原来 `variables` 里的 `customer_name`、`issue` 之类，改成构建函数的参数，在函数里拼进用户消息。参考文档写明 `variables` 的值除了字符串，还可以是图片、文件等输入类型；这类变量迁移后要按图片、文件输入的写法，作为消息内容放进 `input`。

**第 3 步：在请求里显式写 `model` 和 `input`。** 官方迁移后的示例（Python）：

```python
def build_support_prompt(customer_name, issue):
    return [
        {
            "role": "system",
            "content": "You are a helpful support assistant. Be concise, accurate, and friendly. Do not invent policy details.",
        },
        {
            "role": "user",
            "content": f"Customer name: {customer_name}. Issue: {issue}. Write a response to the customer.",
        },
    ]

response = client.responses.create(
    model="gpt-6-astra",
    input=build_support_prompt(
        customer_name="Acme",
        issue="billing question",
    ),
)
```

文本生成指南也写到，可以把生成好的 `instructions` 和 `input` 直接传给 Responses API。`instructions` 参数在参考文档里的定义是插入模型上下文的 system（或 developer）消息。

**第 4 步：把版本管理改到代码仓库。** 原来靠提示词 `version` 区分版本，迁移后用 git 提交、PR 审查和测试或评测来管理；需要灰度时，官方建议用自己的配置或功能开关控制。

**第 5 步：静态内容在前，动态内容在后。** 迁移指南特别提醒：提示词缓存命中依赖完全相同的前缀，所以不变的说明放前面，客户名、问题这类每次都变的内容放后面。

## 迁移时容易漏掉的地方

| 现象 | 可能原因 | 怎么处理 |
|---|---|---|
| 改完后请求没有指定模型 | 原来只传 `prompt`，没写 `model` | 按迁移后示例显式写 `model` |
| 输出风格和原来不一样 | 只搬了部分提示词正文，或拿错了版本 | 回到控制台核对线上实际使用的版本，逐段对照 |
| 用 `previous_response_id` 续聊后，系统规则不生效了 | 参考文档写明：配合 `previous_response_id` 时，上一次响应的 `instructions` 不会带到下一次 | 每次请求都重新传 `instructions` |
| 缓存命中率下降 | 动态内容放在了前面，前缀每次都不同 | 静态说明放前，动态值放后 |
| 搜代码没搜全 | 示例用 `prompt_id`，参考文档用 `id` | 两种写法都搜，再搜 `pmpt_` |

原提示词对象里除了正文还配置了哪些内容，官方迁移指南没有列出。迁移前请在控制台逐项对照，确认改写后的请求把需要的设置都带上了。

## 怎么验证迁移成功

1. **代码层面**：全仓库再搜一遍 `prompt=`、`"prompt"`、`prompt_id`、`pmpt_`，确认生产代码路径里已经没有按提示词 ID 发请求的调用。
2. **请求层面**：新请求里有 `model` 和 `input`，并且能正常返回结果（官方示例用 `response.output_text` 读取文本）。
3. **效果层面**：准备一组有代表性的输入，分别用旧方式和新方式跑一遍对比输出；官方建议把这类样例做成轻量评测数据，以后改提示词都先跑一遍。
4. **时间层面**：以上都在 2026 年 11 月 30 日之前完成，并留出回退时间。

如果项目量大，官方还给了用 Codex 自动迁移的方式：安装 OpenAI Developers 插件和 OpenAI Docs 技能后，在项目里执行 `$openai-docs update this project to store prompts in code instead of using a prompts object`。改完仍要人工审查并按上面的步骤验证。

## 通过 OpenAI 兼容中转调用时要注意什么

迁移后的请求就是普通的 Responses 请求：`model` + `input`（可加 `instructions`），不再依赖某个账号里保存的提示词 ID。走中转服务时，Base URL 填服务方给的 OpenAI 兼容地址，模型名以服务方在售列表为准，不要沿用提示词对象里的设置。以 OpenLux 为例，Responses 的 Base URL 是 `https://api.openlux.ai/v1`，`gpt-6-astra` 等模型以价格页在售列表为准；先用 `/v1/models` 确认地址和 Key 都正确，再发迁移后的请求。

## 小结

这次停用影响的是“按提示词 ID 调用”的写法：把提示词正文搬进代码，把 `variables` 换成函数参数，请求里显式写 `model` 和 `input`，版本交给 git 管理，静态内容放前面保住缓存。在 11 月 30 日前改完并验证，就不会受停用影响。

想用同一套 Responses 写法调用多家模型，可以 [注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-reusable-prompt-object-shutdown-migration&utm_content=footer)。

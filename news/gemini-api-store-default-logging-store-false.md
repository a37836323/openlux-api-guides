---
layout: default
title: "Gemini API 新项目默认保存请求怎么关：store=false 写法、AI Studio 日志设置，以及关掉后 previous_interaction_id 和后台执行不能用"
description: "2026-10-26 起新建的 Gemini API 付费项目默认保存 generateContent 请求（store=true）：按官方文档说明哪些项目受影响、日志保留 55 天与数据使用规则，怎么在请求里设 store=false（SDK 最低版本、REST 顶层字段）或在 AI Studio 设置面板关闭日志，以及 Interactions API 关掉存储后 previous_interaction_id 与后台执行不可用的处理和验证方法。"
permalink: /news/gemini-api-store-default-logging-store-false/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/logs-datasets)

# Gemini API 新项目默认保存请求怎么关：store=false 写法、AI Studio 日志设置，以及关掉后 previous_interaction_id 和后台执行不能用

从 2026 年 10 月 26 日起，新建的 Gemini API 付费项目调用 `generateContent`、`streamGenerateContent` 和 `batchGenerateContent` 时，默认会保存请求（`store=true`），和 Interactions API 的默认行为一致。这一天之前建的项目保持原来的设置不变。如果你的业务不希望 Google 侧保留提示词和回答，有两种关法：在单个请求里设 `store=false`，或者在 AI Studio 日志页的设置面板里把项目的日志关掉。请求里的设置优先于项目设置。

需要注意的是，Interactions API 关掉存储后，`previous_interaction_id` 接续多轮对话和后台执行（`background=true`）都不能用，要改成每次请求带上完整对话历史。

本文依据 Google 官方的 [Gemini API 更新日志](https://ai.google.dev/gemini-api/docs/changelog)、[日志与数据集文档](https://ai.google.dev/gemini-api/docs/logs-datasets)、[日志数据使用政策](https://ai.google.dev/gemini-api/docs/logs-policy)、[Interactions API 文档](https://ai.google.dev/gemini-api/docs/interactions) 和 [generateContent API 参考](https://ai.google.dev/api/generate-content)，适用于直接用自己的 Google 项目和 API Key 调用 Gemini API 的场景。

## 一、先判断你的项目受不受影响

官方日志文档对默认值的说法分三种情况：

| 你的情况 | Generate Content 系列的默认 | Interactions API 的默认 | 要不要处理 |
|---|---|---|---|
| 2026-10-26 及之后新建的付费项目 | 保存（`store=true`） | 保存 | 不想保存就按下文关掉 |
| 2026-10-26 之前建的项目 | 保持原设置：没在 AI Studio 开过就是不保存 | 保存 | Generate Content 一般不用动；用 Interactions 的要看第四节 |
| 免费层项目 | 官方写明日志存储只对付费层项目提供 | Interactions 对象在免费层保留 1 天 | 用 Interactions 的看第四节 |

日志覆盖的调用包括 `GenerateContent`、`BatchGenerateContent`、`StreamGenerateContent`、Interactions（Managed Agents 除外），以及通过 OpenAI 兼容端点发出的调用。官方同时列出不支持日志的情况：Imagen、Veo、嵌入模型、Gemini Robotics，含视频、GIF 或 PDF 的输入，以及公开预览阶段的 Agents。

## 二、保存下来的内容会怎样

按官方日志文档和数据使用政策：

- 日志默认保留 55 天，到期后标记删除；付费项目可以把保留期改成 7、14、28 或 55 天。
- 被你加入数据集（dataset）的日志不受保留期限制，不会自动过期。
- 日志只对你的 Google Cloud 项目可见，和滥用监控日志分开存放。
- 日志里的提示词和回答默认不用于产品改进或模型开发。只有你主动把日志作为反馈分享给 Google 时，分享的数据才可能用于改进 Google 的产品，并可能由人工审核员阅读和标注；官方提醒分享的数据里不要放个人、敏感或保密信息。
- 例外是仅限邀请的 Contributor Tier：项目开启它后，符合条件模型的数据按「Unpaid Services」条款使用。

所以「默认保存」主要影响的是数据在 Google 侧留存多久、合规上能不能接受，而不是默认拿去训练。是否需要关闭，按你自己的合规要求决定。

## 三、方法一：在请求里设 store=false

官方说明请求级的 `store` 优先于项目级设置。用 SDK 时，Generate Content 系列把 `store` 放在 `config` 里，并且需要不低于下面的版本：Python `google-genai` 2.33.0、JS `@google/genai` 2.31.0、Java `google-genai` 1.79.0、Go `google.golang.org/genai` 1.76.0。

Python 写法（官方文档给的是 `config={'store': False}`）：

```python
from google import genai

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="你好",
    config={"store": False},
)
```

直接调 REST 时，按 API 参考，`store` 是 `generateContent` 和 `streamGenerateContent` 请求体的顶层布尔字段，不在 `generationConfig` 里：

```json
{
  "contents": [{"parts": [{"text": "你好"}]}],
  "store": false
}
```

Interactions API 的 `store` 也是顶层参数，Python 写作 `client.interactions.create(..., store=False)`。

容易漏的地方：把 `store` 塞进 `generationConfig`；SDK 版本低于上面的最低版本；只改了主流程，重试、批处理、后台任务等其他调用路径没改。

## 四、方法二：在 AI Studio 设置面板关掉日志

打开 AI Studio 的 [日志页](https://aistudio.google.com/logs)，进入 **Settings** 面板，可以按项目开启或关闭存储，随时可以改。`generateContent` 和 Interactions API 的日志是两个独立开关，要分别看。同一个面板里也能调整保留期（7、14、28、55 天）。

关 Interactions 的开关前要想清楚：官方警告，关闭后 API 不再自动保存和取回对话历史（请求里显式设置了 `store` 的除外）。Interactions 文档写明：`store=false` 与后台执行不兼容，也不能再用 `previous_interaction_id` 接续下一轮。改成无状态用法后，要在每次请求里带上完整的对话历史。官方说明隐式缓存在有状态和无状态两种模式下都支持。

如果你的代码依赖 `previous_interaction_id` 或 `background=true`，可以只在 Generate Content 上关存储，Interactions 保持开启并缩短保留期（官方提醒，保留期变短可能影响取回过去的对话）；或者把多轮逻辑改成自己维护历史后再关。

## 五、怎么确认设置生效

1. 先看项目建立日期和付费层级，对照第一节的表格确认默认值。
2. 改完后用同一个项目的 Key 发一条测试请求，到 AI Studio 日志页对比改动前后新请求是否还会出现。官方说明项目至少要有一个有效的 API Key，日志才会显示。
3. 检查所有调用路径：SDK 版本是否达到最低要求、REST 请求体里 `store` 是否在顶层、批处理和重试代码是否同样带上了 `store=false`。
4. 用 Interactions 的，关掉存储后跑一遍多轮对话，确认代码已经改成每次带完整历史，没有再引用 `previous_interaction_id`，也没有开 `background=true`。

## 六、通过第三方服务调用时

上面的项目设置只对你自己的 Google 项目有效。通过第三方服务或中转调用 Gemini 时，请求用的是服务方的项目，项目级日志开关不归你控制，请求里的 `store` 字段会不会原样转发也取决于服务方，本文没有实测。对数据留存有要求时，先向服务方确认。

如果你想用一个同时支持 Gemini 原生接口和 OpenAI 兼容接口的地址来调用和对比，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-store-default-logging-store-false&utm_content=footer)。

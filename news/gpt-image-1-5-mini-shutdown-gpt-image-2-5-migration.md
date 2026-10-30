---
layout: default
title: "gpt-image-1.5、gpt-image-1-mini 将于 12 月 1 日下线：换成 gpt-image-2.5-sunburst / flare 要改哪些参数"
description: "OpenAI 将于 2026-12-01 移除 gpt-image-1.5、gpt-image-1-mini、chatgpt-image-latest。按官方弃用公告和 Images API 参考，说明换成 gpt-image-2.5-sunburst 或 gpt-image-2.5-flare 时 model、quality、size、background、input_fidelity 要怎么改，以及常见报错排查和验证步骤。"
permalink: /news/gpt-image-1-5-mini-shutdown-gpt-image-2-5-migration/
date: 2026-10-31
---

> 更新日期：2026-10-31 · 一手来源：[OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations)

# gpt-image-1.5、gpt-image-1-mini 将于 12 月 1 日下线：换成 gpt-image-2.5-sunburst / flare 要改哪些参数

结论先说：OpenAI 在弃用公告里写明，`gpt-image-1.5`（含快照 `gpt-image-1.5-2025-12-16`）、`gpt-image-1-mini` 和 `chatgpt-image-latest` 将于 **2026 年 12 月 1 日**从 API 移除，推荐替代是 `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare`。大多数调用只要把 `model` 换掉就能继续跑；需要额外检查的是 `quality`、`size`、`background`、`input_fidelity` 这几个参数，以及 Responses API 图片生成工具里的 `model` 字段。

本文只讲 Image API（`/v1/images/generations`、`/v1/images/edits`）和 Responses API 图片生成工具的迁移，依据是 OpenAI 的[弃用公告](https://developers.openai.com/api/docs/deprecations#2026-06-02-gpt-image-model-deprecations)、[图片生成指南](https://developers.openai.com/api/docs/guides/image-generation)和 Images API 参考。另外提醒：`gpt-image-1` 已于 2026 年 10 月 23 日停用，还在用它的请求应直接迁到 2.5。

## 哪些模型受影响、什么时候停

| 现在用的模型 | 官方移除日期 | 官方推荐替代 |
|---|---|---|
| `gpt-image-1.5`、`gpt-image-1.5-2025-12-16` | 2026-12-01 | `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare` |
| `gpt-image-1-mini` | 2026-12-01 | `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare` |
| `chatgpt-image-latest` | 2026-12-01 | `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare` |
| `gpt-image-1` | 已于 2026-10-23 停用 | `gpt-image-2.5-sunburst` 或 `gpt-image-2.5-flare` |

`gpt-image-1.5` 的模型页已标为 Deprecated。在移除日期之前旧模型仍可调用，但建议现在就完成切换和验证，不要等到 12 月 1 日请求失败才改。

## Sunburst 还是 Flare：怎么选

两个模型都是 2026 年 9 月 8 日发布的（OpenAI 更新日志），默认快照分别是 `gpt-image-2.5-sunburst-2026-09-08` 和 `gpt-image-2.5-flare-2026-09-08`。官方的定位是：

- **Sunburst**：「最强的图片生成与编辑模型」，适合对**编辑精度**要求最高的流程，例如局部修改、按参考图改图。
- **Flare**：最快的高质量日常出图模型，适合批量生成、草图、对速度敏感的场景。

两者支持的接口相同：`/v1/images/generations`、`/v1/images/edits`、`/v1/batch`，都不能直接在 `/v1/chat/completions` 或 `/v1/responses` 里当作主模型使用（在 Responses API 里要放进图片生成工具，见下文）。两者 token 单价相同，与 GPT Image 2 一致，但官方特别说明「单价相同不等于每张图成本相同」，不同模型、不同质量档的 token 消耗会不一样，要用返回里的 `usage` 实测。

如果拿不准，可以先用 Flare 跑一轮现有提示词，对编辑结果不满意的流程再换 Sunburst。

## 迁移时要改的参数对照

下表的「旧模型」指 `gpt-image-1.5` / `gpt-image-1-mini`，内容来自 Images API 参考和图片生成指南：

| 参数 | 旧模型 | gpt-image-2.5-sunburst / flare | 迁移做法 |
|---|---|---|---|
| `model` | `gpt-image-1.5` 等 | `gpt-image-2.5-sunburst` / `gpt-image-2.5-flare` | 必改；生成接口要求显式指定模型 |
| `quality` | `low`、`medium`、`high`、`auto` | 新增 `xhigh`、`max`，默认 `auto` | 原值可沿用；`xhigh`、`max` 只在 2.5 上可用 |
| `size` | 标准尺寸 `1024x1024`、`1536x1024`、`1024x1536` | 标准尺寸都支持，另外支持自定义 `宽x高`（参考文档只把自定义尺寸列给 `gpt-image-2` 和 2.5） | 用自定义尺寸时按下面的限制检查 |
| `background` | 同一参数，取值 `transparent`、`opaque`、`auto` | 参考文档写明支持 `opaque` 和 `transparent` | 用 `transparent` 时 `output_format` 要设为 `png` 或 `webp`（`jpeg` 不支持透明） |
| `input_fidelity` | 1.5 支持 `high`/`low`；1-mini 只支持 `low`；默认 `low` | 参考文档未写明 2.5 的支持情况 | 见下方「编辑请求」一节 |
| `markup`（编辑接口） | 无 | 新增，参考文档写明支持 GPT Image 2.5 和 2.6 | 可选；不能和 `mask` 同时用 |
| `response_format` | GPT 图片模型不支持 | 同样不支持 | 始终返回 base64，读 `data[0].b64_json` |
| `user` | 已弃用 | 已弃用 | 改传 `safety_identifier`（不超过 128 字符） |

**自定义尺寸的限制**（2.5 与 `gpt-image-2` 相同）：宽和高都必须是 16 的倍数；宽高比在 1:3 到 3:1 之间；单边不超过 3840 像素，最大支持 `3840x2160`；总像素在 655,360 到 8,294,400 之间。超过 `2560x1440` 的分辨率官方标注为实验性。例如 `1536x864` 符合要求，`1000x1000`（不是 16 的倍数）就不符合。

**编辑请求（`/v1/images/edits`）**：一次最多 16 张输入图。旧代码里如果写了 `input_fidelity: "high"`，要注意参考文档只写了它在 `gpt-image-1.5`、`gpt-image-1-mini` 上的取值，以及 `gpt-image-2` 要求省略这个参数，没有写 2.5 是否接受。迁移后如果编辑请求因为这个参数报参数错误，先去掉 `input_fidelity` 再试，再用实际出图对比面部、细节保留是否满足要求。

## Responses API 里的改法

如果你不是直接调 Image API，而是在 Responses API 里让对话模型调用图片生成工具，模型名要改在**工具的 `model` 字段**，顶层 `model` 仍然是支持该工具的主模型。官方写法如下（主模型名以你账号可用的为准）：

```json
{
  "model": "gpt-6-astra",
  "input": "Generate an image of gray tabby cat hugging an otter with an orange scarf",
  "tools": [{ "type": "image_generation", "model": "gpt-image-2.5-sunburst" }]
}
```

生成结果在 `output` 里 `type` 为 `image_generation_call` 的项，`result` 是 base64 图片数据。两点注意：

1. Responses API 请求除了图片生成费用，还会计入主模型的 token 用量。
2. 对 GPT Image 2 和 2.5，缓存输入价只适用于 Responses API 的图片生成工具，直接调用 Images API（包括 `/v1/images/edits`）不享受；而且缓存命中的 token 数不会出现在返回的 `usage` 里，无法用 `usage` 核对。

## 迁移后常见报错与排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 12 月 1 日后旧模型请求失败 | `gpt-image-1.5`、`gpt-image-1-mini`、`chatgpt-image-latest` 已移除 | 把 `model` 换成 2.5 两个模型之一；搜一遍配置文件、环境变量和 Batch 任务文件里的旧模型名 |
| 带 `quality: "xhigh"` 或 `"max"` 的请求出错 | 参考文档只把这两档列给 2.5 两个模型 | 旧模型改回 `high`，或先切到 2.5 |
| 自定义 `size` 被拒绝 | 不是 16 的倍数、宽高比超出 1:3～3:1、像素总数或边长超限 | 按上一节限制调整，或先用 `1024x1024` 等标准尺寸 |
| 透明背景请求报错或没有透明效果 | `background: "transparent"` 配了 `jpeg` | 改成 `output_format: "png"` 或 `"webp"` |
| 想拿图片 URL 却拿不到 | GPT 图片模型不支持 `response_format`，只返回 base64 | 解码 `b64_json` 后自己存储或上传 |
| 返回 `error.type = "image_generation_user_error"` | 属于需要修改请求的用户侧错误，例如 `error.code = "moderation_blocked"` | 不要原样自动重试；看 `error.moderation_details.moderation_stage`（`input`、`output` 或 `unknown`）判断是提示词/输入图还是生成结果被拦，再修改输入 |
| 首次调用 GPT 图片模型被拒 | 官方说明可能需要先完成 API 组织验证（Organization Verification） | 在开发者控制台完成组织验证后重试 |

其余鉴权、额度、限流、服务端错误按通用 API 错误处理：记录 request ID，限流和服务端错误带退避重试，额度错误不要自动重试。

## 验证方法与成功标准

切换后按下面三步确认：

1. **最小请求**：用官方示例的形式发一次生成请求，先用低质量和标准尺寸降低耗时：

```bash
curl -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-type: application/json" \
  -d '{"model": "gpt-image-2.5-flare", "prompt": "A red apple on a white table", "quality": "low", "size": "1024x1024"}' \
  | jq -r '.data[0].b64_json' | base64 --decode > apple.png
```

   成功标准：HTTP 200，`apple.png` 能正常打开。

2. **核对返回字段**：Images API 的返回对象可能带 `quality`、`size`、`background` 字段（参考文档列为可选字段），有的话确认它们和你请求的值一致；传 `auto` 时可以从这里看模型实际选了什么。
3. **对比成本和效果**：用同一批提示词分别跑旧模型和新模型，记录 `usage` 里的 token 数和出图效果，再决定生产环境用 Sunburst 还是 Flare、用哪一档 `quality`。Batch 任务也要用新模型名重新提交一次小批量验证。

## 小结

- 截止日期：2026-12-01，`gpt-image-1.5`、`gpt-image-1-mini`、`chatgpt-image-latest` 移除；`gpt-image-1` 已停。
- 必改：`model`（Image API 直接改，Responses API 改工具里的 `model`）。
- 需检查：自定义 `size` 的限制、透明背景配 `png`/`webp`、编辑请求里的 `input_fidelity`、`user` 改 `safety_identifier`。
- 可选新能力：`xhigh`、`max` 质量档，编辑接口的 `markup` 参数。

一手来源：[OpenAI 弃用公告：GPT Image model deprecations](https://developers.openai.com/api/docs/deprecations#2026-06-02-gpt-image-model-deprecations)、[图片生成指南](https://developers.openai.com/api/docs/guides/image-generation)、[Images API 编辑接口参考](https://developers.openai.com/api/reference/resources/images/methods/edit)、[GPT Image 2.5 Sunburst 模型页](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)、[GPT Image 2.5 Flare 模型页](https://developers.openai.com/api/docs/models/gpt-image-2.5-flare)。

如需通过中转调用 GPT 图片模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-image-1-5-mini-shutdown-gpt-image-2-5-migration&utm_content=footer)，在售模型和支持的接口以价格页为准。

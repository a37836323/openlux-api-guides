---
layout: default
title: "gemini-3.1-flash-image 已弃用：换成 gemini-nano-banana-2.1 要改哪些（512 分辨率、image_size 大写 K、思考档位）"
description: "gemini-3.1-flash-image（Nano Banana 2）2026-10-06 起弃用、未公布关停日期，官方替代模型是 gemini-nano-banana-2.1。按官方文档说明迁移要改的地方：模型名、2.1 不支持 512 分辨率、image_size 必须大写 K、默认思考档位从 minimal 变为 medium，附排查表和按像素尺寸验证的方法。"
permalink: /news/gemini-3-1-flash-image-deprecated-nano-banana-2-1-migration/
date: 2026-10-30
---

> 更新日期：2026-10-30 · 一手来源：[Google Gemini API 官方文档](https://ai.google.dev/gemini-api/docs/changelog)

# gemini-3.1-flash-image 已弃用：换成 gemini-nano-banana-2.1 要改哪些（512 分辨率、image_size 大写 K、思考档位）

结论先说：Google 在 2026-10-06 的 [Gemini API 发布说明](https://ai.google.dev/gemini-api/docs/changelog) 里宣布 `gemini-3.1-flash-image`（Nano Banana 2）弃用，暂未公布关停日期，替代模型是 `gemini-nano-banana-2.1`（Nano Banana 2.1）。迁移时最少要做三件事：把模型名换掉；原来用 512 分辨率的改成 1K 及以上（2.1 不支持 512）；决定思考档位要不要显式写成 `minimal`（2.1 默认是 `medium`，旧模型默认是 `minimal`）。宽高比、参考图数量、输入输出 token 上限两者一致，不用改。

本文适用于直接调用 Gemini API（Interactions 或 generateContent）生成图片的代码。原来用 `gemini-2.5-flash-image` 的不在本文范围，官方给它的迁移建议是 Nano Banana 2 Lite（`gemini-3.1-flash-lite-image`），那个模型只支持 1K。以下信息截至 2026-10-30。

## 一、旧模型现在是什么状态

[Gemini 弃用页](https://ai.google.dev/gemini-api/docs/deprecations) 对 `gemini-3.1-flash-image` 的记录是：发布于 2026-05-28，关停日期「No shutdown date announced」，替代模型 `gemini-nano-banana-2.1`。弃用页同时说明，表里的关停日期只是最早可能下线的日期。

要注意的是，同一页对 `gemini-3.7-flash`、`gemini-3.5-flash` 明确写了「请求会自动转到新模型」，而对 `gemini-3.1-flash-image` 没有这样写。所以不要假设旧模型名会被自动换成 2.1，迁移需要自己改代码；也正因为没有关停日期，可以先在测试环境把下面几项改完、对比出图效果再切换。

## 二、两个模型的差别一览

下表来自官方[图片生成指南](https://ai.google.dev/gemini-api/docs/image-generation)和两个模型的规格页：

| 项目 | gemini-3.1-flash-image（旧） | gemini-nano-banana-2.1（新） |
|---|---|---|
| 输出分辨率 | 512、1K、2K、4K，默认 1K | 1K、2K、4K，默认 1K，**不支持 512** |
| 思考档位 | minimal、high，默认 minimal | minimal、medium、high，默认 medium |
| 宽高比 | 1:1、1:4、4:1、1:8、8:1、2:3、3:2、3:4、4:3、4:5、5:4、9:16、16:9、21:9 | 同左 |
| 参考图 | 最多 14 张（人物最多 4 个、物体最多 10 个） | 同左 |
| 输入 / 输出 token 上限 | 131,072 / 32,768 | 同左 |
| 函数调用、结构化输出、缓存 | 不支持 | 不支持 |
| 搜索 grounding（网页 + 图片搜索） | 支持 | 支持 |

2.1 的模型页还写明修复了宽幅和全景比例（1:4、4:1、1:8、8:1）在 2K、4K 下的拼接痕迹（tiling artifacts）。如果你之前因为这个问题回避这些比例，迁移后可以重新测试。

## 三、第一步：换模型名，去掉 512 分辨率

模型名直接从 `gemini-3.1-flash-image` 改成 `gemini-nano-banana-2.1`。

然后检查代码里的分辨率参数：

- Interactions 接口写在 `response_format` 里：`{"type": "image", "image_size": "..."}`。
- generateContent 接口写在 `generationConfig.imageConfig.imageSize`，[API 参考](https://ai.google.dev/api/generate-content)列出的取值是 `512`、`1K`、`2K`、`4K`，不填默认 1K。

图片生成指南明确写了 512px 只有 3.1 Flash Image 提供、2.1 不支持，所以原来填 `512` 的要改成 `1K`（或更高）。按官方分辨率表，同一宽高比下 512 档每张图计 747 个 token，1K 档计 1120 个，所以改完后单张图的输出 token 会增加，费用以官网价格页为准。1K、2K、4K 三档在两个模型上的像素和 token 数相同。

## 四、第二步：image_size 必须用大写 K

官方原话是必须使用大写的「K」（`1K`、`2K`、`4K`），小写（如 `1k`）会被拒绝。迁移时如果改动了分辨率参数，顺带检查一遍；从配置文件或用户输入读取分辨率的代码，最好在发请求前统一转成大写。

另外，generateContent 的 API 参考写明：给不支持图片配置的模型设置 `imageConfig` 会返回错误。如果改完后报的是这类错误，先核对模型名是否拼错，或者是否误填成了文本模型（例如 `gemini-3.8-flash`）。

## 五、第三步：决定思考档位

图片生成指南写明，Gemini 3 图片模型的思考默认开启，API 里无法关闭；思考过程中最多生成两张中间图，这些中间图不收费，但官方说明思考模型默认会对思考 token 计费。

关键变化在默认值：旧模型默认 `minimal`，2.1 默认 `medium`。如果代码里原来没写思考档位，换模型后实际用的档位会从 minimal 变成 medium，出图耗时和 token 用量可能随之变化。想先贴近原来的行为，就显式写 `minimal`，测完效果再决定要不要提高：

```python
interaction = client.interactions.create(
    model="gemini-nano-banana-2.1",
    input=prompt,
    response_format={"type": "image", "aspect_ratio": "16:9", "image_size": "2K"},
    generation_config={"thinking_level": "minimal"},
)
```

用 generateContent 的，对应字段是 `generationConfig.thinkingConfig.thinkingLevel`，枚举值为 `MINIMAL`、`MEDIUM`、`HIGH` 等。原来写的是 `high` 的不用改，2.1 同样支持。

## 六、按现象排查

| 现象 | 可能原因 | 改法 |
|---|---|---|
| 换模型名后请求被拒，请求里分辨率是 512 | 2.1 不支持 512 | 改成 `1K` |
| 分辨率参数被拒 | 写成了小写 `1k`、`2k` | 改成大写 `1K`、`2K` |
| 报错提示不支持图片配置 | 模型名拼错或填成了非图片模型 | 核对模型名为 `gemini-nano-banana-2.1` |
| 没改别的参数，出图变慢、用量变多 | 默认思考档位从 minimal 变成 medium | 显式设为 `minimal` 再对比 |
| 想继续用 512 小图做预览 | 2.1 没有这一档 | 改用 1K；旧模型已弃用，只适合过渡期临时使用 |

## 七、改完怎么验证

1. 用改好的参数发一个最小请求，例如宽高比 `16:9`、分辨率 `2K`。
2. 把返回的图片保存下来，看像素尺寸：按官方表，2.1 在 16:9、2K 下应为 2752x1536，1K 下应为 1376x768。尺寸对得上，说明分辨率和宽高比参数都生效了。
3. 用同一批提示词分别在 `minimal` 和默认档位各跑几次，比较耗时、返回的用量字段和画面效果，再决定线上用哪一档。

## 八、通过中转调用时

OpenLux 的价格接口里，`gemini-nano-banana-2.1` 和 `gemini-3.1-flash-image` 都在售，`supported_endpoint_types` 标注为 `gemini` 和 `openai`。走 Gemini 原生接口时，Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，Key 放在 `x-goog-api-key` 请求头里，Key 在控制台「令牌」页创建。官方图片生成指南的示例都是 Interactions 写法，经中转调用时建议按上面 generateContent 的 `imageConfig`、`thinkingConfig` 字段来改；中转对 Interactions 接口的支持本文没有核实，以实际返回为准。

想用同一个 Key 同时测试新旧两个图片模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-3-1-flash-image-deprecated-nano-banana-2-1-migration&utm_content=footer)。

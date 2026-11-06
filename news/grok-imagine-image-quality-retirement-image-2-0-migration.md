---
layout: default
title: "grok-imagine-image-quality 11 月 2 日退役：请求会转到 grok-imagine-image-2.0 的 low 档，要不要改 model 和 quality"
description: "xAI 的 grok-imagine-image-quality 于 2026-11-02 退役：按官方迁移指南说明请求会转到 grok-imagine-image-2.0 并固定 quality=low，生成和编辑都受影响；如何改 model、选 low/medium/auto、核对 n/aspect_ratio/resolution/response_format，并用响应 model 字段验收。"
permalink: /news/grok-imagine-image-quality-retirement-image-2-0-migration/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[xAI 迁移指南](https://docs.x.ai/developers/migration/imagine-image-quality-nov-2)

# grok-imagine-image-quality 11 月 2 日退役：请求会转到 grok-imagine-image-2.0 的 low 档，要不要改 model 和 quality

如果你的代码里还写着 `grok-imagine-image-quality`（或 `grok-imagine-image-pro`），结论先说：2026 年 11 月 2 日之后请求不会断，xAI 会把它交给 `grok-imagine-image-2.0` 处理，并把 `quality` 固定为 `low`，请求和响应结构都不变。代码不改也能跑，但画质档位就不由你决定了。想自己选档，就把 `model` 改成 `grok-imagine-image-2.0`，再显式传 `quality`。`grok-imagine-image`（1.0）不受这次变更影响。

以上依据是 xAI 官方的 [grok-imagine-image-quality 迁移指南](https://docs.x.ai/developers/migration/imagine-image-quality-nov-2) 和更新日志。本文按官方说明整理影响范围、改法、参数核对和验收步骤，适合直接调用 xAI 图片生成、图片编辑接口的开发者。

## 一、先确认你受不受影响

在代码、配置文件和环境变量里搜一下模型名，对照下表：

| 你现在用的 model | 11 月 2 日之后 | 建议 |
|---|---|---|
| `grok-imagine-image-quality` | 由 `grok-imagine-image-2.0` 处理，`quality` 为 `low`，生成和编辑都一样 | 主动改成 2.0，并自己选 `quality` |
| `grok-imagine-image-pro` | 官方说它本来就转到 quality 模型，所以同样落到 2.0 的 `low` | 同上 |
| `grok-imagine-image`（1.0） | 不受影响 | 不用改 |
| `grok-imagine-image-2.0` | 不变 | 检查有没有显式传 `quality`，没传就是 `auto` |

搜不到也不用担心，可以看线上响应：迁移指南写明，响应里的 `model` 字段报告的是**实际处理这次请求的模型**。11 月 2 日之后，如果你发的是旧名，返回的 `model` 应该变成 2.0，日志里就能确认有没有被转发。

## 二、退役后什么会变、什么不变

| 项目 | 官方说法 |
|---|---|
| 旧模型名能不能继续用 | 能，官方说为了避免中断不需要改代码 |
| 请求和响应结构 | 不变 |
| 实际处理请求的模型 | `grok-imagine-image-2.0`，响应 `model` 字段会如实显示 |
| 画质档位 | 固定 `low`；转发同时覆盖 `/v1/images/generations` 和 `/v1/images/edits` |
| 计费 | 仍发旧名的请求按 2.0 `low` 计费；官方说 2.0 `low` 在每档分辨率下单价都比旧模型低，具体数字以 xAI 价格页为准 |
| 通知期 | 官方从 2026 年 9 月 2 日开始提前 60 天通知 |

编辑场景要多留意一点：走转发时，编辑请求也是 `low`；而直接调用 2.0 又不传 `quality` 时，默认的 `auto` 在编辑上按 `medium` 出图。也就是说，「什么都不改」和「改了 model 但不传 quality」，编辑请求得到的档位不一样，计费也跟着不一样。

## 三、怎么改：一行 model，再加一个可选的 quality

官方把迁移描述为改一行 `model` 字段，`quality` 按需加。`quality` 有三个取值：

| 取值 | 官方说明 | 适合 |
|---|---|---|
| `low` | 转发时用的就是这一档；官方称它成本最接近旧模型 | 想控制成本、量大的批量出图 |
| `medium` | 每张图用更多算力，细节更好 | 画质比成本更重要的场景 |
| `auto` | 省略 `quality` 时的默认值；目前生成用 `low`、编辑用 `medium` | 能接受档位随官方调整、按实际档位计费 |

官方写明：图片**按实际出图的档位计费**；要锁定档位，就显式传 `low` 或 `medium`。另外，官方写明 `quality` 参数**只支持 `grok-imagine-image-2.0`**，给其它模型传它不在官方支持范围内，所以改 `quality` 之前先确认 `model` 已经是 2.0。

用 curl 直接调用的写法：

```bash
curl https://api.x.ai/v1/images/generations \
  -H "Authorization: Bearer $XAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "grok-imagine-image-2.0", "prompt": "A watercolor painting of a lighthouse at dawn", "quality": "medium"}'
```

用 OpenAI Python SDK 时，官方示例把 `quality` 放进 `extra_body`：

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
resp = client.images.generate(
    model="grok-imagine-image-2.0",
    prompt="A watercolor painting of a lighthouse at dawn",
    extra_body={"quality": "medium"},
)
print(resp.data[0].url)
```

图片编辑接口 `/v1/images/edits` 的改法相同：换 `model`，按需传 `quality`。

## 四、顺手核对其它出图参数

既然要改请求，可以把 2.0 的其它参数一起对一遍（取值来自 xAI 图片生成文档）：

| 参数 | 取值 | 省略时 |
|---|---|---|
| `n` | `1`～`10` | `1` |
| `aspect_ratio` | `1:1`、`16:9`/`9:16`、`4:3`/`3:4`、`3:2`/`2:3`、`2:1`/`1:2`、`19.5:9`/`9:19.5`、`20:9`/`9:20`、`21:9`、`5:2`、`auto` | `auto`，由模型按提示词选 |
| `resolution` | `1k`、`2k` | `1k` |
| `response_format` | `url`、`b64_json` | `url`，返回的是临时地址 |
| `deferred` | `true` 时先返回 `request_id`，再轮询 `GET /v1/images/{request_id}` | 不开启 |

几点说明：

- 用 OpenAI Python SDK 时，`aspect_ratio`、`resolution` 也和 `quality` 一样通过 `extra_body` 传。
- 返回的 URL 会过期，拿到后要尽快下载或处理；需要长期保存就自己存一份，或改用 `b64_json`。
- 延迟模式只支持 `url` 格式，结果保留 24 小时；轮询时 `pending` 返回 HTTP 202，`done` 和 `failed` 返回 HTTP 200，失败时 `error` 里带 `code` 和 `message`。

## 五、常见现象与排查

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 11 月 2 日之后出图细节或风格和以前不一样 | 旧名已被转到 2.0 的 `low` 档 | 改成 2.0，用同一批提示词对比 `low` 和 `medium` 后再定档 |
| 监控、对账脚本按模型名匹配，突然对不上 | 响应 `model` 字段报告实际处理模型，变成了 2.0 | 把 `grok-imagine-image-2.0` 加进匹配规则 |
| 传了 `quality`，出图档位和预期不符 | `quality` 只支持 2.0；`model` 可能还是 1.0，或还在用旧名（转发时官方固定为 `low`） | 检查实际发出去的 `model`，改成 2.0 再传 |
| 改成 2.0 后编辑请求的费用和生成不一样 | 没传 `quality`，`auto` 在编辑上按 `medium` 出图并计费 | 想固定成本就显式传 `low` |
| Python 里不知道 `quality`、`resolution` 往哪放 | 官方示例通过 `extra_body` 传 | 按第三节的写法 |
| 图片 URL 过一阵打不开 | 默认返回的是临时地址 | 及时下载，或改用 `b64_json` |

## 六、改完怎么验收

1. **代码里没有旧名**：全局搜索 `grok-imagine-image-quality` 和 `grok-imagine-image-pro`，结果应为零。
2. **响应确认**：抽几条生成请求和编辑请求，响应里的 `model` 应为 `grok-imagine-image-2.0`。
3. **档位是显式的**：每类请求（生成、编辑）都传了你选定的 `quality`，不依赖 `auto` 的默认行为。
4. **画质和成本过一遍**：用固定的一组提示词分别跑 `low` 和 `medium`，人工看图，再对照官方价格页估算单价，决定线上用哪档。
5. **存储链路**：如果用 `url`，确认下载步骤在地址过期前完成。

五项都满足，迁移就算完成：之后的画质档位由你自己选定，不再依赖转发时的默认值。

## 七、通过 OpenLux 调用时

按 OpenLux 价格接口 11 月 1 日的快照，`grok-imagine-image-quality` 和 `grok-imagine-image-2.0` 都在列，接口类型标注为图片生成和图片编辑。模型名以价格页在售列表为准，价格也请以官网价格页为准。`quality` 这类扩展参数，建议先发一次小请求，看返回结果符合预期后再放量。需要账号的话，可以[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=grok-imagine-image-quality-retirement-image-2-0-migration&utm_content=footer)。

## 官方来源

- xAI 迁移指南：https://docs.x.ai/developers/migration/imagine-image-quality-nov-2
- xAI 图片生成文档：https://docs.x.ai/developers/model-capabilities/images/generation
- xAI 更新日志：https://docs.x.ai/docs/release-notes

## 同专题文章

- [Cosmos3-Sim-Bimanual 如何用 vLLM-Omni 推理？59 个动作控制值怎么补齐、如何与输入帧对齐？](https://a37836323.github.io/openlux-api-guides/news/cosmos3-sim-bimanual-vllm-omni-inference/)
- [Transformers 如何调用 Phonon TTS？先核对模型许可和版本](https://a37836323.github.io/openlux-api-guides/news/hugging-face-phonon-transformers-integration/)
- [Transformers 模型能在 AWS Trainium2 上运行吗？torch-neuronx 编译失败或首次运行过慢怎么排查](https://a37836323.github.io/openlux-api-guides/news/check-transformers-model-trainium-support/)
- [Pinecone 报 Vector dimension does not match 怎么办？](https://a37836323.github.io/openlux-api-guides/news/pinecone-vector-dimension-mismatch-fix/)
- [API 用量和账单为什么对不上：时间窗口、计费单位与重试记录核对](https://a37836323.github.io/openlux-api-guides/news/api-usage-billing-reconciliation-workflow/)
- [工具调用返回了参数却执行失败：函数名、字段和业务范围怎么校验](https://a37836323.github.io/openlux-api-guides/news/tool-call-arguments-validation-contract/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

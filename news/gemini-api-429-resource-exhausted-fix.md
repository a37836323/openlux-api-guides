---
layout: default
title: "Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写"
description: "Gemini API 返回 429 RESOURCE_EXHAUSTED 时，按官方速率限制与排错文档区分 RPM、TPM、每日配额和 10 分钟消费限额，分清 402/403/503，并按官方建议写退避重试。"
permalink: /news/gemini-api-429-resource-exhausted-fix/
date: 2026-11-03
---

> 更新日期：2026-11-03 · 一手来源：[Google Gemini API 文档：Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)

# Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写

调用 Gemini API 返回 `429 RESOURCE_EXHAUSTED`，意思是**某一项限额被用完了**，不是请求写错。按 Google 官方的 [速率限制文档](https://ai.google.dev/gemini-api/docs/rate-limits)，限额至少有每分钟请求数（RPM）、每分钟输入 token（TPM）、每天请求数（RPD）三项，超过任意一项都会报错；付费项目另有按 10 分钟滚动窗口计算的消费限额，超了同样返回 `429 RESOURCE_EXHAUSTED`。

所以处理顺序是：先判断撞的是哪一项，再决定是等、是降并发、是缩短请求，还是升级档位。本文只用 Google 官方文档里的说法，适用于直接调用 Gemini API（AI Studio 的 Key）和经 OpenAI 兼容 / Gemini 原生中转调用两种情况，后者在文末单独说明。

## 先确认是不是 429：和 400、402、403、503 怎么区分

Gemini 的几个常见错误长得像，但处理办法完全不同。官方 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting) 的重试一节写明：`429`、`408` 和 `5xx` 属于临时错误，可以重试；`400`、`402`、`403` 代表 Key 有问题、预付额度用完或语法错误，**不要重试**。

| 状态码 | 含义（官方说法） | 能不能重试 | 该做什么 |
|---|---|---|---|
| 429 RESOURCE_EXHAUSTED | 速率限制、每日配额或消费限额用完 | 能，用指数退避 | 本文下面几节 |
| 503 UNAVAILABLE | 服务暂时过载或不可用 | 能，用指数退避 | 稍后重试 |
| 402 Payment Required | 预付（Prepay）额度用完 | 不能 | 充值或开自动续充，充值前请求都不会成功 |
| 403 PERMISSION_DENIED | 项目被拒绝访问，如免费档不可用、账单欠费、Key 泄露被封 | 不能 | 按 AI Studio 里的项目状态处理 |
| 400 FAILED_PRECONDITION | 前置条件不满足，例如账单未启用 | 不能 | 检查项目账单状态 |

要特别注意 402：计费文档写明，预付额度用完后，该结算账号下**所有项目的所有 Key 会同时停止工作**，请求返回 `402 Payment Required`，项目也不会自动降回免费档。这种情况下怎么重试都没用。

如果你用的是 Interactions API，[错误码参考](https://ai.google.dev/gemini-api/docs/api-errors) 把 429 拆成了三种 `code`，可以直接据此判断：

| error.code | 官方描述 | 官方建议 |
|---|---|---|
| `rate_limit_exceeded` | 超过每分钟或每秒的请求数或 token 限额 | 等待后用指数退避重试 |
| `quota_exceeded` | 超过每日配额 | 等配额重置，或申请提高配额 |
| `too_many_requests` | 短时间内请求过多 | 等待后用指数退避重试 |

## 撞的是哪一项限额：按现象对照

官方文档明确了几条规则，排查时最有用：

- **限额按项目算，不按 Key 算。** 原文是「Rate limits are applied per project, not per API key」。在同一个项目里多建几个 Key 并不会多出额度。
- **RPD 在太平洋时间午夜重置。** 换算成北京时间，冬令时是下午 16:00，夏令时是下午 15:00。
- **preview / experimental 模型限额更严。** 官方原话是「Rate limits are more restricted for experimental and preview models」，模型名带 `preview` 的限额比正式模型更严。
- **部分模型有额外维度。** 出图模型有每分钟图片数（IPM），部分模型有每天 token 数（TPD）。
- **联网搜索单独限额。** Gemini 3 及以后的模型使用 Grounding with Google Search，默认每个项目每天 1,500 次请求。
- **失败的请求也算配额。** 计费文档写明，返回 400 或 500 的请求不收 token 费用，但仍然计入配额。

据此对照现象：

| 现象 | 最可能撞的限额 | 怎么处理 |
|---|---|---|
| 并发一高就报，过一两分钟自己恢复 | RPM | 降低并发，加退避重试 |
| 请求次数不多，但每次上下文很长时报 | TPM | 缩短输入（裁历史、少传附件），或把请求打散到更长时间 |
| 一天到某个时间点后一直报，北京时间下午三四点后恢复 | RPD | 等重置；长期不够就升级档位或申请提额 |
| 付费项目，连续发几个很大的请求后报，等一会儿恢复 | 10 分钟消费限额 | 减少高成本请求，缩小上下文或缩短输出 |
| 只有带 Google 搜索的请求报 | 搜索 grounding 的每日次数 | 只在需要时开搜索 |
| 只有 preview 模型报，正式版正常 | preview 模型限额更严 | 业务允许的话换成正式版模型 |

## 到 AI Studio 查实际限额和档位

不要凭网上的数字猜。官方说法是：你当前生效的限额在 AI Studio 的 `https://aistudio.google.com/rate-limit` 页面查看，档位变化后会自动更新；当前所在档位在 AI Studio 的 Projects 页面看。官方还注明，标出的限额**不保证**，实际容量可能有差异。

档位和升级条件（以官方页面为准）：

| 档位 | 条件 | 每 10 分钟消费限额 |
|---|---|---|
| Free | 有活跃项目或在免费试用期 | 不适用 |
| Tier 1 | 绑定有效的结算账号 | 10 美元 |
| Tier 2 | 已付款 100 美元，且距首次成功付款满 3 天 | 200 美元 |
| Tier 3 | 已付款 1,000 美元，且距首次成功付款满 30 天 | 200 美元 |

几点容易误解的地方：

1. 升级是自动的。免费档升到 Tier 1 通常立即生效，之后的升级一般 10 分钟内生效；但满足条件也可能在审核后被拒。
2. Tier 2、Tier 3 看的是整个结算账号在 Google Cloud 上的总消费，不只是 Gemini。
3. 排错指南写明，项目升级到付费档**不会解锁免费档的配额**，付费后的用量按 Gemini API 价格计费。
4. 消费限额是否生效取决于账单历史和账号状况，不是每个项目都会撞到。
5. 如果撞到的是**结算账号级别的档位消费上限**，计费文档写的是该结算账号下所有项目的服务会暂停到下个账单周期开始（每月 1 日）。官方没有写明此时返回的错误码；这和 10 分钟窗口不同，等几分钟不会恢复。

付费档用户长期不够用，可以通过速率限制页面里的表单申请提额，官方说明会审核，但不保证一定提高。

## 重试怎么写：指数退避 + 随机抖动 + 次数上限

排错指南给出的做法：

- 官方 SDK（python-genai、js-genai、go-genai）已经内置指数退避重试，覆盖超时、网络问题和 `429`、`5xx`。其中 Python SDK 对临时错误**最多自动重试 4 次**，初始等待约 1 秒，最长等待 60 秒。如果在 SDK 外面再自己加重试，也要设次数上限。
- 自己用 REST 调用时：从约 1 秒开始，按 2 秒、4 秒、8 秒递增；加随机抖动，避免一批客户端同时重试；只重试 `429`、`408`、`5xx`；设置最大重试次数，防止死循环。

下面是按上述规则写的最小示例（REST 直连，`GEMINI_API_KEY` 从环境变量读取）：

```python
import os, random, time, requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
HEADERS = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
BODY = {"contents": [{"parts": [{"text": "你好"}]}]}

for attempt in range(5):
    r = requests.post(URL, headers=HEADERS, json=BODY, timeout=120)
    if r.status_code not in (408, 429) and r.status_code < 500:
        break
    if attempt < 4:
        time.sleep(min(60, 2 ** attempt) + random.random())
print(r.status_code, r.text[:300])
```

注意上面提到的规则：失败的请求也计入配额。如果是 RPD 用完了，重试只会继续失败，应该停下来等重置，而不是一直重试。

## 降低 429 的几个办法

都来自官方文档里的建议或限额规则：

| 办法 | 依据 | 适用 |
|---|---|---|
| 缩短上下文、限制输出长度 | 消费限额一节建议减少高成本请求 | TPM、10 分钟消费限额 |
| 降并发、匀速发送 | RPM 是每分钟计数 | RPM |
| 批量任务改用 Batch API | Batch 请求的限额和普通调用分开计算 | 大量离线任务 |
| 留意 priority inference 的单独限额 | 其限额默认是标准限额的 0.3 倍，且用量也计入总限额 | 使用优先推理的项目 |
| 只在需要时开 Google 搜索 | 搜索 grounding 默认每项目每天 1,500 次 | 带联网搜索的请求 |

## 经中转调用时要注意什么

如果你用的是中转 Key（例如 OpenLux），请求不经过你自己的 Google 项目，你 AI Studio 里的档位、限额页和账单状态**反映不了这些请求**，上面查 AI Studio 的步骤不适用。这时：

1. 先看返回的状态码和 `message` 原文，以中转实际返回为准，再按本文第一节判断是否该重试。
2. 重试规则不变：只重试 `429`、`408`、`5xx`，退避加抖动，设上限。
3. 排除地址和 Key 问题。OpenLux 的 Gemini 原生接口 Base URL 是 `https://api.openlux.ai`，请求路径为 `/v1beta/models/<模型>:generateContent`，Key 放在 `x-goog-api-key` 头或 `?key=` 查询参数；OpenAI 兼容接口 Base URL 是 `https://api.openlux.ai/v1`，用 `Authorization: Bearer`。Key 在控制台「令牌」页（`https://www.openlux.ai/console/token`）创建。Key 无效时返回 401 `Invalid token`。
4. 模型名只用价格页在售的 ID，并确认该模型支持你调用的接口类型（价格接口里的 `supported_endpoint_types`，Gemini 系列为 `gemini` 和 `openai`）。

最小验证（把 `$OPENLUX_KEY` 换成你的令牌）：

```bash
curl -s https://api.openlux.ai/v1beta/models/gemini-3.8-flash:generateContent \
  -H "x-goog-api-key: $OPENLUX_KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"hi"}]}]}'
```

返回里有 `candidates` 就说明地址、Key 和模型名都对。

## 怎么算解决了

- 按上面的对照表找到了撞的是哪一项限额，且在 AI Studio 限额页能对上（直连时）。
- 高峰期偶发的 429 能被退避重试吸收，最终返回 200。
- RPD 类 429 不再靠重试硬顶，而是在太平洋时间午夜重置后恢复，或升级档位后消失。
- 402、403 没有被当成 429 反复重试。

需要一个同时提供 Gemini 原生接口和 OpenAI 兼容接口的入口，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-429-resource-exhausted-fix&utm_content=footer)

## 同专题文章

- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)
- [Gemini 旧 TTS 预览模型最早 11 月 17 日下线：换成 gemini-3.8-flash-tts 要改哪些](https://a37836323.github.io/openlux-api-guides/news/gemini-tts-preview-shutdown-gemini-3-8-flash-tts-migration/)
- [gemini-3.1-flash-image 已弃用：换成 gemini-nano-banana-2.1 要改哪些（512 分辨率、image_size 大写 K、思考档位）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-image-deprecated-nano-banana-2-1-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了"
description: "Claude 提示缓存没命中、cache_read_input_tokens 一直为 0 时，用 9 月 23 日正式可用的 cache diagnostics 找出 model、system、tools 或 messages 哪里变了，并给出六种 cache_miss_reason 的改法和手动排查清单。"
permalink: /news/claude-prompt-cache-miss-diagnostics-fix/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[Claude Platform 文档](https://platform.claude.com/docs/en/build-with-claude/cache-diagnostics)

# Claude 提示缓存没命中怎么查：用 diagnostics 找出是 system、tools 还是 messages 变了

如果你给 Claude 请求加了 `cache_control`，但 `usage.cache_read_input_tokens` 一直是 0，最省事的查法是打开 **cache diagnostics**：每一轮请求都带上 `diagnostics` 对象，第一轮写 `"previous_message_id": null`，后面每轮填上一轮响应的 `id`。API 会比较前后两次请求，告诉你第一个不一样的地方在模型、system、tools 还是 messages。

Anthropic 发布说明写明，cache diagnostics 已于 2026 年 9 月 23 日在 Claude API 上退出 Beta，不再需要 `cache-diagnosis-2026-04-07` 请求头，还在发这个头的请求照常可用。官方文档：[Cache diagnostics](https://platform.claude.com/docs/en/build-with-claude/cache-diagnostics)。

适用范围：Claude API 的 Messages 接口（`/v1/messages`）。官方说明它**不支持** Amazon Bedrock 和 Google Cloud 上由 Google 托管的 Claude，Managed Agents 也不支持。

## 第一步：先确认是不是真的没命中

看响应里的 `usage`（流式响应在 `message_start` 事件里）：

- `cache_creation_input_tokens`：这次写进缓存的 token 数；
- `cache_read_input_tokens`：这次从缓存读到的 token 数；
- `input_tokens`：最后一个缓存断点之后的 token 数。

三者相加等于总输入。官方原话是：两个缓存字段**都是 0**，说明这次提示根本没被缓存。这时先排除两种和 diagnostics 无关的情况：

1. **提示太短**。低于下表最低长度时，即使标了 `cache_control` 也不会缓存，而且**不报错**。
2. **超时**。默认缓存寿命是 5 分钟，从写入或读取缓存的那次请求**开始**算，不是从响应结束算。

| 模型 | 最低可缓存长度（token） |
|---|---|
| Opus 5.5、Opus 5、Sonnet 5.5、Haiku 5.5、Fable 5.1、Fable 5 | 512 |
| Opus 4.8、Sonnet 5、Sonnet 4.6、Sonnet 4.5 | 1,024 |
| Opus 4.7 | 2,048 |
| Opus 4.6、Opus 4.5、Haiku 4.5 | 4,096 |

上表适用于 Claude API 等官方平台，Bedrock 要看 AWS 自己的文档。

## 第二步：每一轮都带上 diagnostics

`diagnostics` 对象本身就是开关：只有带了它的请求，API 才会以响应 `id` 为键记下一份“指纹”（只有哈希和 token 数估计，不存原文）。所以**每一轮都要带**，漏一轮，下一轮就没东西可比。

第一轮：

```json
"cache_control": {"type": "ephemeral"},
"diagnostics": {"previous_message_id": null}
```

第二轮起，把上一轮响应的 `id` 填进去，其它内容照常追加：

```json
"cache_control": {"type": "ephemeral"},
"diagnostics": {"previous_message_id": "msg_上一轮响应的id"}
```

多轮对话里，每次都把最新一轮的 `id` 往下传。官方 SDK 示例用的是 `client.beta.messages.create(..., diagnostics=...)`，响应里读 `diagnostics.cache_miss_reason.type`。

## 第三步：看懂 diagnostics 的三种返回

| 返回值 | 含义 | 怎么办 |
|---|---|---|
| `null` | 没带 diagnostics、第一轮（无可比）、或比较完没发现差异 | 结合下一节的 usage 判断 |
| `{"cache_miss_reason": null}` | 响应出得太快，比较还没跑完 | 视为没有结论，看下一轮 |
| `cache_miss_reason` 是一个对象 | 给出了原因，`type` 见下表 | 按 `type` 改 |

响应只报告**最早**的一个分叉点。先改掉它，后面可能还藏着别的。

## 六种 cache_miss_reason 分别怎么改

| type | 官方解释 | 改法 |
|---|---|---|
| `model_changed` | 和上一次的 `model` 不同，例如路由、A/B 测试或降级换了模型；缓存按模型分开 | 同一段缓存对话里固定模型 |
| `system_changed` | `system` 不同，常见是把时间戳、请求 ID 拼进了系统提示 | system 写成固定常量，动态内容挪到缓存断点之后的第一条 user 消息 |
| `tools_changed` | `tools` 增删、换顺序，或 `input_schema` 序列化不稳定 | 每轮发同样的工具、固定顺序，序列化时排序键 |
| `messages_changed` | 前面的历史被改、删、重排，而不是只在末尾追加；常见是截断历史或重发时改了 assistant / `tool_result` 的格式 | 历史只追加，assistant 内容和工具结果原样回传 |
| `previous_message_not_found` | 找不到这个 `previous_message_id` 的指纹；**不代表请求变了** | 每轮都带 diagnostics，前后两轮间隔不要太久，确认在同一工作区 |
| `unavailable` | 没有诊断信息：`tool_choice`、`thinking`、`context_management`、`output_config`、`output_format` 或启用的 `anthropic-beta` 头变了，或对话太长、差异超出比较范围 | 缓存对话期间保持这些参数不变；仍不行就用最后一节的手动清单 |

四种 `*_changed` 还会带 `cache_missed_input_tokens`，表示分叉点之后大约有多少输入 token。它是按字节长度估的，只能看量级，不能当账单数字。

## 把 diagnostics 和 usage 放在一起看

下面的判断只适用于传了真实 `previous_message_id` 的轮次：

| diagnostics | cache_read_input_tokens | 说明 |
|---|---|---|
| `null` | 高 | 正常命中 |
| `null` | 很低或 0 | 请求没变，但缓存条目已失效：缩短两轮间隔，或改用 1 小时缓存 |
| `*_changed` | 很低或 0 | 请求变了，按 type 修 |
| `*_changed` | 高 | 少见：变化在提示靠后处，前面的断点仍命中，影响小 |

1 小时缓存的写法是 `"cache_control": {"type": "ephemeral", "ttl": "1h"}`。混用时，1 小时的条目必须排在 5 分钟条目前面。注意官方价格倍数里，1 小时写入比 5 分钟写入更贵，具体以官网价格页为准。

## diagnostics 指不出来时的手动清单

官方提示缓存文档的排错清单，可以逐条对照（[Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)）：

1. 被缓存的部分每次完全一致；显式断点的 `cache_control` 位置不变。
2. 两次调用在缓存寿命内。
3. `tool_choice`、图片的有无、thinking 设置、`output_config.effort` 前后一致。
4. 达到所用模型的最低长度。
5. 断点要放在**每次都不变的最后一个块**上。提示末尾有时间戳、每次不同的上下文时，把断点放在静态前缀的末尾，而不是放在会变的块上。
6. `tool_use` 内容块里的键顺序要稳定，官方点名 Swift、Go 等语言在转 JSON 时可能打乱键顺序。
7. 系统往回找已有缓存最多查 20 个位置。一轮新增 20 个以上块时，在靠近上次写入的位置再加一个断点。
8. Claude API 的缓存按工作区隔离，不同工作区之间不共享。

## 经中转调用时要注意什么

通过 OpenLux 用 Anthropic Messages 格式调用时，Base URL 填 `https://api.openlux.ai`（不带 `/v1`，客户端会自己拼 `/v1/messages`），Key 在控制台「令牌」页创建（`https://www.openlux.ai/console/token`），可以放在 `x-api-key` 或 `Authorization: Bearer` 里。先请求 `/v1/models` 能列出模型，说明地址和 Key 都对；Key 错会返回 401。Claude 各模型支持哪些接口，以价格页标注为准。

需要说清楚的是：官方写明 diagnostics 只在 Claude API 上提供，而且前后两次请求必须在**同一组织、同一工作区**。本文没有核实 OpenLux 是否原样透传 `diagnostics` 字段，也无法保证连续两次请求落在同一个上游工作区。所以经中转时如果响应里没有 `diagnostics` 字段，或者总是返回 `previous_message_not_found`，就按本文第一步和最后一节，用 usage 的三个缓存字段配合手动清单排查。

## 怎么确认修好了

用同一段固定前缀连续发两轮请求，两轮都带 diagnostics，间隔控制在缓存寿命内。第二轮同时满足下面两条就算修好了：`diagnostics` 为 `null`，并且 `cache_read_input_tokens` 接近你那段固定前缀的长度。

想用同一个 Key 调 Claude、GPT、Gemini 等模型，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-prompt-cache-miss-diagnostics-fix&utm_content=footer)。

---
layout: default
title: "gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办"
description: "OpenAI 将于 2027-01-20 下线 gpt-realtime 等旧实时语音模型，替代为 gpt-realtime-2.1。按官方提示词指南、弃用页、模型页、Realtime API 参考和 OpenAI 支持人员在社区的复现结论，说明换模型后「说完我查一下就沉默」的多消息与 phase 原因、半句中断时如何看 response.done 状态、reasoning.effort 设置和提示词迁移步骤。"
permalink: /news/gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[OpenAI Prompting Realtime models](https://developers.openai.com/api/docs/guides/voice-prompting)

# gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办

先说结论：OpenAI 已公告 `gpt-realtime`（快照 `gpt-realtime-2025-08-28`）将于 2027-01-20 下线，官方给出的替代是 `gpt-realtime-2.1`。2.1 是推理型实时语音模型，**一次响应可能返回多条消息**（先一句 `commentary` 前置语，再一条 `final_answer`），而且默认会先说前置语。如果你的播放代码只按「一次响应一条消息」处理，用户就会听到「好的，我帮您查一下」之后长时间没有下文。处理办法是：逐条处理响应里的所有输出项并按 `phase` 区分，把 `session.reasoning.effort` 明确设成 `low`，再按官方提示词指南重写前置语、工具和语言规则。

本文依据 OpenAI 官方的 [Prompting Realtime models 指南](https://developers.openai.com/api/docs/guides/voice-prompting)、[弃用公告页](https://developers.openai.com/api/docs/deprecations)、[gpt-realtime-2.1 模型页](https://developers.openai.com/api/docs/models/gpt-realtime-2.1)和 [Realtime API 参考](https://developers.openai.com/api/reference/resources/realtime)，资料核对日期为 2026-11-01。官方提示词指南以 `gpt-realtime-2` 为例编写，下文引用的社区问题也发生在 `gpt-realtime-2` 上；模型页说明 `gpt-realtime-2.1` 是在 GPT-Realtime-2 基础上改进字母数字识别、静音与噪声处理和打断行为的更新版，所以迁移到 2.1 时应按同样的思路逐项检查。

## 哪些实时模型要下线，分别换成什么

2026-07-20 的弃用公告（Legacy audio, realtime and transcription）列出了以下实时模型，下线日期都是 2027-01-20：

| 要下线的模型 | 官方推荐替代 |
|---|---|
| `gpt-realtime`、`gpt-realtime-2025-08-28` | `gpt-realtime-2.1` |
| `gpt-4o-realtime` | `gpt-realtime-2.1` |
| `gpt-realtime-mini`、`gpt-realtime-mini-2025-12-15` | `gpt-realtime-2.1-mini` |
| `gpt-4o-mini-realtime` | `gpt-realtime-2.1-mini` |

同一公告里的 `gpt-audio`、`gpt-4o-audio` 等音频模型改用 `gpt-audio-1.5`，不在本文范围内。另外，官方提示词指南把 `gpt-realtime-1.5` 列为「快速、可靠的非推理语音模型」，截至核对日它不在弃用列表里。

旧模型和新模型的几项基础差异（来自各自模型页）：

| 项目 | gpt-realtime | gpt-realtime-2.1 |
|---|---|---|
| 推理 | 模型页未列推理能力 | 支持，推理强度可调 |
| 上下文窗口 | 32,000 | 128,000 |
| 最大输出 token | 4,096 | 32,000 |
| 接口 | `v1/realtime` | `v1/realtime` |

## 换模型后常见的三类症状，先对号入座

| 症状 | 最可能的原因 | 先看什么 |
|---|---|---|
| 说完「我帮您查一下」就沉默 5～20 秒，用户追问才继续 | 一次响应里有 `commentary` 和 `final_answer` 两条消息，客户端只播了第一条 | 该响应的 `response.done` 里 `output` 有几项、各自的 `phase` |
| 话说到一半突然停住，转写文本也不完整 | 响应状态为 `incomplete`，原因是 `max_output_tokens` 或 `content_filter` | `response.done` 里的 `status` 和 `status_details.reason` |
| 开口前总多一句铺垫、工具该调不调、回答换了语言 | 2 代默认生成前置语、更依赖精确的提示词，旧提示词没有改写 | 提示词里的前置语、工具、语言三段规则，以及 `reasoning.effort` |

## 症状一：说完「我查一下」就没有下文

OpenAI 开发者社区有开发者反馈：把生产语音客服从旧实时模型换到 `gpt-realtime-2` 后，模型说完「好的，我帮您看看有哪些时段」就结束，期间没有调用任何工具，用户要等十几秒并主动追问才继续；另有两位开发者回复遇到同类问题。OpenAI 支持人员在[该帖](https://community.openai.com/t/gpt-realtime-2-splits-acknowledgment-next-step-into-separate-turns-causing-5-20s-caller-silence-rollback-to-gpt-realtime-1-5-confirmed-as-a-b-fix/1381276)中复现后确认：模型在**同一次响应里返回了两条音频消息**，先是 commentary 前置语，再是 final_answer 的问题；当时使用的 LiveKit 1.5.10 只播放了第一条并丢弃了后面那条。

官方提示词指南对这一行为的说明是：2 代模型可以在 `commentary` 通道输出前置语和工具调用，在 `final` 通道输出最终回答；在 API 输出里，`response.done` 事件中每个输出项带有 `phase` 字段，取值为 `commentary` 或 `final_answer`。

处理步骤：

1. **用 LiveKit 的**：按 OpenAI 支持人员的建议，把 `livekit-agents` 和 `livekit-plugins-openai` 同时升级到至少 1.5.12（该版本加入了多消息支持），两个包版本要一致。
2. **自己写客户端的**：不要假设一次响应只有一个输出项。逐个处理 `response.output_item.added` / `response.output_item.done`，按顺序播放每一条音频；需要区别对待时读取 `phase`，例如前置语只作为短提示播放，`final_answer` 作为正式回答。
3. 升级过渡期间，支持人员认为暂时回退到 `gpt-realtime-1.5` 是合理做法。

如果升级后仍然沉默，官方建议保留一份去敏后的事件记录，包含 `response.output_item.added`、`response.output_item.done` 和最后的 `response.done`，再去反馈。

## 症状二：话说到一半停住——先看 response.done 的状态

API 参考对响应状态的定义是：`status_details.reason` 在响应被取消（`cancelled`）时为 `turn_detected`（服务端 VAD 检测到用户开始说话）或 `client_cancelled`（客户端发了取消事件）；在响应不完整（`incomplete`）时为 `max_output_tokens` 或 `content_filter`（服务端安全过滤触发并截断了响应）。

| `status` | `status_details.reason` | 处理方向 |
|---|---|---|
| `cancelled` | `turn_detected` | 用户插话打断，属于正常行为；如误打断多，检查 VAD 设置 |
| `cancelled` | `client_cancelled` | 检查自己的代码是否在不该取消时发了 `response.cancel` |
| `incomplete` | `max_output_tokens` | 检查会话或单次响应里的 `max_output_tokens` 是否设得过小 |
| `incomplete` | `content_filter` | 安全过滤截断；有开发者在同一社区帖中反馈非英语对话里出现过这种情况，可保留事件记录向官方反馈 |

所以排查「说一半停住」时，第一步是把每个 `response.done` 完整记进日志，别只记转写文本，否则无法区分是被打断、被截断还是客户端自己停了播放。

## 症状三：多出前置语、工具不调用、语言乱切——按官方迁移步骤改提示词

官方指南明确说，2 代模型比早期实时模型更按字面执行指令，旧提示词可能需要重构。它给出的迁移步骤可以归纳为：

1. 用 Codex 或较强的推理模型，参照最新的 Realtime 提示词指南重构提示词，并在要求里附上指南链接。
2. 把推理强度设为 `low`，只对确实需要更深规划的流程再调高。
3. 核对工具名、参数、枚举值、JSON Schema 等设置与实际实现一致。
4. 删除过时示例，补充正常流程、含糊输入、打断、工具调用和兜底的短示例。
5. 拿迁移前后的典型对话做对比，用已有评测检查回退，并记录有意为之的行为变化。
6. 做一次一致性检查，把硬性要求、默认行为、工具规则、安全规则和兜底行为分开写清楚。
7. 跑评测、看失败样例、反复改，直到目标行为稳定。

推理强度在会话配置里设置。API 参考中会话对象有 `reasoning.effort` 字段，可选值为 `minimal`、`low`、`medium`、`high`、`xhigh`，参考里标注的默认值是 `low`；迁移指南仍要求明确设为 `low`，显式写出来也便于以后调整。示例：

```json
{
  "type": "session.update",
  "session": {
    "type": "realtime",
    "model": "gpt-realtime-2.1",
    "reasoning": { "effort": "low" },
    "tool_choice": "auto"
  }
}
```

针对三类具体表现，指南里对应的改法：

- **前置语太多**：2 代默认生成前置语。在提示词里单独写「前置语」一节，规定什么时候用（要调用耗时工具、要查记录、准备转人工）、什么时候不用（答案可以直接给、用户只是确认或否定、音频不清楚、听到的是静音或背景声），长度限制为一句短话，内容描述正在做的动作，而不是「让我想一想」这类填充语。
- **工具该调不调或乱调**：按工具类型写清调用积极程度——只读、低风险查询在意图和必填字段明确时直接调用；修改数据、付款、取消等写操作先复述后果并等用户确认。提示词里提到的工具名必须和实际传入的工具列表一致，指南提醒名称对不上时模型可能编造工具名或假装已完成操作。
- **回答换了语言**：语言和口音分开控制。不要写「跟随用户」「用用户的语言回答」这类宽泛要求，而是写明默认语言、只在用户明确要求或说了完整的另一种语言时才切换，并要求前置语、工具相关提示和最终回答使用同一种语言。

另外，听到静音、背景噪声、等待音乐时模型容易接话。指南建议提供一个无参数的 `wait_for_user` 工具，并在提示词里要求遇到这类音频时调用它、不要说「我在」「没听清」。

## 迁移后怎么验证

1. 发送上面的 `session.update` 后，确认收到 `session.updated`，并检查其中的 `model` 和 `reasoning.effort` 是否为你设置的值。
2. 准备一组带工具调用的典型对话，逐个检查 `response.done`：多条输出项是否都被播放、`phase` 是否被正确区分、`status` 是否为 `completed`。
3. 对照迁移前的录音或转写，确认没有出现长时间静音、半句中断，工具调用次数和参数与预期一致。
4. 语言测试：用带口音的英语、夹杂个别外语词的句子各试一次，确认回答语言不会被带偏。

## 常见问题

**只换 model 字段、其它都不改行不行？** 两个模型都走 `v1/realtime` 接口，但官方指南明确提醒旧提示词可能需要重构，而且多消息响应需要客户端支持。至少要确认播放逻辑能处理一次响应里的多条消息。

**能不能继续用旧模型到下线日？** 下线日是 2027-01-20，在那之前旧模型仍按公告可用。但官方迁移步骤要求重构提示词并用评测对比前后效果，这需要时间，建议提前开始。

**`parallel_tool_calls` 要不要开？** API 参考说明该参数只有推理型实时模型（如 2 代）支持，是否开启取决于你的工具之间有没有先后依赖。

迁移期间如果需要一个能同时调用 GPT、Claude、Gemini 等模型的 OpenAI 兼容接口做文本侧对比测试，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix&utm_content=footer)。

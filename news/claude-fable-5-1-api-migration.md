---
layout: default
title: "Claude Fable 5.1 上线：API 迁移需检查 tool_choice、思维块与数据保留"
description: "Fable 5.1提供1M上下文与128K输出；迁移前须处理tool_choice限制、思维块绑定校验及30天数据保留要求。"
permalink: /news/claude-fable-5-1-api-migration/
date: 2026-09-01
---

> 更新日期：2026-09-01 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#september-1-2026)

<think>**Planning structured Chinese content with official references****Clarifying provider availability and API constraints**</think>

# Claude Fable 5.1 上线：API 迁移需检查 tool_choice、思维块与数据保留

**结论：**准备把现有 Claude API Agent 切换到 `claude-fable-5-1` 的团队，应先完成三项阻断性检查：移除 `tool_choice` 中的 `any` 与 `tool`、审计跨轮重放的 thinking 块及其历史前缀、确认业务可以接受 30 天数据保留。否则，迁移后可能直接出现 400 错误，或因 thinking 块被丢弃而改变上下文连续性。

本文适合已经使用 Claude API 构建工具调用型 Agent、保存多轮消息历史、或依赖提示词缓存的开发与平台团队。文中“官方发布事实”均来自 Claude Platform 2026 年 9 月 1 日的发布说明；“作者建议”用于将这些规则转化为迁移操作。

## 官方发布事实：模型规格、价格与可用位置

Claude 官方于 2026 年 9 月 1 日发布 Claude Fable 5.1，模型 ID 为 `claude-fable-5-1`。官方将其定位于长时运行的代理式编程、知识工作与研究。

| 项目 | 官方发布事实 | 对迁移的含义 |
|---|---|---|
| 模型 ID | `claude-fable-5-1` | 需在模型路由、白名单、计费标签和评测配置中同步更新 |
| 上下文窗口 | 默认 100 万 token | 长历史 Agent 可重新评估截断、摘要与检索策略 |
| 最大输出 | 12.8 万 token | 应检查下游流式消费、数据库字段、响应超时与单轮预算 |
| Thinking | 始终启用 adaptive thinking | 不应假定能沿用过去“关闭 thinking”的控制逻辑 |
| 输入价格 | 每百万 token 10 美元 | 需更新成本模型 |
| 输出价格 | 每百万 token 50 美元 | 长输出或多工具循环应单独设定预算预警 |
| 缓存读取 | 每百万 token 0.25 美元 | 命中缓存时的成本计算应更新 |
| 缓存写入 | 价格不变 | 既有缓存写入预算逻辑可保留，但仍应回归验证 |
| 官方提供位置 | Claude API、Amazon Bedrock、Claude Platform on AWS、Google Cloud、Microsoft Foundry | 应按实际接入渠道核实模型选择与部署配置 |

以上是官方发布规格，不等同于某个具体业务工作流的效果、延迟或成功率。上线前仍应使用自身数据集进行回归测试。

## 先处理会导致 400 的 `tool_choice`

这是最容易在模型 ID 替换后立刻暴露的问题。官方明确说明：在 Claude Fable 5.1 上，`tool_choice` 类型 `any` 与 `tool` 不受支持，并会返回 400 错误；`auto` 与 `none` 的行为不变。

因此，不能只搜索应用代码中的模型名，还要扫描所有实际出站请求，包括：

- SDK 封装层的默认 `tool_choice`；
- Agent 框架根据步骤动态生成的请求；
- 重试、回放、异步任务和评测脚本；
- 按租户、场景或工具集配置的 JSON 模板；
- 旧会话恢复时存储的原始请求参数。

**作者建议：**将迁移分为“兼容模式”和“约束模式”。

1. **兼容模式：**若工具调用并非每一轮都必须发生，改用 `auto`，让模型自行决定是否调用工具。
2. **无工具模式：**不允许该轮调用工具时，使用 `none`。
3. **约束模式：**若业务需要保证工具输入遵守既定 schema，不要依赖已不支持的 `any` 或 `tool`；应评估官方建议的 strict tool use 或 structured outputs。

这里的关键不只是避免 400，还包括重新定义“必须调用某工具”的业务约束应由哪个机制承担：模型选择、结构化输出约束，还是应用侧校验与重试。

## preserved thinking：重放规则比模型切换更严格

对于保存模型输出并在下一轮原样回传的 Agent，thinking 块是本次迁移的另一项核心风险。官方规则可以拆成两个层面。

第一，**模型版本兼容性**：Claude Fable 5.1 生成的 thinking 块只能被生成它的模型或更新模型读取。若将该块重放给较早模型，API 会丢弃该块。官方同时说明，Claude Fable 5.1 可以接受来自 Claude Opus 5、Claude Fable 5、Claude Mythos 5 以及更早 Claude 模型的 thinking 块。

第二，**历史前缀绑定**：对于 2026 年 8 月 31 日及以后创建的新账户，若重放 thinking 块时，该块之前的 `system` 提示、`tools` 定义或此前消息发生变化，Claude Fable 5.1 会返回 400 错误。

这意味着“消息看起来语义等价”并不足以保证可重放。例如，调整系统提示措辞、变更工具 schema、插入一条历史消息，均可能使此前 thinking 块对应的前缀不再匹配。

## 如何设计上下文重放与模型降级

**作者建议：**把 thinking 块视为绑定了“模型版本 + 历史前缀”的状态，而不是可以跨模型、跨提示版本自由搬运的普通文本。

可采用以下决策框架：

1. **是否保存并重放 thinking 块？**  
   若不需要跨轮保留该类块，优先将会话状态与业务记忆分离，减少迁移耦合。

2. **目标模型是否早于产生块的模型？**  
   若是，不应期待该 thinking 块继续生效；官方说明 API 会将其丢弃。

3. **thinking 块之前的内容是否发生变化？**  
   对新账户而言，只要 `system`、工具定义或更早消息变更，就可能触发 400。应停止重放该块，或从新的稳定前缀重新开始会话。

4. **是否必须调整历史提示或工具？**  
   若必须修改，建议将这类变更作为新的会话分支处理，而不是在旧会话中直接替换历史内容。

5. **是否需要定位被系统丢弃的块？**  
   可使用官方提供的 beta 控制能力进行诊断。

官方提供 `thinking-binding-controls-2026-08-01` beta 请求头。启用后，API 会通过响应中的 `input_transformations` 返回被丢弃的块信息；同时可通过 `thinking.block_binding.prefix_mismatch_behavior` 决定历史前缀变化时采用拒绝还是丢弃策略。

**作者建议：**预发布环境可先选择能暴露问题的拒绝策略，以发现不安全的历史改写；在明确理解丢弃后的业务影响前，不应把“自动丢弃”当作无影响的兼容方案。生产处理逻辑还应记录 400 的请求版本、会话 ID、模型 ID、提示版本和工具版本，以便定位历史不匹配来源。

## 提示词缓存、长上下文与成本核算

官方发布信息显示，Claude Fable 5.1 的缓存读取价格为每百万 token 0.25 美元，缓存写入价格不变。与此同时，模型默认支持 100 万 token 上下文、最大输出为 12.8 万 token。

这组条件会改变成本与容量规划，但不会自动保证缓存命中。**作者建议**在迁移评测中分别记录输入 token、输出 token、缓存读取 token 与缓存写入 token，而不是只比较单次请求总成本。对于长时运行 Agent，还应验证：

- 上游是否会构造超过内部网关、日志系统或消息队列限制的大请求；
- 下游是否能持续接收较长的流式输出；
- 会话摘要、检索结果和工具返回是否会挤占核心任务上下文；
- 提示模板版本变化是否影响既有缓存策略；
- 单次任务、单个会话和单租户的费用阈值是否需要调整。

这些是工程验证项目，不是官方对性能或成本结果的承诺。

## 数据保留是上线审批项，而非运行时细节

官方说明，Claude Fable 5.1 需要 30 天数据保留；除非获得 Anthropic 明确授权，否则不支持零数据保留。

因此，数据保留不应留到 API 连通后再讨论。尤其是处理客户内容、源代码、医疗、金融或内部研究材料的系统，应在上线审批前确认数据分类、合同约束、内部政策和供应商使用边界是否允许 30 天保留。

**作者建议：**如果组织要求零数据保留，不应假定 `claude-fable-5-1` 可以直接替换现有模型。应先向 Anthropic 确认是否获得明确授权，并将确认结果纳入供应商治理记录。

## 可执行迁移检查清单

在逐步放量前，建议由应用、平台与合规负责人共同完成以下检查：

- [ ] 将目标模型 ID 配置为 `claude-fable-5-1`，并检查路由、回退和评测任务是否仍引用旧模型。
- [ ] 扫描所有请求路径，确保 `tool_choice` 不再使用 `any` 或 `tool`。
- [ ] 对必须满足 schema 的工具输入，评估 strict tool use 或 structured outputs。
- [ ] 识别是否持久化并重放 thinking 块，包括数据库会话记录、队列任务和故障恢复数据。
- [ ] 禁止把 Fable 5.1 生成的 thinking 块重放到较早模型。
- [ ] 为新账户验证：修改 `system`、`tools` 或此前消息后重放 thinking 块是否触发 400。
- [ ] 在测试环境启用 `thinking-binding-controls-2026-08-01`，检查 `input_transformations` 的处理与日志记录。
- [ ] 按输入、输出、缓存读取和缓存写入分别核对成本统计。
- [ ] 用真实长度的长上下文与长输出样本验证网关、超时、流式解析和存储容量。
- [ ] 在生产审批中确认 30 天数据保留符合组织治理要求。

## 建议的发布顺序

建议先建立一组包含工具调用、工具 schema 变更、历史消息改写、thinking 重放、缓存命中和长输出的回归用例；随后在隔离环境切换模型 ID，并重点观察 400 响应与 `input_transformations`。确认请求结构和会话状态策略稳定后，再小范围放量。

不要把模型切换理解为单一配置变更。对 Agent 而言，`tool_choice` 是请求契约，thinking 块是会话状态，数据保留则是治理边界；三者都完成审计后，才适合推进生产迁移。

截至所给目录快照，OpenLux 公开目录没有与该模型匹配的条目，因此不应把目录状态作为其上线或可用性的依据；如需核对目录，可访问：https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-fable-5-1-api-migration&utm_content=footer

## 官方一手来源

- https://platform.claude.com/docs/en/release-notes/overview#september-1-2026

---
layout: default
title: "Confluent Cloud 早期接入 IBM Granite：用 Flink SQL 做时序预测与异常检测"
description: "IBM Granite 时序模型已在 Confluent Cloud Early Access，可通过 Flink SQL 调用预测和异常检测函数。"
permalink: /news/confluent-cloud-ibm-granite-time-series-early-access/
date: 2026-09-08
---

> 更新日期：2026-09-08 · 一手来源：[Hugging Face Blog](https://huggingface.co/blog/ibm-research/real-time-intelligence)

# Confluent Cloud 早期接入 IBM Granite：用 Flink SQL 做时序预测与异常检测

如果你的数据已经进入 **Confluent Cloud**，并且希望直接在流处理链路中完成**时序预测**或**异常检测**，这项 Early Access 值得优先验证。官方发布的信息显示，IBM Granite Time Series 模型已通过 Confluent Cloud 在 Apache Flink 上提供原生推理，可从 Flink SQL 调用 `AI_FORECAST` 和 `AI_DETECT_ANOMALIES`。

本文适合数据平台工程师、流处理开发者、运维与风控团队，以及需要判断“预测还是异常检测、四个模型怎么选”的技术负责人。需要先划清范围：以下内容分别标注为**官方发布事实**、**OpenLux 目录快照**和**作者建议**；Early Access 不等于普遍可用，也不代表已经具备正式 GA 的服务承诺。

## 先确认接入范围：AWS 上的 Confluent Cloud

### 官方发布事实

当前 Early Access 从 **Confluent Cloud on AWS** 开始。Confluent Platform 对本地和混合环境的支持安排在后续阶段，不能据此推断已经开放。

官方材料还说明，Early Access 期间不收费。这个条件只适用于 Early Access 阶段，不能延伸为长期价格或正式版本的费用判断。材料也没有给出具体区域、账户资格、配额、延迟、吞吐量或服务等级，因此这些内容必须在报名和开通后向官方确认。

### 作者建议

上线前先检查三件事：

1. 业务事件是否已经稳定写入 Confluent Cloud；
2. 使用的 Confluent Cloud 部署环境是否属于当前 AWS Early Access 范围；
3. 团队是否能接受早期功能可能存在的接口、模型覆盖范围或运行限制变化。

本次 OpenLux 当前公开目录快照没有匹配项，因此它不能作为 IBM Granite 已在某个目录中上线或账号可用的证明；实际资格仍应以 Confluent 的 Early Access 流程和官方文档为准：[注册并创建 API Key](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=confluent-cloud-ibm-granite-time-series-early-access&utm_content=footer)

## 两个 Flink SQL 函数分别解决什么问题

### `AI_FORECAST`：预测未来值

官方示例使用 `AI_FORECAST`，输入包括度量值、`event_time` 和 JSON 参数。参数中明确展示了 `model` 与 `horizon`，其中 `horizon` 用于表达预测范围。

材料中的调用形式如下：

```sql
SELECT
  AI_FORECAST(
    load_kw,
    event_time,
    JSON_OBJECT(
      'model' VALUE 'ttm',
      'horizon' VALUE 12
    )
  ) OVER (
    ORDER BY event_time
    RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS forecast
FROM meter_readings;
```

这段 SQL 只能作为官方示例的起点。多条设备、账户或生产线同时存在时，不应直接照抄表名和窗口定义，而要根据官方文档确认序列标识、分区方式、时间字段类型以及结果字段结构。

### `AI_DETECT_ANOMALIES`：识别偏离正常状态的行为

异常检测应使用 `AI_DETECT_ANOMALIES`。它适合设备遥测、支付活动、应用指标等具有持续历史状态的序列。官方材料强调，预测和异常检测都依赖近期历史：下一次观测值需要放在历史上下文中解释，异常也需要与持续更新的“正常状态”比较。

目前给出的材料没有完整列出 `AI_DETECT_ANOMALIES` 的参数签名，因此本文不编写未经核验的调用代码。接入时应直接以 Confluent Cloud for Apache Flink 的官方函数文档为准，尤其确认返回的是异常分数、标记还是包含其他诊断信息的结构。

## 四个模型如何选择

官方发布的是四个互补的时序基础模型。它们都可以通过现有的 `AI_FORECAST` 和 `AI_DETECT_ANOMALIES` 函数调用，切换模型时主要修改 SQL 中的 `model` 参数，不需要重建整条数据管道。

下表是基于官方材料的选择起点，不是性能排名，也不是跨业务场景的基准结论。

| 模型 | 官方材料强调的特点 | 更适合作为哪类起点 | 验证重点 |
|---|---|---|---|
| PatchTST-FM | 按时间片处理序列；各变量分别建模；可返回完整分布 | 需要预测区间或按分位数制定库存、容量策略的场景 | 结果是否提供所需分布信息，预测范围是否满足业务决策 |
| FlowState | 持续更新状态；面向连续时间变化 | 采样频率不固定，或同时存在秒级与小时级数据的场景 | 不同采样间隔、缺失点和状态延续时的结果表现 |
| TTM | 使用较小的混合网络；官方材料强调其面向大规模序列和 CPU 推理 | 序列数量很多、希望控制基础设施复杂度的场景 | 序列规模、变量数量、资源消耗与结果质量之间的平衡 |
| TSPulse | 融合时间与频率视角；支持异常检测、分类、补全和相似性问题 | 异常检测为主，且希望进一步做相似历史检索或补全的场景 | 异常事件、噪声、周期变化和历史相似窗口的识别能力 |

### 作者建议的决策顺序

先按任务筛选，而不是先按模型名称筛选：

- 目标是预测未来负载、需求或产量：先验证 `AI_FORECAST`；
- 目标是发现设备、交易或应用指标偏离正常：先验证 `AI_DETECT_ANOMALIES`；
- 既要预测又要告警：分别设计两类结果和下游处理，不要把预测值直接当作异常分数；
- 序列数量和采样频率是主要约束时，再比较 TTM 与 FlowState；
- 需要预测区间或不确定性信息时，优先核对 PatchTST-FM 的输出结构；
- 异常检测之外还要做相似案例、分类或缺失补全时，再重点验证 TSPulse。

四个模型之间应使用同一批可回放数据进行比较。不要把官方对模型结构的描述替代为本业务上的准确率结论。

## 从数据流到推理结果的落地步骤

### 第一步：整理序列和时间字段

确认每条记录包含：

- 业务序列的标识，例如设备、账户、生产线或指标；
- 数值观测字段；
- `event_time`；
- 能够区分不同序列的稳定键；
- 对预测而言足够连续的历史数据。

官方材料说明，Flink 会按序列管理状态，并以容错方式保留模型所需的历史。作者建议在设计时明确“一个序列是什么”，避免把不同设备或账户混在同一历史上下文中。

### 第二步：报名并验证 Early Access

使用 Confluent 官方 Early Access 流程申请。开通后，不要一开始就接入全部生产流量，建议先用一个低风险主题验证：

1. Flink SQL 是否能识别目标函数；
2. `model` 和 `horizon` 等 JSON 参数是否被当前环境接受；
3. `event_time` 窗口是否按预期推进；
4. 推理结果的字段和数据类型是什么；
5. 多序列状态是否发生串线或重置。

### 第三步：先做单一任务的最小管道

预测和异常检测分开建立最小验证链路。先选择一个模型、一个主题和一类序列，确认端到端数据流通，再扩大范围。

如果需要比较模型，可以保持输入主题、时间窗口、预测范围和下游评估方式不变，只修改 `model` 参数。官方材料明确指出，这种切换不要求重建数据管道。

### 第四步：把结果写回 Kafka

官方方案会将推理结果写入 Kafka topics。之后可以接入告警系统、仪表盘、湖仓或 AI Agent。作者建议为结果主题保留足够的业务上下文，例如序列标识、事件时间、模型名称和运行批次，以便定位“哪个序列、何时、由哪个模型产生了结果”。

### 第五步：使用 Kafka 回放做上线前验证

Kafka 的持久化和可重放特性适合做历史回放。上线前可以：

- 用已知历史区间回放预测，比较预测与实际观测；
- 回放已知异常事件，检查告警是否被识别；
- 比较四个模型在相同数据上的结果；
- 模拟延迟、重复或缺失事件，观察状态恢复行为；
- 记录模型切换前后的输出差异，方便审计和故障排查。

材料没有提供准确率、误报率或延迟数据，因此这些指标应由团队用自己的数据测量，而不是引用宣传材料中的泛化结论。

## 上线前的判断框架

可以用下面四个问题决定是否继续扩大范围：

1. **数据条件是否成立？**  
   序列标识、时间戳和历史状态是否稳定，数据是否已经在 Confluent Cloud 中流动？

2. **业务动作是否明确？**  
   预测结果是否会触发补货、容量调整或排产？异常结果是否会触发告警、人工复核或自动处置？

3. **模型选择是否可解释？**  
   是否能说明为什么从某个模型开始，以及换模型后准备观察哪些指标？

4. **Early Access 风险是否可接受？**  
   是否已经准备回退路径、结果主题隔离、历史回放和人工审核机制？正式环境的价格、限制和可用性应在官方确认后再纳入长期架构。

## 接入检查清单

- [ ] 数据已进入 Confluent Cloud；
- [ ] 环境属于当前 AWS Early Access 范围；
- [ ] 已完成官方报名和权限确认；
- [ ] 已核对 `AI_FORECAST` 与 `AI_DETECT_ANOMALIES` 文档；
- [ ] 已定义序列键和 `event_time`；
- [ ] 已为每个序列保留必要历史状态；
- [ ] 已用单一主题完成最小验证；
- [ ] 已比较至少两个候选模型；
- [ ] 已确认推理结果的字段结构；
- [ ] 已将结果写入独立 Kafka topic；
- [ ] 已完成历史回放、异常样本验证和故障排查；
- [ ] 已确定告警、仪表盘、湖仓或 Agent 的下游责任边界；
- [ ] 已准备 Early Access 结束后的费用、支持范围和迁移确认项。

## 官方一手来源

- https://huggingface.co/blog/ibm-research/real-time-intelligence
- https://events.confluent.io/early-access-flink-features

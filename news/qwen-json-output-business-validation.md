---
layout: default
title: "Qwen 输出 JSON 仍然不能入库：字段、类型与事实的三层验收"
description: "区分 JSON 语法、字段结构和业务事实错误，提供可运行的离线校验器。"
permalink: /news/qwen-json-output-business-validation/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)

# Qwen 输出 JSON 仍然不能入库：字段、类型与事实的三层验收

核验日期：2026 年 9 月 12 日。模型回答已经是合法 JSON，但订单状态、商品属性或客户信息依旧写入失败，是结构化提取中常见的下一阶段问题。本文从一个小型提取任务出发，说明如何区分语法错误、结构错误和事实错误。

开始前可以[注册 OpenLux 并确认实际入口支持的输出能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=qwen-json-output-business-validation&utm_content=intro)。服务商原生功能与聚合接口支持范围要分别核验。

## JSON 能解析不代表业务能接受

阿里云[结构化输出文档](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output)区分 JSON Object 与 JSON Schema 模式：前者关注有效 JSON，后者约束结构；JSON Object 提示中还需要包含 JSON 字样。模式支持取决于具体模型，不能仅凭产品系列名推定。

文档关于格式的能力不等于业务事实正确。例如，数量被输出为负数、商品编号不在原文、状态字段使用了系统不认识的值，都可能发生在语法完全正确的对象中。因此入库前仍需要应用自己的验收。

先把任务定义清楚：输入是什么、允许提取哪些字段、缺失值如何表达、是否允许额外字段。不要让模型自行决定数据库结构，也不要把一段解释文字塞到本应是整数的字段中。

## 先写一份可执行的数据约定

以提取商品名称与数量为例，约定名称必须是非空字符串，数量是正整数或者 null，null 表示原文没有给出数量。这个约定是本文的示例业务规则，应按你的实际需求修改。

| 验收层 | 示例问题 | 处理方式 |
|---|---|---|
| 语法 | 未闭合括号、夹带说明文字 | 保留原始响应并判失败 |
| 结构 | 缺少字段、数量是字符串 | 报告具体字段与类型 |
| 取值 | 数量是负数、名称为空 | 按业务约定拒绝 |
| 事实 | 数量与原文不符 | 比较原文证据 |
| 权限 | 提取结果试图覆盖其他用户记录 | 由业务服务限制写入范围 |

明确区分零、空字符串、null 和字段缺失。若原文未说明数量，模型输出零可能造成错误库存判断；如果应用又把 null 自动转换为零，就会丢失“不知道”的信息。

## 在本地运行一个最小校验器

下面示例只验证两字段的结构与取值，不是完整 JSON Schema 实现。它拒绝额外字段，特别排除 Python 中容易被当成整数的布尔值。代码运行不需要 API Key，也不会产生调用费用。

```python
import json

def validate_item(raw):
    item = json.loads(raw)
    if not isinstance(item, dict) or set(item) != {"name", "quantity"}:
        raise ValueError("字段集合不符合约定")
    if not isinstance(item["name"], str) or not item["name"].strip():
        raise ValueError("name 必须是非空字符串")
    qty = item["quantity"]
    if qty is not None and (type(qty) is not int or qty <= 0):
        raise ValueError("quantity 必须是正整数或 null")
    return item

assert validate_item('{"name":"杯子","quantity":2}')["quantity"] == 2
for raw in [
    '{"name":"杯子","quantity":true}',
    '{"name":"杯子","quantity":"2"}',
    '{"name":"杯子","quantity":-1}',
    '{"name":"杯子"}',
]:
    try:
        validate_item(raw)
    except ValueError:
        continue
    raise AssertionError("不合格样本被接受")
```

生产程序可以采用成熟的校验库，但仍应保留类似反例。不要通过无条件字符串替换来“修复”任意 JSON；它可能改变正文内容，掩盖模型输出与原文不一致的问题。

## 把原文证据加入人工复核

为每条测试样本标记期望字段及原文片段。数量来自哪一句，名称是否包含规格，原文出现两个商品时是否应该拆成两条，都需要预先规定。

初测可以准备正常输入、缺失信息、歧义描述三组样本，每组十条。这个数量适合发现明显错误，不足以证明上线可靠性。正式验收应覆盖业务真实分布，尤其关注会影响后续操作的关键字段。

模型输出的“证据”也需要核对是否真实出现在原文中。仅仅多返回一个 evidence 字段，并不会自动降低事实错误。若证据无法对应，就让任务进入人工复核或明确失败状态。

## 给格式修复和重新提取设置边界

纯语法错误可以尝试有限次数的格式修复；事实错误则应回到原始输入重新提取。不要把已经错误的结果反复交给模型润色，最后只得到更完整的错误对象。

每次尝试保存输入版本、模板版本、响应编号、失败层级和 token 用量。最终成功一条数据只计一次成功任务，但费用应包含所有尝试。这样才能判断结构化模式是否真的降低了整体处理成本。

对于已经通过校验的数据，写入仍应走业务接口，受去重约束、权限和事务控制。模型输出本身不能直接决定要删除或覆盖哪些记录。

## 如何判断本次优化有效

分别统计 JSON 解析通过率、结构通过率、事实通过率和最终入库成功率。如果只看第一项，格式变好可能掩盖事实质量下降。比较两个提示词版本时使用同一组固定样本，并保留独立的新样本防止只对测试集调整。

看到某一层连续失败，就改动对应规则：字段理解不一致时补充定义；输入确实缺失时明确缺失值；输出被截断时先查结束原因，不要立刻扩大格式修复重试次数。

遇到长回答不完整，可继续看[回答截断排查](https://a37836323.github.io/openlux-api-guides/news/qwen-output-truncation-finish-reason/)。需要预算比较可看[成功任务成本](https://a37836323.github.io/openlux-api-guides/model-cost-per-success/)。[进入 OpenLux 开始小样本验证](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=qwen-json-output-business-validation&utm_content=footer)。

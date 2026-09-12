---
layout: default
title: "Invalid schema：additionalProperties 必须为 false，嵌套对象怎么改？"
description: "按错误 context 找到嵌套 Schema，核对 additionalProperties、required 和可空字段。"
permalink: /news/structured-outputs-additionalproperties-false-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/structured-outputs)

# Invalid schema：additionalProperties 必须为 false，嵌套对象怎么改？

出现 `additionalProperties is required to be supplied and to be false` 时，先沿错误中的 `context` 找到具体对象节点。只在最外层添加 `additionalProperties: false`，不一定能修复嵌套对象。还要核对各对象的 `required` 是否包含全部属性，并按需要用可空类型表达业务上的可选值。

资料核验：2026 年 9 月 12 日。若准备评估云端 API，可[查看 OpenLux 的账户与可用模型](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=structured-outputs-additionalproperties-false-fix&utm_content=intro)。OpenLux 是独立服务，具体接口、计费和功能以其当前说明为准。

## JSON 有效，为什么 API 仍拒绝

OpenAI 社区有用户在 Pydantic 联合类型中遇到此错误，也有用户只在嵌套对象出现时失败。两类提问表明，代码里的类型定义看起来正确，并不等于最终发送的 Schema 满足 Structured Outputs 的要求。

这里要区分三层：请求正文是不是合法 JSON，Schema 是否符合该接口支持的子集，以及模型最终返回的数据是否满足业务要求。本文处理第二层，尚未进入模型生成阶段；不是靠在提示词中强调“只返回 JSON”就能修好的问题。

## 按错误 context 找到对象节点

| 错误位置或现象 | 应检查的节点 | 常见遗漏 |
|---|---|---|
| `context=()` | 根对象 | 缺少额外属性限制 |
| `properties` 后跟字段名 | 该字段的对象定义 | 只修了最外层 |
| 指向数组 `items` | 数组元素对象 | 元素也需要完整约束 |
| 指向 `$defs` 或引用路径 | 被引用的定义 | 生成或转换后定义变化 |
| required 报错 | 当前对象的 properties | 属性列表与必需列表不同步 |

建议保存脱敏后的最终 Schema，并按错误路径逐层展开。不要只检查 Pydantic 类定义，因为中间转换、工具封装或手动后处理都可能改变发出的内容。

## 一个明确的对象 Schema

下面仅展示 Schema 本身，不绑定具体模型或请求接口。`note` 在业务上可以没有内容，但键仍必须存在，用 `null` 表示没有值；业务中还应约定 `null` 与空字符串的区别。

```python
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "note": {"type": ["string", "null"]},
        "address": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    },
    "required": ["name", "note", "address"],
    "additionalProperties": False,
}

assert set(schema["required"]) == set(schema["properties"])
address = schema["properties"]["address"]
assert address["additionalProperties"] is False
assert set(address["required"]) == set(address["properties"])
```

离线断言只核对这里展示的约束，不能代替完整的 Schema 支持检查或真实请求验证。尤其是联合类型、引用和自动生成的大 Schema，还应逐项对照官方支持范围。

## 为什么加了 false 后下一个字段又报错

Schema 校验可能先暴露一个节点的问题。修复后继续指出另一个节点，不代表刚才的修改无效，而是还有其他对象没有满足要求。可以先缩减到一个小对象验证，再逐步加入嵌套对象、数组和联合类型，定位是哪一次扩展引入了差异。

不建议对整个 JSON 文本做字符串替换。`additionalProperties` 是 Schema 的结构化字段，把它插在错误层级可能产生新问题。若写脚本检查，应遍历对象定义并报告路径，再由开发者确认哪些节点需要修改。

如果业务原本需要任意键的字典，直接设为 false 可能改变数据模型。应考虑能否把动态键改成明确的键值项列表或其他受支持结构，同时保留业务含义，而不是只追求请求通过。

## Pydantic 和接口封装也要核对

SDK 提供的解析辅助方法与自己调用 `model_json_schema()` 后手动发送，可能走不同的转换流程。检查当前使用的方法、SDK 版本和发出的 Schema，而不是假设所有入口都会做相同处理。

Chat Completions 与 Responses 的结构化输出封装位置不同。Schema 本体正确，也可能因为外层参数放错而失败。应按当前接口文档构造请求；如果只是临时删除 strict 或退回普通 JSON 模式，要清楚记录结构约束已经改变。

## 请求通过后，还要验证什么

使用包含正常值、缺失业务信息和嵌套对象的少量样本验证输出。检查模型拒绝、响应未完成等情况，不能在所有分支里都直接解析成预期业务对象。结构正确也不意味着数字、名称或事实可靠。

若 API 已接受 Schema，但返回字段无法入库，可以继续阅读[JSON 字段与业务验收](../qwen-json-output-business-validation/)，其中的类型与事实核对思路可用于后续处理，具体接口参数仍按当前服务商文档确认。本文没有声称运行了付费 API 测试。

## 提问出处与官方依据

- [独立问题线索 1](https://community.openai.com/t/additionalproperties-error-when-unpacking-list-of-one-pydantic-object-in-union/953872)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [独立问题线索 2](https://community.openai.com/t/unexpected-additionalproperties-requirement-for-nested-pydantic-models-in-response-format/1151727)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [OpenAI 官方文档](https://developers.openai.com/api/docs/guides/structured-outputs)：按当前页面核对解决步骤。历史提问不代表当前所有环境都存在同一问题。

如需要进一步比较云端接口，可[注册 OpenLux 并核对适用能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=structured-outputs-additionalproperties-false-fix&utm_content=footer)。切换服务前单独验证接口与账户配置，不能据此认定原服务的问题已经修复。

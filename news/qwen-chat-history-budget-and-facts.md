---
layout: default
title: "Qwen 多轮对话越聊越长：历史裁剪、事实保留与上下文预算"
description: "为多轮对话设置历史和输出预算，按完整轮次裁剪并保留事实来源。"
permalink: /news/qwen-chat-history-budget-and-facts/
date: 2026-09-11
---

> 更新日期：2026-09-11 · 一手来源：[Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/multi-round-conversation)

# Qwen 多轮对话越聊越长：历史裁剪、事实保留与上下文预算

核验日期：2026 年 9 月 12 日。一个聊天功能刚开始工作正常，聊到后面变慢、成本增加，或者忘记早先约定，往往需要检查历史组织方式。本文讨论客户端维护消息历史的场景，提供可以实施的裁剪与回归方法。

如果你正在搭建自己的对话应用，可先[注册 OpenLux 并确认模型与账户配置](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=qwen-chat-history-budget-and-facts&utm_content=intro)，用短会话验证完整链路后再测试长历史。

## 先确定谁负责保存对话

阿里云[多轮对话文档](https://www.alibabacloud.com/help/en/model-studio/multi-round-conversation)展示了把用户消息和模型回复持续加入 messages 的方式，并提示长历史会消耗更多 token、可能超过上下文限制。本文采用这种显式传入历史的调用方式，不假设服务端自动记住前一轮。

查看第二次真实发出的请求：是否包含第一轮的问题和回答，角色顺序是否正确，是否把同一段历史重复追加两次。界面仍能显示旧消息，并不代表后端把它们正确发送给模型。

把显示记录与模型输入分开管理会更清楚。显示记录用于用户回看，模型输入则可以包含摘要与选定片段；两者都需要遵守会话所属用户的访问范围。

## 为输入和输出分别留空间

上下文预算不能只看用户最后一句话。固定指令、历史消息、检索材料和工具定义都可能占用输入空间，还要给预期输出保留余量。具体 token 计算方法和限制取决于所用模型及接口。

| 输入组成 | 是否通常需要保留 | 可以怎样缩减 |
|---|---|---|
| 系统规则 | 保留当前有效版本 | 删除重复或冲突的表述 |
| 最新问题 | 保留 | 只清理无意义重复 |
| 已确认事实 | 保留来源与有效性 | 用结构化记录替代冗长闲聊 |
| 较早对话 | 按当前问题相关性选取 | 摘要或按完整轮次裁剪 |
| 检索材料 | 保留有引用价值的片段 | 去重并限制片段数量 |
| 工具往返 | 保持协议完整 | 对已完成片段另行摘要 |

预算可以写成“可用窗口减去预留输出和安全余量”。这是一种规划方式，不表示所有厂商都用同样的扣减规则。模型独立输入上限、输出上限和其他约束也需要同时满足。

## 不要把一千个汉字直接当成一千 token

字符数、字节数和 token 数不同。用字符串长度限制请求只能提供粗略保护，不能作为账单依据。能够使用对应计数工具时先做预测，再用实际 usage 校准偏差。

建议给每轮记录模板版本、历史轮数、预计输入、实际输入、实际输出和响应耗时。当费用增加时，这些记录能区分是用户材料变长、历史重复拼接，还是回答长度发生变化。

如果没有可靠计数能力，可以先限制历史轮数与材料大小，采用保守预算，并把“估算”与“实测”分开。不要对用户承诺一个未经验证的固定长度一定不会超限。

## 从完整轮次开始裁剪

普通文本聊天可以先尝试保留最近若干完整问答轮次。以下离线示例的输入是已经成对整理的纯文本问答，不适用于带工具消息或多模态内容的协议校验。

```python
def recent_pairs(pairs, keep):
    if type(keep) is not int or keep < 0:
        raise ValueError("keep 必须是非负整数")
    for pair in pairs:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ValueError("每轮必须是用户与助手的二元组")
        if not all(isinstance(text, str) for text in pair):
            raise ValueError("本示例只接受纯文本")
    return list(pairs[-keep:]) if keep else []

sample = [("预算多少", "请提供范围"), ("三百以内", "已记录")]
assert recent_pairs(sample, 1) == [("三百以内", "已记录")]
assert recent_pairs(sample, 0) == []
assert len(sample) == 2
```

裁剪后仍要检查剩余内容的实际长度。最近一轮就可能包含很长的文件，保留十轮不是天然安全阈值。工具交互应以完整调用链为单位处理，不能随意丢掉与结果配对的消息。

## 摘要里保留事实和来源，不保留猜测

摘要建议分成已确认事实、尚未解决的问题、当前任务和来源位置。用户明确说过的条件可以保留，模型自己推测的偏好不能升级成用户事实。

当用户修正之前的信息时，应标记旧值失效，而不是让两个版本同时存在。比如用户先说预算三百，后来改为五百，摘要需要保留最新约束以及修正关系，避免后续回答继续使用旧预算。

摘要本身也会丢失信息。对号码、日期、金额和专有名词等关键字段，可以保留原文片段或可查的记录编号。摘要更新后抽查这些字段，不能仅因为文字更短就认为压缩成功。

## 用回归问题验证有没有忘记重要内容

建立一组长对话样本，在不同位置放入需要保留的事实，最后提出相关问题。分别运行不裁剪、保留最近轮次、摘要加片段三种策略，比较事实命中、错误引用和总用量。

测试中加入用户修改事实、撤回要求和资料缺失的情况。只测试“记住一句话”会忽略真正的业务难点：哪条信息当前有效，以及回答是否有证据。

上线后先观察有限流量，保存策略版本。如果新策略增加了事实错误，应能够回到上一版本，而不是继续扩大压缩比例。需要分析重复材料的费用时可看[缓存命中排查](https://a37836323.github.io/openlux-api-guides/news/qwen-context-cache-hit-troubleshooting/)；回答短缺则参考[结束原因判断](https://a37836323.github.io/openlux-api-guides/news/qwen-output-truncation-finish-reason/)。

[进入 OpenLux 准备对话测试账户](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=qwen-chat-history-budget-and-facts&utm_content=footer)，先验证历史是否正确传入，再讨论缩减成本。

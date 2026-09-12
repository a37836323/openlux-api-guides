---
layout: default
title: "No tool output found for function call 怎么修？Responses API 回传排查"
description: "检查 Responses 的 call_id、工具结果与响应链，定位多工具和流式中断后的缺失回传。"
permalink: /news/responses-no-tool-output-found-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/function-calling)

# No tool output found for function call 怎么修？Responses API 回传排查

遇到 `No tool output found for function call`，先核对报错中的调用标识，确认它有对应的工具结果被送回同一条响应链。Responses API 的自定义函数结果使用 `function_call_output`，关联字段是函数调用的 `call_id`，不是输出项的 `id`。工具在本地执行成功，也不代表结果已经成功提交给模型。

本文核验于 2026 年 9 月 12 日，讨论普通同步自定义函数调用。异步工具、托管工具和其他接口需按各自协议处理。如需另外评估兼容入口，可[查看 OpenLux 账户与模型入口](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=responses-no-tool-output-found-fix&utm_content=intro)，先确认 Responses 与所需工具能力是否受支持。

## 为什么看起来已经执行工具，仍提示没有输出

OpenAI 社区 2025 年 9 月有用户报告，在 Responses 请求中加入 conversation 后出现这条错误；10 月另一个用户报告流式连接中断，函数等待结果，后续会话无法继续。这些历史帖子是问题线索，不足以证明所有同名报错都由某个服务端缺陷造成。

排查时要区分三件事：模型发出了调用、应用执行了函数、应用把结果提交给正确的响应链。任一环节缺失，日志里的“工具执行完成”都不足以说明协议闭环已经完成。论坛中的清空会话建议也不能直接代替原因分析。

## 先检查 ID 和输出类型

| 字段或对象 | 在这里的作用 | 常见错误 |
|---|---|---|
| 函数调用项的 `id` | 标识输出项 | 错当成回传关联标识 |
| 函数调用项的 `call_id` | 关联函数调用与结果 | 自己生成新值或用错轮次 |
| `function_call_output` | Responses 的函数结果项 | 改成普通聊天文本 |
| 结果项的 `output` | 给模型读取的结果内容 | 只写本地日志，未放进输入 |
| 响应链或会话标识 | 保留调用发生的上下文 | 结果送进另一个会话 |

查看完整 `response.output`，不要只取第一项，也不要只读最终文字。一次响应可以产生多次函数调用，需要逐项处理。若使用推理模型并自行维护输入历史，官方要求把与工具调用一起返回的推理项也带回后续输入。

## 一个不调用 API 的回传检查示例

下面只验证本地构造逻辑。模拟的响应项带有不同的 `id` 和 `call_id`，结果必须与后者一致。真实应用要在参数校验及实际工具执行后生成结果，不能照搬模拟值。

```python
import json

def make_outputs(calls, results):
    outputs = []
    seen = set()
    for item in calls:
        if item.get("type") != "function_call":
            continue
        call_id = item["call_id"]
        if call_id in seen:
            raise ValueError("同一批次出现重复调用标识")
        seen.add(call_id)
        if call_id not in results:
            raise ValueError("尚有工具结果没有完成")
        outputs.append({
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(results[call_id], ensure_ascii=False),
        })
    return outputs

calls = [
    {"type": "function_call", "id": "fc_demo", "call_id": "call_demo"}
]
results = {"call_demo": {"stock": 3} }
outputs = make_outputs(calls, results)
assert outputs[0]["call_id"] == "call_demo"
assert outputs[0]["call_id"] != calls[0]["id"]
assert json.loads(outputs[0]["output"])["stock"] == 3
try:
    make_outputs(calls, {})
except ValueError:
    pass
else:
    raise AssertionError("缺失结果应被识别")
```

将这些结果提交给包含原函数调用的后续请求。可以按官方示例通过前一响应续接，也可以自行维护完整输入项；不要只发送结果，却把它对应的调用上下文丢掉。这里只执行了离线断言，没有声称验证了任何付费接口。

## 多工具与流式中断怎么排查

本文建议先为每次调用保存响应标识、`call_id`、工具名和执行状态。多工具场景先列出本轮所有预期回传项，再与实际准备提交的结果集合比较。不要因为第一个工具完成，就把其余尚未处理的调用遗忘。

流式场景要区分参数增量和完成事件，避免 JSON 参数还没接收完整就执行函数。浏览器断开时，也应检查服务端任务是否仍在继续、结果是否已保存、续接请求是否真正发出。客户端关闭不等于工具从未执行过。

如果工具会创建订单、修改文件或调用其他有副作用的服务，恢复前先查询执行记录。盲目重跑可能让同一个业务动作发生两次。只读工具也应保留完成结果，减少恢复时重复请求和混乱日志。参数正确性可继续阅读[工具调用参数校验](../tool-call-arguments-validation-contract/)。

## 历史会话已经卡住怎么办

先保存脱敏后的调用与结果项，核对缺少的是哪次回传。若实际函数失败，就按应用约定回传清楚的失败结果，不要伪造执行成功。若函数已经执行成功但提交结果失败，优先研究如何把已有结果提交回正确链路，而不是再次执行函数。

当历史状态无法解释时，用新的最小测试会话比较同一工具定义，帮助区分定义问题与历史链问题。新会话能运行，并不说明原会话可以安全删除。保留原始记录，再按官方接口能力处理恢复；不要为了消除错误丢弃未核对的业务操作。

正常恢复应同时满足：报错指向的调用有匹配结果、下一步请求被接受、模型能继续处理结果、业务侧没有重复执行记录。若仍失败，提交脱敏的请求顺序、SDK 版本、request ID 和时间，比单独截取错误句更有帮助。

准备切换入口时，可[注册 OpenLux 并核验所需接口能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=responses-no-tool-output-found-fix&utm_content=footer)。先以独立测试会话验证，不假设不同服务之间可以共享已有响应或会话标识。

## 提问线索与官方依据

- [OpenAI 社区：conversation 与自定义函数场景的报错，2025-09-25](https://community.openai.com/t/its-a-bug-its-an-error-or-it-is-not-possible-to-combine-custom-function-with-conversations-in-responses/1359941)。不采用帖内转述的支持助手回复作为官方结论。
- [OpenAI 社区：流式连接中断后的工具结果缺失，2025-10-06](https://community.openai.com/t/how-to-handle-hanging-connection-conditions/1361157)。
- [OpenAI：Function calling](https://developers.openai.com/api/docs/guides/function-calling)，核对调用、回传和推理项要求。
- [OpenAI：Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)，核对会话状态维护方式。

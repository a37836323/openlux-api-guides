---
layout: default
title: "API 429 与流式中断实战：什么能自动重试，什么重试一次就可能出事故"
description: "API 429、流式中断与安全重试实战"
permalink: /rate-limit-stream-retry/
date: 2026-08-24
---

# API 429 与流式中断实战：什么能自动重试，什么重试一次就可能出事故

接入大模型 API 后，最容易被低估的不是“怎么发请求”，而是“请求失败以后怎么办”。

很多系统的处理方式是：只要报错，就重试 3 次。这个策略看起来稳妥，实际上可能制造三类新问题：

- 额度已经耗尽，却持续发送注定失败的请求；
- SDK 已经自动重试，业务代码又重试，实际请求次数被放大；
- 流式输出已经生成一半，程序重新请求，用户看到重复内容，写数据库或调用工具时甚至产生重复副作用。

真正可靠的原则只有一句：**先判断失败发生在哪个阶段，再决定能否重试。**

## 一张表先说清楚

| 失败情况 | 是否自动重试 | 推荐处理 |
| --- | --- | --- |
| 临时 429 限流，响应包含 `Retry-After` | 可以 | 等待指定时间，限制总次数和总等待时间 |
| 429 额度、余额或消费上限不足 | 不可以 | 停止请求，检查余额、项目限额和账单配置 |
| 首个 token 返回前连接失败 | 通常可以 | 在请求没有外部副作用时，做有限重试 |
| 已经收到部分流式内容后中断 | 不应直接重放 | 保留部分结果，让用户选择继续生成或重新开始 |
| 5xx，且尚未收到任何结果 | 通常可以 | 指数退避并加入随机抖动 |
| 会写数据库、发邮件、下单或调用外部工具 | 不可盲目重试 | 先实现幂等键、状态机或去重机制 |
| 参数错误、模型不存在、权限错误 | 不可以 | 修正请求，重试相同内容没有意义 |

这里最关键的一点是：**429 不只有一种。** 临时速率限制和余额不足都可能表现为 429，但处理方式完全相反。

## 先确认 SDK 是否已经替你重试

OpenAI 官方 SDK 会对部分可恢复错误进行有限重试，并会参考服务端返回的重试等待信息。如果业务层又套一层循环，很容易出现“以为请求 3 次，实际远不止 3 次”的情况。

非流式、没有副作用的普通请求，可以先从 SDK 的有限重试开始：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENLUX_API_KEY"],
    base_url="https://api.openlux.ai/v1",
    max_retries=2,
    timeout=30.0,
)

response = client.chat.completions.create(
    model="gpt-5.6-terra",
    messages=[
        {"role": "user", "content": "把这段会议记录整理成待办事项。"}
    ],
)

print(response.choices[0].message.content)
```

这段代码适合“请求失败后重新执行也不会造成额外影响”的任务。`max_retries=2` 也不是越大越好：失败请求仍会占用速率配额，过度重试会让拥塞更严重。

如果你已经使用任务队列、网关重试或业务层重试，建议把每层的次数列出来，明确只保留一个主要重试层。否则：SDK 2 次 × 网关 3 次 × 任务队列 3 次，最坏情况会被成倍放大。

## 429 到底是“等一下”，还是“别再发了”？

不能只看 HTTP 状态码，还要记录响应体里的错误类型和说明。

### 可以等待后重试

典型特征是请求速率或 token 速率暂时超过限制。此时应：

1. 优先读取 `Retry-After`；
2. 没有该字段时使用指数退避；
3. 加入随机抖动，避免大量进程同时再次请求；
4. 限制最大尝试次数和总等待时长；
5. 从源头限制并发，而不是只在失败后补救。

一个用于“自定义 HTTP 客户端”的简化等待函数如下。若使用官方 SDK，不要再无条件套用一次相同逻辑。

```python
import random
import time

def retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass

    base = min(2 ** attempt, 30)
    return base + random.uniform(0, 0.5)

for attempt in range(4):
    response = send_request()  # 替换成自己的 HTTP 请求函数

    if response.status_code != 429:
        break

    error_text = response.text.lower()
    if "quota" in error_text or "billing" in error_text:
        raise RuntimeError("额度或账单限制，停止自动重试")

    if attempt == 3:
        raise RuntimeError("临时限流持续存在，交给队列稍后处理")

    time.sleep(retry_delay(attempt, response.headers.get("Retry-After")))
```

生产环境不要只靠字符串判断。应根据你实际使用的服务返回结构，对错误 `type`、`code` 和消息做明确分类；未知的 429 默认进入人工可观察的失败队列，不要无限循环。

### 不应该重试

如果错误指向余额不足、消费上限、组织或项目额度限制，等待几秒不会改变结果。正确动作是：

- 暂停对应队列，避免继续积累失败请求；
- 检查网关余额、上游额度、项目预算和用量上限；
- 给运维或负责人发一次聚合告警，而不是每次请求都报警；
- 恢复后先用一个最小请求验证，再逐步放开并发。

## 流式请求为什么最危险

非流式请求失败时，通常可以认为“没有向用户交付结果”。流式请求不同：连接断开时，用户可能已经收到 300 个字。

如果程序直接重新发起同一个请求，会出现：

- 前半段重复；
- 第二次回答的结构和第一次不一致；
- token 成本增加；
- 下游解析器收到两个不完整对象；
- 如果模型已经触发工具调用，外部动作可能执行两次。

因此流式处理至少要维护两个状态：`是否收到过内容` 和 `是否产生过外部副作用`。

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENLUX_API_KEY"],
    base_url="https://api.openlux.ai/v1",
    max_retries=0,  # 流式阶段由应用显式判断是否允许重试
    timeout=45.0,
)

def stream_answer(messages):
    received_text = False

    try:
        stream = client.chat.completions.create(
            model="gpt-5.6-terra",
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            text = chunk.choices[0].delta.content or ""
            if text:
                received_text = True
                yield text

    except Exception as exc:
        if received_text:
            # 不自动重放；把部分结果和失败状态交给前端处理
            raise RuntimeError("流已部分输出，请选择继续生成或重新开始") from exc
        raise  # 首个 token 前失败，可由外层做一次有限重试
```

更好的用户体验不是悄悄重放，而是在页面上保留已生成内容，并提供两个明确按钮：

- “从中断处继续”：把已有内容作为上下文，请模型续写；
- “重新生成”：用户确认后清空旧结果，再发起新请求。

续写也不是数学意义上的无缝恢复，但它比后台自动重放更透明、更可控。

## 有外部副作用时，先谈幂等再谈重试

如果模型只是总结文字，重试的风险主要是成本和重复内容。如果模型可以调用“创建订单”“发送邮件”“写入 CRM”等工具，风险就完全不同。

建议为每个业务动作生成唯一幂等键，例如：

```text
customer_id + task_type + business_date + source_event_id
```

执行工具前查询该幂等键是否已经成功；执行中记录 `processing`；完成后记录结果。即使模型或任务队列再次提交，同一个业务动作也只落地一次。

不要把模型生成的随机文本当幂等键，也不要只依赖“提示词要求模型不要重复调用”。防重复必须由业务系统保证。

## 与其失败后狂重试，不如先控制并发

对批量任务，一个简单的并发闸门往往比复杂重试策略更有效：

```python
import asyncio

semaphore = asyncio.Semaphore(5)

async def guarded_call(call_api, payload):
    async with semaphore:
        return await call_api(payload)
```

实际并发数不能照抄 `5`。应该根据账号限额、单次请求 token 量、模型响应时间和真实 429 比例逐步调整。若任务量有明显峰谷，再增加队列和速率整形，让请求平滑进入 API。

## 最少要记录哪些诊断信息

日志里建议至少保留：

- 自己生成的任务 ID 和客户端请求 ID；
- 请求主机、接口路径、模型名；
- HTTP 状态码、错误类型和错误码；
- 服务端请求 ID，例如 `x-request-id`；
- 当前是第几次尝试、SDK 是否开启自动重试；
- 是否已经收到首个 token；
- 是否已经执行工具或产生外部副作用；
- 总耗时与最终处理方式。

不要记录完整 API Key，也要谨慎记录用户原文。排查问题需要的是请求链路标识，不是把敏感数据复制到日志里。

## 上线前的 6 个故障演练

不要等生产事故发生才验证重试逻辑。上线前至少手动模拟：

1. 使用错误 Key，确认 401 不重试；
2. 使用余额不足的测试渠道，确认额度类 429 不重试；
3. 人为限制并发，确认临时 429 会等待且次数有上限；
4. 首个 token 前断网，确认只进行有限重试；
5. 输出一半后断网，确认页面保留部分内容且不自动重放；
6. 同一个工具调用提交两次，确认业务侧只执行一次。

只要这 6 项真实走通，系统的可靠性通常会比“所有异常统一重试 3 次”高一个层级。

## 最后的落地建议

如果现在只能改一件事，我建议先给失败请求增加结构化分类：`不可重试`、`首个输出前可重试`、`已部分输出需人工选择`、`有副作用需幂等`。有了分类，重试次数、告警和队列策略才有可靠基础。

如果你希望用统一兼容接口做一次低成本故障演练，可通过下面的专属入口注册 OpenLux，再为测试单独创建一个低余额、低权限渠道，避免影响生产 Key：

https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=rate_limit_stream_retry&utm_content=footer

建议先跑最小请求和上述 6 个故障场景，再接入正式业务。本文中的重试次数与并发数是示例，不是适用于所有账号的固定参数。

## 参考资料

- OpenAI API 错误说明：https://developers.openai.com/api/docs/guides/error-codes
- OpenAI API 速率限制建议：https://developers.openai.com/api/docs/guides/rate-limits
- OpenAI API 请求诊断：https://developers.openai.com/api/reference/overview#debugging-requests
- OpenLux 当前模型与接口信息：https://api.openlux.ai/api/pricing

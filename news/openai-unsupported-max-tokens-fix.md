---
layout: default
title: "OpenAI 报 Unsupported parameter: max_tokens 怎么改？两个接口别填错"
description: "按实际端点区分 max_completion_tokens 与 max_output_tokens，排查旧模板和 Batch 请求体。"
permalink: /news/openai-unsupported-max-tokens-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

# OpenAI 报 Unsupported parameter: max_tokens 怎么改？两个接口别填错

如果完整报错要求使用 `max_completion_tokens`，先检查请求是不是发往 `/v1/chat/completions`。在这个接口中按当前模型要求移除 `max_tokens`，改用 `max_completion_tokens`；如果实际调用的是 Responses API，则对应的输出上限字段是 `max_output_tokens`。改完后确认发送出去的请求体，不能只看配置页面上的名称。

本文核验于 2026 年 9 月 12 日，适用于 OpenAI 官方 API 的参数排错。如果使用兼容服务，可[查看 OpenLux 账户与模型入口](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-unsupported-max-tokens-fix&utm_content=intro)，再核对该入口明确支持的接口和字段；兼容名称不代表所有参数行为相同。

## 这是什么真实问题

OpenAI 社区 2024 年 9 月的模型迁移讨论中，用户贴出了 `max_tokens` 不受支持的报错。2025 年 2 月，又有用户在 Batch API 中给 o3-mini 提交请求时遇到同类错误。不同场景的共同点是：换了模型，旧请求模板中的输出长度参数继续原样发送。

本文只使用这些帖子证明问题确实被提出过。帖子中的旧模型角色限制、温度设置和上线权限，不应直接套到当前模型上。下面的字段区别已按当前官方参考文档重新核对。

## 先区分三个长度字段

| 你实际调用的接口 | 应核对的字段 | 容易混淆的地方 |
|---|---|---|
| Chat Completions | `max_completion_tokens` | 官方将旧 `max_tokens` 标为弃用，且不兼容 o 系列 |
| Responses | `max_output_tokens` | 不能把 Chat 的参数直接搬过来 |
| 第三方兼容服务 | 服务商与具体模型文档 | 前端同名设置可能被转换 |
| Batch 中的单条请求 | 单条请求的目标接口 | 批次外层不是生成参数的放置位置 |

Chat 的完成 token 上限包含可见输出和推理 token。不要把数值理解成汉字数，也不要认为设为某个数值就会输出相同数量的可见文字。输出限制与输入上下文上限属于不同问题。

## 在请求发出的位置改参数

先记录 HTTP 路径，再查看应用最终序列化的请求体。很多项目在页面、业务函数和 SDK 封装中各有一层默认值：你删掉业务函数的旧参数，公共封装仍可能把它补回去。检查最终字段名，能发现这种“代码改了，线上还是同一个错误”的情况。

建议把单次请求缩减为模型、输入和一个输出上限参数，暂时移除与本次报错无关的可选参数，确认基础请求格式正确。不要同时发送新旧两个上限字段来碰运气，也不要在未查看请求的情况下全局替换项目中的 `max_tokens`，因为其他服务可能仍使用该字段。

下面是离线构造请求体的示例，不调用网络，也不指定读者账户未必可用的模型。`chosen-model` 仅表示应从账户目录选择的模型 ID，实际请求前必须替换。

```python
def build_payload(endpoint, model, limit):
    if type(limit) is not int or limit <= 0:
        raise ValueError("输出上限需要正整数")
    payload = {"model": model}
    if endpoint == "/v1/chat/completions":
        payload["messages"] = [{"role": "user", "content": "回复一句问候"}]
        payload["max_completion_tokens"] = limit
    elif endpoint == "/v1/responses":
        payload["input"] = "回复一句问候"
        payload["max_output_tokens"] = limit
    else:
        raise ValueError("请先核对目标接口")
    return payload

chat = build_payload("/v1/chat/completions", "chosen-model", 512)
responses = build_payload("/v1/responses", "chosen-model", 512)
assert "max_tokens" not in chat
assert "max_output_tokens" not in chat
assert responses["max_output_tokens"] == 512
assert "max_completion_tokens" not in responses
try:
    build_payload("/v1/responses", "chosen-model", True)
except ValueError:
    pass
else:
    raise AssertionError("布尔值不应作为长度")
```

示例里的 512 是演示值，不是各模型通用的推荐预算。代码只验证字段分流和输入检查，不能证明具体模型已经支持这些请求。

## Batch 报错要改哪一层

如果错误来自批处理，先找到失败行的 `custom_id`，检查该行请求的 URL 和 body。目标是 Chat Completions 的任务，应在该行 body 中修改生成参数，而不是只给整个批次的创建请求增加一个长度字段。

修正生成 JSONL 的模板后，先取少量失败样本核对序列化结果，再创建验证批次。不要把已经成功的记录混进补跑文件，否则会重复产生输出和费用。保存原批次 ID、失败行标识和补跑对应关系，后续可按[批次结果核对教程](../batch-ai-jobs-result-reconciliation/)归并结果。

## 改过后为什么仍然失败

报错仍明确指向 `max_tokens` 时，优先排查旧进程、旧构建产物、插件默认值或网关参数转换。报错已经变成其他字段时，说明排查进入下一层，应按新错误检查模型要求，而不是不断增加输出上限。

如果服务端报错变成了 SDK 的“unexpected keyword argument”，核对当前运行环境加载的 SDK 版本及对应方法签名。保留报错层级：本地函数拒绝参数和远端 API 拒绝请求，需要修的位置不同。更新依赖后也应确认运行进程使用的是更新后的环境。

验证成功的标准是：最终请求不再带错误字段，API 接受请求，并且你能处理返回的完成状态。出现截断时，再研究结束原因、推理预算和任务长度，不要把“参数名改对”与“回答一定完整”混为一谈。

如准备在另一个服务商复测，可[注册 OpenLux 并核对接口支持范围](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-unsupported-max-tokens-fix&utm_content=footer)。保留一份服务商、端点与模型参数的对应配置，避免把官方请求模板无条件复用到其他入口。

## 提问线索与官方依据

- [OpenAI 社区：模型迁移时的参数报错，2024-09-24](https://community.openai.com/t/o1-models-do-not-support-system-role-in-chat-completion/953880)。本文仅引用其中长度参数问题。
- [OpenAI 社区：Batch 中 o3-mini 报 max_tokens 不兼容，2025-02-18](https://community.openai.com/t/reasoning-effort-high-how-to-add-this-in-the-batchapi-for-o3-mini-model/1123650)。
- [OpenAI：Chat Completions 参数参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)。
- [OpenAI：429 排查中的接口输出参数说明](https://help.openai.com/en/articles/5955604)。
- [OpenAI：迁移到 Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)。迁移还涉及输入与输出结构，不能只替换长度字段。

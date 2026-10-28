---
layout: default
title: "OpenAI 报 400「Invalid service_tier argument」怎么办：项目限制了服务等级的排查与改法"
description: "OpenAI 返回 400「Invalid service_tier argument」是因为请求指定或解析出的服务等级被项目/组织设置禁用。按写了 flex/priority/fast、没写或 auto、Flex 降级重试、组织禁用四种情况给出改法和验证方法。"
permalink: /news/openai-invalid-service-tier-argument-400-fix/
date: 2026-10-28
---

> 更新日期：2026-10-28 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/error-codes)

# OpenAI 报 400「Invalid service_tier argument」怎么办：项目限制了服务等级的排查与改法

结论先说：这个 400 一般不是参数写错，而是这次请求指定的服务等级，或者请求最终落到的服务等级，被项目或组织设置禁用了。OpenAI 在 2026 年 10 月 21 日的更新日志里宣布，可以在 Platform 设置里为每个项目选择允许使用的服务等级，组织级设置也能限制所有项目，并为此在错误码文档里加了这一条。官方给的改法有两种：把 `service_tier` 改成项目允许的等级，或者在项目设置里放开需要的等级。

本文适用于直接用 OpenAI API Key 调用 Responses 或 Chat Completions、请求里写了 `service_tier`（`flex`、`priority`、`fast`、`default`、`auto`）或者干脆没写的项目。依据是 OpenAI 官方的 [错误码文档](https://developers.openai.com/api/docs/guides/error-codes)、[Responses 创建接口参考](https://developers.openai.com/api/reference/resources/responses/methods/create)、[Fast mode 指南](https://developers.openai.com/api/docs/guides/fast-mode)、[Flex processing 指南](https://developers.openai.com/api/docs/guides/flex-processing) 和 [API 更新日志](https://developers.openai.com/api/docs/changelog)。

## 一、先确认是不是这个报错

错误码文档写明，返回的是 `invalid_request_error`，`error.param` 为 `service_tier`，消息原文是：

> Invalid `service_tier` argument: The requested service tier is not allowed for this project.

下面几个报错都和服务等级、容量有关，处理方式完全不同，先对一下：

| 报错 | HTTP 状态 | 识别方法 | 官方说明的原因 | 处理 |
|---|---|---|---|---|
| Invalid `service_tier` argument | 400 | `type` 为 `invalid_request_error`，`param` 为 `service_tier` | 指定的或解析后的服务等级不被项目允许 | 改成允许的等级，或更新项目允许的等级 |
| Resource Unavailable（Flex） | 429 | Flex 请求资源不足时返回 | Flex 资源暂时不足，这次不收费 | 指数退避重试，或改用 `auto` / 去掉 `service_tier` 走标准处理 |
| Slow down | 429 | `type` 为 `rate_limit_error`，`code` 为 `slow_down` | 请求速率涨得太快 | 按 `Retry-After` 降速，再逐步加量 |
| Model temporarily overloaded | 503 | `code` 为 `server_is_overloaded` | 模型暂时过载 | 按 `Retry-After` 等待后重试 |

错误码文档对这个 400 给出的解决办法只有改请求和改设置两条，没有提到重试。所以应先改参数或设置，再重发请求。

## 二、这次请求实际按哪个等级判断

很多人卡在「我根本没写 `service_tier` 也报错」。原因是不写也会解析成一个等级。按接口参考和错误码文档整理如下：

| 请求里的 `service_tier` | 实际按哪个等级判断 | 官方依据 |
|---|---|---|
| 不写 | 等同 `auto` | 接口参考：不设置时默认行为是 `auto` |
| `auto` | 项目设置里配置的服务等级；没改过就是 `default` | 接口参考 |
| `default` | 标准价格和性能 | 接口参考 |
| `flex` | Flex 处理 | 接口参考、Flex 指南 |
| `fast` | 按 `priority` 判断 | 错误码文档：`fast` 按 `priority` 评估 |
| `priority` | `priority` | Fast mode 指南：Priority processing 于 2026-07-30 改名为 Fast mode，两个值都能用 |
| Scale Tier | 不受这项项目策略约束 | 错误码文档 |

错误码文档写明，项目限制只作用于 `default`、`flex`、`priority` 三个等级；文档没有提到 `ultrafast` 是否受这项限制。

## 三、按请求写法分支排查

**分支 A：请求里明确写了 `flex`、`priority` 或 `fast`。** 说明这个项目不允许该等级。注意 `fast` 和 `priority` 是同一个判断：项目禁用了 `priority`，写 `fast` 一样报错。改法是换成项目允许的等级。如果直接删掉这个参数，请求会按 `auto` 走项目配置的等级，那个等级也被禁用的话，报错不会消失。

**分支 B：没写 `service_tier`，或者写的是 `auto`。** 错误码文档专门说明，这类请求解析到被禁用的等级时同样会返回这个 400。比如管理员只给项目留了 `flex`，而项目配置的服务等级还是默认的 `default`，那么所有没写 `service_tier` 的老代码都会报错。官方的处理是更新项目设置，让解析出来的等级被允许；也可以在请求里明确写一个项目允许的等级。

**分支 C：Flex 遇到 429 后降级重试，重试反而报 400。** Flex 指南建议在 429 Resource Unavailable 时把 `service_tier` 改成 `auto` 或去掉它，用标准处理重试。如果项目不允许这条重试路径最终落到的等级（例如 `default`），重试就会变成这个 400。上线 Flex 降级逻辑前，先确认重试要用的等级在项目允许列表里。

**分支 D：想在项目设置里打开某个等级，但打不开。** 错误码文档写明「Projects cannot enable tiers blocked by the organization」，组织禁用的等级，项目无法单独开启。这时要请组织管理员在 [组织设置的服务等级部分](https://platform.openai.com/settings/organization/general#service-tiers) 放开。

## 四、修改步骤

1. 记下报错请求的三项信息：`model`、`service_tier`（有没有写、写的什么）、用的是哪个项目的 API Key。
2. 打开 [项目设置](https://platform.openai.com/settings/) 和 [组织设置](https://platform.openai.com/settings/organization/general#service-tiers)，查看允许的服务等级。项目允许列表受组织设置约束。
3. 二选一：
   - 不改设置：在请求里把 `service_tier` 改成允许的等级。
   - 改设置：有权限的话，在项目设置里放开需要的等级；组织禁用的，找组织管理员。
4. 如果依赖 `auto` 或不写参数，再看一下项目配置的服务等级。Fast mode 指南写明，该项在 Settings → Project 下的 General 里，名为 **Project Service Tier**；设成 Fast 后，不写 `service_tier` 的请求默认走 Fast mode。这个值对应的等级必须在允许列表里。

请求里显式指定等级的写法和官方示例一致，以 Python 为例：

```python
from openai import OpenAI

client = OpenAI()
response = client.responses.create(
    model="gpt-6.1-sol",
    input="ping",
    service_tier="default",  # 改成项目允许的等级
)
print(response.service_tier)
```

Chat Completions 同样接受 `service_tier` 参数，写法相同。

## 五、怎么确认改好了

- **成功标准一**：同一个请求返回 200，不再出现 `param` 为 `service_tier` 的 400。
- **成功标准二**：看响应体里的 `service_tier`。接口参考写明，设置了 `service_tier` 时，响应里返回的是实际处理这次请求的等级，可能和请求里写的不一样。Fast mode 指南提到两种正常情况：GPT-5.6 及更早的模型，请求写 `fast` 时响应返回 `priority`；Fast mode 流量增长太快时，部分请求会降到标准速度并按标准价格计费，响应里显示 `default`。这两种都不是报错。
- **成功标准三**：在用量面板按 service tier 分组，确认请求落在预期的等级上。

## 六、常见误区

| 误区 | 实际情况 |
|---|---|
| 以为值拼错了 | 值合法也会报，原因是项目不允许这个等级 |
| 只放开了 `fast` 相关设置，没管 `priority` | `fast` 按 `priority` 判断，两者是同一个开关 |
| 删掉 `service_tier` 就一定好 | 不写等于 `auto`，会落到项目配置的等级，那个等级也可能被禁 |
| 以为 Scale Tier 也受限 | 错误码文档写明 Scale Tier 不在这项项目策略内 |
| 把 Flex 的 429 当成这个 400 处理 | Flex 429 是资源暂时不足，可以退避重试；这个 400 需要改参数或设置 |

如果你调用的是第三方中转，项目和组织设置在中转方手里，第四节的设置步骤你改不了。中转是否透传 `service_tier`、是否会原样返回这个 400，本文没有核实。遇到时先去掉 `service_tier` 发一个最小请求确认，仍然报错就把完整报错信息发给中转方。价格方面，Flex 和 Fast mode 的计费规则以 [官方价格页](https://developers.openai.com/api/docs/pricing) 为准。

## 官方来源

- [Error codes：400 - Invalid service_tier argument](https://developers.openai.com/api/docs/guides/error-codes)
- [Responses 创建接口参考：service_tier 参数](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Fast mode 指南（Project Service Tier、响应里的 service_tier、降级说明）](https://developers.openai.com/api/docs/guides/fast-mode)
- [Flex processing 指南（429 Resource Unavailable 与降级重试）](https://developers.openai.com/api/docs/guides/flex-processing)
- [API 更新日志（2026-10-21 项目服务等级限制）](https://developers.openai.com/api/docs/changelog)

需要一个 OpenAI 兼容地址来调用 GPT、Claude 等模型，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-invalid-service-tier-argument-400-fix&utm_content=footer)。

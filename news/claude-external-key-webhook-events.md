---
layout: default
title: "Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？"
description: "Claude 组织 Webhook 新增 external_key.failed 与 external_key.recovered，用于监测客户管理加密密钥被 KMS 拒绝及恢复。"
permalink: /news/claude-external-key-webhook-events/
date: 2026-11-23
---

> 更新日期：2026-11-23 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#encryption-key-webhook-events)

# Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？

可以。Claude Platform 在 2026 年 11 月 16 日给 organization webhooks（目前是 beta）加了两个事件：你的 KMS 持续拒绝 Anthropic 使用某个客户管理加密密钥（CMEK）时，发送 `external_key.failed`；之后密钥重新可用时，发送 `external_key.recovered`。

但官方文档写得很明确：**不要把这两个事件当作唯一信号**。它们通常要几十分钟才到，有几种情况会漏发，收到后也要自己调用校验接口和发请求确认。本文按 [Claude 官方发版说明](https://platform.claude.com/docs/en/release-notes/overview#encryption-key-webhook-events) 和 [Organization webhooks 文档](https://platform.claude.com/docs/en/manage-claude/organization-webhooks) 讲清楚：前提、怎么订阅、事件内容、收到后怎么处理、什么时候会漏、怎么补查。

适用对象：在 Claude Platform（Claude API）上自己有组织、并且已经用 CMEK 的管理员和运维。这里调用的是 Anthropic 官方的组织管理接口，要用你自己组织的管理凭据，不是第三方中转平台的 API Key。

## 前提：组织要先开通 organization webhooks

官方列的条件，按顺序取第一个符合的：

- 组织开了 HIPAA readiness：不能使用 organization webhooks。
- 组织可以使用客户管理加密密钥：已经有 organization webhooks。
- 其他组织：联系 Anthropic 客户团队申请。

没开通时，相关请求返回 `404`。凭据三选一：

- Admin API Key；
- 带 `org:admin` 范围的 OAuth 令牌（如果令牌绑定的不是组织的 Default Workspace，所有请求都不能做）；
- 不限定工作区的个人或服务账号 Key：列出、查看端点需要 `developer` 或 `admin` 角色；创建、修改、删除端点或更换签名密钥需要 `admin`。

每个请求都要带 `anthropic-beta: webhooks-2026-10-07` 请求头，官方 SDK 和 CLI 会自动带上。

## 订阅两个事件：Admin API 或 Console

用 `POST /v1/organizations/webhooks` 创建端点，在 `enabled_events` 里列出这两个事件类型。官方示例订阅的是另外两个用户档案事件，并说明要收加密密钥事件就把它们换成 `external_key.failed` 和 `external_key.recovered`：

```bash
curl "https://api.anthropic.com/v1/organizations/webhooks" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2026-10-21" \
  -H "anthropic-beta: webhooks-2026-10-07" \
  -H "content-type: application/json" \
  -d '{"url": "https://example.com/anthropic-webhooks", "name": "CMEK alerts", "enabled_events": ["external_key.failed", "external_key.recovered"]}'
```

要求和注意点：

- `url` 必须是 HTTPS、443 端口、公网域名，不能写 IP；同一组织里两个启用中的端点不能用同一个 URL。
- 一个组织最多 32 个端点，已禁用的也算。
- 响应里的 `signing_secret`（`whsec_` 开头）只在创建端点和更换密钥时返回一次，要妥善保存。
- 有组织 `admin` 角色的话，也可以在 Claude Console 的 Webhooks 页面「Organization」标签里管理加密密钥事件的端点。

创建或修改报错时对照下表：

| 状态码 | 官方列出的原因 |
|---|---|
| 400 | `url` 不合规、创建时没列事件类型、组织没有 Default Workspace、会超过 32 个端点、`enabled_events` 里有不接受的事件类型 |
| 403 | 账号角色缺少该请求需要的权限，报错会写出缺哪个权限 |
| 404 | 没带 beta 请求头、组织没开通、组织开了 HIPAA readiness、凭据类型不被接受、端点 ID 不存在 |
| 409 | 会让两个启用中的端点共用 URL，或别的请求同时在改端点（重试即可） |

## 事件内容和投递规则

| 事件 | 官方触发条件 |
|---|---|
| `external_key.failed` | KMS 持续拒绝 Anthropic 使用某个密钥，例如有人停用了密钥或撤掉了 Anthropic 的访问权限 |
| `external_key.recovered` | 在发过 `external_key.failed` 之后，Anthropic 再使用该密钥时恢复正常 |

- 事件用 `data.id` 标识密钥，以 `ekey_` 开头；事件里**不写工作区**，因为多个工作区可能共用一个密钥。
- `created_at` 是 Anthropic 第一次尝试发送的时间，不是密钥失效或恢复的时间。
- 只有真实的拒绝才会触发，**没有测试事件**。
- 密钥失效或恢复时，Anthropic 通常还会给能管理加密密钥的成员发邮件；失败邮件会列出近期被拒的工作区，但可能不全。

投递遵循 Standard Webhooks 规范，带 `webhook-id`、`webhook-timestamp`、`webhook-signature` 三个请求头：

- 先用端点的签名密钥验签，再信任事件内容。
- 5 秒内返回任意 `2xx`，耗时的处理放到之后做；其他响应或不响应都算失败。
- 同一事件可能收到多次，事件 `id` 与 `webhook-id` 相同，按它去重。
- 失败会在几分钟内重试几次，全部失败就丢弃；端点返回 `3xx`、URL 解析到非公网 IP 或持续失败时会被自动禁用，禁用期间的事件不会补发。Anthropic 不会通知你丢弃或禁用。

## 收到事件后怎么处理（官方流程）

1. 先返回 `2xx`。
2. 用 `data.id` 调用 `POST /v1/organizations/external_keys/{external_key_id}/validate` 校验密钥，凭据用 Admin API Key 或 `org:admin` 令牌。
3. 看响应里的 `status`：
   - `failure` 且 `error` 提示重试：照做，再校验一次；
   - `failure` 且是其他提示：按官方 Troubleshoot CMEK 文档排查；
   - `success`：还要逐个检查用这个密钥的工作区，因为一次校验最多只测一个工作区（例如 AWS 密钥策略里按工作区列权限时，KMS 可能只拒绝其中几个）。
4. 检查工作区：用 `include_default=true` 列出工作区，找出 `external_key_id` 是该密钥的，在每个工作区里用能访问该工作区的 API Key 发一个 Messages API 请求。

| 请求结果 | 对这个工作区意味着 |
|---|---|
| `cmek_key_disabled` 或 `cmek_key_network_blocked` 错误 | 你的 KMS 拒绝 Anthropic |
| `cmek_key_unreachable` 错误 | Anthropic 连不上你的 KMS |
| 成功 | 密钥可用，或者失效还不到 1 小时 |

密钥失效后最长 1 小时内请求仍可能成功，所以请求成功时，要在 `external_key.failed` 之后一小时再发一次。修好之后，报错也可能再持续几分钟。修复后重复上面的检查，**不要等 `external_key.recovered`**，它可能不会来。

## 事件多久到、什么时候会漏

官方给的参考时间（前提是每个用该密钥的工作区大约每分钟有一次 Messages API 请求；流量更少会更慢）：

- `external_key.failed`：停用密钥或撤权后 30 分钟内，到达时请求可能仍然成功；
- `external_key.recovered`：密钥恢复后约 30 分钟。

可能漏掉事件的情况：

| 情况 | 可能漏掉 |
|---|---|
| 没有请求用到这个密钥 | `external_key.failed`（只有请求用到密钥时才看得到拒绝） |
| 最后一次拒绝后约一天内没有请求用到密钥 | `external_key.recovered` |
| KMS 故障或超时 | 两个都可能漏，因为故障不算拒绝 |
| 多个组织的密钥几乎同时失效 | 两个事件和邮件都可能没有 |
| Default Workspace 的密钥失效，且它加密了端点的值 | 密钥恢复前的所有事件，包括它自己的 `external_key.failed` |

所以你可能连续收到两次 `external_key.failed`，或者收到前面没有 `external_key.failed` 的 `external_key.recovered`。告警逻辑应按密钥 ID 以校验结果为准，不按事件到达顺序判断。

## Default Workspace 也用了 CMEK 时要注意

组织的 Webhook 端点存放在 Default Workspace。如果这个工作区用了客户管理密钥，端点的 `name`、`description` 和签名密钥会用你的密钥加密。密钥不可用时，依赖它的端点投递全部失败，相关管理请求通常返回 `500`，期间事件被丢弃、不会补发；密钥恢复后投递继续，但要自己补查。如果在 KMS 里删除了这个密钥，这些失败是永久的，也无法再新建端点。

## 怎么算接好了：核对清单

- `GET /v1/organizations/webhooks` 能看到端点，`state` 是 `enabled`，`enabled_events` 里有两个 `external_key` 事件。
- 接收端会验签、按事件 `id` 去重、5 秒内返回 `2xx`。
- 同时对 Messages API 的 `cmek_key_disabled`、`cmek_key_network_blocked`、`cmek_key_unreachable` 三种错误做告警，这是官方要求的第二路信号。
- 定期补查（官方举例每天一次），并且在第一次添加事件类型、端点故障之后、重新启用端点之后各查一次：先确认端点 `state` 为 `enabled`，再列出全部密钥逐个校验；没收到过事件的密钥校验为 `success` 时，除非 Messages API 请求出错，不用再查。

## 官方一手来源

- https://platform.claude.com/docs/en/release-notes/overview#encryption-key-webhook-events
- https://platform.claude.com/docs/en/manage-claude/organization-webhooks

如果你只是想通过 OpenLux 调用 Claude 等模型的 API、不涉及上面这些组织级管理功能，可以[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-external-key-webhook-events&utm_content=footer)。

## 同专题文章

- [Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-streaming-required-10-minutes-max-tokens-fix/)
- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)
- [Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-image-400-size-dimension-limit-fix/)
- [Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？](https://a37836323.github.io/openlux-api-guides/news/claude-api-sampling-parameters-text-watermark/)
- [Claude API 报 400「thinking blocks cannot be modified」或「Invalid signature in thinking block」怎么办：原样回传思考块、redacted_thinking 与改了历史逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-thinking-blocks-cannot-be-modified-fix/)
- [Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

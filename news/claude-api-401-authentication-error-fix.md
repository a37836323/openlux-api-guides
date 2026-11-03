---
layout: default
title: "Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查"
description: "Claude API 报 401 authentication_error 怎么办：按官方错误说明与鉴权文档区分 401、403、404，检查 Authorization / x-api-key 请求头、Key 有效期与停用删除状态、工作区请求头，用最小请求验证，以及走 Anthropic 兼容中转地址时 401 Invalid token 与多写 /v1 的改法。"
permalink: /news/claude-api-401-authentication-error-fix/
date: 2026-11-04
---

> 更新日期：2026-11-04 · 一手来源：[Claude API errors](https://platform.claude.com/docs/en/api/errors)

# Claude API 报 401 authentication_error 怎么办：Key 过期、被停用、请求头与 Base URL 逐项排查

调用 Claude API 返回 401、`error.type` 是 `authentication_error`，说明这次请求用的 API Key 没有通过鉴权。官方[错误说明页](https://platform.claude.com/docs/en/api/errors)给出的原因是 Key 本身有问题，例如格式不对、已撤销或已过期。它和权限不足（403）、资源找不到（404）、付款问题（402）是不同的错误，处理方法也不一样，所以第一步是看清错误类型。

本文适用于用官方 SDK、curl 或各类客户端直接调用 Claude API（`https://api.anthropic.com`）时遇到的 401；如果你用的是 Anthropic 兼容的中转地址，最后一节单独说明。

## 先看错误类型：401、403、404 分别是什么意思

官方说明，Claude API 出错时总是返回 JSON：顶层 `error` 对象里一定有 `type` 和 `message`，响应里还带一个 `request_id`。下表整理自错误说明页和[鉴权文档](https://platform.claude.com/docs/en/manage-claude/authentication)：

| HTTP 状态 | error.type | 官方含义 | 先查哪里 |
|---|---|---|---|
| 401 | `authentication_error` | API Key 有问题，例如格式不对、已撤销或已过期 | Key 本身和请求头 |
| 403 | `permission_error` | Key 没有使用所请求资源的权限 | Console 里组织的访问权限和工作区设置 |
| 404 | `not_found_error` | 请求的资源不存在 | 接口路径、URL 里的资源 ID、工作区 ID |
| 400 | `invalid_request_error` | 请求格式或内容有问题 | 例如 Key 没绑定工作区，却没带工作区请求头 |
| 402 | `billing_error` | 账单或付款信息有问题 | Console 里的付款信息 |

官方还写明，在 Claude Platform on AWS 上，401 也可能是 AWS 凭据或 SigV4 签名的问题，这种情况要去查 AWS 侧配置。

另外，**401 不用加重试**。官方说明 SDK 默认自动重试的是连接错误、限流和 5xx 服务端错误，401 不在其中；Key 没修好，重试多少次结果都一样。

## 第一步：确认请求真的带上了 Key，而且放对了请求头

很多 401 不是 Key 坏了，而是程序实际发出去的 Key 和你以为的不一样。官方 [API 概览](https://platform.claude.com/docs/en/api/overview)列出的请求头是：

- `Authorization: Bearer <你的 Key>`；
- 或者旧的 `x-api-key: <你的 Key>`，官方说明仍然支持，二者有一个即可；
- 另外必须带 `anthropic-version` 和 `content-type: application/json`。

按顺序检查：

1. **Key 从哪里读**。官方说明设置了环境变量 `ANTHROPIC_API_KEY` 时，SDK 会自动读取它。终端里残留的旧变量、`.env` 文件、IDE 运行配置都可能让进程拿到旧 Key。排查时只打印 Key 的前几位和后几位确认，不要把完整 Key 写进日志。
2. **头的格式**。自己拼 HTTP 请求时，`Authorization` 的值必须以 `Bearer ` 开头；`x-api-key` 则直接写 Key。
3. **中间有没有代理或网关**。如果请求要经过只读 `x-api-key` 的代理，而客户端用 `Authorization: Bearer` 发 Key，代理就拿不到 Key。这类情况的改法见本站的 [Anthropic SDK 升级后报 400 或鉴权失败](https://a37836323.github.io/openlux-api-guides/news/anthropic-api-2026-10-21-upgrade-errors-fix/)。

## 第二步：Key 是否已过期、被停用或删除

这是最容易被忽略的原因。按鉴权文档：

- 在 Console 的 API keys 页创建 Key 时要选有效期：3 小时、1 天、7 天、30 天、自定义时长，或 **Never**。如果组织设置了最长有效期策略，**Never** 不可选。有效期在创建时定下，之后不能修改。
- **过期后的请求返回 `401 authentication_error`**，过期的 Key 不能重新启用，只能新建一个。
- 提醒邮件只发给 Key 的创建者：有效期至少 14 天的提前 7 天提醒，至少 7 天的提前 1 天提醒，更短的（例如 3 小时、1 天）**到期不发提醒**。所以昨天还能用、今天突然 401，先看有效期。
- 在 Console 里 **Disable** 是可逆的，可以 **Re-enable**；**Delete** 是永久的。
- Console 的 API keys 表格会显示每个 Key 的过期时间；Admin API 的 List API Keys 接口返回 `expires_at`，没有设置过期的是 `null`。

鉴权文档还写了不同类型的 Key 什么时候停止工作：

| Key 类型 | 什么时候停止工作 |
|---|---|
| 个人 Key | 你失去组织访问权；被移出组织时 Key 会被归档，重新被邀请后也不会恢复，要新建。只绑定单个工作区的 Key，在你失去该工作区权限或工作区被归档时也会失效 |
| 服务账号 Key | 服务账号被归档；单工作区 Key 在服务账号被移出该工作区或工作区被归档时也会失效 |
| 工作区 Key（旧类型） | 过期、被停用或删除，或者所在工作区被归档 |

注意：官方只明确写了“过期后返回 401”，其他几种情况文档写的是 Key 停止工作。排查 401 时这些都值得核对一遍，尤其是团队共用一个人的个人 Key、而这个人已经离开组织的情况。

## 第三步：别把工作区相关的 400、404 当成 401

鉴权文档说明，没有绑定工作区的 Key，每个请求都必须带 `anthropic-workspace-id` 请求头，否则返回 400 `invalid_request_error`，提示这个 Key 没有绑定工作区、请求必须带上工作区 ID。几种相似报错的区别：

| 报错 | 原因 | 改法 |
|---|---|---|
| 400，提示 Key 没有绑定工作区、要带 `anthropic-workspace-id` | Key 未绑定工作区，请求没带该头 | 加上该头，或改用绑定了工作区的 Key |
| 400，`anthropic-workspace-id header must be a valid workspace ID.` | 头里填的不是合法的工作区 ID | 到 Console 的 Workspaces 页 ID 列复制正确的值 |
| 404，``Workspace `<id>` not found.`` | 工作区不存在，或 Key 对应的用户、服务账号无权访问它 | 换成有权限的工作区，或让管理员把账号加进去 |

## 第四步：用最小请求单独验证 Key

把 Key 放进环境变量，用官方文档里的最小请求测试，`-i` 会把响应头一起打印出来：

```bash
curl -i https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-opus-5-5", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello, Claude"}]}'
```

怎么判断：

- **返回 200 和回复内容**：Key 没问题，401 出在你的程序读错了 Key、地址或请求头，回到第一步。成功的响应头里有 `anthropic-organization-id` 和 `anthropic-workspace-id`，可以顺便确认请求落在了你预期的组织和工作区。
- **仍然返回 401**：按第二步检查有效期和状态，必要时新建 Key 换上。官方说明，请求在鉴权完成前就失败时，响应里不会有 `anthropic-workspace-id` 头。
- **需要联系官方支持**：带上响应头里的 `request-id`（错误响应体里的 `request_id` 是同一个值）。

## 用 Anthropic 兼容中转地址时的 401 和 404

如果你把 Base URL 换成了中转地址，请求里的 Key 也要换成这个中转平台控制台里创建的 Key，地址和 Key 要来自同一家。以 OpenLux 为例：

| 项目 | 说明 |
|---|---|
| Base URL | `https://api.openlux.ai`，**不带 `/v1`**，客户端会自己拼成 `/v1/messages` |
| 鉴权头 | `/v1/messages` 同时接受 `x-api-key` 和 `Authorization: Bearer` |
| Key 无效或没带 | 返回 401，报错原文是 `Invalid token (request id: ...)` |
| Base URL 多写了 `/v1` | 返回 404 `Invalid URL (POST /v1/v1/messages)` |
| Key 从哪里来 | 在 OpenLux 控制台的令牌页创建：`https://www.openlux.ai/console/token` |

验证方法：用 `curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $你的中转Key"` 请求模型列表，能列出模型就说明地址和 Key 都对，剩下的问题去查客户端配置。

如果你还没有中转 Key，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-401-authentication-error-fix&utm_content=footer)

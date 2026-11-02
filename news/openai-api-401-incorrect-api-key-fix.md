---
layout: default
title: "OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查"
description: "OpenAI API 报 401 Incorrect API key provided、Invalid Authentication、IP not authorized 怎么办：按官方错误码页对照四种 401 的原因，检查 OPENAI_API_KEY 与 base_url 实际取值、组织和项目请求头、Key 撤销与生效时间，以及中转 Key 和地址不匹配时的改法。"
permalink: /news/openai-api-401-incorrect-api-key-fix/
date: 2026-11-02
---

> 更新日期：2026-11-02 · 一手来源：[OpenAI API 官方文档](https://developers.openai.com/api/docs/guides/error-codes)

# OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查

调用 OpenAI API 返回 401，意思是**这次请求没有通过鉴权**，通常和模型参数、余额无关（余额和额度问题报的是 429）。OpenAI 官方[错误码页](https://developers.openai.com/api/docs/guides/error-codes)列出了 4 种 401：`Invalid Authentication`、`Incorrect API key provided`、`You must be a member of an organization to use the API`、`IP not authorized`。它们的处理方式不同，所以第一步是看清报错原文，再对照下面的表。

本文适用于用官方 SDK、curl 或各类客户端调用 OpenAI API（Responses、Chat Completions 等）时遇到的 401；如果你用的是 OpenAI 兼容的中转地址，最后一节单独说明。

## 四种 401 和 403 对照表

以下内容整理自官方错误码页：

| 报错原文 | 官方给出的原因 | 怎么处理 | 重试有用吗 |
|---|---|---|---|
| Incorrect API key provided | 请求用的 API Key 不正确：有错字或多余空格；属于别的组织或项目；已删除或停用；本地缓存了已撤销的旧 Key | 核对请求头里的 Key，拿不准就新建一个换上；网页端可清理浏览器缓存和 Cookie | 没用 |
| Invalid Authentication | 用了已撤销的 Key；Key 和请求的组织或项目对不上；Key 没有调用该接口所需的权限 | 核对请求头里的 Key 和组织 ID；项目 Key 在对应项目的设置里查看；不确定就新建 Key | 没用 |
| You must be a member of an organization to use the API | 账号不属于任何组织：离开或被移出组织、项目，或组织已删除 | 让组织管理员重新邀请你、加回项目，或新建组织 / 项目 | 没用 |
| IP not authorized | 请求 IP 不在项目或组织配置的 IP 白名单里 | 从白名单内的 IP 发请求，或修改白名单 | 没用 |
| 403 Country, region, or territory not supported | 从不受支持的国家或地区访问 | 对照官方支持地区列表 | 没用 |

官方 Python SDK 的 [README](https://github.com/openai/openai-python) 写明：401 对应 `AuthenticationError`，403 对应 `PermissionDeniedError`。SDK 默认只自动重试连接错误、408、409、429 和 500 以上的错误，**401 不在其中**，所以会立即抛错。不要为 401 加重试循环，重试多少次结果都一样。

## 第一步：确认请求实际带的是哪个 Key、发到了哪里

很多 401 不是 Key 本身坏了，而是程序读到的 Key 或地址和你以为的不一样。按顺序检查：

1. **Key 从哪来**。Python SDK 在代码没传 `api_key` 时读取环境变量 `OPENAI_API_KEY`。终端里残留的旧变量、`.env` 文件、IDE 运行配置都可能覆盖你刚改的值。排查时只打印 Key 的前几位和后几位，确认是不是新 Key，不要把完整 Key 打到日志里。
2. **有没有多余字符**。官方把“错字或多余空格”列为第一个原因。复制 Key 时带进的首尾空格、漏复制或多复制的字符，都会让 Key 对不上。
3. **请求发到了哪里**。SDK 默认请求 OpenAI 官方地址；设置了 `base_url` 参数或 `OPENAI_BASE_URL` 环境变量时，请求会发到你指定的地址。Key 必须和地址是同一家平台签发的。
4. **请求头格式**。官方 [API 参考](https://developers.openai.com/api/reference/overview)要求的格式是 `Authorization: Bearer <你的 Key>`。

## 第二步：用最小请求单独验证 Key

把 Key 放进环境变量，用列出模型的接口验证（官方文档：[List models](https://developers.openai.com/api/reference/resources/models/methods/list)）：

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

- 返回模型列表：Key 和地址都没问题，401 出在你的程序读错了 Key 或地址，回到第一步。
- 仍返回 401：按报错原文对照上表处理。

在 Python 里可以这样区分鉴权错误和其他错误：

```python
from openai import OpenAI, AuthenticationError

client = OpenAI()
try:
    client.models.list()
except AuthenticationError as e:
    print("鉴权失败", e.status_code)
```

## 第三步：Key 属于哪个组织、哪个项目

官方 API 参考写明：**如果你属于多个组织，或者用的是旧版用户级 API Key 访问项目**，需要在请求头里指定组织和项目：

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Organization: $ORGANIZATION_ID" \
  -H "OpenAI-Project: $PROJECT_ID"
```

组织 ID 和项目 ID 在控制台设置页可以查到。这里出错的典型表现是 `Invalid Authentication`：Key 本身有效，但和请求指定的组织或项目对不上。检查时注意：

- 代码或环境变量里写死的 `OpenAI-Organization`、`OpenAI-Project` 是否还是旧值。
- 项目级 Key 要在对应项目下查看和管理，换项目后要用新项目的 Key。
- 如果 Key 设置了受限权限，调用没有授权的接口也会出现 `Invalid Authentication`，需要换一个对该接口有权限的 Key。

## 刚换了 Key 或改了设置还是 401

官方 API 参考说明了生效时间：**撤销 API Key 几秒内生效**；其他影响鉴权的变更通常在 15 分钟内生效，也可能更久。所以：

- 刚撤销旧 Key 后，旧 Key 很快就会报 401，这是预期行为，确认所有部署都已换成新 Key。
- 刚被加入组织或项目、刚修改 IP 白名单或 Key 权限后仍报错，可以稍等再试；超过这个时间仍不行，再核对设置本身。
- 网页端（如 Playground）报 `Incorrect API key provided`，官方建议清理浏览器缓存和 Cookie，排除本地缓存的旧 Key。

另外，官方提醒 API Key 是机密：不要分享给他人，也不要放在浏览器或 App 等客户端代码里，应在服务端从环境变量或密钥管理服务读取。

## 用中转地址时的 401

如果你用的是 OpenAI 兼容的中转 API，最常见的 401 是 **Key 和地址不是同一家**：

| 现象 | 原因 | 改法 |
|---|---|---|
| 用中转 Key 却报 OpenAI 的 `Incorrect API key provided` | 没设置 `base_url` / `OPENAI_BASE_URL`，请求仍发往 OpenAI 官方地址，而中转 Key 不是 OpenAI 签发的 | 把 Base URL 改成中转地址，例如 `https://api.openlux.ai/v1` |
| OpenLux 返回 `Invalid token (request id: ...)` | Key 无效、填错，或把 OpenAI 官方 Key 发到了中转地址 | 在 OpenLux 控制台「令牌」页创建 Key 并替换 |
| 返回 404 而不是 401 | 多半是 Base URL 路径写错，例如多写了一层 `/v1`，OpenLux 会返回 404 `Invalid URL (...)` | OpenAI 兼容接口的 Base URL 填到 `/v1` 为止 |

验证方法和上面一样：请求 `https://api.openlux.ai/v1/models` 并带上 `Authorization: Bearer <OpenLux Key>`，能列出模型就说明地址和 Key 都正确。

## 怎么确认已经修好

- 用同一个运行环境（同一台机器、同一份环境变量）请求 `/v1/models` 返回 200。
- 原来报错的请求不再返回 401，日志里不再出现 `AuthenticationError`。
- 所有部署（本地、CI、服务器）都换成了新 Key，旧 Key 已撤销。

注册入口：[注册 OpenLux 账号](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-401-incorrect-api-key-fix&utm_content=footer)

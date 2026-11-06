---
layout: default
title: "Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查"
description: "Gemini API 报 401 或 403 PERMISSION_DENIED 时，按官方错误码、排错指南和 API Key 文档逐项排查：Key 缺失或失效、GEMINI_API_KEY 与 GOOGLE_API_KEY 冲突、Key 泄露或未加限制被封、项目需要验证或计费，以及走中转时怎么查令牌。"
permalink: /news/gemini-api-401-403-permission-denied-fix/
date: 2026-11-05
---

> 更新日期：2026-11-05 · 一手来源：[Google AI for Developers：Gemini API errors / Troubleshooting / Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-errors)

# Gemini API 报 401、403 PERMISSION_DENIED 怎么办：Key 无效、被封、项目受限与 Key 限制逐项排查

Gemini API 返回 **401**（Interactions API 的错误码是 `authentication`），按 Google 官方 [API errors](https://ai.google.dev/gemini-api/docs/api-errors) 页的说明，是 API Key 缺失、无效或已过期，要先检查 Key 本身。返回 **403 `PERMISSION_DENIED`**（错误码 `permission_denied`）则有两大类原因：一是 Key 没有访问该资源的权限，二是你的 Google Cloud 项目受限、需要验证或需要调整计费。两类错误官方都明确说**不要重试**，重试也不会成功，要先找到原因再改。

本文适用于用 Google AI Studio 的 Key 直接调用 Gemini API，也适用于通过中转平台以 Gemini 原生格式或 OpenAI 兼容格式调用。429 限流和配额见《[Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)》，503、500、504 见《[Gemini API 报 503 UNAVAILABLE、500、504 怎么办](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)》。

## 先对照报错：是 Key 的问题，还是项目的问题

下表出自官方 API errors 页和 [排错指南](https://ai.google.dev/gemini-api/docs/troubleshooting)。Interactions API 的报错是一个 `error` 对象，只有 `code`（小写下划线形式）和 `message` 两个字段，按 `code` 分支处理即可。

| HTTP 状态 | `code` 或报错原文 | 官方含义 | 先查什么 | 要不要重试 |
|---|---|---|---|---|
| 401 | `authentication` | API Key 缺失、无效或过期 | Key 有没有带上、是不是完整、是不是读错了环境变量 | 不要，先改 |
| 403 | `permission_denied` | Key 没有该资源的权限，或项目受限、需要验证、需要改计费 | Key 的 API 限制、AI Studio 里的项目状态 | 不要，先改 |
| 403 | `Your project has been denied access` | 项目被拒绝访问 | AI Studio 项目状态：需要验证、免费层不可用、需要付款等 | 不要，先处理 |
| — | `Your API key was reported as leaked. Please use another API key.` | Key 被判定为已泄露，已被封禁 | 换新 Key，把旧 Key 从代码和仓库里清掉 | 不要，换 Key |
| 400 | `failed_precondition` | 前提条件不满足，例如计费被停用 | 计费状态和账号前提条件 | 不要，先处理 |
| 402 | `payment_required` | 预付（Prepay）余额用完 | 充值或开启自动续充 | 官方明确说不要重试 |

官方排错指南的重试原则是：只对临时性错误（`429`、`408`、`5xx`）重试；`400`、`402`、`403` 这类客户端错误不要重试。所以如果你的代码对所有错误都自动重试，401 和 403 只会白白多打几次请求。

## 401：Key 没带上、带错或已失效

401 的官方含义只有一句：Key 缺失、无效或过期。按下面的顺序查：

1. **请求头是否正确**。官方 [API Key 文档](https://ai.google.dev/gemini-api/docs/api-key) 的 REST 示例用的是请求头 `x-goog-api-key: YOUR_API_KEY`。自己拼请求时，确认头名没写错、值前后没有多余的空格或引号。
2. **环境变量读的是哪一个**。官方 SDK 会自动读取 `GEMINI_API_KEY` 或 `GOOGLE_API_KEY`，**两个都设置时 `GOOGLE_API_KEY` 优先**。常见的坑是：你换了新 Key 写进 `GEMINI_API_KEY`，但系统里还留着旧的 `GOOGLE_API_KEY`，SDK 实际用的是旧 Key。排查时把两个变量都打印长度或前几位核对一下，或者干脆只保留一个。
3. **Key 是否还有效**。到 AI Studio 的 API Keys 页面确认这把 Key 还在、没有被标成 **Blocked**（见下一节）。
4. **代码里是否显式传了别的 Key**。SDK 支持 `genai.Client(api_key="...")` 这种写法，代码里写死了旧 Key 时，改环境变量不会起作用。官方建议只有在不能用环境变量时才这样写。

## 403 之一：Key 被封——泄露、闲置或没有加限制

即使 Key 复制得完全正确，也可能因为 Key 本身被封而失败。官方文档写了三种情况：

- **被判定泄露**：报错信息是 `Your API key was reported as leaked. Please use another API key.`。官方说明 Google 会主动封禁已知泄露的 Key。处理办法是在 AI Studio 的 API Keys 页面新建 Key，更新应用里的凭据。官方给出的换 Key 顺序是：生成新 Key → 部署新 Key → 停用旧 Key（**新 Key 完全生效前不要删除旧 Key**）→ 审计用量。如果有异常扣费，官方建议提交计费支持工单。
- **没有加限制的标准 Key**：官方 API Key 文档写明，Gemini API 会拒绝来自**未加限制的标准 Key**（unrestricted standard keys）的请求；已经加了明确限制的标准 Key 可以继续用。另外，从 2026 年 5 月 7 日起，长时间闲置的未加限制 Key 会被封禁，在 AI Studio 里显示 **Blocked** 标签，官方的处理办法是生成新 Key，或改用一把已加限制的 Key。
- **限制加错了方向**：在 Cloud 控制台把 Key 限制到其他 API、却没有包含 Generative Language API（也就是 Gemini API）时，官方说这把 Key 之后调用 Gemini API 会失败。

给未加限制的 Key 加上限制，官方步骤是：在 AI Studio 的 API Keys 页面找到标为 Unrestricted 的 Key，悬停在标签上点 **Add restrictions**，选 **Restrict to Gemini API only**，再点 **Restrict key** 确认。这一步需要 `apikeys.keys.update` 权限。

官方还说明：从 2026 年 5 月 28 日起，AI Studio 新建的 Key 默认是绑定服务账号的 auth key，默认就限制在 Gemini API 上，并且对泄露的 Key 能更快地停用。所以 Key 是很早以前建的、又报 401 或 403 时，可以考虑在 AI Studio 新建一把，替换后再验证。官方页面没有给出「未加限制被拒」这种情况对应的具体状态码和报错原文，排查时把它当作一项必查项即可。

## 403 之二：Your project has been denied access

如果报错是 `403 PERMISSION_DENIED` 加 `Your project has been denied access`，问题在 Google Cloud 项目，不在 Key。官方排错指南列出的 AI Studio 项目状态有：Verification needed（需要验证）、Restricted（受限）、Free tier unavailable（免费层不可用）、Payment needed（需要付款）、Unavailable（不可用）。对应处理：

- **需要验证**（也可能看到 `FREE_TIER_VERIFICATION_REQUIRED`）：在 AI Studio 里用手机完成验证；或者为项目设置计费，改用付费层，就不需要验证设备。
- **免费层不可用**：官方特别提醒，**在同一个项目里新建 Key 解决不了**，因为是否能用免费层是按 Cloud 项目判断的。要继续用这个项目，需要关联一个有效的 Cloud Billing 账号，转到付费层。另外，升级到付费层并不会解锁免费层额度。
- **需要付款**：在 AI Studio Billing 或 Cloud Billing 控制台结清欠款或更新付款方式，官方说处理后项目会自动恢复 API 访问。
- **因政策被暂停**：查看项目关联邮箱和 Cloud 控制台里的暂停通知，按官方的项目暂停指引处理。

这一类问题换 Key、改代码都没用，只能在项目层面处理。

## 400 failed_precondition 和 402 payment_required

这两个不是 401 或 403，但常和权限问题一起出现：

- `failed_precondition`（400）：官方含义是前提条件不满足，举的例子就是计费被停用。处理办法是确认计费状态和账号的前提条件。
- `payment_required`（402）：预付余额用完。官方建议充值或开启自动续充，并明确说在充值前不要重试，请求不会成功。

## 怎么确认修好了：别只看 models.list

官方排错指南专门提醒：`models.list` 这类只读接口返回 `200 OK`，只能说明 Key 存在，**不能保证推理调用能用**。所以验证时要发一个最小的推理请求。官方 API Key 文档给的示例如下（Key 从环境变量读取，不要写进代码）：

```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/interactions" \
  -H 'Content-Type: application/json' \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H "Api-Revision: 2026-05-20" \
  -d '{"model": "gemini-3.8-flash", "input": "Explain how AI works in a few words"}'
```

成功标准：返回 HTTP 200，并带有模型输出。仍然失败时，看返回 `error.code`：是 `authentication` 就回到第二节查 Key；是 `permission_denied` 就查 Key 限制和项目状态。另外注意接口版本：官方排错指南说明，处于 Beta 阶段的功能只在 `/v1beta` 下可用，并要确认所用模型在官方模型页上。

## 通过中转调用时怎么查

通过中转平台调用时，请求里带的是**中转平台的令牌**，不是你自己的 Google Key，请求也不经过你自己的 Google Cloud 项目，所以上面「项目被拒绝访问」那几项不用查，先查令牌和地址。以 OpenLux 为例：

- **Key**：在 OpenLux 控制台的「令牌」页创建（`https://www.openlux.ai/console/token`）。
- **Gemini 原生格式**：Base URL 填 `https://api.openlux.ai`，请求路径是 `/v1beta/models/<模型>:generateContent`，鉴权用请求头 `x-goog-api-key` 或查询参数 `?key=`。
- **OpenAI 兼容格式**：Base URL 填 `https://api.openlux.ai/v1`，鉴权用 `Authorization: Bearer`。
- **令牌无效时的报错**：返回 401 `Invalid token (request id: ...)`。看到这个就换成控制台里正确的令牌，检查有没有多复制空格。
- **模型名**：只用价格页在售的模型 ID；每个模型支持哪些接口格式，看价格接口里的 `supported_endpoint_types`。

用 OpenAI 兼容地址列模型，能列出来就说明地址和令牌都对：

```bash
curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"
```

## 排查顺序小结

1. 看状态码和 `code`：401 查 Key，403 先看报错原文。
2. 401：核对请求头、`GEMINI_API_KEY` 与 `GOOGLE_API_KEY` 是否冲突、Key 是否被标 Blocked。
3. 403 且提示泄露或 Key 未加限制：新建 Key 或把 Key 限制到 Gemini API，按官方顺序替换旧 Key。
4. 403 且提示项目被拒绝访问：在 AI Studio 看项目状态，完成验证、关联计费或结清欠款；同项目新建 Key 没用。
5. 用最小推理请求验证，不要只看 `models.list`；401、402、403 不要自动重试。

如果你想用一把令牌同时调用 Gemini、GPT 和 Claude，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=gemini-api-401-403-permission-denied-fix&utm_content=footer)。

## 同专题文章

- [Gemini API 报 404 model_not_found 或 not_found 怎么办：模型名写错、旧模型已关停、Base URL 与 API 版本逐项排查](https://a37836323.github.io/openlux-api-guides/news/gemini-api-404-model-not-found-fix/)
- [Gemini API 报 503 UNAVAILABLE、500、504 怎么办：服务过载、服务端错误与超时怎么区分，重试和超时怎么设](https://a37836323.github.io/openlux-api-guides/news/gemini-api-503-unavailable-500-504-fix/)
- [Gemini API 报 429 RESOURCE_EXHAUSTED 怎么办：RPM、TPM、每日配额与 10 分钟消费限额怎么区分，重试怎么写](https://a37836323.github.io/openlux-api-guides/news/gemini-api-429-resource-exhausted-fix/)
- [gemini-3.1-flash-lite 最早 2027 年 5 月 7 日下线：换成 gemini-3.5-flash-lite 要改哪些（thinking_level、采样参数、预填 400）](https://a37836323.github.io/openlux-api-guides/news/gemini-3-1-flash-lite-shutdown-gemini-3-5-flash-lite-migration/)
- [gemini-3.7-flash、gemini-3.5-flash 已弃用并自动转到新模型：thinking_level 报错、token 变多怎么处理](https://a37836323.github.io/openlux-api-guides/news/gemini-3-7-3-5-flash-deprecated-auto-routing-fix/)
- [gemini-3.1-flash-live-preview 最早 11 月 17 日下线：换成 gemini-3.8-live 要改哪些（thinkingLevel、函数调用、proactive_audio）](https://a37836323.github.io/openlux-api-guides/news/gemini-live-preview-shutdown-gemini-3-8-live-migration/)

[查看「Gemini API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/gemini-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

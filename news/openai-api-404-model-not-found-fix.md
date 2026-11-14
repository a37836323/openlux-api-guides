---
layout: default
title: "OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查"
description: "OpenAI API 报 404「The model xxx does not exist or you do not have access to it」（model_not_found）时怎么办：按官方排查顺序核对模型 ID 和接口、用同一个 Key 和项目调 /v1/models 对比、检查项目模型权限 allow_list/deny_list、查 Deprecations 看模型是否已下线，以及走中转时 Base URL 多写 /v1 的 404 怎么区分。"
permalink: /news/openai-api-404-model-not-found-fix/
date: 2026-11-14
---

> 更新日期：2026-11-14 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/rate-limits)

# OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查

**直接结论**：这条报错的意思是「用你这次请求带的 Key、组织和项目，看不到这个模型」。它不一定说明模型真的不存在，常见原因有四类：

1. **模型 ID 写错，或者这个模型不支持你调用的接口**：大小写、多了日期后缀、拼错，或者从别处抄来的名字。
2. **Key 对应的组织、项目不是你以为的那个**：网页里能看到的模型，换一个 Key、换一个项目就可能看不到。
3. **项目被限制了可用模型**：项目的模型权限设成了只允许部分模型（allow list）或禁止部分模型（deny list）。
4. **模型已经下线（shutdown）**：下线后标准 API 不再接受这个模型的请求。

OpenAI 官方在 [Rate limits 文档的 Model availability 一节](https://developers.openai.com/api/docs/guides/rate-limits)里专门写了遇到 `model_not_found` 时的排查顺序，本文按它展开，并补充 [Deprecations](https://developers.openai.com/api/docs/deprecations)、[Models 接口](https://developers.openai.com/api/reference/resources/models) 和 [Error codes](https://developers.openai.com/api/docs/guides/error-codes) 里的相关说明。适用于直接调用 OpenAI API，或通过 OpenAI 兼容中转调用 GPT 系列模型的场景。

## 先看报错原文：是哪一种 404

同样是 404，原因可能完全不同。先对一下原文：

| 报错里的关键内容 | 说明什么 | 先做什么 |
|---|---|---|
| `` The model `xxx` does not exist or you do not have access to it ``（官方文档称 `model_not_found`） | 这个 Key、组织、项目看不到该模型 | 按本文第一步到第四步逐项查 |
| Python SDK 抛出 `NotFoundError` | SDK 把 HTTP 404 映射成这个异常类型，官方说明是「请求的资源不存在」 | 打印异常内容（`print(e)`）看具体是模型还是别的资源（文件、响应 ID 等） |
| 通过中转调用时返回 `Invalid URL (...)`，括号里的路径出现 `/v1/v1/` | Base URL 多写了一层 `/v1`，路径不对，不是模型问题 | 改 Base URL，见下文中转一节 |

openai-python 的 [README](https://github.com/openai/openai-python) 列出了状态码和异常类型的对应关系：404 对应 `NotFoundError`，401 对应 `AuthenticationError`，403 对应 `PermissionDeniedError`。所以如果你看到的是 401 或 403，就不是本文的问题，401 可以看指南站的 [OpenAI API 报 401 Incorrect API key provided](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)。

## 第一步：核对模型 ID 和你调用的接口

官方排查顺序的第一条是 **Check the model ID and endpoint**：

- **从模型文档原样复制模型 ID**。[Models 页面](https://developers.openai.com/api/docs/models)每个模型卡片上都有「Model ID」字段，例如 `gpt-6-luna`、`gpt-6.1-sol`。不要凭印象手打，也不要把网页上的显示名（如「GPT-6 Luna」）当成 ID。
- **确认这个模型支持你调用的接口**。同一个模型不一定在每个接口上都能用，Chat Completions、Responses、音频、图片等接口要分别看模型页的说明。
- **看有没有下线或灰度通知**。新模型可能分批开放，旧模型可能已经下线，见第四步。

最稳妥的做法是用下一步的 `/v1/models` 列表核对，代码里的模型名要和列表里的 `id` 逐字一致。

## 第二步：用同一个 Key 调 /v1/models 对比

官方第二条是 **Compare the organization, project, and credentials**，并特别提醒：网页里当前登录状态下能看到的模型，**换一个 API Key 仍可能不可用**。所以要用**出错那次请求同一个 Key、同样的组织和项目请求头**去列模型：

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "OpenAI-Project: $OPENAI_PROJECT_ID"
```

如果你的请求还带了 `OpenAI-Organization` 头，这里也要一起带上。然后看返回的 `data` 列表里有没有你要的模型 `id`：

- **列表里有，调用却报 404**：回到第一步，检查代码里实际发出去的模型名（打印请求体），以及接口是否支持这个模型。
- **列表里没有**：说明这个 Key 和项目确实用不了它，继续看第三步、第四步。

也可以直接查单个模型：`curl https://api.openai.com/v1/models/$MODEL -H "Authorization: Bearer $OPENAI_API_KEY"`。返回的模型对象里有 `id`、`owned_by`，还有 `shutdown_date`（已公布下线日期就是那个日期，没公布是 `null`）。

## 第三步：查项目的模型权限和模型本身的准入要求

官方第三条是 **Review project restrictions and model requirements**：请项目管理员检查该项目的**模型权限**和**数据保留设置**，并满足模型自己的准入要求、留意灰度通知。

项目的模型权限在官方 [Terraform 项目控制文档](https://developers.openai.com/api/docs/guides/terraform/project-controls)里写得比较清楚，有两种模式：

| 模式 | 含义 | 什么时候会导致 404 |
|---|---|---|
| `allow_list` | 只允许 `model_ids` 里列出的模型 | 你要用的模型不在名单里 |
| `deny_list` | 允许其他可用模型，只禁止名单里的模型 | 你要用的模型正好在禁止名单里 |

另外几条官方说明值得注意：

- **模型权限和速率限制是两回事**。官方原话是达到某个用量等级（usage tier）**不等于**能用所有模型，限额页里出现了某个模型的速率限制，也不能证明你的组织、项目或 Key 有权限用它。
- **只看「列表里没有这个模型」判断不出原因**，要把模型 ID、项目权限、Key 三样都对过。
- 部分专用模型本身就只对获批组织开放（Models 页面上写明「for approved organizations」「authorized」之类的），这类模型要先满足它的准入要求才能调用。

## 第四步：模型是不是已经下线

[Deprecations 页面](https://developers.openai.com/api/docs/deprecations)区分了两个阶段：

- **Deprecated（已公布弃用）**：模型在下线日期前**仍然能用**。
- **Shutdown（已下线）**：官方原话是下线后模型「no longer accepts requests through the standard API」。

所以如果代码很久没改、某天突然开始报这条 404，先去 Deprecations 页面搜一下模型名，看下线日期是否已经过了，再按页面上的推荐替代模型改。几条官方规则：

- 正式发布（GA）的模型至少提前 6 个月通知；专用变体和图片模型至少 3 个月；`preview` 模型可能只有约 2 周。
- **微调模型跟随它的基础模型一起下线**。
- `GET /v1/models` 和查单个模型的接口都会返回 `shutdown_date`，可以用它做定时检查，提前发现快要下线的模型。

指南站整理过几批已公布的下线和迁移，例如 [gpt-3.5-turbo、gpt-4、o1 等 10 月 23 日下线后怎么换](https://a37836323.github.io/openlux-api-guides/news/openai-legacy-models-oct-23-shutdown-migration/)，具体日期仍以官方 Deprecations 页面为准。

## 通过 OpenAI 兼容中转调用时怎么查

如果你不是直连 OpenAI，而是通过 OpenAI 兼容的中转地址调用，排查思路一样，只是「能用哪些模型」要以**中转服务商的模型列表**为准，不以 OpenAI 官网为准：

1. **先分清是路径错还是模型错**。以 OpenLux 为例，OpenAI 兼容接口的 Base URL 填 `https://api.openlux.ai/v1`，客户端或 SDK 会自己拼出 `/v1/chat/completions`、`/v1/responses`。如果 Base URL 多写了一层 `/v1`，请求路径就会变成 `/v1/v1/...`，返回 404 `Invalid URL (...)`（例如 Anthropic Messages 接口多写一层时返回 `Invalid URL (POST /v1/v1/messages)`），这时改地址即可，与模型无关。
2. **用 `/v1/models` 核对模型名**。带上 `Authorization: Bearer <你的 Key>` 请求 `https://api.openlux.ai/v1/models`，能列出模型就说明地址和 Key 都对，再从列表里原样复制模型 ID。
3. **核对模型支持的接口**。OpenLux 价格页和价格接口里每个模型标了 `supported_endpoint_types`（`openai`、`openai-response`、`anthropic`、`gemini`），调用的接口要在其中。

Key 在 OpenLux 控制台「令牌」页创建。中转返回的报错文字可能和 OpenAI 原文不同，以实际返回为准。

## 怎么确认已经修好

满足下面三条，就可以认为问题解决了：

1. 用出错时同一个 Key、同样的项目请求头调 `GET /v1/models`，返回的列表里有你要用的模型 `id`。
2. 用这个 `id` 发一次最小请求，返回 200，不再出现 `does not exist or you do not have access to it`。
3. 对正在使用的模型查一次 `GET /v1/models/{model}`，确认 `shutdown_date` 是 `null` 或在你计划的迁移时间之后。

如果按以上步骤都改过、刷新之后仍然列不出模型，官方建议联系支持，并附上模型 ID、组织 ID 和项目 ID、请求时间、报错原文，以及响应头里的 `x-request-id`（如果有）。**不要把 API Key 发给任何人**。

## 参考资料

- OpenAI 官方文档：[Rate limits · Model availability](https://developers.openai.com/api/docs/guides/rate-limits)（`model_not_found` 四步排查、模型权限和速率限制是两回事）
- OpenAI 官方文档：[Deprecations](https://developers.openai.com/api/docs/deprecations)（弃用与下线的区别、通知期、微调模型跟随基础模型下线、`shutdown_date`）
- OpenAI 官方 API 参考：[Models](https://developers.openai.com/api/reference/resources/models)（`GET /v1/models`、`GET /v1/models/{model}`、模型对象字段）
- OpenAI 官方文档：[Model, tool, and data controls with Terraform](https://developers.openai.com/api/docs/guides/terraform/project-controls)（项目模型权限 `allow_list` / `deny_list`）
- OpenAI 官方文档：[Error codes](https://developers.openai.com/api/docs/guides/error-codes)（Python 库 `NotFoundError` 说明）
- OpenAI 官方 SDK：[openai-python README](https://github.com/openai/openai-python)（HTTP 状态码与异常类型对应表）

想用一个 Key 调用 GPT、Claude、Gemini 等多家模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-404-model-not-found-fix&utm_content=footer)，创建 Key 后先用 `/v1/models` 核对模型名再调用。

## 同专题文章

- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些](https://a37836323.github.io/openlux-api-guides/news/openai-evals-read-only-shutdown-promptfoo-migration/)
- [OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办](https://a37836323.github.io/openlux-api-guides/news/openai-responses-incomplete-max-output-tokens-fix/)
- [OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改](https://a37836323.github.io/openlux-api-guides/news/agent-builder-shutdown-agents-sdk-chatkit-migration/)
- [gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办](https://a37836323.github.io/openlux-api-guides/news/gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查"
description: "n8n 接 OpenAI 兼容中转后，OpenAI Chat Model 节点报 Bad request - please check your parameters、The service is receiving too many requests、Insufficient quota 或要求开启 Responses API 时，如何找到服务端原始报错、用 HTTP Request 节点复现，并按状态码修改 Base URL、Key、模型与 Use Responses API。"
permalink: /news/n8n-openai-chat-model-bad-request-error-fix/
date: 2026-11-02
---

> 更新日期：2026-11-02 · 一手来源：[n8n 官方文档：OpenAI Chat Model 常见问题](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/common-issues/)

# n8n 接中转后 OpenAI Chat Model 报「Bad request - please check your parameters」怎么办：429、Insufficient quota 与 Responses API 提示怎么排查

先说结论：n8n 里看到的「Bad request - please check your parameters」「The service is receiving too many requests from you」这类英文提示，是 n8n 按 HTTP 状态码套上的**通用说法**，不是中转服务返回的原话。排查时先找到服务端的原始报错，再按状态码对症处理；找不到原文时，按 [n8n 官方 OpenAI Chat Model 常见问题](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/common-issues/) 的建议，用 HTTP Request 节点把同样的请求再发一次，看完整返回。

本文适用于已经在 n8n 里用 OpenAI 凭据接好 OpenAI 兼容中转（Base URL 指向中转地址）、但 OpenAI Chat Model 节点运行时报错的读者。凭据怎么填见之前的[《n8n 怎么接入 OpenAI 兼容中转 API》](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-api-openai-compatible-setup/)，本文只讲报错。

## 为什么只看到一句笼统的英文提示

n8n 源码里的通用 API 错误类 [`NodeApiError`](https://github.com/n8n-io/n8n/blob/master/packages/workflow/src/errors/node-api.error.ts) 有一张状态码对照表：只要拿到了 HTTP 状态码，就把错误标题换成表里的固定句子，服务端原来的报错文字一般会放进错误的说明（description）和消息列表里。OpenAI Chat Model 节点调用失败时，最终也会被包成这个错误类。

所以标题只告诉你「是哪一类状态码」，具体哪个参数错、哪个模型不存在，要往下看说明部分。下表是源码里和中转接入最相关的几条：

| HTTP 状态码 | n8n 显示的提示 | 接中转时先查什么 |
|---|---|---|
| 400 | Bad request - please check your parameters | 节点里开的参数、模型和接口是否匹配 |
| 401 | Authorization failed - please check your credentials | 凭据里的 API Key 是否正确 |
| 403 | Forbidden - perhaps check your credentials? | 令牌或账户是否受限，以服务端原文为准 |
| 404 | The resource you are requesting could not be found | Base URL 的 `/v1` 是否多写或少写、模型 ID 是否存在 |
| 429 | The service is receiving too many requests from you | 请求是否太密集、额度是否用完 |
| 503 | Service unavailable - try again later or consider setting this node to retry automatically (in the node settings) | 稍后重试，或开启节点设置里的自动重试 |

没在表里的 4xx、5xx，n8n 分别显示「Your request is invalid or could not be processed by the service」和「The service failed to process your request」。

## 第一步：找到服务端的原始报错

1. 打开报错的执行记录，点开出错的 OpenAI Chat Model 节点，看错误详情里标题以外的内容，找服务端返回的原文，比如带 `model`、`Invalid URL`、`Invalid token` 的那几行。
2. 原文里有 `/v1/v1/...` 这样的路径，说明 Base URL 多写了一层 `/v1`；接 OpenLux 时凭据里的 Base URL 应为 `https://api.openlux.ai/v1`，只带一次 `/v1`。OpenLux 对这种情况返回 404，原文形如 `Invalid URL (POST /v1/v1/...)`。
3. 原文是 `Invalid token (request id: ...)`，就是 OpenLux 认为 Key 无效，回控制台「令牌」页（`https://www.openlux.ai/console/token`）重新复制或新建，再更新 n8n 凭据。
4. 官方常见问题页说明，出现「Bad request - please check your parameters」是因为 n8n 没能解析出服务端的错误信息。这时说明部分可能是空的，直接做第二步。

## 第二步：用 HTTP Request 节点复现，看完整返回

官方给的办法是把同样的操作放进 [HTTP Request 节点](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/) 里跑，拿到更详细的报错。按官方文档的设置项：

- **Method** 选 `POST`，**URL** 填 `https://api.openlux.ai/v1/chat/completions`。
- 打开 **Send Headers**，加 `Authorization`，值为 `Bearer 你的令牌`。
- 打开 **Send Body**，Body Content Type 选 JSON，用 **Using JSON** 填一个最小请求体：

```json
{"model": "gpt-6-luna", "messages": [{"role": "user", "content": "hi"}]}
```

- 在节点选项里打开 **Response → Never Error** 和 **Include Response Headers and Status**。前者让 4xx、5xx 也作为结果返回，后者把状态码一起带出来，这样能直接看到服务端的错误 JSON。

成功标准：状态码 200、返回里有模型回复，说明地址、Key 和模型都没问题，问题出在 OpenAI Chat Model 节点的选项上（下一节）。如果这里也报错，错误 JSON 里的原文就是要修的地方。也可以先 GET `https://api.openlux.ai/v1/models`：能列出模型，说明地址和 Key 都对。

模型 ID 只用 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里在售的，上面的 `gpt-6-luna` 只是示例。

## 400 常见原因：Use Responses API 和模型对不上

OpenAI Chat Model 节点的 **Use Responses API** 开关决定走 Responses 接口还是 Chat Completions 接口（[官方节点文档](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatopenai/#use-responses-api)）。按 n8n 当前主分支源码，节点版本 1.3 起这个开关的默认值是打开。

中转上不是每个模型都支持 Responses。OpenLux 价格接口里每个模型都有 `supported_endpoint_types` 字段：含 `openai-response` 的才能开这个开关。按 2026-11-02 的价格接口：

| 模型示例 | supported_endpoint_types | Use Responses API |
|---|---|---|
| `gpt-6-luna`、`gpt-5.6-sol` | openai、openai-response | 开或关都可以 |
| `claude-sonnet-5-5` | anthropic、openai | 关闭 |
| `deepseek-v4-flash` | openai、anthropic | 关闭 |
| `qwen3.8-max` | openai | 关闭 |

反过来，n8n 源码里还有一条专门的提示：「This model requires the Responses API. Enable "Use Responses API" in the OpenAI Chat Model node options to use this model.」。它在服务端返回 404、报错里说这个模型「not a chat model」时出现，意思是该模型只能走 Responses。确认模型支持 `openai-response` 后打开开关即可。

另外，官方文档把 Conversation ID、Prompt Cache Key、Service Tier 等选项标为 Responses API 专用；关开关前先确认工作流不依赖它们。

## 429 与 Insufficient quota：调大重试不一定有用

n8n 的 [OpenAI 报错处理代码](https://github.com/n8n-io/n8n/blob/master/packages/@n8n/nodes-langchain/nodes/vendors/OpenAi/helpers/error-handling.ts) 对 429 分两种情况：错误码是 `insufficient_quota` 时显示「Insufficient quota detected」，其他 429 显示「OpenAI: Rate limit reached」。这两种都会直接作为错误抛出，不交给节点的 Max Retries 去重试。所以在 OpenAI Chat Model 节点里，429 看到的可能是这两句，而不是上表里的通用提示。

官方常见问题页对限流给了两个办法：用 Loop Over Items 节点把数据拆成小批次，并在末尾接 Wait 节点；或者改用 HTTP Request 节点调用接口，用它自带的批量限制选项。

至于「Insufficient quota」，官方页面教你去 OpenAI 后台查账单、组织和项目限额。那是直连 OpenAI 账号的做法；接中转时，OpenAI 后台看不到你在中转平台的情况，应到所用中转平台的控制台检查令牌状态和账户额度，确认后再重跑。

## 超时、5xx 和断线：Timeout 与 Max Retries

- **Timeout**：按源码，节点选项里 Timeout 默认 60000 毫秒。长输出或推理较久的请求可能超过 60 秒，可以按需调大。
- **Max Retries**：默认 2 次。按 n8n 默认重试规则的[源码](https://github.com/n8n-io/n8n/blob/master/packages/@n8n/ai-utilities/src/utils/failed-attempt-handler/n8nDefaultFailedAttemptHandler.ts)，400、401、402、403、404、405、406、407、409、413 不会重试，调大次数对这些错误没用，要先改配置。
- **节点设置里的 Retry On Fail**：503 提示里说的「node settings」指节点 Settings 标签里的设置。[官方节点设置文档](https://docs.n8n.io/workflows/components/nodes/)说明 Retry On Fail 开启后，执行失败时节点会重跑直到成功；On Error 选 Continue (using error output) 则把错误交给后续节点处理。官方没有说明子节点是否都有这些设置，在所用节点的 Settings 里找得到再开。

## 改完怎么确认

按顺序检查：HTTP Request 复现返回 200 → 回到 OpenAI Chat Model 节点，确认 Use Responses API 和模型的 `supported_endpoint_types` 对得上 → 用一条短输入跑一次工作流，节点不再报错并输出回复。批量任务再观察几轮，没有 429 再放大批次。

还没有中转 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=n8n-openai-chat-model-bad-request-error-fix&utm_content=footer)，在「令牌」页创建 Key 后填进 n8n 的 OpenAI 凭据。

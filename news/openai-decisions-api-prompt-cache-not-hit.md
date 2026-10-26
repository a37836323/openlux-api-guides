---
layout: default
title: "OpenAI Decisions API 缓存没命中怎么办：questions 不进缓存、1024 token 门槛与 30m 限制"
description: "OpenAI Decisions API 提示缓存不命中的排查：只缓存共享 input 前缀、questions 不进缓存也不计入 1024 token 门槛，固定规则放 input 开头加显式断点并用 explicit 模式，ttl 目前只有 30m，按 cached_tokens 与 cache_write_tokens 验证命中。"
permalink: /news/openai-decisions-api-prompt-cache-not-hit/
date: 2026-10-26
---

> 更新日期：2026-10-26 · 一手来源：[OpenAI 官方文档：Decisions](https://developers.openai.com/api/docs/guides/decisions)

# OpenAI Decisions API 缓存没命中怎么办：questions 不进缓存、1024 token 门槛与 30m 限制

Decisions API（`POST /v1/decisions`，目前只支持 `gpt-6-luna`）10 月 22 日正式可用，同时新增了提示缓存，但有开发者发现 `cached_tokens` 一直是 0。直接结论：**Decisions 只缓存共享 `input` 的前缀，`questions` 里的内容（包括问题里的图片）不在可复用前缀里，也不计入 1024 token 的门槛**；同时 Decisions 的缓存时长目前只有 `30m` 一档。所以「内容每次都变、问题每次都一样」的用法，按默认写法基本命中不了。

本文按官方 [Decisions 指南](https://developers.openai.com/api/docs/guides/decisions)、[创建 decision 接口参考](https://developers.openai.com/api/reference/resources/decisions/methods/create) 和 [Prompt caching 指南](https://developers.openai.com/api/docs/guides/prompt-caching) 整理，适用于直接调用 OpenAI 官方 Decisions API 的场景。

## 先看 usage：两个字段判断问题在哪

每次响应的 `usage.input_tokens_details` 里有两个字段：

- `cached_tokens`：本次从缓存读到的 token 数（缓存命中）。
- `cache_write_tokens`：本次写入缓存的 token 数。

官方说明这两个数都**已经包含在 `usage.input_tokens` 里**，算账时不要再加一遍。和 Responses API 不同，Decisions 的接口参考里 `input_tokens_details` 只有这两个字段，没有按时长拆分的 `cache_write_tokens_details`。

用 Python SDK 时可以这样记录（写法来自官方示例的 `client.decisions.create`）：

```python
d = client.decisions.create(model="gpt-6-luna", input=shared_input, questions=questions)
u = d.usage
print(u.input_tokens, u.input_tokens_details.cached_tokens, u.input_tokens_details.cache_write_tokens)
```

## 症状对照表

| 现象 | 最可能的原因 | 处理方向 |
|---|---|---|
| `cached_tokens` 和 `cache_write_tokens` 都是 0 | 共享前缀不到 1024 token（问题内容不算）；或用了 `prompt_cache_options.mode: "explicit"` 却没标断点 | 检查前缀长度；显式模式下至少标一个断点 |
| 每次都有 `cache_write_tokens`，`cached_tokens` 一直 0 | 断点之前的内容每次都在变，默认断点在 `input` 末尾，把变化的内容也写进了缓存 | 把固定内容放到 `input` 开头并在其后标显式断点 |
| 问题完全相同，内容不同，还是不命中 | `questions` 不属于可复用前缀，这是设计如此 | 把长且固定的规则搬到 `input` 开头的 developer 消息里 |
| 想用 12 小时缓存 | Decisions 的 `ttl` 目前只支持 `30m` | 不要传 `12h`；间隔超过 30 分钟就要接受重新写入 |
| 同一前缀，多数请求命中、少数不命中 | 通用缓存指南说明缓存存在单台机器上，流量较高时可能被分流；跨组织、跨区域处理边界不共享缓存；不同的 `prompt_cache_key` 也会分开 | 统计命中率而不是看单次；保持同一组织、区域和 key |

## 原因一：questions 不缓存，前缀不到 1024 token

官方 Decisions 指南写得很明确：

- 默认在**共享 `input` 末尾**放一个隐式缓存断点，现有请求不改代码也能用上缓存。
- 可复用前缀至少要 **1024 token**，`questions` 里的内容不计入这个门槛。
- 前缀在多次请求之间必须**完全一致**才能复用。
- **问题的 `instructions` 里不支持放断点**。

所以官方设想的典型用法是：`input` 里放一份较长的参考文档或参考图片，固定不变，每次换不同的问题去问它。OpenAI 开发者社区的 [GA 公告帖](https://community.openai.com/t/decisions-api-is-now-generally-available-with-new-updates/1408934) 下就有开发者反映「内容每次不同、问题保持不变」的场景缓存不到问题部分，这和官方文档的描述一致，不是配置错误。

如果你的 `input` 本身就很短（比如只有一句工单原文），即使每次一模一样，也达不到 1024 token，不会产生缓存。

## 原因二：断点之前的内容在变

默认的隐式断点在 `input` 的末尾，这意味着 `input` 里任何一处变化都会让整个前缀对不上。常见情况是：开头是固定的判定规则，后面接着每次不同的用户内容，结果每次都在写缓存（`cache_write_tokens` 有值），却从来读不到。

通用 Prompt caching 指南把这类情况列为「共享前缀不等于已缓存前缀」：写入时一直写到动态内容末尾，下一次动态内容一变，就匹配不上；中间没有一个落在固定内容之后的断点。

## 修复：固定内容放前面，用显式断点截住

按接口参考，`input` 里的 developer 消息、user 消息以及工具输出中的 `input_text` / `input_image` 都可以带 `prompt_cache_breakpoint: {"mode": "explicit"}`。做法是：

1. 把**长且固定**的内容（类别定义、判定规则、示例、参考资料）放在 `input` 开头的 developer 消息里。
2. 在这段内容的最后一个 `input_text` 上标显式断点。
3. 每次变化的内容放在后面的 user 消息里。
4. 设置 `prompt_cache_options.mode` 为 `"explicit"`，只在你标记的位置写缓存，避免把每次变化的内容也写进去产生写入费用。
5. `questions` 保持简短，只写这一题要判断的条件。

请求体示意（字段名来自接口参考，内容请换成你自己的）：

```json
{
  "model": "gpt-6-luna",
  "prompt_cache_options": { "mode": "explicit" },
  "input": [
    {
      "role": "developer",
      "content": [{
        "type": "input_text",
        "text": "<固定的类别定义、判定规则和示例，至少 1024 token>",
        "prompt_cache_breakpoint": { "mode": "explicit" }
      }]
    },
    {
      "role": "user",
      "content": [{ "type": "input_text", "text": "<本次待判定的内容>" }]
    }
  ],
  "questions": [
    { "type": "predicate", "name": "duplicate_charge", "instructions": "Does the user report a duplicate charge?" }
  ]
}
```

几点注意：

- 显式模式下如果一个断点都没标，这次请求**完全不使用缓存**。
- 接口参考说明：每个请求最多写 4 个断点；隐式模式会写 1 个隐式断点加最近的最多 3 个显式断点，显式模式写最近的最多 4 个显式断点。
- 从隐式模式切到显式模式后，之前隐式写入的前缀不一定能被新请求读到（通用指南的「Gotchas」专门提到），切换后可能要重新写入一次才会命中。
- 把判定标准从问题里搬到 developer 消息，属于改写提示。官方建议用自己应用里的标注样本来定路由、过滤的阈值；改动提示后，建议用同一批样本复测答案是否稳定，再上线。

## 什么时候不值得折腾

缓存不是免费的：按通用 Prompt caching 指南，GPT-5.6 及以后的模型，30 分钟缓存的写入按普通输入价的 1.25 倍计，读取在多数模型上是 0.1 倍；Decisions 页面说明它的缓存读写费率与 `gpt-6-luna` 的标准缓存费率一致，具体单价以 [官方价格页](https://developers.openai.com/api/docs/pricing) 为准。

官方指南给了一个「最小可缓存长度成本陷阱」的估算：按读取 0.1 倍、写入 1.25 倍、门槛 1024 token 计算，如果一共 10 次请求，原本至少 221 token 的固定前缀扩写到 1024 token 才更省；原本 102 token 及以下的前缀，在这些假设下扩写永远不划算。也就是说，**只为了凑门槛去硬加无用文字通常不值得**，能复用的固定内容本来就够长时，缓存才有意义。

另外，缓存的 token 仍然计入每分钟 token（TPM）限额，开缓存不会放宽限流。

## 关于 12 小时缓存

OpenAI 10 月 20 日推出的 12 小时提示缓存只在 Responses API 里提供。Decisions 接口参考对 `prompt_cache_options.ttl` 的说明是：默认 `30m`，**目前也只支持这一个值**；后端可能保留得更久，但不保证。所以：

- 不要在 Decisions 请求里传 `"ttl": "12h"`。
- 两次请求间隔经常超过 30 分钟的业务，应把「重新写入」算进成本。

Responses API 的 12 小时缓存怎么开，可以看本站的 [OpenAI 12 小时提示缓存设置与命中核对](https://a37836323.github.io/openlux-api-guides/news/openai-prompt-cache-12h-ttl-setup/)。

## 验证步骤与成功标准

1. 用同一份固定前缀（至少 1024 token）连续发两次请求，间隔不超过 30 分钟，`questions` 和后面的 user 内容可以不同。
2. 第一次：`cache_write_tokens` 大于 0，`cached_tokens` 为 0，属于正常写入。
3. 第二次：`cached_tokens` 大于 0，且接近固定前缀的长度；显式模式下 `cache_write_tokens` 不应再包含每次变化的内容。
4. 上线后按天统计命中率：`cached_tokens` 总和除以 `input_tokens` 总和（通用缓存指南推荐的算法）。组织级统计可用 `GET /v1/organization/usage/decisions`（需要带 `api.usage.read` 权限的管理员 Key），注意 `num_model_requests` 按请求计数，一个请求里有多个问题也只算一次。
5. 成功标准：命中率稳定、输入成本下降，且用标注样本复测的答案没有明显变化。

## 参考资料

- 官方文档：[Decisions](https://developers.openai.com/api/docs/guides/decisions)
- 官方接口参考：[Create decision](https://developers.openai.com/api/reference/resources/decisions/methods/create)
- 官方文档：[Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
- 官方更新日志：[Changelog](https://developers.openai.com/api/docs/changelog)

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-decisions-api-prompt-cache-not-hit&utm_content=footer)。

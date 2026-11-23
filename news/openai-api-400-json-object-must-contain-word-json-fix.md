---
layout: default
title: "OpenAI API 开 JSON 模式报 400「'messages' must contain the word 'json'」怎么办：json_object 的提示词要求、Responses 写法与改用 Structured Outputs"
description: "OpenAI API 用 json_object（Chat Completions 的 response_format 或 Responses 的 text.format）报 400「'messages' must contain the word 'json'」或「Response input messages must contain the word 'json'」：按官方 JSON 模式说明在 system 或 user 消息里写明要 JSON，或改用 Structured Outputs，并处理截断、拒绝等边界情况。"
permalink: /news/openai-api-400-json-object-must-contain-word-json-fix/
date: 2026-11-20
---

> 更新日期：2026-11-20 · 一手来源：[OpenAI Structured Outputs 指南](https://developers.openai.com/api/docs/guides/structured-outputs)

# OpenAI API 开 JSON 模式报 400「'messages' must contain the word 'json'」怎么办：json_object 的提示词要求、Responses 写法与改用 Structured Outputs

调用 OpenAI API 时把 `response_format` 设成 `{"type": "json_object"}`（Chat Completions），或把 `text.format` 设成 `{"type": "json_object"}`（Responses API），请求直接返回 400，报错原文是：

- Chat Completions：`'messages' must contain the word 'json' in some form, to use 'response_format' of type 'json_object'.`
- Responses API：`Response input messages must contain the word 'json' in some form to use 'text.format' of type 'json_object'.`

**结论先说**：这不是 Key、模型或网络的问题，而是 JSON 模式自带的一条检查——对话里必须明确要求模型输出 JSON，且上下文里要出现 “JSON” 这个词。最小改法是在 system 或 user 消息里加一句“只输出 JSON 对象”；更推荐的改法是换成 Structured Outputs（`json_schema`）。下面按官方文档说明原因、改法和改完后还要处理的情况。

本文适用于直接用 OpenAI 官方 SDK、curl 调用，以及通过 OpenAI 兼容接口（含中转）调用 GPT 模型的场景。

## 这条报错为什么会出现

OpenAI 官方 [Structured Outputs 指南](https://developers.openai.com/api/docs/guides/structured-outputs) 的 JSON mode 一节写得很清楚：

- 使用 JSON 模式时，**必须**通过对话中的某条消息（例如 system 消息）指示模型生成 JSON；
- 如果没有明确要求，模型可能输出一串没完没了的空白字符，请求会一直跑到 token 上限；
- 为了防止你忘记，**如果上下文里没有出现 “JSON” 这个字符串，API 会直接报错**。

Chat Completions 的 [API 参考](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) 对 `json_object` 也注明：没有 system 或 user 消息指示时，模型不会生成 JSON。

所以这条 400 是“保护性报错”：它在你浪费 token 之前就把请求拦下来了。这个问题在 GitHub 上很常见，例如 [sandpiper #7](https://github.com/William-Hill/sandpiper/issues/7)（gpt-4o 用 `json_object` 时报 400）、[stack #738](https://github.com/megaapp977/stack/issues/738)（Responses API 版本的同一报错）。

## 先对照：你遇到的是哪种情况

| 现象 | 原因 | 怎么改 |
|---|---|---|
| Chat Completions 报 `'messages' must contain the word 'json'` | `response_format` 是 `json_object`，messages 里没有 “JSON” | 在 system 或 user 消息里写明“只输出 JSON 对象” |
| Responses API 报 `Response input messages must contain the word 'json'` | `text.format` 是 `json_object`，input 消息里没有 “JSON” | 在 `input` 的 system 或 user 消息里写明要 JSON |
| 自己的代码没设 `json_object`，却报这个错 | 用的框架、插件或客户端打开了“JSON 输出”选项，替你加了参数 | 抓实际发出的请求体，确认是谁加的 `json_object` |
| 输出是合法 JSON，但字段名、类型不对 | JSON 模式只保证是合法 JSON，不保证符合结构 | 改用 Structured Outputs（`json_schema` + `strict`） |
| JSON 不完整、解析失败 | 输出被 `max_output_tokens` 截断，或被拒绝 / 内容过滤中断 | 看 `status`、`incomplete_details` 和 refusal，见下文 |

## 第一步：确认请求里确实开了 json_object

先看清楚实际发出的请求体，而不是只看自己写的业务代码：

1. Chat Completions 找 `response_format`，Responses API 找 `text.format`，值是 `{"type": "json_object"}` 才会触发这条检查。
2. 如果用的是 Agent 框架、工作流工具或客户端，留意它们的“JSON 模式”“结构化输出”“输出格式”之类的开关。有的框架会在主请求之外再发后续请求（比如生成追问建议），后续请求同样带 `json_object`、但消息里没有 “JSON”，也会报这个错，例如 [agno #9870](https://github.com/agno-agi/agno/issues/9870) 反映的就是这种情况。
3. 报错是 400，属于请求内容问题，原样重试不会好，要改请求。

## 第二步：在消息里写明要 JSON（最小改法）

官方的要求是“通过对话中的某条消息指示模型生成 JSON”，最直接的做法是在 system 消息里写一句，并且**直接写英文单词 JSON**，不要只写“键值对”“结构化数据”这类说法。

Chat Completions（Python）：

```python
from openai import OpenAI

client = OpenAI()
completion = client.chat.completions.create(
    model="gpt-6.2-astra",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "你是信息提取助手，只输出一个 JSON 对象，字段为 name 和 city。"},
        {"role": "user", "content": "张三住在杭州。"},
    ],
)
print(completion.choices[0].message.content)
```

Responses API（Python），写法与官方指南的 JSON mode 示例一致，把要求放在 `input` 的消息里：

```python
response = client.responses.create(
    model="gpt-6.2-astra",
    input=[
        {"role": "system", "content": "只输出一个 JSON 对象，字段为 name 和 city。"},
        {"role": "user", "content": "张三住在杭州。"},
    ],
    text={"format": {"type": "json_object"} },
)
print(response.output_text)
```

注意两点：

- Responses 版本的报错原文说的是 “Response input messages”。如果你把要求只写在了别处（比如单独的 `instructions` 参数）仍然报错，就按上面的写法把含 “JSON” 的要求放进 `input` 的 system 或 user 消息里。
- 只在用户输入里偶然出现 “json” 能通过检查，但不稳定——换一条用户输入就可能又报错。要求应该写在你自己控制的 system 消息里。

## 第三步：能用 Structured Outputs 就别用 json_object

官方明确建议：**能用 Structured Outputs 时，始终用它代替 JSON 模式**。两者区别如下（根据官方指南对照表和 API 参考整理）：

| 对比项 | Structured Outputs | JSON 模式 |
|---|---|---|
| 输出是合法 JSON | 是 | 是 |
| 符合你给的 Schema | 是 | 否 |
| 怎么开启（Responses） | `text.format` 设为 `json_schema`，带 `strict: true` 和 `schema` | `text.format` 设为 `json_object` |
| 怎么开启（Chat Completions） | `response_format` 设为 `json_schema` | `response_format` 设为 `json_object` |
| 支持的模型 | `gpt-4o-mini`、`gpt-4o-2024-08-06` 及以后 | `gpt-3.5-turbo`、`gpt-4-*`、`gpt-4o-*` 及兼容的 GPT-5 模型 |

Responses API 的写法：

```python
response = client.responses.create(
    model="gpt-6.2-astra",
    input=[
        {"role": "system", "content": "从用户输入中提取人物信息。"},
        {"role": "user", "content": "张三住在杭州。"},
    ],
    text={"format": {
        "type": "json_schema",
        "name": "person",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "city": {"type": "string"},
            },
            "required": ["name", "city"],
            "additionalProperties": False,
        },
    } },
)
```

官方指南里的 Structured Outputs 示例（如解方程的 math_reasoning 示例）消息中并没有写 “JSON”，“必须出现 JSON 字样”这条要求写在 JSON 模式一节。用 `strict: true` 时，Schema 里每个对象都要写 `"additionalProperties": false`，否则会报 Invalid schema，改法见 [Structured Outputs 报 additionalProperties 必须为 false 怎么改](https://a37836323.github.io/openlux-api-guides/news/structured-outputs-additionalproperties-false-fix/)。

老模型（如 `gpt-4-turbo` 及更早）不支持 Structured Outputs，只能继续用 JSON 模式，那就按第二步写好提示词。

## 改好之后还要处理的边界情况

官方指南提醒：JSON 模式只保证输出能被解析，不保证符合任何结构；并且在少数情况下输出可能不是完整的 JSON。官方示例要求代码检查这几种情况：

1. `status` 为 `incomplete` 且 `incomplete_details.reason` 为 `max_output_tokens`：输出到上限被截断，JSON 不完整。调大输出上限或缩短输入，排查方法见 [OpenAI API 回答只出一半、status 是 incomplete 怎么办](https://a37836323.github.io/openlux-api-guides/news/openai-api-incomplete-max-output-tokens-truncated-fix/)。
2. 输出内容类型是 `refusal`：模型拒绝了请求，`refusal` 字段里是拒绝说明，不是 JSON。
3. `status` 为 `incomplete` 且原因为 `content_filter`：生成被中断，JSON 可能只有一部分。
4. `status` 为 `completed`：没设停止词时，`output_text` 就是完整的 JSON，可以直接解析。

业务上还应在解析后校验字段：JSON 模式下字段缺失、类型不对都不会报错，这正是官方推荐换成 `json_schema` 的原因。

## 通过中转或其他 OpenAI 兼容接口调用时

- 这条报错由 OpenAI 的 API 返回；只要中转最终把请求交给 OpenAI 模型，改法和直连一样，都是改请求内容。在 OpenLux 调 GPT 模型时，Base URL 填 `https://api.openlux.ai/v1`，Key 在控制台“令牌”页（https://www.openlux.ai/console/token）创建；GPT 模型在价格页标注支持 OpenAI 兼容和 Responses 两种接口，参数按官方文档的写法传。
- 经过网关或代理库时，报错可能被包装成别的状态码，但通常仍带着这句原文。例如 [LiteLLM 的这个 PR](https://github.com/BerriAI/litellm/pull/51320) 里，同一句 `Response input messages must contain the word 'json'` 出现在 500 的 APIError 里。看到原文就按本文改，不要当成服务端故障去重试。
- 其他厂商的 OpenAI 兼容接口也可能有同样的要求，上面提到的 agno #9870 里就有 DashScope 返回同一原文的记录。

## 验证：怎么确认已经改好

用一个最小请求验证（把 `$OPENLUX_API_KEY` 换成你的 Key；直连官方就换成官方地址和 Key）：

```bash
curl https://api.openlux.ai/v1/chat/completions \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-6.2-astra",
       "response_format": {"type": "json_object"},
       "messages": [{"role": "system", "content": "Reply with a JSON object with key ok set to true."},
                    {"role": "user", "content": "test"}]}'
```

成功标准：

1. 返回 200，不再出现 `must contain the word 'json'`；
2. `choices[0].message.content` 能被 `json.loads()` 正常解析；
3. 去掉 system 消息里的 “JSON” 再发一次，应当重新出现这条 400——说明你找对了原因。

如果返回 401，是 Key 没带或写错；返回 404 且提示 `Invalid URL`，检查 Base URL 是否多写或少写了 `/v1`。

想用一个 Key 同时调 GPT、Claude、Gemini 等模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-api-400-json-object-must-contain-word-json-fix&utm_content=footer)。

## 同专题文章

- [OpenAI Embeddings 接口报 400、输入太长或数组超限怎么办：单条 8192 token、一次 2048 条、每请求 30 万 token 与空字符串逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-embeddings-400-input-too-long-8192-token-fix/)
- [OpenAI API 输入太长报 400、超出上下文窗口怎么办：token 计数、服务器端压缩、truncation 与历史裁剪逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-400-context-window-exceeded-fix/)
- [OpenAI API 回答只出一半或返回空、status 是 incomplete 或 finish_reason 是 length 怎么办：输出上限、推理 token 与上下文逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-incomplete-max-output-tokens-truncated-fix/)
- [OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-404-model-not-found-fix/)
- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

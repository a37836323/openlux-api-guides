---
layout: default
title: "OpenAI Embeddings 接口报 400、输入太长或数组超限怎么办：单条 8192 token、一次 2048 条、每请求 30 万 token 与空字符串逐项排查"
description: "OpenAI Embeddings 接口报 400 / BadRequestError、输入太长怎么办：按官方 API 参考核对单条 8192 token、不能是空字符串、数组最多 2048 项、单请求合计 30 万 token 四条限制，用 tiktoken cl100k_base 计数、切分与分批发送，dimensions 只支持 text-embedding-3 及之后模型。"
permalink: /news/openai-embeddings-400-input-too-long-8192-token-fix/
date: 2026-11-23
---

> 更新日期：2026-11-23 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/reference/resources/embeddings/methods/create)

# OpenAI Embeddings 接口报 400、输入太长或数组超限怎么办：单条 8192 token、一次 2048 条、每请求 30 万 token 与空字符串逐项排查

调用 OpenAI 的 `/v1/embeddings`（`text-embedding-3-small`、`text-embedding-3-large`、`text-embedding-ada-002`）时，如果请求被拒、Python SDK 抛出 `BadRequestError`（对应 HTTP 400），而换一段短文本又正常，问题通常出在 `input` 不满足官方 API 参考写明的四条限制：**单条输入不超过 8192 token、不能是空字符串、数组最多 2048 项、同一请求所有输入合计不超过 300,000 token**。另一类相近的问题是 `dimensions` 用在了不支持它的模型上。

本文只讲这几类输入限制，依据是 OpenAI 官方的 [Embeddings API 参考](https://developers.openai.com/api/reference/resources/embeddings/methods/create) 和 [Vector embeddings 指南](https://developers.openai.com/api/docs/guides/embeddings)。鉴权失败（401）、限流（429）不在本文范围。

## 先对照：官方写明的四条输入限制

API 参考对 `input` 参数的说明可以整理成下表：

| 限制项 | 官方要求 | 常见触发场景 |
|---|---|---|
| 单条输入长度 | 不超过模型的最大输入 token，所有嵌入模型都是 8192 | 整篇文档、整页 PDF 不切分直接嵌入 |
| 空输入 | 不能是空字符串 | 切块后留下空段落、读文件失败得到空串 |
| 数组长度 | 数组最多 2048 项 | 一次把整个知识库的所有分块塞进一个请求 |
| 单请求总量 | 所有输入合计最多 300,000 token | 每块都不超 8192，但 2048 块加起来超了 |
| `dimensions` | 只有 `text-embedding-3` 及之后的模型支持 | 给 `text-embedding-ada-002` 传了 `dimensions` |

`input` 可以是字符串、字符串数组、token 数组或 token 数组的数组；数组形式都受「1 到 2048 项」的约束。

## 诊断分支：按报错时的输入情况判断

拿到报错后，先把这次请求的 `input` 打印出来（至少打印条数和每条长度），再按下面的顺序对：

1. **只发一条、但这条很长**：大概率是单条超过 8192 token。按下一节的方法数 token 确认。
2. **发的是数组，条数上千**：先数条数是否超过 2048；不超过的话，再把每条 token 数加起来看是否超过 300,000。
3. **偶发报错，大部分批次正常**：重点查数组里有没有空字符串。切块程序遇到连续换行、只有图片的页面时，容易产出空段落。
4. **加了 `dimensions` 之后才报错**：确认模型是 `text-embedding-3-small` 或 `text-embedding-3-large`，不是 `text-embedding-ada-002`。
5. **以上都排除**：仔细读报错 `message` 里点名的参数，对照 API 参考逐项检查，官方错误码页对 `BadRequestError` 的建议也是「读错误信息、查 API 参考」（见 [Error codes](https://developers.openai.com/api/docs/guides/error-codes)）。

## 第一步：用 tiktoken 数清楚 token

不要用字符数估算，字符数和 token 数之间没有固定比例。官方指南的 FAQ 给出的做法是用 OpenAI 的分词库 `tiktoken`，并写明：**`text-embedding-3-small` 这类第三代嵌入模型使用 `cl100k_base` 编码**。

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

def num_tokens(text: str) -> int:
    return len(enc.encode(text))
```

对每条待嵌入的文本跑一遍 `num_tokens`，找出超过 8192 的那几条；再把整批的结果求和，和 300,000 比较。调用成功后，响应里的 `usage.prompt_tokens` 就是本次请求实际计入的输入 token，可以拿来核对自己的计数。

## 第二步：单条超过 8192 token，先切分再嵌入

API 不会替你把超长文本拆开，需要在发送前自己切分。最直接的办法是按 token 切：

```python
def split_by_tokens(text: str, max_tokens: int = 8000):
    ids = enc.encode(text)
    return [enc.decode(ids[i:i + max_tokens]) for i in range(0, len(ids), max_tokens)]
```

这里留了一点余量（8000 而不是 8192）。实际做知识库检索时，块通常会切得更小，按段落或标题切分更利于检索命中；块大小怎么定官方指南没有给固定数值，按自己的检索效果调。切分后，原来的一条文本变成多条，记得在你自己的数据里保存「块 → 原文档」的对应关系，方便检索后回到原文。

## 第三步：数组超过 2048 项或合计超过 30 万 token，分批发送

批量嵌入时，同时守住两条：**每批最多 2048 条**，**每批 token 合计不超过 300,000**。下面的分批函数按顺序装箱，任一条件快到上限就开新批：

```python
def make_batches(texts, max_items=2048, max_total=300_000):
    batch, total = [], 0
    for t in texts:
        n = num_tokens(t)
        if batch and (len(batch) >= max_items or total + n > max_total):
            yield batch
            batch, total = [], 0
        batch.append(t)
        total += n
    if batch:
        yield batch
```

传入前先保证每条都不超过 8192 token（用上一节的切分）。响应的 `data` 里每个结果都带 `index` 字段，表示它在本批输入里的位置；合并多批结果时按 `index` 对回原文，不要假设顺序。

## 第四步：过滤空字符串，检查 dimensions

**空字符串**：官方明确要求输入不能是空字符串。在切块之后、调用之前加一道过滤，把空串去掉。只含空格、换行的段落对检索也没有意义，建议一并去掉（这是做法建议，官方只写了空字符串）。

```python
texts = [t for t in texts if t and t.strip()]
```

**dimensions**：这个参数只有 `text-embedding-3` 及之后的模型支持。默认长度是 `text-embedding-3-small` 为 1536、`text-embedding-3-large` 为 3072。如果向量库限制了维度（官方指南举的例子是只支持 1024 维的向量库），官方建议在请求里用 `dimensions` 直接要短向量；自己手工截断时，必须重新做 L2 归一化。

改了模型或维度以后，库里已有的向量和新向量长度不一致，写入或检索会报维度不匹配，这时要用同一模型和维度重建索引，可参考本站的 [Pinecone 报 Vector dimension does not match 怎么办](https://a37836323.github.io/openlux-api-guides/news/pinecone-vector-dimension-mismatch-fix/)。

## 验证：怎样算修好了

按下面三条逐项确认：

- 用一条确认不超过 8192 token 的文本单独请求，返回里有 `data[0].embedding`，`object` 为 `list`。
- 正式批量跑之前，先打印每批的条数和 token 合计，确认都在 2048 条、300,000 token 以内。
- 每批返回的 `data` 条数和发送的条数一致；如果用了 `dimensions`，抽查向量长度等于设置值。

走 OpenAI 兼容接口的第三方服务或中转时，请求格式相同，但具体能用哪些嵌入模型、限制是否完全一致，以该服务的模型列表和说明为准；本文的数字来自 OpenAI 官方文档。

## 常见问题

**能不能让接口自动截断超长文本？** Embeddings API 参考里没有自动截断的参数，超长文本需要在发送前自己切分。

**为什么每条都不长，还是被拒？** 看单请求总量：2048 条的上限和 300,000 token 的上限是两条独立限制，条数没超、总 token 也可能超。

**用 token 数组作为输入也受限吗？** 受限。token 数组和 token 数组的数组同样适用 1～2048 项和单条 8192 token 的规则。

需要一个 OpenAI 兼容接口来调用嵌入和对话模型，可以在这里注册：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-embeddings-400-input-too-long-8192-token-fix&utm_content=footer)

## 同专题文章

- [OpenAI API 开 JSON 模式报 400「'messages' must contain the word 'json'」怎么办：json_object 的提示词要求、Responses 写法与改用 Structured Outputs](https://a37836323.github.io/openlux-api-guides/news/openai-api-400-json-object-must-contain-word-json-fix/)
- [OpenAI API 输入太长报 400、超出上下文窗口怎么办：token 计数、服务器端压缩、truncation 与历史裁剪逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-400-context-window-exceeded-fix/)
- [OpenAI API 回答只出一半或返回空、status 是 incomplete 或 finish_reason 是 length 怎么办：输出上限、推理 token 与上下文逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-incomplete-max-output-tokens-truncated-fix/)
- [OpenAI API 报 404「The model `xxx` does not exist or you do not have access to it」怎么办：模型 ID、项目权限、Key 与已下线模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-404-model-not-found-fix/)
- [OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-python-apiconnectionerror-timeout-fix/)
- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

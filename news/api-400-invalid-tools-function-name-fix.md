---
layout: default
title: "调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符"
description: "调用 OpenAI、Claude、Gemini API 带工具时报 400「Invalid 'tools[0].function.name'」的原因与修法：各家工具名允许的字符和长度（OpenAI 64、Claude 128）、MCP 工具名带点号和客户端拼服务器 ID 前缀为什么会撞上，以及如何生成合法别名并映射回原工具。"
permalink: /news/api-400-invalid-tools-function-name-fix/
date: 2026-11-22
---

> 更新日期：2026-11-22 · 一手来源：[OpenAI API Reference](https://developers.openai.com/api/reference/resources/chat)

# 调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符

这条报错的意思是：请求的 `tools` 数组里，有一个工具的名字不符合接口的命名规则。方括号里的数字是这个工具在数组里的位置（从 0 开始数）。**整个请求都会被拒绝**，哪怕模型这一轮根本不会用到这个工具，所以表现是"一开工具就完全没有回复"。

最常见的原因有三种：名字里有点号、冒号、空格等字符；名字超过 64 个字符；客户端为了区分同名工具，自动在名字前面拼了服务器 ID。修法是：发给模型的名字统一改成只含字母、数字、下划线和横线，长度不超过 64，自己的代码里保留"别名 → 原名"的对照，收到工具调用时再换回原名执行。

## 各家接口对工具名的规定

规则来自各家官方文档，下表按 2026 年 11 月的版本整理：

| 接口 | 字段 | 允许的字符 | 最长 | 依据 |
|---|---|---|---|---|
| OpenAI Chat Completions | `tools[].function.name` | a-z、A-Z、0-9、下划线、横线 | 64 | [OpenAI API 参考](https://developers.openai.com/api/reference/resources/chat) |
| Claude Messages | `tools[].name` | 正则 `^[a-zA-Z0-9_-]{1,128}$` | 128 | [Claude 定义工具文档](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) |
| Gemini（声明工具） | `functionDeclarations[].name` | a-z、A-Z、0-9、下划线、冒号、点号、横线 | 128 | [Gemini API 参考](https://ai.google.dev/api/caching) |
| Gemini（调用与结果） | `FunctionCall` / `FunctionResponse` 的 `name` | a-z、A-Z、0-9、下划线、横线 | 128 | 同上 |
| MCP 规范 2025-11-25 | `Tool.name` | 字母、数字、下划线、横线、点号（"应当"级要求） | 128 | [MCP 工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) |

几点说明：

- OpenAI Chat Completions 的官方原文是 "Must be a-z, A-Z, 0-9, or contain underscores and dashes, with a maximum length of 64"，**点号、冒号、空格、中文都不行**。
- OpenAI Responses API 的[函数调用指南](https://developers.openai.com/api/docs/guides/function-calling)只说 `name` 是函数名（例如 `get_weather`），没有另外列字符规则。同一套工具可能在两个接口之间切换时，按 Chat Completions 的规则取名最稳妥。
- Gemini 声明工具时允许冒号和点号，但模型返回的 `FunctionCall` 名字规则更窄。为了不踩边界，建议也不要用。
- 如果通过中转调用，同一份工具定义可能发给不同厂商的模型。直接按最严的规则取名：`^[a-zA-Z0-9_-]{1,64}$`，以后换模型也不用再改。

## 为什么 MCP 工具和多个工具服务器最容易撞上

**MCP 允许点号。** MCP 规范给的合法工具名例子里就有 `admin.tools.list`，长度上限也是 128。客户端如果把 MCP 工具名原样转给 OpenAI Chat Completions 或 Claude，点号就会让请求被拒；超过 64 个字符的名字也过不了 OpenAI。

**客户端自动拼前缀。** Open WebUI 用户在 2026 年 11 月连续报告了这类问题：

- [#34736](https://github.com/open-webui/open-webui/issues/34736)：两个 OpenAPI 工具服务器提供同名工具时，Open WebUI 会把服务器 ID 拼到第二个工具名前面，但没有控制长度，超过 64 个字符后整个对话失败。报告里还提到，FastAPI 默认用函数名加路由路径生成名字，一个较长的路由就能生成 91 个字符的名字。该项目之前已经给 MCP 服务器做了长名缩短（#31821），报告提出时 OpenAPI 工具服务器这条路径还没有。
- [#34718](https://github.com/open-webui/open-webui/issues/34718)、[#34729](https://github.com/open-webui/open-webui/issues/34729)：Tether 接入的服务器 ID 带冒号，拼出来的工具名也带冒号，报 `Invalid 'tools[0].name'` 或 `Invalid 'tools[1].function.name'`。

所以"工具单独用没问题，和另一个服务器一起开就报错"，基本就是拼前缀造成的。

## 第一步：找出是哪一个工具不合法

1. 看报错里的下标，比如 `tools[1]` 就是数组里第 2 个工具。
2. 把实际发出的请求体打印出来（不要只看自己写的工具定义，客户端可能改过名字），逐个检查：

```python
import re

SAFE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

for i, t in enumerate(tools):
    name = t.get("function", t).get("name", "")
    if not SAFE.match(name):
        print(i, len(name), name)
```

`t.get("function", t)` 同时兼容 Chat Completions 的写法（名字在 `function` 里）和 Claude 的写法（名字在工具对象顶层）。打印出来的就是要改的工具。

3. 顺便检查有没有两个工具同名。很多客户端就是为了避开重名才去拼前缀的。

## 第二步：把发给模型的名字和真实工具名分开

自己写代码调用时，不要直接改工具服务器上的真实名字，而是在发请求前生成一个合法的别名，同时记下对照关系：

```python
import hashlib
import re

def safe_tool_name(original, limit=64):
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", original)
    if name == original and 0 < len(name) <= limit:
        return name  # 本来就合法，原样使用
    digest = hashlib.sha1(original.encode()).hexdigest()[:8]
    return name[: limit - 9] + "_" + digest

alias_to_original = {}
for t in tools:
    fn = t["function"]
    alias = safe_tool_name(fn["name"])
    alias_to_original[alias] = fn["name"]
    fn["name"] = alias
```

要点：

- 非法字符换成下划线；只要改过名字或超长，就截短并加上原名的 8 位哈希。这样 `a.b` 和 `a_b` 这种替换后会撞名的情况也能分开。
- 模型返回工具调用后，用 `alias_to_original[调用里的名字]` 找回原工具再执行。Open WebUI #34718 里提出的修复思路也是这样：给模型看的名字稳定、不重复、合法，真实调用仍用原名。
- 需要区分不同服务的工具时，用下划线做前缀，比如 `github_list_prs`、`slack_send_message`。Claude 官方文档也建议这样给工具名加服务前缀。

## 用客户端、改不了代码时怎么办

- **把工具服务器上的工具名改短**，去掉点号和冒号；
- **缩短工具服务器的 ID**，因为它可能被拼进工具名；
- **同名工具只开一个**：两个服务器提供同名工具时，在当前对话里先关掉其中一个；
- **关注客户端的修复进度**：上面几个 Open WebUI 问题写明了原因，修复发布后升级即可。在那之前，按前三条处理最快。

## 第三步：验证是否修好

1. 本地用第一步的正则把所有工具名再跑一遍，没有任何输出才算通过。
2. 带上改名后的 `tools` 发一次最小请求，返回 200，不再是 400。
3. 让模型真正调用一次工具，确认返回的名字能在对照表里找到，并且执行的是原来那个工具。

## 容易混淆的其他工具报错

| 现象 | 原因方向 | 参考 |
|---|---|---|
| 名字合法，但报 schema 不合法、`additionalProperties` 相关错误 | 参数 JSON Schema 写法问题 | [Invalid schema：additionalProperties 必须为 false](https://a37836323.github.io/openlux-api-guides/news/structured-outputs-additionalproperties-false-fix/) |
| Claude 报 `tool_use` ids were found without `tool_result` blocks | 回传工具结果时缺块或顺序不对 | [Claude tool_use 缺 tool_result 排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-tool-use-without-tool-result-fix/) |
| 请求成功、模型也给了参数，但执行失败 | 参数内容没有校验 | [工具调用参数校验](https://a37836323.github.io/openlux-api-guides/news/tool-call-arguments-validation-contract/) |
| 只在某一家的模型上报名字错误 | 各家规则不同，比如 Gemini 声明工具时接受点号，OpenAI 不接受 | 见本文第一张表 |

## 开始使用

想用同一份工具定义调用 GPT、Claude、Gemini 等模型，可以注册 OpenLux 账号，在控制台「令牌」页创建令牌，按上面的规则统一工具名后接入：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=api-400-invalid-tools-function-name-fix&utm_content=footer)

## 同专题文章

- [Hugging Face Chat UI 怎么接入 OpenAI 兼容中转 API：OPENAI_BASE_URL、Key 与模型设置（npm / Docker）](https://a37836323.github.io/openlux-api-guides/news/huggingface-chat-ui-relay-api-openai-base-url-setup/)
- [LangChain OpenAIEmbeddings 怎么接中转 API 的嵌入模型：base_url、check_embedding_ctx_length、text-embedding-3 与 dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/langchain-openaiembeddings-relay-api-base-url-setup/)
- [LangChain 怎么接入 OpenAI 兼容中转 API：ChatOpenAI、init_chat_model 的 base_url、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/langchain-chatopenai-relay-api-base-url-setup/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？](https://a37836323.github.io/openlux-api-guides/news/how-to-deploy-rumble-2-flash-with-transformers/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

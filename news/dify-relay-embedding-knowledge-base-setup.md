---
layout: default
title: "Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置"
description: "Dify 知识库用高质量索引时，怎么让嵌入模型走 OpenAI 兼容中转 API：在 OpenAI-API-compatible 插件里添加嵌入类型模型，API Base URL 填到 /v1，模型名称填 text-embedding-3-small 等在售 ID，上下文长度、encoding format 等字段怎么填，设为默认 Embedding 模型后用检索测试验证，并附 401、404、选不到模型、超时的排查。"
permalink: /news/dify-relay-embedding-knowledge-base-setup/
date: 2026-11-20
---

> 更新日期：2026-11-20 · 一手来源：[Dify 官方文档](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)

# Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置

Dify 知识库选「高质量」索引时要用嵌入模型把分段转成向量。想让这一步走中转 API，做法是在官方插件「OpenAI-API-compatible」里再添加一个**嵌入类型**的模型：模型名称填中转站在售的嵌入模型 ID（如 `text-embedding-3-small`），API Base URL 填到 `/v1`（以 OpenLux 为例是 `https://api.openlux.ai/v1`），然后在「默认模型设置」里把它设为 Embedding 模型，或在知识库设置里直接选它。插件发请求时会在 Base URL 后面接 `/embeddings`，所以 `/v1` 少写或多写都会出错。

本文适用于已经能用插件市场的 Dify 云版和自部署版，已经按 [Dify 怎么接入 OpenAI 兼容中转 API](https://a37836323.github.io/openlux-api-guides/news/dify-relay-api-openai-compatible-setup/) 配好对话模型的读者可以直接从第二步看。步骤依据 [Dify 官方文档「模型供应商」](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)、[「指定索引方式与检索设置」](https://docs.dify.ai/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods) 和 Dify 官方维护的 OpenAI-API-compatible 插件源码；字段名以撰文时插件 0.0.84 版为准，旧版本界面可能不同。

## 先弄清：什么情况下才需要嵌入模型

Dify 官方文档给知识库提供两种索引方式，只有「高质量」用嵌入模型：

| 索引方式 | 是否调用嵌入模型 | 检索方式 | 官方说明的限制 |
|---|---|---|---|
| 高质量 | 是，分段和提问都要转成向量 | 向量检索、全文检索、混合检索 | 以高质量创建后，不能再切换回经济 |
| 经济 | 否，每个分段用 10 个关键词，不消耗 Token | 只有倒排索引 | 效果不满意时可在知识库设置里升级为高质量 |

所以：只用经济索引，不必配嵌入模型；要用语义检索、混合检索，就必须先有一个可用的嵌入模型。官方文档还写明，「默认模型设置」里的 Embedding 模型为空时，依赖它的功能就用不了。

## 第一步：准备 Key 和模型 ID

- **权限**：官方文档写明，只有工作空间所有者和管理员可以管理模型供应商，填入的 Key 对整个工作空间生效。
- **Key**：在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token`。Key 只填进 Dify，不要贴到截图或聊天里。
- **模型 ID**：只填中转站在售的嵌入模型 ID。OpenLux 的在售列表见价格接口 `https://www.openlux.ai/api/pricing_new`，撰文时里面有 `text-embedding-3-small`、`text-embedding-3-large`、`text-embedding-ada-002`，以接口当前返回为准。
- **先选定模型再导入文档**：OpenAI 嵌入指南写明，`text-embedding-3-small` 默认输出 1536 维、`text-embedding-3-large` 默认 3072 维。Dify 官方文档写明，知识库换嵌入模型会把全部分段重新向量化，文档多时代价不小，最好一开始就定下来。

## 第二步：在 OpenAI-API-compatible 里添加嵌入模型

打开「集成」→「模型供应商」，在 OpenAI-API-compatible 卡片上点「添加模型」，模型类型选嵌入模型（插件配置里这一类的类型名是 `text-embedding`，不要选 LLM），按下表填写。字段名、默认值来自插件配置文件 `openai_api_compatible.yaml`：

| 字段 | 填写内容 | 说明 |
|---|---|---|
| 模型名称 | `text-embedding-3-small` 等在售 ID | 插件提示「输入模型全称」 |
| 模型显示名称 | 如「text-embedding-3-small（OpenLux）」 | 选填，只影响界面显示 |
| API Key | OpenLux「令牌」页创建的 Key | 插件以 `Authorization: Bearer` 头发送 |
| API Base URL | `https://api.openlux.ai/v1` | 必填；插件示例为 `https://api.openai.com/v1`，同样带 `/v1` |
| API endpoint中的模型名称 | 一般留空 | 填了会代替「模型名称」发给接口 |
| 模型每批的最大分块数 | 保持默认 `1` | 必填，按字段名是一次请求放几个分段 |
| 模型上下文长度 | `8192` | 必填，插件默认 4096；OpenAI 嵌入指南写明这三个模型的最大输入都是 8192 |
| Embedding encoding format | 先保持 `not_set` | 插件说明：遇到要求显式带 `encoding_format` 的严格网关时改成 `float` |
| 视觉支持 | 保持「不支持」 | 只有多模态嵌入模型才开；OpenAI 嵌入指南讲的是文本输入 |
| 文档前缀、查询前缀 | 留空 | 插件会把前缀加一个空格拼在文本前面；OpenAI 嵌入指南没有要求加前缀 |

插件源码里，文本嵌入请求是 `POST {API Base URL}/embeddings`，请求体为 `{"model": 模型名称, "input": [分段文本…]}`，每次请求超时 60 秒。因此 Base URL 填 `https://api.openlux.ai/v1` 时，实际请求的是 `https://api.openlux.ai/v1/embeddings`。

点保存时，插件会用你填的地址、Key 和模型名对单词 `ping` 发一次嵌入请求，通过了才能保存。地址、Key、模型名任何一项不对，都会在这一步报错。

## 第三步：设为默认，或在知识库里选它

- **设为工作空间默认**：点模型供应商页右上角的「默认模型设置」，把「Embedding 模型」选成刚加的模型。之后新建知识库、没单独选模型的地方都用它。
- **新建知识库时选**：「知识库」→「创建」→「创建即用型知识库」，上传文档、设好分段后，在索引方式里选「高质量」，嵌入模型选刚加的模型。
- **已有知识库换过来**：进入知识库，点左侧「设置」，在「嵌入模型」里改。官方文档提醒：更换嵌入模型会对所有分段重新向量化。只有工作空间所有者、管理员和编辑者能改知识库设置。

## 第四步：验证接通和检索效果

**在 Dify 里看**：第二步能保存，说明插件那次 `ping` 请求成功了。再到知识库左侧点「检索测试」，输入一句文档里有答案的问题，能召回相关分段就算接通。官方文档写明，检索测试里临时调整的检索设置只在当次测试有效；「记录」里能看到测试和应用发起的检索。

**在命令行看**：保存失败又分不清是哪一项时，在运行 Dify 的那台服务器上（自部署时结果才能代表 Dify 发出的请求）先请求一次模型列表，把 `$OPENLUX_API_KEY` 换成自己的 Key：

```bash
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

能列出模型，说明地址和 Key 都对，问题在 Dify 里的填写；返回 401 说明 Key 错了或没带上。想完全按插件的方式再测一次，可以照 OpenAI 嵌入指南的写法发一条嵌入请求，返回里 `data[0].embedding` 是一串数字就说明嵌入接口可用：

```bash
curl https://api.openlux.ai/v1/embeddings \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "text-embedding-3-small", "input": ["ping"]}'
```

## 常见报错和处理

插件把非 200 的响应当作 HTTP 错误抛出，所以接口返回 401、404 这类错误时，报错里一般能看到状态码和请求的完整地址。先看地址是不是 `https://api.openlux.ai/v1/embeddings`，很多问题一眼就能定位。

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 保存时报 401 | Key 填错、复制不完整，或没填 | 重新复制 Key，用上面的 `/v1/models` 命令单独验证 |
| 报 404，或报 JSON 解析错误（如 `Expecting value`），看不出原因 | API Base URL 少了 `/v1`，请求发到了 `https://api.openlux.ai/embeddings` | 改成 `https://api.openlux.ai/v1`。少了 `/v1` 时具体报什么取决于那个地址返回什么，所以报错不一定带地址，先核对 Base URL |
| 报错里的地址出现两次 `embeddings` | Base URL 填成了完整接口 `…/v1/embeddings` | 只填到 `/v1`，插件会自己接 `/embeddings` |
| 提示模型不存在或不可用 | 模型名称和在售 ID 不一致，或填了对话模型 | 对照价格接口复制嵌入模型的准确 ID |
| 知识库设置里选不到这个模型 | 添加时模型类型选成了 LLM | 重新添加，模型类型选嵌入模型 |
| 保存时报错，提示与 `encoding_format` 有关 | 网关要求请求里显式带编码格式 | 把「Embedding encoding format」改成 `float` 再保存 |
| 文档索引失败，报错里有 timeout 或连接错误 | 运行 Dify 的服务器连不上中转地址，或单次请求超过插件的 60 秒超时 | 自部署先在那台服务器上跑上面两条 curl，看能否连通、要多久返回 |

最后两行是按插件源码的行为写的处理方向，Dify 官方文档没有给出这两种情况的报错原文；`encoding_format` 一行的处理来自插件配置文件里的字段说明。

## 参考资料

- Dify 官方文档：[模型供应商](https://docs.dify.ai/zh/self-host/use-dify/workspace/model-providers)（添加自定义模型、凭据验证、默认模型设置、管理权限）
- Dify 官方文档：[指定索引方式与检索设置](https://docs.dify.ai/zh/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods)、[调整知识库设置](https://docs.dify.ai/zh/self-host/use-dify/knowledge/manage-knowledge/introduction)、[测试检索](https://docs.dify.ai/zh/self-host/use-dify/knowledge/test-retrieval)
- 插件源码：[openai_api_compatible.yaml](https://github.com/langgenius/dify-official-plugins/blob/main/models/openai_api_compatible/provider/openai_api_compatible.yaml)（字段名、默认值与说明）、[text_embedding.py](https://github.com/langgenius/dify-official-plugins/blob/main/models/openai_api_compatible/models/text_embedding/text_embedding.py)（请求地址、凭据验证、超时）
- OpenAI 官方文档：[Embeddings 指南](https://developers.openai.com/api/docs/guides/embeddings)（最大输入、默认维度、请求格式）

配好后想直接试：[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=dify-relay-embedding-knowledge-base-setup&utm_content=footer)，在「令牌」页创建 Key 后按上面的表格填进 Dify。

## 同专题文章

- [Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-tab-autocomplete-not-working-fix/)
- [Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-embedding-knowledge-base-rag-setup/)
- [Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)
- [n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查](https://a37836323.github.io/openlux-api-guides/news/n8n-ai-agent-relay-prompt-content-null-session-fix/)
- [Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办](https://a37836323.github.io/openlux-api-guides/news/cline-cli-relay-api-auth-baseurl-setup/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

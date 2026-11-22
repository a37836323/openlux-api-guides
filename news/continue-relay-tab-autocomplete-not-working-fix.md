---
layout: default
title: "Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查"
description: "Continue 接中转 API 后 Tab 自动补全不出建议、补得乱或很慢的排查：roles 默认不含 autocomplete、官方不建议用 GPT/Claude 聊天模型补全、FIM 补全模型（Qwen2.5-Coder、Codestral）单独配置、思考模型、多行补全与日志。"
permalink: /news/continue-relay-tab-autocomplete-not-working-fix/
date: 2026-11-19
---

> 更新日期：2026-11-19 · 一手来源：[Continue 官方文档](https://docs.continue.dev/customize/deep-dives/autocomplete)

# Continue 接中转 API 后 Tab 自动补全不出来、补得乱或很慢怎么办：autocomplete 角色、FIM 模型与开关逐项排查

Continue 接上中转 API 后，聊天和 Agent 能用，但写代码时 Tab 自动补全不出灰色建议、补出来的东西像聊天回答、或者反应很慢，常见原因是**把 GPT、Claude 这类聊天模型当成了自动补全模型**。[Continue 官方 Autocomplete 文档](https://docs.continue.dev/customize/deep-dives/autocomplete)的 FAQ 直接回答了「能不能用 GPT-5 或其他聊天模型做自动补全」：不建议，因为自动补全模型是按特定的提示格式训练的，GPT-5、Claude 没有这种训练，原文是 “won't generate useful completions”。

所以正确的做法是分角色配置：中转里的聊天模型负责聊天、编辑、应用改动，Tab 补全单独配一个官方推荐的补全模型。本文适用于 VS Code 和 JetBrains 里的 Continue 扩展、用 `config.yaml` 配置的读者；设置项名称以撰文时的官方文档为准。还没接通中转的，先看 [Continue 怎么接入 OpenAI 兼容 / Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/continue-relay-api-openai-compatible-setup/)。

## 先按现象找原因

| 现象 | 先查什么 | 本文对应小节 |
|---|---|---|
| 完全没有灰色建议 | 自动补全开关、Copilot 等其他补全是否开着、`editor.inlineSuggest.enabled` | 第一步 |
| 没有任何模型在做补全 | 是否有模型带 `autocomplete` 角色、面板里选没选默认补全模型 | 第二步 |
| 有建议，但内容乱、像聊天回答 | 补全模型是不是 GPT、Claude 这类聊天模型 | 第三步、第四步 |
| 建议出来很慢 | 是否用了思考模型或大模型 | 第五步 |
| 只补一行 | `multilineCompletions` 设置 | 第六步 |
| 以上都查过还是不行 | 看 Continue 日志 | 第七步 |

## 第一步：确认自动补全开关和编辑器设置

按官方 Autocomplete 文档的「Autocomplete not working」排查顺序，先排除和模型无关的原因：

1. **自动补全开关**：确认「Enable Tab Autocomplete」是打开的。VS Code 里点状态栏上的 Continue 按钮切换；JetBrains 在 Settings → Tools → Continue 里勾选。
2. **关掉其他补全**：官方建议停用其他补全提供方，例如 GitHub Copilot。
3. **编辑器内联建议**：VS Code 的 `"editor.inlineSuggest.enabled"` 必须是 `true`。如果你之前为了「手动触发补全」把它改成了 `false`，Continue 就不会自动弹出建议，只能用你绑定的快捷键触发。
4. **按文件关掉的情况**：IDE 用户设置里的「Disable autocomplete in files」是逗号分隔的通配符列表，看看当前文件是不是被它排除了。

## 第二步：确认有模型承担 autocomplete 角色

Continue 用 `roles` 决定一个模型做什么。按 [config.yaml 参考](https://docs.continue.dev/reference)，可选值有 `chat`、`autocomplete`、`embed`、`rerank`、`edit`、`apply`、`summarize`，**不写时默认是 `[chat, edit, apply, summarize]`，不含 `autocomplete`**。

这意味着：按接入教程只给中转模型写了 `provider`、`model`、`apiBase`、`apiKey`，没写 `roles`，这条模型只会用在聊天、编辑和应用改动上，Tab 补全没有模型可用。

要让某个模型负责补全，就在它的 `roles` 里写上 `autocomplete`。官方文档的示例里还提到，配好后要在 Continue 面板里把它选为默认的自动补全模型。

## 第三步：为什么不要把中转里的聊天模型设成补全模型

[Continue 官方 Autocomplete 角色说明](https://docs.continue.dev/customize/model-roles/autocomplete)写明，自动补全模型是按 FIM（fill-in-the-middle，中间填充）格式训练的：把光标前后的代码给模型，让它预测中间缺的部分。官方还提到，大型聊天模型即使写了大量提示词，在这件事上也常常表现不好；而补全任务很窄，小模型就够，原文举例 3B 参数的模型也能做得不错。

官方推荐的补全模型是：

| 类型 | 官方推荐 |
|---|---|
| 开源（本地 Ollama） | Qwen2.5-Coder 1.5B、Qwen2.5-Coder 7B |
| 闭源 | Codestral、Mercury Coder |

官方的评价是闭源模型略好于开源模型。

写本文时（2026-11-19）查了 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 的在售列表，**没有上面这几款补全模型**；在售的是 `gpt-5.6-sol`、`claude-sonnet-5-5` 这类聊天模型，按官方说法不适合做 Tab 补全。所以接 OpenLux 时，建议只把它用在聊天、编辑、Agent 上，补全另配。在售列表会变化，以价格接口为准。

## 第四步：推荐配置——聊天走中转，补全单独配

下面是一份 `config.yaml` 示例：中转模型保持默认角色（聊天、编辑、应用），本地 Ollama 的 Qwen2.5-Coder 1.5B 只做补全。补全模型的写法照抄官方 Ollama 示例，使用前先装好 [Ollama](https://ollama.ai) 并运行 `ollama run qwen2.5-coder:1.5b` 下载模型。

```yaml
name: My Config
version: 0.0.1
schema: v1
models:
  - name: OpenLux gpt-5.6-sol
    provider: openai
    model: gpt-5.6-sol
    apiBase: https://api.openlux.ai/v1
    apiKey: <你的 OpenLux Key>
  - name: Qwen 1.5b Autocomplete Model
    provider: ollama
    model: qwen2.5-coder:1.5b
    roles:
      - autocomplete
```

不想跑本地模型，可以按官方写法改用 Codestral：在 Mistral 控制台拿 Key，`provider: mistral`、`model: codestral-latest`、`roles: [autocomplete]`。官方特别说明 Codestral 的 Key 和普通 Mistral Key 不是同一种；如果用的是团队共用 Key 或 `api.mistral.ai`，要加 `apiBase: "https://api.mistral.ai/v1"`。

`config.yaml` 里写着明文 Key，分享配置或截图前先删掉。保存后，在 Continue 面板里确认默认补全模型是 `Qwen 1.5b Autocomplete Model`（或你配的 Codestral）。

## 第五步：补全很慢，先看是不是思考模型

官方 Autocomplete 文档说思考模型一般不推荐用来补全，因为生成慢。如果模型支持关掉思考，官方给的 Ollama 写法是在这条模型下加：

```yaml
    requestOptions:
      extraBodyProperties:
        think: false
```

`extraBodyProperties` 的作用是把这些字段合并进请求体。这个 `think: false` 是 Ollama 示例里的字段，别的服务商不一定认，不要照搬到中转模型上。另外，官方提到大多数优秀的补全模型在 10B 参数以内，换更大的模型帮助不大，反而更慢。

## 第六步：只补一行、触发时机不合适

- **只出单行**：官方说明多行补全默认是 `auto`，可以在 IDE 用户设置里把「Multiline Autocompletions」改成 `always`（旧版 `config.json` 里对应 `tabAutocompleteOptions` 的 `"multilineCompletions": "always"`）。官方还提到，光标在文件中间时有些模型输出会变短，可以临时把光标下方的内容移走，或换更大的补全模型试试。
- **想调触发延迟、超时**：在补全模型下写 `autocompleteOptions`。按 config.yaml 参考，`debounceDelay` 是触发补全前的延迟（毫秒），`modelTimeout` 是补全请求的超时（毫秒），`maxPromptTokens` 是补全提示的最大 token 数；这些选项只对带 `autocomplete` 角色的模型生效。官方页面给的示例值是 `debounceDelay: 250`、`modelTimeout: 150`，但没有说明这些就是默认值，按自己的情况调。
- **想一行一行接受**：VS Code 里把 `editor.action.inlineSuggest.acceptNextLine` 绑到 Tab，「when」条件设为 `inlineSuggestionVisible && !editorReadonly`，剩下的部分按 Esc 丢弃。

## 第七步：查日志并验证

如果以上都配好了还是没有建议，按官方说明看日志：

- VS Code：打开 Developer Tools，看 Console 里的报错；
- JetBrains：看 `~/.continue/logs/core.log`。

日志里如果是补全模型连不上，可以回头检查 Ollama 是否在运行、模型是否已下载，或 Codestral 的 Key 和 `apiBase`。官方排查清单的最后一步是到 [GitHub Issues](https://github.com/continuedev/continue/issues) 提问。

**怎样算修好**：

1. 打开一个代码文件，输入函数签名或注释后停一下，能出现灰色的补全建议，按 Tab 能接受；
2. 聊天面板里选 `OpenLux gpt-5.6-sol` 发一条问题能正常回答，说明中转那一侧没受影响。聊天侧报错时，可以在终端用 `curl https://api.openlux.ai/v1/models -H "Authorization: Bearer $OPENLUX_API_KEY"` 单独确认地址和 Key：能列出模型说明两者都对，返回 401 说明 Key 错了或没带上。

## 参考资料

- Continue 文档：[Autocomplete（深入说明与 FAQ）](https://docs.continue.dev/customize/deep-dives/autocomplete)
- Continue 文档：[Autocomplete 角色](https://docs.continue.dev/customize/model-roles/autocomplete)（FIM、推荐模型）
- Continue 文档：[config.yaml Reference](https://docs.continue.dev/reference)（`roles` 默认值、`autocompleteOptions`、`requestOptions`）
- Continue 文档：[OpenAI 配置](https://docs.continue.dev/customize/model-providers/top-level/openai)（OpenAI 兼容服务商改 `apiBase`）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=continue-relay-tab-autocomplete-not-working-fix&utm_content=footer)，在「令牌」页创建 Key，把中转模型配成 Continue 的聊天和编辑模型。

## 同专题文章

- [n8n 知识库（RAG）怎么接中转 API 的嵌入模型：Embeddings OpenAI 节点、Base URL、text-embedding-3 与 Dimensions 设置](https://a37836323.github.io/openlux-api-guides/news/n8n-relay-embeddings-openai-vector-store-setup/)
- [Cherry Studio 知识库怎么接中转 API 的嵌入模型：添加 text-embedding-3、选嵌入模型与重建知识库，资料一直处理中怎么办](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-relay-embedding-knowledge-base-setup/)
- [Dify 知识库怎么接中转 API 的嵌入模型：OpenAI-API-compatible 添加 Text Embedding、API Base URL 与 text-embedding-3 设置](https://a37836323.github.io/openlux-api-guides/news/dify-relay-embedding-knowledge-base-setup/)
- [Open WebUI 知识库接中转 API 的嵌入模型：RAG_OPENAI_API_BASE_URL、Key 与 text-embedding-3 设置，报 'NoneType' object has no attribute 'encode' 或 429 怎么办](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-embedding-knowledge-base-rag-setup/)
- [Cherry Studio 智能体接中转 API 选不到模型、提示必须启用 API 网关或一直等待怎么办：Anthropic 端点、运行模式与 API 网关逐项排查](https://a37836323.github.io/openlux-api-guides/news/cherry-studio-agent-relay-anthropic-endpoint-api-gateway-fix/)
- [LobeHub 接中转 API 后没有图片上传按钮、技能用不了或深度思考用不了怎么办：自定义模型能力开关与 MODEL_LIST 扩展配置](https://a37836323.github.io/openlux-api-guides/news/lobehub-relay-vision-skills-model-capabilities-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

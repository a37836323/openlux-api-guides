---
layout: default
title: "VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查"
description: "VS Code 用自带 Key（Custom Endpoint）接中转后，模型选择器看不到模型、只显示 Models，或提示配置辅助模型时，按工作区信任、toolCalling、组织 BYOK 策略、harness、辅助模型设置和地址/Key 逐项排查。"
permalink: /news/vscode-byok-relay-model-not-showing-utility-model-fix/
date: 2026-11-10
---

> 更新日期：2026-11-10 · 一手来源：[Visual Studio Code 官方文档](https://code.visualstudio.com/docs/copilot/customization/language-models)

# VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查

先说结论：VS Code 里用自带 Key（BYOK，Custom Endpoint）接中转后「模型不出现」，先排除 VS Code 自己的几道门槛，再查 Key 和地址：工作区处在受限模式（Restricted Mode）会停用智能体；模型没标 `toolCalling: true` 时，在智能体场景下不会出现在选择器里；Copilot Business / Enterprise 账号需要管理员开启 BYOK 策略；Copilot harness 会话要另开实验设置；没登录 GitHub 时还要自己指定辅助模型（utility models）。按下面顺序一项项排除，最后用 `/v1/models` 和最小配置确认地址与 Key。

本文依据 VS Code 官方文档 [Language models in VS Code](https://code.visualstudio.com/docs/copilot/customization/language-models)（页面更新日期 2026-11-04）和 [Workspace Trust](https://code.visualstudio.com/docs/editing/workspaces/workspace-trust)，适用于用 Language Models 编辑器里 Custom Endpoint 提供方接入的情况。还没配置过的话，先看站内的接入篇《VS Code 怎么接入 OpenAI 兼容 / Claude 中转 API》。

## 先按现象找原因

| 现象 | 最可能的原因 | 先做什么 |
|---|---|---|
| 模型选择器只显示「Models」，没有模型名 | 需要信任工作区，或需要登录 | 打开选择器看提示；受限模式下信任该文件夹 |
| 配置已保存，选择器里还是没有新模型 | 刚加完未刷新；或智能体场景下 `toolCalling` 不是 `true` | 重启 VS Code；确认模型支持工具调用后设 `toolCalling: true` |
| Copilot Business / Enterprise 账号用不了自己的 Key | 组织管理员停用了 BYOK 策略 | 找管理员在 GitHub.com 的 Copilot 策略里开启 |
| 普通聊天能用，切到 Copilot harness 会话看不到 | 该 harness 下 BYOK 要单独打开实验设置 | 打开 `chat.agentHost.byokModels.enabled` |
| Chat 视图提示配置辅助模型，标题、提交信息生成不了 | 没登录 GitHub，内置辅助模型不可用 | 把 `chat.utilityModel`、`chat.utilitySmallModel` 指到你的 BYOK 模型 |
| 能选到模型，但一发消息就报 401 / 404 | Key 或地址不对 | 按第五步用 curl 单独验证 |
| 代码补全（行内建议）还是原来的样子 | 行内补全本来就不走 BYOK | 属正常现象，见最后一节 |

## 第一步：选择器只显示「Models」，先看工作区信任和登录

官方原话是：如果模型选择器显示的是 **Models** 而不是某个模型名，打开它，检查是否需要信任工作区或登录。

工作区信任这一项最容易被忽略。按 Workspace Trust 文档：

- 打开一个陌生文件夹时，VS Code 会以受限模式打开；在信任对话框里选了「No, I don't trust the authors」也会进入受限模式。
- 受限模式会停用或限制智能体（AI agents）、终端、任务、调试、工作区设置和扩展；文档专门写明，在受限模式打开工作区会停用该工作区里的智能体。
- 工作区信任在 VS Code 窗口和 Agents 窗口之间共享，一边不信任，两边的智能体都不会运行。

怎么判断：窗口顶部有受限模式横幅，状态栏有 Restricted Mode 标记。确认这个项目来源可靠后，点横幅里的 Manage 或状态栏标记，在 Workspace Trust 编辑器里信任该文件夹。项目来源不明时，官方建议保持受限模式，这种情况下就不要在这个文件夹里用智能体。

## 第二步：模型加了但选择器里没有

确认工作区已信任后，模型还是不出现，逐项检查 `chatLanguageModels.json`：

1. **先重启 VS Code。** 官方在 Custom Endpoint 步骤里写明：新加的模型没有立刻出现在选择器里时，重启 VS Code。
2. **`toolCalling` 是否为 `true`。** 官方说明：模型要在聊天的智能体场景下可用，必须支持工具调用；不支持工具调用的模型不会出现在选择器里。`toolCalling` 的含义是「该模型支持工具调用时设为 `true`」，所以要先查该模型厂商文档确认它支持工具调用，再设 `true`，不要为了让它显示出来随便打开。
3. **`vendor` 是否为 `customendpoint`。** 只有这个值才走 Custom Endpoint 提供方。旧的 OpenAI Compatible 提供方和 `github.copilot.chat.customOAIModels` 设置已被官方标为弃用，还在用旧写法的建议按 Custom Endpoint 重新添加。
4. **提供方层是否写了 `url`。** 官方说明提供方层的 `url` 是用来自动发现模型的：设置后 VS Code 去该地址查询可用模型列表，代替 `models` 数组。想按自己写的 `models` 逐个配置，就不要在提供方层写 `url`，地址写在每个模型的 `url` 里。
5. **`apiType` 和模型是否匹配。** 官方要求选 API 类型时确认模型支持该类型。在 OpenLux 价格接口 `https://www.openlux.ai/api/pricing_new` 里看模型的 `supported_endpoint_types`：例如 2026-11-10 查询时 `gpt-5.4` 只有 `openai-response`，就要用 `responses`；`claude-sonnet-5-5` 有 `anthropic` 和 `openai`，可以用 `messages` 或 `chat-completions`。
6. **上下文长度。** `maxInputTokens` 与 `maxOutputTokens` 之和不能超过模型的上下文窗口；也可以填 `contextWindow`（输入加输出总量）并省略 `maxInputTokens`，VS Code 用它减去 `maxOutputTokens` 得出输入上限。数值以模型厂商文档为准。

改完保存，再重启一次 VS Code 看是否出现。

## 第三步：确认 harness 和账号类型

VS Code 里同一个模型能不能用，还取决于你用的是哪种会话（官方叫 harness）以及账号类型：

| 情况 | 官方说明 | 处理 |
|---|---|---|
| Local harness 会话 | BYOK 模型不需要登录 GitHub，也不需要 Copilot 订阅 | 正常添加即可 |
| Copilot harness 会话（Chat 视图或 Agents 窗口） | 需要打开 `chat.agentHost.byokModels.enabled`，该功能为实验性质，可能变更或移除 | 在设置里搜索并打开它后再试 |
| Anthropic Claude、OpenAI Codex harness | 在 Language Models 编辑器里加模型，并不会给每个 harness 配好鉴权 | 按对应 harness 自己的要求配置凭据 |
| Copilot Business / Enterprise 账号 | 管理员可以在 GitHub.com 的 Copilot 策略里停用 Bring Your Own Language Model Key in VS Code；开启后才能像个人账号一样添加自己的 Key | 联系组织管理员开启这项策略 |

如果你是 Copilot Business / Enterprise 账号、各项配置都对却始终用不了自己的 Key，优先排查最后一行，这项策略需要组织管理员处理。

## 第四步：提示配置辅助模型（utility models）

VS Code 除了主聊天模型，还在后台用轻量模型做辅助任务，比如生成会话标题、提交信息、PR 描述和意图识别。你在会话里选的模型不管这些任务。官方说明：

- 默认使用 GitHub Copilot 提供的内置辅助模型；**没登录 GitHub 时内置辅助模型不可用**，VS Code 会在 Chat 视图里弹出提示，让你配置辅助模型。
- `chat.utilityModel`：用于标题、摘要、设置搜索、Git 审查等一般辅助任务。
- `chat.utilitySmallModel`：用于提交信息、PR 标题和描述、重命名建议、分支名、意图识别等轻量任务，官方建议选快且便宜的模型。
- `chat.byokUtilityModelDefault`：主模型是 BYOK 模型时，决定辅助任务默认用谁，可选 None、Main Agent Model、GitHub Copilot；`chat.utilityModel` / `chat.utilitySmallModel` 里指定了具体模型时，以它们为准。

处理方法：打开设置编辑器，搜索 `chat.utilityModel` 和 `chat.utilitySmallModel`，各选一个你已添加的 BYOK 模型；或者把 `chat.byokUtilityModelDefault` 设为 Main Agent Model，让辅助任务跟主模型走。设好后，标题生成、提交信息、PR 描述等辅助功能就会改用你指定的模型。

## 第五步：用 /v1/models 和最小配置验证地址与 Key

前面几步都排除了，但一发消息就报错，回到地址和 Key 本身。先在终端单独验证（Key 换成你在 OpenLux 控制台「令牌」页 `https://www.openlux.ai/console/token` 创建的令牌）：

```bash
curl -sS https://api.openlux.ai/v1/models -H "Authorization: Bearer 你的令牌"
```

返回模型列表，说明地址和 Key 都对；返回 401 `Invalid token`，说明 Key 错了或没带上，回控制台重新复制。Key 没问题后，在 Language Models 编辑器里点该提供方旁边的齿轮，重新填 Key 或地址。

地址最容易错在 `/v1`。官方的地址解析规则是：模型 `url` 里已经带了 `/chat/completions`、`/responses` 或 `/messages` 时原样使用；否则 VS Code 自动拼上对应路径，结尾不是 `/v1` 这类版本段时还会先插入 `/v1`。为避免歧义，官方建议写完整地址：

| `apiType` | 模型 `url` 写法 |
|---|---|
| `chat-completions` | `https://api.openlux.ai/v1/chat/completions` |
| `responses` | `https://api.openlux.ai/v1/responses` |
| `messages` | `https://api.openlux.ai/v1/messages` |

如果你手写了 `/v1` 又自己拼了一次，出现 `/v1/v1/...`，OpenLux 会返回 404 `Invalid URL`，按上表改成完整地址即可。鉴权头方面，官方说明 Messages 类型默认发 `x-api-key`，其他类型默认发 `Authorization: Bearer`；OpenLux 的 `/v1/messages` 两种头都接受，一般不用改。确实需要自定义鉴权头时，在模型的 `requestHeaders` 里写 `"Authorization": "Bearer ${apiKey}"`，VS Code 会在请求时替换成已保存的 Key，并且不再另发默认鉴权头。

最小验证：先只留一个模型，`id` 用价格接口里的准确 ID，`apiKey` 用官方建议的输入变量写法（如 `${input:openluxKey}`），不要把明文 Key 写进文件。这个模型能在选择器里选中并正常回复后，再逐个加其他模型。

## 哪些功能本来就不走自带 Key

官方写明 BYOK 只作用于聊天和辅助任务。以下功能仍需要 GitHub 账号（部分需要 Copilot 订阅），不会改用你的中转模型：

- 行内建议（代码补全）
- 语义搜索
- 依赖 embeddings 的功能

所以「接了中转、代码补全还是老样子」或「没登录 GitHub 时补全不可用」都是预期行为，不是配置错误。

## 参考资料

- VS Code 官方：[Language models in VS Code](https://code.visualstudio.com/docs/copilot/customization/language-models)（BYOK、Custom Endpoint 配置参考、地址解析、辅助模型、常见问题）
- VS Code 官方：[Workspace Trust](https://code.visualstudio.com/docs/editing/workspaces/workspace-trust)（受限模式与智能体）

按上面顺序检查后，模型能在选择器里选中并正常回复，就说明接通了。还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=vscode-byok-relay-model-not-showing-utility-model-fix&utm_content=footer)。价格以官网价格页为准。

## 同专题文章

- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)
- [Continue 接中转 API 报 fetch failed、证书错误或 401 怎么办：caBundlePath、代理与 secrets 读不到 Key 逐项排查](https://a37836323.github.io/openlux-api-guides/news/continue-relay-fetch-failed-certificate-401-fix/)
- [Cline 接中转 API 连不上、超时或报证书错误怎么办：VS Code、CLI、JetBrains 的代理与 CA 证书设置](https://a37836323.github.io/openlux-api-guides/news/cline-relay-connection-timeout-proxy-certificate-fix/)
- [Codex CLI 接中转后流式卡住不结束、第二轮或工具调用失败怎么办：Responses 兼容、response.completed 与模型名逐项排查](https://a37836323.github.io/openlux-api-guides/news/codex-cli-relay-stream-stall-tool-call-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办"
description: "Cline CLI（终端版）接入 OpenAI 兼容中转 API：用 cline auth --provider openai-compatible --apikey --modelid --baseurl 一条命令配置，Base URL 带 /v1，配置保存位置、验证方法、-p 与 -P 的区别，以及 invalid provider、base URL is only supported for OpenAI and OpenAI-compatible providers、requires a TTY 等报错的处理。"
permalink: /news/cline-cli-relay-api-auth-baseurl-setup/
date: 2026-11-13
---

> 更新日期：2026-11-13 · 一手来源：[Cline 官方文档](https://docs.cline.bot/cli/cli-reference)

# Cline CLI 怎么接入 OpenAI 兼容中转 API：cline auth --baseurl、Key 与模型设置，报 invalid provider 或 base URL is only supported 怎么办

在终端里用 Cline CLI 接 OpenAI 兼容中转，一条命令就能配好：`cline auth --provider openai-compatible --apikey <Key> --modelid <模型 ID> --baseurl https://api.openlux.ai/v1`。Base URL 要带 `/v1`；`--baseurl` 只能配合 `openai-compatible`（或 `openai-native`）使用，配在 `anthropic` 上会直接报 `base URL is only supported for OpenAI and OpenAI-compatible providers`。

本文适用于 `npm install -g cline` 安装的 Cline CLI（终端版）。VS Code 等编辑器里的 Cline 扩展请看本站的《Cline 怎么接入 OpenAI 兼容 / Claude 中转 API》。命令、参数和报错原文都出自 Cline 官方 [CLI Reference](https://docs.cline.bot/cli/cli-reference) 和官方仓库的 [auth 命令源码](https://github.com/cline/cline/blob/main/apps/cli/src/commands/auth.ts)。本文没有用真实 Key 跑通 Cline CLI，命令行为以你本机 `cline auth --help` 的输出为准。

## 开始前准备

| 项目 | 要求或填写内容 | 依据 |
|---|---|---|
| Node.js | 20 及以上（官方推荐 22） | Cline 官方安装文档 |
| 安装 CLI | `npm install -g cline` | Cline 官方安装文档 |
| 服务商 ID | `openai-compatible` | 官方源码：OpenAI 兼容服务商的内置 ID |
| Base URL | `https://api.openlux.ai/v1`（带 `/v1`） | Cline 官方 SDK 文档示例的 `baseUrl` 写到 `/v1` |
| API Key | 在 OpenLux 控制台「令牌」页创建：`https://www.openlux.ai/console/token` | — |
| 模型 ID | 价格接口 `https://www.openlux.ai/api/pricing_new` 里支持 `openai` 端点的模型，例如 `gpt-5.6-sol`、`claude-sonnet-5-5` | — |

模型 ID 要和价格接口、`/v1/models` 返回的写法完全一致，不要自己改大小写或加前缀。

## 第一步：先用 /v1/models 验证地址和 Key

先在终端确认地址和 Key 没问题，再配 Cline，后面出错时就能分清是 Cline 的问题还是 Key 的问题。把 Key 放进环境变量，不要直接写在命令里，免得留在 shell 历史中：

```bash
export OPENLUX_API_KEY="你的 Key"
curl https://api.openlux.ai/v1/models \
  -H "Authorization: Bearer $OPENLUX_API_KEY"
```

- 返回模型列表：地址和 Key 都对，记下要用的模型 ID；
- 返回 401 `Invalid token`：Key 填错或没带上，回「令牌」页重新复制。

## 第二步：用 cline auth 一条命令配置

官方 CLI Reference 写明，`cline auth` 不带参数会打开交互式设置；想跳过提示，就直接传服务商、Key 和模型：

```bash
cline auth --provider openai-compatible \
  --apikey "$OPENLUX_API_KEY" \
  --modelid gpt-5.6-sol \
  --baseurl https://api.openlux.ai/v1
```

短参数写法是 `cline auth -p openai-compatible -k "$OPENLUX_API_KEY" -m gpt-5.6-sol -b https://api.openlux.ai/v1`。按官方源码，配置成功会输出 `Provider configured: openai-compatible (gpt-5.6-sol)`。

几点要注意：

- 服务商 ID 写 `openai` 也行。源码把 `openai` 当作 `openai-compatible` 的别名处理，官方 OpenAI 服务商的 ID 是 `openai-native`。
- 想用 Claude 模型时，同样选 `openai-compatible`，模型 ID 填 `claude-sonnet-5-5` 这类同时支持 `openai` 端点的模型。不要用 `anthropic` 服务商加 `--baseurl`，原因见下面的报错表。
- 只想在当前机器上交互式配置的话，直接运行 `cline auth`，流程和编辑器扩展里一样（官方 Authorization 文档原话：Runs the same auth flow as IDE setup）。

## 第三步：配置存在哪里、怎么确认生效

官方 Config 文档说明，服务商的 Key 和配置保存在 `~/.cline/data/settings/providers.json`。`~/.cline/` 是全局配置，官方说它在 IDE、CLI、SDK 之间共用。如果用 `--config <目录>` 或环境变量 `CLINE_DIR` 换了配置目录，就要到那个目录下找。这个文件里有 Key，不要提交到仓库，也不要发到聊天里。

确认生效的办法：

1. 运行 `cline config` 打开配置界面，查看当前配置。
2. 跑一个最小任务，只打印最终回答：

```bash
cline --json "只回复 OK" | jq -r 'select(.type == "run_result") | .text'
```

官方说明 `--json` 每行输出一个 JSON 对象，`run_result` 一行里带 `model` 和最终的 `text`。能打印出回答，说明请求已经走通。出错时，错误会以 `{"type":"error","message":...}` 的形式输出到 stderr。

不带 `-P` 直接运行 `cline` 时，按源码会先用最近一次配置的服务商，都没有才退回默认的 `cline`。所以 `cline auth` 配好以后，平时直接 `cline "任务"` 就行。

## 运行时临时换模型或服务商

| 需求 | 写法 | 说明 |
|---|---|---|
| 这次换个模型 | `cline -m claude-sonnet-5-5 "任务"` | `-m` 只对本次会话生效 |
| 这次指定服务商 | `cline -P openai-compatible "任务"` | 注意是**大写** `-P` |
| 这次临时用另一个 Key | `cline -P openai-compatible -k "$OPENLUX_API_KEY" "任务"` | 官方说明：`-k` 也会保存为该服务商的 Key |
| 设置推理强度 | `cline --thinking high "任务"` | 可选 `none`、`low`、`medium`、`high`、`xhigh` |

最容易写错的是 `-p`：在 `cline auth` 里，`-p` 表示服务商；在 `cline` 主命令里，`-p` 表示 Plan 模式（`--plan`），指定服务商要用大写 `-P`。

## 常见报错和处理

前六条报错原文来自官方 `auth` 命令源码，后面几条按 OpenLux 接口的返回写：

| 报错原文 | 原因 | 处理 |
|---|---|---|
| `invalid provider "xxx"` | 服务商 ID 不在 CLI 的服务商列表里，常见于拼错 | 改成 `openai-compatible` |
| `base URL is only supported for OpenAI and OpenAI-compatible providers` | 在 `anthropic` 等服务商上传了 `--baseurl` | 改用 `--provider openai-compatible`，模型 ID 填支持 `openai` 端点的模型 |
| `auth quick setup requires --provider <id> when using --apikey/--modelid/--baseurl/--azure-api-version` | 传了 Key、模型或地址，却没写服务商 | 补上 `--provider openai-compatible` |
| `auth quick setup requires --apikey <key>` 或 `requires --modelid <id>` | 一条命令配置时漏了 Key 或模型，或者环境变量是空的 | 先 `echo ${OPENLUX_API_KEY:+已设置}` 确认变量不为空，再补齐参数 |
| `interactive auth setup requires a TTY` | 在 CI、管道或脚本里运行了不带参数的 `cline auth` | 改用上面那条带 `--provider/--apikey/--modelid` 的命令 |
| `provider "xxx" requires API key setup` | 只写了服务商，没带 Key 和模型 | 按提示补上 `--apikey` 和 `--modelid` |
| 401 `Invalid token` | Key 错了、已删除，或者 `-k` 把旧 Key 覆盖了上去 | 用第一步的 curl 验证 Key，再重新运行 `cline auth` |
| 404 `Invalid URL (POST /v1/v1/chat/completions)` | Base URL 多写了一层 `/v1` | Base URL 改成 `https://api.openlux.ai/v1` |
| 返回的是网页 HTML，不是接口 JSON | Base URL 少了 `/v1`，请求落到了网站页面上（2026-11-13 用不带 Key 的请求核对过） | 同上，补上 `/v1` |
| 提示模型不存在 | 模型 ID 不在售，或拼写和接口返回的不一致 | 对照 `/v1/models` 的返回重新填 `--modelid` |

如果连不上、超时或报证书错误，问题一般出在网络上，不在 `cline auth`。按本站《Cline 接中转 API 连不上、超时或报证书错误怎么办》配置代理和 CA 证书。CLI 日志默认在 `~/.cline/data/logs/cline.log`，用 `cline doctor log` 可以直接打开。

## 求助时带上什么

- `cline version` 的输出；
- 你运行的 `cline auth` 命令（把 Key 换成 `***`）；
- 报错原文，或者 `--json` 模式下 stderr 里那行 `{"type":"error",...}`；
- 第一步 curl `/v1/models` 的结果（是否 200）。

## 参考资料

- Cline 文档：[CLI Reference](https://docs.cline.bot/cli/cli-reference)（`auth` 的 `-p/-k/-m/-b` 参数、全局 `-P/-k/-m/--thinking`、`--json` 输出、配置文件位置）
- Cline 文档：[Installing Cline](https://docs.cline.bot/getting-started/installing-cline)（Node.js 版本与 `npm install -g cline`）
- Cline 文档：[Config](https://docs.cline.bot/getting-started/config)（`~/.cline/data/settings/providers.json`）
- Cline 文档：[Model Providers](https://docs.cline.bot/sdk/model-providers)（OpenAI 兼容服务商用 `openai-compatible`，`baseUrl` 写到 `/v1`）
- Cline 源码：[apps/cli/src/commands/auth.ts](https://github.com/cline/cline/blob/main/apps/cli/src/commands/auth.ts)（报错原文与参数校验）

还没有 Key 的话，可以先[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cline-cli-relay-api-auth-baseurl-setup&utm_content=footer)，在「令牌」页创建 Key 后，按上面的命令配置 Cline CLI。

## 同专题文章

- [n8n AI Agent 接中转 API 报 400 Invalid value for 'content'、No prompt specified 或 No sessionId 怎么办：Prompt、Chat Model 与 Simple Memory 逐项排查](https://a37836323.github.io/openlux-api-guides/news/n8n-ai-agent-relay-prompt-content-null-session-fix/)
- [Zed 接中转 API 用 DeepSeek 思考模型时续轮报 400、看不到思考过程或图片发不出去怎么办：interleaved_reasoning、reasoning_effort 与 capabilities 逐项设置](https://a37836323.github.io/openlux-api-guides/news/zed-relay-deepseek-reasoning-content-400-capabilities-fix/)
- [Chatbox 接中转 API 后图片发不出去、模型说看不到图片或知识库用不了怎么办：模型能力勾选、OCR、文档解析器与嵌入模型逐项排查](https://a37836323.github.io/openlux-api-guides/news/chatbox-relay-image-file-vision-knowledge-base-fix/)
- [VS Code 用自带 Key 接中转后模型选择器看不到模型、只显示 Models 或提示配置辅助模型怎么办：工作区信任、工具调用、组织策略与 harness 逐项排查](https://a37836323.github.io/openlux-api-guides/news/vscode-byok-relay-model-not-showing-utility-model-fix/)
- [Dify 接中转 API 后 LLM 节点报 InvokeConnectionError、InvokeRateLimitError 或超时怎么办：错误类型、重试与失败分支逐项排查](https://a37836323.github.io/openlux-api-guides/news/dify-relay-llm-node-invoke-error-retry-fix/)
- [Open WebUI 接中转 API 报 Unexpected token 'd'、回复乱码、Model not found 或证书错误怎么办：反向代理、DNS 与 CA 证书逐项排查](https://a37836323.github.io/openlux-api-guides/news/open-webui-relay-stream-unexpected-token-dns-certificate-fix/)

[查看「客户端接入：Cline、Codex CLI、Cherry Studio、n8n 等」全部文章](https://a37836323.github.io/openlux-api-guides/topics/clients/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

---
layout: default
title: "Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置"
description: "Claude Code 接入 Claude 中转 API 的配置步骤：ANTHROPIC_BASE_URL 不带 /v1、ANTHROPIC_AUTH_TOKEN 与 ANTHROPIC_API_KEY 怎么选、settings.json 写法、/model 选模型、/status 确认，以及 401、模型不存在、一直要求登录等报错处理。"
permalink: /news/claude-code-relay-api-base-url-setup/
date: 2026-10-26
---

> 更新日期：2026-10-26 · 一手来源：[Claude Code 官方文档](https://code.claude.com/docs/en/llm-gateway-connect)

# Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置

先说结论：Claude Code 走中转，只需要两个环境变量。`ANTHROPIC_BASE_URL` 填中转地址，`ANTHROPIC_AUTH_TOKEN`（或 `ANTHROPIC_API_KEY`）填令牌，然后用 `/model` 选一个中转在售的 Claude 模型 ID。接 OpenLux 时，Base URL 填 `https://api.openlux.ai`，**不要带 `/v1`**，因为 Claude Code 会自己在后面拼 `/v1/messages`。

本文的配置项名称和排错表都来自 Claude Code 官方文档 [Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect)。中转在官方文档里叫「LLM gateway」，适用于 Claude Code 命令行和 VS Code 扩展，桌面应用另有入口，见后文。有两点要先知道：

- 官方 [LLM gateway 说明](https://code.claude.com/docs/en/llm-gateway) 写明不支持通过任何网关让 Claude Code 调用非 Claude 模型，所以这里只讲 Claude 模型。
- 设置了网关凭据后，请求用的是这个凭据，而不是你的 claude.ai 订阅登录，订阅的用量限制不适用于这些请求。只设 `ANTHROPIC_BASE_URL`、不设凭据时，生效的还是 claude.ai 登录。

## 需要准备的三项配置

| 配置项 | 填什么 | 说明 |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `https://api.openlux.ai` | Anthropic Messages 协议，不带 `/v1`，实际请求路径是 `/v1/messages` |
| `ANTHROPIC_AUTH_TOKEN` | OpenLux 令牌 | 以 `Authorization: Bearer` 请求头发送；没把握用哪个变量时，官方建议先用它 |
| `ANTHROPIC_API_KEY` | OpenLux 令牌 | 以 `x-api-key` 请求头发送；前一个变量返回 401 时换成它 |
| 模型 ID | 如 `claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5` | 以 OpenLux 价格页在售列表为准，名字要完全一致 |

令牌在 OpenLux 控制台的「令牌」页创建：`https://www.openlux.ai/console/token`。价格以官网价格页为准，本文不写具体数字。

## 第一步：先用 curl 验证地址和令牌

官方建议在打开 Claude Code 之前，先用一条只要 1 个 token 的请求直接测网关。这样如果失败，可以确定是地址或令牌的问题，和 Claude Code 的配置无关。先在终端导出变量（把令牌换成你自己的）：

```bash
export ANTHROPIC_BASE_URL=https://api.openlux.ai
export ANTHROPIC_AUTH_TOKEN=你的OpenLux令牌
```

再发验证请求（照抄官方命令，其中的 `claude-sonnet-4-6` 也在 OpenLux 在售列表里）：

```bash
curl -sS -w '\n%{http_code}\n' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-4-6", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

结果怎么判断：

- 返回以 `{"id":"msg_` 开头、带 `"content":[...]` 的 JSON：地址和令牌都正常。
- 报模型不存在：说明地址和令牌已经通过鉴权，只是模型名不对，换一个在售模型 ID 就行。
- 返回 `401`：令牌被拒。如果是猜的变量，按官方说法换成 `x-api-key: $ANTHROPIC_API_KEY` 请求头再试，同时检查令牌有没有复制完整、有没有被删除。

还可以请求 OpenAI 兼容的模型列表 `https://api.openlux.ai/v1/models`，能列出模型也能说明地址和令牌是对的。

## 第二步：写进 settings.json 长期生效

`export` 只对当前终端有效，从程序坞或开始菜单启动的编辑器看不到；只在 shell 里导出时，后台智能体也不一定能读到。官方建议验证通过后，把变量写进 Claude Code 设置文件的 `env` 块：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openlux.ai",
    "ANTHROPIC_AUTH_TOKEN": "你的OpenLux令牌"
  }
}
```

放在哪个文件：

- `~/.claude/settings.json`：对所有项目生效，Windows 上是 `%USERPROFILE%\.claude\settings.json`。
- `.claude/settings.local.json`：只对一个项目生效。手动创建时，先把它加进 gitignore。
- **不要**把令牌写进项目的 `.claude/settings.json`，这个文件会提交到仓库，所有克隆的人都看得到。

shell 和设置文件设了同一个变量时，以设置文件为准。

## 第三步：选模型

官方文档特别说明：`ANTHROPIC_BASE_URL` 只改变请求发往哪里，不决定由哪个模型回答。模型按下面的优先级生效，从高到低：

1. 会话中输入 `/model claude-opus-5-5` 立即切换；`/model` 会把选择写进用户设置，作为新会话的默认值。
2. 启动时用 `claude --model claude-sonnet-5-5`，只对这次启动的会话有效。
3. 环境变量 `ANTHROPIC_MODEL`，同样只对这次启动有效。
4. 设置文件里的 `model` 字段。

如果想让 `opus`、`sonnet`、`haiku` 这些别名指向中转上的具体版本，可以设置 `ANTHROPIC_DEFAULT_OPUS_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL`。用 `--model`、`ANTHROPIC_MODEL` 或 `model` 字段指定的模型，Claude Code 不会提前检查，名字写错要到第一次请求才报 `There's an issue with the selected model`。详见官方 [模型配置文档](https://code.claude.com/docs/en/model-config)。

## 第四步：在 Claude Code 里确认生效

在已经导出变量的同一个终端里运行 `claude`，发一条消息，再输入 `/status`：

- `Anthropic base URL` 这一行显示 `https://api.openlux.ai`：请求已经走中转。没有这一行，说明变量没传进会话。
- `Auth token` 或 `API key` 这一行写着你设置的变量名：生效的是令牌，而不是之前保存的 claude.ai 登录。

和旧登录的关系：`ANTHROPIC_AUTH_TOKEN` 设置后立即优先于已保存的 claude.ai 登录；`ANTHROPIC_API_KEY` 在交互模式下要先确认一次才生效。启动时提示两个凭据冲突、`auth may not work as expected`，可以运行 `/logout` 清掉旧登录，只留中转令牌。

## VS Code 扩展和桌面应用

**VS Code 扩展**：用「Preferences: Open User Settings (JSON)」打开 VS Code 自己的用户设置，在 `claudeCode.environmentVariables` 里写变量。官方说明扩展启动前会先从这里检查凭据，只写在 `~/.claude/settings.json` 里的值过不了扩展自己的登录检查。

```json
{
  "claudeCode.environmentVariables": [
    { "name": "ANTHROPIC_BASE_URL", "value": "https://api.openlux.ai" },
    { "name": "ANTHROPIC_AUTH_TOKEN", "value": "你的OpenLux令牌" }
  ]
}
```

**桌面应用**：不读 `ANTHROPIC_BASE_URL` 和 `settings.json`，要在 Help → Troubleshooting → Enable Developer Mode 后，从 Developer → Configure Third-Party Inference 填网关地址。

另外，设置网关凭据后，Remote Control 和语音听写不可用，这是官方说明的限制，不是中转的问题。

## 常见报错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `401`，提示令牌无效 | 令牌错、已删除，或放进了中转不读取的请求头 | 在 `ANTHROPIC_AUTH_TOKEN` 和 `ANTHROPIC_API_KEY` 之间切换；令牌失效就在控制台重新创建 |
| 请求路径不对导致失败（如 404） | Base URL 多写了 `/v1`，Claude Code 再拼 `/v1/messages` 后变成 `/v1/v1/messages` | Base URL 只填 `https://api.openlux.ai` |
| `There's an issue with the selected model` 或模型不存在 | 模型 ID 拼错，或不在在售列表 | 用价格页上的完整 ID，如 `claude-sonnet-5-5` |
| 一直要求登录，但 curl 测试正常 | Claude Code 没读到凭据；项目设置文件里的 `env` 要在首次向导和信任提示之后才生效 | 把 `ANTHROPIC_AUTH_TOKEN` 写在 shell 导出或 `~/.claude/settings.json` |
| 设了 `ANTHROPIC_API_KEY` 却没生效，也不提示 | 之前拒绝过这个 Key | 在 `/config` 里打开 `Use custom API key` |
| `Connection refused` 或 `ENOTFOUND` | 地址写错，或网络、代理拦截 | 先跑第一步的 curl，确认地址和网络 |
| `API returned an empty or malformed response (HTTP 200)` | 返回的不是 API 响应，常见是 HTML 错误页或登录页 | 用第一步的 curl 看返回是不是 JSON；Base URL 要填 API 地址，不是控制台网页地址 |
| `400`，提到 `context_management` 或 `Extra inputs are not permitted` | 上游不接受 Claude Code 发送的预发布字段 | 设置 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`，可去掉大部分预发布字段（官方说明少数不受它控制） |

## 开始使用

按上面四步走完，`/status` 显示中转地址和令牌、发消息能正常回复，就说明接入成功。还没有令牌的话，可以先 [注册 OpenLux 并创建令牌](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-api-base-url-setup&utm_content=footer)。

---
layout: default
title: "Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查"
description: "Claude Code 走中转后 /model 列表只有 opus、sonnet、haiku，或切换模型报 Model not found、There's an issue with the selected model：按官方文档开启网关模型发现、用 ANTHROPIC_DEFAULT_*_MODEL 和 ANTHROPIC_CUSTOM_MODEL_OPTION 手动指定，并逐项排查。"
permalink: /news/claude-code-relay-model-picker-missing-models-fix/
date: 2026-11-03
---

> 更新日期：2026-11-03 · 一手来源：[Claude Code Docs](https://code.claude.com/docs/en/llm-gateway-connect)

# Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查

先说结论：Claude Code 通过 `ANTHROPIC_BASE_URL` 走中转时，`/model` 列表默认只显示**内置**的模型项（如 `opus`、`sonnet`、`haiku` 这些别名），不会自动去中转拉取模型列表。想让中转上的模型出现在列表里，有两种办法：设置 `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1` 开启网关模型发现，或者用 `ANTHROPIC_DEFAULT_OPUS_MODEL` 这类变量、`ANTHROPIC_CUSTOM_MODEL_OPTION` 自己把模型 ID 写进去。切换时报 `Model ... not found` 或 `There's an issue with the selected model`，多数是模型 ID 不在中转的在售列表里。

本文的变量名、版本号和报错原文都来自 Claude Code 官方文档：[Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect)（排错表里的「Models missing from the /model picker」一行）、[Gateway compatibility guide 的 Model discovery 一节](https://code.claude.com/docs/en/llm-gateway-protocol#model-discovery)、[Model configuration](https://code.claude.com/docs/en/model-config) 和 [Error reference](https://code.claude.com/docs/en/errors)。地址和令牌还没配好的，先看 [Claude Code 接入中转的配置篇](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)；本文假设 curl 测试已经能通、`/status` 里能看到中转地址。

## 先对照现象找原因

| 现象 | 原因 | 处理 |
|---|---|---|
| `/model` 只有 `opus`、`sonnet`、`haiku` 等内置项，没有中转的其他模型 | 网关模型发现默认关闭，中转的模型名不在内置列表里 | 开启 `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1`，或用环境变量手动加 |
| 开了发现，`claude-sonnet-5-5` 这类模型还是没有单独一行 | 它和内置别名当前指向的是同一个模型，官方规定只显示别名那一行 | 属正常现象，选 `sonnet` 那一行即可；用 `/status` 确认实际模型 |
| 开了发现，列表没变化 | 发现请求超时、被重定向、没带上凭据，或返回的 `id` 里不含 `claude`/`anthropic` | 用 `claude --debug` 看 `[gatewayDiscovery]` 日志，见下文 |
| `/model <名字>` 报 `Model '...' not found` | Claude Code 用一个最小请求向中转确认这个名字，中转回答没有这个模型 | 对照中转在售列表改正模型 ID |
| 第一次发消息报 `There's an issue with the selected model` | 用 `--model`、`ANTHROPIC_MODEL` 或 `model` 设置指定的名字写错了，这几种方式不会提前检查 | 改正 ID，或删掉残留的旧值 |
| 切换时报 `API error: 429 ... · model not changed` | 确认模型的请求被限流或遇到服务端错误，会话保留原模型 | 稍等后重新切换 |
| 启动时提示 `isn't recognized · context assumed to be 200k tokens` | 当前 Claude Code 版本不认识这个模型 ID，按 200K 上下文处理 | 先 `claude update`；中转自定义别名用 `modelOverrides` 映射 |

## 为什么默认看不到中转的模型

官方文档对 `/model` 列表的说明是：内置列表里是别名和 Claude Code 已知的模型，网关上额外的模型名要靠「网关模型发现」或手动配置才会加进来。发现功能**默认关闭**，官方给的理由是：网关背后是一把共享 Key 时，默认打开会让这把 Key 能访问的所有模型都出现在每个用户的列表里。

别名本身会随版本更新。官方版本表写明，在 Anthropic API 上：v2.1.280 起 `opus` 指向 Opus 5.5，v2.1.284 起 `sonnet` 指向 Sonnet 5.5，v2.1.293 起 `haiku` 指向 Haiku 5.5。走 `ANTHROPIC_BASE_URL` 时，Claude Code 把中转当成 Claude API 对待、发送 Anthropic 的模型 ID（如 `claude-opus-5-5`）。版本表列的是 Anthropic API 上的指向，走中转时实际用的是哪个模型，以会话里 `/status` 显示的为准；想固定版本就用下文方法二。

接 OpenLux 时，Claude 模型 ID 以价格接口 `https://www.openlux.ai/api/pricing_new` 为准，例如 `claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5`、`claude-fable-5-1`、`claude-opus-4-8`；其中 `claude-opus-5-5`、`claude-sonnet-5-5` 与 Claude Code 文档示例里的写法相同。要用的模型必须支持 `anthropic` 端点（价格接口的 `supported_endpoint_types` 字段），上面这些 Claude 模型都列了 `anthropic`。

## 方法一：开启网关模型发现

在启动 Claude Code 的 shell 里导出，或写进 `~/.claude/settings.json` 的 `env` 块：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.openlux.ai",
    "ANTHROPIC_AUTH_TOKEN": "你的OpenLux令牌",
    "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY": "1"
  }
}
```

开启后，Claude Code 每次启动会向中转发 `GET /v1/models?limit=1000`，把返回的模型加进 `/model` 列表。官方写明的几条规则，排查时逐条对照：

- **只保留含 `claude` 或 `anthropic` 的 ID**（不区分大小写，出现在任意位置即可）。GPT、Gemini 等模型不会出现，这和官方「不支持通过网关让 Claude Code 调用非 Claude 模型」的说明一致。v2.1.223 之前要求 ID 以这两个词**开头**。
- **默认 3 秒超时，任何重定向都算失败**，连 `http` 跳 `https` 也算。超时或重定向时静默失败，不报错。v2.1.269 起可以用 `CLAUDE_CODE_GATEWAY_MODEL_DISCOVERY_TIMEOUT_MS` 调大超时。所以 Base URL 要直接写 `https://` 开头的地址。
- **必须有凭据**：请求会带上 `Authorization`（来自 `ANTHROPIC_AUTH_TOKEN` 或 `apiKeyHelper`）和 `x-api-key`（来自 `ANTHROPIC_API_KEY`），两个头都带需要 v2.1.248 或更高版本，更早的版本设了 `ANTHROPIC_AUTH_TOKEN` 时只发 `Authorization`，否则只发 `x-api-key`。凭据只放在 `ANTHROPIC_CUSTOM_HEADERS` 里时，发现会被跳过。
- **设置了任何 `CLAUDE_CODE_USE_*` 提供方变量时不运行**，即使同时设了 `ANTHROPIC_BASE_URL`。
- **结果会缓存**到 `~/.claude/cache/gateway-models.json`（Windows 是 `%USERPROFILE%\.claude\cache\gateway-models.json`），每次启动刷新；请求失败时退回上次缓存或内置列表。
- 管理员设了 `availableModels` 时，只加允许的模型；`modelPicker` 设了 `replaceBuiltInOptions` 时，发现的模型会被隐藏。

OpenLux 的 OpenAI 兼容接口用 `Authorization: Bearer` 鉴权，所以开启发现时建议把令牌放在 `ANTHROPIC_AUTH_TOKEN`。可以先用 curl 自己看一下 `/v1/models` 返回什么：

```bash
curl -sS "https://api.openlux.ai/v1/models" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN"
```

官方要求的格式是返回里有 `data` 数组，每项至少有 `id`，可选 `display_name` 和 `description`。能看到 `data` 里有 `"id": "claude-..."` 这样的条目，说明发现功能有东西可读；返回 `401` 就是令牌不对，先回去修凭据。

**怎么确认发现跑了**：用 `claude --debug` 启动，到 `~/.claude/debug/<session-id>.txt` 里找 `[gatewayDiscovery]` 开头的行。第一次成功会记录缓存了多少个模型；`404`、超时、重定向也会记在这里；没有可用凭据时会写 `[gatewayDiscovery] skipped`。

## 方法二：用环境变量手动指定模型

不想开发现，或者发现返回的列表里没有你要的那个，可以手动配置。官方给了三类做法：

**1. 让别名指向固定版本。** 设置 `ANTHROPIC_DEFAULT_OPUS_MODEL`、`ANTHROPIC_DEFAULT_SONNET_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL`（还有 `ANTHROPIC_DEFAULT_FABLE_MODEL`），值必须是完整的模型 ID：

```bash
export ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-5-5
export ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-5-5
export ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-5-5
```

设了之后，`/model` 列表里这个系列只显示一行你指定的模型，替换掉该系列的内置项。`ANTHROPIC_DEFAULT_HAIKU_MODEL` 还决定后台任务（如会话标题）用哪个模型。想改显示名和说明，可以加 `_NAME`、`_DESCRIPTION` 后缀的变量，例如 `ANTHROPIC_DEFAULT_OPUS_MODEL_NAME`；官方写明这两个后缀在 `ANTHROPIC_BASE_URL` 指向网关时也生效。注意 `_SUPPORTED_CAPABILITIES` 后缀**只在** Bedrock、Agent Platform、Foundry 这类提供方配置下生效，走 `ANTHROPIC_BASE_URL` 时设了也没用。

**2. 额外加一行自定义模型。** `ANTHROPIC_CUSTOM_MODEL_OPTION` 在列表末尾加**一个**条目，不替换内置别名：

```bash
export ANTHROPIC_CUSTOM_MODEL_OPTION=claude-opus-4-8
export ANTHROPIC_CUSTOM_MODEL_OPTION_NAME="Opus 4.8 via OpenLux"
```

官方说明 Claude Code 对这个变量里的 ID **不做校验**，填什么就发什么，所以要自己对照在售列表写准确。环境变量在启动时读取，改完要重启 `claude`。设了 `availableModels` 时，要把这个 ID 也加进允许列表，否则会被过滤掉。要列多个模型，官方建议改用 `modelPicker` 设置。

**3. 直接指定一次。** 会话里输入 `/model claude-opus-4-8`，或启动时用 `claude --model claude-opus-4-8`、设置 `ANTHROPIC_MODEL`。`/model <名字>` 会写进用户设置作为以后新会话的默认值；`--model` 和 `ANTHROPIC_MODEL` 只对这次启动有效。

## 切换模型时的报错怎么处理

**`Model 'xxx' not found`**：输入的名字不是别名时，Claude Code 会发一个最小请求向中转确认，这条报错通常就是中转的回答。处理：对照价格接口里的在售 ID 重新输入，注意大小写、点号和连字符，例如是 `claude-sonnet-5-5`，不是 `claude-sonnet-5.5` 或展示名。名字里带空格也会报这一条。

**`There's an issue with the selected model (...). It may not exist or you may not have access to it.`**：官方说明这表示模型名不被识别或无权访问。用 `--model`、`ANTHROPIC_MODEL`、`model` 设置指定的模型不会提前检查，写错了要到第一次请求才报这个错。处理：

- 交互模式下运行 `/model` 重新选；`-p` 非交互模式下改正 `--model` 或 `ANTHROPIC_MODEL`。
- 改了还是回到错误的模型，说明别处还留着旧值。按优先级逐个检查：会话内 `/model`、启动参数 `--model`、环境变量 `ANTHROPIC_MODEL`、设置文件的 `model` 字段、`ANTHROPIC_DEFAULT_MODEL`。
- 官方特别提到：走网关时**所有模型**都报这个错，可以设置 `ENABLE_TOOL_SEARCH=false` 再试，排除中转不接受工具搜索相关字段的情况。

**`API error: 429 ... · model not changed`**：确认模型的请求被拒了，原因是限流或服务端错误这类没有单独条目的情况，会话继续用原来的模型。按中间那段服务端说明处理，稍等后重新切换。

**启动提示模型 `isn't recognized`、上下文按 200K 处理**：当前 Claude Code 版本不认识这个 ID。如果是比你的版本更新的模型，运行 `claude update`；如果是中转自定义的别名，官方建议在设置文件里用 `modelOverrides` 把 Anthropic 模型 ID 映射到这个别名，Claude Code 就会按对应模型处理上下文窗口和功能。用价格接口里的标准 ID 仍出现这个提示，先确认 Claude Code 是不是版本较旧。

## 改完怎么验证

1. 在设置好变量的同一个终端运行 `claude`（改了环境变量要重启会话）。
2. 输入 `/model`：开了发现的，应看到中转返回的 Claude 模型（和别名指向同一模型的会并入别名那一行），没有说明的条目显示 `From gateway`；手动配置的，应看到你设的那一行。
3. 选中一个模型发一条消息，能正常回复说明模型 ID 正确。
4. 输入 `/status`：确认 `Anthropic base URL` 是中转地址，当前模型是你选的那个。
5. 发现没生效时，用 `claude --debug` 重启，查 `~/.claude/debug/` 下日志里的 `[gatewayDiscovery]` 行。

## 开始使用

`/model` 能看到并切换到中转上的 Claude 模型、发消息正常回复，就说明模型配置没问题。模型价格以官网价格页为准。还没有令牌的话，可以先 [注册 OpenLux 并在「令牌」页创建 Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-code-relay-model-picker-missing-models-fix&utm_content=footer)。

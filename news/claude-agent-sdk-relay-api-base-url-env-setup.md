---
layout: default
title: "Claude Agent SDK 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、env 选项与模型设置（Python / TypeScript）"
description: "Claude Agent SDK（Python / TypeScript）接 Claude 中转 API：没有专门的网关参数，给它启动的 Claude Code 进程设 ANTHROPIC_BASE_URL=https://api.openlux.ai（不带 /v1）和 ANTHROPIC_AUTH_TOKEN，model 填完整模型 ID；TypeScript 的 options.env 会整个替换环境变量要展开 process.env；附 settings.json 覆盖、401、404、模型不存在、找不到 CLI 的排查。"
permalink: /news/claude-agent-sdk-relay-api-base-url-env-setup/
date: 2026-11-24
---

> 更新日期：2026-11-24 · 一手来源：[Claude Code 官方文档](https://code.claude.com/docs/en/llm-gateway-connect)

# Claude Agent SDK 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、env 选项与模型设置（Python / TypeScript）

结论先说：Claude Agent SDK 没有专门的网关参数。它在后台启动一个 Claude Code 进程，并把环境变量传给这个进程。所以接中转只要让这个进程拿到两个变量：`ANTHROPIC_BASE_URL=https://api.openlux.ai`（不带 `/v1`）和 `ANTHROPIC_AUTH_TOKEN=<你的 OpenLux 令牌>`，再用 `model` 选项填中转上在售的完整模型 ID。

依据是 Claude Code 官方文档 [Connect Claude Code to an LLM gateway](https://code.claude.com/docs/en/llm-gateway-connect) 里的「Agent SDK」一节，以及 Agent SDK 的 [Quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart)、[Python 参考](https://code.claude.com/docs/en/agent-sdk/python)、[TypeScript 参考](https://code.claude.com/docs/en/agent-sdk/typescript) 和 [排错页](https://code.claude.com/docs/en/agent-sdk/troubleshooting)。中转在官方文档里叫「LLM gateway」。

## 适用范围和前提

- **适用对象**：Python 包 `claude-agent-sdk`（Python 3.10 及以上）和 TypeScript 包 `@anthropic-ai/claude-agent-sdk`（Node.js 18.14 及以上）。自己写工具循环、直接调 Messages API 的 Anthropic Client SDK 不是本文对象。
- **不用另装 Claude Code**：官方说明两个 SDK 都自带 Claude Code 原生程序，多数安装不需要单独装。
- **认证方式只能用 Key**：官方说明，除非事先获批，Anthropic 不允许第三方开发者在基于 Agent SDK 的产品里提供 claude.ai 登录或其额度，要用 API Key 方式认证。走中转用的是 OpenLux 令牌，属于这一类。
- **要准备的东西**：在 OpenLux 控制台「令牌」页（`https://www.openlux.ai/console/token`）创建一个令牌；从价格接口 `https://www.openlux.ai/api/pricing_new` 选一个 `supported_endpoint_types` 含 `anthropic` 的 Claude 模型。2026-11-24 查询时，`claude-opus-5-5`、`claude-sonnet-5-5`、`claude-haiku-5-5` 都含 `anthropic`。

## 需要设置的三项

| 设置项 | 填什么 | 说明 |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `https://api.openlux.ai` | 不带 `/v1`，Claude Code 自己拼 `/v1/messages`。多写会变成 `/v1/v1/messages`，返回 404 |
| `ANTHROPIC_AUTH_TOKEN` | OpenLux 令牌 | 以 `Authorization: Bearer` 请求头发送。官方建议：不确定网关读哪种请求头时先用它 |
| `model` 选项 | 如 `claude-sonnet-5-5` | 官方说明这个选项接受模型别名或完整模型名；接中转时填价格接口里的完整 ID |

也可以用 `ANTHROPIC_API_KEY` 代替 `ANTHROPIC_AUTH_TOKEN`，它以 `x-api-key` 请求头发送。OpenLux 的 `/v1/messages` 两种请求头都接受，二选一即可。

## 第一步：先用 curl 验证地址和令牌

官方建议在写代码之前，先直接给网关发一个只要 1 个 token 的请求，这样失败时能确定是地址或令牌的问题，而不是代码的问题：

```bash
export ANTHROPIC_BASE_URL=https://api.openlux.ai
export ANTHROPIC_AUTH_TOKEN=你的OpenLux令牌

curl -sS -w '\n%{http_code}\n' -X POST "$ANTHROPIC_BASE_URL/v1/messages" \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model": "claude-sonnet-5-5", "max_tokens": 1, "messages": [{"role": "user", "content": "."}]}'
```

怎么看结果（按官方说明）：

- 返回以 `{"id":"msg_` 开头、带 `"content":[...]` 的 JSON：地址和令牌都对。
- 返回「模型不存在」一类的错误：地址和令牌也是通的，只是模型名要改。
- 返回 `401`：令牌被拒绝。OpenLux 返回的原文是 `Invalid token`，检查令牌是否复制完整、是否已删除。

## 第二步：Python 写法

下面的示例都假设你已把 OpenLux 令牌放在环境变量 `OPENLUX_API_KEY` 里。

Python SDK 的 `env` 选项会**叠加**在当前进程的环境变量上。所以在启动程序的终端里 `export` 过这两个变量，就可以不写 `env`；想把配置写在代码里，就这样传：

```python
import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


async def main():
    options = ClaudeAgentOptions(
        model="claude-sonnet-5-5",
        env={
            "ANTHROPIC_BASE_URL": "https://api.openlux.ai",
            "ANTHROPIC_AUTH_TOKEN": os.environ["OPENLUX_API_KEY"],
        },
    )
    async for message in query(prompt="用一句话介绍你自己", options=options):
        if isinstance(message, ResultMessage):
            print(message.subtype, message.is_error, message.result)


asyncio.run(main())
```

注意：SDK 不会自动读取 `.env` 文件。令牌放在 `.env` 里的话，要先自己用 `dotenv` 之类的库加载。

## 第三步：TypeScript 写法

TypeScript SDK 不一样：**只要设置了 `options.env`，就会整个替换**子进程的环境变量，不再继承 `process.env`。官方要求把 `process.env` 展开进去，否则 `PATH` 和你在终端里导出的变量都传不进去：

```ts
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "用一句话介绍你自己",
  options: {
    model: "claude-sonnet-5-5",
    env: {
      ...process.env,
      ANTHROPIC_BASE_URL: "https://api.openlux.ai",
      ANTHROPIC_AUTH_TOKEN: process.env.OPENLUX_API_KEY,
    },
  },
})) {
  if (message.type === "result") {
    console.log(`Done: ${message.subtype}`);
  }
}
```

如果完全不设 `options.env`，子进程默认继承 `process.env`，在终端里导出这两个变量也能用。

## 第四步：确认接通，以及 settings.json 的影响

**成功标准**：Python 里最后的 `ResultMessage` 满足 `subtype` 为 `success`、`is_error` 为 `False`、`result` 里有回答；TypeScript 打印出 `Done: success`。Python 参考说明，`subtype` 为 `success` 时 `is_error` 仍可能为 `True`（例如模型拒答），这时看 `stop_reason`；`api_error_status` 是导致结束的 API 错误的 HTTP 状态码。

**注意 `~/.claude/settings.json`**：Agent SDK 默认会加载用户、项目和本地三类设置文件（`settingSources` / `setting_sources` 的默认值是全部来源）。官方网关文档又说明，同一个变量在终端里和设置文件的 `env` 块里都设了，以设置文件为准。所以，如果这台机器上的 Claude Code 已经在 `~/.claude/settings.json` 的 `env` 里配了别的网关地址或令牌，SDK 进程可能用的是那一份，而不是你在代码里传的值。排查办法：

1. 打开 `~/.claude/settings.json` 和项目下的 `.claude/settings.json`、`.claude/settings.local.json`，看 `env` 里有没有 `ANTHROPIC_BASE_URL`、`ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_API_KEY`。
2. 或者把 `settingSources: []`（Python 为 `setting_sources=[]`）传进选项，不加载这三类设置。官方说明管理员下发的托管策略不受这个选项影响，照常加载。

## 常见报错和处理

| 现象 | 可能原因 | 处理 |
|---|---|---|
| `Not logged in` 或 `Invalid API key` | 变量没传进 SDK 启动的进程：TypeScript 设了 `env` 却没展开 `process.env`；令牌只写在 `.env` 里没加载；程序由 IDE 或服务管理器启动，拿不到终端里的变量 | 按第二、三步在代码里显式传 `env`；先加载 `.env` |
| 401，`Invalid token` | 令牌错误、复制不完整或已删除 | 用第一步的 curl 单独测；在控制台重新创建令牌 |
| 404，`Invalid URL (POST /v1/v1/messages)` | `ANTHROPIC_BASE_URL` 多写了 `/v1` | 改成 `https://api.openlux.ai` |
| `There's an issue with the selected model` 或模型不存在 | `model` 填了中转上没有的名字 | 换成价格接口里含 `anthropic` 端点的完整 ID |
| 400，提到 `context_management` 或 `Extra inputs are not permitted` | 上游拒收 Claude Code 发出的预发布字段 | 按官方网关排错表，在 `env` 里加 `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1` |
| `Native CLI binary for <platform>-<arch> not found`（TypeScript） | 安装时跳过了 npm 可选依赖，例如 `npm ci --omit=optional` | 不跳过可选依赖重新安装，或单独安装 Claude Code 后设 `pathToClaudeCodeExecutable` |
| `CLINotFoundError`（Python） | pip 装的是源码包而不是平台 wheel（如 ARM64 Windows），没有自带程序 | 单独安装 Claude Code，或用 `cli_path` 指向 `claude` 可执行文件 |
| `ProcessError`，只有 `Check stderr output for details` | 这段文字是固定文本，不是真正的报错 | 传 `stderr` 回调，把 Claude Code 写到 stderr 的内容打印出来再看 |

同一份网关配置也适用于 Claude Code 命令行，命令行的配置方法见 [Claude Code 怎么接入 Claude 中转 API](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)。

## 开始使用

在 OpenLux 控制台创建令牌，先跑一遍第一步的 curl，再把两个变量和模型 ID 传给 Agent SDK：[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-agent-sdk-relay-api-base-url-env-setup&utm_content=footer)

## 同专题文章

- [Claude 桌面版怎么接入 Claude 中转 API：开发者模式、Configure Third-Party Inference、网关地址、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-desktop-relay-api-third-party-inference-gateway-setup/)
- [Claude 客户管理加密密钥被 KMS 拒绝时，如何用 Webhook 发现与恢复告警？](https://a37836323.github.io/openlux-api-guides/news/claude-external-key-webhook-events/)
- [Claude API 报「Streaming is required for operations that may take longer than 10 minutes」怎么办：max_tokens 阈值、流式拿完整结果、timeout 与 Batches 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-streaming-required-10-minutes-max-tokens-fix/)
- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)
- [Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-image-400-size-dimension-limit-fix/)
- [Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？](https://a37836323.github.io/openlux-api-guides/news/claude-api-sampling-parameters-text-watermark/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

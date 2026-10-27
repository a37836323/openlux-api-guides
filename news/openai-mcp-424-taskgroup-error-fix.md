---
layout: default
title: "OpenAI 调用 MCP 工具报 424「unhandled errors in a TaskGroup」怎么办：outputSchema、structuredContent 与连通性排查"
description: "Responses API 或 Playground 调用远程 MCP 工具报 424 unhandled errors in a TaskGroup (1 sub-exception)：按官方文档核对 outputSchema 与 structuredContent、返回内容类型、isError 写法、公网可达性与 authorization，并用 MCP Inspector 验证。"
permalink: /news/openai-mcp-424-taskgroup-error-fix/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[OpenAI MCP 工具文档](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)

# OpenAI 调用 MCP 工具报 424「unhandled errors in a TaskGroup」怎么办：outputSchema、structuredContent 与连通性排查

在 Responses API 或 API Playground 里接入远程 MCP 服务器，工具列表能拿到，但一调用工具就失败，报错文字是 `424: unhandled errors in a TaskGroup (1 sub-exception)`。这个报错本身不说明原因，要按下面的顺序排查：**先查工具是否声明了 `outputSchema` 却没返回符合它的 `structuredContent`**，再查返回内容格式，最后查 OpenAI 能否连上并通过鉴权访问你的服务器。

本文适用于 Responses API 的 MCP 工具（`type: "mcp"`）和 API Playground 中添加的 MCP 服务器。在 ChatGPT 开发者模式里添加连接器时，社区也有人遇到同样的文字，排查思路可以参考，但界面和日志位置不同。依据来自 OpenAI 的 [MCP 工具文档](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)、[连接与测试指南](https://developers.openai.com/apps-sdk/deploy/testing) 和 MCP 官方规范的 [Tools 章节](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

## 这个报错到底说明了什么

OpenAI 的 [错误码文档](https://developers.openai.com/api/docs/guides/error-codes) 只列了 400、401、403、429、500、503，没有解释 424，也没有提到 MCP。MCP 工具文档的说法是：工具调用失败时，会把错误写进 `mcp_call` 输出项的 `error` 字段，内容可能是 MCP 协议错误、MCP 工具执行错误，或一般的连接错误。

`unhandled errors in a TaskGroup (1 sub-exception)` 从字面看对应 Python 的任务组机制。按 [Python 文档](https://docs.python.org/3/library/asyncio-task.html) 对 `asyncio.TaskGroup` 的说明，组内任务失败时，异常会被合并进 `ExceptionGroup` 再抛出；「1 sub-exception」就是里面包着 1 个具体异常。所以只看这句话，看不出真正的原因，需要换一个能显示原始错误的工具去复现（见后文 MCP Inspector 一节）。

在 OpenAI 社区 [API Returns 424 Error for MCP Calls](https://community.openai.com/t/api-returns-424-error-for-mcp-calls/1353593) 一帖中，首帖用户描述：服务器日志显示请求已正常处理，MCP Inspector 和其他客户端也能用，只有 OpenAI 这边报 424；之后又有多位用户回复遇到同样问题。其中一位用户确认原因是定义了输出 schema，但返回里缺少 `structuredContent`；另一位改为让工具返回结构化数据而不是文本后解决。OpenAI 支持人员在 2026-10-21 的回复中建议：如果工具声明了 `outputSchema`，检查返回的 `structuredContent` 是否与之匹配。

## 先按这张表定位方向

| 现象 | 优先检查 | 官方依据 | 处理方式 |
|---|---|---|---|
| 工具列表正常，调用工具时 424 | 工具是否声明了 `outputSchema`，返回里有没有符合它的 `structuredContent` | MCP 规范：声明了输出 schema 的服务器必须返回符合它的结构化结果 | 补上 `structuredContent`，或去掉 `outputSchema` |
| 只有某些参数或某些情况下失败 | 出错分支是否也返回了合规结构 | MCP 规范：工具执行错误用 `isError: true` 的结果返回 | 出错时返回 `isError: true` 和文字说明 |
| `mcp_list_tools` 里没有你的工具 | 服务器地址、传输协议、`allowed_tools` | OpenAI 文档：`tools` 只列出成功导入的工具 | 核对 `server_url`、传输方式和工具名 |
| 服务器在内网或本机 | OpenAI 能否从公网访问到它 | OpenAI 文档：远程服务器需在公网；私有服务器用 Secure MCP Tunnel | 改用公网 HTTPS 地址，或用 `tunnel_id` |
| 服务器需要令牌，调用失败 | 是否每次请求都带了 `authorization` | OpenAI 文档：该字段不会被保存，每次创建请求都要带 | 每次请求都传入令牌 |

## 第一步：核对 outputSchema 和 structuredContent

MCP 规范对输出 schema 的要求是：如果工具提供了输出 schema，服务器**必须**返回符合该 schema 的结构化结果，客户端**应当**按 schema 校验结果。结构化结果放在返回的 `structuredContent` 字段里，是一个 JSON 对象；为了兼容旧客户端，规范建议同时在 `content` 里放一份序列化后的 JSON 文本。

规范中给出的合规返回示例（工具声明了 `temperature`、`conditions`、`humidity` 三个必填字段）：

```json
{
  "content": [
    {"type": "text", "text": "{\"temperature\": 22.5, \"conditions\": \"Partly cloudy\", \"humidity\": 65}"}
  ],
  "structuredContent": {"temperature": 22.5, "conditions": "Partly cloudy", "humidity": 65}
}
```

逐项检查：

1. 在 `tools/list` 的结果里找到出问题的工具，看它有没有 `outputSchema`。以 `tools/list` 实际返回的工具定义为准，不要只看自己的代码。
2. 如果有，确认每一次调用（包括空结果、找不到数据等分支）都返回了 `structuredContent`，而不是只在 `content` 里放一段文字。
3. 确认 `structuredContent` 的字段名、类型和必填项与 `outputSchema` 一致，例如 schema 写的是 `number`，就不要返回字符串 `"22.5"`。
4. 如果这个工具本来就只需要返回文字，可以直接去掉 `outputSchema`，只返回 `content`。

OpenAI 的连接与测试指南在打包前的检查清单里也写了同一条：结构化结果要与每个工具声明的输出 schema 一致。

## 第二步：检查返回内容格式和出错时的写法

规范定义的非结构化内容类型有 `text`、`image`、`audio`、`resource_link` 和 `resource`（嵌入资源）。如果你的服务器在 `content` 里放了规范之外的类型，例如自定义的 `"type": "json"`，排查时先改成 `text`，把 JSON 放进 `structuredContent` 或序列化成文本。

工具内部出错时的写法也要区分清楚。规范把错误分为两类：

- **协议错误**：未知工具、请求格式不对、服务器错误，用标准 JSON-RPC 的 `error` 返回，例如 `-32602`。
- **工具执行错误**：外部 API 失败、参数校验不通过、业务逻辑错误，应当返回一个正常的结果，并设置 `isError: true`，在 `content` 里用文字写明原因。

规范的说明是，工具执行错误里的说明能让模型据此调整参数重试。排查 424 时，顺带检查工具的出错分支是否按这种方式返回。

## 第三步：确认 OpenAI 能连上并通过鉴权

按 OpenAI MCP 工具文档：

- Responses API 支持使用 **Streamable HTTP** 或 **HTTP/SSE** 传输协议的远程 MCP 服务器。
- 远程服务器可以是**公网上**任何实现了 MCP 的服务器，用 `server_url` 指定；如果服务器是私有的、部署在内网或防火墙后面，要用 Secure MCP Tunnel，并用 `tunnel_id` 指定。如果你填的是本机或内网地址，应改为公网 HTTPS 地址或改用 Secure MCP Tunnel。
- 模型会先拉取工具列表，生成 `mcp_list_tools` 输出项，其中的 `tools` 只列出**成功导入**的工具。在这里找不到你的工具，就先别查调用阶段。
- 用 `allowed_tools` 限制导入的工具时，名字要和服务器返回的工具名一致。
- 需要令牌的服务器，令牌放在 MCP 工具的 `authorization` 字段。Responses API **不会保存**这个值，所以每次创建请求都要重新传入。

另外，`connector_id` 对 2026-09-01 之后发布的模型已弃用，文档要求改用 `server_url` 或 `tunnel_id`。

## 用 MCP Inspector 和 Playground 复现与验证

OpenAI 的连接与测试指南推荐两个工具：

**MCP Inspector**：直接列出并调用你的工具，看服务器原始返回。

```bash
npx @modelcontextprotocol/inspector@latest
```

指南建议用有代表性的输入、边界情况、缺失的标识和空结果逐个调用工具，并核对 schema 校验、鉴权错误和返回内容。前面社区帖子里的用户，就是在 Inspector 中看到了缺少 `structuredContent` 的问题。

**API Playground**：选择 **Tools → Add → MCP Server**，填入 HTTPS 地址并连接，然后发测试提示词，查看原始的请求和响应数据。

修改后判断是否解决，看这几点：

1. 响应里的 `mcp_list_tools` 列出了目标工具。
2. `mcp_call` 输出项的 `error` 为空，`output` 里有工具的返回内容。
3. 在 Inspector 中用同一组输入调用，核对 `structuredContent` 与 `outputSchema` 一致。

改了工具名、描述或 schema 后，指南建议把测试用例重新跑一遍。

## 仍然失败时：准备这些信息找官方支持

如果按上面三步检查后仍然报 424，OpenAI 支持人员在社区帖子里要求提供：最近一次请求的 request ID、带时区的失败时间，以及一份去掉凭据和隐私信息的最小请求与响应示例，提交到自己的私密支持工单里，不要把账户细节贴到公开帖子中。

通过 OpenAI 兼容的中转服务调用 Responses API 时，是否支持 `mcp` 工具类型、`mcp_call` 的 `error` 字段是否原样返回，以实际响应为准。排查时可以先用 MCP Inspector 确认服务器本身合规，再判断问题在哪一段。

如果你需要一个 OpenAI 兼容的 API 入口来调试和对比多个模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-mcp-424-taskgroup-error-fix&utm_content=footer)。

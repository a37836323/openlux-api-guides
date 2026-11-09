---
layout: default
title: "OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查"
description: "OpenAI Python SDK 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 时，先用 e.__cause__ 和 OPENAI_LOG 看底层原因，再按 Base URL、代理、HTTPX2 证书信任库、超时与重试逐项排查。"
permalink: /news/openai-python-apiconnectionerror-timeout-fix/
date: 2026-11-10
---

> 更新日期：2026-11-10 · 一手来源：[OpenAI Error codes 文档与 openai-python README](https://developers.openai.com/api/docs/guides/error-codes)

# OpenAI Python 报 APIConnectionError: Connection error 或 APITimeoutError: Request timed out 怎么办：Base URL、代理、证书与超时重试逐项排查

用 OpenAI 官方 Python SDK（`pip install openai`）调用接口时，报 `openai.APIConnectionError: Connection error.` 或 `openai.APITimeoutError: Request timed out.`，说明 **SDK 没有拿到一个完整的 HTTP 响应**：要么连不上服务器，要么等响应等到超时。这和 401、404、429 这类“服务器回了错误码”的情况是两条路，排查方向完全不同。

本文适用于直连 OpenAI，也适用于把 `base_url` 换成 OpenAI 兼容中转地址的情况。依据是 OpenAI 官方 [Error codes 文档](https://developers.openai.com/api/docs/guides/error-codes) 中的 Python 库错误类型说明，以及 [openai-python 官方 README](https://github.com/openai/openai-python) 和它的 [HTTPX2 迁移说明](https://github.com/openai/openai-python/blob/main/httpx2.md)。

## 先分清：连接错误和状态码错误不是一回事

官方 README 的说法是：库无法连接到 API 时（例如网络连接问题或超时），会抛出 `openai.APIConnectionError` 的子类；服务器返回 4xx 或 5xx 时，抛出的是 `openai.APIStatusError` 的子类，带 `status_code` 和 `response`。SDK 源码里，`APITimeoutError` 本身就是 `APIConnectionError` 的子类，两者默认的报错文字分别是 `Request timed out.` 和 `Connection error.`。

| 报错 | 属于哪类 | 说明了什么 | 先查什么 |
|---|---|---|---|
| `APIConnectionError: Connection error.` | 连接错误 | 没连上或连接中途失败，没有状态码 | Base URL、代理、证书、防火墙 |
| `APITimeoutError: Request timed out.` | 连接错误的子类 | 等待超过了设定的超时时间 | 超时设置、网络、是否长输出 |
| `AuthenticationError`（401） | 状态码错误 | 服务器已收到请求，Key 不对 | Key 和请求头 |
| `NotFoundError`（404） | 状态码错误 | 服务器已收到请求，路径或资源不存在 | 路径是否多/少 `/v1`、模型名 |
| `RateLimitError`（429） | 状态码错误 | 服务器已收到请求，触发限流或额度问题 | 看 `error.code` |
| `InternalServerError`（≥500） | 状态码错误 | 服务器端出错或过载 | 稍后重试 |

所以如果你看到的是 401、404，说明网络是通的，不用往代理和证书上查；只有 `APIConnectionError` / `APITimeoutError` 才需要按下面的步骤走。

OpenAI 官方 Error codes 文档对这两个错误的建议是：`APIConnectionError` 的原因是连接服务出了问题，应检查网络设置、代理配置、SSL 证书或防火墙规则；`APITimeoutError` 的原因是请求超时，应稍等后重试，持续出现再联系支持。

## 第一步：把底层原因打印出来

`Connection error.` 本身信息很少。README 给出的做法是捕获异常后看 `e.__cause__`，那里是底层 HTTP 库抛出的原始异常，往往能看出是域名解析失败、连接被拒、证书校验失败还是代理问题：

```python
import openai
from openai import OpenAI

client = OpenAI()
try:
    client.models.list()
except openai.APIConnectionError as e:
    print(type(e).__name__)
    print(repr(e.__cause__))
```

还可以打开 SDK 日志（README：设置环境变量 `OPENAI_LOG`，取 `info` 或更详细的 `debug`）：

```shell
export OPENAI_LOG=debug
```

另外确认一下实际在用的 SDK 版本，后面代理、证书、超时的写法都和版本有关：

```python
import openai
print(openai.__version__)
```

## 第二步：核对 Base URL 和环境变量

请求发到哪里，由 `base_url` 决定。README 说明 `base_url` 可以在创建客户端时传入，也可以用环境变量 `OPENAI_BASE_URL` 设置。常见问题：

1. **环境变量残留**：代码里没传 `base_url`，但系统或 `.env` 里还留着旧的 `OPENAI_BASE_URL`，请求就发到了一个已经不可用的地址。先 `echo $OPENAI_BASE_URL` 看一眼。
2. **地址拼写**：域名或端口写错，请求连不到正确的服务器，通常表现为 `APIConnectionError`，而不是 404。
3. **路径层级**：OpenAI 兼容地址一般要带到 `/v1`。路径层级写错时，只要域名能连上，通常会收到 404 这类状态码错误，而不是连接错误，可以据此区分。

如果接的是 OpenLux 这类 OpenAI 兼容中转，`base_url` 填 `https://api.openlux.ai/v1`，Key 在控制台「令牌」页创建：

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.openlux.ai/v1",
    api_key="你的令牌",
)
print([m.id for m in client.models.list().data][:5])
```

`client.models.list()` 请求的是 `/v1/models`。能列出模型，说明地址和 Key 都对；报 401（`Invalid token`）说明网络已通、只是 Key 不对；仍然是 `APIConnectionError`，再往下查代理和证书。

## 第三步：需要代理的网络，显式给 SDK 配代理

如果你所在的网络必须经过代理才能出网，官方 README 的做法是通过 `http_client` 传入带 `proxy` 参数的客户端。当前版本 README 的写法：

```python
from openai import OpenAI, DefaultHttpx2Client

client = OpenAI(
    base_url="https://api.openlux.ai/v1",
    http_client=DefaultHttpx2Client(proxy="http://你的代理地址:端口"),
)
```

注意两点：

- 当前 SDK 的 README 说明默认 HTTP 客户端已改为 **HTTPX2**，安装 `openai` 不再顺带安装 `httpx`；迁移说明里写明旧名字 `DefaultHttpxClient` 仍可用，但现在构造的也是 HTTPX2 客户端。自己直接构造 HTTP 客户端时，要用 `httpx2.Client`，不要再传 `httpx.Client`。
- 你用的如果是旧版本 SDK，写法以该版本 README 为准（先用上一步的 `openai.__version__` 确认版本）。

## 第四步：证书校验失败，按 HTTPX2 的信任库来配

`e.__cause__` 里如果是证书校验相关的错误，要特别注意 HTTPX2 迁移说明里的一条变化：**以前 HTTPX 用 `certifi` 提供的 CA 证书包校验证书；HTTPX2 改为使用操作系统的信任库，SDK 也不再安装 `certifi`**。官方列出的受影响场景有三类：

| 场景 | 为什么会失败 | 官方给的处理方式 |
|---|---|---|
| 精简容器镜像，没有系统 CA 证书 | 系统信任库是空的 | 往系统信任库装 CA 证书 |
| 公司网络有 TLS 检查代理 | 系统信任库里缺少该代理所需的根证书 | 把根证书装进系统信任库，或设置 `SSL_CERT_FILE` / `SSL_CERT_DIR` 指向含它的文件或目录 |
| 原来依赖自定义或修改过的 `certifi` 证书包 | 升级后不再读 `certifi` | 设置 `SSL_CERT_FILE`，或给客户端传 `verify=ssl.SSLContext` |

环境变量方式（迁移说明写明在默认 `trust_env=True` 时生效）：

```shell
export SSL_CERT_FILE=/path/to/ca-bundle.pem
```

在代码里显式指定：

```python
import ssl
from openai import OpenAI, DefaultHttpx2Client

ctx = ssl.create_default_context(cafile="/path/to/ca-bundle.pem")
client = OpenAI(http_client=DefaultHttpx2Client(verify=ctx))
```

如果是升级 SDK 之后才开始出现连接错误，而且 `e.__cause__` 指向证书校验，优先查这一项。

## 第五步：超时与重试怎么设

**默认值**：README 写明请求默认 10 分钟超时；SDK 源码里的默认值是总超时 600 秒、连接超时 5 秒。超时后抛 `APITimeoutError`。

**改超时**：`timeout` 可以传数字，也可以传 `httpx2.Timeout` 分别设置连接、读、写：

```python
import httpx2
from openai import OpenAI

client = OpenAI(timeout=httpx2.Timeout(120.0, connect=10.0))
```

也可以只对某一次请求改：`client.with_options(timeout=30.0)`。如果你自己把总超时设得比模型生成完整回答所需的时间还短，长输出的请求就会稳定地报 `APITimeoutError`，这时应调大超时，而不是一味加重试次数。

**重试**：README 写明，连接错误、408、409、429 和 ≥500 默认自动重试 **2 次**，带短暂的指数退避；超时的请求同样默认重试两次。用 `max_retries` 调整，`0` 表示不重试：

```python
client = OpenAI(max_retries=5)
```

README 同时说明，只有请求体可以安全重发时才会重试。所以你看到 `APITimeoutError` 时，SDK 可能已经重试过，实际等待时间可能是单次超时的数倍。

**流式中途断开**：README 特别说明，消费流式响应（`Stream` / `AsyncStream`）时，读超时抛 `APITimeoutError`，其它请求失败抛 `APIConnectionError`，并且**流式消费过程不会自动重试**，因为重放请求可能让已经输出的内容重复。流式场景要在自己的代码里捕获这两个异常，决定是否从头重发。

## 排查顺序速查

| 顺序 | 检查项 | 怎么判断通过 |
|---|---|---|
| 1 | 打印 `e.__cause__`，开 `OPENAI_LOG=debug` | 能看到具体的底层错误 |
| 2 | `OPENAI_BASE_URL` 和 `base_url` | 地址是你想要的，域名和端口正确 |
| 3 | `client.models.list()` 最小请求 | 返回模型列表，或至少返回 401 等状态码 |
| 4 | 代理 | 需要代理的网络已用 `proxy=` 显式配置 |
| 5 | 证书 | 系统信任库或 `SSL_CERT_FILE` 含所需根证书 |
| 6 | 超时与重试 | 超时大于正常响应时间，重试次数符合预期 |

做到第 3 步能拿到模型列表，连接问题就排除了；之后再报错，按具体的状态码（401、404、429 等）去查。

想用一个 OpenAI 兼容地址同时调用 GPT、Claude、Gemini 等模型，可以[注册 OpenLux 获取 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-python-apiconnectionerror-timeout-fix&utm_content=footer)。

## 同专题文章

- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些](https://a37836323.github.io/openlux-api-guides/news/openai-evals-read-only-shutdown-promptfoo-migration/)
- [OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办](https://a37836323.github.io/openlux-api-guides/news/openai-responses-incomplete-max-output-tokens-fix/)
- [OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改](https://a37836323.github.io/openlux-api-guides/news/agent-builder-shutdown-agents-sdk-chatkit-migration/)
- [gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办](https://a37836323.github.io/openlux-api-guides/news/gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix/)
- [whisper-1 将于 2027 年 2 月 26 日下线：换成 gpt-transcribe 要改哪些参数（language、时间戳、字幕格式）](https://a37836323.github.io/openlux-api-guides/news/whisper-1-shutdown-gpt-transcribe-migration/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

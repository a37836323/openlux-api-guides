---
layout: default
title: "OpenLux API 接入实战：用 OpenAI SDK 切换统一网关，并处理 401、429 和流式中断"
description: "OpenLux API 快速接入、401、429 与流式中断处理实战"
permalink: /quickstart/
---

# OpenLux API 接入实战：用 OpenAI SDK 切换统一网关，并处理 401、429 和流式中断

如果项目已经使用 OpenAI SDK，切换到 OpenLux 的核心只有三项：把 API Key 放进环境变量、将 `base_url` 设为 `https://api.openlux.ai/v1`、把 `model` 改成控制台实际可用的模型 ID。

真正容易踩坑的不是这三行配置，而是模型名、账号分组、429 重试和流式中断。本文给出一套可以直接改进项目的接入方式，同时明确哪些数据已经从公开接口核验，哪些能力仍需要使用自己的账号做真实请求验证。

> 核验时间：2026-08-24。OpenLux 公开价格接口当时返回 460 个在售模型条目，并列出了 `/v1/chat/completions` 和 `/v1/responses` 两种 OpenAI 风格端点。未携带令牌访问 `/v1/models` 会返回 401，说明该路径已启用鉴权。模型权限和最终价格仍以登录后控制台为准。

## 一、先准备 API Key

注册并登录 OpenLux 后，在控制台创建 API Key。不要把 Key 直接写进代码，更不要提交到 Git 仓库。

本文统一使用现有 OpenLux 推广渠道，平台与文章效果通过链接中的 UTM 参数区分：

https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openlux_api_quickstart&utm_content=article

macOS 或 Linux：

```bash
export OPENLUX_API_KEY="替换成控制台创建的密钥"
```

Windows PowerShell：

```powershell
$env:OPENLUX_API_KEY="替换成控制台创建的密钥"
```

OpenAI 官方 SDK 同样建议将 API Key 放在环境变量中，而不是硬编码在源码里。

## 二、Python：完成第一个 Chat Completions 请求

先安装 SDK：

```bash
pip install -U openai
```

新建 `quickstart.py`：

```python
import os

from openai import OpenAI


client = OpenAI(
    api_key=os.environ["OPENLUX_API_KEY"],
    base_url="https://api.openlux.ai/v1",
    timeout=60.0,
    max_retries=2,
)

response = client.chat.completions.create(
    model="gpt-5.6-terra",
    messages=[
        {
            "role": "system",
            "content": "你是一个严谨、简洁的技术助手。",
        },
        {
            "role": "user",
            "content": "用三点解释什么是指数退避。",
        },
    ],
)

print(response.choices[0].message.content)
```

运行：

```bash
python quickstart.py
```

这里的 `gpt-5.6-terra` 只是示例。实际调用前应先查看控制台模型列表，确认账号所在分组能够使用该模型。不要看到公开价格页里有模型名，就假定自己的 Key 一定有权限。

## 三、cURL：先排除 SDK 配置问题

遇到问题时，先用最小 cURL 请求验证鉴权、域名和模型名，比一开始就在业务框架里排查更快。

```bash
curl https://api.openlux.ai/v1/chat/completions \
  -H "Authorization: Bearer $OPENLUX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5.6-terra",
    "messages": [
      {"role": "user", "content": "只回复：连接成功"}
    ]
  }'
```

如果 cURL 成功而业务代码失败，问题通常在环境变量、代理、SDK 初始化或请求参数；如果 cURL 也失败，就先检查 Key、模型权限和账号余额。

## 四、Node.js：只替换客户端配置

安装 SDK：

```bash
npm install openai
```

新建 `quickstart.mjs`：

```javascript
import OpenAI from "openai";

const client = new OpenAI({
  apiKey: process.env.OPENLUX_API_KEY,
  baseURL: "https://api.openlux.ai/v1",
  timeout: 60_000,
  maxRetries: 2,
});

const response = await client.chat.completions.create({
  model: "gpt-5.6-terra",
  messages: [
    { role: "system", content: "你是一个严谨、简洁的技术助手。" },
    { role: "user", content: "用三点解释什么是指数退避。" },
  ],
});

console.log(response.choices[0].message.content);
```

运行：

```bash
node quickstart.mjs
```

## 五、Responses API 能不能用？

OpenAI 当前官方 SDK 的基础示例优先使用 Responses API。OpenLux 的公开价格接口也列出了 `/v1/responses`，并把 GPT-5.6 Luna、Terra、Sol 标记为支持 `openai-response`。

如果控制台显示你的模型和分组支持该端点，可以这样验证：

```python
response = client.responses.create(
    model="gpt-5.6-terra",
    input="用一句话解释幂等性。",
)

print(response.output_text)
```

但“公开接口列出端点”不等于每个渠道和模型的全部参数都完全一致。生产接入前，至少要验证普通文本、流式输出、结构化输出和工具调用这四类请求。

## 六、401 怎么排查？

401 通常不是“模型不够好”，而是鉴权链路没有建立。按下面顺序检查：

1. 环境变量是否真的存在；
2. Key 前后是否多了空格或引号；
3. 请求头是否为 `Authorization: Bearer ...`；
4. `base_url` 是否为 `https://api.openlux.ai/v1`；
5. Key 是否已被删除、禁用或重新生成；
6. 服务器、容器、CI 环境是否拿到了同一个环境变量；
7. 是否把 ChatGPT 登录凭据误当成了 API Key。

可以先做本地检查，但不要打印完整 Key：

```python
import os

key = os.getenv("OPENLUX_API_KEY", "")
if not key:
    raise RuntimeError("没有检测到 OPENLUX_API_KEY")

print("Key 已读取，长度：", len(key))
```

## 七、429 不要固定等待一秒后无限重试

429 可能代表请求频率、并发数、账号额度或上游渠道受到限制。生产代码应该：

- 优先读取服务端返回的 `Retry-After`；
- 没有该字段时使用指数退避并增加随机抖动；
- 设置最大重试次数和总超时；
- 记录模型、状态码、request ID 和耗时；
- 对工具调用、支付、写数据库等非幂等操作单独处理。

不要在几十个并发请求遇到 429 后全部 `sleep(1)`。它们会在一秒后同时再次请求，形成新的流量尖峰。

## 八、流式输出中断后为什么不能无脑重放？

流式请求已经输出一部分内容后断开，服务端可能已经继续生成，甚至已经执行过工具调用。如果客户端直接重放完整请求，可能导致：

- 用户看到重复内容；
- 工具或业务动作执行两次；
- token 重复计费；
- 前端状态与服务端日志不一致。

更稳妥的做法是给每次业务请求分配 request ID，区分“连接前失败”和“已经收到部分输出后失败”。只有尚未产生任何输出、且业务本身可安全重试时，才自动重试。

## 九、Luna、Terra、Sol 怎么选？

OpenLux 公开价格接口在 2026-08-24 返回的基准价格如下，单位是美元 / 100 万 token：

| 模型 | 输入基准价 | 输出基准价 | 缓存命中基准价 | 更适合先验证的任务 |
| --- | ---: | ---: | ---: | --- |
| `gpt-5.6-luna` | $0.2 | $1.2 | $0.02 | 分类、提取、大批量简单任务 |
| `gpt-5.6-terra` | $2 | $12 | $0.2 | 通用开发、质量与成本平衡 |
| `gpt-5.6-sol` | $5 | $30 | $0.5 | 高价值、复杂推理和专业任务 |

这些是基准价，最终价格还取决于账号分组倍率。不要只比较输入单价；真实成本还包括输出长度、失败率、重试次数和任务成功率。

推荐先准备 20～50 条真实业务样本，比较三个模型的：

- 任务成功率；
- 首字延迟和总耗时；
- 输入、输出和缓存 token；
- 每个成功任务的最终成本；
- 失败后是否需要人工返工。

## 十、上线前的最小验收清单

- [ ] Key 只保存在服务端环境变量；
- [ ] 用 cURL 完成一次最小请求；
- [ ] 记录模型名、状态码、request ID、耗时和 token；
- [ ] 验证 401、429 和超时行为；
- [ ] 流式中断后不会自动重复执行业务动作；
- [ ] 账号分组和最终扣费经过一次真实账单核对；
- [ ] 准备至少一个可切换的备用模型；
- [ ] 客户端和服务端都没有输出完整 API Key。

## 总结

OpenLux API 的最小接入并不复杂：官方 OpenAI SDK 加上新的 `base_url`、API Key 和真实模型 ID 就能开始验证。生产环境真正需要投入精力的是鉴权、限流、流式中断、账单核对和可替换性。

如果准备开始测试，先注册账号、创建独立 API Key，再用本文的 cURL 请求完成第一次验证：

https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openlux_api_quickstart&utm_content=footer

---

数据来源与说明：

- OpenLux 实时定价接口：https://api.openlux.ai/api/pricing
- OpenAI 官方 SDK 文档：https://developers.openai.com/api/docs/libraries
- 本文更新时间：2026-08-24
- 本文已核验公开价格数据、端点声明和未授权响应；正式发布前仍需用测试账号完成一次付费真实调用，并把结果补入文章。

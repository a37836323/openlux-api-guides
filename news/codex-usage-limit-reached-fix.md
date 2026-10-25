---
layout: default
title: "Codex 提示用量到上限怎么办：查剩余额度与重置时间、加购 credits、改用 API Key"
description: "Codex 用 ChatGPT 登录时提示用量到上限的处理：用 codex login status 确认登录方式，在用量面板和 /status 查看剩余额度与重置时间，了解 5 小时窗口与每周上限，按套餐加购 credits，或用 codex login --with-api-key 改为按 API 价格计费，并按官方因素减少消耗。"
permalink: /news/codex-usage-limit-reached-fix/
date: 2026-10-26
---

> 更新日期：2026-10-26 · 一手来源：[OpenAI 官方文档：Codex Pricing](https://developers.openai.com/codex/pricing)

# Codex 提示用量到上限怎么办：查剩余额度与重置时间、加购 credits、改用 API Key

用 ChatGPT 账号登录 Codex（桌面端、CLI 或 IDE 插件）时，额度来自你的 ChatGPT 套餐，用完后要等重置或换一种计费方式才能继续。处理思路很简单：先确认自己是哪种登录方式，再去用量面板看剩余额度和重置时间，然后在「等重置」「加购 credits」「改用 API Key 按量计费」三条路里选一条。本文只依据 OpenAI 官方的 Codex [Pricing 页面](https://developers.openai.com/codex/pricing) 和 [Authentication 页面](https://developers.openai.com/codex/auth) 整理，适用于 Free、Go、Plus、Pro、Business、Edu、Enterprise 各套餐下的 Codex 使用者；具体价格和额度数值以官网页面为准，官方会随时调整。

## 先确认你是用哪种方式登录的

Codex 有两种登录方式，额度来源完全不同：

- 用 ChatGPT 登录：走套餐内额度，受本文说的 5 小时窗口、每周上限约束。
- 用 API Key 登录：按 OpenAI Platform 的标准 API 价格计费，不消耗 ChatGPT 套餐额度。

在 CLI 里运行下面的命令，可以看到当前生效的登录方式：

```bash
codex login status
```

官方说明 CLI 和 IDE 插件共用同一份登录缓存，所以在任一端退出登录，另一端也需要重新登录。如果显示的是 API Key 登录却仍然被拒，那就不是套餐额度问题，应该去 Platform 后台查 API 组织的限额和账单，本文后面的「加购 credits」不适用。

## 套餐额度是怎么算的

官方 Pricing 页面的要点：

- ChatGPT Work 和 Codex 共用同一份额度，Work 使用与 Codex 相同的价格、credits 和用量上限。
- 本地消息和云端对话共用套餐额度，云端任务可能比本地消息消耗更多。
- 页面给出的是 Plus 和 Standard Business 每 5 小时的本地消息估算；Pro 目前没有 5 小时限制。
- 每周上限也可能生效（原文 "Weekly limits may also apply"）。
- 开通 flexible pricing 的 Enterprise/Edu 没有固定限额，按 credits 扣减；没开通的 Enterprise/Edu 大多数功能与 Plus 的单席位额度相同。

页面当前给出的 Plus / Standard Business 每 5 小时本地消息估算如下（官方强调这些不是固定的消息上限，实际以用量面板为准）：

| 模型 | Plus | Standard Business |
|---|---|---|
| GPT-6 Astra | 5-45 | 5-45 |
| GPT-6.1 Sol | 15-160 | 15-160 |
| GPT-6 Sol | 15-150 | 15-150 |
| GPT-6 Luna | 350-3,000 | 350-3,000 |

区间这么宽，是因为官方说模型选择、上下文、推理、工具调用、检索和缓存都会影响消耗，单看提示词长度并不能可靠估算。同一个账号，换个模型或换个任务，能发的消息数可能差很多。

## 去哪里查剩余额度和重置时间

官方给了两个入口：

1. 用量面板：[chatgpt.com/codex/settings/usage](https://chatgpt.com/codex/settings/usage)。官方说明当前额度和重置时间都在这里看。
2. CLI 会话里输入斜杠命令 `/status`，查看本次会话可用的剩余额度。

官方建议每一两周看一次面板，了解自己的消耗节奏和剩余容量。排查时先看清楚是 5 小时窗口用完了，还是每周上限用完了：两者的重置时间都以面板显示为准；如果等不了，再考虑下面的另外两条路。

## 额度用完后能做什么

官方「What happens when you hit usage limits?」一节的说法整理成下表：

| 情况 | 官方给出的做法 | 注意事项 |
|---|---|---|
| 任务正在执行中途触顶 | 当前这一轮可以继续做完 | 受 fair use 限制，不能当作无限额度 |
| Plus、Pro 用户 | 购买额外 credits 继续使用，不必升级套餐 | credits 的价格以官网为准 |
| 开通 flexible pricing 的 Business、Edu、Enterprise | 购买更多 workspace credits | 未开通 flexible pricing 的工作区不适用这一条 |
| 所有用户 | 用 API Key 继续跑本地对话 | 按标准 API 价格计费，云端功能不可用 |

如果只是偶尔触顶，等 5 小时窗口重置成本最低；需要马上接着干活，再在加购 credits 和 API Key 之间选。

## 改用 API Key 继续工作的步骤

官方 Authentication 页面给出的操作：

1. 在 OpenAI 后台（platform.openai.com/api-keys）创建 API Key，放进环境变量 `OPENAI_API_KEY`。
2. CLI 按官方示例，从标准输入把密钥传给登录命令：

```bash
printenv OPENAI_API_KEY | codex login --with-api-key
```

3. IDE 插件在未登录界面选择 Use API Key 并填入密钥；桌面端选择 Sign in another way 后填入。
4. 再运行 `codex login status`，确认当前是 API Key 登录。

切换前要知道这些限制（均来自官方页面）：

- 计费走 OpenAI Platform 账户的标准 API 价格，不再使用套餐内的 credits。
- 依赖 ChatGPT 工作区或云服务的功能会受限或不可用；Codex cloud 必须用 ChatGPT 登录。Pricing 页面也写明 API Key 方式没有 GitHub 代码审查、Slack 等云端功能。
- 能用哪些模型取决于你的 API Key 有哪些模型权限。
- 数据保留和数据共享遵循 API 组织的设置，而不是 ChatGPT 工作区的设置，企业用户切换前最好先和管理员确认。
- 官方提醒不要用 API Token 价格去倒推订阅里包含多少任务，两套计费口径不同。

额度重置后想切回套餐，先 `codex logout` 清掉已存的凭据，再运行 `codex login` 走浏览器登录。凭据默认以明文保存在 `~/.codex/auth.json`（也可能在系统凭据库里），官方要求把它当作密码保管。团队如果想统一登录方式，可以在配置里写 `forced_login_method = "chatgpt"` 或 `"api"`，凭据不符时 Codex 会退出登录并退出程序。

## 为什么额度掉得这么快：官方列出的影响因素

社区里不少用户反馈长任务中途触顶、额度消耗比预期快。官方没有逐条回应这些个案，但 Pricing 页面列出了影响消耗的因素，可以逐项对照：

- 模型：表格里不同模型的估算区间差距很大，轻量模型能发的消息数明显更多。
- 速度模式：相对 Standard 模式，Fast 消耗套餐内额度的倍率是 2.5 倍，GPT-6 Astra 和 GPT-6.1 Sol 的 Ultrafast 是 8 倍。
- 图片生成：平均比普通消息快 3 到 5 倍消耗额度，视画质和尺寸而定。
- 本地还是云端：云端任务可能更耗额度。
- 会话越长、需要的上下文越多，每条消息消耗越多。

官方给出的省额度建议：

1. 提示词简短明确，去掉不需要的上下文。
2. 只提供相关文件，能缩小资料范围或时间范围就缩小。
3. 说清楚面向谁、什么格式、多长，把必做和可选的改进分开。
4. 缩小 AGENTS.md，大项目可以在仓库里分层嵌套 AGENTS.md，控制注入的上下文量。
5. 少挂 MCP 服务器，每个 MCP 服务器都会给消息增加上下文，不用时关掉。
6. 结果够用的话，换更小的模型或收窄任务范围。

## 处理完后怎么验证

- 套餐方式：重置时间过后，在用量面板或 `/status` 里看到额度已恢复，新发起的任务能正常执行。
- API Key 方式：`codex login status` 显示为 API Key 登录，本地任务能正常跑完，并且能在 OpenAI Platform 的用量页面看到对应的调用记录。
- 省额度调整：调整模型、速度模式和 MCP 服务器后，隔一段时间对比用量面板，看同样的工作量消耗是否下降。

## 参考资料

- 官方文档：[Codex Pricing](https://developers.openai.com/codex/pricing)
- 官方文档：[Codex Authentication](https://developers.openai.com/codex/auth)

如果你需要在一个入口里同时调用多家厂商的模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=codex-usage-limit-reached-fix&utm_content=footer)。

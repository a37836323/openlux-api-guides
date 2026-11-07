---
layout: default
title: "Claude Code 接入与报错 | OpenLux API 实战指南"
description: "Claude Code 接入与报错：共 6 篇，按发布时间从新到旧排列。"
permalink: /topics/claude-code/
---

# Claude Code 接入与报错

共 6 篇，按发布时间从新到旧排列。[返回全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

- 2026-11-08 · [Claude Code 走中转报 429、Repeated 529 Overloaded 或一直 Retrying 怎么办：限流、过载与重试变量逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-429-529-overloaded-retry-fix/)：Claude Code 走中转时一直 Retrying、报 Request rejected (429) 或 Repeated 529 Overloaded errors 怎么办。按 Claude Code 官方错误页和 Claude API 错误页，说明 429 与 529 的区别、用 /status 和 /v1/models 确认凭据、降低并发、/model 换模型，以及 CLAUDE_CODE_MAX_RETRIES、RETRY_WATCHDOG、529 退避变量怎么设。
- 2026-11-05 · [Claude Code 走中转报 401、Invalid API key 或一直让你 /login 怎么办：AUTH_TOKEN 与 API_KEY 怎么选、凭据优先级与 /status 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-401-invalid-api-key-fix/)：Claude Code 用 ANTHROPIC_BASE_URL 走中转时报 401、Invalid API key · Fix external API key、Invalid auth token 或一直提示 Not logged in · Please run /login 的排查：先用 curl 测令牌，再按官方说明选 ANTHROPIC_AUTH_TOKEN 或 ANTHROPIC_API_KEY、查凭据优先级与残留变量、用 /status 确认，VS Code 扩展与 apiKeyHelper 的特殊情况。
- 2026-11-03 · [Claude Code 走中转报 Unable to connect to API、Request timed out 怎么办：连接失败、超时与流式中断逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-unable-to-connect-timeout-fix/)：Claude Code 用 ANTHROPIC_BASE_URL 走中转时报 Unable to connect to API、Connection refused、ENOTFOUND、Request timed out、证书错误或回复中途断开的排查：先在同一终端用 curl 测 /v1/messages，再查残留 Base URL、代理变量、NODE_EXTRA_CA_CERTS，按官方说明调 API_TIMEOUT_MS 与流式看门狗，每次都 Connection dropped 时排查 tool search 字段。
- 2026-11-03 · [Claude Code 走中转后 /model 里看不到或切不了模型：网关模型发现、ANTHROPIC_DEFAULT_*_MODEL 与 Model not found 排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-model-picker-missing-models-fix/)：Claude Code 走中转后 /model 列表只有 opus、sonnet、haiku，或切换模型报 Model not found、There's an issue with the selected model：按官方文档开启网关模型发现、用 ANTHROPIC_DEFAULT_*_MODEL 和 ANTHROPIC_CUSTOM_MODEL_OPTION 手动指定，并逐项排查。
- 2026-11-02 · [Claude Code 走中转报 400「Extra inputs are not permitted」怎么办：context_management、output_config 与 thinking 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-400-extra-inputs-not-permitted-fix/)：Claude Code 接中转后报 400「Extra inputs are not permitted」：按报错点名的 context_management、output_config、thinking、system 角色或工具字段逐项处理，升级版本、设置 CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS，以及这个变量管不到的情况。
- 2026-10-26 · [Claude Code 怎么接入 Claude 中转 API：ANTHROPIC_BASE_URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/claude-code-relay-api-base-url-setup/)：Claude Code 接入 Claude 中转 API 的配置步骤：ANTHROPIC_BASE_URL 不带 /v1、ANTHROPIC_AUTH_TOKEN 与 ANTHROPIC_API_KEY 怎么选、settings.json 写法、/model 选模型、/status 确认，以及 401、模型不存在、一直要求登录等报错处理。

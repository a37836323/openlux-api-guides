---
layout: default
title: OpenLux API 实战指南
description: 解决 API 接入、错误排查、安全重试、模型成本和最新接口变化
permalink: /
---

# OpenLux API 实战指南

这里不堆泛泛的产品介绍，只整理开发者在真实接入中会遇到的问题。新闻栏目只收录有官方一手依据、并且能转化为实际操作建议的 API 与模型变化。

## 基础指南

- [OpenLux API 接入实战：用 OpenAI SDK 切换统一网关，并处理 401、429 和流式中断](./quickstart/)
- [`this organization has been disabled` 怎么排查：先定位请求到底失败在哪一层](./organization-disabled/)
- [API 429 与流式中断实战：什么能自动重试，什么重试一次就可能出事故](./rate-limit-stream-retry/)
- [模型选型为什么不能只看每百万 Token 单价？我更建议算“每个成功任务成本”](./model-cost-per-success/)

## 最新 API 与模型动态

- 2026-09-01 · [Claude Fable 5.1 上线：API 迁移需检查 tool_choice、思维块与数据保留](./news/claude-fable-5-1-api-migration/)
- 2026-09-01 · [在浏览器接入 Hugging Face WebGPU 内核：安装、版本与兼容性检查](./news/huggingface-webgpu-kernels-browser-inference/)
- 2026-08-28 · [Compliance API 会话转录正式可用：企业合规接入需要确认的权限与产品面](./news/compliance-api-session-transcripts-ga/)
- 2026-08-27 · [Gemini Omni 1.1 Flash 视频 API 控制指南：场景延展、首尾帧与 4K 输出](./news/gemini-omni-1-1-flash-video-api-controls/)
- 2026-08-26 · [Gemini 3.5 Transcribe 接入指南：实时与录音转写 API 怎么选](./news/gemini-3-5-transcribe-api-preview/)
- 2026-08-24 · [Claude API 电脑与浏览器工具正式可用，Files 和 Skills API 退出 Beta](./news/claude-api-computer-browser-files-skills-ga/)
- 2026-08-24 · [OpenAI 高风险 Agent 安全措施：上线前检查沙箱、隔离与审计](./news/openai-agent-security-deployment-checklist/)
- 2026-08-24 · [OpenAI API 零数据保留：符合资格客户上线前需核对的边界](./news/openai-api-zero-data-retention-eligibility-and-boundaries/)
- 2026-08-24 · [Anthropic Python SDK 1.0 发布：迁移到 httpx2 前先检查这些变更](./news/anthropic-python-sdk-v1-migration/)
- 2026-08-24 · [GPT-5.6 Sol API 与 credit pricing 未来三个月下调超20%，开发者该怎么评估](./news/gpt-5-6-sol-api-credit-pricing-cut/)

所有示例都应先使用低权限、低余额测试 Key 验证，再进入生产环境。

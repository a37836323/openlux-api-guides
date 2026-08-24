---
layout: default
title: OpenLux API 实战指南
description: 解决 API 接入、错误排查、安全重试与模型成本评估问题
permalink: /
---

# OpenLux API 实战指南

这里不堆泛泛的产品介绍，只整理开发者在真实接入中会遇到的问题：第一次请求怎么跑通、错误发生在哪一层、什么时候能重试，以及怎样衡量模型的真实任务成本。

## 指南目录

1. [OpenLux API 快速接入：处理 401、429 和流式中断](./quickstart/)
2. [`this organization has been disabled` 怎么分层排查](./organization-disabled/)
3. [API 429 与流式中断：什么能重试，什么不能](./rate-limit-stream-retry/)
4. [模型选型为什么要算“每个成功任务成本”](./model-cost-per-success/)

## 阅读建议

第一次接入从快速开始读起；遇到组织禁用或鉴权异常时先做分层排查；批量和流式业务上线前必须完成重试故障演练；模型选型则使用真实任务集评估，不只比较每百万 token 单价。

所有示例都应先使用低权限、低余额测试 Key 验证，再进入生产环境。

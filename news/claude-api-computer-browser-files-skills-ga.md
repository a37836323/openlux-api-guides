---
layout: default
title: "Claude API 电脑与浏览器工具正式可用，Files 和 Skills API 退出 Beta"
description: "Claude API 新增正式版电脑操作和浏览器工具，Files、Skills API 取消 Beta 头部要求，并支持 Managed Agents 域名限制。"
permalink: /news/claude-api-computer-browser-files-skills-ga/
date: 2026-08-24
---

> 更新日期：2026-08-24 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#august-19-2026)

# Claude API 电脑与浏览器工具正式可用，Files 和 Skills API 退出 Beta

## 结论先行：谁需要现在处理

**适合正在维护 Claude API 工具调用、文件引用、Agent Skills 或 Managed Agents 的开发者。**

2026 年 8 月 19 日，Claude API 的 `computer use` 工具以 `computer_toolset_20260801` 退出 Beta；同时上线了由应用自行托管浏览器的 `browser_toolset_20260801`。Files API 和 Skills API 也退出 Beta，相关请求可以移除对应的 Beta 头部。

迁移时不要把“退出 Beta”理解成“旧集成只需删一个请求头”。尤其是已有 `computer_20251124` 集成，升级后会改变请求形状和工具处理方式，必须按照官方迁移指南检查。Files API 则提供了新响应格式，删除头部后需要同步调整分页、文件过期时间和文件列表过滤逻辑。

## 本次发布改变了什么

| 能力 | 官方发布事实 | 建议动作 | 重点验证 |
|---|---|---|---|
| Computer use | `computer_toolset_20260801` 退出 Beta；支持批量动作，默认启用 zoom，并可通过 `configs` 按成员配置 | 现有 `computer_20251124` 集成按官方迁移指南改造 | 请求形状、动作解析、批量动作处理和成员配置 |
| Browser use | 上线 `browser_toolset_20260801`，由应用托管浏览器 | 新项目使用浏览器工具集，并自行管理浏览器视口 | 可访问性树、元素引用、表单、标签页、下载和可选上传 |
| Files API | `/v1/files` 及引用已上传文件的 Messages 请求不再要求 Beta 头部 | 删除 `files-api-2025-04-14`，改用新响应格式 | `expires_at`、`page`、`next_page` 和 `ids[]` |
| Skills API | `/v1/skills` 和通过 `container` 加载 Skills 的 Messages 请求不再要求 Beta 头部 | 删除 `skills-2025-10-02` | 正式版请求仍能加载和执行现有 Skills |
| Managed Agents | `web_search`、`web_fetch` 支持域名限制及更多配置 | 在 `agent_toolset_20260401` 的 `configs` 中设置策略 | 允许域、禁止域和额外参数是否生效 |

上述工具集可用于 Claude Fable 5、Claude Mythos 5、Claude Opus 5、Claude Sonnet 5 和 Claude Opus 4.8 的 Claude API。这里仅表示官方发布说明中的模型范围，不代表其他部署渠道或组织环境一定具有相同可用性，实际仍应以项目环境中的接口返回为准。

## Computer use：不要只删除 Beta 头部

### 官方发布事实

新的电脑操作工具集名称是 `computer_toolset_20260801`。官方说明的变化包括：

- 不再需要 Beta 头部；
- 支持在一轮中提交多个动作；
- `zoom` 默认启用；
- 可以通过 `configs` 对成员分别配置；
- 早期 Beta 版本仍可使用；
- 从 `computer_20251124` 升级会改变请求形状和工具处理方式。

因此，已有集成不能简单按照“替换工具名称、删除请求头”的方式上线。批量动作可能影响服务端返回事件的数量、动作确认逻辑和错误重试逻辑；默认启用 zoom 也可能改变截图或视觉处理流程。本文不补写官方材料没有列出的字段和调用示例，避免把旧版本结构误套到新工具集。

### 推荐迁移步骤

1. **盘点旧版本依赖**：确认代码、SDK 封装、提示词和日志中是否固定使用 `computer_20251124`。
2. **对照官方迁移指南**：重点检查请求结构、工具结果解析、动作分发、异常处理和多动作处理。
3. **保留旧路径作为回滚方案**：官方说明早期 Beta 版本仍可用，因此可以先在隔离环境验证新路径，再决定切换方式。
4. **覆盖真实操作场景**：至少测试点击、输入、滚动、截图、缩放和连续动作；如果业务依赖人工确认，也要检查每个动作的确认边界。
5. **比较原始事件日志**：不要只看最终文本，要核对工具调用、工具返回、动作顺序和失败后的重试是否符合现有状态机。
6. **最后再移除旧兼容代码**：当新工具集在回归测试中稳定后，再清理旧版本分支和不再使用的 Beta 头部。

## Browser use：它不是一台完整的远程桌面

### 官方发布事实

`browser_toolset_20260801` 是由客户端应用托管浏览器的工具集，运行在浏览器视口内，而不是完整桌面环境。它能够读取页面的可访问性树，并提供元素引用、表单输入、标签页管理、下载报告以及可选的文件上传能力，同时保留截图和点击控制。

### 作者建议：先判断任务边界

如果任务主要是网页导航、表单填写、标签页切换、下载文件或读取页面结构，浏览器工具通常更容易建立明确的页面级状态。若业务需要操作浏览器之外的桌面窗口、系统界面或更广泛的屏幕环境，则不应直接把 browser use 当作 computer use 的替代品。

新建集成时应确认三件事：

- 浏览器视口由应用自身托管，而不是假设平台自动提供完整桌面；
- 下载报告和可选文件上传是否已接入业务侧的文件生命周期管理；
- 页面元素引用、标签页和表单状态是否会在导航、刷新或跳转后失效。

这些是接入边界和应用责任，不是发布说明承诺的自动化成功率。上线前应使用自己的目标网站和权限模型进行验证。

## Files API：移除头部后要处理新响应格式

### 官方发布事实

Files API 已退出 Beta。以下请求不再需要 `files-api-2025-04-14`：

- `/v1/files` 相关请求；
- Messages API 中引用已上传文件的请求。

不带该头部时，接口使用新的响应格式，包括：

- 上传时可设置 `expires_in_seconds`；
- 文件对象报告 `expires_at`；
- 列表接口使用 `page` 和 `next_page` 分页；
- 列出文件时支持 `ids[]` 过滤器。

如果继续发送 `files-api-2025-04-14`，请求仍能工作，但返回旧格式。

### 推荐迁移步骤

先在测试环境移除头部，然后逐项检查：

1. 文件对象解析是否读取新的过期时间字段 `expires_at`；
2. 文件列表是否从旧分页逻辑切换到 `page`、`next_page`；
3. 是否可以用 `ids[]` 缩小列表查询范围；
4. 文件过期后，业务是否能给出明确的重新上传或重新绑定提示；
5. Messages 请求引用文件时，文件 ID、权限和生命周期是否仍被正确保存。

如果当前系统暂时无法处理新格式，可以短期保留旧 Beta 头部。但这只是兼容路径，不应在未评估的情况下同时混用两套响应解析逻辑。

## Skills API：头部可删，但要验证正式版加载链路

Agent Skills 和 Skills API（`/v1/skills`）已退出 Beta。包括通过 Messages API 的 `container` 参数加载 Skills 的请求，也不再需要 `skills-2025-10-02`。

迁移重点不是改写 Skill 内容，而是确认请求链路仍符合正式版接口：

- 删除 `skills-2025-10-02` 后，Skills 是否仍能被加载；
- `container` 相关请求是否仍返回预期结果；
- 应用是否把 Skill 加载失败与模型执行失败区分开；
- 旧的 Beta 头部是否由 SDK、公共请求封装或环境变量隐式注入；
- 测试和生产环境是否使用了不同的头部集合。

官方说明继续发送该头部仍可正常工作。因此，团队可以先完成正式版兼容性验证，再统一清理公共请求层中的旧头部，避免部分服务使用旧格式、部分服务使用正式版的情况。

## Managed Agents：用域名策略缩小 Web 工具范围

Managed Agents 的 `web_search` 和 `web_fetch` 现在可以在 `agent_toolset_20260401` 的 `configs` 数组中设置 `allowed_domains` 或 `blocked_domains`。此外：

- `web_fetch` 支持 `max_content_tokens`；
- `web_search` 支持 `user_location`；
- 每个 `configs` 条目由 `name` 标识，也可以带可选的 `type`；
- 仅传入 `name`、`enabled` 和 `permission_policy` 的请求仍可工作；
- 使用类型化 SDK 时，`configs` 条目会对应按工具区分的类型。

作者建议优先采用允许域名列表，而不是把访问范围交给 Agent 自行判断。迁移时建立一份业务域名清单，并测试搜索结果跳转、页面抓取、重定向和不在允许范围内的网站。域名限制是访问控制配置，不能替代凭证隔离、敏感数据脱敏和出站请求审计。

## 上线前检查清单

- [ ] 确认是否仍依赖 `computer_20251124`，并完成请求形状迁移。
- [ ] 为批量动作、zoom 默认行为和工具返回建立回归测试。
- [ ] 新浏览器项目使用 `browser_toolset_20260801`，并明确由应用托管视口。
- [ ] 移除 `files-api-2025-04-14` 后，更新 `expires_at` 和分页解析。
- [ ] 验证 `ids[]` 文件列表过滤不会破坏旧的缓存或同步逻辑。
- [ ] 移除 `skills-2025-10-02`，测试 `/v1/skills` 和 `container` 加载链路。
- [ ] 检查 SDK 或公共请求层是否隐式添加旧 Beta 头部。
- [ ] 为 Managed Agents 的 `web_search`、`web_fetch` 配置访问域名策略。
- [ ] 在测试环境记录原始请求、响应和工具事件，再逐步放量。
- [ ] 不把“退出 Beta”当成性能、成功率或所有区域可用性的保证。

## 目录核验说明

本文使用的 OpenLux 当前公开目录快照未匹配到相关条目，因此不据此声称这些工具已在其他目录或渠道上线；判断仍以官方发布说明和实际 API 验证为准。注册或查看目录入口：<https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-computer-browser-files-skills-ga&utm_content=footer>

## 官方一手来源

- [Claude Platform release notes](https://platform.claude.com/docs/en/release-notes/overview#august-19-2026)

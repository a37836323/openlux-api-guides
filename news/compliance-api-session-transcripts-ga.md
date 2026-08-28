---
layout: default
title: "Compliance API 会话转录正式可用：企业合规接入需要确认的权限与产品面"
description: "Cowork 和 Claude Code 会话转录接口正式脱离 beta，并扩展支持 Claude Science 与 Microsoft 365 会话。"
permalink: /news/compliance-api-session-transcripts-ga/
date: 2026-08-28
---

> 更新日期：2026-08-28 · 一手来源：[Claude 平台发版](https://platform.claude.com/docs/en/release-notes/overview#august-26-2026)

# Compliance API 会话转录正式可用：企业合规接入需要确认的权限与产品面

结论先说：如果企业要获取 Cowork 或 Claude Code 的会话转录，当前已核验的信息是，Compliance API 的 session endpoints 已脱离 beta；如果要获取用户机器上的 Claude Science 或 Claude for Microsoft 365 会话，则仍属于 Claude Enterprise 组织中的 beta 能力。两类场景都使用现有的 Compliance Access Key，并要求 `read:compliance_user_data` scope。

本文适合负责合规审计、内部留痕、风控平台或数据归档的 Claude Enterprise 管理员与开发者。重点不是判断某个模型能力，而是确认组织资格、密钥权限、接口路径、`product_surface` 字段，以及迁移后的回归验证范围。

## 先区分三类信息

### 官方发布事实

根据 Claude Platform 2026 年 8 月 26 日的发版说明：

- Compliance API 的 session endpoints 已对 Cowork 和 Claude Code sessions 脱离 beta。
- local session endpoints 在 Claude Enterprise organizations 中以 beta 形式支持 Claude Science 会话。
- local session endpoints 也支持 Claude for Microsoft 365 在 Excel、PowerPoint、Word 和 Outlook 中的会话。
- 上述 local session endpoints 使用现有 Compliance Access Key，并要求 `read:compliance_user_data` scope。

这里的“脱离 beta”只适用于 Cowork 和 Claude Code 的 session endpoints。不能据此推断所有本地会话类型都已经进入正式状态。

### 接口材料明确说明的用途

官方此前对本地会话接口的说明包括：

| 接口 | 用途 | 适用核验重点 |
|---|---|---|
| `GET /v1/compliance/apps/sessions/local` | 列出组织内本地会话 | 能否访问列表、分页或返回字段是否符合现有处理逻辑 |
| `GET /v1/compliance/apps/sessions/local/{session_id}` | 获取单个会话元数据 | 会话标识、所属用户及产品面字段 |
| `GET /v1/compliance/apps/sessions/local/{session_id}/messages` | 获取单个会话转录 | 消息内容是否可读取、结构是否能被下游解析 |

这些是“用户机器上运行的会话”对应的 local session endpoints。当前材料没有提供请求体、分页参数、响应完整 schema 或 SDK 调用示例，因此不应据此补写未被核验的参数。

### OpenLux 目录快照

当前提供的 OpenLux 公开目录匹配结果为空。它不能用来证明 Compliance API 是否已经上线，也不能替代 Claude Platform 官方文档。相关目录入口为：https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=compliance-api-session-transcripts-ga&utm_content=footer

## 权限：先确认密钥，再排查接口

接入前最关键的检查有两个：

1. 组织是否属于 Claude Enterprise。
2. 现有 Compliance Access Key 是否带有 `read:compliance_user_data` scope。

官方材料明确把这个 scope 与本地会话接口关联起来。若密钥不包含该 scope，不能假设只要拥有普通 API 权限就可以读取会话转录，也不能假设新建其他类型的密钥能够自动替代 Compliance Access Key。

权限排查应当分层进行：

- 先验证密钥能否调用本地会话列表接口。
- 再验证能否根据返回的 `session_id` 获取单个会话元数据。
- 最后验证 messages 接口是否能返回转录。
- 将“无法列出会话”“能列出但无法读取详情”“能读取详情但无法读取 messages”分别记录，不要把它们合并成一个笼统的鉴权失败。

材料没有给出错误码、认证头名称、密钥创建页面步骤或权限变更流程，因此这些部分需要以当前官方 API reference 和组织内部权限流程为准。

## `product_surface` 是路由识别信号

本地会话接口新增覆盖范围后，返回数据中的 `product_surface` 需要纳入下游处理。

已核验的值和规则如下：

| 会话来源 | `product_surface` 规则 | 接入处理建议 |
|---|---|---|
| Claude Science | `claude_science` | 单独标记，并保留 beta 状态 |
| Claude for Microsoft 365 | 以 `office_agents` 开头 | 按前缀识别，不要只匹配一个固定完整值 |
| Cowork | 材料未提供具体 `product_surface` 值 | 以实际响应字段为准，不要预设值 |
| Claude Code | 材料未提供具体 `product_surface` 值 | 以实际响应字段为准，不要预设值 |

需要特别注意：现有材料只说明这些值会出现在返回结果中，没有说明它们是请求参数，也没有说明管理员需要在 API 请求中设置某个产品面字段。因此，接入方不应把 `claude_science` 或 `office_agents` 当作必须提交的配置值。

对于以 `office_agents` 开头的值，建议在数据模型中保存完整原值，同时增加按前缀归类的逻辑。这样既能识别 Excel、PowerPoint、Word 和 Outlook 会话，也不会因为未来具体值不同而丢失来源信息。这个处理方式属于作者建议，不是官方 schema 承诺。

## Cowork 和 Claude Code 的迁移重点

此前材料说明，Cowork 和 Claude Code 会话曾以 beta 方式通过 Compliance API 返回转录；8 月 26 日发版说明确认其 session endpoints 已脱离 beta。迁移时应把重点放在接口行为回归，而不是只删除某个 beta 标记。

建议按以下顺序执行：

1. **盘点现有调用**  
   找出所有调用 Compliance API session endpoints 的服务、定时任务和归档流程，确认它们是否处理 Cowork 或 Claude Code sessions。

2. **核对密钥范围**  
   确认调用使用的是 Compliance Access Key，并核查 `read:compliance_user_data` scope。不要因为旧环境已经能调用，就跳过密钥记录和权限审计。

3. **验证列表接口**  
   调用 local sessions 列表接口，检查能否发现组织内目标会话，以及现有解析器是否能处理返回字段。

4. **验证元数据接口**  
   选取列表中返回的 `session_id`，请求对应详情接口，核对会话标识、元数据和 `product_surface` 的保存逻辑。

5. **验证转录接口**  
   请求同一会话的 messages 接口，确认消息内容能够进入审计、检索或归档流程。测试时应同时覆盖空会话、长会话和包含多种消息类型的真实响应结构；其中具体消息类型不能在没有官方 schema 支持的情况下预先编造。

6. **保留迁移前后对照**  
   对相同会话记录请求时间、响应状态、字段集合和下游入库结果。不要把“接口不再 beta”解释为响应结构、保留策略或所有产品面都发生了变化。

## Claude Science 和 Microsoft 365 的单独验证

这两类会话仍需按 beta 能力管理。企业在扩大采集范围前，应先确认自身确实是 Claude Enterprise organization，并在测试环境或受控范围内验证：

- 列表接口是否能返回 Claude Science 会话；
- `product_surface` 是否为 `claude_science`；
- Microsoft 365 会话是否覆盖 Excel、PowerPoint、Word 和 Outlook；
- Microsoft 365 返回值是否符合“以 `office_agents` 开头”的识别规则；
- 详情接口与 messages 接口是否都能沿用现有 Compliance Access Key 和 scope；
- 下游是否把 beta 会话与正式接口会话混为同一稳定性等级。

材料没有提供这些会话的额外开关、产品管理员配置或数据字段差异。接入方案中应把“需要组织侧配置”的部分列为待官方文档确认项，而不是凭经验补充。

## 实用检查清单

上线或迁移前，至少完成以下核对：

- [ ] 组织类型已确认是 Claude Enterprise。
- [ ] 使用的密钥类型已确认是 Compliance Access Key。
- [ ] 密钥包含 `read:compliance_user_data` scope。
- [ ] local sessions 列表接口调用成功。
- [ ] 详情接口可以读取列表返回的 `session_id`。
- [ ] messages 接口可以获取转录。
- [ ] Cowork 会话完成迁移后回归测试。
- [ ] Claude Code 会话完成迁移后回归测试。
- [ ] `claude_science` 被识别为 Claude Science 会话。
- [ ] `office_agents` 前缀识别逻辑已测试。
- [ ] 下游保存完整 `product_surface` 原值。
- [ ] beta 能力与已脱离 beta 的能力在监控和变更记录中分开标注。
- [ ] 未将材料未提供的请求参数、错误码或响应字段写死。

## 如何做最终判断

如果目标只是继续读取 Cowork 或 Claude Code 的会话转录，判断依据是：组织与密钥权限满足要求，三个接口的列表、详情和 messages 回归测试均通过，并且下游没有依赖未经确认的 beta 标记。

如果目标包括 Claude Science 或 Microsoft 365 会话，则还要增加 beta 能力评估：确认组织资格、验证具体 `product_surface` 返回值，并为字段变化和接口状态变化保留监控。当前资料支持的是“可以按官方说明进行验证和接入”，不支持宣称这些本地会话能力已经全面正式上线。

## 官方一手来源

- https://platform.claude.com/docs/en/release-notes/overview#august-26-2026

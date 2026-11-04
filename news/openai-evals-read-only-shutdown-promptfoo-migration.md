---
layout: default
title: "OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些"
description: "OpenAI Evals 平台 2026-10-31 起只读、11-30 停用：按官方弃用页和迁移指南，说明要先保留哪些数据，如何用 Promptfoo 重建评测、对应 string_check/text_similarity/score_model/python 评分器，并用 OpenAI 兼容地址运行与验收。"
permalink: /news/openai-evals-read-only-shutdown-promptfoo-migration/
date: 2026-11-01
---

> 更新日期：2026-11-01 · 一手来源：[OpenAI 弃用页](https://developers.openai.com/api/docs/deprecations)

# OpenAI Evals 10 月 31 日起只读、11 月 30 日停用：评测迁到 Promptfoo 要改哪些

先说结论：OpenAI 已经宣布弃用 Evals 平台。按官方弃用页，**2026 年 10 月 31 日起现有评测变为只读**，**11 月 30 日 Evals 控制台和 API 计划停用**；为评测流程写的 graders（评分器）也在这次调整范围内。官方给的迁移方向是开源命令行工具 Promptfoo，迁移指南写明**不依赖 Evals 导出功能**，也就是要你自己把数据、提示词和评分规则搬到 Promptfoo 的配置文件里重建。

本文适用于：用 `POST /v1/evals`、`/v1/evals/<id>/runs` 跑过评测，或在控制台里建过 Evals、打算在 11 月 30 日前迁走的开发者。依据：

- OpenAI 弃用页（Evals platform 一条）：https://developers.openai.com/api/docs/deprecations
- 官方迁移指南《Moving from OpenAI Evals to Promptfoo》：https://developers.openai.com/cookbook/examples/evaluation/moving-from-openai-evals-to-promptfoo
- OpenAI Evals 指南与 Graders 指南（页首都有弃用提示）
- Promptfoo 官方文档：安装、OpenAI 提供方、断言类型、测试用例

## 时间线与影响范围

| 日期 | 官方说法 | 对你的影响 |
|---|---|---|
| 2026-06-03 | 邮件通知 Evals 用户产品将弃用 | 开始规划迁移 |
| 2026-10-31 | 现有用户的评测变为只读 | 已有评测内容在过渡期内仍可查看，但不要再指望在 Evals 里继续迭代 |
| 2026-11-30 | Evals 控制台和 API 计划停用 | 还在调用 Evals 接口的脚本、CI 任务会失效 |
| 同步 | 评测流程里的 graders 一并调整 | 评分规则要在新工具里重建 |

注意两点：官方没有公布只读期间具体哪些接口会返回什么报错；弃用页也没有给数据导出方法。所以下面的做法以“趁还能看，先把东西抄下来，再重建”为主。

## 先判断你属于哪种情况

| 现状 | 建议做法 |
|---|---|
| 只在控制台里偶尔看过评测结果 | 记下关键评测的通过率作为基线，按第四节重建即可 |
| CI 或定时任务里调用 Evals API | 先停掉或改成 Promptfoo 命令，避免 11 月 30 日后整条流水线报错 |
| 用了 score_model 等模型打分 | 重建后必须先人工抽查打分是否合理，再用于上线判断 |
| 用了 graders 做强化微调 | 微调有单独的时间表（2027-01-06 起现有客户也不能新建微调任务），另行评估 |

## 第一步：趁只读期把要保留的东西记下来

迁移指南的思路是“重建”而不是“导出”，所以停用前请整理好这四样：

1. **测试数据**：你上传时用的 JSONL 原件（`purpose="evals"`）。官方示例里每行把字段包在 `item` 对象里，例如 `ticket_text`、`correct_label`。本地没有备份的，尽快整理出来。
2. **提示词模板**：运行配置里 `input_messages` 的 `template`（各条 `role`、`content`），以及里面引用了哪些数据字段。
3. **评分规则**：`testing_criteria` 里每个评分器的 `type`、`operation`、`reference`、`pass_threshold` 等。
4. **基线结果**：最近一次运行的 `result_counts`（`total`、`passed`、`failed`、`errored`）和 `report_url`。官方指南给出了查询运行状态的接口 `GET /v1/evals/<eval_id>/runs/<run_id>`。

## 第二步：安装 Promptfoo 并生成配置

按 Promptfoo 安装文档，需要 **Node.js 22.22.0 或更新版本**（推荐 Node.js 24 LTS），下面三种方式任选一种（npm 全局安装、npx 直接运行、Homebrew）：

```bash
npm install -g promptfoo
npx promptfoo@latest
brew install promptfoo
```

然后执行 `promptfoo init`（用 npx 时是 `npx promptfoo@latest init`），按向导生成 `promptfooconfig.yaml`。配置文件主要由 `prompts`（提示词）、`providers`（调用哪个模型）、`tests`（测试用例）、`defaultTest`（所有用例共用的断言和选项）组成。

## 第三步：把数据和提示词搬过去

- **数据**：Promptfoo 支持 JSONL，一行一个用例，每行用 `vars` 放变量、`assert` 放断言，例如 `{"vars": {"x": 5}, "assert": [{"type": "equals", "value": "8"}]}`。把原来每行 `item` 里的字段挪到 `vars` 里即可；也可以用 CSV，列名自动成为变量，`__expected` 列写断言（不写类型前缀时默认是 `equals`）。测试文件用 `tests: file://tests.yaml` 或 `tests: file://test_cases.csv` 这样的写法引用。
- **提示词**：Evals 里引用数据字段的写法是“item.字段名”放在双花括号里；Promptfoo 同样用双花括号，但直接写变量名本身（不带 `item.` 前缀）。
- **模型输出**：Evals 评分器里用“sample.output_text”指代模型输出；Promptfoo 的断言默认就是对模型输出做检查，不需要再写这个引用。

## 第四步：评分器怎么对应

迁移指南只说“把 grader 重建成 Promptfoo 的 assertion 并验证行为”，没有逐项对照。下表是按两边官方文档对各类型的定义整理的，迁移后都要验证：

| OpenAI 评分器 | Promptfoo 断言 | 说明 |
|---|---|---|
| `string_check` 的 `eq` | `equals` | 完全相等 |
| `string_check` 的 `ne`（文档正文写作 `neq`） | `not-equals` | Promptfoo 的任何断言都可加 `not-` 前缀取反 |
| `string_check` 的 `like` / `ilike` | `contains` / `icontains` | 包含参考文本；`i` 版本不区分大小写 |
| `text_similarity` 的 `bleu`、`gleu`、`meteor` | `bleu`、`gleu`、`meteor` | 默认阈值 0.5，可用 `threshold` 改 |
| `text_similarity` 的 `rouge_l` | `rouge-l` | 默认阈值 0.75 |
| `text_similarity` 的 `cosine` | `similar` | 都是向量余弦相似度，但嵌入模型可能不同，分数不一定一致 |
| `text_similarity` 的 `fuzzy_match` | 无同名断言 | 可改用 `levenshtein`（编辑距离）或代码断言，算法不同，需重新定阈值 |
| `score_model` | `llm-rubric` | Promptfoo 分数是 0～1；原来用了别的 `range` 要换算阈值 |
| `python`（`grade(sample, item)`） | `python`（`get_assert(output, context)`） | 原 `item` 字段改从 `context["vars"]` 取；可返回布尔、分数或含 `pass`、`score`、`reason` 的字典 |

迁移指南特别提醒：基于相似度的打分**在不同系统间不一定得到相同的数值**；用模型当裁判的评分器尤其要先验证，再用于回归判断。

## 用 OpenAI 兼容地址跑评测

Promptfoo 的提供方写成 `openai:chat:<模型>` 或 `openai:responses:<模型>`。如果模型不走 OpenAI 官方，而是走 OpenAI 兼容网关，Promptfoo 文档给的写法是 `apiBaseUrl` 加 `apiKeyEnvar`：

```yaml
providers:
  - id: openai:chat:gpt-6-luna
    config:
      apiBaseUrl: https://api.openlux.ai/v1
      apiKeyEnvar: OPENLUX_API_KEY
defaultTest:
  options:
    provider:
      id: openai:chat:gpt-6-luna
      config:
        apiBaseUrl: https://api.openlux.ai/v1
        apiKeyEnvar: OPENLUX_API_KEY
```

要点：`apiBaseUrl` 要带 `/v1`，但不要带 `/chat/completions` 或 `/responses`，Promptfoo 会自己补；模型名照网关列出的 ID 原样写；**上面 `providers` 的设置不会自动用于 `llm-rubric` 这类模型打分断言**，所以要在 `defaultTest.options.provider` 里再配一遍。示例里的地址和模型是 OpenLux 的，换成别的网关时按它的文档改。

## 运行与验收

1. 先确认网关地址和 Key 都对：带上 Key 请求 `https://api.openlux.ai/v1/models`，能列出模型就说明没问题。
2. 校验配置：`promptfoo validate config -c promptfooconfig.yaml`，没有报错再往下走。
3. 运行：`promptfoo eval -c promptfooconfig.yaml --no-cache`。
4. 查看：`promptfoo view` 在本地打开结果页面，逐条看失败用例。
5. 对照基线：拿第一步记下的 `result_counts` 比较。精确匹配类断言的通过情况应能逐条解释；相似度和模型打分类的差异，要抽查样本确认是阈值问题还是规则写错。迁移指南也提醒，Promptfoo 每次运行都是全新的，和旧的 Evals 运行记录没有关联。

验收标准：配置校验通过、评测完整跑完、失败用例都能说清原因，然后再把命令接进 CI，替换原来调用 Evals API 的步骤。

## 常见报错与排查

| 现象 | 原因 | 处理 |
|---|---|---|
| 401 | Key 错，或 `apiKeyEnvar` 指定的环境变量没设置 | 按 Promptfoo 文档，这个变量缺失时**不会**回退到 `OPENAI_API_KEY`，要确认变量名和值 |
| 404，路径里出现两个 `/v1` | `apiBaseUrl` 末尾的 `/v1` 和请求路径重复了 | 只保留一处 `/v1` |
| 模型打分断言报鉴权错误或没走网关 | 只配了 `providers`，没配打分模型 | 在 `defaultTest.options.provider` 里设置 |
| 相似度分数和旧评测对不上 | 两边算法或嵌入模型不同 | 重新定阈值，不要直接照搬旧分数 |
| 改完配置一跑就报错 | 可能是 YAML 结构或断言类型写错 | 先跑 `promptfoo validate config` 定位 |

## 小结

11 月 30 日前要做的是：抄下数据、提示词、评分规则和基线结果，用 Promptfoo 重建评测，并把 CI 里的 Evals 调用换掉。评测要调用的模型可以继续走 OpenAI 兼容地址，只需在 `providers` 和 `defaultTest.options.provider` 两处配好地址和 Key。

想用一个 Key 调用 GPT、Claude、Gemini 等模型跑评测，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-evals-read-only-shutdown-promptfoo-migration&utm_content=footer)，价格以官网价格页为准。

## 同专题文章

- [OpenAI API 报 401 Incorrect API key provided 怎么办：Key 写错、项目不对、已撤销与 Base URL 指错逐项排查](https://a37836323.github.io/openlux-api-guides/news/openai-api-401-incorrect-api-key-fix/)
- [OpenAI Responses API 返回 status: incomplete、只有推理没有正文：max_output_tokens 被推理用光怎么办](https://a37836323.github.io/openlux-api-guides/news/openai-responses-incomplete-max-output-tokens-fix/)
- [OpenAI Agent Builder 将于 11 月 30 日停用：工作流导出成 Agents SDK、ChatKit 改自托管，换 Base URL 后报 404/401/400 怎么改](https://a37836323.github.io/openlux-api-guides/news/agent-builder-shutdown-agents-sdk-chatkit-migration/)
- [gpt-realtime 将于 2027 年 1 月 20 日下线：换成 gpt-realtime-2.1 后说完「我查一下」就沉默、话说一半停住怎么办](https://a37836323.github.io/openlux-api-guides/news/gpt-realtime-shutdown-gpt-realtime-2-1-silence-fix/)
- [whisper-1 将于 2027 年 2 月 26 日下线：换成 gpt-transcribe 要改哪些参数（language、时间戳、字幕格式）](https://a37836323.github.io/openlux-api-guides/news/whisper-1-shutdown-gpt-transcribe-migration/)
- [gpt-audio、gpt-audio-mini 将于 2027 年 1 月 20 日下线：换成 gpt-audio-1.5 要改哪些](https://a37836323.github.io/openlux-api-guides/news/gpt-audio-mini-shutdown-gpt-audio-1-5-migration/)

[查看「OpenAI API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/openai-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

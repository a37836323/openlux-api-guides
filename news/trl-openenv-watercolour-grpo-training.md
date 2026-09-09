---
layout: default
title: "用 TRL 与 OpenEnv 部署自定义视觉奖励 GRPO：配置与排错要点"
description: "基于 HF Jobs、Spaces 和 Inference Providers 复现代码生成模型的自定义奖励 GRPO 训练，并避开 MoE LoRA 配置陷阱。"
permalink: /news/trl-openenv-watercolour-grpo-training/
date: 2026-09-09
---

> 更新日期：2026-09-09 · 一手来源：[Hugging Face Blog](https://huggingface.co/blog/train-to-paint-with-code)

# 用 TRL 与 OpenEnv 部署自定义视觉奖励 GRPO：配置与排错要点

**结论先行：**如果你要用 TRL、OpenEnv 和 Hugging Face Jobs 训练一个“模型写代码—浏览器渲染—视觉模型评分”的 GRPO 任务，重点不只是把训练命令跑起来，而是同时处理好环境 gate、奖励混合、参考池设计，以及 MoE 模型的 LoRA 覆盖范围。针对官方示例中的 `Qwen/Qwen3.5-35B-A3B`，手工指定常见 `target_modules` 可能只覆盖 40 层中的 10 层；官方文章采用 `all-linear` 后，LoRA 可覆盖各线性层，训练才出现学习信号。

本文适合准备复现官方水彩绘画示例，或将其改造成自定义审美、偏好评分、浏览器交互等强化学习环境的工程人员。

## 一、官方方案的组件边界：训练、环境与奖励分开部署

**官方发布事实：**Hugging Face 于 2026 年 9 月 3 日发布了该方案，并公开参考池数据集、RL 环境、训练脚本、已训练模型和代码仓库。文章描述的流程可在 Hugging Face 平台上端到端运行：

- 使用 **Hugging Face Jobs** 启动训练；
- 使用 **OpenEnv** 承载强化学习环境；
- 将 RL 环境和评分模型部署为 **Spaces**；
- 通过 **Inference Providers** 调用视觉评审模型；
- 将训练产物保存到 Hub。

这一拆分方式对自定义奖励环境尤其重要。训练器不应直接承担浏览器渲染、JavaScript 执行和反作弊校验；这些工作应放进环境端。训练器负责生成候选代码、接收环境返回的奖励，再由 GRPO 更新策略。

## 二、环境设计：浏览器渲染不是奖励函数的附属品

**官方发布事实：**示例环境使用 `p5.brush`、无头 Chromium、系统提示约束和反作弊 gate。模型输出 JavaScript，通过浏览器实际渲染后再评分。

环境的 gate 至少承担四类判断：

1. 代码是否能编译并执行；
2. 是否确实使用指定绘图库；
3. 是否在画布上产生有效绘制；
4. 是否试图通过文本或其他方式干扰评分器。

官方示例还把模型可调用的 `p5.brush` 方法限制为 10 个。这样的 allowlist 不只是安全控制，也是风格约束：模型只能通过有限的填充、形状和笔刷相关能力作画，不能随意调用更多 API 改变任务目标。

| 环节 | 官方示例中的实现 | 工程上应验证的问题 |
|---|---|---|
| 策略输出 | 生成 JavaScript 绘画代码 | 输出格式是否稳定、是否有最大长度限制 |
| 执行环境 | 无头 Chromium 渲染 | 超时、崩溃、空白画布如何处理 |
| API 约束 | `p5.brush` 方法白名单，共 10 个 | 是否允许了绕过预期风格的调用 |
| 反作弊 gate | 编译、绘制、库调用和作弊检查 | gate 拒绝时是否返回明确且可观测的结果 |
| 视觉奖励 | 成对评审与 HPSv3 | 图像、文本描述、参考图是否对齐 |
| 训练更新 | TRL 的 GRPOTrainer | 奖励缩放与 LoRA 覆盖是否正确 |

**作者建议：**先单独验证环境，再启动完整 GRPO。具体来说，手工提交几段“正常绘制”“无法编译”“空白画布”“画布文字”等代码，确认 gate 的接受与拒绝行为符合预期。否则，训练曲线不动时，你很难判断问题来自模型、奖励模型，还是浏览器执行层。

## 三、奖励设计：把“能运行”和“审美偏好”分层处理

**官方发布事实：**该示例的总奖励由四项组成：

- 编译与反作弊 gate：权重 0.05；
- 代码长度：权重 0.05；
- 基于 Inference Providers 调用 `Qwen3-VL-30B-A3B-Instruct` 的成对评审：权重 0.60；
- HPSv3：权重 0.30。

其中，成对评审会把候选绘画与从参考池随机抽取的图像进行比较；HPSv3 则对渲染图和文本描述给出偏好分数。前者更接近“是否符合你定义的参考风格”，后者更接近通用视觉偏好代理。

需要注意的是，视觉奖励并非客观正确答案。参考池中的作品、分层规则和抽样策略，都会进入策略优化目标。

**官方发布事实：**文章的参考池包含 178 张绘画，并分为两个偏好层级。成对评审抽取四张参考图时，一半来自较高偏好层级，一半来自另一层级。文章指出，参考池会决定模型最终学习到的风格和输出多样性。

**作者建议：**自定义审美奖励前，优先审查参考池，而不是急于调整权重。可用以下问题做筛选：

- 参考图是否只集中于单一主题、构图或色彩；
- 高偏好与一般偏好样本的边界是否一致；
- 是否包含你希望模型保留的多样性；
- 参考池是否混入与目标风格不相符、但视觉模型可能偏爱的图像；
- 评审提示词是否明确说明比较标准，而不是只要求“选更好的一张”。

如果池子只奖励一种花、一种构图或一种笔触，GRPO 会倾向于收缩到该分布附近；这是奖励定义的结果，不应误判为训练器故障。

## 四、MoE 模型 LoRA：先检查适配器到底覆盖了哪里

**官方发布事实：**在 `Qwen/Qwen3.5-35B-A3B` 上，作者发现常见的手工 `target_modules` 列表仅训练到 40 层中的 10 层。原因是该 MoE 架构中许多投影层的命名不同于常见稠密模型。改为 `all-linear` 后，LoRA 能覆盖每个线性层，训练才开始学习。

官方示例使用的关键开关包括：

```bash
--model Qwen/Qwen3.5-35B-A3B \
--lora \
--all-linear \
--bf16 \
--gradient-checkpointing
```

这里的关键不是盲目把所有层都设为可训练，而是确认 LoRA 实际挂载到了预期模块。官方文章同时说明：该架构中的 routed experts 为融合张量，`all-linear` 也不会使其全部变为可训练；但其余线性层获得适配器已足以让示例训练出现学习。

**作者建议：**不要只看命令行是否带了 `--lora`。启动训练前后都应检查：

- LoRA 注入模块总数；
- 各层覆盖情况，尤其是 MoE block；
- 可训练参数数量是否符合预期；
- 是否出现“只有少数层有 adapter”的情况；
- 修改 `target_modules` 后，训练参数统计是否实际变化。

## 五、奖励曲线不学习时，按四项配置逐一排查

**官方发布事实：**作者将成功运行与失败配置对比后，列出了四项关键变化：

| 配置项 | 失败配置 | 官方成功配置 |
|---|---|---|
| 学习率 | `2e-5` | `5e-5` |
| 学习率调度器 | `linear` | `constant_with_warmup` |
| `scale_rewards` | `group` | `none` |
| LoRA 目标模块 | 手工列表 | `all-linear` |

官方文章的解释是：较低学习率不足以推动学习；线性衰减会使学习率在训练中段明显下降；当一个样本被 gate 拒绝时，按组缩放奖励可能压低同组其他样本的优势；而手工 LoRA 模块列表无法充分覆盖该 MoE 模型。

官方给出的启动命令包含以下核心参数，适合作为初始基线：

```bash
hf jobs uv run train/watercolour_grpo.py --flavor h200 --timeout 48h --secrets HF_TOKEN -- \
  --env-url https://<you>-watercolour-env.hf.space \
  --model Qwen/Qwen3.5-35B-A3B \
  --lora --all-linear --bf16 --gradient-checkpointing \
  --lr 5e-5 \
  --lr-scheduler constant_with_warmup \
  --warmup-steps 5 \
  --scale-rewards none \
  --steps 110 \
  --n-episodes 240 \
  --num-generations 8 \
  --per-device-batch-size 1 \
  --gradient-accumulation-steps 8 \
  --max-completion-length 8192 \
  --run-tag my-run \
  --out <you>/watercolour-grpo \
  --push-to-hub
```

其中 `<you>`、环境 URL、输出 Hub 仓库和训练主题需要替换为你的配置。

## 六、从复制示例到自定义任务的迁移步骤

建议按“先缩小、再加复杂度”的顺序迁移，而不是一开始就加入浏览器、多个视觉评审器和复杂奖励混合。

1. **复制两个 Space。**复制官方提供的环境 Space 和评分模型 Space。  
2. **配置奖励混合。**按文章要求设置两个与奖励混合有关的环境变量；变量名和具体取值应以官方仓库说明为准。  
3. **确认环境 URL。**将训练命令中的 `--env-url` 改为你自己的环境 Space 地址。  
4. **做环境单测。**检查正常代码、失败代码、空白输出和作弊尝试是否得到预期 gate 结果。  
5. **先跑小规模控制任务。**先减少主题复杂度或奖励项，确认奖励能随训练变化，再恢复浏览器和视觉评审。  
6. **检查 LoRA 覆盖。**对文中所用 MoE 模型，优先使用并核查 `all-linear`。  
7. **固定四项训练基线。**先使用 `5e-5`、`constant_with_warmup`、`scale_rewards=none` 和 `all-linear`，再逐项做消融。  
8. **审查参考池。**在改变视觉模型或奖励权重之前，确认池子的主题、风格和偏好标注能代表你真正想优化的输出。  

## 七、上线前检查清单

- [ ] 环境 Space 与评分模型 Space 均已复制并可访问  
- [ ] 两个奖励混合环境变量已按官方说明设置  
- [ ] `--env-url` 指向自己的环境地址  
- [ ] 无头 Chromium 能稳定渲染有效输出  
- [ ] gate 能拒绝编译失败、无绘制和违规输出  
- [ ] 视觉评审输入包含正确的渲染图、描述和参考图  
- [ ] 参考池覆盖目标风格所需的主题与多样性  
- [ ] Qwen3.5-35B-A3B 的 LoRA 使用 `--all-linear`，并已确认覆盖范围  
- [ ] 学习率、调度器和奖励缩放与官方成功基线一致  
- [ ] 输出仓库、运行标签和 Hub 推送权限已配置  

如需建立用于相关工作流的 API 凭据，可通过 OpenLux 的[注册并创建 API Key](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=trl-openenv-watercolour-grpo-training&utm_content=footer)。

## 官方一手来源

- https://huggingface.co/blog/train-to-paint-with-code

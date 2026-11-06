---
layout: default
title: "Cosmos3-Sim-Bimanual 如何用 vLLM-Omni 推理？59 个动作控制值怎么补齐、如何与输入帧对齐？"
description: "说明 Cosmos3-Sim-Bimanual 的动作序列、帧数对齐与部署前提，并区分已验证环境和最低硬件要求。"
permalink: /news/cosmos3-sim-bimanual-vllm-omni-inference/
date: 2026-11-07
---

> 更新日期：2026-11-07 · 一手来源：[Hugging Face Blog](https://huggingface.co/blog/nvidia/cosmos-interactive-world-simulation)

# Cosmos3-Sim-Bimanual 如何用 vLLM-Omni 推理？59 个动作控制值怎么补齐、如何与输入帧对齐？

先给结论：用 vLLM-Omni 跑 Cosmos3-Nano-Sim-Bimanual 时，**客户端只需要提交已经归一化的 59 维动作，不用自己补到 64**——官方 notebook 写明「the server pads actions to 64 channels」，补的是索引 59～63 共 5 个 0。帧数要比动作行数多 1（T 行动作对应 T+1 帧），并且动作行数要能被检查点的时间压缩系数整除（官方推理说明写的是能被 4 整除）。发布的推理动作已经归一化，不要再做一次训练归一化。服务端需要 Linux、一块 NVIDIA GPU、Docker 和 NVIDIA Container Toolkit；官方提到的单台 GB200 只是测试配置，不是最低显存要求。

这篇适合正在把双臂机器人或仿真动作流接到 Cosmos3-Nano-Sim-Bimanual 的开发者。注意它是根据给定动作**预测视频**的模型，官方 notebook 原话是「it does not choose robot actions」，不会替你生成机器人动作。

## 先分清三类信息

**官方发布事实：** [Hugging Face 官方文章](https://huggingface.co/blog/nvidia/cosmos-interactive-world-simulation)介绍了 Cosmos 3 新增的四个开放权重检查点，其中 Cosmos3-Nano-Sim-Bimanual 支持 YAM 和 AgiBot 双臂机器人，从一张图开始，按机器人动作或相机动作生成后续画面。动作格式、补齐和帧数规则出自 NVIDIA cosmos-framework 仓库里的 vLLM-Omni notebook、推理说明和 unified v1 动作 schema（链接见文末）。

**OpenLux 相关：** 本文讲的是官方自部署流程，不涉及 OpenLux 是否提供这个模型。

**作者建议：** 把输入校验拆成动作结构、动作长度、时间对齐和归一化四项，逐项通过后再跑短样本；短样本跑通只说明流程通了，不说明生成质量。

## 59 个值是什么，64 由谁补？

unified v1 动作 schema 规定原始规范向量是 59 个值，字段布局如下：

| 索引 | 含义 |
|---|---|
| 0～8 | 自身（ego）平移 + rot6d 旋转 |
| 9～17 | 右手腕平移 + rot6d |
| 18～32 | 右手五个指尖 xyz |
| 33 | `right_openness`（右夹爪开合） |
| 34～42 | 左手腕平移 + rot6d |
| 43～57 | 左手五个指尖 xyz |
| 58 | `left_openness`（左夹爪开合） |
| 59～63 | 补齐位，固定为 0（由服务端追加） |

几个容易弄错的点，均来自 schema 原文：

1. rot6d 存的是旋转矩阵的**前两列**，不是前两行；单位旋转是 `[1, 0, 0, 0, 1, 0]`。
2. 缺失的字段必须填 0 并在有效掩码里标为无效；测出来恰好是 0 的值仍然是有效的。
3. 64 维掩码 = 59 维有效掩码 + 5 个 `false`。无效维和补齐维（59～63）是两回事，但取值都必须严格为 0。
4. 不同控制域的有效索引不同：`agibotworld` 和 `behavior1k_lerobot` 是 0～17、33、34～42、58；`xdof_yam` 没有 ego，是 9～17、33、34～42、58。指尖位只对自定义适配器有效。

所以「怎么补齐」的答案是：**不要自己补**。官方 notebook 的校验函数要求 `raw_action_dim` 和检查点的 `action_dim` 都等于 59，动作数组形状必须是 `(T, 59)` 且全部是有限值；你如果自己补到 64 再发，这一步就会报「Expected ... finite 59D actions」。

## 动作序列怎样与输入帧对齐？

官方文章原话是「T transitions need T+1 observations」。推理说明和 notebook 把它落到了请求参数上：

| 参数 | 要求 | 不满足时的报错或现象 |
|---|---|---|
| `action_chunk_size` | 等于 T，且为正数 | `action_chunk_size must equal num_frames - 1 and be positive` |
| `num_frames` | 等于 T+1 | 同上 |
| 动作行数 T | 能被检查点的 `temporal_compression_factor` 整除（推理说明写为能被 4 整除） | `Action count must align with the checkpoint's temporal compression factor` |
| 动作维度 | 每行 59 个已归一化的有限值 | `Expected 59D action rows matching the checkpoint` |
| `domain_names` | 每行一个控制域，或整段一个 | `Supply one domain name per action, or one scalar domain name` |
| `fps` | 正的有限数，与动作对齐 | `fps must be positive and finite` |

官方示例默认是 900 行动作、901 帧、30 FPS；推理说明强调这只是示例长度，不是模型上限，自己的轨迹可以换别的对齐长度，但两个长度字段都要在 manifest 里写好，命令不会替你改。schema 里还规定第 i 行动作对应第 i+1 帧观测。

帧和动作对不上时，先查切片边界和采样逻辑，确认初始观测单独保留，不要在推理端临时补帧或删动作。

## 已归一化的动作不要重复处理

官方文章说明「released inference actions are already normalized」，推理说明也写了「Do not apply training normalization again」。schema 给出的归一化公式是 `y = asinh((x - offset) / scale) / asinh(1)`，统计量文件固定、带 SHA-256 校验，官方要求做规范复现时不要自己重算或替换。

因此要在数据管线里标清动作来源：直接用官方发布的推理动作时，关掉归一化步骤；用自己的原始采集数据时，按官方数据契约和 schema 的规定转换一次，并同时核对时间戳、控制域、单位、夹爪标定和位姿约定，不能只看张量宽度对不对。

## vLLM-Omni 部署前检查什么？

官方 notebook 列出的服务端前提是：Linux、一块 NVIDIA GPU、Docker 加 NVIDIA Container Toolkit，以及能访问 `nvidia/Cosmos3-Nano-Sim-Bimanual` 的 Hugging Face 账号（容器里要能拿到 `HF_TOKEN`）。客户端需要 Python 3.10 以上和 FFmpeg/FFprobe。

- [ ] 拉取官方镜像 `vllm/vllm-omni:cosmos3`。
- [ ] 用 `hf download` 下载检查点，服务端和客户端使用同一个 `COSMOS3_MODEL_REVISION`。
- [ ] 按 notebook 的 `vllm serve` 命令启动（含 `--omni`、`--model-class-name Cosmos3NanoSimBimanualPipeline` 和对应的 deploy 配置），等待 `/v1/models` 里出现 `nvidia/Cosmos3-Nano-Sim-Bimanual`。
- [ ] 请求走同步视频接口 `/v1/videos/sync`，图片放 `input_reference`，动作放在 `extra_params` 里。
- [ ] `extra_params` 序列化后超过 1 MiB 会被服务端的表单字段上限挡住，长轨迹要相应调整服务端配置。

官方示例命令通过 `"guardrails":false` 关闭了安全护栏，notebook 提醒在其他应用里要按自己的部署策略开启。

## 从样本到正式运行的验证步骤

1. **先跑官方示例。** 用 notebook 里的两个已发布 manifest（unified 动作和混合控制域各一个），确认环境能出视频。
2. **校验输入。** 按上面的表核对 59 维、T 与 T+1、整除 4、控制域和 fps。
3. **核对数值处理。** 确认动作只归一化过一次，掩码与零值规则正确。
4. **检查输出。** notebook 用 ffprobe 核对输出视频的帧数、FPS 和分辨率与 manifest 一致，并完整解码一遍；长视频要看前、中、后段有没有冻结帧、跳变或与动作不符。
5. **再扩大任务。** 保存输入版本、检查点版本和日志，便于区分 schema 错误、时序错误与部署问题。

## 判断是否可以继续

动作字段含义可追溯、提交的是 59 维已归一化动作、`num_frames = action_chunk_size + 1` 且动作行数整除 4、服务端环境满足官方前提——这几项都过了，再推进更长的推理或后训练。官方文章还建议正式训练前先验证样本、测试训练和断点恢复，并在留出的 episode 上评估质量：短运行成功只说明流程执行，不代表模型已经收敛。

如需通过 OpenLux 调用其他大模型 API，可[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=cosmos3-sim-bimanual-vllm-omni-inference&utm_content=footer)。

## 官方一手来源

- Hugging Face Blog，NVIDIA Cosmos 3 开放模型文章：https://huggingface.co/blog/nvidia/cosmos-interactive-world-simulation
- vLLM-Omni 运行 Cosmos3-Nano-Sim-Bimanual 的官方 notebook：https://github.com/NVIDIA/cosmos-framework/blob/main/.agents/skills/cookbooks/cosmos3/simulation/bimanual/run_bimanual_with_vllm_omni.ipynb
- 推理说明：https://github.com/NVIDIA/cosmos-framework/blob/main/.agents/skills/cosmos3-nano-sim-bimanual/inference/SKILL.md
- unified v1 动作 schema：https://github.com/NVIDIA/cosmos-framework/blob/main/.agents/skills/cosmos3-nano-sim-bimanual/post-training/references/unified-v1-action-schema.md

## 同专题文章

- [Transformers 如何调用 Phonon TTS？先核对模型许可和版本](https://a37836323.github.io/openlux-api-guides/news/hugging-face-phonon-transformers-integration/)
- [grok-imagine-image-quality 11 月 2 日退役：请求会转到 grok-imagine-image-2.0 的 low 档，要不要改 model 和 quality](https://a37836323.github.io/openlux-api-guides/news/grok-imagine-image-quality-retirement-image-2-0-migration/)
- [Transformers 模型能在 AWS Trainium2 上运行吗？torch-neuronx 编译失败或首次运行过慢怎么排查](https://a37836323.github.io/openlux-api-guides/news/check-transformers-model-trainium-support/)
- [Pinecone 报 Vector dimension does not match 怎么办？](https://a37836323.github.io/openlux-api-guides/news/pinecone-vector-dimension-mismatch-fix/)
- [API 用量和账单为什么对不上：时间窗口、计费单位与重试记录核对](https://a37836323.github.io/openlux-api-guides/news/api-usage-billing-reconciliation-workflow/)
- [工具调用返回了参数却执行失败：函数名、字段和业务范围怎么校验](https://a37836323.github.io/openlux-api-guides/news/tool-call-arguments-validation-contract/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

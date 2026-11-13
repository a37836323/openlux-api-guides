---
layout: default
title: "如何用 Hugging Face Jobs 微调 TRELLIS.2？遇到“需要 HF_TOKEN 和 DINOv3 权限”怎么处理"
description: "Hugging Face 发布 TRELLIS.2 LoRA 微调流程，涵盖数据预处理、Jobs 或 Docker 运行、ss 与 shape 训练配置及必要权限。"
permalink: /news/how-to-finetune-trellis2-with-hugging-face-jobs/
date: 2026-11-13
---

> 更新日期：2026-11-13 · 一手来源：[Hugging Face Blog](https://huggingface.co/blog/3d-lora-finetuning)

# 如何用 Hugging Face Jobs 微调 TRELLIS.2？遇到“需要 HF_TOKEN 和 DINOv3 权限”怎么处理

如果你准备用 Hugging Face Jobs 或本地 Docker 为 TRELLIS.2 训练 LoRA，官方指南列出的前置条件有两项：一个 `HF_TOKEN`，以及 Hugging Face 账户对 DINOv3 的访问权限（DINOv3 是 gated 模型，要单独申请）。用自有数据时，还要先把网格上传到 Hub。这两项都准备好之后，再按“预处理 → 训练 `ss` 或 `shape` 分支”的顺序跑。

本文适合想用自有 GLB、OBJ 网格做 3D 微调的开发者，也适合需要判断该训练 TRELLIS.2 结构分支还是形状分支的读者。事实部分来自 Hugging Face 2026 年 11 月 12 日发布的官方博客 [Fine-Tuning TRELLIS.2](https://huggingface.co/blog/3d-lora-finetuning)，作者自己的建议会单独标出。

## 先理解：TRELLIS.2 的 LoRA 训练改了什么

官方指南不是完整微调整个 TRELLIS.2，而是只给两个 DiT 加 LoRA：

- `Sparse-Structure Flow DiT`：生成 16³×8 的潜变量，再由 VAE 解码成 64³ 的占用网格，也就是对象的粗结构；
- `Shape Flow DiT`：解码成 512³ 的 O-Voxel 几何，负责更细的形状；
- `Texture Flow DiT`：输出基础色、金属度、粗糙度和透明度并导出 GLB，这一级保持冻结。

示例任务用的是 Google Scanned Objects（GSO）里的 188 个鞋类对象，留出 9 个做评估。原模型生成的鞋整体看起来没问题，但鞋底不对，所以只动结构和形状。官方给出的纹理冻结原因有三条：数据集的漫反射贴图里烘焙了光照；训练需要的 PBR 贴图缺失；在这些贴图上训练有灾难性遗忘的风险。官方原话的意思是：选择冻结什么，和选择微调什么同样重要。

LoRA 用 PEFT 实现，两个 DiT 合计约 930 万可训练参数：结构 DiT 在注意力和 MLP 层用 rank 8，形状 DiT 只在注意力层用 rank 16。所以这套流程适合改变某类对象的结构和几何特征，不是一个材质训练模板。

## 为什么需要 HF_TOKEN 和 DINOv3 权限

### HF_TOKEN

Token 在 [Hugging Face 设置页](https://huggingface.co/settings/tokens/new) 创建。按官方命令，容器要从 Hub 读取你上传的网格，把预处理得到的 latents 推到 `--push-to` 指定的仓库，训练时再把 LoRA checkpoint 推到另一个仓库，这些都要用到 Token。如果网格仓库或输出仓库是私有的，Token 还必须对它们有相应权限。

在 Jobs 里，官方用 `--secrets HF_TOKEN` 把它作为加密环境变量传进任务，不打进镜像；本地 Docker 用 `-e HF_TOKEN=...` 传入容器。

### DINOv3 权限

TRELLIS.2 先用 BiRefNet 去背景，再用 DINOv3-L 把输入图像编码成特征 token。DINOv3 是 gated 模型，官方要求账户先在 [DINOv3 模型合集](https://huggingface.co/collections/facebook/dinov3) 获得访问权限。

有 Token 不等于有 DINOv3 权限。如果 Token 已经设置好，任务仍然卡在下载或加载 DINOv3 上，先去合集页确认这个账户的访问申请是否已经通过，而不是去调训练参数。

## Hugging Face Jobs 的执行顺序

### 第一步：设置 Token 并上传网格

```bash
export HF_TOKEN=hf_xxx
```

把自己的 GLB 或 OBJ 上传到一个 Hub 仓库，例如 `your-username/my-meshes`。`your-username` 是占位符，换成你的用户名或组织名。

### 第二步：运行预处理

预处理在容器里用 Blender（通过 `xvfb-run` 无界面运行）给每个对象渲染 16 个视角，再跑 TRELLIS.2 的 data_toolkit 流程生成 latents。官方在 `a100-large` 上处理 188 个对象约用了 1 小时。

```bash
hf jobs run -d --flavor a100-large \
  --timeout 6h --secrets HF_TOKEN \
  cr.hf.co/suvadityamuk/trellis2-finetuning-prep:latest \
  trellis2-prep \
  --meshes your-username/my-meshes \
  --push-to your-username/my-meshes-trellis2 \
  --private --holdout 0.05 --views 16 --workers 8
```

参数说明：

| 参数 | 官方说明 |
|---|---|
| `-d` | 后台运行并打印 job ID，之后用 `hf jobs logs -f <id>` 看日志 |
| `--flavor a100-large` | 80 GB 显存的 GPU，全部规格用 `hf jobs hardware` 查看 |
| `--timeout` | 超时后重跑会续上：预处理跳过已完成的对象，训练从 `--push-to` 里最新的 checkpoint 继续 |
| `--secrets HF_TOKEN` | 以加密环境变量传入，不写进镜像 |
| `--holdout 0.05` | 留出一部分对象不参与训练，用于评估 |

### 第三步：选择训练分支

| `--config` | 微调对象 | 官方配置文件 |
|---|---|---|
| `ss` | Sparse-Structure Flow DiT（粗结构） | `ss_flow_lora_gso.json` |
| `shape` | Shape Flow DiT（细几何） | `slat_flow_img2shape_lora_gso.json` |
| 无 | Texture Flow DiT 保持冻结 | 不训练 |

作者建议（非官方结论）：整体结构不对时先看 `ss`；结构基本对、问题在几何细节时重点看 `shape`。官方示例两个分支都训练了。

### 第四步：训练 Sparse-Structure LoRA

```bash
hf jobs run -d --flavor a100-large \
  --timeout 12h --secrets HF_TOKEN \
  cr.hf.co/suvadityamuk/trellis2-finetuning-train:latest \
  trellis2-train --config ss \
  --latents your-username/my-meshes-trellis2 \
  --push-to your-username/my-trellis2-lora \
  --run-name ss_lora --push-path ss_lora \
  --trackio-space your-username/trellis2-trackio
```

### 第五步：训练 Shape LoRA

官方说明：shape 阶段把 `--config`、`--run-name`、`--push-path` 换成 shape，并加上 `--set max_steps=3000 i_save=500`。

```bash
hf jobs run -d --flavor a100-large \
  --timeout 12h --secrets HF_TOKEN \
  cr.hf.co/suvadityamuk/trellis2-finetuning-train:latest \
  trellis2-train --config shape \
  --latents your-username/my-meshes-trellis2 \
  --push-to your-username/my-trellis2-lora \
  --run-name shape_lora --push-path shape_lora \
  --trackio-space your-username/trellis2-trackio \
  --set max_steps=3000 i_save=500
```

训练指标记录到 Trackio。想先跳过预处理、用官方已处理好的数据试跑，可以把 `--latents` 换成 `suvadityamuk/gso-footwear-trellis2-latents`，`--push-to` 换成你自己的仓库，例如 `your-username/trellis2-footwear-lora`。

## 本地 Docker 怎么运行

不用 Jobs 时，官方提供了同样的两个镜像。预处理：

```bash
docker run --gpus all --rm --shm-size 16g -e HF_TOKEN=hf_xxx \
  -v hf-cache:/root/.cache/huggingface -v "$PWD/work":/workspace/work \
  cr.hf.co/suvadityamuk/trellis2-finetuning-prep:latest \
  trellis2-prep --meshes your-username/my-meshes \
  --push-to your-username/my-meshes-trellis2
```

训练时把镜像换成 `cr.hf.co/suvadityamuk/trellis2-finetuning-train:latest`，命令换成 `trellis2-train`，后面的参数和上面 Jobs 训练命令一样。官方在单张 A100 80 GB 上训练，ss 用了 7.2 小时，shape 用了 3.6 小时，本地显卡显存不足时更适合用 Jobs。

## 任务失败时按顺序排查

1. **Token 是否传进去了**：Jobs 命令里有没有 `--secrets HF_TOKEN`，本机是否先 `export` 过；Docker 有没有 `-e HF_TOKEN=...`。检查时只看变量是否为空，不要把 Token 打印到日志或截图里，更不要写进镜像或提交到代码仓库。
2. **DINOv3 权限是否已通过**：Token 正常但加载 DINOv3 失败，去 [DINOv3 模型合集](https://huggingface.co/collections/facebook/dinov3) 确认这个账户的访问申请状态。改训练步数或换 `--config` 解决不了权限问题。
3. **仓库名是否写对**：原始网格仓库、latents 仓库、LoRA 输出仓库、Trackio Space 名称都要换成你自己的，Token 对私有仓库要有读写权限。
4. **预处理是否完成**：训练读的是 `--latents` 指向的预处理结果，不是原始 GLB/OBJ。预处理超时就原命令重跑，会跳过已完成的对象。
5. **训练超时**：同样原命令重跑，会从 `--push-to` 里最新的 checkpoint 继续，不用从头训。
6. **分支是否选对**：`ss` 和 `shape` 对应不同 DiT、不同配置文件。目标是几何细节却只训了 `ss`，命令能跑完也未必解决问题。

## 怎么判断训练有效

官方用留出的 9 个对象比较原模型和 LoRA：

| 指标 | 原模型 | LoRA |
|---|---|---|
| F-score@0.02（越高越好） | 0.276 | 0.803 |
| Chamfer distance（越低越好） | 0.174 | 0.033 |
| Normal consistency（越高越好） | 0.530 | 0.804 |

9 个留出对象的 F-score 都有提升。训练好的 adapter 在 `suvadityamuk/trellis-2-finetune-gso`，完整代码在 [GitHub 仓库](https://github.com/suvadityamuk/trellis2-finetuning)。

这些数字只对应官方的鞋类数据集。迁移到自己的数据时，作者建议先用少量代表性对象把“上传 → 预处理 → 训练一个分支 → 推送 checkpoint”整条链路跑通，再用没参与训练的对象对比原模型和 LoRA 的结构、几何，同时留意原本生成得好的类别有没有变差。

## 结论

看到“需要 HF_TOKEN 和 DINOv3 权限”，按这个顺序处理：创建 Token 并用 `--secrets HF_TOKEN`（Jobs）或 `-e HF_TOKEN=...`（Docker）传入；在 DINOv3 合集页确认账户已获准访问；上传网格并运行 `trellis2-prep`；再按目标选择 `--config ss` 或 `--config shape` 训练，shape 阶段别漏了 `--set max_steps=3000 i_save=500`。Jobs 和本地 Docker 用的是同一套镜像，区别只在 GPU 资源和 Token 的传法。

## 官方来源

- Hugging Face 官方博客：https://huggingface.co/blog/3d-lora-finetuning
- 训练代码：https://github.com/suvadityamuk/trellis2-finetuning
- DINOv3 模型合集：https://huggingface.co/collections/facebook/dinov3

[注册并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=how-to-finetune-trellis2-with-hugging-face-jobs&utm_content=footer)

## 同专题文章

- [llama.cpp 升级 v1.0.0 会破坏 C API/ABI 吗？如何固定 libllama/libggml 版本并安排迁移](https://a37836323.github.io/openlux-api-guides/news/llama-cpp-v1-api-abi-migration/)
- [Cosmos3-Sim-Bimanual 如何用 vLLM-Omni 推理？59 个动作控制值怎么补齐、如何与输入帧对齐？](https://a37836323.github.io/openlux-api-guides/news/cosmos3-sim-bimanual-vllm-omni-inference/)
- [Transformers 如何调用 Phonon TTS？先核对模型许可和版本](https://a37836323.github.io/openlux-api-guides/news/hugging-face-phonon-transformers-integration/)
- [grok-imagine-image-quality 11 月 2 日退役：请求会转到 grok-imagine-image-2.0 的 low 档，要不要改 model 和 quality](https://a37836323.github.io/openlux-api-guides/news/grok-imagine-image-quality-retirement-image-2-0-migration/)
- [Transformers 模型能在 AWS Trainium2 上运行吗？torch-neuronx 编译失败或首次运行过慢怎么排查](https://a37836323.github.io/openlux-api-guides/news/check-transformers-model-trainium-support/)
- [Pinecone 报 Vector dimension does not match 怎么办？](https://a37836323.github.io/openlux-api-guides/news/pinecone-vector-dimension-mismatch-fix/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

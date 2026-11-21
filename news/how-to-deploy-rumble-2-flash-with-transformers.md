---
layout: default
title: "怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？"
description: "Rumble-2-Flash 已开源，支持 Transformers 和 vLLM；本文给出安装、加载模型、音频输入与自动语言检测的接入步骤。"
permalink: /news/how-to-deploy-rumble-2-flash-with-transformers/
date: 2026-11-19
---

> 更新日期：2026-11-19 · 一手来源：[Hugging Face Blog](https://huggingface.co/blog/rumble-2-flash)

# 怎么用 Transformers 部署 Rumble-2-Flash 语音识别模型？

如果你的目标是加载 `Reson8/Rumble-2-Flash`，识别本地或 URL 音频，并在没有指定语言时自动检测，直接使用 Transformers 的 `AutoProcessor`、`AutoModelForMultimodalLM` 和 `apply_transcription_request`。安装 `torch`、`transformers`、`accelerate` 后，省略 `language` 参数即可让模型自动检测语言，解码时改用 `return_format="parsed"`。如果要以服务方式部署，模型卡也给出了 `vllm serve` 命令和 OpenAI 兼容客户端示例。

本文适合需要在 Python 推理脚本中部署语音识别模型的开发者，也适合已经使用 Transformers 或 vLLM、希望评估轻量多语言语音模型的团队。所有接口和参数都来自 [Rumble-2-Flash 官方发布博客](https://huggingface.co/blog/rumble-2-flash) 和 [模型卡](https://huggingface.co/Reson8/Rumble-2-Flash)。

## 先确认模型和运行方式

**官方发布事实：** Reson8 于 2026 年 11 月 18 日在 Hugging Face 博客发布 Rumble-2-Flash。模型仓库为 `Reson8/Rumble-2-Flash`，采用 Apache 2.0 许可，参数规模为 0.5B。语言数量上，博客写的是 40 多种，模型卡标注为 45 种，但没有给出完整语言列表。

博客说明，Rumble-2-Flash 沿用 Qwen3-ASR 架构，原生支持 Transformers 和 vLLM，不需要分叉的运行时，也不需要设置 `trust_remote_code`。这意味着已有 Transformers 推理流程可以直接按标准自动类接口接入。

模型支持两种语言控制方式：

- 明确传入 `language`，值为语言的英文名称，例如 `"English"`、`"Dutch"`；
- 完全省略 `language`，让模型自动检测语言。

## 安装依赖

官方示例使用 `uv` 安装以下依赖：

```bash
uv pip install torch transformers accelerate
```

模型卡没有写明最低 Transformers 版本，也没有给出显存或 GPU 要求。如果加载时提示找不到 `AutoModelForMultimodalLM` 或不认识模型架构，先把 `transformers` 升级到最新版本再试。具体的 PyTorch 安装命令，按你的操作系统、硬件和 CUDA 环境单独确认。

## 使用 URL 音频完成转写

下面的代码就是官方博客和模型卡给出的示例，只把最后一行拆开写。示例使用 URL 音频并指定英语：

```python
from transformers import AutoProcessor, AutoModelForMultimodalLM

model_id = "Reson8/Rumble-2-Flash"

processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForMultimodalLM.from_pretrained(
    model_id,
    device_map="auto",
)

inputs = processor.apply_transcription_request(
    audio="https://hf.co/datasets/hf-internal-testing/dummy-audio-samples/resolve/main/bcn_weather.mp3",
    language="English",
).to(model.device, dtype=model.dtype)

output = model.generate(**inputs, max_new_tokens=512)

generated = output[:, inputs["input_ids"].shape[-1]:]

text = processor.decode(
    generated,
    return_format="transcription_only",
)[0]

print(text)
```

这里有三个需要注意的接口细节：

1. `AutoProcessor.from_pretrained` 和 `AutoModelForMultimodalLM.from_pretrained` 使用同一个模型 ID。
2. `device_map="auto"` 交由 Transformers 自动安排模型设备。
3. `generate` 返回的序列包含输入部分，所以要先按 `input_ids` 的长度截掉输入，再解码。

`max_new_tokens=512` 是官方示例的生成长度上限，不代表音频时长或固定转写字数。

成功标准：脚本打印出一段英文转写文本，且没有夹带输入提示内容。

## 改成本地音频或 NumPy 输入

官方说明 `audio` 参数接受本地路径、URL、NumPy 数组，或者由这些组成的列表。音频在本地时，只需把 `audio` 换成文件路径，其余代码不变：

```python
inputs = processor.apply_transcription_request(
    audio="/path/to/audio.mp3",
    language="English",
).to(model.device, dtype=model.dtype)
```

| 输入形式 | 用法 | 适合场景 |
|---|---|---|
| 本地路径 | `audio="/path/to/audio.mp3"` | 文件已下载到推理机器 |
| URL | `audio="https://..."` | 音频由可访问地址提供 |
| NumPy 数组 | `audio=array` | 已在 Python 中完成音频读取 |
| 以上输入的列表 | `audio=[...]` | 一次提交多个音频 |

模型卡没有规定采样率、声道、数组形状，也没有说明 URL 访问失败时怎么处理。用 NumPy 数组或批量列表时，先拿几条样本跑通，再接入正式数据管线。

## 如何启用自动语言检测

自动语言检测的做法不是填写某个特殊值，而是**省略 `language` 参数**，并在解码时把 `return_format` 换成 `"parsed"`：

```python
inputs = processor.apply_transcription_request(
    audio="/path/to/audio.mp3",
).to(model.device, dtype=model.dtype)

output = model.generate(**inputs, max_new_tokens=512)
generated = output[:, inputs["input_ids"].shape[-1]:]

result = processor.decode(
    generated,
    return_format="parsed",
)[0]

print(result)
```

模型卡说明：不设 `language` 时，模型的原始输出以 `language <语言名><asr_text>` 开头，后面才是转写文字。所以自动检测时如果仍用 `"transcription_only"` 或自己直接解码，结果里可能混进语言标记，这就是官方建议改用 `"parsed"` 的原因。模型卡没有写 `"parsed"` 返回的具体结构，第一次使用时先 `print` 出来看清字段，再写后续处理代码。

两种模式怎么选：

- 音频语言固定且已知：显式指定 `language`，解码用 `"transcription_only"`；
- 多语言混合或语言未知：省略 `language`，解码用 `"parsed"`；
- 拿不准时：用同一段音频分别跑两种配置，对比结果。

## 数字、语气词和重复词怎么控制

模型卡列出了四个转写选项：

| 选项 | 默认值 | 作用 |
|---|---|---|
| `language` | 不设 | 用英文名强制指定语言，如 `"Dutch"`、`"English"` |
| `digits` | `true` | 数字写成阿拉伯数字；`false` 时写成文字 |
| `filler` | `false` | `true` 时保留 "um"、"uh" 这类语气词 |
| `verbatim` | `true` | `false` 时合并重复的词 |

模型卡的说法是：在 vLLM 里通过 `chat_template_kwargs` 传这些选项，在 Transformers 里直接传给 `processor.apply_chat_template`。注意官方的 Transformers 示例用的是 `apply_transcription_request`，并没有给出 `digits`、`filler`、`verbatim` 的 Transformers 完整调用示例；需要这些选项时，优先用下面的 vLLM 方式，它有官方示例可照抄。

## 用 vLLM 部署成 OpenAI 兼容服务

模型卡给出的安装和启动命令：

```bash
uv pip install "vllm[audio]" openai
vllm serve Reson8/Rumble-2-Flash --max-model-len 4096
```

服务启动后，用 OpenAI SDK 把音频按 base64 放进 `audio_url` 发给本地服务（以下与模型卡示例一致）：

```python
import base64
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
audio = base64.b64encode(open("audio.wav", "rb").read()).decode()

response = client.chat.completions.create(
    model="Reson8/Rumble-2-Flash",
    messages=[{
        "role": "user",
        "content": [{
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav;base64,{audio}"},
        }],
    }],
    temperature=0,
    extra_body={"chat_template_kwargs": {"language": "English"}},
)
print(response.choices[0].message.content)
```

要把数字写成文字、保留语气词，就在同一个 `chat_template_kwargs` 里加上对应选项，例如 `{"language": "English", "digits": False, "filler": True}`。去掉 `language` 则走自动检测；按模型卡说明，这时输出开头会带 `language <语言名><asr_text>` 标记，需要自己处理。

模型卡没有写最低 vLLM 版本。如果 `vllm serve` 报不认识模型架构，先升级 vLLM。

## 部署前检查清单

- [ ] 模型 ID 使用 `Reson8/Rumble-2-Flash`。
- [ ] 已安装 `torch`、`transformers`、`accelerate`（vLLM 方式另装 `vllm[audio]` 和 `openai`）。
- [ ] `AutoProcessor` 与 `AutoModelForMultimodalLM` 都能从模型仓库加载。
- [ ] 本地路径、URL 或 NumPy 数组输入至少验证一种。
- [ ] 已知语言时显式传入 `language`；自动检测时省略 `language` 并用 `return_format="parsed"`。
- [ ] 生成结果已去掉输入 token 部分。
- [ ] 需要 `digits`、`filler`、`verbatim` 时，已确认选项实际生效。
- [ ] 已确认 Apache 2.0 许可与项目发布要求相容。

## 如何判断是否适合迁移

博客公布的评测结果包括：Open ASR Leaderboard 多语言赛道错误率 6.96%、英语赛道 WER 6.6%，以及 AppTek 呼叫中心数据集（302 小时、14 种英语口音）上 WER 7.86%。这些是发布方给出的结果，不代表你的音频、硬件和批处理方式一定能达到相同表现。

迁移前建议建立自己的小型验证集，至少覆盖：

- 业务中实际出现的语言；
- 清晰录音与压缩、嘈杂录音；
- 不同说话人和口音；
- 数字、专有名词、重复词和语气词；
- 单条推理与批量推理。

比较时同时记录识别错误、语言判断是否正确、单条延迟、批量吞吐和显存占用，符合业务要求再决定是否从现有模型迁移。

Rumble-2-Flash 是自行部署的开源模型，截至 2026 年 11 月 19 日不在 OpenLux 在售模型列表里。如果你的业务同时需要调用 GPT、Claude、Gemini 等托管模型，可以[注册 OpenLux 并创建 API Key](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=how-to-deploy-rumble-2-flash-with-transformers&utm_content=footer)。

## 官方一手来源

- Rumble-2-Flash 发布博客：https://huggingface.co/blog/rumble-2-flash
- 模型卡：https://huggingface.co/Reson8/Rumble-2-Flash

## 同专题文章

- [调用 API 报 400「Invalid 'tools[0].function.name'」怎么办：工具名只能用字母、数字、下划线和横线，OpenAI 最长 64 字符](https://a37836323.github.io/openlux-api-guides/news/api-400-invalid-tools-function-name-fix/)
- [GitHub Copilot CLI 怎么接入 OpenAI 兼容 / Claude 中转 API：providers.json、Base URL、Key 与模型设置](https://a37836323.github.io/openlux-api-guides/news/github-copilot-cli-relay-api-providers-json-setup/)
- [中转站检测：怎么判断 API 中转站是不是官方原模型（6 个自测方法，含降智排查）](https://a37836323.github.io/openlux-api-guides/news/check-api-relay-real-model/)
- [如何获取 Google DeepMind 的 SatWeave 和 PARDIG 天气数据集？](https://a37836323.github.io/openlux-api-guides/news/how-to-access-pardig-satweave-weather-datasets/)
- [llama.cpp 升级 v1.0.0 会破坏 C API/ABI 吗？如何固定 libllama/libggml 版本并安排迁移](https://a37836323.github.io/openlux-api-guides/news/llama-cpp-v1-api-abi-migration/)
- [如何用 Hugging Face Jobs 微调 TRELLIS.2？遇到“需要 HF_TOKEN 和 DINOv3 权限”怎么处理](https://a37836323.github.io/openlux-api-guides/news/how-to-finetune-trellis2-with-hugging-face-jobs/)

[查看「其他模型与通用实践」全部文章](https://a37836323.github.io/openlux-api-guides/topics/general/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

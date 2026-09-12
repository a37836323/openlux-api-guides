---
layout: default
title: "Whisper API 报 413、音频超过 25MB：怎么压缩和分段？"
description: "文件转写超过上传限制时，核对错误来源，压缩或按时间分段并验证每段可播放。"
permalink: /news/whisper-audio-413-25mb-limit-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[OpenAI 官方文档](https://developers.openai.com/api/docs/guides/speech-to-text)

# Whisper API 报 413、音频超过 25MB：怎么压缩和分段？

如果文件转写请求报 `413` 或超过内容大小限制，先确认错误来自 OpenAI 转写接口，还是你自己的上传服务、代理或工作流平台。当前官方文件转写指南列出的上限是 25 MB；较大录音可以压缩或按时间分段。直接把二进制文件切成固定字节块，可能得到无法解码的音频。

资料核验：2026 年 9 月 12 日。若准备评估云端 API，可[查看 OpenLux 的账户与可用模型](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=whisper-audio-413-25mb-limit-fix&utm_content=intro)。OpenLux 是独立服务，具体接口、计费和功能以其当前说明为准。

## 这个问题不只是录音太长

OpenAI 社区有用户在 Node.js 上传音频时遇到 413，也有 n8n 用户因为 25 MB 限制考虑自托管 Whisper。这是两处独立的上传问题线索，不代表自托管就没有内存、时长或服务配置限制。

文件大小与录音时长不同。相同长度的录音，编码、码率、声道和是否夹带视频都会影响体积。短视频也可能比长时间的压缩语音文件更大，因此先查看实际文件字节数，而不是凭播放时长判断能否上传。

## 先定位是哪一层返回 413

| 失败位置 | 应检查什么 | 处理方向 |
|---|---|---|
| 浏览器上传到自己的后台 | 后台与反向代理限制 | 核对本地上传配置 |
| 工作流读取附件时 | 平台附件和节点限制 | 查该平台文档与日志 |
| 请求到达转写接口后 | 上游错误正文与文件大小 | 压缩或分段 |
| 小文件仍报格式错误 | 实际编码与容器格式 | 重新导出为支持格式 |

不要看到 413 就直接放宽服务器全部上传限制。即使自己的入口允许更大文件，上游仍有独立限制。保留请求时间、文件大小、目标端点及错误正文，先确定需要修改哪一层。

## 能压缩时先做小样本比较

当前官方指南列出 mp3、mp4、mpeg、mpga、m4a、wav、webm 等输入格式。选择当前接口明确支持的格式，先对短片段转码并试听，再比较转写效果。旧帖中的格式或极低码率建议，不应直接套到所有模型上。

如果原文件包含不需要的视频，可以提取音轨，减少传输体积。降低码率或转为单声道前，先确认是否会影响说话人区分、背景信息和关键语音。保留原始录音，避免后续只能从已经失真的压缩文件恢复内容。

压缩后重新检查实际大小，并留出余量，不要把文件做得刚好等于限制边界。编码成功不代表内容完整，至少试听开头、中间、末尾和低音量片段。

## 分段时按音频时间切，不按原始字节切

使用音频工具按时间或静音点导出独立可播放的片段。每段应有自己的有效容器结构，并再次检查大小；只把大文件数组切成几段，不会自动产生有效的 MP3 或 MP4 文件。

官方指南建议避免在句子中间切开。固定时长分段便于管理，但可能切断词句；更精细的流程可以结合静音区间选择边界。若使用重叠片段来保护边界语音，合并时必须处理重复内容，不能直接把所有转写结果拼接。

下面的离线示例检查一个无重叠分段清单，确认时间连续且顺序正确。它只验证记录，不负责切音频或调用转写服务。

```python
def check_segments(segments, total_seconds):
    cursor = 0
    for item in segments:
        if item["start"] != cursor or item["end"] <= item["start"]:
            return False
        cursor = item["end"]
    return cursor == total_seconds

segments = [
    {"file": "part-001.mp3", "start": 0, "end": 300},
    {"file": "part-002.mp3", "start": 300, "end": 570},
]
assert check_segments(segments, 570)
assert not check_segments(segments[1:], 570)
```

实际清单还应记录文件大小、生成方式、原文件标识和转写状态。若有意采用重叠策略，应改用与该策略相匹配的检查规则，而不是照搬无重叠断言。

## 合并文本时别丢掉时间关系

按片段顺序归并结果，先确认没有缺段或重复补跑。若接口返回片段内时间戳，需要加上该片段在原录音中的起点，才能对应原文件位置。不同模型支持的时间戳和输出格式不完全相同，应查具体模型说明。

对切分边界附近的人名、数字和否定词做抽查。它们容易因缺少上下文而影响结果。失败片段单独补跑，并保留原结果与替换关系，不要因为一段失败就重新提交全部录音。

## 怎样验收这次处理

每段都能独立播放、体积符合当前上游要求、转写请求成功，并且合并结果覆盖完整时间范围，才算完成上传与分段处理。还要检查是否遗漏首尾内容，不能只看 API 返回成功。

需要把转写结果整理成纪要时，可以阅读[会议转写与行动项核验](../meeting-audio-transcription-action-items/)。先保证音频覆盖和转写完整，再生成总结，避免后续模型把缺失片段当成真实没有发生。

## 提问出处与官方依据

- [独立问题线索 1](https://community.openai.com/t/hosting-whisper-model-on-vultr-machine/1360429)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [独立问题线索 2](https://community.openai.com/t/how-do-i-get-whisper-to-allow-larger-files-in-the-request/572288)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [OpenAI 官方文档](https://developers.openai.com/api/docs/guides/speech-to-text)：按当前页面核对解决步骤。历史提问不代表当前所有环境都存在同一问题。

如需要进一步比较云端接口，可[注册 OpenLux 并核对适用能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=whisper-audio-413-25mb-limit-fix&utm_content=footer)。切换服务前单独验证接口与账户配置，不能据此认定原服务的问题已经修复。

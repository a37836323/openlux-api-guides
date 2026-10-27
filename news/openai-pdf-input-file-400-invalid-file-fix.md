---
layout: default
title: "OpenAI 传 PDF 报 400「You uploaded an invalid file」怎么办：input_file 写法、50 MB 上限与 PDF 内容排查"
description: "OpenAI Responses API 用 input_file 传 PDF 报 400「You uploaded an invalid file」：按官方文档核对 file_data 前缀、50 MB 上限、视觉模型与 detail，再排查 JPEG 2000、C2PA、图片数量等已知 PDF 内容问题，附 request ID 提交方法。"
permalink: /news/openai-pdf-input-file-400-invalid-file-fix/
date: 2026-10-27
---

> 更新日期：2026-10-27 · 一手来源：[OpenAI File inputs 文档](https://developers.openai.com/api/docs/guides/file-inputs)

# OpenAI 传 PDF 报 400「You uploaded an invalid file」怎么办：input_file 写法、50 MB 上限与 PDF 内容排查

用 Responses API 的 `input_file`（或 Chat Completions 的 `file` 内容块）把 PDF 发给模型，返回 HTTP 400、`invalid_request_error`，报错文字是 `You uploaded an invalid file. Please try again with a different file.`。这个报错不会告诉你具体是哪里不对，排查要分两步：**先核对请求写法是否符合官方文档**（接口、`file_data` 格式、文件大小、模型），**写法没问题再查 PDF 文件本身**。2026 年 10 月 OpenAI 社区里有多位开发者报告过几类 PDF 内容触发的 400，OpenAI 支持人员已陆续回复修复，本文把时间线也整理在下面。

依据：OpenAI 官方 [File inputs 文档](https://developers.openai.com/api/docs/guides/file-inputs)、[API 参考概览中关于 request ID 的说明](https://developers.openai.com/api/reference/overview)，以及 OpenAI 社区帖 [HTTP 400 on PDF input_file](https://community.openai.com/t/http-400-on-pdf-input-file-with-jpeg-2000-images-or-an-embedded-c2pa-manifest-gpt-5-4-rotate-pages-still-cropped/1402705) 中用户报告和 OpenAI_Support 的回复。

## 先核对：官方对 PDF 输入的硬性要求

下表是 File inputs 文档里写明的要求，逐项对照自己的请求：

| 检查项 | 官方文档的说法 | 不符合时怎么改 |
|---|---|---|
| 接口与文件类型 | Responses API 的 `input_file` 支持 PDF、文本/代码、Word、PPT、表格等；Chat Completions 只接受 PDF | 在 Chat Completions 里传非 PDF 文件，改用 Responses API，或自己读出文本作为 `text` 内容发送 |
| 传文件的方式 | `file_data`（Base64）、`file_id`（先上传）、`file_url`（外部链接）；Chat Completions 不支持 `file_url` | Chat Completions 改用 `file_data` 或 `file_id` |
| `file_data` 格式 | 官方 SDK 示例写成 `data:application/pdf;base64,` 前缀加 Base64 内容，并同时给出 `filename` | 补上前缀和带 `.pdf` 后缀的文件名 |
| 文件大小 | 每个文件必须小于 50 MB，一次请求内所有文件合计上限也是 50 MB | 拆成多次请求，或改用 File Search 做大文件检索 |
| 模型 | 同时解析文字和页面图像需要有视觉能力的模型，如 `gpt-4o` 及之后的模型 | 换成支持视觉输入的模型 |
| `detail` 参数 | 只用于 Responses API 的 PDF，取值 `auto`、`low`、`high`；Chat Completions 的文件输入不支持 `detail` | 在 Chat Completions 里去掉 `detail`，在 Responses 里只用这三个值 |
| 上传用途 | 用 Files API 上传时可以用任何支持的 purpose，但作为模型输入的文件建议用 `user_data` | 上传时设 `purpose="user_data"` |

文档没有给出 PDF 页数上限，只有上面的 50 MB 大小限制。Base64 编码后体积会比原文件大，官方没有说明 50 MB 是按原文件还是按编码后计算，接近上限时建议留出余量或改用 `file_id`。

## 对照官方写法：Responses API 最小示例

官方文档给出的 Base64 写法（Python，按官方示例精简）：

```python
import base64
from openai import OpenAI

client = OpenAI()
with open("draconomicon.pdf", "rb") as f:
    base64_string = base64.b64encode(f.read()).decode("utf-8")

response = client.responses.create(
    model="gpt-6-astra",
    input=[{
        "role": "user",
        "content": [
            {"type": "input_file", "filename": "draconomicon.pdf",
             "file_data": f"data:application/pdf;base64,{base64_string}"},
            {"type": "input_text", "text": "What is the first dragon in the book?"},
        ],
    }],
)
print(response.output_text)
```

对照时重点看三处：内容块的 `type` 是 `input_file`；`file_data` 带了 `data:application/pdf;base64,` 前缀；`filename` 有 `.pdf` 后缀。如果用 `file_id`，文档示例是先 `client.files.create(file=..., purpose="user_data")`，再在 `input_file` 里填 `file_id`。

## 写法都对仍然 400：近期已知的 PDF 内容问题

在上面提到的社区帖子里，几位开发者用同一套请求写法，只因 PDF 内容不同而稳定复现 400。按时间整理如下（日期为帖子时间，UTC）：

| 触发条件（用户报告） | 现象 | OpenAI_Support 的回复 |
|---|---|---|
| PDF 里有 JPEG 2000 图片（`/Filter /JPXDecode`） | 400；用户把这些图片流换成 Flate 编码、像素不变后，同一请求成功 | 10-06 回复称已于 10 月 5 日合并修复；10-19 回复相关扫描组件更新已部署 |
| PDF 内嵌 C2PA 清单（例如 ChatGPT 生成并签名的 PDF） | 400，报错为 `You uploaded an invalid file...`；去掉内嵌清单的版本成功 | 10-19 回复「C2PA 清单被误判为 SVG」的修复已部署 |
| 单个 PDF 里放置的图片超过约 50 张 | 用户测得 50 张通过、51 张失败，按单个文件计算；改用 Files API 上传后用 `file_id` 也是同样的 400 | 10-06 回复这是 10 月 5 日引入的 PDF 扫描回归，不是有意设置的限制，修复已上线 |
| 页面带 `/Rotate 90/270` 的扫描件 | 不报错，但模型只看到页面的一个正方形区域，上部约 29% 内容缺失 | 10-26 回复包括旋转问题在内的所有问题应已解决 |

10 月 20 日，最早发帖的用户确认此前报 400 的两类文件（单张 JPEG 2000 图片的 PDF、带 C2PA 清单的 PDF）已能正常处理。所以如果你在 10 月上中旬遇到过这类 400，现在可以先原样重试一次。

需要注意：第三行说明，换成 `file_id` 上传并不能绕开 PDF 内容本身导致的 400，用户报告两种方式结果相同。

## 怎么判断是请求问题还是 PDF 问题

社区用户定位问题的思路是做 A/B 对比：保持请求其他部分不变，只换文件。可以按这个顺序：

1. 用同一段代码发一个只有几行文字、没有图片的小 PDF。如果仍然 400，问题在请求写法、模型或账户侧，回到第一节的表格逐项检查。
2. 小 PDF 成功、原 PDF 失败，说明问题在文件本身。先确认大小低于 50 MB。
3. 再看原 PDF 是否属于上表列出的类型：是否含 JPEG 2000 图片、是否有内嵌文件、图片数量是否很多、是否是带旋转属性的扫描件。
4. 如果在官方回复修复之后仍然失败，帖子里用户在修复前采用的临时做法是预处理文件：把 JPEG 2000 图片重新编码、去掉内嵌文件、把扫描页像素转正。这是社区用户的做法，不是官方方案，处理后要核对内容没有丢失。

判断成功的标准：同一请求返回 200，`output_text` 里能引用到 PDF 中的具体内容（包括扫描件页面顶部的信息），而不只是泛泛的回答。

## 仍然失败：带上 request ID 找官方支持

OpenAI_Support 在帖子里请仍遇到失败的用户提供 `x-request-id` 和 UTC 时间。按 [API 参考概览](https://developers.openai.com/api/reference/overview)：

- 响应头里的 `x-request-id` 用来标识这次请求、供排查使用；官方建议在生产环境记录它，官方 SDK 在顶层响应对象上提供了读取这个值的属性。
- 也可以自己在请求头里加 `X-Client-Request-Id`（只能是 ASCII，最长 512 字符，否则请求会以 400 失败），在超时或网络问题拿不到响应头时，用它让支持查找请求是否到达。

提交时附上失败时间（UTC）、模型名、传文件的方式（`file_data` 还是 `file_id`），以及 PDF 是否含上表所列特征。PDF 内容若涉及隐私，不要贴到公开帖子里。

## 通过 OpenAI 兼容中转调用时

经中转调用 Responses API 时，用 `file_data` 方式的 PDF 以 Base64 写在 JSON 请求体里，同样要满足上游 50 MB 的限制。中转服务是否支持 `input_file`、能否使用 `file_id`，以实际响应为准。排查时先在中转入口用上面的小 PDF 做对照，确认请求能通，再换回原文件。

如果你需要一个 OpenAI 兼容的 API 入口来调试和对比多个模型，可以 [注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=openai-pdf-input-file-400-invalid-file-fix&utm_content=footer)。

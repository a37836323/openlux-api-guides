---
layout: default
title: "Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查"
description: "Claude API 发送图片返回 400 invalid_request_error 时，按官方 Vision 文档逐项排查：单图 10 MB（base64 后）、8000 像素上限、超过 20 张图的更严尺寸限制、tool_result 截图不自动缩放、oversized_image 报错与支持格式。"
permalink: /news/claude-api-image-400-size-dimension-limit-fix/
date: 2026-11-18
---

> 更新日期：2026-11-18 · 一手来源：[Anthropic Claude 文档：Vision](https://platform.claude.com/docs/en/build-with-claude/vision)

# Claude API 传图片报 400 invalid_request_error 怎么办：单图 10 MB、8000 像素、超过 20 张图的尺寸限制与格式逐项排查

用 Claude Messages API 发图片时，如果返回 HTTP 400、错误类型是 `invalid_request_error`，而去掉图片就能正常返回，常见原因在图片本身：单张太大、边长超过 8000 像素、一次请求里图片超过 20 张触发了更严的尺寸限制、截图通过 `tool_result` 回传时超出模型上限，或者你给图片打了 `"oversized_image": "error"` 标记。整个请求体超过 128 MB 时返回的是 413 `request_too_large`，不是 400，处理方法见本站的 [Claude API 413 排查文章](https://a37836323.github.io/openlux-api-guides/news/claude-api-413-request-too-large-fix/)。

本文的限制数字和报错说明全部来自 Anthropic 官方文档 [Vision](https://platform.claude.com/docs/en/build-with-claude/vision)、[Coordinates and bounding boxes](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates) 和 [Claude API errors](https://platform.claude.com/docs/en/api/errors)。适用于直接调用 Claude API 的 Messages 接口；Amazon Bedrock、Google Cloud 等平台的限制有差别，文中单独标出。

## 先确认是不是图片引起的 400

官方错误文档对 400 的定义是「请求的格式或内容有问题」，范围很宽：思考参数、`tool_choice`、预填充、消费上限等都会返回 400。所以先做两件事：

1. 看响应体里的 `error.message`。官方说明错误一律以 JSON 返回，顶层 `error` 对象里有 `type` 和 `message`，同时带一个 `request_id`。消息里提到 image、dimensions、many-image requests 之类的字样，才往下按图片排查。
2. 保留其他参数不变，只把图片块去掉再发一次。去掉图片就成功，说明问题在图片；仍然 400，就按消息去查思考、工具等其他参数。

如果是 base64 图片，官方说明报错会带上位置，例如 `messages.0.content.0`，可以直接对应到第几条消息的第几个内容块。通过 URL 或 `file_id` 引用的图片，报错不带位置，看不出是哪一张，这时只能逐张排查。

## 官方限制一览

下表是 Vision 文档「Request limits」和「Supported formats」两节给出的数字，按「报错时先对照哪一行」整理：

| 项目 | Claude API 上的限制 | 超出时的结果 |
| --- | --- | --- |
| 单张图片大小 | 10 MB（按 base64 编码后计算） | 请求失败，返回校验错误 |
| 单张图片尺寸 | 最大 8000×8000 像素 | 请求失败，`oversized_image` 设置也放不过去 |
| 一次请求超过 20 张图 | 对请求里每一张图套用更严的单图尺寸限制 | 400 `invalid_request_error`，消息提到 many-image requests 并给出当前像素上限 |
| 每次请求的图片数 | 200k 上下文窗口的模型最多 100 张，其他模型最多 600 张 | 请求失败，返回校验错误 |
| 整个请求体 | Messages API 最大 128 MB | 413 `request_too_large` |
| 支持的格式 | JPEG、PNG、GIF、WebP（`image/jpeg`、`image/png`、`image/gif`、`image/webp`） | 不支持动画，动图只用第一帧 |

其他平台的差别（官方原文）：Amazon Bedrock 上单张图片上限是 5 MB（base64 编码后），而且只支持 base64 图片来源，请求总大小也更低；Claude Models on Google Cloud（Google 托管）同样只支持 base64 来源、请求总大小更低，而它的单图上限，官方的平台说明写 5 MB、正文限制表写 10 MB，以你所用平台自己的文档为准。claude.ai 网页端单张 10 MB、每条消息最多 20 张。

注意「10 MB」官方写明是按 base64 编码后的大小算的，所以要看编码后的字符串长度，而不是只看磁盘上的原文件大小。坐标文档还说明：超过模型原生分辨率的图片会被自动缩小，不会报错；只有超出上表这些请求限制，请求才会以校验错误失败。

## 情况一：单张太大或边长超过 8000 像素

这两个都是硬限制，官方在坐标文档里说明：8000 像素的最长边限制和多图请求的更严限制都单独拒绝，`oversized_image` 设置不会让图片绕过它们。

改法：

1. 在发送前用图片库读出宽高，最长边超过 8000 像素的先缩小。
2. 文件大的照片可以转成 JPEG 或有损 WebP 压缩。官方提醒，有损压缩会产生伪影，压缩过度（尤其是多次压缩）会让图里的文字难以辨认，压缩参数要实际看过发出去的图片再定。
3. 不需要那么高的清晰度时，直接缩到模型的原生分辨率以内（见下一节「自动缩放」），既减少体积，也不会损失模型实际看到的内容。

## 情况二：一次请求超过 20 张图后报 many-image requests

这是最容易误判的一种：单看每张图都没超 8000 像素，但请求里图片一多就开始 400。官方规则是：一次 API 请求里超过 20 张图时，对请求里每一张图都套用更严的单图尺寸限制，超过的图片会被拒绝，错误类型是 `invalid_request_error`，消息里会提到「many-image requests」并写出当前的像素上限。

计数时容易漏掉的部分，官方写得很明确：

- 请求里所有 `image` 块都算，包括多轮对话里你重新发送的前几轮图片；
- 嵌在 `tool_result` 里的图片也算，例如电脑使用工具回传的截图；
- 在 Claude Models on Google Cloud（Google 托管）和 Amazon Bedrock 上，PDF 之类的 `document` 块也计入这个阈值。

官方给出的两种改法，任选一种就能在所有平台上不超限：

1. 把每张图缩到宽和高都不超过 3000 像素；
2. 把一次请求里的图片和文档块控制在 20 个以内，例如只保留最近几轮的截图，或把早期图片换成文字摘要后再发。

对话越长、图片越多，请求体也越大。官方建议多图场景用 Files API 上传一次、之后用 `file_id` 引用，避免每轮重复发送 base64 数据；但用 `file_id` 只是让请求体变小，图片数量和尺寸限制照样适用。

## 情况三：截图通过 tool_result 回传时报错

普通图片超过模型原生分辨率时，Claude 会自动等比缩小后再处理，不会报错。官方说明唯一的例外是回传给电脑使用（computer use）和浏览器使用（browser use）工具集的截图和放大图：这类 `tool_result` 图片超出模型上限时，API 直接返回校验错误，不会替你缩小。

各模型的原生分辨率上限（Vision 文档「Resolution and token cost」一节）：

| 分辨率档位 | 适用模型 | 最长边上限 | 视觉 token 上限 |
| --- | --- | --- | --- |
| 高分辨率 | Claude 4.7 及之后的模型 | 2576 像素 | 4784 |
| 标准 | 其他模型 | 1568 像素 | 1568 |

视觉 token 按 `⌈宽/28⌉ × ⌈高/28⌉` 计算。官方特别提醒，多数照片和截图是 token 上限先触发，而不是边长上限：例如 1920×1080 的截图在标准档会缩到 1456×819，而不是按最长边缩到 1568×882。所以截图要在你的程序里先缩到合适尺寸再回传，尺寸请用官方坐标文档「Resize your image before uploading」一节的参考实现计算，不要只按最长边手算。缩放后，Claude 返回的点击坐标是针对你发出去的那张图的，需要再换算回屏幕尺寸。

## 情况四：设置了 oversized_image: error 之后被拒绝

做坐标定位、表格框选时，为了防止服务器悄悄缩放导致坐标对不上，官方提供了图片块上的可选字段 `transformations`：

```json
{
  "type": "image",
  "source": { "type": "base64", "media_type": "image/png", "data": "..." },
  "transformations": { "oversized_image": "error" }
}
```

打了这个标记的图片如果需要缩放，请求会被拒绝，返回 400 `invalid_request_error`，消息里写出图片的原始尺寸和能接受的最大尺寸。官方给出的报错原文示例（1920×1080 图片发给标准档模型）：

```text
messages.0.content.0: image dimensions 1920x1080 exceed the maximum image size of a model named on this request and would be downsized to 1456x819; scale the image to at most 1456x819 or set the image's oversized_image setting to "downsize"
```

改法就是按消息里给出的目标尺寸缩小后重发；如果这张图被缩放也无所谓（比如只是一个 logo），把它的设置改回 `"downsize"` 或去掉 `transformations` 字段即可，不写时默认就是 `"downsize"`。另外两点官方说明：

- 同一请求里如果点名了多个模型，判断标准是所有被点名模型都能接受的尺寸；同一张 1920×1080 图片，标准档会拒绝，高分辨率档则不会。
- 打了 `"error"` 标记、但服务器读不出尺寸的图片也会被拒绝，这时消息说的是「无法确定图片的源尺寸」，而不是上面的缩放提示，需要检查图片文件本身是否完整。

## 格式与 media_type 检查

官方支持的格式只有 JPEG、PNG、GIF、WebP 四种，对应 `media_type` 为 `image/jpeg`、`image/png`、`image/gif`、`image/webp`。官方没有在这几页列出格式错误的报错原文，排查时按以下顺序核对：

1. 文件真实格式是不是这四种之一（HEIC、BMP、TIFF 等需要先转换）；
2. base64 图片的 `media_type` 是否和文件真实格式一致，不要把 PNG 写成 `image/jpeg`；
3. 官方示例里 `data` 是纯 base64 字符串，按示例写，不要混入其他内容；
4. 官方说明不支持动画，动图只使用第一帧，需要整段动画信息时要自己拆帧。

## 修好后怎么验证

1. **看状态码**：重发后返回 HTTP 200、拿到正常文本回答，就说明图片已被接受。
2. **用 token 计数接口预检，但别全信**：官方说明 token 计数接口根据尺寸估算图片 token，计数成功不代表图片符合 Messages API 的请求限制；不过它会执行 `transformations` 的检查，可以提前确认内嵌（base64）图片是否会被缩放。URL 和 `file_id` 图片在计数时不会被拉取检查，只能在真正调用 Messages 时确认。
3. **核对多图请求**：数一下整段对话（含历史轮次和 `tool_result`）里的图片块总数，超过 20 个时确认每张图宽高都不超过 3000 像素。
4. **保留 request_id**：如果问题仍未解决，把响应体里的 `request_id`（或响应头 `request-id`）连同报错原文一起提交给支持人员。

## 排查顺序小结

| 报错或现象 | 先查什么 | 怎么改 |
| --- | --- | --- |
| 400，去掉图片就成功 | 单图大小、边长 | 缩到 8000 像素以内、base64 后不超过 10 MB（Bedrock 5 MB） |
| 400，消息提到 many-image requests | 整个请求里的图片总数 | 每张缩到 3000 像素以内，或减到 20 个图片和文档块以内 |
| 电脑使用 / 浏览器使用回传截图时报校验错误 | 截图尺寸是否超过模型原生分辨率 | 在程序里按官方参考实现缩放后再回传 |
| 400，消息写 would be downsized to | 是否设置了 `oversized_image: error` | 按给出的尺寸缩小，或改回 `downsize` |
| 413 request_too_large | 整个请求体是否超过 128 MB | 改用 Files API 的 `file_id`，减少重复发送的图片 |

需要一个同时支持 Claude、GPT、Gemini 等模型的 API 接入地址时，可以[注册 OpenLux](https://api.openlux.ai/register?channel=c_tiu9nw5h&utm_source=openlux_api_guides&utm_medium=owned_content&utm_campaign=claude-api-image-400-size-dimension-limit-fix&utm_content=footer)。

## 同专题文章

- [Claude API 报 400「This model does not support assistant message prefill」怎么办：预填充为什么不能用、改成结构化输出与续写的写法](https://a37836323.github.io/openlux-api-guides/news/claude-api-400-assistant-message-prefill-not-supported-fix/)
- [Claude API 设置 temperature、top_p 或 top_k 后为什么可能没有文本水印？](https://a37836323.github.io/openlux-api-guides/news/claude-api-sampling-parameters-text-watermark/)
- [Claude API 报 400「thinking blocks cannot be modified」或「Invalid signature in thinking block」怎么办：原样回传思考块、redacted_thinking 与改了历史逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-thinking-blocks-cannot-be-modified-fix/)
- [Claude API 回答只出一半、stop_reason 是 max_tokens 怎么办：调大上限、续写与思考占用逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-stop-reason-max-tokens-truncated-fix/)
- [Claude API 报 400「tool_use ids were found without tool_result blocks immediately after」怎么办：漏回结果、中间插了消息、文本放在结果前逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-tool-use-without-tool-result-fix/)
- [Claude API 报 404 not_found_error 怎么办：请求路径、Base URL 多写 /v1、模型 ID 与文件 ID 逐项排查](https://a37836323.github.io/openlux-api-guides/news/claude-api-404-not-found-error-fix/)

[查看「Claude API 报错与迁移」全部文章](https://a37836323.github.io/openlux-api-guides/topics/claude-api/) · [全部文章目录](https://a37836323.github.io/openlux-api-guides/news/)

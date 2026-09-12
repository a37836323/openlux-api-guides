---
layout: default
title: "OpenAI API 报 CERTIFICATE_VERIFY_FAILED：证书链怎么修？"
description: "区分证书链、域名、系统时间与企业代理，配置可信 CA 并保持 HTTPS 校验。"
permalink: /news/openai-python-certificate-verify-failed-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[HTTPX 官方文档](https://www.python-httpx.org/advanced/ssl/)

# OpenAI API 报 CERTIFICATE_VERIFY_FAILED：证书链怎么修？

`CERTIFICATE_VERIFY_FAILED` 表示 HTTPS 连接的身份校验没有通过。先检查完整底层错误、系统时间、目标域名和运行环境使用的可信 CA；企业代理或自定义证书场景，应按组织提供的可信证书配置客户端。不要把永久关闭证书校验当作修复完成。

资料核验：2026 年 9 月 12 日。若准备评估云端 API，可[查看 OpenLux 的账户与可用模型](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-python-certificate-verify-failed-fix&utm_content=intro)。OpenLux 是独立服务，具体接口、计费和功能以其当前说明为准。

## 为什么错误外面还包着 APIConnectionError

OpenAI 社区有 macOS 用户报告无法取得本地签发者证书，也有多名用户在 Python 调用中遇到同类 TLS 错误。旧帖里使用的 HTTP 库和当前 SDK 可能不同，因此不能直接沿用某个历史环境变量。

SDK 可以把底层连接异常包装为 `APIConnectionError`。应继续查看异常原因链，确认是证书验证、DNS、连接拒绝还是代理错误。只有看到 TLS 相关证据，才进入本文的证书检查流程。

## 先从错误正文确定方向

| 底层线索 | 优先核对 | 常见误区 |
|---|---|---|
| unable to get local issuer certificate | 信任根和服务端中间证书链 | 只换 API Key |
| certificate has expired | 证书有效期与系统时间 | 忽略时间设置 |
| hostname mismatch | 请求域名与证书对应关系 | 用 IP 替换域名继续请求 |
| self-signed certificate in certificate chain | 企业代理或自建入口的可信 CA | 随意导入来源不明证书 |
| 浏览器可用但 Python 失败 | 各自使用的证书存储 | 假设所有程序共享配置 |

这些是检查方向，不是仅凭一行报错就能确定根因。保存域名、时间、运行环境和底层异常类型，通常比重装整个 SDK 更有帮助。

## 浏览器信任，不代表 HTTPX 也信任

HTTPX 官方 SSL 文档说明，默认会验证 HTTPS，并使用证书集合；也支持通过 `SSLContext` 配置客户端。浏览器、操作系统、容器和 Python 环境可能使用不同的信任来源。

如果公司网络有 HTTPS 检查代理，浏览器可能已经安装组织的根证书，而应用容器没有。应向负责网络的人员确认可信 CA 和配置方式，再让实际发请求的运行环境使用它。不要从论坛下载陌生证书来“试一下”。

如果没有企业代理，也应确认基础镜像或系统的 CA 证书是否完整、系统时间是否正确，以及请求是否被配置到了错误的主机。单独升级 Python 包不一定能修复服务端缺少中间证书的问题。

## 使用 SSLContext 配置受信任的 CA

下面仅展示如何在保留验证的前提下构造上下文。函数需要调用者提供已经确认可信的 CA 文件，不会自动下载证书，也不发出网络请求。

```python
import ssl

def context_with_extra_ca(ca_file):
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=ca_file)
    return context

context = ssl.create_default_context()
assert context.check_hostname is True
assert context.verify_mode == ssl.CERT_REQUIRED
```

HTTPX 客户端可以通过 `verify=context` 使用该上下文。若交给 OpenAI SDK，还要按其官方自定义 HTTP 客户端方式接入，并处理同步或异步客户端的类型及关闭时机。只在独立测试脚本里创建上下文，不会自动改变应用其他请求的证书配置。

## 环境变量配置也要确认使用者

HTTPX 官方文档说明了 `SSL_CERT_FILE` 和 `SSL_CERT_DIR`。具体程序是否读取环境配置，还取决于客户端设置和启动环境。旧 requests 教程中的变量不能默认视为 HTTPX 的配置方式。

容器里设置证书路径时，确认文件已经放进容器或正确挂载，且运行用户有读取权限。不要只验证宿主机路径存在。修改后重新启动实际服务，并再次核对运行环境，避免后台任务继续使用旧配置。

如果同时配置代理，先确认代理地址及证书责任边界。发生 `unexpected keyword argument proxies` 时，属于客户端构造参数问题，应阅读[HTTPX 依赖兼容排查](../openai-httpx-unexpected-proxies-fix/)，不能用证书文件解决。

## 为什么不建议长期 verify=False

关闭验证可能让一次请求通过，但同时取消了对目标身份的关键检查，不能证明连接到了预期服务。正式修复应恢复可信链与域名校验，而不是把错误隐藏起来。

也不要为了消除域名错误，把 HTTPS 改成 HTTP，或把目标域名替换为固定 IP。它们会改变连接语义，可能绕开原本需要保留的身份与路由条件。对企业入口，应由维护者修复证书和域名配置。

## 修复后怎么验证

在原来失败的运行环境中重试，确认 HTTPS 校验保持启用且不再报证书错误。若随后收到 401 或其他正常 HTTP 错误，说明连接已经越过 TLS 阶段，但业务鉴权仍需单独处理。

最后验证原应用，而不只验证终端脚本；检查异步任务、定时任务和容器是否使用相同的可信配置。官方补充见 [OpenAI Python 客户端文档](https://github.com/openai/openai-python)。本文仅执行本地上下文断言，没有向付费 API 发起测试请求。

## 提问出处与官方依据

- [独立问题线索 1](https://community.openai.com/t/certificate-verify-failed/117006)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [独立问题线索 2](https://community.openai.com/t/ssl-certificate-verify-failed/32442)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [HTTPX 官方文档](https://www.python-httpx.org/advanced/ssl/)：按当前页面核对解决步骤。历史提问不代表当前所有环境都存在同一问题。

如需要进一步比较云端接口，可[注册 OpenLux 并核对适用能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-python-certificate-verify-failed-fix&utm_content=footer)。切换服务前单独验证接口与账户配置，不能据此认定原服务的问题已经修复。

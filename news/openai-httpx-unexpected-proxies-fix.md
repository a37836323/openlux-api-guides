---
layout: default
title: "OpenAI Python 报 unexpected keyword argument proxies 怎么解决？"
description: "客户端还没发请求就报 proxies 参数错误？区分依赖不兼容与网络代理故障。"
permalink: /news/openai-httpx-unexpected-proxies-fix/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[HTTPX 官方发布说明](https://github.com/encode/httpx/releases/tag/0.28.0)

# OpenAI Python 报 unexpected keyword argument proxies 怎么解决？

如果在创建 `OpenAI` 或 `AsyncOpenAI` 客户端时出现 `unexpected keyword argument 'proxies'`，先检查 OpenAI SDK、HTTPX 和上层框架的版本组合。它可能是本地依赖之间传递了已经移除的参数，此时请求还没发送，修改 API Key、余额或模型通常没有帮助。

资料核验：2026 年 9 月 12 日。若准备评估云端 API，可[查看 OpenLux 的账户与可用模型](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-httpx-unexpected-proxies-fix&utm_content=intro)。OpenLux 是独立服务，具体接口、计费和功能以其当前说明为准。

## 这类错误为什么突然出现

OpenAI Python 仓库在 2024 年 11 月有两条独立报告：一条来自同步客户端，另一条来自异步客户端，均涉及旧 SDK 与 HTTPX 0.28 的组合。HTTPX 官方 0.28.0 发布说明确认移除了此前弃用的 `proxies` 参数。

这些历史版本说明了一个可核对的兼容性原因，不代表今天所有报错都来自同一版本。你自己的封装层、代理配置代码或其他调用 HTTPX 的库，也可能继续传入这个字段。

## 先看调用栈，不要只看最后一行

| 失败位置 | 更可能需要检查 | 判断依据 |
|---|---|---|
| `Client.__init__` | 依赖和构造参数 | 客户端初始化即失败 |
| `AsyncClient.__init__` | 异步客户端及上层封装 | 请求方法尚未执行 |
| 自己代码中的 `httpx.Client` | 是否还传 `proxies=` | 错误参数来自本地代码 |
| 建立连接后报 ProxyError | 代理地址、认证与网络 | 已越过参数检查阶段 |

保存最早指向业务代码或依赖的栈帧，能判断参数是谁传入的。不要把“unexpected keyword”与代理服务无法连接混为一类：两者需要改变的位置不同。

## 核对实际加载的版本与签名

在报错进程使用的解释器中检查版本。IDE 终端、Notebook 内核和容器可能有独立依赖；升级宿主机的包，不会自动更新容器镜像。

```python
from importlib import metadata
import inspect

def version_of(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "未安装"

for name in ("openai", "httpx", "httpcore", "langchain-openai"):
    print(name, version_of(name))

def accepts_named_parameter(factory, name):
    return name in inspect.signature(factory).parameters

def example_client(*, proxy=None):
    return proxy

assert accepts_named_parameter(example_client, "proxy")
assert not accepts_named_parameter(example_client, "proxies")
```

这里仅演示读取版本和检查参数，没有建立网络连接。实际排错时，还应对安装环境中的 `httpx.Client` 和相关封装检查签名或源代码。输出中不要包含代理密码和完整环境变量。

## 应该升级哪些依赖

如果参数由旧 SDK 或上层框架传入，优先在独立测试环境中更新兼容的依赖组合，而不是只更新 HTTPX。阅读项目的依赖约束，保存升级前锁文件，再运行 `python -m pip check` 检查已声明的依赖冲突。

`pip check` 通过并不代表运行时完全兼容，因为库的版本范围可能比实际支持范围宽。仍应验证客户端初始化，再用小请求检查正常和异常路径。异步应用还要单独验证异步客户端，不能只靠同步测试推断。

已有项目暂时无法升级时，可以恢复此前确认能运行的锁定组合，并记录迁移事项。不要直接修改 `site-packages` 中的一行代码后就结束，下一次部署可能覆盖修改，其他调用路径也可能没有同步处理。

## 自己写的代理配置怎样调整

HTTPX 当前代理文档展示了 `proxy` 和基于 `mounts` 的配置方式。它们不意味着应该全局把项目里每个 `proxies` 字符串改为 `proxy`：不同库的参数定义并不相同，应在实际 HTTPX 客户端构造位置处理。

OpenAI SDK 如需自定义 HTTP 客户端，应查官方仓库的 `http_client` 配置示例。业务层、SDK 层和 HTTP 客户端层各自接收什么参数，要分开确认。代理 URL 的协议、地址和认证配置属于后续检查，不能用于解释初始化阶段的 Python 参数错误。

代理说明见 [HTTPX 官方代理文档](https://www.python-httpx.org/advanced/proxies/)，SDK 接入方式见 [OpenAI Python 官方仓库](https://github.com/openai/openai-python)。

## 怎样确认不会部署后再次出现

修复后保存完整依赖锁定结果，并在与生产相同的运行方式下验证。确保构建镜像使用更新后的锁文件，服务重启后再次读取实际版本。只在本机临时安装成功，不能证明服务器已经采用相同组合。

最终应确认三件事：客户端初始化不再失败、请求能够发出、应用能正确处理响应。若出现证书错误，可转到[HTTPS 证书链排查](../openai-python-certificate-verify-failed-fix/)；若出现额度不足，则转到[API 计费与额度排查](../chatgpt-plus-api-insufficient-quota/)。保留新的错误边界，避免继续围绕已经解决的参数名打转。

## 提问出处与官方依据

- [独立问题线索 1](https://github.com/openai/openai-python/issues/1903)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [独立问题线索 2](https://github.com/openai/openai-python/issues/1908)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [HTTPX 官方发布说明](https://github.com/encode/httpx/releases/tag/0.28.0)：按当前页面核对解决步骤。历史提问不代表当前所有环境都存在同一问题。

如需要进一步比较云端接口，可[注册 OpenLux 并核对适用能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=openai-httpx-unexpected-proxies-fix&utm_content=footer)。切换服务前单独验证接口与账户配置，不能据此认定原服务的问题已经修复。

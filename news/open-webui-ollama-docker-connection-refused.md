---
layout: default
title: "Open WebUI 连不上 Ollama？Docker localhost 与 11434 排查"
description: "从实际发请求的容器检查 Ollama 地址、解析、监听和持久化连接配置。"
permalink: /news/open-webui-ollama-docker-connection-refused/
date: 2026-09-12
---

> 更新日期：2026-09-12 · 一手来源：[Open WebUI 官方文档](https://docs.openwebui.com/troubleshooting/connection-error/)

# Open WebUI 连不上 Ollama？Docker localhost 与 11434 排查

如果 Open WebUI 在 Docker 中运行，而 Ollama 在宿主机上，配置里的 `localhost` 通常指向 WebUI 容器自身。先从实际发起请求的容器检查目标地址，再核对 Ollama 的监听地址和端口。浏览器能打开 WebUI，不等于 WebUI 后端能连接模型服务。

资料核验：2026 年 9 月 12 日。若准备评估云端 API，可[查看 OpenLux 的账户与可用模型](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=open-webui-ollama-docker-connection-refused&utm_content=intro)。OpenLux 是独立服务，具体接口、计费和功能以其当前说明为准。

## 用户实际遇到的现象

Open WebUI 仓库有连接挂起的 issue，也有“模型列表不显示”的独立提问，日志中出现连接 `host.docker.internal:11434` 被拒绝。标题看起来像界面故障，底层可能仍是后端无法连接 Ollama。

历史 issue 的客户端版本只说明报告环境。本文按当前 Open WebUI、Ollama 和 Docker 官方文档排查网络边界，不把某个旧版本的缺陷当作所有连接失败的原因。

## 先画清楚服务分别运行在哪里

| 部署方式 | WebUI 应连接的位置 | 最容易填错的地址 |
|---|---|---|
| 两个进程都在同一宿主机 | 该主机上的 Ollama 地址 | 实际使用了另一台机器地址 |
| WebUI 在容器，Ollama 在宿主机 | 容器能够访问的宿主机地址 | 容器里的 localhost |
| 两者在同一 Docker 网络 | Ollama 服务名与内部端口 | 宿主机映射端口或错误服务名 |
| Ollama 在远端服务器 | 受控网络中的远端地址 | 本地电脑的回环地址 |

Docker Desktop 文档提供 `host.docker.internal` 作为访问宿主机服务的方式。Linux Docker Engine 的环境可能需要额外的主机映射或不同网络安排，不能假设每台机器都自动解析相同名称。

## 先分辨拒绝连接、超时和解析失败

连接被拒绝时，重点确认目标主机和端口是否有服务监听，以及防火墙是否主动拒绝。域名解析失败时，先检查容器 DNS 或主机映射。超时可能涉及网络路径、防火墙或服务无响应，应结合日志判断。

在宿主机能访问而容器不能访问时，优先排查两者之间的网络，而不是反复拉取模型。模型还没下载与 TCP 无法连接是不同阶段，修改模型名称不会让一个没有监听的端口突然可用。

如果容器已安装 curl，可从容器内对实际地址发起只读检查。不要为了测试重建整个应用或删除数据卷；缺少工具时，使用已有的运行环境或经过确认的诊断容器。

## 核对 Ollama 的监听与启动环境

Ollama 官方 FAQ 说明可以用 `OLLAMA_HOST` 配置服务监听。若服务只监听宿主机回环地址，桥接网络中的容器可能无法通过宿主机网络地址访问。需要按部署方式调整可达地址，并限制允许访问的网络范围。

配置环境变量应放在实际启动服务的位置。systemd 服务、桌面应用与手工 shell 启动的环境可能不同。修改 shell 配置文件但没有改变服务环境，可能不会影响已经运行的 Ollama。

按官方步骤重启服务后，再从原来失败的位置检查连接。若为容器通信开放了更广的监听地址，同时确认防火墙或网络隔离，避免让模型服务意外暴露到公网。

## host 网络和桥接网络不要混着理解

Open WebUI 文档给出了 host 网络的部署示例。Linux 上采用 host 网络后，服务与端口行为不同于普通桥接端口映射；应按所选方式访问，不要继续照搬原来的端口假设。

桥接网络中，宿主机映射和容器间服务名属于另一套连接方式。两者都可以用于合适的部署，关键是选择一套明确的网络路径，并从发请求的一端验证。不要同时加入多个冲突地址，再靠随机重启判断哪一个有效。

## 改了环境变量，为什么界面仍用旧地址

当前 Open WebUI 文档指出，保存到数据库的连接配置可能优先于环境变量。先在管理连接设置中核对实际保存的地址，纠正不可达入口，再保存并重新测试。

如果界面已经无法进入，先备份数据，再按当前官方恢复配置说明处理。不要为了修一个连接地址删除整个数据卷，聊天记录和用户设置可能也在里面。日志显示的目标地址比你打算使用的配置更能说明实际行为。

## 怎样确认完全恢复

先确认 WebUI 后端可以连接 Ollama，再确认模型列表出现，最后发起一条简短对话并检查正常结束。如果只修复列表加载，生成请求仍可能在其他参数或资源限制上失败，应继续按新错误处理。

官方补充：[Ollama FAQ](https://docs.ollama.com/faq)、[Docker Desktop 网络说明](https://docs.docker.com/desktop/features/networking/)。本文给出排查顺序，没有替读者修改本地网络或调用模型。

## 提问出处与官方依据

- [独立问题线索 1](https://github.com/open-webui/open-webui/issues/2337)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [独立问题线索 2](https://github.com/open-webui/open-webui/issues/4373)：仅作为用户遇到问题的证据，回复不直接等同官方结论。
- [Open WebUI 官方文档](https://docs.openwebui.com/troubleshooting/connection-error/)：按当前页面核对解决步骤。历史提问不代表当前所有环境都存在同一问题。

如需要进一步比较云端接口，可[注册 OpenLux 并核对适用能力](https://api.openlux.ai/register?channel=c_lkv0gzwj&utm_source=content_site&utm_medium=article&utm_campaign=open-webui-ollama-docker-connection-refused&utm_content=footer)。切换服务前单独验证接口与账户配置，不能据此认定原服务的问题已经修复。

#!/usr/bin/env python3
"""Build the OpenLux API problem-solving guide hub as plain static HTML."""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).parent
OUT = ROOT / "dist"
SITE = "https://openlux-api-guides.pages.dev"
REGISTER = "https://api.openlux.ai/register?channel=c_8qh1bdxz"
UPDATED = "2026-08-08"
INDEXNOW_KEY = "71c6e4e8203d49768f4f4f2cc93d896a"

PAGES = [
  {
    "slug": "claude-code-relay-setup",
    "title": "Claude Code 国内中转配置：Windows、macOS、Linux 完整步骤",
    "desc": "用 ANTHROPIC_BASE_URL 和 ANTHROPIC_AUTH_TOKEN 配置 Claude Code 中转，并用最短命令验证连接。",
    "answer": "先准备兼容 Anthropic Messages API 的地址和密钥，再把它们写入 Claude Code 的环境变量。OpenLux 的基础地址填写 https://api.openlux.ai，不要自行追加 /v1/messages。",
    "sections": [
      ("1. 安装并确认 Claude Code", '<pre><code>npm install -g @anthropic-ai/claude-code\nclaude --version</code></pre><p>官方当前还提供原生安装方式；如果已经安装，先执行 <code>claude update</code>。</p>'),
      ("2. macOS / Linux 配置", '<pre><code>export ANTHROPIC_BASE_URL="https://api.openlux.ai"\nexport ANTHROPIC_AUTH_TOKEN="你的 API Key"\nclaude</code></pre><p>需要永久生效时，把前两行加入 <code>~/.zshrc</code> 或 <code>~/.bashrc</code>，然后重新打开终端。</p>'),
      ("3. Windows PowerShell 配置", '<pre><code>$env:ANTHROPIC_BASE_URL="https://api.openlux.ai"\n$env:ANTHROPIC_AUTH_TOKEN="你的 API Key"\nclaude</code></pre><p>永久保存可用 <code>[Environment]::SetEnvironmentVariable</code>，保存后必须新开 PowerShell 窗口。</p>'),
      ("4. 30 秒验证", '<pre><code>claude -p "只回复 OK"</code></pre><p>返回内容说明链路可用。401 优先检查 Key；404 检查地址是否多写路径；超时先用 <code>curl -I https://api.openlux.ai</code> 检查网络。</p>'),
      ("安全提醒", '<p>API Key 只放在本机环境变量或密钥管理器里，不要提交到 Git、截图或粘贴进公开日志。中转服务属于第三方网关，处理敏感代码前应评估数据与合规要求。</p>'),
    ],
    "faqs": [("BASE_URL 后面要加 /v1 吗？", "Claude Code 这里使用服务基础地址；OpenLux 配置为 https://api.openlux.ai。不要自行追加 /v1/messages。"), ("为什么设置后仍访问旧地址？", "通常是旧终端没有重新加载变量，或项目/用户设置覆盖了环境变量。新开终端并按排查页逐项检查。")],
  },
  {
    "slug": "anthropic-base-url-not-working",
    "title": "ANTHROPIC_BASE_URL 不生效：7 项排查清单",
    "desc": "Claude Code 仍走官方地址、环境变量不生效或请求 404 时的逐项排查方法。",
    "answer": "最常见的原因不是中转故障，而是变量只写进了另一个终端、变量名拼错、旧进程未重启，或 BASE_URL 末尾多加了接口路径。按下面顺序查，能避免盲目重装。",
    "sections": [
      ("1. 确认当前进程真的读到了变量", '<pre><code># macOS / Linux\nprintf \'%s\\n\' "$ANTHROPIC_BASE_URL"\n\n# PowerShell\n$env:ANTHROPIC_BASE_URL</code></pre><p>期望值为 <code>https://api.openlux.ai</code>。空值说明配置根本没进入当前终端。</p>'),
      ("2. 排除错误路径", '<p>只填基础地址，不要写成 <code>https://api.openlux.ai/v1/messages</code>。网关会根据 Claude Code 的请求自动拼接接口路径。多写路径通常导致 404。</p>'),
      ("3. 检查认证变量", '<pre><code># 只确认是否存在，不要把 Key 输出到日志\ntest -n "$ANTHROPIC_AUTH_TOKEN" &amp;&amp; echo TOKEN_SET</code></pre><p>Claude Code 网关可使用 <code>ANTHROPIC_AUTH_TOKEN</code>。注意不要把 OpenAI 客户端的变量名直接照搬过来。</p>'),
      ("4. 彻底重启进程", '<p>退出所有 Claude Code 会话并新开终端。VS Code 内置终端是在 VS Code 启动时继承环境的，必要时连编辑器一起重启。</p>'),
      ("5. 网络与状态码定位", '<pre><code>curl -I --max-time 10 https://api.openlux.ai\nclaude -p "只回复 OK"</code></pre><ul><li>401/403：密钥、余额或权限；</li><li>404：Base URL 或模型路由；</li><li>429：额度或速率限制；</li><li>连接超时：DNS、代理或防火墙。</li></ul>'),
      ("6. 更新并诊断客户端", '<pre><code>claude update\nclaude doctor</code></pre><p>如果同一组变量在另一个设备可用，优先检查本机版本、证书和代理环境，而不是反复换 Key。</p>'),
    ],
    "faqs": [("变量名区分大小写吗？", "在 macOS 和 Linux 上区分，必须准确写成 ANTHROPIC_BASE_URL。"), ("能同时设置 HTTPS_PROXY 吗？", "可以，但它是网络代理，与 LLM 网关地址不是同一概念；错误代理也可能造成超时。")],
  },
  {
    "slug": "organization-disabled",
    "title": "Claude API 报 organization has been disabled 怎么处理",
    "desc": "解释 organization has been disabled 的含义、先做哪些账户检查，以及如何避免无效重试。",
    "answer": "这通常表示上游组织账户被停用，不是代码语法错误。换模型、重装 SDK、连续重试一般不会恢复账户；应先确认错误来自哪个服务商，再走该服务商的账户申诉或更换合法可用的 API 通道。",
    "sections": [
      ("先确定错误来自哪里", '<p>记录 HTTP 状态码、请求域名、响应中的 request ID 和发生时间，但必须删除 API Key、Cookie 与业务数据。直连 Anthropic 时联系 Anthropic；通过第三方网关时先查网关控制台和公告。</p>'),
      ("不要做的三件事", '<ul><li>不要把 API Key 发给陌生人“代查”；</li><li>不要无限重试，可能继续触发风控或消耗额度；</li><li>不要把账户停用误判成模型不存在。</li></ul>'),
      ("可执行处理顺序", '<ol><li>在服务商控制台确认组织状态、账单和通知邮件；</li><li>保存脱敏后的 request ID，向对应支持渠道申诉；</li><li>业务必须恢复时，切换到你有权使用且状态正常的通道；</li><li>恢复后轮换曾暴露的 Key，并做一次最小请求验证。</li></ol>'),
      ("切换网关后的 Claude Code 配置", '<pre><code>export ANTHROPIC_BASE_URL="https://api.openlux.ai"\nexport ANTHROPIC_AUTH_TOKEN="新通道的 API Key"\nclaude -p "只回复 OK"</code></pre><p>第三方网关不是解封原组织，而是另一条独立调用路径。使用前应查看服务条款、数据处理方式和实际模型可用性。</p>'),
    ],
    "faqs": [("换一个 API Key 能解决吗？", "如果 Key 仍属于同一个被停用组织，通常不能；需处理组织状态或使用独立且合规的通道。"), ("这是代码 Bug 吗？", "通常不是。先根据响应域名与 request ID 确认错误来源。")],
  },
  {
    "slug": "cline-api-error",
    "title": "Cline API Error 排查：401、404、429 和连接失败",
    "desc": "Cline 配置 OpenAI Compatible 服务时，从 Base URL、API Key、Model ID 到错误码的完整排查。",
    "answer": "Cline 的 OpenAI Compatible 配置必须同时匹配 Base URL、API Key 和 Model ID。OpenLux 的 Base URL 填 https://api.openlux.ai/v1；模型名应从当前模型列表选择，不要凭记忆输入。",
    "sections": [
      ("正确配置位置", '<ol><li>打开 Cline，点击设置齿轮；</li><li>API Provider 选择 <strong>OpenAI Compatible</strong>；</li><li>Base URL 填 <code>https://api.openlux.ai/v1</code>；</li><li>填入 API Key；</li><li>填写控制台当前可用的 Model ID，然后 Verify。</li></ol>'),
      ("先用 curl 隔离客户端问题", '<pre><code>curl https://api.openlux.ai/v1/models \\\n  -H "Authorization: Bearer 你的_API_Key"</code></pre><p>能返回模型列表而 Cline 失败，问题更可能在 Cline 的 Provider 或 Model ID 配置。不要公开粘贴完整返回中的敏感字段。</p>'),
      ("按状态码处理", '<ul><li><strong>401/403</strong>：Key 错误、失效或无权限；</li><li><strong>404</strong>：Base URL 路径或 Model ID 不匹配；</li><li><strong>429</strong>：余额、并发或速率限制；</li><li><strong>5xx</strong>：记录 request ID，稍后重试并查看服务状态；</li><li><strong>超时</strong>：先检查 DNS、防火墙及系统代理。</li></ul>'),
      ("仍失败时收集这些信息", '<p>保留 Cline 版本、Provider、脱敏后的 URL、Model ID、状态码、request ID 与发生时间。永远不要在工单、群聊或截图中展示完整 Key。</p>'),
    ],
    "faqs": [("Base URL 要不要加 /v1？", "Cline 的 OpenAI Compatible 配置中，OpenLux 使用 https://api.openlux.ai/v1。"), ("为什么 Verify 成功但对话失败？", "常见原因是所选模型不支持当前工具调用、上下文超限或账户额度变化；查看实际响应状态码。")],
  },
  {
    "slug": "cherry-studio-claude-api",
    "title": "Cherry Studio 配置 Claude API 中转：地址、密钥、模型",
    "desc": "在 Cherry Studio 中使用 OpenAI 兼容方式配置 Claude 模型，并验证模型列表和常见错误。",
    "answer": "在 Cherry Studio 新增 OpenAI 兼容服务商，API 地址使用 https://api.openlux.ai/v1，填入 API Key 后获取或手动添加当前可用的 Claude Model ID，再做连通性测试。",
    "sections": [
      ("配置步骤", '<ol><li>打开设置中的模型服务；</li><li>新增自定义或 OpenAI 兼容服务商；</li><li>API 地址填 <code>https://api.openlux.ai/v1</code>；</li><li>粘贴 API Key；</li><li>获取模型列表，选择名称含 Claude 的可用模型；</li><li>点击连接测试并发起一条最短对话。</li></ol>'),
      ("模型列表取不到怎么办", '<pre><code>curl https://api.openlux.ai/v1/models \\\n  -H "Authorization: Bearer 你的_API_Key"</code></pre><p>curl 也返回 401 时先换正确 Key；curl 正常但客户端失败时，检查地址有没有重复出现 <code>/v1/v1</code>。</p>'),
      ("模型 ID 不要猜", '<p>模型上下线和命名可能变化，以实时模型列表及产品控制台为准。仅凭网上教程复制旧 Model ID，容易得到 404 或 model not found。</p>'),
      ("密钥与隐私", '<p>只在可信设备保存 Key，不要同步进公开配置仓库。第三方客户端和网关都会参与请求链路，发送公司代码、个人信息或密钥前先确认适用的安全政策。</p>'),
    ],
    "faqs": [("API 地址为什么要带 /v1？", "OpenAI 兼容客户端通常从 /v1 下调用 models 和 chat/completions。"), ("能把同一个 Key 分享给多人吗？", "不建议。应按人员或设备创建独立 Key，便于限额、审计和撤销。")],
  },
]

CSS = """*{box-sizing:border-box}body{margin:0;background:#f7f8fc;color:#172033;font:16px/1.75 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#315ee7}.wrap{max-width:920px;margin:auto;padding:0 22px}header{background:#111936;color:#fff}header .wrap{padding-top:18px;padding-bottom:18px;display:flex;justify-content:space-between;gap:20px;align-items:center}header a{color:#fff;text-decoration:none}.brand{font-weight:800;font-size:20px}.hero{padding:58px 0 38px;background:linear-gradient(135deg,#111936,#263b85);color:#fff}.hero h1{font-size:clamp(30px,5vw,48px);line-height:1.2;margin:0 0 18px}.hero p{max-width:760px;font-size:18px}.main{padding:34px 22px 70px}article,.card,.quick{background:white;border:1px solid #e4e7f0;border-radius:14px;padding:25px;margin:0 0 20px;box-shadow:0 4px 18px #15204a0a}.quick{border-left:5px solid #315ee7}.quick h2{margin-top:0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}.grid .card{margin:0}.card h2{font-size:20px;line-height:1.4;margin-top:0}h2{line-height:1.35;margin-top:32px}pre{overflow:auto;background:#111936;color:#f1f5ff;padding:16px;border-radius:9px;line-height:1.55}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}.cta{background:#eaf0ff;border-radius:12px;padding:20px;margin:30px 0}.button{display:inline-block;background:#315ee7;color:#fff;text-decoration:none;padding:10px 17px;border-radius:8px;font-weight:700}.meta{color:#697386;font-size:14px}.crumb{margin-bottom:18px;font-size:14px}footer{border-top:1px solid #e1e4ec;padding:28px 0;color:#687188}.refs{font-size:14px}ul,ol{padding-left:24px}@media(max-width:600px){header .wrap{align-items:flex-start;flex-direction:column}.hero{padding-top:38px}}"""

def layout(title, desc, body, canonical, schema):
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><meta name="description" content="{escape(desc)}"><link rel="canonical" href="{canonical}"><link rel="stylesheet" href="/assets/style.css"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script></head><body><header><div class="wrap"><a class="brand" href="/">OpenLux API 实战指南</a><nav><a href="https://doc.openlux.ai">API 文档</a>　<a href="https://api.openlux.ai">控制台</a></nav></div></header>{body}<footer><div class="wrap">独立问题解决指南 · 更新于 {UPDATED} · 配置与模型可用性以产品控制台和官方文档为准</div></footer></body></html>'''

def build():
    OUT.mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets/style.css").write_text(CSS, encoding="utf-8")
    cards = ''.join(f'<article class="card"><h2><a href="/{p["slug"]}/">{escape(p["title"])}</a></h2><p>{escape(p["desc"])}</p><a href="/{p["slug"]}/">查看解决步骤 →</a></article>' for p in PAGES)
    home_body = f'<section class="hero"><div class="wrap"><h1>AI API 配置，不再靠猜</h1><p>围绕 Claude Code、Cline 和桌面客户端的真实报错，给出可以复制、可以验证的处理步骤。</p></div></section><main class="wrap main"><div class="grid">{cards}</div><div class="cta"><h2>需要一个兼容 API 通道？</h2><p>先查看实时模型、价格和开发文档，再决定是否使用。不要在网页或聊天中分享 API Key。</p><a class="button" href="{REGISTER}" rel="nofollow sponsored">查看 OpenLux 控制台</a>　<a href="https://doc.openlux.ai">阅读 API 文档</a></div></main>'
    schema = {"@context":"https://schema.org","@type":"WebSite","name":"OpenLux API 实战指南","url":SITE}
    (OUT / "index.html").write_text(layout("OpenLux API 实战指南：Claude Code 与 AI 客户端排错", "Claude Code、Cline、Cherry Studio API 中转配置和错误排查指南。", home_body, SITE+"/", schema), encoding="utf-8")
    for p in PAGES:
        url = f'{SITE}/{p["slug"]}/'
        sections = ''.join(f'<h2>{title}</h2>{html}' for title, html in p["sections"])
        faq_html = ''.join(f'<h3>{escape(q)}</h3><p>{escape(a)}</p>' for q,a in p["faqs"])
        body = f'<section class="hero"><div class="wrap"><div class="crumb"><a href="/">首页</a> / 配置排错</div><h1>{escape(p["title"])}</h1><p>{escape(p["desc"])}</p><div class="meta">更新：{UPDATED}</div></div></section><main class="wrap main"><div class="quick"><h2>直接答案</h2><p>{escape(p["answer"])}</p></div><article>{sections}<div class="cta"><h2>继续操作</h2><p>先看实时模型和官方接口文档；注册后请妥善保管 Key。</p><a class="button" href="{REGISTER}" rel="nofollow sponsored">打开 OpenLux</a>　<a href="https://doc.openlux.ai">API 文档</a></div><h2>常见问题</h2>{faq_html}<h2>参考资料</h2><p class="refs"><a href="https://docs.anthropic.com/en/docs/claude-code/llm-gateway">Anthropic：LLM gateway configuration</a> · <a href="https://docs.cline.bot/provider-config/openai-compatible">Cline：OpenAI Compatible</a></p></article></main>'
        schema = [{"@context":"https://schema.org","@type":"TechArticle","headline":p["title"],"description":p["desc"],"dateModified":UPDATED,"mainEntityOfPage":url,"author":{"@type":"Organization","name":"OpenLux API 实战指南"}}, {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in p["faqs"]]}]
        d = OUT / p["slug"]
        d.mkdir(exist_ok=True)
        (d / "index.html").write_text(layout(p["title"],p["desc"],body,url,schema), encoding="utf-8")
    urls = [SITE+"/"]+[f'{SITE}/{p["slug"]}/' for p in PAGES]
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{u}</loc><lastmod>{UPDATED}</lastmod></url>' for u in urls)+'</urlset>', encoding="utf-8")
    (OUT / "robots.txt").write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n', encoding="utf-8")
    (OUT / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    (OUT / "404.html").write_text(layout("页面未找到", "页面不存在", '<main class="wrap main"><article><h1>页面未找到</h1><p><a href="/">返回指南首页</a></p></article></main>', SITE+"/404.html", {}), encoding="utf-8")
    print(f"built {len(PAGES)+1} pages in {OUT}")

if __name__ == "__main__": build()

# B 组 AI 日报 DeepSeek 配置指引（2026-07-12）

> **发给**：B 苏哲勋（云服务器运维）  
> **协同**：E 刘帅华 / A 牛雨昊（日报 API 与验收）  
> **服务器**：`152.136.29.158`  
> **用途**：在云服务器启用 **AI 监控日报** 的大模型生成（DeepSeek）  
> **预计耗时**：约 5 分钟

---

## 1. 背景说明

### 1.1 当前状态

| 项目 | 状态 |
|------|------|
| 日报 API | ✅ 已部署（`/api/reports/daily/`） |
| 前端页面 | ✅ `DailyReport.vue` 可用 |
| 数据统计 | ✅ 从告警/事件表真实汇总 |
| **LLM 文案生成** | ❌ 未配 Key，目前走**规则模板** |

未配置时，生成日报仍可用，但页面提示为「日报已生成（规则模板）」，答辩演示效果较弱。

### 1.2 配置后的效果

配置 DeepSeek API Key 后：

- 后端调用 OpenAI 兼容接口生成 Markdown 日报
- 数据库 `daily_report.source` 记为 `ai`
- 前端提示 **「AI 日报已生成」**

### 1.3 代码位置（无需改代码）

| 文件 | 说明 |
|------|------|
| `backend/apps/reports/services.py` | 读取环境变量，调用 LLM |
| `deploy/home-camera-backend.service` | 通过 `EnvironmentFile` 加载 `.env.production` |
| `backend/.env.example` | 变量说明与示例 |

逻辑简述：

```text
有 DAILY_REPORT_AI_API_KEY → 调 DeepSeek Chat Completions → source=ai
无 Key 或调用失败           → 规则模板 build_template_report() → source=template
```

---

## 2. 配置步骤

### 2.1 SSH 登录服务器

```bash
ssh root@152.136.29.158
cd /service/home-camera-monitor/backend
```

### 2.2 编辑生产环境变量文件

```bash
vim .env.production
# 或: nano .env.production
```

在文件**末尾**追加以下内容（Key 向 **E/A 组私聊索取**，勿发到群聊）：

```env
# ── AI 监控日报（DeepSeek）────────────────────────────
DAILY_REPORT_AI_API_KEY=<私聊 E/A 组获取，格式 sk-...>
DAILY_REPORT_AI_BASE_URL=https://api.deepseek.com/v1
DAILY_REPORT_AI_MODEL=deepseek-chat
DAILY_REPORT_AI_TIMEOUT=30
```

> **说明**：接口为 OpenAI 兼容格式，无需安装额外 SDK；`services.py` 使用标准库 `urllib` 调用。

### 2.3 重启后端服务

```bash
sudo systemctl restart home-camera-backend
sudo systemctl status home-camera-backend --no-pager
```

确认服务状态为 `active (running)`。

### 2.4 可选：命令行快速验证 Key 是否有效

在服务器 `backend` 目录下（需已激活 conda 环境 `home-camera`）：

```bash
python -c "
import json, os, urllib.request
from pathlib import Path

# 手动加载 .env.production（与 systemd 行为一致）
for line in Path('.env.production').read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip())

key = os.getenv('DAILY_REPORT_AI_API_KEY', '')
req = urllib.request.Request(
    os.getenv('DAILY_REPORT_AI_BASE_URL', 'https://api.deepseek.com/v1').rstrip('/') + '/chat/completions',
    data=json.dumps({
        'model': os.getenv('DAILY_REPORT_AI_MODEL', 'deepseek-chat'),
        'messages': [{'role': 'user', 'content': '回复 OK'}],
        'max_tokens': 5,
    }).encode(),
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    method='POST',
)
with urllib.request.urlopen(req, timeout=15) as resp:
    print('DeepSeek 连通性:', resp.status)
"
```

期望输出：`DeepSeek 连通性: 200`

---

## 3. 功能验收

### 3.1 前端验收（A/E 组执行）

1. 登录 `http://152.136.29.158`（演示账号 `15333601865` / `123456`）
2. 左侧菜单 → **监控日报**
3. 选择日期 → 点击 **生成 AI 日报**
4. 确认：
   - 顶部提示为 **「AI 日报已生成」**（非「规则模板」）
   - 正文为自然语言 Markdown，非固定七段模板
   - 「重点事件回放」表格有数据（若当日有告警）

### 3.2 API 验收（可选）

先登录拿 Token，再触发生成：

```bash
# 1. 登录
curl -s -X POST http://127.0.0.1/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"15333601865","password":"123456"}'

# 2. 生成日报（将 <TOKEN> 替换为上一步 access）
curl -s -X POST http://127.0.0.1/api/reports/daily/generate/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-07-12"}'
```

检查返回 JSON 中：

```json
{
  "source": "ai",
  "title": "监控日报 2026-07-12",
  "summary": "# ..."
}
```

`source` 必须为 `"ai"`。

### 3.3 失败时的表现

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 仍显示「规则模板」 | Key 未写入或未重启 | 检查 `.env.production` 并 `systemctl restart` |
| 生成很慢后变模板 | DeepSeek 超时/余额不足 | 查 `journalctl -u home-camera-backend` 日志 |
| 401 / 403 | Key 错误或过期 | 联系 E/A 组换新 Key |
| 接口 500 | 后端异常 | `journalctl -u home-camera-backend -n 50 --no-pager` |

日志关键字：`AI 日报生成失败，将回退模板`

```bash
journalctl -u home-camera-backend -n 100 --no-pager | grep -i "日报\|DAILY_REPORT\|deepseek"
```

---

## 4. 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `DAILY_REPORT_AI_API_KEY` | ✅ | 无 | DeepSeek API Key；未设则走模板 |
| `DAILY_REPORT_AI_BASE_URL` | 否 | `https://api.openai.com/v1` | 生产请设为 `https://api.deepseek.com/v1` |
| `DAILY_REPORT_AI_MODEL` | 否 | `gpt-4o-mini` | 生产请设为 `deepseek-chat` |
| `DAILY_REPORT_AI_TIMEOUT` | 否 | `30` | 请求超时（秒） |

也可改用 OpenAI / 其他兼容网关，只需改 `BASE_URL` 和 `MODEL`。

---

## 5. 安全与协作

1. **API Key 勿提交 Git** — 只写在服务器 `.env.production`（已在 `.gitignore`）
2. **Key 私聊传递** — E/A 组单独发给 B，不要写在飞书公开文档或群消息里
3. **配完后回复** — B 在群里回复「AI 日报 Key 已配置 + 已重启」，A/E 做前端验收
4. **答辩后** — 建议在 DeepSeek 控制台轮换 Key

---

## 6. 协作分工

| 角色 | 负责人 | 事项 |
|------|--------|------|
| B 组 | 苏哲勋 | 写 `.env.production`、重启 `home-camera-backend` |
| E 组 | 刘帅华 | 提供 API Key、API 侧验收 |
| A 组 | 牛雨昊 | 前端「监控日报」页验收、答辩演示 |

---

## 7. 相关文档

| 文档 | 用途 |
|------|------|
| [B组-最新部署指引-20260712.md](./B组-最新部署指引-20260712.md) | 整体部署与联调验收 |
| [总体架构说明.md](../架构设计/总体架构说明.md) | 结题架构（含 reports 模块） |
| `backend/.env.example` | 本地开发变量模板 |

---

*编写：A 组 牛雨昊 · 2026-07-12*

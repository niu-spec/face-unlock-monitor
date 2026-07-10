# B 组下一步部署指引

> **发给**：B 苏哲勋（流媒体 / Nginx / 云服务器）  
> **日期**：2026-07-10  
> **背景**：A 组已在 `dev` 分支补完人脸画框与人数同步修复，**代码已 push 到 GitHub**，请 B 组部署到云服务器。

---

## 1. 本次更新内容（commit `cf90519`）

| 改动 | 说明 |
|------|------|
| 人脸画框 | C 组逻辑补全：`draw_face_boxes()` 统一绘制，MJPEG 应出现红/绿人脸框 |
| 人数同步 | `/api/video/status` 增加 `presence` 字段，与 MJPEG 同进程 |
| 前端人数 | 优先读视频后端的 presence，避免 Nginx 拆进程导致人数为 0 |
| AI 诊断 | MJPEG 画面左上角显示 `AI ok faces:N persons:N` |

**仓库地址**：
- GitHub：`https://github.com/niu-spec/home-camera-monitor` 分支 `dev`

---

## 2. 部署步骤（SSH 登录云服务器后执行）

```bash
# ① 进入项目目录（按实际路径调整）
cd /service/home-camera-monitor

# ② 拉取最新 dev 分支（历史若被重写，用 reset 而非 pull）
git fetch origin dev
git reset --hard origin/dev

# ③ 确认已拉到最新（应包含 cf90519）
git log -1 --oneline
# 期望输出：cf90519 fix(face): unify face box drawing and MJPEG presence sync

# ④ 激活 Python 环境（云上用的是 venv，不是 conda）
source backend/venv/bin/activate
pip install -r backend/requirements.txt -q

# ⑤ 检查 Django 配置
cd backend
python manage.py check

# ⑥ 重启视频后端
systemctl restart home-camera-backend
systemctl status home-camera-backend --no-pager
```

> ⚠️ **不要重启 `home-mediamtx`**，否则会断开所有 OBS 推流。

---

## 3. 部署后自测（在服务器上）

```bash
# 视频后端健康（8010）
curl -s http://127.0.0.1:8010/api/video/status | python3 -m json.tool

# 通过 Nginx 80 端口（前端实际访问路径）
curl -s http://127.0.0.1/api/video/status | python3 -m json.tool
curl -s http://127.0.0.1/api/home/presence/ | python3 -m json.tool
```

### 通过标准

| 检查项 | 期望 |
|--------|------|
| `workers.1.has_frame` | `true`（OBS 推流中） |
| `workers.1.last_processed_error` | `null` |
| `/api/video/status` 含 `presence` 字段 | 有，`updated_at` 非 null |
| 有人脸时 `presence.total` | ≥ 1 |
| `/api/auth/captcha/` | 200 |

---

## 4. 前端验收（部署完成后通知 A 组）

A 组会在本地前端验证，B 组部署完请告知一声。

A 组操作：
1. 打开 `http://localhost:5173/monitor`
2. OBS 推流（推流码 `1`）
3. 切换到 **「MJPEG 备用」**（WebRTC 无 AI 画框，属正常）
4. 对着摄像头露脸

### 期望现象

| 项目 | 正常表现 |
|------|----------|
| MJPEG 画面 | 红框（陌生人）或绿框（家人） |
| 左上角 | `AI ok faces:1 persons:N` + 绿色 `stream 1` |
| 右侧人数 | 总人数 ≥ 1 |

---

## 5. Nginx 配置（若部署后人数仍为 0 再检查）

若 MJPEG 有画框但前端人数仍为 0，检查 Nginx 是否把 `/api/home/` 指到了 `8000` 而非 `8010`。

**建议**：所有 `/api/` 与 `/video_feed/` 统一反代到 `8010`：

```nginx
location /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600;
}

location /api/ {
    proxy_pass http://127.0.0.1:8010/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

改完后：

```bash
nginx -t && nginx -s reload
```

---

## 6. 常见问题排查

```bash
# 查看 AI 处理日志
journalctl -u home-camera-backend -n 50 --no-pager | grep -iE "AI|face|失败|error"

# 确认 dlib 可用
source /service/home-camera-monitor/backend/venv/bin/activate
python -c "import dlib; import face_recognition; print('OK')"
```

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `git pull` 后 commit 不是 `cf90519` | 分支不对 | 确认 `git branch` 在 `dev` |
| MJPEG 有 `AI ok` 但 `faces:0` | 画面里没人脸 | 正常，对着摄像头试 |
| MJPEG 显示 `AI err` | AI 链报错 | 查 journalctl 日志 |
| 有画框但人数为 0 | Nginx 路由问题 | 见第 5 节 |
| 服务启动失败 | venv 缺依赖 | `pip install -r requirements.txt` |

---

## 7. 不需要做的

- ❌ 不需要新建 `face` 分支（代码已在 `dev` 上）
- ❌ 不需要对外开放 `8000` / `8010` 端口
- ❌ 不需要暴露 RTSP `8554` 到公网
- ❌ 不要随便重启 MediaMTX 容器

---

## 8. 完成后请回复 A 组

部署完成后，请告知：

1. `git log -1` 的 commit hash
2. `curl http://127.0.0.1/api/video/status` 中 `presence.total` 的值（有人脸时）
3. MJPEG 画面是否能看到人脸框

**联系人**：A 牛雨昊（前端 / 联调）

**详细背景文档**：[B组-AI联调待办.md](B组-AI联调待办.md)

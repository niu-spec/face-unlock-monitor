# B 组 AI 联调待办清单

> **负责人**：B 苏哲勋（流媒体 / Nginx / 云服务器）  
> **编制日期**：2026-07-09  
> **最后更新**：2026-07-09（B 组反馈「已完成」后的核对版）  
> **背景**：OBS 推流与 WebRTC 预览已正常，但 MJPEG 画面无 AI 画框、前端人数统计一直为 0。

---

## 0. B 组「已完成」核对结论（2026-07-09 实测）

B 组反馈已完成。对照云服务器实测与 `dev` 分支代码，结论如下：

### ✅ B 组已完成（可认可）

| 项 | 说明 |
|----|------|
| MediaMTX 推流 / WebRTC | `9090` / `8889` 正常 |
| MJPEG 视频流 | `/video_feed/1` 有画面，`has_frame: true` |
| dlib 环境 | 云上 `venv` 内 `dlib==19.24.6` 已安装（**非 conda**，路径 `/service/home-camera-monitor/backend/venv`） |
| 视频处理进程 | `8010` 上 `last_processed_error: null`，处理链无报错 |
| dlib 人脸画框（离线验证） | B 组称已生成测试图，说明 dlib 可画框 |

### ❌ 仍未通过验收（前端实测）

| 项 | 实测结果 | 说明 |
|----|----------|------|
| `/api/home/presence/` | `total: 0`，`updated_at: null` | **人数未写入**，右侧统计仍为 0 |
| MJPEG 实时 AI 画框 | 前端仍看不到框 | 可能只在离线测试图生效，未接入完整流水线 |
| 人体框 / 危险区域 | 未验证到 | C/D 的 `detection` 模块可能未部署到云 |
| `dev` 分支最新修复 | 未部署 | 云上 `/api/video/status` **无** `presence` 字段，**无** `AI ok faces:N` 诊断行 |

### 结论

> **B 组完成的是「流媒体 + dlib 环境 + 基础视频处理」，尚未完成「AI 结果同步到前端」的联调验收。**
>
> 人数为 0 的核心原因：云上视频处理**没有调用** `apps.face.services.process_frame()` 去更新内存中的 `presence`，或 `/api/home/presence/` 读到了另一个 Django 进程。

**不必改 Nginx 的前提**：若 `/api/home/presence/` 与 `/video_feed/` 已在同一 `8010` 进程，则问题在代码接入，而非 Nginx。当前 `updated_at: null` 说明 **`get_face_service().process_frame()` 未被成功执行或未部署 C 组代码**。

---

## 1. 问题现象

| 现象 | 状态 |
|------|------|
| OBS 推流 `rtmp://152.136.29.158:9090/stream/1` | ✅ 正常 |
| WebRTC 预览 `:8889/stream/1/` | ✅ 正常 |
| MJPEG `/video_feed/1` 有画面 | ✅ 正常 |
| MJPEG 左上角绿色 `stream 1` | ✅ 有（说明 `process_frame()` 在跑） |
| MJPEG AI 画框（人脸/人体） | ❌ 无 |
| `/api/home/presence/` 人数统计 | ❌ 一直为 0，`updated_at` 为 null |

---

## 2. 根因分析

### 2.1 Nginx 将 API 与视频拆到两个 Django 进程（主要问题）

云服务器当前架构：

| 端口 | 进程 | 职责 |
|------|------|------|
| `8010` | `home-camera-backend` | 视频拉流、MJPEG、**AI 处理**、人数内存快照 |
| `8000` | mini-rednote 主业务 | 登录、告警、家庭等业务 API |

若 Nginx 将 `/api/home/presence/` 反代到 `8000`，而 AI 在 `8010` 上更新人数，则：

- 前端读到的 `presence` **永远是初始值 0**
- `updated_at` 始终为 `null`（说明 AI 结果从未被 API 进程读到）

**判断依据**：`/api/video/status` 显示 `last_processed_error: null`（8010 上 AI 可能已在跑），但 `/api/home/presence/` 的 `updated_at` 仍为 null。

### 2.2 dlib 环境（B 组已完成）

云上实际使用 **venv**（非 conda `home-camera`）：

```bash
/service/home-camera-monitor/backend/venv
# dlib==19.24.6 已安装
```

验证命令（B 组已做过可跳过）：

```bash
source /service/home-camera-monitor/backend/venv/bin/activate
python -c "import dlib; import face_recognition; print('dlib OK')"
```

### 2.3 本地无法替代云端 AI

云 RTSP `8554` 不对外开放，前端开发者无法在本机拉流跑 AI，**必须在云服务器 `8010` 进程内完成 AI 联调**。

---

## 3. 剩余待办（B 组 + C 组协作）

### B 组 — P0：部署 `dev` 分支完整 AI 流水线

B 组当前的云上代码可能是**自定义简化版**（仅 dlib 画框），需合并 `dev` 分支中 C/D 已实现的完整链路：

```python
# backend/apps/video_stream/services.py 中应调用：
get_face_service().process_frame(...)      # C 组：人脸 + presence 更新
detection_service.detect_people(...)       # D 组：人体检测
detection_service.draw_overlays(...)       # D 组：画框
```

```bash
cd /service/home-camera-monitor
git fetch origin dev
git pull origin dev
source backend/venv/bin/activate          # 云上实际用 venv，不是 conda
pip install -r backend/requirements.txt -q
cd backend && python manage.py check
systemctl restart home-camera-backend
```

`dev` 分支部署后新增：

1. `/api/video/status` 带 `presence` 字段（同进程读人数，不依赖 Nginx）
2. MJPEG 画面诊断行：`AI ok faces:N persons:N` 或 `AI err`
3. `close_old_connections()` 修复后台线程数据库访问

---

### B 组 — P1：确认 `process_frame` 调用了 C 组人脸服务

云上若只写了独立 dlib 画框逻辑，**不会**更新 `presence`。必须走：

```
apps.face.services.get_face_service().process_frame()
  → 更新 self._presence
  → GET /api/home/presence/ 可读
```

本地自测命令（部署后在云上执行，OBS 推流中）：

```bash
curl -s http://127.0.0.1:8010/api/home/presence/
# 期望：updated_at 非 null；对着摄像头时 total >= 1
```

---

### C 组 — P0：确认人脸模块已合入并被 video_stream 调用

| 文件 | 职责 |
|------|------|
| `backend/apps/face/services.py` | `process_frame()` 检测人脸并更新 `_presence` |
| `backend/apps/video_stream/services.py` | 每帧调用 face + detection |

C 组确认 `feature/face` 已合并进 `dev` 且云上已 `git pull`。

---

### Nginx — 仅在必要时修改（非当前阻塞项）

**若** `/api/home/presence/` 与 `/video_feed/` 已同走 `8010`，**无需改 Nginx**。

**若** 部署 `dev` 后 `presence.updated_at` 仍为 null，再检查 Nginx 是否将 `/api/home/` 指到了 `8000`：

```nginx
# 已有（保留）
location /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600;
}

location /api/video/ {
    proxy_pass http://127.0.0.1:8010/api/video/;
}

# 需要新增或修改：所有业务 API 也走 8010
location /api/ {
    proxy_pass http://127.0.0.1:8010/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

> **注意**：若 `/api/` 与 `/api/video/` 同时存在，确保 `/api/video/` 的 `location` 块在 `/api/` 之前，或统一只保留 `/api/` 一条规则。

改完后执行：

```bash
nginx -t
nginx -s reload
# 或 systemctl reload nginx
```

---

### P1 — 查看 AI 处理日志（仍失败时）

```bash
journalctl -u home-camera-backend -n 100 --no-pager | grep -iE "AI|face|失败|error"
```

常见报错：

| 日志关键词 | 处理 |
|-----------|------|
| `face_recognition 未安装` | venv 内 `pip install face-recognition` 后重启 |
| `AI 处理链执行失败` + database | 确认已部署最新 `services.py`（含 `close_old_connections`） |
| 无报错但 `faces:0` | 非故障，被检测者需正对摄像头 |

---

## 4. 验证清单（B 组自测）

部署完成后，在服务器上执行：

```bash
# 1. 视频后端健康
curl -s http://127.0.0.1:8010/api/video/status | python3 -m json.tool

# 2. 通过 Nginx 80 端口访问（前端实际路径）
curl -s http://127.0.0.1/api/video/status | python3 -m json.tool
curl -s http://127.0.0.1/api/home/presence/ | python3 -m json.tool

# 3. 业务 API 不再 404
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/api/auth/captcha/
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/api/alerts/
```

**通过标准**：

| 检查项 | 期望 |
|--------|------|
| `workers.1.has_frame` | `true`（OBS 推流中） |
| `workers.1.last_processed_error` | `null` |
| `presence.updated_at` | 非 null（有人脸时 `total >= 1`） |
| `/api/auth/captcha/` | `200` |
| MJPEG 画面 | 有 `AI ok faces:N persons:N` 诊断行 + 人脸/人体画框 |

---

## 5. 前端验证（B 组完成后通知 A 组）

1. 确认 `frontend/.env.development` 指向云：

   ```env
   VITE_API_TARGET=http://152.136.29.158
   VITE_VIDEO_FEED_TARGET=http://152.136.29.158
   VITE_WEBRTC_BASE_URL=http://152.136.29.158:8889
   ```

2. 打开 `http://localhost:5173/monitor`
3. 切换到 **「MJPEG 备用」**（WebRTC 无 AI 画框，属正常）
4. 对着摄像头露脸，观察：
   - 画面：红/绿人脸框、黄色人体框
   - 左上角：`AI ok faces:1 persons:1`
   - 右侧人数：≥ 1

---

## 6. 不需要做的

- ❌ 不需要对外开放 `8000` / `8010` 端口（走 Nginx 80 即可）
- ❌ 不需要暴露 RTSP `8554` 到公网
- ❌ 不要随便重启 `home-mediamtx`（会断开所有推流）
- ❌ 不要把视频后端改绑到 `8000`（与 mini-rednote 冲突）

---

## 7. 相关文档

- [cloud-api-handoff-for-b-group.md](cloud-api-handoff-for-b-group.md) — Nginx 80 端口业务 API 反代
- [video-stream-webrtc-integration.md](video-stream-webrtc-integration.md) — WebRTC + MJPEG 完整架构
- [backend_handoff_video_stream.md](backend_handoff_video_stream.md) — OBS 推流参数
- [DEV_SETUP.md](DEV_SETUP.md) — 本地开发环境（含 dlib 说明）

---

## 8. 分工速查（B 组完成后下一步）

| 任务 | 负责 | 状态 |
|------|------|------|
| MediaMTX / OBS / WebRTC | B | ✅ 完成 |
| dlib 环境（venv） | B | ✅ 完成 |
| 部署 `dev` 完整 `process_frame` 流水线 | B | ❌ 待做 |
| `presence` 写入 `/api/home/presence/` | B + C | ❌ 待做 |
| 人体检测 / 危险区域画框 | D | ❌ 待部署到云 |
| 前端人数读 `/api/video/status.presence` | A | ✅ 代码已改，待云部署生效 |

---

## 9. 联系人

| 问题类型 | 联系人 |
|---------|--------|
| Nginx / MediaMTX / 云部署 | B 苏哲勋 |
| AI 画框 / 人脸识别逻辑 | C 王梓铭 |
| 异常检测 / 危险区域 | D 李东礼 |
| 前端 / 联调 | A 牛雨昊 |

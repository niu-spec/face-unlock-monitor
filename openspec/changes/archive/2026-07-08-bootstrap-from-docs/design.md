## Context

home-camera-monitor 是小学期团队项目，6 人分工：前端（A）、流媒体（B）、人脸（C）、检测（D）、Django 业务（E）、文档（F）。架构已从 Flask 单体演进为 Django 统一后端（:8000），视频流由 `apps/video_stream/` 提供 MJPEG；MediaMTX 替代原 Nginx-RTMP 方案。

当前实现状态：

| 模块 | 状态 | 位置 |
|------|------|------|
| 视频 MJPEG | 已实现（需 OBS 推流） | `backend/apps/video_stream/` |
| 危险区域 CRUD + Canvas | 已实现 | `frontend/src/views/ZoneEditor.vue` |
| 居家监控页 | 已实现 | `frontend/src/views/HomeMonitor.vue` |
| Django 业务 API | 已实现 | `backend/apps/{accounts,zones,alerts,events}/` |
| 人脸识别 / 异常检测 | 待接入 | `process_frame()` 扩展点 |
| 用户管理页 | 占位 | `frontend/src/views/UserManage.vue` |

## Goals / Non-Goals

**Goals:**

- 将现有文档与已实现行为固化为 6 个 capability spec，供后续 change 引用
- 在 config 中记录流 ID 双轨约定（`1`/`2` ↔ `living_room`/`kitchen`）
- 明确 AI 模块接入点（`video_stream/services.py` → `process_frame()`）

**Non-Goals:**

- 不在本 change 中实现 AI 检测、自动推流或 UserManage 页面
- 不修改数据库 schema 或 API 契约（除非后续独立 change）

## Decisions

### 1. Spec 粒度：按业务能力而非代码目录

每个 capability 对应用户可感知的功能域（如 `zone-management`），而非 Django app 名称。`frontend-integration` 单独成 spec，因为流 ID 映射是跨前后端的关键契约。

### 2. 流 ID 双轨制

- **视频层**: MediaMTX 推流码 `1`（客厅）、`2`（厨房）→ `/video_feed/{id}`
- **业务层**: Django zones/alerts 使用 `living_room`、`kitchen`
- **前端**: `frontend/src/constants/streams.js` 统一转换

备选方案：后端统一改为数字 ID —— 拒绝，因已有 zones 数据与 API 使用 legacyId。

### 3. OpenSpec 工作流

```
/opsx-propose → proposal + design + specs + tasks
/opsx-apply   → 按 tasks 实现并勾选
/opsx-archive → 合并 specs 到 openspec/specs/，归档 change
```

### 4. 坐标系

危险区域 Canvas 使用 640×480 固定坐标系，与 OBS 推荐推流分辨率一致；后端 `points_json` 存储该坐标系下的多边形顶点数组。

## Risks / Trade-offs

- [文档与代码漂移] → 每次功能 PR 同步更新 spec 或新建 change
- [AI 模块未接入] → specs 中 face/detection 需求标记为「待实现」，避免虚假完成
- [MediaMTX 未启动时] → 前端显示 waiting 占位，属预期行为而非 bug

## Migration Plan

1. 完成本 change 全部 artifacts
2. 运行 `/opsx-archive bootstrap-from-docs` 将 specs 写入 `openspec/specs/`
3. 下一 change 示例：`ai-video-integration`（C/D 接入 process_frame）

## Open Questions

- B 组自动推流完成后，是否需要在 spec 中增加「摄像头自动注册」能力？
- 人数统计是否改用 WebSocket 推送，还是继续轮询 `/api/home/presence/`？

## Why

前端监控页与危险区域编辑器原先使用 `living_room`/`kitchen` 作为视频流 ID，与 B 组 MediaMTX 推流码 `1`/`2` 不一致，导致 `/video_feed/` 无法显示画面。需要在 OpenSpec 驱动下完成 ID 对齐与 ZoneEditor Canvas 画框功能。

## What Changes

- 新增 `frontend/src/constants/streams.js` 双轨 ID 映射
- HomeMonitor.vue 改用 `/video_feed/1`、`/video_feed/2`
- ZoneEditor.vue 实现 640×480 Canvas 多边形画框与 zoneApi CRUD
- 更新 `frontend-integration`、`zone-management` spec

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `frontend-integration`: 流 ID 映射函数与 videoFeedPath 约定
- `zone-management`: Canvas 画框编辑、视频背景叠加、按 stream 过滤

## Impact

- `frontend/src/constants/streams.js`（新建）
- `frontend/src/views/HomeMonitor.vue`
- `frontend/src/views/ZoneEditor.vue`
- `frontend/src/api/index.js`

**状态：已于 commit 57a0cc1 实现，本 change 为追溯归档。**

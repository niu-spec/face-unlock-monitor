## Context

B 组完成 Django video_stream 迁移后，推流码为数字 ID（OBS 推 `stream/1`）。Django zones API 仍使用 `living_room`/`kitchen`。前端需统一转换，避免业务层与视频层 ID 混用。

## Goals / Non-Goals

**Goals:**
- 单一映射源 `streams.js`
- ZoneEditor 在视频背景上绘制多边形
- 坐标系固定 640×480

**Non-Goals:**
- 不修改后端 stream_id 字段格式
- 不在本 change 实现 AI 检测

## Decisions

### streams.js 为唯一映射入口

所有页面通过 `toVideoStreamId()` / `toZoneStreamId()` / `videoFeedPath()` 转换，禁止硬编码 ID。

### Canvas 交互

点击添加顶点、撤销、清空；表格行点击加载已有区域编辑。

## Risks / Trade-offs

- [点击顺序影响多边形形状] → 文档说明按边界顺序点击

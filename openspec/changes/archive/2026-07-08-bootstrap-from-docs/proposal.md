## Why

项目已有较完整的架构文档与部分已实现功能（视频流、危险区域画框、Django 业务 API），但缺少可追踪的需求规格与变更流程。引入 OpenSpec 后，团队可以用统一格式描述「做什么」、评审后再实现，避免前后端/AI 模块接口不一致。

## What Changes

- 从 `docs/总体架构说明.md`、`docs/backend_handoff_video_stream.md` 等现有文档提炼首批 capability specs
- 在 `openspec/config.yaml` 写入项目上下文（技术栈、端口、分支规范、流 ID 约定）
- 建立 Cursor 命令（`/opsx-propose`、`/opsx-apply`、`/opsx-archive`）的工作流基线
- 不修改任何运行时代码；本 change 仅产出规格与设计文档

## Capabilities

### New Capabilities

- `video-stream`: OBS/MediaMTX 推流 → Django OpenCV 拉 RTSP → MJPEG 预览
- `zone-management`: 危险区域多边形 CRUD 与 Canvas 画框编辑
- `auth-accounts`: JWT 登录与家庭成员管理
- `home-monitor`: 多路摄像头居家监控页与人数统计展示
- `alerts-events`: 告警列表、处置与事件日志
- `frontend-integration`: 前端 API 封装、流 ID 映射与 Vite 代理约定

### Modified Capabilities

（无——`openspec/specs/` 当前为空，均为新建）

## Impact

- **文档**: `openspec/specs/`、`openspec/config.yaml`
- **工具**: `.cursor/commands/`、`.cursor/skills/`（已在 init 阶段创建）
- **代码**: 无直接改动；后续 change 将引用这些 specs 驱动实现

## Context

当前 `process_frame()` 处理器链为纯视频管线：`face → detection → annotate → return`。新增音频检测能力后，需要一条**并行的音频管线**，与视频管线共享告警写入通道和联动缓冲器。

架构约束：
- 音频采集不能复用 OpenCV `VideoCapture`（不支持音频轨道），需要独立 FFmpeg 子进程
- 音频分类使用 PANNs CNN14（PyTorch），与 YOLOv8n 共享 PyTorch 运行时，不引入新深度学习框架
- 当 RTSP 流不含音频轨道时自动降级，不影响现有视频检测功能
- 音视频联动不是「必要条件」而是「增强」— 音频异常独立产生告警

## Goals / Non-Goals

**Goals:**
- 从 RTSP 流中抽取 PCM 音频，以固定时长块（3s）送入分类模型
- 识别尖叫/呼救、打架/争吵、哭喊、玻璃破碎四类异常声音
- 实现音视频联动：同一时间窗口内视频+音频同时异常 → 升级为紧急告警
- 新增的音频告警类型纳入现有告警冷却机制

**Non-Goals:**
- 不实现语音识别（ASR）/ 说话人识别
- 不替换现有 MediaMTX 推拉流方案
- 不在前端增加音频波形展示或实时播放

## Decisions

### 1. 并行音频管线

```
RTSP 流 ──┬── OpenCV VideoCapture ──→ 视频帧 → process_frame()（已有）
          │
          └── FFmpeg 子进程 ──→ PCM ──→ AudioDetectionService（新增）
                                            │
                                            ├── PANNs CNN14 推理
                                            ├── create_alert(SCREAM/FIGHT/...)
                                            └── AVCorrelationBuffer.enqueue_audio()
```

视频管线中的检测结果也通过 `DetectionService._enqueue_video_results()` 入队联动缓冲器。

**理由**：FFmpeg 子进程独立于 OpenCV，解耦清晰；一方崩溃不影响另一方。

### 2. 音频分类模型：PANNs CNN14

选择 PANNs（而非 YAMNet 或自定义分类器）的理由：
- PyTorch 原生，与 YOLOv8n 共享运行时，不引入 TensorFlow
- AudioSet 527 类预训练，已覆盖目标类别（Screaming、Shout、Crying、Shatter 等）
- 通过 `torch.hub.load` 一行加载，首次运行时自动下载权重 (~80MB)
- 若 torch.hub 不可用，自动降级为直接下载 checkpoint + 本地构建网络

### 3. AudioSet 类别 → 业务告警类型映射

多标签聚合策略：
- **SCREAM**：Screaming / Shout / Yell / Battle cry — 取 max 概率
- **FIGHT**：多标签组合判定 — Shout/Yell 概率 × 0.7 + 嘈杂人声/对话概率 × 0.3
- **CRYING**：Crying, sobbing / Baby cry, infant cry — 取 max 概率
- **GLASS_BREAK**：Shatter / Glass — 取 max 概率

### 4. 音视频联动规则

| 音频 | 视频 | 时间窗口 | 联动告警 |
|------|------|----------|----------|
| SCREAM/FIGHT | FALL | ±5s | EMERGENCY (CRITICAL, priority=100) |
| SCREAM/FIGHT | FIRE | ±5s | EMERGENCY (CRITICAL, priority=90) |
| SCREAM/FIGHT | INTRUSION | ±5s | EMERGENCY (CRITICAL, priority=85) |
| CRYING | FALL | ±5s | EMERGENCY (HIGH, priority=70) |

**理由**：联动是「增强」而非「替代」— 音频异常独立产生告警，联动额外创建一条 EMERGENCY 关联告警。

### 5. 告警写入方式

与现有 `ai-video-integration` design.md 决策一致：同进程直调 `apps.alerts.services.create_alert()`，因为 `AlertViewSet` 要求 `IsAuthenticated`，同进程内无 JWT。

### 6. 降级策略

三层降级保护：
1. FFmpeg 未安装 / RTSP 无音频轨道 → `AudioCapture` 标记 `degraded`，不启动线程
2. PANNs 模型加载失败（网络/兼容性） → `AudioDetectionService._model_ready = False`，不执行推理
3. FFmpeg 运行中崩溃 → 自动重连（最多 3 次），超限后降级

降级全过程不影响视频检测正常运行。

## Open Questions

- 云端部署时需确认 FFmpeg 已安装；MediaMTX Docker 自带 FFmpeg 但 Django 宿主机可能需独立安装
- PANNs 类别索引的硬编码 fallback 值可能因模型版本不同而有 ±1~2 偏移，生产环境建议验证

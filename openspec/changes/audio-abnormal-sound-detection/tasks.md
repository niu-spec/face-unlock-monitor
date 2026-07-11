## 1. 音频采集（audio_capture.py）

- [x] 1.1 实现 `AudioCapture` 类，通过 `subprocess.Popen` 管理 FFmpeg 子进程
- [x] 1.2 FFmpeg 参数：`-vn -acodec pcm_s16le -ar 32000 -ac 1 -f s16le pipe:1`
- [x] 1.3 实现后台线程循环读取 PCM 数据，按 `chunk_duration`（默认 3s）组装音频块
- [x] 1.4 实现 `on_audio_chunk(pcm_float32, timestamp)` 回调机制
- [x] 1.5 实现 `is_degraded` 降级标记：FFmpeg 未安装 / 启动失败 / 音频轨道缺失
- [x] 1.6 实现自动重连逻辑（最多 `MAX_RECONNECTS` 次，超限后降级）
- [x] 1.7 实现 `stop()` 安全终止 FFmpeg 子进程
- [x] 1.8 实现 PCM int16 → float32[-1, 1] 标准化转换
- [x] 1.9 实现全局采集器注册表 `get_or_create_audio_capture()` + `stop_all_audio_captures()`

## 2. 音频分类（audio_service.py）

- [x] 2.1 实现 `AudioDetectionService` 服务类
- [x] 2.2 实现 PANNs CNN14 模型懒加载（`_ensure_model`，线程安全，仅加载一次）
- [x] 2.3 实现 `torch.hub.load("qiuqiangkong/panns_audioset", "cnn14")` 优先加载
- [x] 2.4 实现 fallback：直接下载 checkpoint + `_build_cnn14()` 本地构建网络（与官方架构一致）
- [x] 2.5 实现 AudioSet 527 类标签解析（从模型元数据或硬编码 fallback）
- [x] 2.6 实现 AudioSet → 业务告警类型映射（SCREAM/FIGHT/CRYING/GLASS_BREAK）
- [x] 2.7 实现 FIGHT 多标签组合判定逻辑（喊叫类 × 0.7 + 嘈杂人声 × 0.3）
- [x] 2.8 实现音频预处理链：预加重 → 对数梅尔频谱图 → tensor
- [x] 2.9 实现连续帧防误报机制（不同类型要求不同连续帧数）
- [x] 2.10 实现音频告警冷却（每个告警类型独立冷却时间）
- [x] 2.11 实现 `create_alert()` 调用（同进程直调，注入 `metadata.source="audio"`）
- [x] 2.12 实现告警音频片段保存（WAV 格式，`snapshots/audio/` 目录）
- [x] 2.13 实现 `start_for_stream(stream_id, rtsp_url)` / `stop_for_stream(stream_id)`
- [x] 2.14 实现 `get_stream_status()` / `get_global_status()` 状态查询

## 3. 音视频联动（av_correlation.py）

- [x] 3.1 实现 `AudioEvent` / `VideoEvent` 数据结构
- [x] 3.2 实现 `AVCorrelationBuffer` 滑动时间窗口缓冲器
- [x] 3.3 实现 `enqueue_audio_event()` / `enqueue_video_event()` 入队接口
- [x] 3.4 实现过期事件自动清理（`_prune_stream`，滑动窗口裁剪）
- [x] 3.5 实现 `CORRELATION_RULES` 联动规则表（音频类型 + 视频类型 → EMERGENCY + 优先级）
- [x] 3.6 实现 `_check_correlation()` 匹配最高优先级联动规则
- [x] 3.7 实现 `_create_emergency_alert()` 创建联动紧急告警（type=EMERGENCY, level=CRITICAL/HIGH）
- [x] 3.8 实现联动告警冷却（`EMERGENCY_COOLDOWN` 默认 30s）
- [x] 3.9 实现 `get_stream_events()` / `get_status()` 调试接口
- [x] 3.10 实现全局单例 `get_av_correlation_buffer()`

## 4. 集成与接口

- [x] 4.1 修改 `DetectionService.__init__` 添加 `_av_correlation` / `_audio_service` 属性
- [x] 4.2 实现 `_ensure_av_correlation()` 懒初始化联动缓冲器
- [x] 4.3 实现 `_enqueue_video_results()` 将视频告警入队联动缓冲器
- [x] 4.4 修改 `process_frame()` 在获取 results 后调用 `_enqueue_video_results()`
- [x] 4.5 修改 `video_stream/services.py` 的 `get_worker()`，启动时调用 `_start_audio_for_stream()`
- [x] 4.6 实现 `_start_audio_for_stream()` 创建 AudioDetectionService + AudioCapture
- [x] 4.7 新增 `GET /api/detection/audio/status/` 端点（支持 `?stream_id=` 查询参数）

## 5. 数据与配置

- [x] 5.1 在 `Alert.TYPE_CHOICES` 中新增 6 种告警类型：SCREAM / FIGHT / CRYING / GLASS_BREAK / ABNORMAL_SOUND / EMERGENCY
- [x] 5.2 在 `Alert.LEVEL_CHOICES` 中新增 CRITICAL 严重等级
- [x] 5.3 在 `DETECTION_CONFIG` 中新增音频告警冷却配置
- [x] 5.4 在 `requirements.txt` 中新增 5 个依赖：librosa / soundfile / scipy / ffmpeg-python / torchaudio

## 6. 文档

- [x] 6.1 更新 `docs/架构设计/AI危险区域与异常检测模块_技术文档.md`，新增第 9 节：异常声学事件检测与音视频联动告警
- [x] 6.2 补齐 OpenSpec change 文档（本条）

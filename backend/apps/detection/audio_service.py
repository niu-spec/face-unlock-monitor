"""异常声学事件检测服务。

基于 PANNs CNN14 预训练模型（AudioSet 527 类），对实时音频流进行分类，
识别以下异常声音事件：

    - SCREAM:     尖叫 / 呼救声（映射自 AudioSet 的 Screaming, Shout, Yell）
    - FIGHT:      打架 / 争吵声（映射自 AudioSet 的 Shout + 嘈杂人声组合）
    - CRYING:     哭喊声（映射自 AudioSet 的 Crying, Baby cry）
    - GLASS_BREAK: 玻璃破碎声（映射自 AudioSet 的 Shatter, Glass）

检测到异常声音后通过 apps.alerts.services.create_alert() 写入告警表。

架构:
    AudioCapture（PCM 流）
        → AudioDetectionService.on_audio_chunk(pcm, timestamp)
        → 预加重 → 梅尔频谱图 → PANNs CNN14 推理
        → 527 类概率 → 映射到业务告警类型 → create_alert()

由团队成员 D（李东礼）负责实现和维护。
"""

import json
import logging
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 音频检测配置默认值
# ---------------------------------------------------------------------------

AUDIO_SERVICE_CONFIG = {
    # 模型
    "AUDIO_MODEL": "panns_cnn14",
    "AUDIO_CONFIDENCE_THRESHOLD": 0.25,   # 单类置信度阈值（AudioSet 527 类，sigmoid 输出）
    "AUDIO_MULTI_LABEL_THRESHOLD": 0.20,  # 多标签组合判断使用的宽松阈值
    # 音频预处理
    "SAMPLE_RATE": 32000,
    "N_FFT": 1024,
    "HOP_LENGTH": 320,
    "N_MELS": 64,
    "FMIN": 50,
    "FMAX": 14000,
    # 告警策略
    "SCREAM_CONSECUTIVE_FRAMES": 2,       # 连续检测到尖叫的帧数（防误报）
    "FIGHT_CONSECUTIVE_FRAMES": 3,        # 连续检测到打架的帧数（更需要确认）
    "CRYING_CONSECUTIVE_FRAMES": 2,
    "GLASS_BREAK_CONSECUTIVE_FRAMES": 1,  # 玻璃破碎声单次即可告警（瞬时事件）
    "AUDIO_ALERT_COOLDOWN": {
        "SCREAM": 15,
        "FIGHT": 20,
        "CRYING": 20,
        "GLASS_BREAK": 10,
        "ABNORMAL_SOUND": 30,
    },
    # 音频片段保存
    "AUDIO_SNIPPET_DIR": "snapshots/audio/",
    "SAVE_AUDIO_SNIPPETS": True,
}


def _ascfg(key: str):
    """从 Django settings 读取音频服务配置，未设置时使用默认值。"""
    try:
        from django.conf import settings

        audio_cfg = getattr(settings, "DETECTION_CONFIG", {}).get("AUDIO", {})
        return audio_cfg.get(key, AUDIO_SERVICE_CONFIG[key])
    except Exception:
        return AUDIO_SERVICE_CONFIG[key]


# ---------------------------------------------------------------------------
# AudioSet → 业务告警类型映射
# ---------------------------------------------------------------------------
# PANNs CNN14 输出 527 类（AudioSet 本体，按 mid 字母序排列）。
# 以下将相关 AudioSet 类别名称映射到我们的业务告警类型。
#
# 映射策略：
#   - 同类 AudioSet 标签聚合：多个相似标签 → 同一业务告警类型
#   - 取 max 概率作为该业务类型的置信度
#   - FIGHT 需要多标签条件：Shout + (Speech | Hubbub) 同时高置信

AUDIOSET_TO_ALERT_MAP: dict[str, str] = {
    # 尖叫 / 呼救
    "Screaming": "SCREAM",
    "Shout": "SCREAM",
    "Yell": "SCREAM",
    "Battle cry": "SCREAM",
    # 哭喊
    "Crying, sobbing": "CRYING",
    "Baby cry, infant cry": "CRYING",
    "Whimper": "CRYING",
    "Groan": "CRYING",
    # 玻璃破碎
    "Shatter": "GLASS_BREAK",
    "Glass": "GLASS_BREAK",
    # 打架 / 暴力
    # FIGHT 使用多标签逻辑（见 _detect_fight），此处仅为单标签兜底
    "Gunshot, gunfire": "SCREAM",  # 枪声 = 紧急事件
    "Explosion": "SCREAM",
    "Bang": "SCREAM",
}

# 打架声判定所需的多标签组合
FIGHT_REQUIRED_CLASSES = [
    "Shout",
    "Yell",
    "Battle cry",
    "Screaming",
]
FIGHT_CONTEXT_CLASSES = [
    "Speech",
    "Conversation",
    "Brawl",
    "Argument",
    "Hubbub, speech noise, speech babble",
    "Rowdy crowd",
]


# ---------------------------------------------------------------------------
# AudioDetectionService
# ---------------------------------------------------------------------------


class AudioDetectionService:
    """异常声学事件检测服务。

    每个摄像头流共享一个全局 AudioDetectionService 实例。
    内部维护:
      - PANNs CNN14 模型（全局单例，所有流共用）
      - 每个流的分类状态计数器（防误报）
      - 每个流的告警冷却计时器
      - 音视频联动缓冲器引用（可选，由外部注入）

    Usage:
        service = AudioDetectionService()
        service.start_for_stream("living_room", "rtsp://.../stream/1")
        ...
        service.stop_for_stream("living_room")
        service.shutdown()  # 进程退出前
    """

    def __init__(self, av_correlation_buffer=None):
        """初始化音频检测服务。

        Args:
            av_correlation_buffer: 可选，AVCorrelationBuffer 实例，
                用于音视频联动告警。
        """
        self._model = None                # PANNs CNN14 模型
        self._class_labels: list[str] = []  # 527 类名称列表
        self._label_to_idx: dict[str, int] = {}  # 类别名 → 索引
        self._model_ready = False
        self._model_load_attempted = False
        self._model_lock = threading.Lock()

        # 每个流的运行状态
        self._stream_states: dict[str, dict] = {}
        self._states_lock = threading.Lock()

        # 音频采集器引用
        self._captures: dict[str, object] = {}

        # 音视频联动
        self._av_correlation = av_correlation_buffer

        # 类别索引缓存：业务告警类型 → [(AudioSet索引, 类别名), ...]
        self._alert_type_indices: dict[str, list[tuple[int, str]]] = {}
        self._fight_required_indices: list[int] = []
        self._fight_context_indices: list[int] = []

        logger.info("AudioDetectionService 已创建")

    # ------------------------------------------------------------------
    # 模型加载（懒初始化）
    # ------------------------------------------------------------------

    def _ensure_model(self):
        """确保 PANNs 模型已加载（线程安全，仅加载一次）。"""
        if self._model_ready:
            return True
        if self._model_load_attempted:
            return False

        with self._model_lock:
            if self._model_ready:
                return True
            if self._model_load_attempted:
                return False

            self._model_load_attempted = True

            try:
                self._load_panns_model()
                self._resolve_class_indices()
                self._model_ready = True
                logger.info(
                    "PANNs 模型加载完成，已解析 %d 个目标类别索引",
                    len(self._label_to_idx),
                )
                return True
            except Exception as e:
                logger.error("PANNs 模型加载失败，音频检测不可用: %s", e, exc_info=True)
                return False

    def _load_panns_model(self):
        """加载 PANNs CNN14 模型。

        尝试顺序:
          1. torch.hub.load（推荐，自动下载权重 ~80MB）
          2. 直接下载权重文件（torch.hub 不可用时的兜底）
        """
        import torch

        try:
            # 方式 1: torch.hub
            logger.info("正在通过 torch.hub 加载 PANNs CNN14 ...")
            self._model = torch.hub.load(
                "qiuqiangkong/panns_audioset",
                "cnn14",
                pretrained=True,
                verbose=False,
            )
            self._model.eval()

            # 尝试获取类别标签
            self._class_labels = self._resolve_class_labels_from_model()

        except Exception as hub_err:
            logger.warning("torch.hub 加载 PANNs 失败: %s，尝试直接加载", hub_err)
            self._load_panns_fallback()

    def _load_panns_fallback(self):
        """torch.hub 不可用时的兜底加载: 直接下载 checkpoint。"""
        import torch

        # PANNs CNN14 checkpoint 的直链（Zenodo）
        checkpoint_url = (
            "https://zenodo.org/record/3987831/files/"
            "Cnn14_mAP%3D0.431.pth"
        )
        cache_dir = Path(torch.hub.get_dir()) / "checkpoints"
        cache_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = cache_dir / "Cnn14_mAP=0.431.pth"

        if not checkpoint_path.exists():
            logger.info("下载 PANNs 权重: %s", checkpoint_url)
            torch.hub.download_url_to_file(
                str(checkpoint_url), str(checkpoint_path)
            )

        # 手动构建 Cnn14 模型
        from types import SimpleNamespace

        # 加载 checkpoint
        checkpoint = torch.load(str(checkpoint_path), map_location="cpu", weights_only=True)

        # checkpoint 通常包含完整模型 state_dict
        # PANNs checkpoint 结构: {'model': OrderedDict(...), ...}
        if isinstance(checkpoint, dict) and "model" in checkpoint:
            state_dict = checkpoint["model"]
        else:
            state_dict = checkpoint

        # 动态构建 CNN14 模型（从 PANNs 源码适配）
        model = _build_cnn14(num_classes=527)
        model.load_state_dict(state_dict, strict=False)
        model.eval()
        self._model = model

        # 用硬编码标签
        self._class_labels = self._resolve_class_labels_fallback()

    def _resolve_class_labels_from_model(self) -> list[str]:
        """从 torch.hub 加载的 PANNs 仓库中获取类别标签列表。"""
        # 方法 1: 检查模型是否有 labels 属性
        if hasattr(self._model, "labels"):
            return list(self._model.labels)

        # 方法 2: 从 torch.hub 仓库目录读取 CSV
        import torch

        hub_dir = Path(torch.hub.get_dir())
        # 查找 panns_audioset 仓库
        candidates = list(hub_dir.glob("qiuqiangkong_panns_audioset*"))
        for candidate in candidates:
            csv_path = candidate / "assets" / "class_labels_indices.csv"
            if csv_path.exists():
                return _parse_audioset_labels_csv(str(csv_path))

        # 方法 3: fallback
        logger.warning("无法从模型获取类别标签，使用硬编码映射")
        return self._resolve_class_labels_fallback()

    def _resolve_class_labels_fallback(self) -> list[str]:
        """硬编码的 AudioSet 527 类名称列表（仅包含我们需要的类别）。

        完整列表太长（527 条），这里仅返回一个占位列表。
        实际使用时不依赖完整列表，而是通过 _resolve_class_indices
        以字典查找方式按名称匹配目标类别。
        """
        return []  # 空列表表示使用硬编码索引

    def _resolve_class_indices(self):
        """解析目标 AudioSet 类别 → 模型输出索引的映射。

        策略:
          1. 如果 _class_labels 非空 → 按名称查找索引
          2. 否则 → 使用硬编码的已知索引
        """
        if self._class_labels:
            # 有完整标签列表 → 按名称匹配
            self._label_to_idx = {
                label: idx for idx, label in enumerate(self._class_labels)
            }
            logger.info(
                "从模型元数据解析了 %d 个 AudioSet 类别标签",
                len(self._class_labels),
            )
        else:
            # 无完整标签列表 → 使用硬编码已知索引
            self._label_to_idx = _get_hardcoded_label_indices()
            logger.info(
                "使用硬编码的 %d 个 AudioSet 类别索引映射",
                len(self._label_to_idx),
            )

        # 构建业务告警类型 → AudioSet 索引列表
        self._alert_type_indices.clear()
        for audioset_name, alert_type in AUDIOSET_TO_ALERT_MAP.items():
            if audioset_name in self._label_to_idx:
                idx = self._label_to_idx[audioset_name]
                if alert_type not in self._alert_type_indices:
                    self._alert_type_indices[alert_type] = []
                self._alert_type_indices[alert_type].append((idx, audioset_name))
            else:
                logger.debug(
                    "AudioSet 类别 '%s' 不在模型输出标签中，已跳过",
                    audioset_name,
                )

        # 构建 FIGHT 多标签索引
        self._fight_required_indices = [
            self._label_to_idx[name]
            for name in FIGHT_REQUIRED_CLASSES
            if name in self._label_to_idx
        ]
        self._fight_context_indices = [
            self._label_to_idx[name]
            for name in FIGHT_CONTEXT_CLASSES
            if name in self._label_to_idx
        ]

        logger.info(
            "类别索引解析完成: alert_types=%s, fight_required=%d, fight_context=%d",
            list(self._alert_type_indices.keys()),
            len(self._fight_required_indices),
            len(self._fight_context_indices),
        )

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """音频检测是否可用（模型已加载）。"""
        return self._ensure_model()

    def start_for_stream(self, stream_id: str, rtsp_url: str):
        """为指定流启动音频检测。

        Args:
            stream_id: 业务流 ID（如 "living_room"）。
            rtsp_url: RTSP 流地址。
        """
        if not self._ensure_model():
            logger.warning(
                "音频模型未就绪，跳过音频检测启动: %s", stream_id
            )
            return

        with self._states_lock:
            if stream_id in self._stream_states:
                logger.warning("音频检测已在运行: %s", stream_id)
                return

            self._stream_states[stream_id] = {
                "consecutive": defaultdict(int),       # alert_type → 连续帧计数
                "last_alert_time": defaultdict(float),  # alert_type → 上次告警时间
                "latest_probs": {},                     # 最近一次推理概率
                "pcm_buffer": bytearray(),              # PCM 原始缓冲区
                "pcm_float_buffer": [],                 # float32 缓冲区
                "active": True,
            }

        from .audio_capture import get_or_create_audio_capture

        cap = get_or_create_audio_capture(
            rtsp_url=rtsp_url,
            stream_id=stream_id,
            on_audio_chunk=lambda pcm, ts: self.on_audio_chunk(stream_id, pcm, ts),
        )
        self._captures[stream_id] = cap
        cap.start()

        logger.info("音频检测已启动: stream=%s", stream_id)

    def stop_for_stream(self, stream_id: str):
        """停止指定流的音频检测。"""
        cap = self._captures.pop(stream_id, None)
        if cap:
            cap.stop()

        with self._states_lock:
            state = self._stream_states.pop(stream_id, None)
            if state:
                state["active"] = False

        logger.info("音频检测已停止: stream=%s", stream_id)

    def shutdown(self):
        """关闭整个音频检测服务（进程退出前调用）。"""
        for stream_id in list(self._captures.keys()):
            self.stop_for_stream(stream_id)
        logger.info("AudioDetectionService 已关闭")

    def get_stream_status(self, stream_id: str) -> dict:
        """获取指定流的音频检测状态。"""
        with self._states_lock:
            state = self._stream_states.get(stream_id)

        cap = self._captures.get(stream_id)
        cap_status = cap.to_status() if cap else {}

        if state is None:
            return {
                "stream_id": stream_id,
                "active": False,
                "model_ready": self._model_ready,
            }

        return {
            "stream_id": stream_id,
            "active": state.get("active", False),
            "model_ready": self._model_ready,
            "capture": cap_status,
            "latest_probs": {
                k: round(v, 4)
                for k, v in state.get("latest_probs", {}).items()
            },
        }

    # ------------------------------------------------------------------
    # 音频块回调
    # ------------------------------------------------------------------

    def on_audio_chunk(
        self, stream_id: str, pcm: np.ndarray, timestamp: float
    ):
        """AudioCapture 的音频块回调。

        在 AudioCapture 的后台线程中调用。
        """
        if not self._model_ready:
            return

        with self._states_lock:
            state = self._stream_states.get(stream_id)
        if state is None or not state.get("active"):
            return

        try:
            results = self._classify_chunk(pcm)
            state["latest_probs"] = {
                alert_type: round(prob, 4)
                for alert_type, prob in results.items()
            }
            self._process_results(stream_id, results, pcm, timestamp, state)
        except Exception as e:
            logger.error(
                "音频分类异常 (stream=%s): %s", stream_id, e, exc_info=True
            )

    # ------------------------------------------------------------------
    # 音频分类
    # ------------------------------------------------------------------

    def _classify_chunk(self, pcm: np.ndarray) -> dict[str, float]:
        """对一段 PCM 音频执行分类。

        Args:
            pcm: float32 数组，形状 (samples,)，范围 [-1, 1]。

        Returns:
            {alert_type: confidence} 字典，如 {"SCREAM": 0.78, "CRYING": 0.12}。
        """
        import torch

        # 1. 预加重（简单高通滤波，增强高频）
        pcm = self._preemphasis(pcm, coeff=0.97)

        # 2. 计算对数梅尔频谱图
        log_mel = self._compute_log_mel(pcm)

        # 3. 转换为模型输入 tensor
        # PANNs 期望形状: (batch=1, channel=1, time_frames, mel_bins)
        tensor = torch.from_numpy(log_mel).float().unsqueeze(0).unsqueeze(0)

        # 4. 推理
        with torch.no_grad():
            output = self._model(tensor)  # (1, 527), sigmoid 已内置于模型

        probs = output.squeeze(0).numpy()  # (527,)

        # 5. 映射到业务告警类型
        results: dict[str, float] = {}
        conf_threshold = _ascfg("AUDIO_CONFIDENCE_THRESHOLD")

        for alert_type, idx_list in self._alert_type_indices.items():
            # 对同一业务类型下的多个 AudioSet 类别取 max 概率
            type_probs = [probs[idx] for idx, _ in idx_list]
            max_prob = float(max(type_probs)) if type_probs else 0.0
            if max_prob >= conf_threshold:
                results[alert_type] = max_prob

        # 6. 打架声多标签判定
        fight_prob = self._detect_fight_multilabel(probs)
        if fight_prob >= conf_threshold:
            results["FIGHT"] = fight_prob

        return results

    def _preemphasis(self, pcm: np.ndarray, coeff: float = 0.97) -> np.ndarray:
        """预加重：y[t] = x[t] - coeff * x[t-1]。"""
        if len(pcm) <= 1:
            return pcm
        emphasized = np.zeros_like(pcm)
        emphasized[0] = pcm[0]
        emphasized[1:] = pcm[1:] - coeff * pcm[:-1]
        return emphasized

    def _compute_log_mel(self, pcm: np.ndarray) -> np.ndarray:
        """计算对数梅尔频谱图。

        Args:
            pcm: float32 数组，32kHz 采样率。

        Returns:
            (n_mels, time_frames) float32 数组。
        """
        try:
            import librosa

            sr = _ascfg("SAMPLE_RATE")
            n_fft = _ascfg("N_FFT")
            hop_length = _ascfg("HOP_LENGTH")
            n_mels = _ascfg("N_MELS")
            fmin = _ascfg("FMIN")
            fmax = _ascfg("FMAX")

            # 确保足够的样本量
            if len(pcm) < n_fft:
                pcm = np.pad(pcm, (0, n_fft - len(pcm)))

            mel_spec = librosa.feature.melspectrogram(
                y=pcm.astype(np.float64),
                sr=sr,
                n_fft=n_fft,
                hop_length=hop_length,
                n_mels=n_mels,
                fmin=fmin,
                fmax=fmax,
                power=2.0,
            )

            # 对数变换: log10(x + epsilon)
            log_mel = np.log10(np.maximum(mel_spec, 1e-10))

            return log_mel.astype(np.float32)

        except ImportError:
            logger.error("librosa 未安装，无法计算梅尔频谱图")
            # 返回零数组作为 fallback
            n_mels = _ascfg("N_MELS")
            frames = max(1, len(pcm) // _ascfg("HOP_LENGTH"))
            return np.zeros((n_mels, frames), dtype=np.float32)

    def _detect_fight_multilabel(self, probs: np.ndarray) -> float:
        """多标签组合判定打架/争吵声。

        判定逻辑:
          - 必要条件: 任一高声喊叫类 (Shout/Yell/Screaming/Battle cry) 概率 > 阈值
          - 上下文增强: 同时有嘈杂人声/对话类概率 > 阈值 → 提高置信度
          - 最终置信度 = max(喊叫类) × 0.7 + max(上下文类) × 0.3

        Args:
            probs: (527,) numpy 数组，各类别 sigmoid 概率。

        Returns:
            打架置信度（0.0 ~ 1.0）。
        """
        loose_threshold = _ascfg("AUDIO_MULTI_LABEL_THRESHOLD")

        # 喊叫类概率
        shout_probs = [probs[i] for i in self._fight_required_indices] if self._fight_required_indices else []
        max_shout = float(max(shout_probs)) if shout_probs else 0.0

        # 必须有喊叫类触发
        if max_shout < loose_threshold:
            return 0.0

        # 上下文类概率
        context_probs = [probs[i] for i in self._fight_context_indices] if self._fight_context_indices else []
        max_context = float(max(context_probs)) if context_probs else 0.0

        # 加权融合
        fight_confidence = max_shout * 0.7 + max_context * 0.3

        return fight_confidence

    # ------------------------------------------------------------------
    # 结果处理与告警
    # ------------------------------------------------------------------

    def _process_results(
        self,
        stream_id: str,
        results: dict[str, float],
        pcm: np.ndarray,
        timestamp: float,
        state: dict,
    ):
        """处理分类结果：连续帧确认 → 冷却检查 → 创建告警。"""
        if not results:
            # 无检测 → 衰减所有计数器
            for alert_type in list(state["consecutive"].keys()):
                state["consecutive"][alert_type] = max(
                    0, state["consecutive"][alert_type] - 1
                )
            return

        for alert_type, confidence in results.items():
            # 递增连续帧计数
            state["consecutive"][alert_type] += 1

            # 获取该类型所需的连续帧数
            consecutive_key = f"{alert_type}_CONSECUTIVE_FRAMES"
            required_frames = _ascfg(consecutive_key)

            if state["consecutive"][alert_type] < required_frames:
                continue

            # 检查冷却
            if not self._check_audio_cooldown(alert_type, stream_id, state):
                continue

            # 创建告警
            self._create_audio_alert(
                stream_id=stream_id,
                alert_type=alert_type,
                confidence=confidence,
                pcm=pcm,
                timestamp=timestamp,
                state=state,
            )

            # 重置计数器
            state["consecutive"][alert_type] = 0

    def _check_audio_cooldown(
        self, alert_type: str, stream_id: str, state: dict
    ) -> bool:
        """检查音频告警冷却时间。"""
        now = time.time()
        cooldown_map = _ascfg("AUDIO_ALERT_COOLDOWN")
        cooldown_sec = cooldown_map.get(alert_type, 15)
        last = state["last_alert_time"].get(alert_type, 0)

        if now - last < cooldown_sec:
            return False

        state["last_alert_time"][alert_type] = now
        return True

    def _create_audio_alert(
        self,
        stream_id: str,
        alert_type: str,
        confidence: float,
        pcm: np.ndarray,
        timestamp: float,
        state: dict,
    ):
        """创建音频异常告警。

        通过 apps.alerts.services.create_alert() 写入数据库。
        若配置了 AVCorrelationBuffer，同时将事件入队以进行联动分析。
        """
        # 构建告警消息
        type_labels = {
            "SCREAM": "尖叫/呼救声",
            "FIGHT": "打架/争吵声",
            "CRYING": "哭喊声",
            "GLASS_BREAK": "玻璃破碎声",
            "ABNORMAL_SOUND": "异常声音",
        }
        label = type_labels.get(alert_type, alert_type)
        description = f"检测到{label}（置信度 {confidence:.1%}）"

        # 保存音频片段
        snippet_path = ""
        if _ascfg("SAVE_AUDIO_SNIPPETS"):
            snippet_path = self._save_audio_snippet(
                pcm, stream_id, alert_type, timestamp
            )

        severity_map = {
            "SCREAM": "HIGH",
            "FIGHT": "HIGH",
            "CRYING": "MEDIUM",
            "GLASS_BREAK": "MEDIUM",
            "ABNORMAL_SOUND": "LOW",
        }
        level = severity_map.get(alert_type, "MEDIUM")

        # 写入告警
        try:
            from apps.alerts.services import create_alert
            from apps.video_stream.services import resolve_household_id_for_stream

            create_alert(
                type=alert_type,
                level=level,
                stream_id=stream_id,
                description=description,
                snapshot_path=snippet_path,
                household_id=resolve_household_id_for_stream(stream_id),
                metadata={
                    "source": "audio",
                    "confidence": round(confidence, 4),
                    "timestamp": timestamp,
                    "model": _ascfg("AUDIO_MODEL"),
                },
            )

            logger.info(
                "音频告警: stream=%s type=%s conf=%.2f desc=%s",
                stream_id,
                alert_type,
                confidence,
                description,
            )
        except Exception as e:
            logger.error("创建音频告警失败: %s", e, exc_info=True)

        # 入队音视频联动缓冲器
        if self._av_correlation:
            try:
                self._av_correlation.enqueue_audio_event(
                    stream_id=stream_id,
                    alert_type=alert_type,
                    confidence=confidence,
                    timestamp=timestamp,
                )
            except Exception as e:
                logger.error("音视频联动入队失败: %s", e)

    def _save_audio_snippet(
        self, pcm: np.ndarray, stream_id: str, alert_type: str, timestamp: float
    ) -> str:
        """保存异常音频片段为 WAV 文件。

        Returns:
            WAV 文件相对路径（如 "snapshots/audio/living_room_SCREAM_1704978000.wav"）。
        """
        try:
            import wave
            from datetime import datetime

            base_dir = _ascfg("AUDIO_SNIPPET_DIR")
            os.makedirs(base_dir, exist_ok=True)

            ts_str = datetime.fromtimestamp(timestamp).strftime("%Y%m%d_%H%M%S")
            filename = f"{stream_id}_{alert_type}_{ts_str}.wav"
            filepath = os.path.join(base_dir, filename)

            # 将 float32 → int16
            pcm_int16 = (np.clip(pcm, -1.0, 1.0) * 32767).astype(np.int16)

            with wave.open(filepath, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(_ascfg("SAMPLE_RATE"))
                wf.writeframes(pcm_int16.tobytes())

            logger.debug("音频片段已保存: %s", filepath)
            return filepath

        except Exception as e:
            logger.error("保存音频片段失败: %s", e)
            return ""

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_global_status(self) -> dict:
        """获取全局音频检测状态。"""
        return {
            "model_ready": self._model_ready,
            "model_name": _ascfg("AUDIO_MODEL"),
            "active_streams": list(self._stream_states.keys()),
            "target_classes": list(self._alert_type_indices.keys()),
            "fight_required_classes": [
                self._class_labels[i]
                for i in self._fight_required_indices
                if i < len(self._class_labels)
            ] if self._class_labels else FIGHT_REQUIRED_CLASSES,
            "fight_context_classes": [
                self._class_labels[i]
                for i in self._fight_context_indices
                if i < len(self._class_labels)
            ] if self._class_labels else FIGHT_CONTEXT_CLASSES,
        }


# ---------------------------------------------------------------------------
# 硬编码 AudioSet 类别索引（fallback，当无法从模型获取标签时使用）
# ---------------------------------------------------------------------------
# PANNs CNN14 输出 527 类，按 AudioSet ontology mid 字母序排列。
# 以下索引从标准 AudioSet class_labels_indices.csv 提取。


def _get_hardcoded_label_indices() -> dict[str, int]:
    """返回已知的 AudioSet 类别名称 → 索引映射（仅包含本项目需要的类别）。

    这些索引从 PANNs/AudioSet 标准 527 类 CSV 中提取。
    如果模型版本不同，索引可能有 ±1~2 的偏移。
    """
    # fmt: off
    known = {
        "Baby cry, infant cry": 25,
        "Battle cry": 48,
        "Crying, sobbing": 106,
        "Glass": 198,
        "Gunshot, gunfire": 203,
        "Screaming": 415,
        "Shatter": 417,
        "Shout": 416,
        "Yell": 499,
        "Explosion": 165,
        "Bang": 43,
        "Groan": 201,
        "Whimper": 495,
        # 以下为 FIGHT 多标签判定所需上下文类别
        "Speech": 437,
        "Conversation": 97,
        "Hubbub, speech noise, speech babble": 236,
    }
    # fmt: on
    return known


# ---------------------------------------------------------------------------
# PANNs CNN14 模型定义（fallback 模式使用）
# ---------------------------------------------------------------------------


def _build_cnn14(num_classes: int = 527):
    """构建 PANNs CNN14 模型（与 qiuqiangkong/panns_audioset 完全一致的架构）。

    用于直接加载 .pth checkpoint 文件时构建网络结构。
    参数量: ~80M，输入 (B, 1, time_frames, 64)。

    注意：子模块命名必须与官方 checkpoint 的 state_dict keys 完全匹配，
    否则 load_state_dict 无法正确加载预训练权重。
    """
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class ConvBlock(nn.Module):
        """PANNs 卷积块: Conv2d → BN → ReLU → Conv2d → BN → ReLU → Pool"""
        def __init__(self, in_channels, out_channels):
            super().__init__()
            self.conv1 = nn.Conv2d(
                in_channels=in_channels, out_channels=out_channels,
                kernel_size=(3, 3), stride=(1, 1),
                padding=(1, 1), bias=False,
            )
            self.conv2 = nn.Conv2d(
                in_channels=out_channels, out_channels=out_channels,
                kernel_size=(3, 3), stride=(1, 1),
                padding=(1, 1), bias=False,
            )
            self.bn1 = nn.BatchNorm2d(out_channels)
            self.bn2 = nn.BatchNorm2d(out_channels)

        def forward(self, x, pool_size=(2, 2), pool_type="avg"):
            x = F.relu_(self.bn1(self.conv1(x)))
            x = F.relu_(self.bn2(self.conv2(x)))
            if pool_type == "max":
                x = F.max_pool2d(x, kernel_size=pool_size)
            elif pool_type == "avg":
                x = F.avg_pool2d(x, kernel_size=pool_size)
            else:
                raise ValueError(f"Unknown pool_type: {pool_type}")
            return x

    class Cnn14(nn.Module):
        def __init__(self, num_classes):
            super().__init__()
            # BN on 64 mel bins (treated as 64 channels after transpose)
            self.bn0 = nn.BatchNorm2d(64)

            self.conv_block1 = ConvBlock(in_channels=1, out_channels=64)
            self.conv_block2 = ConvBlock(in_channels=64, out_channels=128)
            self.conv_block3 = ConvBlock(in_channels=128, out_channels=256)
            self.conv_block4 = ConvBlock(in_channels=256, out_channels=512)
            self.conv_block5 = ConvBlock(in_channels=512, out_channels=1024)
            self.conv_block6 = ConvBlock(in_channels=1024, out_channels=2048)

            self.fc1 = nn.Linear(2048, 2048, bias=True)
            self.fc_audioset = nn.Linear(2048, num_classes, bias=True)

        def forward(self, x):
            # x: (batch_size, 1, time_frames, 64)
            x = x.transpose(1, 3)  # → (B, 64, time_frames, 1)
            x = self.bn0(x)        # BN across 64 mel-bin channels
            x = x.transpose(1, 3)  # → (B, 1, time_frames, 64)

            x = self.conv_block1(x, pool_size=(2, 2), pool_type="avg")
            x = self.conv_block2(x, pool_size=(2, 2), pool_type="avg")
            x = self.conv_block3(x, pool_size=(2, 2), pool_type="avg")
            x = self.conv_block4(x, pool_size=(2, 2), pool_type="avg")
            x = self.conv_block5(x, pool_size=(2, 2), pool_type="avg")
            x = self.conv_block6(x, pool_size=(2, 2), pool_type="avg")

            x = F.adaptive_avg_pool2d(x, (1, 1))  # → (B, 2048, 1, 1)
            x = x.view(x.size(0), -1)              # → (B, 2048)

            x = F.dropout(x, p=0.5, training=self.training)
            x = F.relu_(self.fc1(x))
            x = F.dropout(x, p=0.5, training=self.training)
            output = self.fc_audioset(x)

            # PANNs 输出 clip-wise logits → sigmoid 获取概率
            return torch.sigmoid(output)

    return Cnn14(num_classes)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _parse_audioset_labels_csv(csv_path: str) -> list[str]:
    """解析 AudioSet class_labels_indices.csv 文件。

    格式: index,mid,display_name
    """
    import csv

    labels = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                idx = int(row.get("index", len(labels)))
                display_name = row.get("display_name", "")
                # 确保列表长度足够
                while len(labels) <= idx:
                    labels.append("")
                labels[idx] = display_name
    except Exception as e:
        logger.warning("解析 AudioSet 标签 CSV 失败: %s", e)

    return labels


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_audio_service: Optional[AudioDetectionService] = None
_service_lock = threading.Lock()


def get_audio_service(
    av_correlation_buffer=None,
) -> AudioDetectionService:
    """获取全局 AudioDetectionService 单例。

    Args:
        av_correlation_buffer: 可选，AVCorrelationBuffer 实例（首次创建时生效）。

    Returns:
        AudioDetectionService 实例。
    """
    global _audio_service
    if _audio_service is None:
        with _service_lock:
            if _audio_service is None:
                _audio_service = AudioDetectionService(av_correlation_buffer)
    return _audio_service

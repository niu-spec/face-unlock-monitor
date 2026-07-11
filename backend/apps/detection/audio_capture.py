"""FFmpeg 音频采集模块。

从 RTSP 流中抽取音频轨道，输出 PCM 数据供音频分类模型使用。
当 RTSP 流无音频轨道时自动降级，不影响现有视频检测功能。

架构:
    RTSP 流 ──→ FFmpeg 子进程（-vn, PCM s16le）──→ stdout pipe
        ──→ AudioCapture 后台线程循环读取
        ──→ 累积至 chunk_duration 秒后回调 on_audio_chunk

由团队成员 D（李东礼）负责实现和维护。
"""

import logging
import subprocess
import threading
import time
import os
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 音频采集配置默认值
# ---------------------------------------------------------------------------

AUDIO_CAPTURE_CONFIG = {
    "SAMPLE_RATE": 32000,        # PANNs CNN14 原生采样率
    "CHANNELS": 1,               # 单声道
    "CHUNK_DURATION": 3.0,       # 每次回调的音频块时长（秒）
    "SAMPLE_WIDTH": 2,           # s16le = 2 字节/采样
    "RECONNECT_DELAY": 2.0,      # FFmpeg 断开后重连间隔（秒）
    "MAX_RECONNECTS": 3,         # 最大重连次数（超过后降级）
    "FFMPEG_PATH": "ffmpeg",     # FFmpeg 可执行文件路径
}


def _acfg(key: str):
    """从 Django settings 读取音频采集配置，未设置时使用默认值。"""
    try:
        from django.conf import settings

        audio_cfg = getattr(settings, "DETECTION_CONFIG", {}).get("AUDIO", {})
        return audio_cfg.get(key, AUDIO_CAPTURE_CONFIG[key])
    except Exception:
        return AUDIO_CAPTURE_CONFIG[key]


# ---------------------------------------------------------------------------
# AudioCapture — FFmpeg 音频采集器
# ---------------------------------------------------------------------------


class AudioCapture:
    """从 RTSP 流中持续抽取音频，以固定时长块回调。

    每个摄像头流对应一个 AudioCapture 实例，内部维护:
      - 一个 FFmpeg 子进程（通过 subprocess.Popen 管理）
      - 一个后台读取线程

    当 RTSP 流不含音频轨道时 FFmpeg 自动退出，
    AudioCapture 标记为 degraded 模式，不影响视频检测。

    Usage:
        def handle_audio(pcm: np.ndarray, timestamp: float):
            # pcm: float32[-1..1] 形状 (samples,)
            print(f"收到 {len(pcm)/32000:.1f}s 音频")

        cap = AudioCapture("rtsp://127.0.0.1:8554/stream/1", on_audio_chunk=handle_audio)
        cap.start()
        ...
        cap.stop()
    """

    def __init__(
        self,
        rtsp_url: str,
        stream_id: str = "",
        on_audio_chunk: Optional[Callable[[np.ndarray, float], None]] = None,
    ):
        """初始化音频采集器。

        Args:
            rtsp_url: RTSP 流地址。
            stream_id: 业务流 ID（用于日志和告警关联）。
            on_audio_chunk: 音频块回调，
                func(pcm_float32: np.ndarray, timestamp: float)。
        """
        self._rtsp_url = rtsp_url
        self._stream_id = stream_id
        self._on_chunk = on_audio_chunk
        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._degraded = False         # True = 无音频轨道，已降级
        self._reconnect_count = 0
        self._lock = threading.Lock()
        self._sample_rate = _acfg("SAMPLE_RATE")
        self._channels = _acfg("CHANNELS")
        self._chunk_duration = _acfg("CHUNK_DURATION")
        self._sample_width = _acfg("SAMPLE_WIDTH")
        self._bytes_per_sample = self._channels * self._sample_width
        self._chunk_bytes = (
            int(self._sample_rate * self._chunk_duration) * self._bytes_per_sample
        )

        logger.info(
            "AudioCapture init: stream=%s chunk=%.1fs sr=%d",
            stream_id or rtsp_url,
            self._chunk_duration,
            self._sample_rate,
        )

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    @property
    def is_degraded(self) -> bool:
        """是否已降级（无音频轨道 → 仅视频检测）。"""
        return self._degraded

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """启动音频采集（后台线程）。"""
        if self._running:
            logger.warning("AudioCapture 已在运行: %s", self._stream_id)
            return

        self._running = True
        self._degraded = False
        self._reconnect_count = 0
        self._thread = threading.Thread(
            target=self._read_loop, daemon=True, name=f"audio-{self._stream_id}"
        )
        self._thread.start()
        logger.info("AudioCapture 已启动: %s", self._stream_id)

    def stop(self):
        """停止音频采集，终止 FFmpeg 子进程。"""
        self._running = False
        self._terminate_process()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("AudioCapture 已停止: %s", self._stream_id)

    def to_status(self) -> dict:
        """返回采集器运行状态（供 /api/detection/audio/status 使用）。"""
        return {
            "stream_id": self._stream_id,
            "rtsp_url": self._rtsp_url,
            "running": self._running,
            "degraded": self._degraded,
            "sample_rate": self._sample_rate,
            "chunk_duration_s": self._chunk_duration,
            "reconnect_count": self._reconnect_count,
        }

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _spawn_ffmpeg(self) -> Optional[subprocess.Popen]:
        """启动 FFmpeg 子进程，输出 PCM 到 stdout。"""
        cmd = [
            _acfg("FFMPEG_PATH"),
            "-loglevel", "error",
            "-rtsp_transport", "tcp",       # RTSP over TCP 更稳定
            "-i", self._rtsp_url,
            "-vn",                           # 丢弃视频
            "-acodec", "pcm_s16le",          # 16-bit little-endian PCM
            "-ar", str(self._sample_rate),
            "-ac", str(self._channels),
            "-f", "s16le",                   # raw PCM（无 WAV 头，更高效）
            "pipe:1",                        # stdout
        ]

        logger.info("启动 FFmpeg: %s", " ".join(cmd))

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                bufsize=0,                   # 无缓冲
            )
            return proc
        except FileNotFoundError:
            logger.error(
                "FFmpeg 未找到！请确认 ffmpeg 已安装且在 PATH 中。"
                "音频检测将降级。"
            )
            self._degraded = True
            return None
        except Exception as e:
            logger.error("启动 FFmpeg 失败: %s", e)
            self._degraded = True
            return None

    def _terminate_process(self):
        """安全终止 FFmpeg 子进程。"""
        with self._lock:
            if self._process is None:
                return
            proc = self._process
            self._process = None

        try:
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2.0)
        except Exception as e:
            logger.warning("终止 FFmpeg 进程时出错: %s", e)

    def _read_loop(self):
        """后台线程：循环管理 FFmpeg 子进程并读取 PCM 数据。"""
        while self._running:
            # ---- 启动 FFmpeg ----
            proc = self._spawn_ffmpeg()
            if proc is None:
                # FFmpeg 无法启动 → 降级
                logger.warning(
                    "FFmpeg 启动失败，音频检测降级: %s", self._stream_id
                )
                self._degraded = True
                return  # 退出线程

            with self._lock:
                self._process = proc

            try:
                self._read_pcm_loop(proc)
            except Exception as e:
                logger.error("PCM 读取循环异常: %s", e)
            finally:
                self._terminate_process()

            if not self._running:
                break

            # ---- 重连逻辑 ----
            self._reconnect_count += 1
            max_reconnects = _acfg("MAX_RECONNECTS")
            if self._reconnect_count > max_reconnects:
                logger.error(
                    "FFmpeg 重连 %d 次失败，音频检测降级: %s",
                    max_reconnects,
                    self._stream_id,
                )
                self._degraded = True
                break

            logger.info(
                "FFmpeg 断开，%.1fs 后重连 (%d/%d): %s",
                _acfg("RECONNECT_DELAY"),
                self._reconnect_count,
                max_reconnects,
                self._stream_id,
            )
            time.sleep(_acfg("RECONNECT_DELAY"))

    def _read_pcm_loop(self, proc: subprocess.Popen):
        """从 FFmpeg stdout 循环读取 PCM 并组装为音频块。"""
        buffer = bytearray()

        while self._running:
            # 每次读取一个完整音频块的字节量
            try:
                # chunk_bytes 可能很大（3s × 32000 × 2B = 192KB），
                # 使用 os.read 而非 proc.stdout.read 避免阻塞超时问题
                chunk = os.read(proc.stdout.fileno(), max(self._chunk_bytes, 4096))
            except (ValueError, OSError) as e:
                logger.error("读取 FFmpeg stdout 失败: %s", e)
                break

            if not chunk:
                # FFmpeg 退出（EOF）
                stderr_output = ""
                try:
                    proc.wait(timeout=1.0)
                    if proc.stderr:
                        remaining = proc.stderr.read()
                        if remaining:
                            stderr_output = remaining.decode("utf-8", errors="replace")
                except Exception:
                    pass

                if proc.returncode != 0:
                    logger.warning(
                        "FFmpeg 异常退出 (code=%d): %s stderr: %s",
                        proc.returncode,
                        self._stream_id,
                        stderr_output[:200],
                    )
                else:
                    logger.info("FFmpeg 正常退出: %s", self._stream_id)
                break

            buffer.extend(chunk)

            # 当缓冲区达到一个完整音频块时触发回调
            while len(buffer) >= self._chunk_bytes:
                chunk_bytes = buffer[:self._chunk_bytes]
                del buffer[:self._chunk_bytes]

                # 转换为 float32 numpy 数组 [-1.0, 1.0]
                pcm_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
                pcm_float = pcm_int16.astype(np.float32) / 32768.0

                if self._on_chunk and not self._degraded:
                    try:
                        self._on_chunk(pcm_float, time.time())
                    except Exception as e:
                        logger.error(
                            "音频回调异常 (stream=%s): %s",
                            self._stream_id,
                            e,
                            exc_info=True,
                        )


# ---------------------------------------------------------------------------
# 全局采集器注册表
# ---------------------------------------------------------------------------

_captures: dict[str, AudioCapture] = {}
_captures_lock = threading.Lock()


def get_or_create_audio_capture(
    rtsp_url: str,
    stream_id: str = "",
    on_audio_chunk: Callable[[np.ndarray, float], None] = None,
) -> AudioCapture:
    """获取或创建指定流 ID 的音频采集器（单例模式）。

    Args:
        rtsp_url: RTSP 流地址。
        stream_id: 业务流 ID。
        on_audio_chunk: 音频块回调（仅首次创建时生效）。

    Returns:
        AudioCapture 实例。
    """
    key = stream_id or rtsp_url
    with _captures_lock:
        if key not in _captures:
            _captures[key] = AudioCapture(rtsp_url, stream_id, on_audio_chunk)
        return _captures[key]


def stop_all_audio_captures():
    """停止所有音频采集器（进程退出前调用）。"""
    with _captures_lock:
        for key, cap in list(_captures.items()):
            cap.stop()
            del _captures[key]
    logger.info("所有 AudioCapture 已停止")

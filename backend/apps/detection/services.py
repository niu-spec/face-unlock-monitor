"""检测服务模块 — 危险区域与异常检测（Django 版）。

负责：
  - 危险区域闯入 / 距边缘过近 / 异常停留检测（YOLO 行人检测 + IoU 追踪 + 多边形碰撞）
  - 着火检测（三区间 HSV + RGB 暖色兜底 + 连通域滤波，面积阈值 15%）
  - 摔倒检测（IoU 跨帧追踪 + 状态持久化 + 双路径 + 中心点判定；容忍 YOLO 横向人体间歇丢帧）
  - 异常声学事件检测（PANNs CNN14 音频分类）★ v1.3 新增
  - 音视频联动告警（AVCorrelationBuffer）★ v1.3 新增

由团队成员 D（李东礼）负责实现和维护。

告警通过 apps.alerts.services.create_alert() 写入（同进程直调，避免 HTTP POST
被 AlertViewSet 的 IsAuthenticated 拦截，OpenSpec design.md 已注明同进程允许直调）。

行人检测：优先使用 YOLOv8n，若不可用则自动降级为 HOG。
音频检测：从 RTSP 流提取音频，PANNs CNN14 分类，RTSP 无音频轨道时自动降级。
"""

import json
import logging
import threading
import time
from collections import defaultdict
from typing import Optional

import cv2
import numpy as np

try:
    from ultralytics import YOLO

    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 检测配置（可在 Django settings 中覆盖）
# ---------------------------------------------------------------------------

DETECTION_CONFIG = {
    # --- 视频处理 ---
    "FRAME_WIDTH": 480,
    "FRAME_HEIGHT": 480,
    "FRAME_SKIP": 3,
    # --- 着火（FIRE）---
    # 策略：颜色宽松捕获火焰像素，面积严格过滤误报。
    # 三个 HSV 区间 + RGB 暖色确保真火焰不漏检，
    # 20% 面积阈值 + 连通域过滤挡住暖色灯光/反光。
    # Range 1: 红/橙/黄明焰
    "FIRE_HSV_LOWER_1": (0, 55, 80),
    "FIRE_HSV_UPPER_1": (35, 255, 255),
    # Range 2: 深红/品红区域
    "FIRE_HSV_LOWER_2": (150, 55, 80),
    "FIRE_HSV_UPPER_2": (180, 255, 255),
    # Range 3: 黄/白热焰核心（高亮）
    "FIRE_HSV_LOWER_3": (15, 15, 200),
    "FIRE_HSV_UPPER_3": (38, 130, 255),
    # 面积阈值：画面占比 ≥ 20% 才触发（真火焰大面积，灯光反光分散）
    "FIRE_AREA_THRESHOLD": 0.20,
    # 火焰区域最小连通域（过滤碎片噪点）
    "FIRE_MIN_CONTOUR_AREA": 500,
    # 亮核判定：真火焰有高亮核心（V > 200），墙/暖色物体没有
    # 火焰掩码内亮核像素占比 ≥ 此值才认定为真火
    "FIRE_BRIGHT_CORE_V": 200,
    "FIRE_BRIGHT_CORE_RATIO": 0.08,
    # --- 摔倒（FALL）---
    # 双路径判定 + 中心点追踪：
    #   Path 1（标准）: 曾站立 → AR 骤降或中心点大幅下移 → 横向姿态（多帧确认）
    #   Path 2（快速）: 极端横向姿态（h/w < 0.55），无需曾站立直接告警
    # 蹲下 vs 摔倒：蹲下变化缓慢且中心点小幅下移，AR 速度不触发骤变阈值。
    "FALL_ASPECT_RATIO_THRESHOLD": 0.90,       # 高宽比阈值（< 此值视为横向，1.0=正方形）
    "FALL_EXTREME_AR_THRESHOLD": 0.55,         # 极端高宽比（直接触发，不要求曾站立）
    "FALL_PERSIST_FRAMES": 5,                  # 横向姿态持续帧数
    "FALL_MIN_STANDING_RATIO": 1.45,           # 站立高宽比（≥ 此值视为站立）
    "FALL_CENTER_DROP_RATIO": 0.20,            # 中心点下移比例（> 此值视为骤降）
    "FALL_AR_VELOCITY_THRESHOLD": 0.50,        # AR 变化速率阈值（/s，dt 上限 0.5s 防丢帧稀释）
    "FALL_MAX_STANDING_FRAMES_TO_RESET": 2,    # 非站立帧数阈值（降低，避免短暂遮挡重置）
    # --- YOLO 行人检测（优先）---
    "YOLO_MODEL": "yolov8n.pt",
    "YOLO_IMGSZ": 480,
    "YOLO_CONFIDENCE_THRESHOLD": 0.35,
    "YOLO_IOU_THRESHOLD": 0.45,
    "YOLO_PERSON_CLASS_ID": 0,
    # --- HOG 行人检测（YOLO 不可用时降级）---
    "HOG_MAX_DIM": 480,
    "HOG_WIN_STRIDE": (4, 4),
    "HOG_PADDING": (8, 8),
    "HOG_SCALE": 1.05,
    "HOG_CONFIDENCE_THRESHOLD": 0.5,
    "HOG_NMS_THRESHOLD": 0.3,
    # --- 闯入检测（INTRUSION）---
    "INTRUSION_PERSIST_FRAMES": 1,
    # --- 告警冷却（秒）---
    "ALERT_COOLDOWN_SECONDS": {
        "FIRE": 30,
        "FALL": 15,
        "INTRUSION": 10,
        "PROXIMITY": 10,
        "LOITER": 15,
        # 音频告警冷却 ★ v1.3
        "CRYING": 20,
        "GLASS_BREAK": 10,
        "EMERGENCY": 30,  # 联动紧急告警
    },
}


# ZoneEditor 画布尺寸（前端固定 640×480，检测帧需按比例缩放）
ZONE_EDITOR_WIDTH = 640
ZONE_EDITOR_HEIGHT = 480


def _cfg(key: str):
    """从 Django settings 读取检测配置，未设置时使用默认值。"""
    try:
        from django.conf import settings

        return getattr(settings, "DETECTION_CONFIG", {}).get(
            key, DETECTION_CONFIG[key]
        )
    except Exception:
        return DETECTION_CONFIG[key]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _parse_polygon(points) -> Optional[np.ndarray]:
    """将多边形坐标解析为 (N, 1, 2) 格式的 numpy 数组。

    Args:
        points: JSON 数组 [[x1,y1],[x2,y2],...] 或 JSON 字符串。

    Returns:
        numpy 数组或 None（解析失败时）。
    """
    if isinstance(points, str):
        try:
            points = json.loads(points)
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Failed to parse polygon points: %s", points)
            return None
    if not points or len(points) < 3:
        return None
    try:
        return np.array(points, dtype=np.int32).reshape((-1, 1, 2))
    except (ValueError, TypeError):
        return None


def _parse_polygon_for_frame(
    points, frame_width: int, frame_height: int
) -> Optional[np.ndarray]:
    """将 ZoneEditor 坐标缩放至实际检测帧尺寸。"""
    polygon = _parse_polygon(points)
    if polygon is None or frame_width <= 0 or frame_height <= 0:
        return polygon

    scale_x = frame_width / ZONE_EDITOR_WIDTH
    scale_y = frame_height / ZONE_EDITOR_HEIGHT
    if abs(scale_x - 1.0) < 0.01 and abs(scale_y - 1.0) < 0.01:
        return polygon

    scaled = polygon.astype(np.float64).copy()
    scaled[:, 0, 0] *= scale_x
    scaled[:, 0, 1] *= scale_y
    return scaled.astype(np.int32)


def _scale_editor_distance(
    distance: int, frame_width: int, frame_height: int
) -> int:
    """将 ZoneEditor 中的像素距离缩放至检测帧坐标系。"""
    scale_x = frame_width / ZONE_EDITOR_WIDTH
    scale_y = frame_height / ZONE_EDITOR_HEIGHT
    return max(1, int(round(distance * (scale_x + scale_y) / 2)))


def _is_point_in_polygon(point: tuple, polygon: np.ndarray) -> bool:
    """判断点是否在多边形内部。"""
    return cv2.pointPolygonTest(polygon, point, False) >= 0


def _is_rect_in_polygon(
    x: int, y: int, w: int, h: int, polygon: np.ndarray
) -> bool:
    """判断人体框底部中心（脚部）或几何中心是否在多边形内部。

    脚部优先（人站在区域内），中心兜底（人上半身探入区域）。
    """
    cx, cy = x + w // 2, y + h // 2
    # 底部中心 = 脚部位置
    foot_y = y + h
    return _is_point_in_polygon((cx, foot_y), polygon) or _is_point_in_polygon(
        (cx, cy), polygon
    )


def _rect_center(x: int, y: int, w: int, h: int) -> tuple[int, int]:
    return x + w // 2, y + h // 2


def _distance_point_to_polygon(point: tuple[int, int], polygon: np.ndarray) -> float:
    """点到多边形轮廓的有符号距离（OpenCV measureDist=True）。

    当前 OpenCV 版本约定：内部为正，外部为负，绝对值为到边界的像素距离。
    """
    return float(cv2.pointPolygonTest(polygon, point, True))


def _segments_intersect(
    a: tuple[int, int],
    b: tuple[int, int],
    c: tuple[int, int],
    d: tuple[int, int],
) -> bool:
    """Return whether two closed 2D segments intersect or touch."""

    def cross(origin, first, second) -> int:
        return (
            (first[0] - origin[0]) * (second[1] - origin[1])
            - (first[1] - origin[1]) * (second[0] - origin[0])
        )

    def on_segment(start, point, end) -> bool:
        return (
            min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        )

    ab_c = cross(a, b, c)
    ab_d = cross(a, b, d)
    cd_a = cross(c, d, a)
    cd_b = cross(c, d, b)
    if (ab_c > 0) != (ab_d > 0) and (cd_a > 0) != (cd_b > 0):
        return True
    return (
        (ab_c == 0 and on_segment(a, c, b))
        or (ab_d == 0 and on_segment(a, d, b))
        or (cd_a == 0 and on_segment(c, a, d))
        or (cd_b == 0 and on_segment(c, b, d))
    )


def _polygon_intersects_rect(
    polygon: np.ndarray, x: int, y: int, width: int, height: int
) -> bool:
    """Return whether a polygon and a person bounding box overlap or touch."""
    if width <= 0 or height <= 0:
        return False

    right, bottom = x + width, y + height
    rect_points = [(x, y), (right, y), (right, bottom), (x, bottom)]
    if any(cv2.pointPolygonTest(polygon, point, False) >= 0 for point in rect_points):
        return True

    points = [tuple(map(int, point[0])) for point in polygon]
    if any(x <= px <= right and y <= py <= bottom for px, py in points):
        return True

    rect_edges = list(zip(rect_points, rect_points[1:] + rect_points[:1]))
    polygon_edges = list(zip(points, points[1:] + points[:1]))
    return any(
        _segments_intersect(rect_start, rect_end, poly_start, poly_end)
        for rect_start, rect_end in rect_edges
        for poly_start, poly_end in polygon_edges
    )


def _normalize_forbidden_roles(forbidden) -> list[str]:
    if isinstance(forbidden, str):
        return [r.strip() for r in forbidden.split(",") if r.strip()]
    if isinstance(forbidden, list):
        return [str(r).strip() for r in forbidden if str(r).strip()]
    return []


# ---------------------------------------------------------------------------
# 简单人员追踪器（IoU-based）
# ---------------------------------------------------------------------------


class SimplePersonTracker:
    """基于 IoU 的轻量级人员追踪器。

    解决 YOLO/HOG 每帧独立检测导致的 track_id 不连续问题。
    同一人在不同帧被分配相同 track_id，使摔倒/徘徊/闯入持续检测成为可能。

    算法：
      1. 计算已有轨迹与当前检测之间的 IoU 矩阵
      2. 贪婪匹配（按 IoU 降序分配）
      3. 未匹配的检测 → 创建新轨迹
      4. 未匹配的轨迹 → lost_frames += 1，超阈值后删除
      5. 匹配成功的轨迹 → 更新位置，lost_frames 归零
    """

    def __init__(self, max_lost_frames: int = 10, iou_threshold: float = 0.3):
        # tid → {"bbox": (x, y, w, h), "lost": int}
        self._tracks: dict[int, dict] = {}
        self._next_id = 0
        self._max_lost = max_lost_frames
        self._iou_threshold = iou_threshold

    def update(self, boxes: list[dict]) -> list[dict]:
        """为当前帧检测框分配稳定的 track_id。

        Args:
            boxes: [{"x", "y", "w", "h"}, ...] 当前帧检测结果。

        Returns:
            同列表，但每个 box 的 track_id 被替换为跨帧稳定的 ID。
        """
        if not boxes:
            # 无检测 → 所有轨迹丢失计数+1
            for tid in list(self._tracks.keys()):
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self._max_lost:
                    del self._tracks[tid]
            return []

        # 提取已有轨迹的 bbox
        active_tids = list(self._tracks.keys())
        track_boxes = [self._tracks[tid]["bbox"] for tid in active_tids]

        # 计算 IoU 矩阵
        num_tracks = len(active_tids)
        num_dets = len(boxes)
        iou_matrix = np.zeros((num_tracks, num_dets), dtype=np.float32)
        for t in range(num_tracks):
            tx, ty, tw, th = track_boxes[t]
            for d in range(num_dets):
                dx, dy, dw, dh = boxes[d]["x"], boxes[d]["y"], boxes[d]["w"], boxes[d]["h"]
                iou_matrix[t, d] = self._compute_iou(tx, ty, tw, th, dx, dy, dw, dh)

        matched_track_ids: set[int] = set()
        matched_det_ids: set[int] = set()

        # 贪婪匹配（按 IoU 从高到低）
        if num_tracks > 0 and num_dets > 0:
            # 收集所有 (iou, t, d) 三元组并按 IoU 降序排列
            candidates = []
            for t in range(num_tracks):
                for d in range(num_dets):
                    iou = iou_matrix[t, d]
                    if iou >= self._iou_threshold:
                        candidates.append((iou, t, d))
            candidates.sort(key=lambda x: x[0], reverse=True)

            for iou, t, d in candidates:
                tid = active_tids[t]
                if tid in matched_track_ids or d in matched_det_ids:
                    continue
                # 匹配成功
                boxes[d]["track_id"] = tid
                self._tracks[tid]["bbox"] = (
                    boxes[d]["x"], boxes[d]["y"], boxes[d]["w"], boxes[d]["h"]
                )
                self._tracks[tid]["lost"] = 0
                matched_track_ids.add(tid)
                matched_det_ids.add(d)

        # 未匹配的检测 → 新轨迹
        for d in range(num_dets):
            if d not in matched_det_ids:
                tid = self._next_id
                self._next_id += 1
                boxes[d]["track_id"] = tid
                self._tracks[tid] = {
                    "bbox": (boxes[d]["x"], boxes[d]["y"], boxes[d]["w"], boxes[d]["h"]),
                    "lost": 0,
                }

        # 未匹配的轨迹 → lost++
        for tid in active_tids:
            if tid not in matched_track_ids:
                self._tracks[tid]["lost"] += 1
                if self._tracks[tid]["lost"] > self._max_lost:
                    del self._tracks[tid]

        return boxes

    def remove_track(self, tid: int):
        """手动移除指定轨迹（如人员已离开画面）。"""
        self._tracks.pop(tid, None)

    @staticmethod
    def _compute_iou(
        x1: int, y1: int, w1: int, h1: int,
        x2: int, y2: int, w2: int, h2: int,
    ) -> float:
        """计算两个轴对齐矩形框的 IoU。"""
        ix1 = max(x1, x2)
        iy1 = max(y1, y2)
        ix2 = min(x1 + w1, x2 + w2)
        iy2 = min(y1 + h1, y2 + h2)
        inter_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area1 = w1 * h1
        area2 = w2 * h2
        union_area = area1 + area2 - inter_area
        return inter_area / union_area if union_area > 0 else 0.0


# ---------------------------------------------------------------------------
# 检测服务主类
# ---------------------------------------------------------------------------


class DetectionService:
    """危险区域与异常检测服务。

    在视频处理流水线中，每 N 帧调用一次 process_frame()，
    返回检测结果列表，并通过 apps.alerts.services 写入告警。

    Usage:
        service = DetectionService()
        results = service.process_frame(frame, stream_id, person_boxes, face_roles)
    """

    def __init__(self):
        """初始化 YOLO 行人检测器（HOG 降级）及告警冷却计时器。"""
        self._detector_type = "HOG"  # 默认降级
        self._yolo = None

        if _YOLO_AVAILABLE:
            try:
                model_path = _cfg("YOLO_MODEL")
                self._yolo = YOLO(model_path)
                self._detector_type = "YOLO"
                logger.info("YOLO model loaded: %s", model_path)
            except Exception as e:
                logger.warning("YOLO init failed, falling back to HOG: %s", e)

        if self._detector_type == "HOG":
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(
                cv2.HOGDescriptor_getDefaultPeopleDetector()
            )
            logger.info("HOG pedestrian detector initialized (fallback)")

        self._cooldown: dict[str, dict[str, float]] = defaultdict(dict)
        self._fall_counter: dict[int, int] = defaultdict(int)
        self._fall_last_seen: dict[int, float] = {}   # 摔倒状态最后活跃时间（秒级 epoch）
        self._person_history: dict[int, dict] = {}    # 人物历史状态（AR/中心点/站立追踪）
        self._loiter_since: dict[tuple[int, int], float] = {}
        self._current_snapshot_frame = None
        self._current_household_id: int | None = None
        self._intrusion_counter: dict[str, dict[int, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # 跨帧人员追踪器（解决 YOLO/HOG 每帧独立检测导致的 track_id 不连续）
        self._person_tracker = SimplePersonTracker(
            max_lost_frames=15, iou_threshold=0.20
        )
        # YOLO/HOG 推理与追踪状态在进程内单例上共享，多路流并发时串行化。
        self._inference_lock = threading.Lock()

        # ★ v1.3 音视频联动
        self._av_correlation = None
        self._audio_service = None

        logger.info(
            "DetectionService initialized (detector=%s, Django)",
            self._detector_type,
        )

    # -----------------------------------------------------------------------
    # 公共入口
    # -----------------------------------------------------------------------

    def process_frame(
        self,
        frame: np.ndarray,
        stream_id: str,
        person_boxes: Optional[list[dict]] = None,
        face_roles: Optional[dict[int, str]] = None,
        zones: Optional[list[dict]] = None,
        snapshot_frame: Optional[np.ndarray] = None,
        household_id: int | None = None,
        *,
        include_fast: bool = True,
    ) -> list[dict]:
        """处理单帧画面，执行全部检测逻辑。

        Args:
            frame: BGR 格式的 numpy 图像数组 (H, W, 3)。
            stream_id: 摄像头流 ID（如 "living_room"）。
            person_boxes: 已检测的人体框列表，
                [{'x', 'y', 'w', 'h', 'track_id'}, ...]。
                若为 None，则内部使用 YOLO 自行检测（HOG 降级）。
            face_roles: 人脸识别结果，{track_id: role}，
                role 为 'adult' / 'child' / 'stranger'。
            zones: 危险区域配置列表，每项含
                {'id', 'name', 'points_json', 'forbidden_roles',
                 'safe_distance', 'dwell_time'}。
            include_fast: 是否执行着火/摔倒等快速 overlay 检测。
                WebRTC 快速路径可在外部先跑 fast alerts，此处传 False。

        Returns:
            detection_results: 检测结果列表。
        """
        results: list[dict] = []

        if frame is None or frame.size == 0:
            return results

        self._current_snapshot_frame = snapshot_frame
        self._current_household_id = household_id
        frame_height, frame_width = frame.shape[:2]

        # 内部行人检测（若调用方未提供 person_boxes）
        if person_boxes is None:
            person_boxes = self._detect_pedestrians(frame)

        # 1. 危险区域：闯入 / 距边缘过近 / 异常停留
        if zones:
            results.extend(
                self._detect_zone_violations(
                    stream_id,
                    zones,
                    person_boxes,
                    face_roles or {},
                    frame_width,
                    frame_height,
                )
            )

        if include_fast:
            results.extend(self.detect_fast_alerts(
                frame,
                stream_id,
                person_boxes,
                household_id=household_id,
                snapshot_frame=snapshot_frame,
                enqueue=False,
            ))

        # ★ v1.3 视频检测事件入队音视频联动缓冲器
        if results:
            self._enqueue_video_results(
                stream_id=stream_id, results=results
            )

        self._current_snapshot_frame = None
        self._current_household_id = None
        return results

    def detect_fire_alerts(
        self,
        frame: np.ndarray,
        stream_id: str,
        *,
        household_id: int | None = None,
        snapshot_frame: Optional[np.ndarray] = None,
    ) -> list[dict]:
        """Fast-path fire detection for WebRTC canvas overlays."""
        if frame is None or frame.size == 0:
            return []

        previous_snapshot = self._current_snapshot_frame
        previous_household = self._current_household_id
        self._current_snapshot_frame = snapshot_frame
        self._current_household_id = household_id
        try:
            return self._detect_fire(frame, stream_id)
        finally:
            self._current_snapshot_frame = previous_snapshot
            self._current_household_id = previous_household

    def detect_fall_alerts(
        self,
        person_boxes: list[dict],
        stream_id: str,
        *,
        household_id: int | None = None,
        snapshot_frame: Optional[np.ndarray] = None,
    ) -> list[dict]:
        """Fast-path fall detection for WebRTC canvas overlays."""
        previous_snapshot = self._current_snapshot_frame
        previous_household = self._current_household_id
        self._current_snapshot_frame = snapshot_frame
        self._current_household_id = household_id
        try:
            return self._detect_fall(person_boxes, stream_id)
        finally:
            self._current_snapshot_frame = previous_snapshot
            self._current_household_id = previous_household

    def detect_fast_alerts(
        self,
        frame: np.ndarray,
        stream_id: str,
        person_boxes: Optional[list[dict]] = None,
        *,
        household_id: int | None = None,
        snapshot_frame: Optional[np.ndarray] = None,
        enqueue: bool = True,
    ) -> list[dict]:
        """Run fire/fall detection for low-latency WebRTC overlays."""
        if frame is None or frame.size == 0:
            return []

        boxes = person_boxes or []
        results: list[dict] = []
        results.extend(
            self.detect_fire_alerts(
                frame,
                stream_id,
                household_id=household_id,
                snapshot_frame=snapshot_frame,
            )
        )
        results.extend(
            self.detect_fall_alerts(
                boxes,
                stream_id,
                household_id=household_id,
                snapshot_frame=snapshot_frame,
            )
        )
        if enqueue and results:
            self.enqueue_detection_results(stream_id, results)
        return results

    def enqueue_detection_results(
        self, stream_id: str, results: list[dict]
    ) -> None:
        """Publish fast-path detection results to the AV correlation buffer."""
        if results:
            self._enqueue_video_results(stream_id=stream_id, results=results)

    # -----------------------------------------------------------------------
    # 行人检测（YOLO 优先，HOG 降级）
    # -----------------------------------------------------------------------

    def detect_people(self, frame: np.ndarray) -> list[dict]:
        """返回 YOLO 检出的人体框；YOLO 不可用时自动使用 HOG 降级。"""
        if frame is None or frame.size == 0:
            return []
        return self._detect_pedestrians(frame)
    def _detect_pedestrians(self, frame: np.ndarray) -> list[dict]:
        """YOLO 行人检测，不可用时自动降级为 HOG。

        检测后通过 SimplePersonTracker 分配跨帧稳定的 track_id。
        YOLO 第一轮 0 人时自动降置信度重扫，应对横向/非直立人体。
        """
        with self._inference_lock:
            if self._detector_type == "YOLO" and self._yolo is not None:
                boxes = self._detect_pedestrians_yolo(frame)
                if not boxes:
                    # 低置信度重扫：摔倒/横向人体 YOLO 检测不稳定
                    boxes = self._detect_pedestrians_yolo(frame, conf=0.20)
            else:
                boxes = self._detect_pedestrians_hog(frame)
            # 跨帧追踪：为每个检测框分配稳定的 track_id
            return self._person_tracker.update(boxes)

    def _detect_pedestrians_yolo(
        self, frame: np.ndarray, conf: float | None = None
    ) -> list[dict]:
        """使用 YOLOv8n 检测行人（class_id=0 即 person）。"""
        results = self._yolo(
            frame,
            imgsz=_cfg("YOLO_IMGSZ"),
            conf=conf if conf is not None else _cfg("YOLO_CONFIDENCE_THRESHOLD"),
            iou=_cfg("YOLO_IOU_THRESHOLD"),
            classes=[_cfg("YOLO_PERSON_CLASS_ID")],
            verbose=False,
        )

        boxes = []
        if results and len(results) > 0:
            result = results[0]
            if result.boxes is not None:
                for i, box in enumerate(result.boxes.xyxy):
                    x1, y1, x2, y2 = box.tolist()
                    x, y = int(x1), int(y1)
                    w, h = int(x2 - x1), int(y2 - y1)
                    conf = (
                        float(result.boxes.conf[i])
                        if result.boxes.conf is not None
                        else 1.0
                    )
                    boxes.append(
                        {
                            "x": x,
                            "y": y,
                            "w": w,
                            "h": h,
                            "track_id": i,
                            "confidence": round(conf, 3),
                        }
                    )
        return boxes

    def _detect_pedestrians_hog(self, frame: np.ndarray) -> list[dict]:
        """使用 HOG 检测器检测行人（降级方案）。

        优化：
          - 大帧先降采样到 HOG_MAX_DIM，检测完再映射回原始坐标
          - 对重叠框做 NMS 去重
        """
        h, w = frame.shape[:2]
        max_dim = _cfg("HOG_MAX_DIM")
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects, weights = self._hog.detectMultiScale(
            gray,
            winStride=_cfg("HOG_WIN_STRIDE"),
            padding=_cfg("HOG_PADDING"),
            scale=_cfg("HOG_SCALE"),
        )

        # 收集通过置信度阈值的框
        threshold = _cfg("HOG_CONFIDENCE_THRESHOLD")
        candidates: list[tuple[int, int, int, int, float]] = []
        for i, (x, y, bw, bh) in enumerate(rects):
            if weights[i] >= threshold:
                candidates.append((int(x), int(y), int(bw), int(bh), float(weights[i])))

        if not candidates:
            return []

        # NMS 去重
        nms_threshold = _cfg("HOG_NMS_THRESHOLD")
        keep = self._nms(candidates, nms_threshold)

        boxes = []
        for idx in keep:
            x, y, bw, bh, _weight = candidates[idx]
            if scale != 1.0:
                x, y = int(x / scale), int(y / scale)
                bw, bh = int(bw / scale), int(bh / scale)
            boxes.append(
                {
                    "x": x,
                    "y": y,
                    "w": bw,
                    "h": bh,
                    "track_id": idx,
                }
            )
        return boxes

    @staticmethod
    def _nms(
        boxes: list[tuple[int, int, int, int, float]], threshold: float
    ) -> list[int]:
        """简单的 IoU-based NMS，返回保留的框索引列表。"""
        if not boxes:
            return []

        # 按置信度降序排列
        indexed = sorted(
            enumerate(boxes), key=lambda item: item[1][4], reverse=True
        )
        keep: list[int] = []

        while indexed:
            idx, (x1, y1, w1, h1, _) = indexed.pop(0)
            keep.append(idx)

            filtered = []
            for j, (x2, y2, w2, h2, conf) in indexed:
                # 计算 IoU
                ix1, iy1 = max(x1, x2), max(y1, y2)
                ix2, iy2 = min(x1 + w1, x2 + w2), min(y1 + h1, y2 + h2)
                inter_area = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area1, area2 = w1 * h1, w2 * h2
                union_area = area1 + area2 - inter_area
                iou = inter_area / union_area if union_area > 0 else 0

                if iou < threshold:
                    filtered.append((j, (x2, y2, w2, h2, conf)))

            indexed = filtered

        return keep

    # -----------------------------------------------------------------------
    # 1. 危险区域检测（INTRUSION / PROXIMITY / LOITER）
    # -----------------------------------------------------------------------

    def _detect_zone_violations(
        self,
        stream_id: str,
        zones: list[dict],
        person_boxes: list[dict],
        face_roles: dict[int, str],
        frame_width: int,
        frame_height: int,
    ) -> list[dict]:
        """检测危险区域闯入、距边缘过近与异常停留。"""
        results: list[dict] = []
        active_loiter_keys: set[tuple[int, int]] = set()
        now = time.time()
        active_ids = {box.get("track_id", -1) for box in person_boxes}
        self._cleanup_stale_tracks(active_ids)
        persist = _cfg("INTRUSION_PERSIST_FRAMES")

        for zone in zones:
            if not zone.get("is_active", zone.get("enabled", True)):
                continue

            polygon = _parse_polygon_for_frame(
                zone.get("points_json", ""), frame_width, frame_height
            )
            if polygon is None:
                continue

            forbidden = _normalize_forbidden_roles(zone.get("forbidden_roles", []))

            zone_id = zone.get("id", 0)
            zone_name = zone.get("name", "危险区域")
            safe_distance = _scale_editor_distance(
                max(0, int(zone.get("safe_distance") or 50)),
                frame_width,
                frame_height,
            )
            dwell_time = max(1, int(zone.get("dwell_time") or 5))

            zone_key = str(zone.get("id", zone.get("name", "unknown")))

            for box in person_boxes:
                tid = box.get("track_id", -1)
                role = face_roles.get(tid, "stranger")
                # An unrecognized person is always security-sensitive.  Keep
                # configured role filtering for known household members, but
                # never let a missing face-role mapping suppress an intrusion.
                if role != "stranger" and role not in forbidden:
                    self._intrusion_counter[zone_key][tid] = 0
                    continue

                cx, cy = _rect_center(box["x"], box["y"], box["w"], box["h"])
                signed_dist = _distance_point_to_polygon((cx, cy), polygon)
                inside = _polygon_intersects_rect(
                    polygon, box["x"], box["y"], box["w"], box["h"]
                )
                bbox = (box["x"], box["y"], box["w"], box["h"])

                if inside:
                    # 默认一帧即触发；可通过 INTRUSION_PERSIST_FRAMES 覆盖。
                    self._intrusion_counter[zone_key][tid] += 1

                    if self._intrusion_counter[zone_key][tid] >= persist:
                        if self._check_cooldown("INTRUSION", stream_id):
                            msg = f"[{zone_name}] 检测到 {role} 闯入禁区"
                            persisted = self._create_alert(
                                alert_type="INTRUSION",
                                level="HIGH",
                                stream_id=stream_id,
                                description=msg,
                            )
                            results.append(
                                {
                                    "alert_type": "INTRUSION",
                                    "message": msg,
                                    "bbox": bbox,
                                    "severity": "high",
                                    "zone_id": zone_id,
                                    "zone_name": zone_name,
                                }
                            )
                            logger.info("Zone intrusion: %s", msg)
                            if persisted:
                                self._intrusion_counter[zone_key][tid] = 0
                            else:
                                self._release_cooldown("INTRUSION", stream_id)
                else:
                    self._intrusion_counter[zone_key][tid] = 0

                # 距边缘过近（PROXIMITY）：人在外部且距边界 < safe_distance
                edge_gap = abs(signed_dist) if signed_dist < 0 else 0.0
                if not inside and signed_dist < 0 and edge_gap < safe_distance:
                    if self._check_cooldown("PROXIMITY", f"{stream_id}:{zone_id}"):
                        msg = (
                            f"[{zone_name}] {role} 距禁区边缘过近"
                            f"（{edge_gap:.0f}px < {safe_distance}px）"
                        )
                        self._create_alert(
                            alert_type="PROXIMITY",
                            level="MEDIUM",
                            stream_id=stream_id,
                            description=msg,
                        )
                        results.append(
                            {
                                "alert_type": "PROXIMITY",
                                "message": msg,
                                "bbox": bbox,
                                "severity": "medium",
                                "zone_id": zone_id,
                                "zone_name": zone_name,
                                "detail": {
                                    "distance_px": round(edge_gap, 1),
                                    "safe_distance_px": safe_distance,
                                },
                            }
                        )
                        logger.info("Zone proximity: %s", msg)

                # 异常停留（LOITER）：在禁区内或紧贴边界外
                in_loiter_area = inside or (
                    signed_dist < 0 and abs(signed_dist) < safe_distance
                )
                if in_loiter_area:
                    loiter_key = (int(zone_id), int(tid))
                    active_loiter_keys.add(loiter_key)
                    started = self._loiter_since.get(loiter_key)
                    if started is None:
                        self._loiter_since[loiter_key] = now
                    elif now - started >= dwell_time:
                        if self._check_cooldown("LOITER", f"{stream_id}:{zone_id}"):
                            msg = (
                                f"[{zone_name}] {role} 在禁区附近停留超过"
                                f" {dwell_time} 秒"
                            )
                            self._create_alert(
                                alert_type="LOITER",
                                level="MEDIUM",
                                stream_id=stream_id,
                                description=msg,
                            )
                            results.append(
                                {
                                    "alert_type": "LOITER",
                                    "message": msg,
                                    "bbox": bbox,
                                    "severity": "medium",
                                    "zone_id": zone_id,
                                    "zone_name": zone_name,
                                    "detail": {
                                        "dwell_seconds": round(now - started, 1),
                                        "dwell_threshold": dwell_time,
                                    },
                                }
                            )
                            logger.info("Zone loiter: %s", msg)
                            self._loiter_since[loiter_key] = now

        stale = [key for key in self._loiter_since if key not in active_loiter_keys]
        for key in stale:
            del self._loiter_since[key]

        return results

    # -----------------------------------------------------------------------
    # 2. 着火检测（FIRE）
    # -----------------------------------------------------------------------

    def _detect_fire(self, frame: np.ndarray, stream_id: str) -> list[dict]:
        """检测画面中火焰区域（HSV 颜色 + RGB 暖色双路融合）。

        策略：HSV 三区间掩码 + RGB 暖色掩码 → OR 合并 → 形态滤波 → 连通域去噪 → 面积判定。
        RGB 暖色作为兜底：R 通道明显大于 G 和 B 的像素（火焰独有特征）。
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]
        frame_area = h * w

        # 每 30 帧输出一次诊断
        if not hasattr(self, "_fire_debug_frame"):
            self._fire_debug_frame = 0
        self._fire_debug_frame += 1
        fire_log = self._fire_debug_frame % 30 == 0

        # ---- HSV 三区间火焰颜色掩码 ----
        mask1 = cv2.inRange(
            hsv,
            np.array(_cfg("FIRE_HSV_LOWER_1")),
            np.array(_cfg("FIRE_HSV_UPPER_1")),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array(_cfg("FIRE_HSV_LOWER_2")),
            np.array(_cfg("FIRE_HSV_UPPER_2")),
        )
        mask3 = cv2.inRange(
            hsv,
            np.array(_cfg("FIRE_HSV_LOWER_3")),
            np.array(_cfg("FIRE_HSV_UPPER_3")),
        )
        hsv_mask = cv2.bitwise_or(mask1, mask2)
        hsv_mask = cv2.bitwise_or(hsv_mask, mask3)
        hsv_area = cv2.countNonZero(hsv_mask)

        # ---- RGB 暖色兜底：R 通道显著大于 G 和 B ----
        r = frame[:, :, 2].astype(np.float32)
        g = frame[:, :, 1].astype(np.float32)
        b = frame[:, :, 0].astype(np.float32)
        rgb_warm = (
            (r > g * 1.2) & (r > b * 1.4) & (r > 80)
        )
        rgb_mask = (rgb_warm * 255).astype(np.uint8)
        rgb_area = cv2.countNonZero(rgb_mask)
        color_mask = cv2.bitwise_or(hsv_mask, rgb_mask)
        combined_area = cv2.countNonZero(color_mask)

        # ---- 形态滤波：先去噪再连接断裂区域 ----
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
        morph_area = cv2.countNonZero(mask)

        # 过滤小面积噪点
        min_contour_area = _cfg("FIRE_MIN_CONTOUR_AREA")
        num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        clean_mask = np.zeros_like(mask)
        kept = 0
        for label_id in range(1, num_labels):
            area = stats[label_id, cv2.CC_STAT_AREA]
            if area >= min_contour_area:
                clean_mask[labels == label_id] = 255
                kept += 1
        mask = clean_mask

        fire_area = cv2.countNonZero(mask)
        ratio = fire_area / frame_area if frame_area > 0 else 0

        # ---- 亮核判定：真火焰有高亮核心，墙壁/暖色物体没有 ----
        # 在火焰掩码内统计高亮像素（V > 200 + 低饱和）占比
        bright_core_mask = cv2.inRange(
            hsv,
            np.array([0, 0, _cfg("FIRE_BRIGHT_CORE_V")]),
            np.array([255, 100, 255]),
        )
        core_in_fire = cv2.bitwise_and(mask, bright_core_mask)
        core_pixels = cv2.countNonZero(core_in_fire)
        core_ratio = core_pixels / fire_area if fire_area > 0 else 0

        if fire_log:
            logger.info(
                "[FIRE DEBUG] 帧#%d stream=%s frame=%dx%d "
                "hsv=%.2f%% rgb=%.2f%% combined=%.2f%% "
                "morph=%.2f%% final=%.2f%%(%dcc,%dpx) "
                "core=%.1f%%(%dpx) threshold=%.1f%% core_min=%.1f%%",
                self._fire_debug_frame, stream_id, w, h,
                hsv_area / frame_area * 100,
                rgb_area / frame_area * 100,
                combined_area / frame_area * 100,
                morph_area / frame_area * 100,
                ratio * 100, kept, fire_area,
                core_ratio * 100, core_pixels,
                _cfg("FIRE_AREA_THRESHOLD") * 100,
                _cfg("FIRE_BRIGHT_CORE_RATIO") * 100,
            )

        if ratio < _cfg("FIRE_AREA_THRESHOLD"):
            return []

        # 亮核占比不足 → 大概率是墙壁/暖色物体，不是真火
        if core_ratio < _cfg("FIRE_BRIGHT_CORE_RATIO"):
            if fire_log:
                logger.info(
                    "[FIRE DEBUG] 帧#%d 面积达标但亮核不足(%.1f%% < %.1f%%), 跳过",
                    self._fire_debug_frame,
                    core_ratio * 100,
                    _cfg("FIRE_BRIGHT_CORE_RATIO") * 100,
                )
            return []

        if not self._check_cooldown("FIRE", stream_id):
            return []

        # 提取最大火焰连通域的包围框
        find_result = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = find_result[0] if len(find_result) == 2 else find_result[1]
        if contours:
            largest = max(contours, key=cv2.contourArea)
            x, y, fw, fh = cv2.boundingRect(largest)
        else:
            x, y, fw, fh = 0, 0, w, h

        msg = f"检测到疑似火焰区域（占比 {ratio:.1%}，面积 {fire_area}px）"

        self._create_alert(
            alert_type="FIRE",
            level="HIGH",
            stream_id=stream_id,
            description=msg,
        )

        logger.info("Fire detected: %s", msg)
        return [
            {
                "alert_type": "FIRE",
                "message": msg,
                "bbox": (x, y, fw, fh),
                "severity": "high",
                "detail": {
                    "area_ratio": round(ratio, 3),
                    "area_px": fire_area,
                },
            }
        ]

        return []

    # -----------------------------------------------------------------------
    # 3. 摔倒检测（FALL）
    # -----------------------------------------------------------------------

    def _cleanup_stale_tracks(self, active_ids: set[int]) -> None:
        """清理已离开画面的 track_id 残留计数器与历史状态。

        重要：摔倒检测的 _fall_counter 和 _person_tracker
        **不在此处清理**。原因：YOLO 对横向/非直立人体检测不稳定，
        若人摔倒后短暂丢检测，立即清空计数器会导致摔倒永远无法触发。
        这些结构由各自的管理逻辑自行维护生命周期。
        """
        # 仅清理闯入计数器（zone violations，不跨检测间隙持久化）
        for zone_key in list(self._intrusion_counter.keys()):
            for tid in list(self._intrusion_counter[zone_key].keys()):
                if tid not in active_ids:
                    del self._intrusion_counter[zone_key][tid]
        # _fall_counter / _person_tracker 由各自逻辑管理
        self._expire_fall_state(time.time())

    def _expire_fall_state(self, now: float, max_age: float = 30.0):
        """清理超过 max_age 秒未出现的摔倒追踪状态，防止内存泄漏。"""
        stale_fall_ids = [
            tid for tid, ts in self._fall_last_seen.items()
            if now - ts > max_age
        ]
        for tid in stale_fall_ids:
            self._fall_counter.pop(tid, None)
            self._fall_last_seen.pop(tid, None)
            self._person_history.pop(tid, None)

    def _detect_fall(
        self, person_boxes: list[dict], stream_id: str
    ) -> list[dict]:
        """检测人员摔倒 — 双路径 + 中心点追踪。

        Path 1 — 标准摔倒（曾站立 → 姿态骤变 → 横向姿态）:
          条件 a: 高宽比 h/w < FALL_ASPECT_RATIO_THRESHOLD（横向）
          条件 b: 曾站立（h/w ≥ FALL_MIN_STANDING_RATIO 持续 ≥ 3 帧）
          条件 c: 骤变确认（AR 变化速率 > 阈值 或 中心点大幅下移）
          持续 FALL_PERSIST_FRAMES 帧后告警。

        Path 2 — 极端姿态（无需曾站立，直接触发）:
          条件: h/w < FALL_EXTREME_AR_THRESHOLD（人几乎平躺）
          持续 FALL_PERSIST_FRAMES 帧后告警。

        蹲下 vs 摔倒区分:
          - 蹲下: h/w ≈ 0.8~1.2, 变化缓慢, 中心点小幅下移 → 递减计数器
          - 摔倒: h/w < 0.9 + 骤变信号, 或 h/w < 0.55 → 告警

        防丢帧: AR 速度计算时 dt 上限 0.5s，避免 YOLO 间歇丢帧稀释速度信号。
        """
        results = []
        now = time.time()

        fall_ar_threshold = _cfg("FALL_ASPECT_RATIO_THRESHOLD")
        fall_extreme_ar = _cfg("FALL_EXTREME_AR_THRESHOLD")
        fall_min_standing = _cfg("FALL_MIN_STANDING_RATIO")
        fall_persist = _cfg("FALL_PERSIST_FRAMES")
        fall_ar_velocity = _cfg("FALL_AR_VELOCITY_THRESHOLD")
        fall_center_drop = _cfg("FALL_CENTER_DROP_RATIO")
        max_standing_reset = _cfg("FALL_MAX_STANDING_FRAMES_TO_RESET")

        active_ids = {box.get("track_id", -1) for box in person_boxes}
        for tid in active_ids:
            if tid >= 0:
                self._fall_last_seen[tid] = now
        self._cleanup_stale_tracks(active_ids)

        # 每 30 帧输出一次诊断摘要
        if not hasattr(self, "_fall_debug_frame"):
            self._fall_debug_frame = 0
        self._fall_debug_frame += 1
        should_log = self._fall_debug_frame % 30 == 0

        if person_boxes and should_log:
            logger.info(
                "[FALL DEBUG] 帧#%d stream=%s boxes=%d counters=%s history=%d",
                self._fall_debug_frame, stream_id, len(person_boxes),
                dict(self._fall_counter) if self._fall_counter else "{}",
                len(self._person_history),
            )

        for box in person_boxes:
            bw, bh = box["w"], box["h"]
            if bw <= 0 or bh <= 0:
                continue

            aspect_ratio = bh / bw  # h/w
            tid = box.get("track_id", -1)
            center_y = box["y"] + bh // 2

            # ---- 初始化 / 获取该人物历史状态 ----
            if tid not in self._person_history:
                self._person_history[tid] = {
                    "prev_ar": aspect_ratio,
                    "prev_cy": center_y,
                    "prev_h": bh,
                    "prev_time": now,
                    "was_standing": False,
                    "standing_frames": 0,
                }

            hist = self._person_history[tid]
            dt = now - hist.get("prev_time", now)
            # 上限 0.5s：YOLO 丢 3-5 帧时不稀释 AR 速度信号
            effective_dt = min(dt, 0.5)

            # ---- 追踪站立历史 ----
            if aspect_ratio >= fall_min_standing:
                hist["standing_frames"] += 1
                if hist["standing_frames"] >= 3:
                    hist["was_standing"] = True
            else:
                hist["standing_frames"] = max(0, hist["standing_frames"] - 1)
                if hist["standing_frames"] <= 0:
                    hist["was_standing"] = False

            # ---- 计算骤变信号 ----
            ar_velocity = 0.0
            if hist["prev_ar"] > 0 and effective_dt > 0.01:
                ar_velocity = (hist["prev_ar"] - aspect_ratio) / effective_dt
            is_rapid_drop = ar_velocity > fall_ar_velocity

            cy_drop = center_y - hist["prev_cy"]
            ref_h = max(bh, hist.get("prev_h", bh))
            center_drop_ratio = cy_drop / ref_h if ref_h > 0 else 0
            is_center_dropped = center_drop_ratio > fall_center_drop

            is_sudden = is_rapid_drop or is_center_dropped
            is_low_ar = aspect_ratio < fall_ar_threshold
            is_extreme = aspect_ratio < fall_extreme_ar
            is_fallen_pose = bw > bh  # 宽大于高 = 横向姿态

            # ---- 判定 ----
            path1 = (
                is_low_ar and is_fallen_pose
                and hist["was_standing"] and is_sudden
            )
            path2 = is_extreme and is_fallen_pose

            if should_log:
                logger.info(
                    "[FALL DEBUG] tid=%d box=%dx%d ar=%.2f dt=%.2fs "
                    "ar_vel=%.2f cy_drop=%.1f%% "
                    "standing=%s(%d) low=%s extreme=%s "
                    "rapid_drop=%s center_dropped=%s "
                    "path1=%s path2=%s counter=%d/%d",
                    tid, bw, bh, aspect_ratio, dt,
                    ar_velocity, center_drop_ratio * 100,
                    hist["was_standing"], hist["standing_frames"],
                    is_low_ar, is_extreme,
                    is_rapid_drop, is_center_dropped,
                    path1, path2,
                    self._fall_counter.get(tid, 0), fall_persist,
                )

            if path1 or path2:
                trigger_path = "extreme_pose" if (path2 and not path1) else "standard"
                self._fall_counter[tid] += 1

                if self._fall_counter[tid] >= fall_persist:
                    if not self._check_cooldown("FALL", stream_id):
                        if should_log:
                            logger.info("[FALL DEBUG] tid=%d 已达阈值但冷却中", tid)
                        # 仍更新历史，避免 dt 累积
                        hist["prev_ar"] = aspect_ratio
                        hist["prev_cy"] = center_y
                        hist["prev_h"] = bh
                        hist["prev_time"] = now
                        continue

                    msg = (
                        f"检测到人员疑似摔倒"
                        f"（高宽比 {aspect_ratio:.2f}, "
                        f"路径 {trigger_path}, "
                        f"AR 速率 {ar_velocity:.1f}/s, "
                        f"中心下移 {center_drop_ratio:.1%}）"
                    )

                    self._create_alert(
                        alert_type="FALL",
                        level="HIGH",
                        stream_id=stream_id,
                        description=msg,
                    )

                    logger.info(
                        "Fall detected [%s] (track=%d): %s",
                        trigger_path, tid, msg,
                    )
                    results.append(
                        {
                            "alert_type": "FALL",
                            "message": msg,
                            "bbox": (box["x"], box["y"], bw, bh),
                            "severity": "high",
                            "detail": {
                                "aspect_ratio": round(aspect_ratio, 2),
                                "track_id": tid,
                                "ar_velocity": round(ar_velocity, 2),
                                "center_drop_ratio": round(center_drop_ratio, 2),
                                "trigger_path": trigger_path,
                            },
                        }
                    )
                    # 告警后重置计数器和历史（避免连续重复告警）
                    self._fall_counter[tid] = 0
                    hist["prev_ar"] = aspect_ratio
                    hist["standing_frames"] = 0
                    hist["was_standing"] = False
            elif is_low_ar and is_fallen_pose and not is_sudden:
                # 低高宽比但变化缓慢 → 蹲下/坐下，递减计数器
                self._fall_counter[tid] = max(0, self._fall_counter[tid] - 1)
            else:
                # 站起来了 → 重置计数器
                if self._fall_counter.get(tid, 0) > 0 and should_log:
                    logger.info(
                        "[FALL DEBUG] tid=%d 恢复直立，计数器 %d→0",
                        tid, self._fall_counter[tid],
                    )
                self._fall_counter[tid] = 0

            # ---- 更新历史 ----
            hist["prev_ar"] = aspect_ratio
            hist["prev_cy"] = center_y
            hist["prev_h"] = bh
            hist["prev_time"] = now

        return results

    # -----------------------------------------------------------------------
    # ★ v1.3 音视频联动集成
    # -----------------------------------------------------------------------

    def _ensure_av_correlation(self):
        """懒初始化音视频联动缓冲器（延迟导入，避免循环依赖）。"""
        if self._av_correlation is None:
            try:
                from .av_correlation import get_av_correlation_buffer

                self._av_correlation = get_av_correlation_buffer()
                logger.info("AVCorrelationBuffer 已关联到 DetectionService")
            except Exception as e:
                logger.warning("音视频联动缓冲器初始化失败: %s", e)

    def _enqueue_video_results(
        self, stream_id: str, results: list[dict]
    ):
        """将视频检测结果入队到音视频联动缓冲器。

        仅入队可能与音频事件联动的告警类型:
          FALL, FIRE, INTRUSION, PROXIMITY
        （LOITER 通常无典型关联声音，不入队以节省缓冲器空间）
        """
        self._ensure_av_correlation()
        if self._av_correlation is None:
            return

        correlatable_types = {"FALL", "FIRE", "INTRUSION", "PROXIMITY"}
        for r in results:
            alert_type = r.get("alert_type", "")
            if alert_type not in correlatable_types:
                continue

            try:
                self._av_correlation.enqueue_video_event(
                    stream_id=stream_id,
                    alert_type=alert_type,
                    confidence=1.0,
                    description=r.get("message", ""),
                )
            except Exception as e:
                logger.debug("视频事件入队联动缓冲器失败: %s", e)

    # -----------------------------------------------------------------------
    # 告警冷却
    # -----------------------------------------------------------------------

    def _check_cooldown(self, alert_type: str, stream_id: str) -> bool:
        """检查告警冷却状态。"""
        now = time.time()
        cooldown_map = _cfg("ALERT_COOLDOWN_SECONDS")
        cooldown_sec = cooldown_map.get(alert_type, 10)
        last = self._cooldown.get(alert_type, {}).get(stream_id, 0)

        if now - last < cooldown_sec:
            return False

        self._cooldown[alert_type][stream_id] = now
        return True

    def _release_cooldown(self, alert_type: str, stream_id: str) -> None:
        """Allow the next frame to retry when alert persistence failed."""
        self._cooldown.get(alert_type, {}).pop(stream_id, None)

    # -----------------------------------------------------------------------
    # 告警写入（对接 dev 分支 alerts 模块）
    # -----------------------------------------------------------------------

    def _create_alert(
        self,
        alert_type: str,
        level: str,
        stream_id: str,
        description: str,
        snapshot_path: str = "",
    ) -> bool:
        """通过 apps.alerts.services.create_alert() 写入告警（同进程直调）。

        告警端点 AlertViewSet 要求 IsAuthenticated + active_household_id，
        同进程 HTTP POST 无 JWT → 401，因此改用 service 函数直调。
        OpenSpec design.md 已注明同进程允许直调 service。

        告警类型：
          - INTRUSION（区域闯入）
          - PROXIMITY（距边缘过近）
          - LOITER（异常停留）
          - FIRE（火情）
          - FALL（人员摔倒）
        """
        if self._current_household_id is None:
            logger.warning(
                "Skipping unscoped %s alert for stream %s; will retry",
                alert_type,
                stream_id,
            )
            return False
        try:
            from apps.alerts.services import create_alert

            create_alert(
                type=alert_type,
                level=level,
                stream_id=stream_id,
                description=description,
                snapshot_path=snapshot_path,
                frame=self._current_snapshot_frame,
                household_id=self._current_household_id,
            )
            return True
        except Exception as e:
            logger.error("通过告警服务写入告警失败: %s", e)
            return False

    # -----------------------------------------------------------------------
    # 标注绘制
    # -----------------------------------------------------------------------

    def draw_overlays(
        self,
        frame: np.ndarray,
        results: list[dict],
        zones: Optional[list[dict]] = None,
        person_boxes: Optional[list[dict]] = None,
    ) -> np.ndarray:
        """在帧上绘制检测结果标注框。

        Args:
            frame: 原始 BGR 帧。
            results: process_frame() 返回的检测结果。
            zones: 危险区域配置。
            person_boxes: 人体框列表。

        Returns:
            标注后的 BGR 帧。
        """
        annotated = frame.copy()
        frame_height, frame_width = annotated.shape[:2]

        if zones:
            for zone in zones:
                polygon = _parse_polygon_for_frame(
                    zone.get("points_json", ""), frame_width, frame_height
                )
                if polygon is not None:
                    cv2.polylines(annotated, [polygon], True, (0, 0, 255), 2)
                    name = zone.get("name", "")
                    if name and len(polygon) > 0:
                        pt = tuple(polygon[0][0])
                        cv2.putText(
                            annotated,
                            f"Zone: {name}",
                            (pt[0], pt[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 0, 255),
                            1,
                        )

        color_map = {
            "INTRUSION": (0, 0, 255),
            "PROXIMITY": (0, 128, 255),
            "LOITER": (255, 128, 0),
            "FIRE": (0, 165, 255),
            "FALL": (0, 255, 255),
        }

        if person_boxes:
            for box in person_boxes:
                x, y, w, h = box["x"], box["y"], box["w"], box["h"]
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (255, 255, 0), 2)
                cv2.putText(
                    annotated,
                    "person",
                    (x, max(20, y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    1,
                )
        for r in results:
            alert_type = r.get("alert_type", "")
            color = color_map.get(alert_type, (0, 255, 0))
            bbox = r.get("bbox")
            if bbox:
                x, y, w, h = bbox
                cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
                cv2.putText(
                    annotated,
                    f"{alert_type}",
                    (x, y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                )

        return annotated


# 全局单例
_detection_service: Optional[DetectionService] = None


def get_detection_service() -> DetectionService:
    """获取全局检测服务实例。"""
    global _detection_service
    if _detection_service is None:
        _detection_service = DetectionService()
    return _detection_service

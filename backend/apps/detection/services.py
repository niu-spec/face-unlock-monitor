"""检测服务模块 — 危险区域与异常检测（Django 版）。

负责：
  - 危险区域闯入 / 距边缘过近 / 异常停留检测（YOLO 行人检测 + IoU 追踪 + 多边形碰撞）
  - 积水检测（镜面反射 + 边缘纹理分析 + 颜色辅助，三信号融合）
  - 着火检测（三区间 HSV + 亮度 + 连通域滤波）
  - 摔倒检测（IoU 跨帧追踪 + 状态持久化 + 双路径判定；容忍 YOLO 横向人体间歇丢帧）
  - 异常声学事件检测（PANNs CNN14 音频分类）★ v1.3 新增
  - 音视频联动告警（AVCorrelationBuffer）★ v1.3 新增

由团队成员 D（李东礼）负责实现和维护。

告警通过 apps.alerts.services.create_alert() 写入（同进程直调，避免 HTTP POST
被 AlertViewSet 的 IsAuthenticated 拦截，OpenSpec design.md 已注明同进程允许直调）。

行人检测：优先使用 YOLOv8n，若不可用则自动降级为 HOG。
音频检测：从 RTSP 流提取音频，PANNs CNN14 分类，RTSP 无音频轨道时自动降级。
"""

import json
import time
import logging
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
    # --- 积水（WATER）---
    # 室内地板积水的多信号融合检测：
    #   Signal A — 镜面反射：湿滑地板产生亮斑（低饱和 + 高亮度）
    #   Signal B — 纹理抑制：水面平滑，边缘密度显著低于干燥地面
    #   Signal C — 蓝/青色液体（洗涤剂、泳池水等有色溢水）
    "FLOOD_ROI_BOTTOM_RATIO": 0.55,
    # Signal A: 镜面反射检测
    "FLOOD_REFLECT_V_LOWER": 160,       # 高亮度阈值
    "FLOOD_REFLECT_S_UPPER": 80,        # 低饱和度上限（反光区域色彩淡）
    "FLOOD_REFLECT_AREA_THRESHOLD": 0.06,
    # Signal B: 边缘/纹理稀疏检测
    "FLOOD_EDGE_CANNY_LOW": 40,
    "FLOOD_EDGE_CANNY_HIGH": 120,
    "FLOOD_EDGE_SPARSITY_THRESHOLD": 0.65,  # 边缘像素占比低于此值视为平滑
    # Signal C: 蓝/青色液体（保留原有逻辑作为辅助）
    "FLOOD_HSV_LOWER": (85, 40, 40),
    "FLOOD_HSV_UPPER": (145, 255, 255),
    "FLOOD_COLOR_AREA_THRESHOLD": 0.10,
    # 综合判定：至少满足 (A + B) 或 C 才触发告警
    # --- 着火（FIRE）---
    # 火焰颜色范围：三个 HSV 区间覆盖明焰、暗焰与红热区域
    # Range 1: 红/橙/黄明焰（低饱和也能捕获，避免过滤暗火）
    "FIRE_HSV_LOWER_1": (0, 55, 80),
    "FIRE_HSV_UPPER_1": (35, 255, 255),
    # Range 2: 深红/品红区域
    "FIRE_HSV_LOWER_2": (155, 55, 80),
    "FIRE_HSV_UPPER_2": (180, 255, 255),
    # Range 3: 黄/白热焰（高亮高温核心）
    "FIRE_HSV_LOWER_3": (18, 20, 200),
    "FIRE_HSV_UPPER_3": (38, 120, 255),
    # 亮度阈值（大幅降低，捕获焰体而非仅核心））
    "FIRE_BRIGHTNESS_THRESHOLD": 130,
    # 面积阈值（降低以检测初起小火）
    "FIRE_AREA_THRESHOLD": 0.02,
    # 火焰区域最小连通域（过滤噪声）
    "FIRE_MIN_CONTOUR_AREA": 80,
    # --- 摔倒（FALL）---
    # 极简策略：人体框宽大于高 = 横向姿态 = 疑似摔倒。
    # 连续 N 帧确认后告警，无需曾站立/速度/位移等前置条件。
    "FALL_PERSIST_FRAMES": 3,                  # 横向姿态持续帧数
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
    "INTRUSION_PERSIST_FRAMES": 3,
    # --- 告警冷却（秒）---
    "ALERT_COOLDOWN_SECONDS": {
        "WATER": 30,
        "FIRE": 30,
        "FALL": 15,
        "INTRUSION": 10,
        "PROXIMITY": 10,
        "LOITER": 15,
        # 音频告警冷却 ★ v1.3
        "SCREAM": 15,
        "FIGHT": 20,
        "CRYING": 20,
        "GLASS_BREAK": 10,
        "ABNORMAL_SOUND": 30,
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

        # 2. 积水检测
        results.extend(self._detect_water(frame, stream_id))

        # 3. 着火检测
        results.extend(self._detect_fire(frame, stream_id))

        # 4. 摔倒检测
        results.extend(self._detect_fall(person_boxes, stream_id))

        # ★ v1.3 视频检测事件入队音视频联动缓冲器
        if results:
            self._enqueue_video_results(
                stream_id=stream_id, results=results
            )

        self._current_snapshot_frame = None
        self._current_household_id = None
        return results

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
        """检测危险区域闯入、距边缘过近与异常停留（闯入需持续 N 帧防误报）。"""
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
            if not forbidden:
                continue

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
                if role not in forbidden:
                    self._intrusion_counter[zone_key][tid] = 0
                    continue

                # 脚部（底部中心）用于判断人是否站在区域内
                foot_x = box["x"] + box["w"] // 2
                foot_y = box["y"] + box["h"]
                foot_dist = _distance_point_to_polygon((foot_x, foot_y), polygon)
                foot_inside = foot_dist > 0

                cx, cy = _rect_center(box["x"], box["y"], box["w"], box["h"])
                signed_dist = _distance_point_to_polygon((cx, cy), polygon)
                inside = foot_inside or signed_dist > 0
                bbox = (box["x"], box["y"], box["w"], box["h"])

                if inside:
                    # 闯入：需持续 N 帧才触发告警（防误报）
                    self._intrusion_counter[zone_key][tid] += 1

                    if self._intrusion_counter[zone_key][tid] >= persist:
                        if self._check_cooldown("INTRUSION", stream_id):
                            msg = f"[{zone_name}] 检测到 {role} 闯入禁区"
                            self._create_alert(
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
                            self._intrusion_counter[zone_key][tid] = 0
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
    # 2. 积水检测（WATER）
    # -----------------------------------------------------------------------

    def _detect_water(self, frame: np.ndarray, stream_id: str) -> list[dict]:
        """检测画面下方积水（多信号融合）。

        室内地面积水通常表现为：
          - 镜面反射（Signal A）：湿滑地面产生亮斑
          - 纹理抑制（Signal B）：水面平滑，边缘密度低
          - 有色液体（Signal C）：蓝/青色溢水（洗涤剂等）

        判定规则：满足 (A + B) 或 C 任一组合即触发告警。
        """
        h, w = frame.shape[:2]
        roi_y_start = int(h * _cfg("FLOOD_ROI_BOTTOM_RATIO"))
        roi = frame[roi_y_start:h, 0:w]
        roi_h, roi_w = roi.shape[:2]
        roi_area = roi_h * roi_w

        if roi_area <= 0:
            return []

        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # ---- Signal A: 镜面反射检测 ----
        # 湿地板 = 高亮度 + 低饱和（反光区域色彩被冲刷）
        s_channel = hsv_roi[:, :, 1]
        v_channel = hsv_roi[:, :, 2]
        refl_mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
        refl_mask[
            (v_channel >= _cfg("FLOOD_REFLECT_V_LOWER"))
            & (s_channel <= _cfg("FLOOD_REFLECT_S_UPPER"))
        ] = 255

        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        refl_mask = cv2.morphologyEx(refl_mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
        refl_mask = cv2.morphologyEx(refl_mask, cv2.MORPH_CLOSE, kernel_small, iterations=2)

        refl_area = cv2.countNonZero(refl_mask)
        refl_ratio = refl_area / roi_area

        # ---- Signal B: 边缘/纹理稀疏检测 ----
        # 水面平滑，Canny 边缘密度显著低于正常地板纹理
        blurred = cv2.GaussianBlur(gray_roi, (5, 5), 0)
        edges = cv2.Canny(
            blurred,
            _cfg("FLOOD_EDGE_CANNY_LOW"),
            _cfg("FLOOD_EDGE_CANNY_HIGH"),
        )
        edge_pixels = cv2.countNonZero(edges)
        edge_ratio = edge_pixels / roi_area
        is_texture_sparse = edge_ratio < (1.0 - _cfg("FLOOD_EDGE_SPARSITY_THRESHOLD"))
        # 计算边缘密度（1 - 归一化边缘比），高值 = 纹理少 = 可能积水
        edge_sparsity = 1.0 - min(1.0, edge_ratio * 3)  # 放大敏感度

        # ---- Signal C: 蓝/青色液体检测（保留原逻辑）----
        color_mask = cv2.inRange(
            hsv_roi,
            np.array(_cfg("FLOOD_HSV_LOWER")),
            np.array(_cfg("FLOOD_HSV_UPPER")),
        )
        kernel_med = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, kernel_med, iterations=2)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel_med, iterations=2)
        color_area = cv2.countNonZero(color_mask)
        color_ratio = color_area / roi_area

        # ---- 组合判定 ----
        signal_ab = (
            refl_ratio >= _cfg("FLOOD_REFLECT_AREA_THRESHOLD")
            and edge_sparsity >= _cfg("FLOOD_EDGE_SPARSITY_THRESHOLD")
        )
        signal_c = color_ratio >= _cfg("FLOOD_COLOR_AREA_THRESHOLD")

        if not (signal_ab or signal_c):
            return []

        if not self._check_cooldown("WATER", stream_id):
            return []

        # 确定主要检测信号（用于日志）
        if signal_ab and signal_c:
            source = "reflection+texture+color"
        elif signal_ab:
            source = "reflection+texture"
        else:
            source = "color"

        msg = (
            f"检测到疑似积水区域"
            f"（信号源: {source}, "
            f"反光 {refl_ratio:.1%}, "
            f"纹理稀疏度 {edge_sparsity:.1%}, "
            f"颜色 {color_ratio:.1%}）"
        )

        self._create_alert(
            alert_type="WATER",
            level="HIGH",
            stream_id=stream_id,
            description=msg,
        )

        logger.info("Water detected (%s): %s", source, msg)
        return [
            {
                "alert_type": "WATER",
                "message": msg,
                "bbox": (0, roi_y_start, w, h - roi_y_start),
                "severity": "high",
                "detail": {
                    "source": source,
                    "reflection_ratio": round(refl_ratio, 3),
                    "edge_sparsity": round(edge_sparsity, 3),
                    "color_ratio": round(color_ratio, 3),
                },
            }
        ]

    # -----------------------------------------------------------------------
    # 3. 着火检测（FIRE）
    # -----------------------------------------------------------------------

    def _detect_fire(self, frame: np.ndarray, stream_id: str) -> list[dict]:
        """检测画面中火焰区域（三区间 HSV + 亮度 + 形态滤波）。

        改进要点：
          1. 三区间 HSV 覆盖明焰、暗焰、高温白热核心
          2. 降低饱和度下限（100→55）捕获暗火
          3. 降低亮度阈值（180→130）捕获焰体而非仅核心
          4. 面积阈值从 5% → 2%，可检测初起小火
          5. 形态滤波过滤零星噪点
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, w = frame.shape[:2]
        frame_area = h * w

        # 三区间火焰颜色掩码
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
        color_mask = cv2.bitwise_or(mask1, mask2)
        color_mask = cv2.bitwise_or(color_mask, mask3)

        # 亮度掩码（明度通道独立阈值）
        v_channel = hsv[:, :, 2]
        _, bright_mask = cv2.threshold(
            v_channel, _cfg("FIRE_BRIGHTNESS_THRESHOLD"), 255, cv2.THRESH_BINARY
        )
        mask = cv2.bitwise_and(color_mask, bright_mask)

        # 形态滤波：先去噪再连接断裂区域
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)

        # 过滤小面积噪点
        min_contour_area = _cfg("FIRE_MIN_CONTOUR_AREA")
        num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(
            mask, connectivity=8
        )
        clean_mask = np.zeros_like(mask)
        for label_id in range(1, num_labels):
            area = stats[label_id, cv2.CC_STAT_AREA]
            if area >= min_contour_area:
                clean_mask[labels == label_id] = 255
        mask = clean_mask

        fire_area = cv2.countNonZero(mask)
        ratio = fire_area / frame_area if frame_area > 0 else 0

        if ratio >= _cfg("FIRE_AREA_THRESHOLD"):
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
    # 4. 摔倒检测（FALL）
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

    def _detect_fall(
        self, person_boxes: list[dict], stream_id: str
    ) -> list[dict]:
        """检测人员摔倒 — 极简策略。

        判定：人体框宽大于高（横向姿态）连续 FALL_PERSIST_FRAMES 帧 → 告警。
        无前置条件（不要求曾站立/速度/位移），蹲下（近似方形）不会触发。
        """
        results = []
        now = time.time()
        fall_persist = _cfg("FALL_PERSIST_FRAMES")

        active_ids = {box.get("track_id", -1) for box in person_boxes}
        for tid in active_ids:
            if tid >= 0:
                self._fall_last_seen[tid] = now
        self._cleanup_stale_tracks(active_ids)

        for box in person_boxes:
            bw, bh = box["w"], box["h"]
            if bw <= 0 or bh <= 0:
                continue

            tid = box.get("track_id", -1)
            is_horizontal = bw > bh  # 宽 > 高 = 横向姿态

            if is_horizontal:
                self._fall_counter[tid] += 1

                if self._fall_counter[tid] >= fall_persist:
                    if not self._check_cooldown("FALL", stream_id):
                        continue

                    msg = f"检测到人员疑似摔倒（宽高比 {bh / bw:.2f}，连续 {fall_persist} 帧）"

                    self._create_alert(
                        alert_type="FALL",
                        level="HIGH",
                        stream_id=stream_id,
                        description=msg,
                    )

                    logger.info("Fall detected (track=%d): %s", tid, msg)
                    results.append(
                        {
                            "alert_type": "FALL",
                            "message": msg,
                            "bbox": (box["x"], box["y"], bw, bh),
                            "severity": "high",
                            "detail": {
                                "aspect_ratio": round(bh / bw, 2),
                                "track_id": tid,
                            },
                        }
                    )
                    self._fall_counter[tid] = 0
            else:
                # 直立或蹲姿 → 重置计数器
                self._fall_counter[tid] = 0

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
        （WATER / LOITER 通常无典型关联声音，不入队以节省缓冲器空间）
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
    ):
        """通过 apps.alerts.services.create_alert() 写入告警（同进程直调）。

        告警端点 AlertViewSet 要求 IsAuthenticated + active_household_id，
        同进程 HTTP POST 无 JWT → 401，因此改用 service 函数直调。
        OpenSpec design.md 已注明同进程允许直调 service。

        告警类型：
          - INTRUSION（区域闯入）
          - PROXIMITY（距边缘过近）
          - LOITER（异常停留）
          - WATER（积水）
          - FIRE（火情）
          - FALL（人员摔倒）
        """
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
        except Exception as e:
            logger.error("通过告警服务写入告警失败: %s", e)

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
            "WATER": (255, 0, 0),
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

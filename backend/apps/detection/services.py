"""检测服务模块 — 危险区域与异常检测（Django 版）。

负责：
  - 危险区域闯入 / 距边缘过近 / 异常停留检测（YOLO 行人检测 + 多边形碰撞）
  - 积水检测（HSV 颜色 + 形态分析）
  - 着火检测（HSV 火焰颜色 + 亮度分析）
  - 摔倒检测（人体框高宽比分析）

由团队成员 D（李东礼）负责实现和维护。

告警通过 apps.alerts.services.create_alert() 写入（同进程直调，避免 HTTP POST
被 AlertViewSet 的 IsAuthenticated 拦截，OpenSpec design.md 已注明同进程允许直调）。

行人检测：优先使用 YOLOv8n，若不可用则自动降级为 HOG。
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
    "FLOOD_ROI_BOTTOM_RATIO": 0.6,
    "FLOOD_HSV_LOWER": (90, 50, 50),
    "FLOOD_HSV_UPPER": (140, 255, 255),
    "FLOOD_AREA_THRESHOLD": 0.15,
    # --- 着火（FIRE）---
    "FIRE_HSV_LOWER_1": (0, 100, 100),
    "FIRE_HSV_UPPER_1": (25, 255, 255),
    "FIRE_HSV_LOWER_2": (160, 100, 100),
    "FIRE_HSV_UPPER_2": (180, 255, 255),
    "FIRE_AREA_THRESHOLD": 0.05,
    "FIRE_BRIGHTNESS_THRESHOLD": 180,
    # --- 摔倒（FALL）---
    "FALL_ASPECT_RATIO_THRESHOLD": 1.3,
    "FALL_PERSIST_FRAMES": 5,
    # --- YOLO 行人检测（优先）---
    "YOLO_MODEL": "yolov8n.pt",
    "YOLO_CONFIDENCE_THRESHOLD": 0.5,
    "YOLO_IOU_THRESHOLD": 0.45,
    "YOLO_PERSON_CLASS_ID": 0,
    # --- HOG 行人检测（YOLO 不可用时降级）---
    "HOG_WIN_STRIDE": (4, 4),
    "HOG_PADDING": (8, 8),
    "HOG_SCALE": 1.05,
    "HOG_CONFIDENCE_THRESHOLD": 0.5,
    # --- 告警冷却（秒）---
    "ALERT_COOLDOWN_SECONDS": {
        "WATER": 30,
        "FIRE": 30,
        "FALL": 15,
        "INTRUSION": 10,
        "PROXIMITY": 10,
        "LOITER": 15,
    },
}


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


def _is_point_in_polygon(point: tuple, polygon: np.ndarray) -> bool:
    """判断点是否在多边形内部。"""
    return cv2.pointPolygonTest(polygon, point, False) >= 0


def _is_rect_in_polygon(
    x: int, y: int, w: int, h: int, polygon: np.ndarray
) -> bool:
    """判断矩形框中心点是否在多边形内部。"""
    cx, cy = x + w // 2, y + h // 2
    return _is_point_in_polygon((cx, cy), polygon)


def _rect_center(x: int, y: int, w: int, h: int) -> tuple[int, int]:
    return x + w // 2, y + h // 2


def _distance_point_to_polygon(point: tuple[int, int], polygon: np.ndarray) -> float:
    """点到多边形轮廓的有符号距离：内部为负，外部为正，边界为 0。"""
    return float(cv2.pointPolygonTest(polygon, point, True))


def _normalize_forbidden_roles(forbidden) -> list[str]:
    if isinstance(forbidden, str):
        return [r.strip() for r in forbidden.split(",") if r.strip()]
    if isinstance(forbidden, list):
        return [str(r).strip() for r in forbidden if str(r).strip()]
    return []


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
        self._loiter_since: dict[tuple[int, int], float] = {}
        self._current_snapshot_frame = None

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

        # 内部行人检测（若调用方未提供 person_boxes）
        if person_boxes is None:
            person_boxes = self._detect_pedestrians(frame)

        # 1. 危险区域：闯入 / 距边缘过近 / 异常停留
        if zones:
            results.extend(
                self._detect_zone_violations(
                    stream_id, zones, person_boxes, face_roles or {}
                )
            )

        # 2. 积水检测
        results.extend(self._detect_water(frame, stream_id))

        # 3. 着火检测
        results.extend(self._detect_fire(frame, stream_id))

        # 4. 摔倒检测
        results.extend(self._detect_fall(person_boxes, stream_id))

        self._current_snapshot_frame = None
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
        """YOLO 行人检测，不可用时自动降级为 HOG。"""
        if self._detector_type == "YOLO" and self._yolo is not None:
            return self._detect_pedestrians_yolo(frame)
        return self._detect_pedestrians_hog(frame)

    def _detect_pedestrians_yolo(self, frame: np.ndarray) -> list[dict]:
        """使用 YOLOv8n 检测行人（class_id=0 即 person）。"""
        results = self._yolo(
            frame,
            conf=_cfg("YOLO_CONFIDENCE_THRESHOLD"),
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
        """使用 HOG 检测器检测行人（降级方案）。"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects, weights = self._hog.detectMultiScale(
            gray,
            winStride=_cfg("HOG_WIN_STRIDE"),
            padding=_cfg("HOG_PADDING"),
            scale=_cfg("HOG_SCALE"),
        )

        boxes = []
        threshold = _cfg("HOG_CONFIDENCE_THRESHOLD")
        for i, (x, y, w, h) in enumerate(rects):
            if weights[i] >= threshold:
                boxes.append(
                    {
                        "x": int(x),
                        "y": int(y),
                        "w": int(w),
                        "h": int(h),
                        "track_id": i,
                    }
                )
        return boxes

    # -----------------------------------------------------------------------
    # 1. 危险区域检测（INTRUSION / PROXIMITY / LOITER）
    # -----------------------------------------------------------------------

    def _detect_zone_violations(
        self,
        stream_id: str,
        zones: list[dict],
        person_boxes: list[dict],
        face_roles: dict[int, str],
    ) -> list[dict]:
        """检测危险区域闯入、距边缘过近与异常停留。"""
        results: list[dict] = []
        active_loiter_keys: set[tuple[int, int]] = set()
        now = time.time()

        for zone in zones:
            if not zone.get("is_active", zone.get("enabled", True)):
                continue

            polygon = _parse_polygon(zone.get("points_json", ""))
            if polygon is None:
                continue

            forbidden = _normalize_forbidden_roles(zone.get("forbidden_roles", []))
            if not forbidden:
                continue

            zone_id = zone.get("id", 0)
            zone_name = zone.get("name", "危险区域")
            safe_distance = max(0, int(zone.get("safe_distance") or 50))
            dwell_time = max(1, int(zone.get("dwell_time") or 5))

            for box in person_boxes:
                tid = box.get("track_id", -1)
                role = face_roles.get(tid, "stranger")
                if role not in forbidden:
                    continue

                cx, cy = _rect_center(box["x"], box["y"], box["w"], box["h"])
                signed_dist = _distance_point_to_polygon((cx, cy), polygon)
                inside = signed_dist < 0
                bbox = (box["x"], box["y"], box["w"], box["h"])

                if inside:
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
                elif 0 < signed_dist < safe_distance:
                    if self._check_cooldown("PROXIMITY", f"{stream_id}:{zone_id}"):
                        msg = (
                            f"[{zone_name}] {role} 距禁区边缘过近"
                            f"（{signed_dist:.0f}px < {safe_distance}px）"
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
                                    "distance_px": round(signed_dist, 1),
                                    "safe_distance_px": safe_distance,
                                },
                            }
                        )
                        logger.info("Zone proximity: %s", msg)

                in_loiter_area = inside or (
                    signed_dist >= 0 and signed_dist < safe_distance
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
        """检测画面下方积水。

        dev 分支告警类型: WATER（对应 Flask 版的 FLOOD）。
        """
        h, w = frame.shape[:2]
        roi_y_start = int(h * _cfg("FLOOD_ROI_BOTTOM_RATIO"))
        roi = frame[roi_y_start:h, 0:w]

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(_cfg("FLOOD_HSV_LOWER")),
            np.array(_cfg("FLOOD_HSV_UPPER")),
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        roi_area = roi.shape[0] * roi.shape[1]
        water_area = cv2.countNonZero(mask)
        ratio = water_area / roi_area if roi_area > 0 else 0

        if ratio >= _cfg("FLOOD_AREA_THRESHOLD"):
            if not self._check_cooldown("WATER", stream_id):
                return []

            msg = f"检测到疑似积水区域（占比 {ratio:.1%}）"

            self._create_alert(
                alert_type="WATER",
                level="HIGH",
                stream_id=stream_id,
                description=msg,
            )

            logger.info("Water detected: %s", msg)
            return [
                {
                    "alert_type": "WATER",
                    "message": msg,
                    "bbox": (0, roi_y_start, w, h - roi_y_start),
                    "severity": "high",
                    "detail": {"area_ratio": round(ratio, 3)},
                }
            ]

        return []

    # -----------------------------------------------------------------------
    # 3. 着火检测（FIRE）
    # -----------------------------------------------------------------------

    def _detect_fire(self, frame: np.ndarray, stream_id: str) -> list[dict]:
        """检测画面中火焰区域。"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

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
        mask = cv2.bitwise_or(mask1, mask2)

        v_channel = hsv[:, :, 2]
        _, bright_mask = cv2.threshold(
            v_channel, _cfg("FIRE_BRIGHTNESS_THRESHOLD"), 255, cv2.THRESH_BINARY
        )
        mask = cv2.bitwise_and(mask, bright_mask)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        frame_area = frame.shape[0] * frame.shape[1]
        fire_area = cv2.countNonZero(mask)
        ratio = fire_area / frame_area if frame_area > 0 else 0

        if ratio >= _cfg("FIRE_AREA_THRESHOLD"):
            if not self._check_cooldown("FIRE", stream_id):
                return []

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours:
                x, y, fw, fh = cv2.boundingRect(
                    max(contours, key=cv2.contourArea)
                )
            else:
                x, y, fw, fh = 0, 0, frame.shape[1], frame.shape[0]

            msg = f"检测到疑似火焰区域（占比 {ratio:.1%}）"

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
                    "detail": {"area_ratio": round(ratio, 3)},
                }
            ]

        return []

    # -----------------------------------------------------------------------
    # 4. 摔倒检测（FALL）
    # -----------------------------------------------------------------------

    def _detect_fall(
        self, person_boxes: list[dict], stream_id: str
    ) -> list[dict]:
        """检测人员摔倒。"""
        results = []

        for box in person_boxes:
            w, h = box["w"], box["h"]
            if w <= 0:
                continue

            aspect_ratio = h / w
            tid = box.get("track_id", -1)

            if aspect_ratio < _cfg("FALL_ASPECT_RATIO_THRESHOLD"):
                self._fall_counter[tid] += 1

                if self._fall_counter[tid] >= _cfg("FALL_PERSIST_FRAMES"):
                    if not self._check_cooldown("FALL", stream_id):
                        continue

                    msg = f"检测到人员疑似摔倒（高宽比 {aspect_ratio:.2f}）"

                    self._create_alert(
                        alert_type="FALL",
                        level="HIGH",
                        stream_id=stream_id,
                        description=msg,
                    )

                    logger.info("Fall detected: %s", msg)
                    results.append(
                        {
                            "alert_type": "FALL",
                            "message": msg,
                            "bbox": (box["x"], box["y"], w, h),
                            "severity": "high",
                            "detail": {
                                "aspect_ratio": round(aspect_ratio, 2),
                                "track_id": tid,
                            },
                        }
                    )
                    self._fall_counter[tid] = 0
            else:
                self._fall_counter[tid] = 0

        return results

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

        if zones:
            for zone in zones:
                polygon = _parse_polygon(zone.get("points_json", ""))
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
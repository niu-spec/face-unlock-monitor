"""检测服务模块 — 危险区域与异常检测（Django 版）。

负责：
  - 危险区域闯入检测（HOG 行人检测 + 多边形碰撞）
  - 积水检测（HSV 颜色 + 形态分析）
  - 着火检测（HSV 火焰颜色 + 亮度分析）
  - 摔倒检测（人体框高宽比分析）

由团队成员 D（李东礼）负责实现和维护。

告警通过 apps.alerts.services.create_alert() 写入数据库，
与 dev 分支的告警模块（刘帅华）对接。
"""

import json
import time
import logging
from collections import defaultdict
from typing import Any, Optional

import cv2
import numpy as np

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
    # --- HOG 行人检测 ---
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
        """初始化 HOG 行人检测器及告警冷却计时器。"""
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self._cooldown: dict[str, dict[str, float]] = defaultdict(dict)
        self._fall_counter: dict[int, int] = defaultdict(int)

        logger.info("DetectionService initialized (Django + HOG + HSV)")

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
    ) -> list[dict]:
        """处理单帧画面，执行全部检测逻辑。

        Args:
            frame: BGR 格式的 numpy 图像数组 (H, W, 3)。
            stream_id: 摄像头流 ID（如 "living_room"）。
            person_boxes: 已检测的人体框列表，
                [{'x', 'y', 'w', 'h', 'track_id'}, ...]。
                若为 None，则内部使用 HOG 自行检测。
            face_roles: 人脸识别结果，{track_id: role}，
                role 为 'adult' / 'child' / 'stranger'。
            zones: 危险区域配置列表，每项含
                {'id', 'name', 'points_json', 'forbidden_roles'}。

        Returns:
            detection_results: 检测结果列表。
        """
        results: list[dict] = []

        if frame is None or frame.size == 0:
            return results

        # 内部行人检测（若调用方未提供 person_boxes）
        if person_boxes is None:
            person_boxes = self._detect_pedestrians(frame)

        # 1. 危险区域闯入检测
        if zones:
            results.extend(
                self._detect_zone_intrusion(
                    frame, stream_id, zones, person_boxes, face_roles or {}
                )
            )

        # 2. 积水检测
        results.extend(self._detect_water(frame, stream_id))

        # 3. 着火检测
        results.extend(self._detect_fire(frame, stream_id))

        # 4. 摔倒检测
        results.extend(self._detect_fall(person_boxes, stream_id))

        return results

    # -----------------------------------------------------------------------
    # 行人检测（HOG）
    # -----------------------------------------------------------------------

    def _detect_pedestrians(self, frame: np.ndarray) -> list[dict]:
        """使用 HOG 检测器检测行人。"""
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
    # 1. 危险区域闯入检测（INTRUSION）
    # -----------------------------------------------------------------------

    def _detect_zone_intrusion(
        self,
        frame: np.ndarray,
        stream_id: str,
        zones: list[dict],
        person_boxes: list[dict],
        face_roles: dict[int, str],
    ) -> list[dict]:
        """检测危险区域闯入。

        dev 分支告警类型: INTRUSION（对应 Flask 版的 ZONE_INTRUSION）。
        """
        results = []

        for zone in zones:
            if not zone.get("is_active", zone.get("enabled", True)):
                continue

            polygon = _parse_polygon(zone.get("points_json", ""))
            if polygon is None:
                continue

            forbidden = zone.get("forbidden_roles", [])
            if isinstance(forbidden, str):
                forbidden = [r.strip() for r in forbidden.split(",") if r.strip()]

            for box in person_boxes:
                tid = box.get("track_id", -1)
                role = face_roles.get(tid, "stranger")

                if role not in forbidden:
                    continue

                if _is_rect_in_polygon(
                    box["x"], box["y"], box["w"], box["h"], polygon
                ):
                    if not self._check_cooldown("INTRUSION", stream_id):
                        continue

                    zone_name = zone.get("name", "危险区域")
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
                            "bbox": (box["x"], box["y"], box["w"], box["h"]),
                            "severity": "high",
                            "zone_id": zone.get("id"),
                            "zone_name": zone_name,
                        }
                    )
                    logger.info("Zone intrusion: %s", msg)

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
        """通过 apps.alerts.services.create_alert() 写入告警。

        与 dev 分支刘帅华的告警模块对接，告警类型使用 dev 分支的命名：
          - INTRUSION（区域闯入）
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
            )
        except Exception as e:
            logger.error("Failed to create alert via service: %s", e)

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
            "WATER": (255, 0, 0),
            "FIRE": (0, 165, 255),
            "FALL": (0, 255, 255),
        }

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
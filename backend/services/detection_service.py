"""检测服务模块 — 危险区域与异常检测。

负责：
  - 危险区域闯入检测（HOG 行人检测 + 多边形碰撞）
  - 积水检测（HSV 颜色 + 形态分析）
  - 着火检测（HSV 火焰颜色 + 亮度分析）
  - 摔倒检测（人体框高宽比分析）

由团队成员 D（李东礼）负责实现和维护。
"""

import json
import time
import logging
from collections import defaultdict
from typing import Any, Optional

import cv2
import numpy as np

from config import Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _parse_polygon(points_json: str) -> Optional[np.ndarray]:
    """将 JSON 多边形坐标解析为 (N, 1, 2) 格式的 numpy 数组。

    Args:
        points_json: JSON 字符串，如 '[[x1,y1],[x2,y2],...]'。

    Returns:
        numpy 数组或 None（解析失败时）。
    """
    try:
        pts = json.loads(points_json)
        if not pts or len(pts) < 3:
            return None
        return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Failed to parse polygon points: %s", points_json)
        return None


def _is_point_in_polygon(point: tuple, polygon: np.ndarray) -> bool:
    """判断点是否在多边形内部。

    Args:
        point: (x, y) 坐标。
        polygon: cv2 格式的多边形数组。

    Returns:
        True 表示点在多边形内部。
    """
    return cv2.pointPolygonTest(polygon, point, False) >= 0


def _is_rect_in_polygon(
    x: int, y: int, w: int, h: int, polygon: np.ndarray
) -> bool:
    """判断矩形框是否与多边形有交集（以矩形中心点判断）。

    Args:
        x, y: 矩形左上角坐标。
        w, h: 矩形宽高。
        polygon: cv2 格式的多边形。

    Returns:
        True 表示矩形中心在多边形内部。
    """
    cx, cy = x + w // 2, y + h // 2
    return _is_point_in_polygon((cx, cy), polygon)


# ---------------------------------------------------------------------------
# 检测服务主类
# ---------------------------------------------------------------------------


class DetectionService:
    """危险区域与异常检测服务。

    在视频处理流水线中，每 N 帧调用一次 process_frame()，
    返回检测结果列表，供调用方（如 video.py）标注和告警。

    Usage:
        service = DetectionService()
        results = service.process_frame(frame, stream_id, person_boxes, face_roles)
        # results: List[dict] 包含告警类型和位置信息
    """

    def __init__(self):
        """初始化 HOG 行人检测器及告警冷却计时器。"""
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # 告警冷却：{alert_type: {stream_id: last_alert_time}}
        self._cooldown: dict[str, dict[str, float]] = defaultdict(dict)

        # 摔倒持续帧计数器：{track_id: consecutive_fall_count}
        self._fall_counter: dict[int, int] = defaultdict(int)

        logger.info("DetectionService initialized (HOG + HSV analysis)")

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
            stream_id: 摄像头流 ID。
            person_boxes: 已检测到的人体框列表，每项含
                {'x', 'y', 'w', 'h', 'track_id'}。
                若为 None，则内部使用 HOG 自行检测。
            face_roles: 人脸识别结果，{track_id: role}，
                role 为 'adult' / 'child' / 'stranger'。
            zones: 危险区域配置列表，每项含
                {'id', 'name', 'points_json', 'forbidden_roles'}。

        Returns:
            detection_results: 检测结果列表，每项为：
                {
                    'alert_type': str,      # ZONE_INTRUSION / FLOOD / FIRE / FALL
                    'message': str,         # 告警描述
                    'bbox': (x, y, w, h),  # 关联区域框（可选）
                    'severity': str,        # high / medium
                }
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
        results.extend(self._detect_flood(frame, stream_id))

        # 3. 着火检测
        results.extend(self._detect_fire(frame, stream_id))

        # 4. 摔倒检测
        results.extend(self._detect_fall(person_boxes, stream_id))

        return results

    # -----------------------------------------------------------------------
    # 行人检测（HOG）
    # -----------------------------------------------------------------------

    def _detect_pedestrians(self, frame: np.ndarray) -> list[dict]:
        """使用 HOG 检测器检测行人。

        Args:
            frame: BGR 图像。

        Returns:
            人体框列表 [{'x', 'y', 'w', 'h', 'track_id'}, ...]。
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects, weights = self._hog.detectMultiScale(
            gray,
            winStride=Config.HOG_WIN_STRIDE,
            padding=Config.HOG_PADDING,
            scale=Config.HOG_SCALE,
        )

        boxes = []
        for i, (x, y, w, h) in enumerate(rects):
            if weights[i] >= Config.HOG_CONFIDENCE_THRESHOLD:
                boxes.append(
                    {"x": int(x), "y": int(y), "w": int(w), "h": int(h), "track_id": i}
                )
        return boxes

    # -----------------------------------------------------------------------
    # 1. 危险区域闯入检测
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

        对每个启用的危险区域，检查是否有行人进入，
        且该行人的角色属于 forbidden_roles。

        Args:
            frame: 当前帧（用于绘制标注，可选）。
            stream_id: 摄像头流 ID。
            zones: 危险区域配置列表。
            person_boxes: 人体框列表。
            face_roles: {track_id: role}。

        Returns:
            闯入告警结果列表。
        """
        results = []

        for zone in zones:
            if not zone.get("enabled", True):
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

                # 仅当角色属于禁止角色时触发
                if role not in forbidden:
                    continue

                if _is_rect_in_polygon(
                    box["x"], box["y"], box["w"], box["h"], polygon
                ):
                    if not self._check_cooldown("ZONE_INTRUSION", stream_id):
                        continue

                    msg = (
                        f"[{zone.get('name', '危险区域')}] "
                        f"检测到 {role} 闯入禁区"
                    )
                    results.append(
                        {
                            "alert_type": "ZONE_INTRUSION",
                            "message": msg,
                            "bbox": (box["x"], box["y"], box["w"], box["h"]),
                            "severity": "high",
                            "zone_id": zone.get("id"),
                            "zone_name": zone.get("name"),
                        }
                    )
                    logger.info("Zone intrusion: %s", msg)

        return results

    # -----------------------------------------------------------------------
    # 2. 积水检测（FLOOD）
    # -----------------------------------------------------------------------

    def _detect_flood(self, frame: np.ndarray, stream_id: str) -> list[dict]:
        """检测画面下方积水。

        通过 HSV 颜色空间分析画面下方区域，
        检测大面积蓝色/青色反光区域（积水特征）。

        Args:
            frame: BGR 图像。
            stream_id: 摄像头流 ID。

        Returns:
            积水告警结果列表。
        """
        h, w = frame.shape[:2]
        roi_y_start = int(h * Config.FLOOD_ROI_BOTTOM_RATIO)
        roi = frame[roi_y_start:h, 0:w]

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(
            hsv,
            np.array(Config.FLOOD_HSV_LOWER),
            np.array(Config.FLOOD_HSV_UPPER),
        )

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        roi_area = roi.shape[0] * roi.shape[1]
        flood_area = cv2.countNonZero(mask)
        ratio = flood_area / roi_area if roi_area > 0 else 0

        if ratio >= Config.FLOOD_AREA_THRESHOLD:
            if not self._check_cooldown("FLOOD", stream_id):
                return []

            msg = f"检测到疑似积水区域（占比 {ratio:.1%}）"
            logger.info("Flood detected: %s", msg)
            return [
                {
                    "alert_type": "FLOOD",
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
        """检测画面中火焰区域。

        通过 HSV 颜色空间检测红/橙/黄色火焰区域，
        并结合亮度阈值过滤误检。

        Args:
            frame: BGR 图像。
            stream_id: 摄像头流 ID。

        Returns:
            着火告警结果列表。
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 火焰颜色范围 — 红色在 HSV 中分两段
        mask1 = cv2.inRange(
            hsv,
            np.array(Config.FIRE_HSV_LOWER_1),
            np.array(Config.FIRE_HSV_UPPER_1),
        )
        mask2 = cv2.inRange(
            hsv,
            np.array(Config.FIRE_HSV_LOWER_2),
            np.array(Config.FIRE_HSV_UPPER_2),
        )
        mask = cv2.bitwise_or(mask1, mask2)

        # 亮度过滤：火焰区域 V 通道应较高
        v_channel = hsv[:, :, 2]
        _, bright_mask = cv2.threshold(
            v_channel, Config.FIRE_BRIGHTNESS_THRESHOLD, 255, cv2.THRESH_BINARY
        )
        mask = cv2.bitwise_and(mask, bright_mask)

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        frame_area = frame.shape[0] * frame.shape[1]
        fire_area = cv2.countNonZero(mask)
        ratio = fire_area / frame_area if frame_area > 0 else 0

        if ratio >= Config.FIRE_AREA_THRESHOLD:
            if not self._check_cooldown("FIRE", stream_id):
                return []

            # 定位火焰区域边界框
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
        """检测人员摔倒。

        通过人体框高宽比判断：当 h/w 比值低于阈值时，
        认为人体处于躺倒状态（摔倒）。

        Args:
            person_boxes: 人体框列表。
            stream_id: 摄像头流 ID。

        Returns:
            摔倒告警结果列表。
        """
        results = []

        for box in person_boxes:
            w, h = box["w"], box["h"]
            if w <= 0:
                continue

            aspect_ratio = h / w
            tid = box.get("track_id", -1)

            if aspect_ratio < Config.FALL_ASPECT_RATIO_THRESHOLD:
                self._fall_counter[tid] += 1

                if self._fall_counter[tid] >= Config.FALL_PERSIST_FRAMES:
                    if not self._check_cooldown("FALL", stream_id):
                        continue

                    msg = f"检测到人员疑似摔倒（高宽比 {aspect_ratio:.2f}）"
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
                    # 重置计数，避免重复告警
                    self._fall_counter[tid] = 0
            else:
                # 恢复正常姿态，重置计数
                self._fall_counter[tid] = 0

        return results

    # -----------------------------------------------------------------------
    # 告警冷却
    # -----------------------------------------------------------------------

    def _check_cooldown(self, alert_type: str, stream_id: str) -> bool:
        """检查告警冷却状态。

        同一类型告警在冷却时间内不会重复触发。

        Args:
            alert_type: 告警类型。
            stream_id: 摄像头流 ID。

        Returns:
            True 表示可以触发告警。
        """
        now = time.time()
        cooldown_sec = Config.ALERT_COOLDOWN_SECONDS.get(alert_type, 10)
        last = self._cooldown.get(alert_type, {}).get(stream_id, 0)

        if now - last < cooldown_sec:
            return False

        self._cooldown[alert_type][stream_id] = now
        return True

    # -----------------------------------------------------------------------
    # 工具：绘制标注（供 video.py 调用）
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
            zones: 危险区域配置（用于绘制区域多边形）。
            person_boxes: 人体框列表。

        Returns:
            标注后的 BGR 帧。
        """
        annotated = frame.copy()

        # 绘制危险区域多边形
        if zones:
            for zone in zones:
                polygon = _parse_polygon(zone.get("points_json", ""))
                if polygon is not None:
                    cv2.polylines(
                        annotated, [polygon], True, (0, 0, 255), 2
                    )
                    # 区域名称
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

        # 绘制检测结果框
        color_map = {
            "ZONE_INTRUSION": (0, 0, 255),   # 红色
            "FLOOD": (255, 0, 0),             # 蓝色
            "FIRE": (0, 165, 255),            # 橙色
            "FALL": (0, 255, 255),            # 黄色
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
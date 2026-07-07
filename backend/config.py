"""应用全局配置模块。

定义数据库连接、检测参数阈值等配置项。
"""

import os


class Config:
    """Flask 应用配置基类。"""

    # --- 数据库 ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:root@localhost:3306/home_camera"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- 视频处理 ---
    FRAME_WIDTH = 480          # 处理帧宽度
    FRAME_HEIGHT = 480         # 处理帧高度
    FRAME_SKIP = 3             # 每 N 帧处理一次（跳帧以降低负载）

    # --- 异常检测：积水（FLOOD）---
    # 画面下方检测区域比例（从画面高度的 60% 到 100%）
    FLOOD_ROI_BOTTOM_RATIO = 0.6
    # 蓝色/青色 HSV 范围（积水反光颜色）
    FLOOD_HSV_LOWER = (90, 50, 50)
    FLOOD_HSV_UPPER = (140, 255, 255)
    # 积水区域面积占 ROI 比例阈值，超过则触发告警
    FLOOD_AREA_THRESHOLD = 0.15

    # --- 异常检测：着火（FIRE）---
    # 火焰颜色 HSV 范围（红/橙/黄）
    FIRE_HSV_LOWER_1 = (0, 100, 100)
    FIRE_HSV_UPPER_1 = (25, 255, 255)
    FIRE_HSV_LOWER_2 = (160, 100, 100)
    FIRE_HSV_UPPER_2 = (180, 255, 255)
    # 火焰区域面积占全帧比例阈值
    FIRE_AREA_THRESHOLD = 0.05
    # 火焰亮度阈值（V 通道）
    FIRE_BRIGHTNESS_THRESHOLD = 180

    # --- 异常检测：摔倒（FALL）---
    # 人体框高宽比低于此阈值判定为躺倒/摔倒
    FALL_ASPECT_RATIO_THRESHOLD = 1.3
    # 摔倒持续帧数阈值（避免误报）
    FALL_PERSIST_FRAMES = 5

    # --- 危险区域检测 ---
    # HOG 行人检测器参数
    HOG_WIN_STRIDE = (4, 4)
    HOG_PADDING = (8, 8)
    HOG_SCALE = 1.05
    # 行人检测置信度阈值
    HOG_CONFIDENCE_THRESHOLD = 0.5

    # --- 告警冷却时间（秒），同一类型告警最短间隔 ---
    ALERT_COOLDOWN_SECONDS = {
        "FLOOD": 30,
        "FIRE": 30,
        "FALL": 15,
        "ZONE_INTRUSION": 10,
    }
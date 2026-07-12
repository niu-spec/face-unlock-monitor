# AI 危险区域与异常检测模块 — 技术文档

> **项目名称**：home-camera-monitor（实时视频分析监测系统）  
> **模块名称**：AI 危险区域与异常检测  
> **负责人**：李东礼（团队 D）  
> **编制日期**：2026-07-07  
> **版本**：v1.3（YOLOv8n + 音频检测 + WebRTC overlay API）

---

## 1. 文档概述

### 1.1 目的

本文档系统记录 AI 危险区域与异常检测模块的开发过程、技术方案、实现细节及交付成果，供项目成员查阅和后续维护参考。

### 1.2 适用范围

本文档适用于以下读者：

- 后端开发人员：了解模块接口与集成方式
- 前端开发人员：了解 API 端点和数据结构
- 测试人员：了解检测逻辑与验证方法
- 项目管理人员：了解模块完成度与功能覆盖

### 1.3 模块边界

本模块仅负责以下检测功能，不涉及人脸识别、视频推拉流、告警业务 CRUD 等由其他团队成员负责的模块：

| 功能 | 告警类型 | 责任人 |
|------|----------|--------|
| 危险区域闯入 | `INTRUSION` | 李东礼 |
| 距边缘过近 | `PROXIMITY` | 李东礼 |
| 异常停留 | `LOITER` | 李东礼 |
| 积水检测 | `WATER` | 李东礼 |
| 着火检测 | `FIRE` | 李东礼 |
| 摔倒检测 | `FALL` | 李东礼 |
| 异常声学（可选） | `SCREAM`/`FIGHT`/`CRYING`/`GLASS_BREAK`/`EMERGENCY` | 李东礼 |

---

## 2. 任务背景与需求

### 2.1 项目背景

本系统面向居家智能摄像头监控场景，需对家庭摄像头实时画面进行 AI 分析。除人脸识别与人员统计外，还需支持危险区域配置和异常情况检测，包括：

- 厨房等危险区域禁止小孩进入
- 地面积水识别
- 火焰/着火检测
- 人员摔倒检测

### 2.2 需求规格

| 需求项 | 说明 |
|--------|------|
| 危险区域配置 | 前端可画框配置禁区多边形，存储于数据库 |
| 角色关联 | 危险区域关联禁止角色（如 `child`），仅匹配角色触发告警 |
| 积水检测 | 画面下方出现大面积蓝色/反光区域时触发告警 |
| 着火检测 | 画面中出现红/橙/黄色火焰区域时触发告警 |
| 摔倒检测 | 人体框高宽比异常（躺倒姿态）时触发告警 |
| 异常种类 | ≥2 种异常类型（实现 3 种） |
| 告警冷却 | 同类型告警不重复触发，有最短间隔 |
| 防误报 | 摔倒检测需连续多帧确认 |

### 2.3 与总体架构的关系

依据 [总体架构说明](总体架构说明.md)，本模块位于应用层的 `detection` 模块，接入 `video_stream.process_frame()` 处理器链：

```
RTSP 拉流（CameraWorker 采集线程，frame.copy()）
    → process_frame() 处理器链
    → 人脸检测识别 + 人数统计（dlib）          ← 王梓铭
    → 行人检测（YOLOv8n 优先）+ 危险区域判断     ← 李东礼
    → 异常检测：积水 / 着火 / 跌倒              ← 李东礼
    → overlay 快照 → GET /api/video/presence/  ← 前端 WebRTC + Canvas 叠加
    → MJPEG 输出（/video_feed/，含烧录标注，备用/调试）
```

---

## 3. 技术方案

### 3.1 技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| YOLOv8n | 行人检测（优先） | 准确率 ~90%，模型仅 6MB，ultralytics 自动下载，远优于 HOG |
| OpenCV HOG | 行人检测（降级） | YOLO 不可用时自动降级，无需模型文件，运行轻量 |
| OpenCV HSV | 颜色分割（积水/火焰） | 计算效率高，适合实时视频处理 |
| cv2.pointPolygonTest | 多边形碰撞检测 | OpenCV 内置，精确判断点是否在多边形内 |
| 高宽比分析 | 摔倒检测 | 无需训练模型，基于人体几何特征，简单有效 |

### 3.2 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│           video_stream/services.py（CameraWorker）              │
│  RTSP 拉流（采集线程）→ process_frame()（AI 处理线程）           │
└───────────────────────────────┬──────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────┐
│                   DetectionService                            │
│  ┌─────────────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  │
│  │ _detect_zone_    │  │ _detect_ │  │_detect_│  │_detect_│  │
│  │ intrusion()      │  │ flood()  │  │ fire() │  │ fall() │  │
│  │ 危险区域闯入      │  │ 积水检测  │  │ 着火检测│  │ 摔倒检测│  │
│  └────────┬────────┘  └────┬─────┘  └───┬────┘  └───┬────┘  │
│           └────────────────┼─────────────┼──────────┘        │
│                            ▼                                 │
│                  ┌─────────────────┐                         │
│                  │ _check_cooldown │  告警冷却控制            │
│                  └─────────────────┘                         │
└───────────────────────────────┬──────────────────────────────┘
                                │ List[dict] 检测结果
                                ▼
           ┌────────────────────────────────────┐
           │  标注绘制（draw_overlays）           │
           │  告警记录写入（Alert 模型）           │
           └────────────────────────────────────┘
```

### 3.3 模块目录结构

```
backend/
├── apps/
│   ├── alerts/                        # 告警模块（刘帅华）
│   │   ├── models.py                  # Alert 数据模型（Django ORM）
│   │   ├── services.py                # create_alert() 等告警写入接口
│   │   └── ...
│   ├── zones/                         # 危险区域 CRUD（刘帅华）
│   │   ├── models.py                  # Zone 数据模型（Django ORM）
│   │   └── ...
│   └── detection/                     # 危险区域与异常检测 ★ 本模块
│       ├── __init__.py
│       ├── services.py                # 核心检测服务（DetectionService）
│       ├── views.py                   # API 视图（analyze / status）
│       └── urls.py                    # URL 路由
├── config/
│   ├── settings.py                    # Django 配置（已注册 detection app）
│   └── urls.py                        # 根路由（已添加 /api/detection/）
└── manage.py                          # Django 入口
```

---

## 4. 详细实现

### 4.1 配置文件

检测参数采用两层配置机制：

1. **默认值**：定义在 [services.py](file:///c:/Users/30363/OneDrive/Desktop/camera-monitor/home-camera-monitor/backend/apps/detection/services.py) 的 `DETECTION_CONFIG` 字典中
2. **覆盖值**：可在 Django [settings.py](file:///c:/Users/30363/OneDrive/Desktop/camera-monitor/home-camera-monitor/backend/config/settings.py) 中通过 `DETECTION_CONFIG` 字典覆盖，未设置时使用默认值

关键配置项：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FLOOD_ROI_BOTTOM_RATIO` | 0.6 | 积水检测 ROI 起始比例（画面下方 40%） |
| `FLOOD_HSV_LOWER/UPPER` | (90,50,50)/(140,255,255) | 积水蓝色/青色 HSV 范围 |
| `FLOOD_AREA_THRESHOLD` | 0.15 | 积水面积占比阈值 |
| `FIRE_HSV_LOWER_1/UPPER_1` | (0,100,100)/(25,255,255) | 火焰红/橙色 HSV 范围 |
| `FIRE_HSV_LOWER_2/UPPER_2` | (160,100,100)/(180,255,255) | 火焰红色 HSV 范围（高段） |
| `FIRE_AREA_THRESHOLD` | 0.05 | 火焰面积占比阈值 |
| `FIRE_BRIGHTNESS_THRESHOLD` | 180 | 火焰亮度 V 通道阈值 |
| `FALL_ASPECT_RATIO_THRESHOLD` | 0.8 | 高宽比阈值（低于此值且 w>h 判定为横向姿态） |
| `FALL_PERSIST_FRAMES` | 5 | 摔倒持续帧数（防误报） |
| `FALL_MIN_STANDING_RATIO` | 1.6 | 明确站立高宽比（h/w > 此值累计 3 帧后标记为曾站立） |
| `FALL_CENTER_DROP_RATIO` | 0.30 | 中心点下移比例（> 30% 人体高度判定为大幅坠落） |
| `FALL_AR_VELOCITY_THRESHOLD` | 1.0 | 高宽比变化速率阈值（> 1.0/s 判定为骤变，单位/秒） |
| `YOLO_MODEL` | `yolov8n.pt` | YOLO 模型文件（首次运行时自动下载） |
| `YOLO_CONFIDENCE_THRESHOLD` | 0.5 | YOLO 检测置信度阈值 |
| `YOLO_IOU_THRESHOLD` | 0.45 | YOLO NMS IOU 阈值 |
| `YOLO_PERSON_CLASS_ID` | 0 | COCO 数据集中 person 类别 ID |
| `HOG_CONFIDENCE_THRESHOLD` | 0.5 | HOG 行人检测置信度阈值（降级时使用） |
| `ALERT_COOLDOWN_SECONDS` | 见配置 | 各类型告警冷却时间 |

### 4.2 数据模型

#### 4.2.1 Zone（危险区域）

Django 模型位于 `backend/apps/zones/models.py`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT PK | 自增 |
| `household` | FK | 所属家庭 |
| `name` | VARCHAR | 区域名称（如「厨房」） |
| `stream_id` | VARCHAR | 业务流 ID（`living_room` / `kitchen`） |
| `points_json` | JSON | 多边形顶点 `{x,y}` 数组（640×480 坐标系） |
| `forbidden_roles` | JSON | 禁止角色列表（如 `["child"]`） |
| `safe_distance` | INT | 距边缘安全距离（像素） |
| `dwell_time` | INT | 逗留超时（秒） |
| `is_active` | BOOL | 是否启用 |

#### 4.2.2 Alert（告警记录）

Django 模型位于 `backend/apps/alerts/models.py`，通过 `apps.alerts.services.create_alert()` 写入：

告警类型枚举（与 dev 分支 alerts/models.py 对齐）：

| 枚举值 | 含义 | 归属模块 |
|--------|------|----------|
| `FACE_UNKNOWN` | 陌生人 | 人脸模块（王梓铭） |
| `INTRUSION` | 危险区域闯入 | 本模块 |
| `WATER` | 积水 | 本模块 |
| `FIRE` | 着火 | 本模块 |
| `FALL` | 摔倒 | 本模块 |

### 4.3 核心检测服务（DetectionService）

#### 4.3.1 类结构

```python
class DetectionService:
    def __init__(self)           # 初始化 YOLO（HOG 降级） + 冷却计数器
    def process_frame(...)       # 公共入口：执行全部检测
    def draw_overlays(...)       # 标注绘制
    def _detect_pedestrians(...) # YOLO 行人检测（HOG 降级）
    def _detect_pedestrians_yolo(...) # YOLOv8n 检测
    def _detect_pedestrians_hog(...)  # HOG 检测（降级方案）
    def _detect_zone_intrusion(...) # 危险区域闯入
    def _detect_water(...)       # 积水检测
    def _detect_fire(...)        # 着火检测
    def _detect_fall(...)        # 摔倒检测
    def _check_cooldown(...)     # 告警冷却检查
```

#### 4.3.2 公共入口：process_frame()

```python
def process_frame(
    self,
    frame: np.ndarray,                              # BGR 图像
    stream_id: str,                                 # 流 ID
    person_boxes: Optional[list[dict]] = None,      # 外部人体框（可选）
    face_roles: Optional[dict[int, str]] = None,    # 人脸角色（可选）
    zones: Optional[list[dict]] = None,             # 危险区域配置（可选）
) -> list[dict]:                                    # 检测结果列表
```

**设计要点**：

- `person_boxes` 参数可选：若传入则复用外部检测结果（如人脸模块已做行人检测），否则内部 YOLO 自行检测，避免重复计算
- `face_roles` 用于危险区域闯入的角色匹配（如判断是否为 `child`）
- `zones` 参数可选：无区域配置时跳过闯入检测
- 返回统一格式的检测结果列表，每个结果包含 `alert_type`、`message`、`bbox`、`severity` 等字段

#### 4.3.3 危险区域闯入检测

**算法流程**：

```
1. 遍历所有启用的危险区域
2. 解析每个区域的 points_json 为 cv2 多边形
3. 遍历所有人体框
4. 获取该行人的角色（来自 face_roles）
5. 若角色属于 forbidden_roles，检查矩形中心点是否在多边形内
6. 若在内部且冷却时间已过，生成 INTRUSION 告警
```

**关键实现**：

- 多边形碰撞检测使用 `cv2.pointPolygonTest()`，以人体框中心点为判断依据
- 角色匹配支持字符串 `"child"` 和逗号分隔 `"child,elderly"` 两种格式
- 告警冷却 10 秒，避免同一事件反复触发

#### 4.3.4 积水检测

**算法流程**：

```
1. 截取画面下方 40% 区域作为 ROI
2. 转换 BGR → HSV 颜色空间
3. 使用 cv2.inRange 过滤蓝色/青色范围
4. 形态学开运算 + 闭运算去噪（椭圆核 5×5，各 2 次迭代）
5. 计算积水像素占 ROI 面积比例
6. 比例 ≥ 15% 且冷却时间已过 → 触发 WATER 告警
```

**设计考量**：

- 仅检测画面下方是因为积水通常在地面，画面顶部区域不会积水
- 形态学开运算去除孤立噪点，闭运算连接断裂区域
- 冷却时间 30 秒，因为积水是持续性场景，不需要高频告警

#### 4.3.5 着火检测

**算法流程**：

```
1. 转换 BGR → HSV 颜色空间
2. 双段红色范围过滤（HSV 红色在色相环两端）
3. V 通道亮度过滤（> 180），排除暗红色误检
4. 形态学开运算 + 闭运算去噪（椭圆核 3×3）
5. 计算火焰像素占全帧面积比例
6. 比例 ≥ 5% 且冷却时间已过 → 触发 FIRE 告警
7. 定位最大火焰轮廓边界框
```

**设计考量**：

- 红色在 HSV 中跨越 0° 边界，需分两段检测（0~25° 和 160~180°）
- 亮度过滤可有效排除红色衣物、红色家具等误检
- 冷却时间 30 秒

#### 4.3.6 摔倒检测

**算法流程**：

```
1. 遍历所有人体框
2. 计算高宽比 aspect_ratio = h / w
3. 若 aspect_ratio < 1.3，递增该 track_id 的连续摔倒计数
4. 若连续计数 ≥ 5 帧且冷却时间已过 → 触发 FALL 告警
5. 若 aspect_ratio ≥ 1.3，重置计数（恢复正常姿态）
```

**设计考量**：

- 站立人体高宽比通常 > 2.0，躺倒时 < 1.3
- 5 帧持续确认机制避免蹲下、弯腰等短暂动作的误报
- 冷却时间 15 秒，较积水/着火短，因为摔倒需要更及时响应

#### 4.3.7 告警冷却机制

```python
def _check_cooldown(alert_type: str, stream_id: str) -> bool:
    now = time.time()
    cooldown_sec = Config.ALERT_COOLDOWN_SECONDS[alert_type]
    last = self._cooldown[alert_type][stream_id]
    if now - last < cooldown_sec:
        return False
    self._cooldown[alert_type][stream_id] = now
    return True
```

以 `{alert_type: {stream_id: timestamp}}` 二级字典存储各类型、各摄像头流的最近告警时间，按类型独立冷却。

#### 4.3.8 YOLO 行人检测（v1.2 新增）

v1.2 将行人检测器从 HOG 升级为 **YOLOv8n**，采用双检测器策略：

**初始化流程**：

```
1. 尝试导入 ultralytics.YOLO
2. 若成功，加载 yolov8n.pt（首次运行时自动下载 ~6MB）
3. 若失败（ultralytics 未安装 / 模型加载异常），自动降级为 HOG
4. 记录当前使用的检测器类型到日志
```

**YOLO 推理流程**：

```
1. 调用 self._yolo(frame, conf=0.5, iou=0.45, classes=[0])
2. 过滤 class_id=0（COCO 数据集的 person 类别）
3. 将 xyxy 格式转换为 {x, y, w, h} 格式
4. 附加 confidence 分数到 box 字典中
```

**输出格式**（与 HOG 完全兼容）：

```python
{
    "x": int,          # 左上角 x
    "y": int,          # 左上角 y
    "w": int,          # 宽度
    "h": int,          # 高度
    "track_id": i,     # 框序号（HOG 兼容）
    "confidence": 0.85 # YOLO 置信度（新增字段）
}
```

**性能对比**：

| 指标 | HOG | YOLOv8n |
|------|-----|---------|
| 行人检测准确率 | ~60-70% | ~90%+ |
| 模型文件大小 | 无（内置） | ~6MB（自动下载） |
| 推理速度（CPU） | 快 | 中等 |
| 误报率 | 较高 | 低 |
| 漏检率 | 较高 | 低 |

**设计考量**：

- `_detect_pedestrians()` 作为统一入口，内部根据 `self._detector_type` 自动路由到 YOLO 或 HOG
- 下游模块（闯入检测、摔倒检测）完全无感知，无需任何修改
- `confidence` 字段为可选字段，不影响现有逻辑

#### 4.3.9 标注绘制（draw_overlays）

提供 `draw_overlays()` 方法供 `video_stream.process_frame()` 在 MJPEG 编码前调用；前端主展示通过 `/api/video/presence/` overlay API 在 WebRTC 预览上 Canvas 叠加。在帧上绘制：

- 危险区域多边形（红色轮廓 + 区域名称）
- 各类型告警边界框（不同颜色区分）

颜色映射：

| 告警类型 | BGR 颜色 | 视觉效果 |
|----------|----------|----------|
| `INTRUSION` | (0, 0, 255) | 红色 |
| `WATER` | (255, 0, 0) | 蓝色 |
| `FIRE` | (0, 165, 255) | 橙色 |
| `FALL` | (0, 255, 255) | 黄色 |

### 4.4 API 接口

#### 4.4.1 POST /api/detection/analyze

对单帧图像执行检测分析。

**请求**（multipart/form-data）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image` | file | 是 | 图像文件（jpg/png） |
| `stream_id` | string | 否 | 摄像头流 ID，默认 "living_room" |
| `zones` | JSON string | 否 | 危险区域配置列表 |
| `person_boxes` | JSON string | 否 | 已检测的人体框列表 |
| `face_roles` | JSON string | 否 | 人脸识别角色映射 |

**响应**：

```json
{
    "success": true,
    "results": [
        {
            "alert_type": "INTRUSION",
            "message": "[厨房] 检测到 child 闯入禁区",
            "bbox": [120, 200, 80, 160],
            "severity": "high",
            "zone_id": 1,
            "zone_name": "厨房"
        }
    ]
}
```

#### 4.4.2 GET /api/detection/status

获取检测服务运行状态。

**响应**：

```json
{
    "success": true,
    "status": "running",
    "service": "DetectionService",
    "capabilities": ["INTRUSION", "WATER", "FIRE", "FALL"]
}
```

#### 4.4.3 模块间调用接口

其他模块（如 `video_stream.services`）可通过 `get_detection_service()` 获取全局服务实例，直接调用 `process_frame()` 和 `draw_overlays()` 方法：

```python
from apps.detection.services import get_detection_service

service = get_detection_service()
results = service.process_frame(frame, stream_id, person_boxes, face_roles, zones)
annotated = service.draw_overlays(frame, results, zones, person_boxes)
```

告警通过 `apps.alerts.services.create_alert()` 写入数据库，与 dev 分支刘帅华的告警模块对接，无需直接操作 Alert 模型。

---

## 5. 数据流

### 5.1 视频处理流水线中的检测流程

```
┌──────────┐     ┌──────────────────────┐     ┌──────────────────┐
│ RTSP 拉流 │ ──→ │ CameraWorker 采集线程  │ ──→ │ process_frame()  │
└──────────┘     │ frame.copy() 防并发    │     │ 人脸识别（王梓铭）  │
                 └──────────────────────┘     └────────┬─────────┘
                                                        │ person_boxes + face_roles
                                                        ▼
                                               ┌──────────────────┐
                                               │ 检测服务（李东礼） │
                                               │ 危险区域 / 积水    │
                                               │ 着火 / 摔倒        │
                                               └────────┬─────────┘
                                                        │ results
                                                        ▼
                                               ┌──────────────────┐
                                               │ overlay 快照发布   │
                                               │ /api/video/presence│
                                               └────────┬─────────┘
                                                        │
                                                        ▼
                                               ┌──────────────────┐
                                               │ MJPEG 输出（备用） │
                                               │ /video_feed/      │
                                               └──────────────────┘
```

### 5.2 告警记录流程

```
检测结果 → _create_alert() → apps.alerts.services.create_alert()
         → Alert 模型写入数据库
         → 前端轮询 /api/alerts/ 获取
         → 告警中心展示 + 处置
```

---

## 6. 交付文件清单

| 文件路径 | 说明 | 代码行数 |
|----------|------|----------|
| `backend/apps/detection/__init__.py` | 模块初始化 | 0 |
| `backend/apps/detection/services.py` | 核心检测服务（Django 适配版） | ~400 |
| `backend/apps/detection/views.py` | API 视图（analyze / status） | ~90 |
| `backend/apps/detection/urls.py` | URL 路由 | 7 |
| `backend/config/settings.py` | Django 配置（已注册 detection app + DETECTION_CONFIG） | 修改 8 行 |
| `backend/config/urls.py` | 根路由（已添加 /api/detection/） | 修改 1 行 |
| `backend/requirements.txt` | 依赖（已添加 opencv/numpy/pillow/ultralytics） | 修改 1 行 |

**总计**：新增 4 个文件，修改 3 个文件，约 500 行代码。

> **架构变更说明**：v1.0 基于 Flask 蓝图，v1.1 适配为 Django app，与 dev 分支统一架构。告警类型命名同步为 `INTRUSION`/`WATER`/`FIRE`/`FALL`，告警写入通过 `apps.alerts.services.create_alert()` 对接。v1.2 行人检测器从 HOG 升级为 YOLOv8n，HOG 保留作为降级方案。

---

## 7. 验收标准对应

| 验收项 | 分值 | 实现情况 |
|--------|------|----------|
| 目标检测：危险区域画框 + 厨房禁止小孩进入 + 闯入告警 | 25 | 已实现，通过多边形碰撞 + 角色匹配 |
| 实时视频检测：≥2 种异常 | 20 | 已实现 3 种（积水、着火、摔倒） |
| 告警中心对接 | 8 | 已定义 Alert 模型 + API，由刘帅华对接 |

---

## 8. 后续建议

### 8.1 参数调优

- 积水/着火面积阈值需根据实际摄像头安装角度和室内环境微调
- YOLO 置信度阈值（`YOLO_CONFIDENCE_THRESHOLD`）可根据实际场景在 0.3~0.7 之间调整

### 8.2 功能扩展

- 摔倒检测可结合关键点检测（如 MediaPipe Pose）提高准确率
- 着火检测可增加运动特征分析（火焰闪烁频率），减少静态红色物体误报
- 支持多摄像头流独立配置不同的检测阈值

### 8.3 性能优化

- YOLO 推理在 CPU 上较 HOG 慢，建议配合跳帧策略（当前 `FRAME_SKIP=3`）
- 积水/着火检测可降低分辨率后执行，减少计算开销
- 可考虑使用 ONNX 或 OpenVINO 加速 YOLO 推理

---

## 9. 异常声学事件检测与音视频联动告警

> **版本**：v1.3 — 新增音频检测能力  
> **状态**：代码已合入 `dev`（2026-07-11）；OpenSpec change `audio-abnormal-sound-detection` 待云验收归档  
> **编制日期**：2026-07-11

### 9.1 需求背景

当前模块仅覆盖**视觉维度**的异常检测（积水、着火、摔倒），但居家安全场景中存在大量仅靠视觉难以可靠识别的事件：

| 事件类型 | 视觉特征 | 听觉特征 | 仅视频的局限 |
|----------|----------|----------|-------------|
| 打架/争吵 | 人体快速移动、肢体接触 | 高声喊叫、撞击声、争吵语音 | 视觉易被遮挡，且与打闹难以区分 |
| 尖叫/呼救 | 人脸恐惧表情（需高分辨率）| 尖锐叫声、呼救语音 | 表情识别需近距离+高分辨率，居家摄像头难以满足 |
| 玻璃破碎 | 碎片飞溅（极难检测） | 清脆碎裂声 | 碎片太小，YOLO 不可能稳定检测 |
| 婴儿哭喊 | 面部表情 | 持续哭声音频 | 夜间/昏暗环境视觉失效 |

**核心思路**：增加**音频维度**的异常事件检测，并通过**音视频联动分析**（同一时间窗口内音频+视频同时触发异常 → 置信度提升），提高整体检测的可靠性。

### 9.2 功能需求

| 编号 | 需求项 | 说明 |
|------|--------|------|
| R9.1 | 实时音频采集 | 从 RTSP 视频流中抽取音频轨道，连续输出音频片段 |
| R9.2 | 异常声音分类 | 识别尖叫、哭喊、争吵声、玻璃破碎等异常声音类别 |
| R9.3 | 异常声音告警 | 检测到异常声音时，以独立告警类型写入告警表 |
| R9.4 | 音视频联动 | 同一时间窗口内音频+视频同时触发异常时，提升告警等级或创建关联告警 |
| R9.5 | 音频告警冷却 | 与视频告警一致的冷却机制，防止同一事件反复触发 |
| R9.6 | 音频片段存储 | 触发告警时保存异常音频片段（3-5 秒），供回放确认 |

### 9.3 技术方案

#### 9.3.1 总体架构

```
RTSP 流 (rtsp://127.0.0.1:8554/stream/1)
        │
        ├─── OpenCV VideoCapture ──→ 视频帧 ──→ process_frame()（已有）
        │                                         ├── 人脸识别
        │                                         ├── 危险区域闯入
        │                                         ├── 积水/着火/摔倒
        │                                         └── 告警创建
        │
        └─── FFmpeg 子进程 ──→ 音频 PCM 流 ──→ AudioDetectionService（新增）
                       │                           ├── 音频分帧 (2-3s chunks)
                       │                           ├── 梅尔频谱图提取
                       │                           ├── PANNs 分类推理
                       │                           ├── 异常声音告警创建
                       │                           └── 写入联动缓冲器
                                                  │
                    ┌─────────────────────────────┘
                    ▼
          ┌──────────────────┐
          │ 音视频联动缓冲器   │  ← 新增
          │ (滑动时间窗口)    │
          │                  │
          │ 视频告警 ──┬── 时间关联 ──→ 联动告警（severity 升级）
          │ 音频告警 ──┘              │
          └──────────────────────────┘
```

#### 9.3.2 音频采集方案：FFmpeg 从 RTSP 抽取音频

现有视频采集使用 OpenCV `VideoCapture` 读取 RTSP 流，但 OpenCV **不支持读取音频轨道**。需要单独的音频采集通道：

```
ffmpeg -i rtsp://127.0.0.1:8554/stream/1 \
       -vn \                    # 丢弃视频
       -acodec pcm_s16le \      # 16-bit PCM
       -ar 32000 \              # 重采样至 32kHz（与 audio_capture.py 一致）
       -ac 1 \                  # 单声道
       -f wav \                 # WAV 格式
       pipe:1                   # 输出到 stdout（Python 进程读取）
```

**关键设计点**：
- FFmpeg 作为**子进程**启动（通过 `subprocess.Popen`），持续输出 PCM 数据到管道
- Python 端按固定时长（2-3 秒）从管道读取音频块
- FFmpeg 进程与 Django 主进程同生命周期，随 `video_stream` worker 启停
- 当 RTSP 流无音频轨道时，FFmpeg 会报错退出 → 自动降级（仅视频检测，不影响现有功能）

#### 9.3.3 音频分类模型：PANNs CNN14

| 对比维度 | PANNs CNN14 | YAMNet | 自定义分类器 |
|----------|-------------|--------|-------------|
| 深度学习框架 | PyTorch ✅ | TensorFlow ❌ | PyTorch ✅ |
| 预训练数据集 | AudioSet (2M+) | AudioSet (2M+) | 需自训练 |
| 模型大小 | ~80MB | ~15MB | 取决于设计 |
| 类别覆盖 | 527 类 | 521 类 | 自定义 |
| 与现有技术栈兼容 | ✅ (同 YOLO) | ❌ 需新增 TF | ✅ |
| 推理延迟 (CPU) | ~50ms/chunk | ~30ms/chunk | ~10ms/chunk |

**选择 PANNs 理由**：
1. 与 YOLOv8n 共享 PyTorch 运行时，**不引入第二个深度学习框架**
2. AudioSet 527 类中已包含目标类别：`Shout`、`Screaming`、`Crying, sobbing`、`Shatter`、`Yell`、`Gunshot, gunfire` 等
3. 通过 `torch.hub` 一行加载，无需额外配置

**目标音频类别映射**：

| 业务告警类型 | AudioSet 对应类别 | 类别 ID |
|-------------|-------------------|---------|
| `SCREAM` | Screaming / Shout / Yell | 特定 ID |
| `FIGHT` | Shout + 嘈杂人声组合 | 多标签 |
| `GLASS_BREAK` | Shatter / Glass | 特定 ID |
| `CRYING` | Crying, sobbing / Baby cry, infant cry | 特定 ID |

**推理流程**：
```
PCM 音频块 (16kHz, mono, 3s)
    → librosa 提取梅尔频谱图 (64 mel-bands)
    → torch tensor (1, 1, T, 64)  [batch, channel, time, mel]
    → PANNs CNN14 前向推理
    → sigmoid 输出 527 类概率
    → 映射到目标类别 + 阈值过滤 (> 0.3)
    → 触发告警
```

#### 9.3.4 音视频联动分析

**滑动时间窗口缓冲器**：

```
class AVCorrelationBuffer:
    """
    维护一个环形缓冲器，记录近 N 秒内的所有检测事件。
    
    - audio_events:  deque[AudioEvent]    (timestamp, alert_type, confidence)
    - video_events:  deque[VideoEvent]    (timestamp, alert_type, confidence)
    
    每个新事件入队时，检查时间窗口内是否存在异类事件。
    """
```

**联动规则**：

| 视频告警 | 音频告警 | 时间窗口 | 联动结果 |
|----------|----------|----------|----------|
| `FALL` | `SCREAM` | ±5s | 创建 `EMERGENCY` 关联告警（severity: critical） |
| `INTRUSION` | `SCREAM` / `FIGHT` | ±5s | `INTRUSION` 升级为 critical |
| `FIRE` | `SCREAM` | ±5s | `FIRE` 升级为 critical |
| `WATER` | — | — | 不联动（积水无典型关联声音） |
| — | `SCREAM` | 仅音频 | 单独创建 `SCREAM` 告警（severity: high） |
| — | `FIGHT` | 仅音频 | 单独创建 `FIGHT` 告警（severity: high） |
| — | `GLASS_BREAK` | 仅音频 | 单独创建 `GLASS_BREAK` 告警（severity: medium） |

**设计考量**：
- 即使没有视频告警配合，音频异常仍**独立产生告警**（不依赖视频确认）
- 联动是"增强"而非"必要条件"——视频检测不可靠时，音频独立工作
- 时间窗口可配置（默认 ±5 秒）

#### 9.3.5 模块目录结构（新增部分）

```
backend/apps/detection/
├── __init__.py
├── services.py                      # 已有：DetectionService（视频检测）
├── audio_service.py                 # 新增：AudioDetectionService（音频检测）
├── audio_capture.py                 # 新增：FFmpeg 音频采集子进程管理
├── av_correlation.py                # 新增：音视频联动缓冲器 & 规则引擎
├── views.py                         # 已有（需新增 GET /api/detection/audio/status）
├── urls.py                          # 已有（需新增路由）
└── tests/
    ├── test_audio_service.py        # 新增：音频检测单元测试
    └── test_av_correlation.py       # 新增：联动逻辑单元测试
```

#### 9.3.6 新增告警类型

在 `alerts/models.py` 的告警类型枚举中新增：

| 枚举值 | 含义 | 触发源 | 默认严重程度 |
|--------|------|--------|-------------|
| `SCREAM` | 尖叫/呼救声 | 音频：PANNs 检测 | `high` |
| `FIGHT` | 打架/争吵声 | 音频：PANNs 检测 | `high` |
| `GLASS_BREAK` | 玻璃破碎声 | 音频：PANNs 检测 | `medium` |
| `CRYING` | 哭喊声（婴儿/成人） | 音频：PANNs 检测 | `medium` |
| `EMERGENCY` | 音视频联动紧急事件 | 联动：AVCorrelationBuffer | `critical` |

### 9.4 配置项（新增）

在 `DETECTION_CONFIG` 字典中新增音频相关配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `AUDIO_ENABLED` | `True` | 是否启用音频检测（RTSP 无音频时自动降级） |
| `AUDIO_CHUNK_DURATION` | `3.0` | 音频分析块时长（秒） |
| `AUDIO_SAMPLE_RATE` | `16000` | 音频重采样率 |
| `AUDIO_N_MELS` | `64` | 梅尔频谱图频带数 |
| `AUDIO_MODEL` | `panns_cnn14` | 音频分类模型 |
| `AUDIO_CONFIDENCE_THRESHOLD` | `0.3` | 音频分类置信度阈值 |
| `AV_CORRELATION_WINDOW` | `5.0` | 音视频联动时间窗口（秒） |
| `AUDIO_ALERT_COOLDOWN` | `15` | 音频告警冷却时间（秒） |
| `AUDIO_SNIPPET_DIR` | `snapshots/audio/` | 异常音频片段保存目录 |

### 9.5 数据流：音频处理完整链路

```
1. Django video_stream worker 启动
       │
2. ──── spawn FFmpeg 子进程 ────→ stdout: PCM 16kHz mono
       │
3. AudioDetectionService 后台线程
       │  循环读取 3 秒 PCM → numpy array
       │
4. librosa.feature.melspectrogram() → 梅尔频谱图
       │
5. PANNs CNN14 推理 → 527 类概率向量
       │
6. 映射到目标类别 + 阈值过滤
       │
7. 触发告警 → create_alert(AudioAlert)
       │
8. AVCorrelationBuffer.enqueue(audio_event)
       │
9. 检查窗口内是否有 video_event → 有 → create_alert(EMERGENCY, severity=critical)
       │                             无 → 仅音频告警
       │
10. 保存音频片段 (.wav) → alert.snapshot_path 关联
```

### 9.6 性能评估

| 环节 | 预估 CPU 开销 | 说明 |
|------|-------------|------|
| FFmpeg 音频解码 | 极低 (~1%) | 纯音频解码，无视频 |
| 梅尔频谱图提取 | 极低 (~1%) | librosa 高度优化 |
| PANNs CNN14 推理 (CPU) | **~15-20%** 单核 | 每 3 秒推理一次，约 50-80ms |
| 联动缓冲器 | 忽略不计 | 纯内存操作 |

- 音频推理频率：每 3 秒一次（远低于视频的每帧处理），CPU 开销可控
- 推荐使用 ONNX Runtime 加速 PANNs 推理（参考 8.3 节 ONNX 建议）
- 若 CPU 资源紧张，可增大 `AUDIO_CHUNK_DURATION` 至 5 秒降低推理频率

### 9.7 依赖清单

#### 9.7.1 系统级依赖

| 组件 | 安装方式 | 说明 |
|------|----------|------|
| FFmpeg | `apt install ffmpeg` (Linux) / `choco install ffmpeg` (Windows) | 服务器可能已有；需确认版本 ≥ 4.0 |

#### 9.7.2 Python 依赖（新增至 requirements.txt）

```
librosa>=0.10.0
soundfile>=0.12.0
torchaudio>=2.0.0
ffmpeg-python>=0.2.0
scipy>=1.10.0          # 可能已有，检查
```

#### 9.7.3 模型文件

| 文件 | 大小 | 获取方式 |
|------|------|----------|
| `Cnn14_mAP=0.431.pth` | ~80MB | `torch.hub.load('qiuqiangkong/panns_audioset', 'cnn14')` 首次运行时自动下载至 `~/.cache/torch/hub/` |

### 9.8 风险与降级策略

| 风险 | 影响 | 降级方案 |
|------|------|----------|
| RTSP 流不含音频轨道 | 音频检测完全不可用 | FFmpeg 报错后自动禁用音频检测，仅视频检测正常工作 |
| PANNs 模型下载失败 | 音频检测不可用 | 捕获异常，日志告警，仅视频检测正常工作 |
| FFmpeg 子进程崩溃 | 音频管道中断 | 自动重连机制（最多 3 次重试），重连失败后降级 |
| CPU 负载过高 | 视频帧处理延迟 | 调大音频 chunk duration 或暂时禁用音频检测 |
| 模型误判（类间混淆） | 误报/漏报 | 通过置信度阈值 + 连续多帧确认 + 音视频联动降低误报 |

### 9.9 验收标准对应

| 验收项 | 实现情况 |
|--------|----------|
| 识别打架/争吵声 | 通过 PANNs AudioSet `Shout` + 多标签组合识别 |
| 识别尖叫/呼救声 | 通过 PANNs AudioSet `Screaming`、`Crying, sobbing` 识别 |
| 音视频联动分析 | AVCorrelationBuffer 滑动时间窗口 + 联动规则引擎 |
| 提高异常行为检测可靠性 | 音频独立告警 + 视频独立告警 + 联动升级 → 三维检测 |

### 9.10 实施状态

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1–6 | 音频采集、PANNs 分类、音视频联动、集成 | ✅ 已完成（见 `openspec/changes/audio-abnormal-sound-detection/tasks.md`） |
| 云验收 | 生产环境音频告警 + EMERGENCY 联动 | 待归档 OpenSpec change |

---

*文档结束 — 变更请通知文档专员刘澎潮（F）。*
# AI 危险区域与异常检测模块 — 技术文档

> **项目名称**：home-camera-monitor（实时视频分析监测系统）  
> **模块名称**：AI 危险区域与异常检测  
> **负责人**：李东礼（团队 D）  
> **编制日期**：2026-07-07  
> **版本**：v1.1（适配 Django 架构）

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
| 危险区域闯入检测 | `INTRUSION` | 李东礼 |
| 积水检测 | `WATER` | 李东礼 |
| 着火检测 | `FIRE` | 李东礼 |
| 摔倒检测 | `FALL` | 李东礼 |

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

依据 [总体架构说明](../docs/总体架构说明.md)，本模块位于应用层的 `detection` 模块，处于视频处理流水线中：

```
RTMP 帧 → 跳帧 → 缩放 480×480
    → 人脸检测识别 + 人数统计（dlib）      ← 王梓铭
    → 行人检测 + 危险区域判断（HOG）       ← 李东礼
    → 异常检测：积水 / 着火 / 跌倒          ← 李东礼
    → 画框标注 → MJPEG 输出
```

---

## 3. 技术方案

### 3.1 技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| OpenCV HOG | 行人检测 | 项目统一选用，无需额外模型文件，运行轻量 |
| OpenCV HSV | 颜色分割（积水/火焰） | 计算效率高，适合实时视频处理 |
| cv2.pointPolygonTest | 多边形碰撞检测 | OpenCV 内置，精确判断点是否在多边形内 |
| 高宽比分析 | 摔倒检测 | 无需训练模型，基于人体几何特征，简单有效 |

### 3.2 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                    video.py（视频流水线）                       │
│  拉取 RTMP 帧 → 缩放 → 调用 DetectionService.process_frame()  │
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
| `FALL_ASPECT_RATIO_THRESHOLD` | 1.3 | 高宽比阈值（低于此值判定为摔倒） |
| `FALL_PERSIST_FRAMES` | 5 | 摔倒持续帧数（防误报） |
| `HOG_CONFIDENCE_THRESHOLD` | 0.5 | HOG 行人检测置信度阈值 |
| `ALERT_COOLDOWN_SECONDS` | 见配置 | 各类型告警冷却时间 |

### 4.2 数据模型

#### 4.2.1 Zone（危险区域）

```python
class Zone(db.Model):
    id              # INT PK, 自增
    name            # VARCHAR(64), 区域名称（如"厨房"）
    stream_id       # VARCHAR(16), 关联摄像头流 ID
    points_json     # TEXT, 多边形顶点坐标 JSON
    forbidden_roles # VARCHAR(64), 禁止角色（逗号分隔，如"child"）
    enabled         # BOOLEAN, 是否启用
    created_at      # DATETIME, 创建时间
```

#### 4.2.2 Alert（告警记录）

```python
class Alert(db.Model):
    id              # INT PK, 自增
    alert_type      # VARCHAR(32), 告警类型枚举
    stream_id       # VARCHAR(16), 关联摄像头流 ID
    message         # VARCHAR(256), 告警描述
    status          # VARCHAR(16), 处置状态（pending/confirmed/resolved/dismissed）
    snapshot_path   # VARCHAR(256), 告警截图路径
    detected_at     # DATETIME, 检测到异常的时间
    created_at      # DATETIME, 创建时间
    updated_at      # DATETIME, 更新时间
```

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
    def __init__(self)           # 初始化 HOG 检测器 + 冷却计数器
    def process_frame(...)       # 公共入口：执行全部检测
    def draw_overlays(...)       # 标注绘制
    def _detect_pedestrians(...) # HOG 行人检测
    def _detect_zone_intrusion(...) # 危险区域闯入
    def _detect_flood(...)       # 积水检测
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

- `person_boxes` 参数可选：若传入则复用外部检测结果（如人脸模块已做行人检测），否则内部 HOG 自行检测，避免重复计算
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

#### 4.3.8 标注绘制（draw_overlays）

提供 `draw_overlays()` 方法供 video.py 在 MJPEG 输出前调用，在帧上绘制：

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

其他模块（如 video.py）可通过 `get_detection_service()` 获取全局服务实例，直接调用 `process_frame()` 和 `draw_overlays()` 方法：

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
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│ RTMP 拉流 │ ──→ │ 缩放 480×480 │ ──→ │ 人脸识别（王梓铭） │
└──────────┘     └──────────────┘     └────────┬─────────┘
                                               │ person_boxes + face_roles
                                               ▼
                                      ┌──────────────────┐
                                      │ 检测服务（李东礼） │
                                      │                  │
                                      │ 危险区域闯入 ──────┤
                                      │ 积水检测    ──────┤
                                      │ 着火检测    ──────┤
                                      │ 摔倒检测    ──────┤
                                      └────────┬─────────┘
                                               │ results
                                               ▼
                                      ┌──────────────────┐
                                      │ draw_overlays()  │
                                      │ 标注框 + 区域     │
                                      └────────┬─────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐
                                      │ MJPEG 输出       │
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
| `backend/requirements.txt` | 依赖（已添加 opencv/numpy/pillow） | 修改 3 行 |

**总计**：新增 4 个文件，修改 3 个文件，约 500 行代码。

> **架构变更说明**：v1.0 基于 Flask 蓝图，v1.1 适配为 Django app，与 dev 分支统一架构。告警类型命名同步为 `INTRUSION`/`WATER`/`FIRE`/`FALL`，告警写入通过 `apps.alerts.services.create_alert()` 对接。

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
- HOG 行人检测在密集场景下可能漏检，可考虑后续升级为 YOLO 等深度学习方案

### 8.2 功能扩展

- 摔倒检测可结合关键点检测（如 MediaPipe Pose）提高准确率
- 着火检测可增加运动特征分析（火焰闪烁频率），减少静态红色物体误报
- 支持多摄像头流独立配置不同的检测阈值

### 8.3 性能优化

- 当前 HOG 行人检测每帧执行，若帧率较高可考虑跳帧策略
- 积水/着火检测可降低分辨率后执行，减少计算开销

---

*文档结束 — 变更请通知文档专员刘澎潮（F）。*
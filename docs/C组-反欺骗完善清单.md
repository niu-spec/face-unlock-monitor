# C 组 — 人脸反欺骗（活体检测）完善清单

> **负责人**：王梓铭（C 组）  
> **对照文档**：`docs/4_小学期任务清单.pdf` → 人脸识别可选项「防御静态图片、视频、AI 换脸等欺骗认证（8 分）」  
> **编写日期**：2026-07-10  
> **当前分支**：`dev`

---

## 一、现状说明

### 已实现（无需重做）

| 能力 | 位置 | 说明 |
|------|------|------|
| 被动活体检测服务 | `backend/apps/face/liveness.py` | 三类攻击：静态图 / 视频重放 / 纹理异常（AI 换脸） |
| 视频管线接入 | `backend/apps/video_stream/services.py` → `process_frame()` | 每帧在识别后调用 `get_liveness_service().observe()` |
| 告警类型 | `backend/apps/alerts/models.py` | `FACE_SPOOF` / `FACE_REPLAY` / `FACE_DEEPFAKE` |
| 告警中心筛选 | `frontend/src/views/AlertCenter.vue` | 已支持按攻击类型筛选、处置、忽略 |
| 单元测试 | `backend/apps/face/tests/test_services.py` | `LivenessDetectionServiceTests` 覆盖静态图场景 |

### 为何仍算「部分实现」

当前是 **OpenCV 启发式规则**（帧间运动、哈希重复、纹理统计），仅在 **MJPEG/RTSP 实时监控链路** 生效：

- 家人注册仍接受 **单张静态照片**，录入环节无活体校验
- 攻击告警 **不带截图**，告警中心无法回放
- 无对外 API、前端无活体状态展示
- WebRTC 预览不走 AI 管线，用户看不到检测结果
- 未实现 PDF 建议的 **主动动作挑战** 或 **Aurora Guard 光反射** 方案
- `FACE_AUTH_FAILED` 类型已定义但无检测逻辑

---

## 二、必改项（建议优先完成，答辩可演示）

### 任务 1：攻击告警附带截图

**问题**：`liveness.py` 的 `_persist_alert()` 调用 `create_alert()` 时未传 `frame`，导致告警无 `snapshot_path`，回放按钮灰色。

**改法**：

1. `LivenessDetectionService.observe()` 增加参数或内部保留最近一帧
2. `_persist_alert(event, household_id, frame=...)` 传入当前帧
3. 参考 `face/services.py` 中 `_persist_unknown_alert()` 的写法

**涉及文件**：

- `backend/apps/face/liveness.py`
- （可选）`backend/apps/face/tests/test_services.py` 补充 snapshot 断言

**验收**：用静态照片对摄像头欺骗 → 告警中心出现 `FACE_SPOOF` → 点击「回放」可见截图。

---

### 任务 2：家人注册增加多帧活体校验

**问题**：`POST /api/face/register/` 只接收单张图（`FaceRegisterView` + `FamilyRegister.vue`），攻击者可注册阶段就上传照片。

**改法（推荐最小方案）**：

**后端**

1. 新增注册模式：接受 **3～5 帧** 图片（multipart 多文件或 base64 数组）
2. 对每帧做人脸检测，取 `presence` 列表
3. 调用已有 `LivenessDetectionService.analyze_sequence(frames, presences)`
4. 若 `passed=False`，返回 400 + `attack_type` / `reason`，**拒绝入库**
5. 通过后仍用其中质量最好的一帧提取 128 维编码

**前端**（`frontend/src/views/FamilyRegister.vue` + `FaceCapture.vue`）

1. 注册时连续采集 3～5 帧（间隔约 200～300ms）
2. 提交前展示「活体检测中…」
3. 失败时提示「检测到疑似照片/视频欺骗，请真人面对摄像头重试」

**涉及文件**：

- `backend/apps/face/views.py` — `FaceRegisterView`
- `backend/apps/face/liveness.py` — 复用 `analyze_sequence`
- `frontend/src/views/FamilyRegister.vue`
- `frontend/src/components/FaceCapture.vue`
- `frontend/src/api/index.js` — `faceApi.register` 传多帧

**验收**：上传同一张静态图多次 → 注册失败；真人连续拍摄 → 注册成功。

---

### 任务 3：暴露活体检测 API

**问题**：`analyze_sequence()` 仅内部使用，Swagger 无接口，其他组无法联调。

**改法**：

新增 `POST /api/face/liveness/`（AllowAny 或 IsAuthenticated 与 analyze 保持一致）：

```json
// 请求：多帧 image[] + stream_id（可选）
// 响应
{
  "passed": true,
  "status": "passed",
  "attack_type": null,
  "score": 0.82,
  "reason": "连续帧存在自然变化，未发现明显欺骗特征",
  "details": { "motion_score": 0.05, "replay_score": 0.0, ... }
}
```

**涉及文件**：

- `backend/apps/face/views.py` — 新增 `FaceLivenessView`
- `backend/apps/face/urls.py`
- Swagger 注解

**验收**：Swagger `/api/docs/` 可调用；返回结构与单元测试一致。

---

### 任务 4：监控页展示活体状态

**问题**：用户在前端看不到是否通过活体；仅 `VIDEO_SHOW_HUD=1` 时 MJPEG 画面有调试文字。

**改法**：

1. 在 `get_face_service().process_frame()` 或 presence 快照中 **附带 liveness 摘要**（`status` / `attack_type` / `reason`）
2. 扩展 `GET /api/video/status` 或 `GET /api/home/presence/` 返回 `liveness` 字段
3. `HomeMonitor.vue` 增加状态 Tag，例如：
   - `passed` → 绿色「活体正常」
   - `insufficient` → 灰色「检测中…」
   - `attack` → 红色「疑似欺骗：静态照片」

**涉及文件**：

- `backend/apps/video_stream/services.py` — 将 liveness 写入 worker 状态
- `backend/apps/home/views.py`（或 video status 视图）
- `frontend/src/views/HomeMonitor.vue`

**验收**：监控页实时显示活体状态；静态图欺骗时变红并可在告警中心看到对应记录。

---

## 三、建议改项（提升稳定性，减少答辩翻车）

### 任务 5：检测阈值可配置

**问题**：motion / replay / texture 阈值写死在 `liveness.py`，不同摄像头、光照下调参困难。

**改法**：

在 `backend/config/settings.py` 增加 `LIVENESS_CONFIG` 字典，`LivenessDetectionService` 从 settings 读取：

```python
LIVENESS_CONFIG = {
    "window_size": 8,
    "min_samples": 4,
    "alert_cooldown": 30,
    "motion_threshold": 0.003,
    "box_motion_threshold": 0.004,
    "replay_threshold": 0.95,
    "texture_threshold": 0.9,
}
```

**验收**：改 settings 后行为变化，无需改业务代码。

---

### 任务 6：攻击时标记人脸不可信（可选但推荐）

**问题**：检测到 `FACE_SPOOF` 后，画面上仍可能显示绿色「家人」框。

**改法**：

1. `process_frame()` 中若 liveness 为 attack，在 `presence.faces` 上增加 `trusted: false`
2. `draw_face_boxes()` 对不可信人脸改 **橙色框** + 标签「疑似欺骗」
3. 可选：已知家人 + 攻击 → 发 `FACE_AUTH_FAILED` 而非仅攻击类型告警

**涉及文件**：

- `backend/apps/video_stream/services.py`
- `backend/apps/face/services.py` — `draw_face_boxes`

---

### 任务 7：补测试

**问题**：活体相关仅有 2 个单元测试，无注册拒绝、无 API 集成测试。

**建议补充**（`backend/apps/face/tests/`）：

| 用例 | 预期 |
|------|------|
| 静态帧序列 | `FACE_SPOOF` |
| 有规律运动帧序列 | `passed` |
| 注册接口提交静态多帧 | HTTP 400 |
| 攻击告警带 snapshot_path | 非空 |

CI 脚本 `scripts/ci-backend-test.sh` 已跑 face tests，新增用例会自动进 CI。

---

## 四、可选加分项（时间充裕再做）

PDF 可选 8 分提到可参考 **Aurora Guard（光反射）** + **随机动作序列**：

| 方案 | 工作量 | 说明 |
|------|--------|------|
| **主动动作挑战** | 中 | 注册/认证时随机「请眨眼 / 向左转头」，前端引导 + 后端校验头部姿态变化 |
| **Silent-Face-Anti-Spoofing 等开源模型** | 中高 | 替换或辅助现有启发式，显著降低误报漏报 |
| **Aurora Guard 光反射** | 高 | 需屏幕打光序列 + 反射分析，适合答辩 demo 但不强求 |

**建议**：先把第二节必改项做完，答辩演示「注册拦截 + 实时监控告警 + 截图回放」；若有余力再加「随机动作挑战」即可显著抬高可选分。

---

## 五、不在 C 组范围（知悉即可）

| 事项 | 负责 |
|------|------|
| WebRTC 流叠加 AI 框 | B 组（流媒体）或 A 组（前端 WebRTC 组件） |
| 告警中心筛选/忽略 UI | A 组（已完成） |
| OpenSpec 联调任务 4.1/4.2（OBS 推流 E2E） | B + C + D 联调 |

C 组只需保证 **MJPEG 链路**（`/video_feed/{id}`）上活体与告警闭环可演示。

---

## 六、推荐实施顺序

```
任务 1（告警截图）  →  1～2 小时，立刻改善演示效果
    ↓
任务 3（liveness API） →  便于前后端并行
    ↓
任务 2（注册活体）  →  核心缺口，答辩重点
    ↓
任务 4（监控页状态） →  用户可见
    ↓
任务 5～7（配置 / 画框 / 测试）→  打磨
```

---

## 七、验收清单（C 组自测 + 联调）

- [ ] 静态照片对摄像头 → 10 秒内产生 `FACE_SPOOF` 告警
- [ ] 该告警可在告警中心筛选、处置，且 **回放有截图**
- [ ] 用手机播放人脸视频 → 可产生 `FACE_REPLAY`（或至少不误判为 passed）
- [ ] 注册时提交同一张图多次 → **拒绝注册**
- [ ] 真人面对摄像头连续采集 → **注册成功**
- [ ] Swagger 存在 `POST /api/face/liveness/` 且文档完整
- [ ] 监控页显示活体状态（正常 / 检测中 / 疑似欺骗）
- [ ] `python manage.py test apps.face` 全部通过
- [ ] 推 `feature/face` → GitHub Actions CI 绿

---

## 八、相关代码索引

| 文件 | 作用 |
|------|------|
| `backend/apps/face/liveness.py` | 活体检测核心（**主要改动点**） |
| `backend/apps/face/services.py` | 人脸识别、注册、画框 |
| `backend/apps/face/views.py` | 注册 / 分析 API（**新增 liveness API**） |
| `backend/apps/face/urls.py` | 路由 |
| `backend/apps/video_stream/services.py` | 视频 AI 处理链 |
| `frontend/src/views/FamilyRegister.vue` | 家人注册页 |
| `frontend/src/components/FaceCapture.vue` | 摄像头采集 |
| `frontend/src/views/HomeMonitor.vue` | 监控主页 |
| `openspec/changes/ai-video-integration/tasks.md` | OpenSpec 任务（§2 人脸识别） |

---

## 九、分支与协作

- 开发分支：`feature/face`
- 合并目标：`dev`
- 改 API 契约后请在群里 @ E 组（刘帅华）确认 Swagger 与前端联调
- 改 `process_frame` 入参/出参请 @ D 组（李东礼）确认检测链不受影响

---

**有问题联系**：A 组 牛雨昊（Git / 联调协调）

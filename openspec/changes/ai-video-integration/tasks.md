## 1. 接口契约（C/D 共用）

- [ ] 1.1 在 `process_frame()` 实现处理器链注册机制
- [ ] 1.2 定义 face/detection 模块输入输出格式（frame + events）

## 2. C — 人脸识别（王梓铭）

- [ ] 2.1 接入 dlib 人脸检测与 128 维编码比对
- [ ] 2.2 实现 `/api/face/register/` 与家人库持久化
- [ ] 2.3 更新 `/api/home/presence/` 人数统计
- [ ] 2.4 陌生人触发 `FACE_UNKNOWN` 告警

## 3. D — 异常检测（李东礼）

- [ ] 3.1 HOG 行人检测用于区域闯入判断
- [ ] 3.2 厨房禁区 + child 角色 → `INTRUSION`
- [ ] 3.3 积水/着火/跌倒检测 → `WATER`/`FIRE`/`FALL`

## 4. 联调验证

- [ ] 4.1 OBS 推流时 MJPEG 画面含 AI 标注框
- [ ] 4.2 告警中心可见对应类型告警

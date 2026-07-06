# home-camera-monitor

Smart home camera monitoring system with RTMP streaming, Flask AI backend, and dlib face recognition — family identification, person counting, stranger alerts, danger zones, and emergency detection.

## 应用场景

**居家智能摄像头监控**：通过家庭摄像头实时分析家中画面，识别家庭成员、统计当前在家人数、检测陌生人；支持设定危险区域（如厨房禁止小孩进入）；对积水、着火、人员摔倒等异常情况进行识别并告警。

## 核心功能

| 模块 | 功能 |
|------|------|
| 人脸识别 | 家庭成员注册与识别、陌生人告警 |
| 人员统计 | 实时统计画面/家中人数、熟人/陌生人数量 |
| 危险区域 | 前端画框配置禁区（如厨房），小孩进入即告警 |
| 异常检测 | 积水、着火、人员摔倒（≥2 种，满足课程验收） |
| 告警中心 | 事件展示、处置、日志与回放 |

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + Element Plus |
| 后端 | Flask + Blueprint |
| AI | OpenCV + dlib + face_recognition |
| 数据库 | MySQL |
| 流媒体 | Nginx-RTMP |
| 部署 | gunicorn + Nginx 反代 |

## 项目结构

```
home-camera-monitor/
├── frontend/          # Vue3 前端
├── backend/           # Flask 后端（AI + 业务 API）
├── nginx/             # Nginx-RTMP 配置
├── deploy/            # 部署脚本
├── docs/              # 项目文档
└── scripts/           # 工具脚本
```

## 快速开始

### 后端

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python app.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 推流地址

```
推流：rtmp://{服务器IP}:9090/live/1
观看：http://{服务器IP}/video_feed/1
```

## 文档

- [总体架构说明](docs/总体架构说明.md)
- [项目任务分工表](docs/项目任务分工表.pdf)

## 团队

见 [CONTRIBUTORS.md](CONTRIBUTORS.md)

## License

MIT

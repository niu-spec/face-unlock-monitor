# face-unlock-monitor

Smart door access system with RTMP video streaming, Flask AI backend, and dlib face recognition — unlock, stranger alert, and zone intrusion detection.

## 应用场景

**人脸识别开锁（智慧门禁）**：已注册用户刷脸通过自动开锁；陌生人拒绝开锁并告警；支持门禁区域闯入、尾随、徘徊检测。

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
face-unlock-monitor/
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

# Backend (Django)

See [docs/开发指南/DEV_SETUP.md](../docs/开发指南/DEV_SETUP.md) for the full local dev guide.

## Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| Python | **3.10** | dlib cannot be pip-installed on Windows with 3.11+ |
| dlib | 19.24.6 | Install via conda-forge (`environment.yml`) |
| MySQL | 8.x / 9.x | Credentials via env vars |

> Do **not** use `python -m venv` + pip for dlib on Windows. Use conda env `home-camera`.

## Quick start (Windows)

```powershell
# from project root
.\scripts\setup_backend.ps1
.\scripts\start_backend.ps1
```

Or manually:

```powershell
conda activate home-camera
cd backend
$env:DB_PASSWORD = "your_password"
python manage.py migrate
python manage.py runserver 8000
```

- Swagger: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

## Conda environment

```powershell
cd backend
conda env create -f environment.yml   # first time
conda env update -f environment.yml   # update
```

## Verify face recognition

```powershell
python -c "import dlib, face_recognition; print(dlib.__version__, 'OK')"
python manage.py test apps.face.tests
```

Model files (`.dat`) come from `face-recognition-models` (not in Git). See [dat/README.md](dat/README.md).

## Environment variables

Copy [.env.example](.env.example) and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `127.0.0.1` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | `Root@1234` | MySQL password |
| `DB_NAME` | `home_camera_monitor` | Database name |
| `DJANGO_SECRET_KEY` | dev key in settings | Change in production |
| `DJANGO_DEBUG` | `True` | Set `False` in production |

## Linux (server)

Use the same `environment.yml` or install dlib via conda-forge, then:

```bash
pip install -r requirements.txt
# 生产环境使用 deploy/start_backend.sh（gunicorn workers=1 threads=16 bind 127.0.0.1:8010）
bash deploy/start_backend.sh
```

Deploy script: [deploy/deploy-all.sh](../deploy/deploy-all.sh)

## Video & AI endpoints

| Path | Description |
|------|-------------|
| `GET /video_feed/{id}` | MJPEG 备用流（`process_frame()` 烧录 AI 标注） |
| `GET /api/video/status/` | Worker 状态 + overlay 快照 |
| `GET /api/video/presence/?stream_id=` | 前端 FaceOverlay 轮询数据源 |
| `GET /api/home/presence/` | 人数统计（legacy/fallback） |

视频处理由 `apps/video_stream/services.py` 的 `CameraWorker` 完成（采集/AI 分线程，`frame.copy()` 防并发）。

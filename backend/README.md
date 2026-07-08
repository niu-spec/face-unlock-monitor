# Backend (Django)

See [docs/DEV_SETUP.md](../docs/DEV_SETUP.md) for the full local dev guide.

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
gunicorn -w 2 -b 0.0.0.0:8000 config.wsgi:application
```

Deploy script: [deploy/deploy-django.sh](../deploy/deploy-django.sh)

# Frontend (Vue3 + Vite)

REST client for the Django backend. See [docs/开发指南/DEV_SETUP.md](../docs/开发指南/DEV_SETUP.md) for full setup.

## Dev server

```bash
npm install
npm run dev
```

Or from project root: `.\scripts\start_frontend.ps1`

Default: http://localhost:5173/

Vite proxies `/api` and `/video_feed` to Django at `http://localhost:8000` (see `vite.config.js`).

## Environment

Copy `.env.development.example` to `.env.development`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_TARGET` | `http://localhost:8000` | API proxy target |
| `VITE_VIDEO_FEED_TARGET` | same as API | Video feed proxy (can point to cloud MediaMTX) |

## Routes

| Path | Page |
|------|------|
| `/login` | Login |
| `/register` | Register |
| `/monitor` | Home monitor (live feed + person stats) |
| `/family` | Family face registration |
| `/zones` | Danger zone editor |
| `/alerts` | Alert center |
| `/events` | Event log |
| `/users` | User hub |
| `/households` | Household management |
| `/profile` | Profile (phone binding) |

## API client

- Axios wrapper: `src/api/request.js`
- Auto headers: `Authorization: Bearer <token>`, `X-Active-Household-Id`
- Stream ID mapping: `src/constants/streams.js` (video `1`/`2` ↔ business `living_room`/`kitchen`)

## Structure

```
src/
├── api/           # Axios + API modules
├── components/    # Shared components
├── constants/     # Stream ID mapping
├── views/         # Pages
└── router/        # Vue Router
```

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

**监控页主预览**使用 WebRTC（MediaMTX :8889），AI 标注通过 `/api/video/presence/` 获取后在 `FaceOverlay.vue` Canvas 上叠加，不依赖 MJPEG `<img>`。

## Environment

Copy `.env.development.example` → `.env.development`（本地），或 `.env.production.example` → `.env.production`（构建）：

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_TARGET` | `http://localhost:8000` | Dev only: API proxy target |
| `VITE_VIDEO_FEED_TARGET` | same as API | Dev only: MJPEG fallback proxy |
| `VITE_WEBRTC_BASE_URL` | `http://127.0.0.1:8889` | MediaMTX WebRTC base（生产改成公网主机或 `/webrtc`） |

## Routes

| Path | Page |
|------|------|
| `/login` | Login |
| `/register` | Register |
| `/monitor` | Home monitor — WebRTC iframe + FaceOverlay + PersonStats |
| `/family` | Family face registration (multi-frame liveness) |
| `/zones` | Danger zone editor — WebRTC + FaceOverlay + canvas polygon |
| `/alerts` | Alert center |
| `/events` | Event log |
| `/reports` | AI daily report |
| `/users` | User hub |
| `/households` | Household management |
| `/profile` | Profile (phone binding) |
| `/settings/notifications` | DingTalk notification settings |

## API client

- Axios wrapper: `src/api/request.js`
- Auto headers: `Authorization: Bearer <token>`, `X-Active-Household-Id`
- Stream ID mapping: `src/constants/streams.js` (video `1`/`2` ↔ business `living_room`/`kitchen`)
- Video overlay: `videoApi.presence()` / `videoApi.status()` — polled every 200ms on monitor/zone pages
- WebRTC URL: `webrtcPreviewUrl()` in `src/constants/streams.js`

## Structure

```
src/
├── api/           # Axios + API modules
├── components/    # FaceOverlay, PersonStats, FaceCapture, EventReplayDialog
├── constants/     # Stream ID mapping + WebRTC URL helpers
├── views/         # Pages (HomeMonitor, ZoneEditor, AlertCenter, …)
└── router/        # Vue Router
```

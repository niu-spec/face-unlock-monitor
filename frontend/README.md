# 居家监控前端

Vue3 + Vite + Element Plus 单页应用，通过 REST API 与 Django 业务后端联调。

## 开发

```bash
npm install
npm run dev
```

默认地址：http://localhost:5173/

开发模式下，`/api` 与 `/video_feed` 请求由 Vite 代理到 `http://localhost:8000`（Django）。

## 页面路由

| 路径 | 页面 |
|------|------|
| `/login` | 登录 |
| `/monitor` | 居家监控（实时画面 + 人数统计） |
| `/family` | 家人人脸录入 |
| `/zones` | 危险区域画框 |
| `/alerts` | 告警中心 |
| `/events` | 事件记录 |
| `/users` | 用户管理（账户概览，跳转个人信息/家庭管理） |
| `/households` | 家庭管理 |
| `/profile` | 个人信息（换绑手机号） |

## 目录结构

```
src/
├── api/           # Axios 封装与接口定义
├── components/    # 公共组件（如 PersonStats）
├── views/         # 页面
└── router/        # 路由配置
```

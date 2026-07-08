# GitLab CI/CD 使用说明

> **项目**：home-camera-monitor  
> **负责人**：A 牛雨昊  
> **配置文件**：`.gitlab-ci.yml`（项目根目录）  
> **GitHub 仓库**：https://github.com/niu-spec/home-camera-monitor

---

## 1. 概述

本项目使用 **GitLab CI/CD** 实现持续集成与部署，满足课程「项目基础建设 — CI/CD（选做 4 分）」要求。

| 阶段 | Job | 做什么 |
|------|-----|--------|
| test | `backend-test` | Django check + 人脸模块单元测试 |
| build | `frontend-build` | `npm run build` 验证前端可编译 |
| deploy | `deploy-production` | 手动触发，SSH 部署到云服务器（仅 `main`） |

**触发条件**：push 到 `dev` / `main` / `feature/*` 分支，或创建 Merge Request 时自动运行。

---

## 2. 一次性初始化（组长操作）

### 2.1 创建 GitLab 项目并导入 GitHub 仓库

1. 登录 [gitlab.com](https://gitlab.com)（或用学校 GitLab）
2. **New project** → **Import project** → **GitHub**
3. 授权后选择 `niu-spec/home-camera-monitor`
4. 可见性选 **Private** 或 **Internal**
5. 点击 **Import**

导入完成后，GitLab 地址类似：
`https://gitlab.com/你的用户名/home-camera-monitor`

### 2.2 配置 GitHub → GitLab 自动同步（推荐）

在 GitLab 项目中：

1. **Settings** → **Repository** → **Mirroring repositories**
2. **Git repository URL**：`https://github.com/niu-spec/home-camera-monitor.git`
3. 勾选 **Mirror direction**: Pull
4. 填入 GitHub Personal Access Token（需 `repo` 权限）
5. 保存后点 **Update now** 立即同步

之后每次 GitHub push，可手动或定时 Pull 到 GitLab。

**或** 在本地添加 GitLab 远程并双推：

```bash
git remote add gitlab https://gitlab.com/你的用户名/home-camera-monitor.git
git push gitlab dev
git push gitlab main
```

### 2.3 配置部署变量（CD 阶段，可选）

**Settings** → **CI/CD** → **Variables** → **Add variable**：

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `SSH_PRIVATE_KEY` | Variable（Masked） | 云服务器 SSH 私钥全文 |
| `DEPLOY_HOST` | Variable | 服务器 IP，如 `152.136.29.158` |
| `DEPLOY_USER` | Variable | SSH 用户，如 `root` |

未配置时，`backend-test` 和 `frontend-build` 仍可正常运行；仅 `deploy-production` 需要上述变量。

### 2.4 开启 Shared Runners

**Settings** → **CI/CD** → **Runners** → 确认 **Shared runners** 已启用（gitlab.com 免费账户默认有）。

---

## 3. 组员日常使用

### 3.1 开发流程（不变）

```bash
git checkout dev
git pull origin dev
git checkout -b feature/face
# ... 写代码 ...
git add .
git commit -m "feat(face): xxx"
git push origin feature/face
```

### 3.2 触发 CI

**方式 A**：GitHub 同步到 GitLab 后，在 GitLab 项目页 → **Build** → **Pipelines** 查看

**方式 B**：直接推送到 GitLab：

```bash
git push gitlab feature/face
```

### 3.3 查看 Pipeline 结果

1. 打开 GitLab 项目
2. 左侧 **Build** → **Pipelines**
3. 绿色 ✓ = 通过，红色 ✗ = 失败，点进去看 Job 日志

### 3.4 Merge Request 自动检查

在 GitLab 创建 MR（`feature/face` → `dev`）时，Pipeline 会自动跑，MR 页面显示通过/失败状态。

---

## 4. Pipeline 详情

### backend-test

- 镜像：`python:3.10-bookworm`
- 依赖：`backend/requirements-ci.txt`（不含 dlib，CI 环境无法编译）
- 步骤：
  1. `python manage.py check --deploy`
  2. `python manage.py test apps.face.tests`
- 数据库：CI 环境自动使用 SQLite（`settings.py` 中 `CI=true` 时切换）

### frontend-build

- 镜像：`node:20-bookworm`
- 步骤：`npm ci` → `npm run build`
- 产物：`frontend/dist/`（保留 1 周，可下载）

### deploy-production

- 仅 `main` 分支
- **手动触发**（Pipeline 页面点 ▶️ Play）
- SSH 到服务器执行 `deploy/deploy-django.sh`

---

## 5. 结题验收材料

| 材料 | 获取方式 |
|------|----------|
| Pipeline 配置 | 截图 `.gitlab-ci.yml` 或 GitLab CI/CD → Editor |
| 成功运行记录 | GitLab → Pipelines → 绿色 Pipeline 详情截图 |
| 组员都会使用 | 晨会演示：push → 看 Pipeline 结果 |
| 本文档 | `docs/CI-CD使用说明.md` |

建议截图保存到 `docs/验收材料/CI-CD/` 目录。

---

## 6. 常见问题

### Q：Pipeline 失败，backend-test 报 face_recognition 错误？

`requirements-ci.txt` 已排除 dlib。若仍报错，确认测试使用了 mock（`apps.face.tests` 已 mock `_load_face_recognition`）。

### Q：只有 GitHub，没有推 GitLab，Pipeline 会跑吗？

不会。必须在 GitLab 有仓库且 push/同步后才会触发。见 §2.1、§2.2。

### Q：deploy 阶段怎么手动触发？

Pipelines 页面 → 找到 `main` 分支的 Pipeline → `deploy-production` 右侧点 **Play**。

### Q：feature 分支会跑 CI 吗？

会。`feature/*` 分支 push 后自动触发 `backend-test` 和 `frontend-build`。

---

## 7. 与 OpenSpec / Swagger 的关系

| 基础建设项 | 对应实现 |
|-----------|----------|
| 代码管理（GitHub） | `CONTRIBUTORS.md` + 分支规范 |
| OpenSpec | `openspec/` + `docs/OpenSpec使用说明.md` |
| Swagger | `http://localhost:8000/api/docs/` |
| **CI/CD** | **本文件 + `.gitlab-ci.yml`** |

---

*文档维护：修改 Pipeline 时请同步更新本文档。*

# CI/CD 使用说明

> **项目**：home-camera-monitor  
> **负责人**：A 牛雨昊  
> **GitHub 仓库**：https://github.com/niu-spec/home-camera-monitor  
> **云服务器**：152.136.29.158

---

## 0. 当前方案（2026-07-10 更新）

| 方案 | 角色 | 说明 |
|------|------|------|
| **Jenkins**（主用，结题材料） | 云服务器 `:8080` | 符合评分表「Jenkins/GitLab」，**全员浏览器可用** |
| **GitHub Actions**（辅用） | GitHub 仓库 | push 即跑 test/build，零额外注册 |
| ~~GitLab CI~~ | 已弃用 | gitlab.com 需身份验证，组员无法全员使用 |

**为什么不用 GitLab：** gitlab.com 注册需手机/身份验证，组员过不了；且日常只推 GitHub，Pipeline 不会自动跑。

**日常开发：** 只推 GitHub 即可，CI 自动触发。

```bash
git push origin feature/xxx
# → GitHub Actions 自动跑 CI
# → Jenkins（配好 Webhook 后）自动跑 Pipeline
```

---

## 1. 组员日常使用

### 1.1 开发流程

```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-module
# ... 写代码 ...
git add .
git commit -m "feat(module): your change"
git push origin feature/your-module
```

### 1.2 查看 CI 结果

**方式 A — GitHub Actions（推荐，零门槛）**

1. 打开 https://github.com/niu-spec/home-camera-monitor/actions
2. 找到你的 commit 对应的 workflow run
3. 绿色 ✓ = 通过，红色 ✗ = 失败，点进去看日志

**方式 B — Jenkins（结题演示用）**

1. 浏览器打开 `http://152.136.29.158:8080`
2. 登录 Jenkins 账号（组长分配）
3. 进入 **home-camera-monitor** 任务 → 查看构建历史

### 1.3 合并到 dev

```bash
# 在 GitHub 创建 Pull Request：feature/xxx → dev
# PR 页面会显示 GitHub Actions 检查结果
# 合并后 Jenkins 也会触发（若 Webhook 已配置）
```

### 1.4 手动部署（仅组长 / B 组）

Jenkins Pipeline 的 **Deploy Production** 阶段需手动确认：

1. Jenkins → 最新构建 → 等待 test/build 通过
2. 出现 **Deploy to production server?** → 点 **Deploy**
3. 或在服务器 SSH 手动执行：

```bash
cd /service/home-camera-monitor
DEPLOY_BRANCH=dev bash deploy/deploy-all.sh
```

---

## 2. Pipeline 详情

### backend-test

- 脚本：`scripts/ci-backend-test.sh`
- Python 3.10 + `backend/requirements-ci.txt`（不含 dlib，避免 CI 编译失败）
- 步骤：
  1. `python manage.py check`
  2. `python manage.py test` — face / detection / video_stream / reports
- 数据库：CI 环境自动使用 SQLite（`settings.py` 中 `CI=true` 时切换）

### frontend-build

- 脚本：`scripts/ci-frontend-build.sh`
- Node.js 20 → `npm ci` → `npm run build`
- 产物：`frontend/dist/`

### deploy-production（Jenkins 手动触发）

- 仅 `dev` / `main` 分支
- Deploy 前将 `/service/home-camera-monitor` 重置为 **当前构建 commit**（与 CI 测试一致）
- 执行 `deploy/deploy-all.sh`：migrate → 重启 backend → npm build → reload nginx（**默认不重启 MediaMTX**）
- Jenkins 环境变量 `DEPLOY_MEDIAMTX=0`；仅手动 `DEPLOY_MEDIAMTX=1` 时重建 `home-mediamtx`
- Jenkins 用户需配置 docker 组 + 代码目录写权限 + `deploy/jenkins.sudoers.example`（见 Jenkins 安装指引 §6）

---

## 3. 配置文件一览

| 文件 | 用途 |
|------|------|
| `Jenkinsfile` | Jenkins Pipeline 定义（主 CI/CD） |
| `.github/workflows/ci.yml` | GitHub Actions（辅 CI） |
| `scripts/ci-backend-test.sh` | 后端测试（Jenkins / Actions 共用） |
| `scripts/ci-frontend-build.sh` | 前端构建（Jenkins / Actions 共用） |
| `deploy/deploy-all.sh` | 生产部署入口 |

---

## 4. Jenkins 安装（B 组一次性操作）

详见 **[B组-Jenkins安装指引.md](../B组-Jenkins安装指引.md)**。

概要：

1. SSH 登录 `152.136.29.158`
2. 运行 `deploy/install_jenkins.sh`（或按文档手动安装）
3. 浏览器访问 `http://152.136.29.158:8080` 完成初始化
4. 新建 Pipeline 任务，SCM 指向 GitHub `dev` 分支，Script Path = `Jenkinsfile`
5. 配置 GitHub Webhook（push 自动触发）
6. 给 6 名组员各建 Jenkins 账号

---

## 5. 结题验收材料

| 材料 | 获取方式 |
|------|----------|
| Pipeline 配置 | 截图 `Jenkinsfile` + Jenkins 任务配置页 |
| 成功运行记录 | Jenkins 构建历史绿色截图 + GitHub Actions 绿色截图 |
| 组员都会使用 | 晨会演示：每人 push 一次 → 两处 CI 均出现构建记录 |
| 部署记录 | Jenkins Deploy 阶段截图 或 服务器 deploy 日志 |
| 本文档 | `docs/部署运维/CI-CD使用说明.md` |

建议截图保存到 `docs/验收材料/CI-CD/` 目录。

---

## 6. 常见问题

### Q：只推 GitHub，CI 会跑吗？

会。GitHub Actions 自动触发；Jenkins 需 B 组配好 Webhook（见 Jenkins 安装指引）。

### Q：GitLab 还要用吗？

不用。已移除 `.gitlab-ci.yml`，日常只推 GitHub 即可。

### Q：Pipeline 失败，backend-test 报 face_recognition 错误？

`requirements-ci.txt` 已排除 dlib。确认测试使用了 mock（`apps.face.tests` 已 mock `_load_face_recognition`）。

### Q：Jenkins 构建失败，找不到 node / python3？

B 组需在服务器安装 Node.js 20 和 Python 3.10+（见 Jenkins 安装指引 §2）。

### Q：deploy 阶段怎么触发？

Jenkins 构建到 Deploy 阶段时会暂停等待确认，点 **Deploy** 即可。不要在 feature 分支 deploy。

### Q：GitHub Actions 算 CI/CD 加分吗？

评分表写「Jenkins/GitLab」。GitHub Actions 作为辅助；**结题以 Jenkins 截图为主**，Actions 作补充。

---

## 7. 与 OpenSpec / Swagger 的关系

| 基础建设项 | 对应实现 |
|-----------|----------|
| 代码管理（GitHub） | `CONTRIBUTORS.md` + 分支规范 |
| OpenSpec | `openspec/` + `docs/项目管理/OpenSpec/OpenSpec使用说明.md` |
| Swagger | `http://152.136.29.158/api/docs/` |
| **CI/CD** | **Jenkins** + GitHub Actions |

---

*文档维护：修改 CI 配置时请同步更新本文档。*

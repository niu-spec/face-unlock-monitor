# B 组 — CD 落地任务清单

> **负责人**：苏哲勋（B 组）  
> **协作**：A 组 牛雨昊（Jenkins 账号 / 结题截图）  
> **服务器**：152.136.29.158  
> **代码仓库**：https://github.com/niu-spec/home-camera-monitor（`dev` 分支）  
> **日期**：2026-07-10

---

## 背景

A 组已根据 B 组反馈（`B组-CD落地反馈.md`）二次修复，详见 **`A组回复-B组CD阻塞修复.md`**：

- `DEPLOY_MEDIAMTX=0`（默认跳过 MediaMTX，不重启 `home-mediamtx`）
- Jenkins Deploy 改用 ff-only / checkout tracked，**保留** `.env.production` 等未跟踪文件
- sudoers / nginx 路径适配宝塔

**你需要做的**：pull 最新 `dev` → 配置权限 → **跑通 Deploy** → 留截图。

---

## 任务总览

| # | 任务 | 优先级 | 预计耗时 |
|---|------|--------|---------|
| 1 | Pull 最新 `dev` | P0 | 5 min |
| 2 | 配置 Jenkins 用户权限（目录 + docker + sudoers） | P0 | 20 min |
| 3 | 验证 Jenkins Pipeline（test/build） | P0 | 10 min |
| 4 | 验证 Deploy 阶段端到端 | P0 | 15 min |
| 5 | 确认 GitHub Webhook / pollSCM | P1 | 10 min |
| 6 | 整理结题截图交给 A 组 | P1 | 15 min |

---

## 任务 1：Pull 最新代码

SSH 登录服务器：

```bash
ssh root@152.136.29.158   # 或你的常用账号
cd /service/home-camera-monitor
git fetch origin dev
git merge --ff-only origin/dev
git log -1 --oneline
grep "skip MediaMTX" deploy/deploy-all.sh
```

确认最新 commit 包含：

- `deploy/deploy-all.sh` 中 `DEPLOY_MEDIAMTX` 默认跳过 MediaMTX
- `Jenkinsfile` 中 `DEPLOY_MEDIAMTX=0`

---

## 任务 2：配置 Jenkins 用户权限（一次性）

### 2.1 代码目录写权限

Deploy 会更新 **tracked 文件**，**不会删除** `.env.production`、`yolov8n.pt`、`mysql8-data/`（见 `生产目录文件策略.md`），jenkins 用户需可写：

```bash
sudo chown -R jenkins:jenkins /service/home-camera-monitor
```

> 若 conda 环境路径也在该目录下，改属主后确认 `conda activate home-camera` 仍正常。

### 2.2 Docker 组

```bash
sudo usermod -aG docker jenkins
```

### 2.3 sudoers（systemctl + nginx）

```bash
cd /service/home-camera-monitor
sudo cp deploy/jenkins.sudoers.example /etc/sudoers.d/jenkins-deploy
sudo chmod 440 /etc/sudoers.d/jenkins-deploy
sudo visudo -cf /etc/sudoers.d/jenkins-deploy
```

期望输出：`parsed OK`

### 2.4 重启 Jenkins

```bash
sudo systemctl restart jenkins
sudo systemctl status jenkins --no-pager
```

### 2.5 快速自检（可选，推荐）

```bash
sudo -u jenkins -H bash -lc '
  cd /service/home-camera-monitor
  DEPLOY_USE_SUDO=auto DEPLOY_MEDIAMTX=0 SKIP_GIT_UPDATE=1 bash deploy/deploy-all.sh
'
```

期望输出含 `[deploy] skip MediaMTX` 和 `[deploy] completed`，且 **home-mediamtx 容器未被重建**。

---

## 任务 3：验证 Jenkins CI（test + build）

1. 浏览器打开：**http://152.136.29.158:8080**
2. 进入任务 **home-camera-monitor**
3. 点击 **Build Now**（或 push 到 `dev` 触发）
4. 等待 **Backend Test**、**Frontend Build** 两阶段绿色通过

**若失败**：

| 报错 | 处理 |
|------|------|
| `npm: command not found` | 安装 Node.js 20（见 `docs/B组-Jenkins安装指引.md` §2） |
| `python3: command not found` | `sudo apt install -y python3 python3-venv python3-pip` |
| backend-test 失败 | 点进日志看具体 test，群里 @ 对应模块负责人 |

---

## 任务 4：验证 Deploy 阶段（CD 核心）

> 仅 `dev` / `main` 分支构建会出现 Deploy 阶段；feature 分支不会。

1. 在 **dev** 分支触发一次构建（push 空 commit 或 Build Now）
2. test/build 通过后，Pipeline 在 **Deploy Production** 暂停
3. 点击 **Deploy to production server?** → **Deploy**
4. 查看 Console Output，确认：

```
[deploy] restart home-camera-backend
[deploy] skip MediaMTX
[deploy] reload nginx
[deploy] completed
```

5. 浏览器验证生产环境：

| 检查项 | URL | 期望 |
|--------|-----|------|
| 前端首页 | http://152.136.29.158/ | 正常打开 |
| Swagger | http://152.136.29.158/api/docs/ | 200 |
| MJPEG | http://152.136.29.158/video_feed/1 | 有画面或占位 |
| WebRTC | http://152.136.29.158:8889/ | MediaMTX 正常 |

**若 Deploy 失败**：

| 报错 | 处理 |
|------|------|
| `Permission denied` (systemctl) | 重做任务 2.3 sudoers |
| `sudo: a password is required` | sudoers 未生效或路径不对 |
| `working tree has local changes` | `cd /service/home-camera-monitor && git status`，stash 或 reset |
| `missing env file: .env.production` | 确认 `backend/.env.production` 存在 |
| docker 权限错误 | 确认 jenkins 在 docker 组并重启 jenkins |

---

## 任务 5：Webhook 与自动触发

### 5.1 检查 GitHub Webhook

GitHub 仓库 → **Settings → Webhooks**：

- Payload URL：`http://152.136.29.158:8080/github-webhook/`
- Recent Deliveries 应为绿色 ✓

若 Webhook 失败（GitHub 无法访问 8080）：

- 腾讯云安全组放行 **TCP 8080**
- 或暂时依赖 `Jenkinsfile` 内 **pollSCM**（每 5 分钟检查，有延迟）

### 5.2 Jenkins 任务配置确认

| 配置项 | 值 |
|--------|-----|
| Pipeline script from SCM | ✓ |
| Repository | `https://github.com/niu-spec/home-camera-monitor.git` |
| Branch | `*/dev` |
| Script Path | `Jenkinsfile` |
| GitHub hook trigger | ✓ 勾选 |

---

## 任务 6：结题材料（交给 A 组）

请截图保存（可放 `docs/验收材料/CI-CD/`，或发群文件）：

- [ ] Jenkins 任务配置页（Pipeline from SCM）
- [ ] 一次完整构建：**Backend Test + Frontend Build 绿色**
- [ ] **Deploy Production** 确认框 + Deploy 成功后日志（含 `[deploy] completed`）
- [ ] GitHub Webhook 交付成功记录（或注明使用 pollSCM）
- [ ] 浏览器访问生产站点正常

反馈模板（发群 @牛雨昊）：

```
B 组 CD 落地反馈
- Jenkins: http://152.136.29.158:8080 正常
- 最新构建: #___ 绿色（test + build + deploy）
- Webhook: 已配置 / 使用 pollSCM
- 生产验证: 首页 + Swagger + 推流 正常
- 截图: 已发群 / 已提交 docs/验收材料/CI-CD/
```

---

## 附录：日常运维命令

### 手动部署（不经过 Jenkins）

```bash
cd /service/home-camera-monitor
git fetch origin dev && git reset --hard origin/dev
DEPLOY_BRANCH=dev bash deploy/deploy-all.sh
```

### 查看服务状态

```bash
systemctl status home-camera-backend --no-pager
docker ps | grep home-mediamtx
ss -lntp | grep -E '8010|9090|8554|8889|8080'
```

### 相关文档

| 文档 | 说明 |
|------|------|
| [B组-Jenkins安装指引.md](../B组-Jenkins安装指引.md) | Jenkins 安装与插件 |
| [B组-云部署与联调指引.md](../B组-云部署与联调指引.md) | 生产拓扑与 Nginx |
| [CI-CD使用说明.md](../CI-CD使用说明.md) | 全员使用说明 |
| [deploy/README.md](../../deploy/README.md) | 部署脚本与环境变量 |

---

*完成以上 P0 任务后，CD 部分即可视为结题就绪。*

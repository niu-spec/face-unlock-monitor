# A 组回复 B 组 — CD 阻塞项已修复

> **日期**：2026-07-10  
> **对应反馈**：`docs/部署运维/记录/B组-CD落地反馈.md`  
> **dev commit**：待 push 后填写

---

## 已修复项

### P0-1：默认跳过 MediaMTX ✅

- `deploy/deploy-all.sh`：`DEPLOY_MEDIAMTX` 默认 `0`，仅 `=1` 时执行 `mediamtx_run.sh`
- 日志明确输出：`[deploy] skip MediaMTX (set DEPLOY_MEDIAMTX=1 to restart home-mediamtx)`
- `Jenkinsfile` 环境变量：`DEPLOY_MEDIAMTX=0`

### P0-2：生产未跟踪文件策略 ✅

见 **`docs/部署运维/记录/生产目录文件策略.md`**：

| 文件 | 处理 |
|------|------|
| `.env.production` | 保留本地，已加入 `.gitignore` |
| `yolov8n.pt` | 保留本地，已加入 `.gitignore` |
| `mysql8-data/` | 保留本地，已加入 `.gitignore`，建议日后迁出 |
| `deploy/start_backend.sh` | 仓库已有，Deploy 同步 tracked 版本 |

Jenkins Deploy **不再** `git reset --hard`，改为 ff-only merge 或仅 checkout tracked 文件。

### P1-2：sudoers Nginx 路径 ✅

`deploy/jenkins.sudoers.example` 已补充：

- `/usr/bin/nginx`
- `/usr/sbin/nginx`
- `/www/server/nginx/sbin/nginx`（宝塔）
- `/etc/init.d/nginx`

`deploy/deploy-lib.sh` 会自动探测 nginx 路径，支持宝塔 reload。

---

## B 组下一步（请按序执行）

### 1. Pull 最新 dev

```bash
cd /service/home-camera-monitor
git fetch origin dev
git merge --ff-only origin/dev
grep -n "skip MediaMTX" deploy/deploy-all.sh   # 确认修复已到位
```

### 2. 配置 Jenkins 权限（本轮可执行）

```bash
sudo chown -R jenkins:jenkins /service/home-camera-monitor
sudo usermod -aG docker jenkins

sudo cp deploy/jenkins.sudoers.example /etc/sudoers.d/jenkins-deploy
sudo chmod 440 /etc/sudoers.d/jenkins-deploy
sudo visudo -cf /etc/sudoers.d/jenkins-deploy

sudo systemctl restart jenkins
```

### 3. 可选：jenkins 用户预检（不重启 MediaMTX）

```bash
sudo -u jenkins -H bash -lc '
  cd /service/home-camera-monitor
  DEPLOY_USE_SUDO=auto DEPLOY_MEDIAMTX=0 SKIP_GIT_UPDATE=1 bash deploy/deploy-all.sh
'
```

期望日志含：

```text
[deploy] skip MediaMTX
[deploy] completed
```

且 `docker ps` 中 `home-mediamtx` 启动时间**不变**。

### 4. Jenkins Deploy Production

1. 在 **dev** 分支触发构建（#8 或更新）
2. Backend Test + Frontend Build 绿
3. 点击 **Deploy** 确认
4. Console 含 `[deploy] skip MediaMTX` + `[deploy] completed`

### 5. 反馈 A 组

```text
B 组 CD 复测反馈
- 构建号：#___
- Deploy：已执行 / 失败（附日志）
- MediaMTX：未重启（容器启动时间不变）
- 生产验证：首页 / Swagger / api/video/status 正常
```

---

## 仍未解决（P1，不阻塞 Deploy）

| 项 | 说明 |
|----|------|
| GitHub fetch 不稳定 | Jenkins 可暂用本地缓存；网络恢复后改回 SCM 标准配置 |
| `stream/1` WebRTC 404 | 推流/路径问题，与 CD 无关，单独排查 |

---

*修复 push 到 `dev` 后请 B 组开始 §2 起步骤。*

# B组 CD 落地反馈给 A 组

时间：2026-07-10  
项目：home-camera-monitor  
服务器：152.136.29.158  
Jenkins：http://152.136.29.158:8080  
Jenkins 任务：home-camera-monitor

## 结论

本轮已完成 Jenkins 基础状态检查、`dev` 分支最新代码缓存同步、Backend Test、Frontend Build 和生产环境只读验证。

当前结论：

- CI 已跑通。
- CD 的 Deploy Production 未执行。
- 未执行部署的原因是 `deploy/deploy-all.sh` 当前会调用 `deploy/mediamtx_run.sh`，存在重启或重建 `home-mediamtx` 的风险，违反本次 B 组安全限制。
- 因此当前还不能判定“Jenkins CD 端到端流程已跑通”。

## 当前代码状态

- 生产目录当前分支：`dev`
- 生产目录当前 commit：`c1ca749`
- 最新 `origin/dev` commit：`aee475d`
- Jenkins 最新成功构建：`#7`
- Jenkins `#7` 使用代码：`origin/dev` 缓存 commit `aee475d`
- 工作区状态：生产目录存在未跟踪文件，未执行 `git reset --hard`

生产目录未跟踪文件包括：

```text
backend/.env.production
backend/yolov8n.pt
deploy/start_backend.sh
mysql8-data/
```

这些文件包含生产配置、模型文件或数据库数据目录，B 组未覆盖、未删除、未重置。

## Jenkins CI 验证

最新构建：`#7`

结果：

- Backend Test：通过
- Frontend Build：通过
- Deploy Production：跳过，未执行

关键日志结论：

```text
source revision: aee475d
Backend Test: Ran 17 tests, OK
Frontend Build: vite build succeeded
Deploy Production: skipped
Finished: SUCCESS
```

说明：由于服务器到 GitHub 的 `git fetch/git clone` 链路不稳定，Jenkins 当前临时使用服务器本地缓存的 `origin/dev` 导出源码来跑 CI。等 GitHub 网络链路稳定后，建议恢复为标准的 `Pipeline script from SCM`。

## 生产环境验证

已验证：

- 后端服务 `home-camera-backend.service`：active
- 后端监听：`127.0.0.1:8010`
- Jenkins：`*:8080` 正常监听
- 首页：`http://152.136.29.158/` 返回 200
- API：`http://152.136.29.158/api/video/status` 返回 200
- Swagger：`http://152.136.29.158/api/docs/` 返回 200
- MediaMTX：`home-mediamtx` 仍在运行
- MySQL：`home-mysql8` 仍在运行
- RTMP/RTSP/WebRTC 相关端口仍在监听：`9090`、`8554`、`8889`、`8189`

注意：

- `http://152.136.29.158:8889/stream/1/` 当前返回 404，说明 `stream/1` 当前没有可用 WebRTC path。
- `/api/video/status` 显示 `stream/2` 有帧，`stream/1` 无帧。

## 阻塞 CD 的 P0 问题

### P0-1：部署脚本会触碰 MediaMTX

`origin/dev:deploy/deploy-all.sh` 中存在如下逻辑：

```bash
if command -v docker >/dev/null 2>&1; then
  bash "$MEDIA_SCRIPT"
else
  echo "[deploy] docker not found, skip MediaMTX restart"
fi
```

其中：

```bash
MEDIA_SCRIPT="$APP_DIR/deploy/mediamtx_run.sh"
```

这会在 Docker 存在时执行 MediaMTX 脚本。当前服务器上 Docker 存在，且 `home-mediamtx` 是正在运行的生产容器。

本次 B 组安全限制明确要求：

- 不要重启或重建 `home-mediamtx`
- 不要修改 MediaMTX 配置
- 不要修改 `9090`、`8554`、`8889`、`8189` 端口

因此 B 组已停止 Deploy Production，没有点击人工确认部署。

建议 A 组修复方式：

1. `deploy-all.sh` 默认不要执行 `mediamtx_run.sh`。
2. 增加显式开关，例如：

```bash
if [ "${DEPLOY_MEDIAMTX:-0}" = "1" ]; then
  bash "$MEDIA_SCRIPT"
else
  echo "[deploy] skip MediaMTX"
fi
```

3. Jenkins CD 默认设置 `DEPLOY_MEDIAMTX=0`。
4. 部署日志中应明确出现：

```text
[deploy] skip MediaMTX
```

### P0-2：生产目录不是干净工作区

当前生产目录存在未跟踪文件，不能直接执行：

```bash
git reset --hard origin/dev
```

建议 A 组明确这些文件的归属策略：

- `backend/.env.production`：保留为生产环境本地配置，不纳入 Git。
- `backend/yolov8n.pt`：模型文件，建议放入固定外部目录或明确下载流程。
- `deploy/start_backend.sh`：当前服务依赖文件，建议纳入仓库或改为标准部署生成。
- `mysql8-data/`：数据库数据目录，不应放在应用 Git 工作树内，建议迁移到 `/data/mysql8` 或 Docker volume。

## P1 问题

### P1-1：Jenkins 从 GitHub 拉取不稳定

实际现象：

- Jenkins Git 插件 `git fetch` 超时或中断。
- 命令行 `git clone --depth 1` 出现 `Failure when receiving data from the peer`。
- GitHub codeload tarball 下载也卡住。

当前临时方案：

- 先在服务器本地已有 Git 对象库中维护 `origin/dev`。
- Jenkins 使用本地缓存 `origin/dev` 导出源码跑 CI。

建议：

- 检查服务器到 GitHub 的网络质量。
- 如网络长期不稳定，可考虑配置国内镜像、代理或改用 Gitee mirror。
- 网络稳定后恢复 Jenkins 标准配置：

```text
Definition: Pipeline script from SCM
SCM: Git
Repository URL: https://github.com/niu-spec/home-camera-monitor.git
Branch: */dev
Script Path: Jenkinsfile
```

### P1-2：sudoers 模板需适配服务器 Nginx 路径

仓库模板当前包含：

```text
jenkins ALL=(ALL) NOPASSWD: /bin/systemctl restart home-camera-backend, /bin/systemctl reload nginx, /bin/systemctl is-active nginx, /usr/sbin/nginx
```

服务器实际 Nginx 路径：

```text
/usr/bin/nginx
/www/server/nginx/sbin/nginx
/etc/init.d/nginx
```

建议 A 组更新模板，避免 Jenkins 部署时 `nginx -t` 或 reload 权限不匹配。

## 建议修复清单

建议 A 组优先处理：

1. 修改 `deploy-all.sh`，默认跳过 MediaMTX。
2. 明确生产未跟踪文件处理策略，尤其是 `.env.production`、`yolov8n.pt`、`mysql8-data/`、`deploy/start_backend.sh`。
3. 修正 `jenkins.sudoers.example` 中 Nginx 路径。
4. 等脚本修复后，B 组再配置 Jenkins 最小 sudoers 权限。
5. 再跑一次 Jenkins Deploy Production 人工确认部署。

## B 组未执行的操作

出于安全限制，本轮未执行：

- 未执行 `git reset --hard origin/dev`
- 未整体 `chown -R /service/home-camera-monitor`
- 未加入 Jenkins 到 docker 组
- 未落地 `/etc/sudoers.d/jenkins-deploy`
- 未点击 Jenkins Deploy Production 人工确认
- 未重启或重建 `home-mediamtx`
- 未修改 MediaMTX 配置
- 未删除或修改数据库数据

## 截图清单

建议补充以下截图：

1. Jenkins `#7` 构建成功页。
2. Jenkins Pipeline 页面：Backend Test 绿色、Frontend Build 绿色。
3. Console Output：`aee475d`、`Ran 17 tests`、`vite build`、`Finished: SUCCESS`。
4. 生产首页：`http://152.136.29.158/`。
5. Swagger：`http://152.136.29.158/api/docs/`。
6. API 状态：`http://152.136.29.158/api/video/status`。
7. GitHub Webhook Recent Deliveries，若已配置。

不要截图包含密码、Token、私钥、数据库密码的页面。

## 可直接发群文本

```text
B 组 CD 落地反馈

- Jenkins：http://152.136.29.158:8080
- 当前生产目录 commit：c1ca749
- 最新 origin/dev commit：aee475d
- 最新构建：#7
- Backend Test：通过
- Frontend Build：通过
- Deploy Production：未执行

未执行 Deploy 的原因：
origin/dev 的 deploy/deploy-all.sh 当前会在 Docker 存在时调用 deploy/mediamtx_run.sh，存在重启或重建 home-mediamtx 的风险，违反本次“不重启或修改 MediaMTX”的安全限制。

生产验证：
- 首页正常
- /api/video/status 正常
- Swagger 正常
- home-camera-backend 正常
- home-mediamtx 仍在运行，未被重启
- MySQL 仍在运行

需要 A 组修复：
1. deploy-all.sh 默认跳过 MediaMTX，建议增加 DEPLOY_MEDIAMTX=0/1 开关。
2. 明确生产目录未跟踪文件处理策略：.env.production、yolov8n.pt、deploy/start_backend.sh、mysql8-data/。
3. 修正 jenkins.sudoers.example 中 Nginx 路径以适配服务器。

当前 CI 已满足验收，CD 端到端尚未满足结题条件，待 A 组修复部署脚本后 B 组再跑 Deploy Production。
```

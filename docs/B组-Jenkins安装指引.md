# B 组 Jenkins 安装指引

> **发给**：B 苏哲勋（流媒体 / Nginx / 云服务器）  
> **日期**：2026-07-10  
> **背景**：GitLab.com 需身份验证，组员无法全员使用；改用云服务器 Jenkins + GitHub Webhook，符合课程「Jenkins/GitLab + 全员可用」要求。

---

## 1. 架构

```
组员 git push origin dev
        ↓
   GitHub 仓库
        ↓ webhook
Jenkins :8080（152.136.29.158）
        ↓
  backend-test + frontend-build
        ↓（手动确认）
  deploy/deploy-all.sh → 重启服务
```

GitHub Actions 也会并行跑 CI（组员在 GitHub Actions 页查看）；Jenkins 用于结题截图。

---

## 2. 前置依赖

SSH 登录服务器后确认：

```bash
python3 --version    # 需要 3.10+
node --version       # 需要 20+
npm --version
docker --version     # deploy 阶段需要
git --version
```

若缺 Node.js 20：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

若缺 Python venv：

```bash
sudo apt-get install -y python3-venv python3-pip
```

---

## 3. 安装 Jenkins

### 方式 A：一键脚本

```bash
cd /service/home-camera-monitor
git fetch origin dev && git reset --hard origin/dev
sudo bash deploy/install_jenkins.sh
```

### 方式 B：手动安装

```bash
sudo apt update
sudo apt install -y openjdk-17-jre fontconfig

curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null

echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" \
  | sudo tee /etc/apt/sources.list.d/jenkins.list

sudo apt update
sudo apt install -y jenkins
sudo systemctl enable jenkins
sudo systemctl start jenkins

# 初始密码
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

浏览器访问：**http://152.136.29.158:8080**

1. 输入初始密码
2. 选 **Install suggested plugins**
3. 创建管理员账号（建议用户名 `admin`，密码告知 A 组）

### 防火墙

若 8080 外网无法访问：

```bash
# 腾讯云安全组：入站放行 TCP 8080
# 或宝塔面板 → 安全 → 放行 8080
sudo ufw allow 8080/tcp 2>/dev/null || true
```

---

## 4. 配置 Jenkins 任务

### 4.1 安装插件

**Manage Jenkins → Plugins → Available**，搜索并安装：

- **GitHub Integration**（或 GitHub plugin）
- **Pipeline**
- **Git**

重启 Jenkins。

### 4.2 新建 Pipeline 任务

1. **New Item** → 名称 `home-camera-monitor` → 类型 **Pipeline** → OK
2. **General** → 勾选 **GitHub project**，URL 填：
   `https://github.com/niu-spec/home-camera-monitor`
3. **Build Triggers** → 勾选 **GitHub hook trigger for GITScm polling**
4. **Pipeline** 区：
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/niu-spec/home-camera-monitor.git`
   - Branch: `*/dev`（或 `*` 匹配所有分支）
   - Script Path: `Jenkinsfile`
5. 保存

### 4.3 配置 GitHub Webhook

在 GitHub 仓库：

1. **Settings → Webhooks → Add webhook**
2. Payload URL: `http://152.136.29.158:8080/github-webhook/`
3. Content type: `application/json`
4. 事件：Just the push event
5. Active ✓ → Add webhook

推送测试：

```bash
git commit --allow-empty -m "ci: test jenkins webhook"
git push origin dev
```

Jenkins 任务应在 1 分钟内自动开始构建。

> 若 GitHub Webhook 报 SSL/连接失败，检查安全组 8080 是否放行；或暂时依赖 Jenkinsfile 里的 `pollSCM`（每 5 分钟检查一次）。

---

## 5. 给组员建账号

**Manage Jenkins → Users → Create User**（或在 Security 里启用用户注册）

建议给 6 名组员各建一个账号：

| 组员 | 建议用户名 | 角色 |
|------|-----------|------|
| A 牛雨昊 | niu-spec | Admin |
| B 苏哲勋 | suzhexun | Admin |
| C 王梓铭 | wangziming | User（可查看 + 触发构建） |
| D 李东礼 | lidongli | User |
| E 刘帅华 | liushuaihua | User |
| F 刘澎潮 | liupengchao | User |

**Manage Jenkins → Security → Authorization** → 选 **Logged-in users can do anything**（小团队够用）。

组员使用：浏览器打开 `http://152.136.29.158:8080` → 登录 → 查看构建结果。

---

## 6. Deploy 阶段权限

Jenkins Pipeline 的 Deploy 阶段会执行 `deploy/deploy-all.sh`，需要 Jenkins 用户能：

- `systemctl restart home-camera-backend`
- `docker` 操作
- `nginx -s reload`

```bash
# 将 jenkins 用户加入 docker 组
sudo usermod -aG docker jenkins

# 允许 jenkins 无密码执行 deploy 相关命令（按需调整）
sudo visudo -f /etc/sudoers.d/jenkins-deploy
```

写入：

```
jenkins ALL=(ALL) NOPASSWD: /bin/systemctl restart home-camera-backend, /bin/systemctl reload nginx, /usr/sbin/nginx
```

然后重启 Jenkins：

```bash
sudo systemctl restart jenkins
```

---

## 7. 验证清单

| # | 检查项 | 命令 / 操作 | 期望 |
|---|--------|------------|------|
| 1 | Jenkins 可访问 | 浏览器 `http://152.136.29.158:8080` | 登录页正常 |
| 2 | Webhook 触发 | push 到 `dev` | Jenkins 自动开始构建 |
| 3 | Backend test | 查看构建日志 | `OK` / 绿色 |
| 4 | Frontend build | 查看构建日志 | `dist/` 构建成功 |
| 5 | GitHub Actions | GitHub → Actions 页 | 同样绿色通过 |
| 6 | Deploy（可选） | Jenkins Deploy 阶段点确认 | 服务重启，前端更新 |

---

## 8. 常见问题

### Jenkins 构建报 `npm: command not found`

安装 Node.js 20（见 §2），重启 Jenkins。

### Jenkins 构建报 `python3: command not found`

```bash
sudo apt install -y python3 python3-venv python3-pip
```

### Deploy 阶段报 `Permission denied` (systemctl)

按 §6 配置 sudoers，或将 deploy 改为 root 用户执行的 SSH 步骤。

### GitHub Webhook 最近交付显示 failed

- 检查 8080 端口是否外网可达
- 检查 Jenkins 是否运行：`sudo systemctl status jenkins`
- 临时用 pollSCM 兜底（Jenkinsfile 已配置）

### deploy-all.sh 报 working tree has local changes

服务器上有本地改动，先 stash 或 `git reset --hard origin/dev`。

---

## 9. 完成后反馈 A 组

```
Jenkins URL: http://152.136.29.158:8080
管理员账号: admin / ******
Webhook: 已配置 / 未配置（用的 pollSCM）
测试构建: #N 绿色通过
组员账号: 已创建 6 个
```

---

*维护：Jenkins 或 deploy 脚本变更时同步更新本文档。*

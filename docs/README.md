# 项目文档索引

> **仓库**：https://github.com/niu-spec/home-camera-monitor  
> **主分支**：`dev`  
> **最后整理**：2026-07-14（按当前 `docs/` 实存文件重编）

---

## 目录结构（当前）

```
docs/
├── README.md                         # 本索引
├── 总体架构说明.md                     # 结题架构文档（原架构设计/ 已并入此处）
├── 产品需求与设计文档3.0.pdf            # 需求与设计终稿
├── 课程要求/                          # 课程下发 PDF
├── 工作日报/                          # 组内日报 0708–0714
├── 开发指南/
│   └── DEV_SETUP.md                  # 本地开发必读
└── 项目管理/
    ├── 项目基础建设教师查阅说明.md      # §5 交老师（链接查阅）
    ├── Git 昵称对应的真实姓名.md        # 与根目录 CONTRIBUTORS.md 对照
    ├── 项目组总结报告.md / .pdf
    ├── 相关截图/                      # §5 可选附图（分支/Contributors/Swagger）
    └── …
```

> **已删除、不再引用**：`docs/架构设计/`、`docs/部署运维/`（含 CI/Swagger 运维专篇）。  
> 部署操作以仓库根目录 `deploy/README.md`、`nginx/README.md` 及云服务器现场为准；架构说明见 `总体架构说明.md`。

---

## 开发入门

| 文档 | 读者 | 说明 |
|------|------|------|
| [开发指南/DEV_SETUP.md](开发指南/DEV_SETUP.md) | 全员 | **本地开发必读** — conda、dlib、MySQL、前后端启动 |
| [../README.md](../README.md) | 全员 | 项目概览 |
| [../frontend/README.md](../frontend/README.md) | A/E | 前端 |
| [../backend/README.md](../backend/README.md) | B/C/D/E | 后端 |
| [../deploy/README.md](../deploy/README.md) | A/B | 部署脚本 |
| [../nginx/README.md](../nginx/README.md) | B | MediaMTX / Nginx 端口与反代 |

---

## 架构与产品文档

| 文档 | 读者 | 说明 |
|------|------|------|
| [总体架构说明.md](总体架构说明.md) | 全员 / 答辩 | **结题设计文档 v1.5** — WebRTC + overlay、模块划分 |
| [产品需求与设计文档3.0.pdf](产品需求与设计文档3.0.pdf) | 全员 / 平台提交 | 需求与设计终稿 |

---

## 课程要求与结题材料

| 文档 | 读者 | 说明 |
|------|------|------|
| [课程要求/](课程要求/) | 全员 | 日程、任务清单、CICD 参考等课程 PDF |
| [工作日报/](工作日报/) | 平台提交 | 0708–0714 组内日报 |
| [项目管理/项目基础建设教师查阅说明.md](项目管理/项目基础建设教师查阅说明.md) | **交老师** | §5「去哪看」：GitHub / OpenSpec / Swagger / CI 链接 |
| [项目管理/Git 昵称对应的真实姓名.md](项目管理/Git%20昵称对应的真实姓名.md) | 验收 | 昵称 ↔ 姓名（亦见根目录 [CONTRIBUTORS.md](../CONTRIBUTORS.md)） |
| [项目管理/项目组总结报告.md](项目管理/项目组总结报告.md) / [pdf](项目管理/项目组总结报告.pdf) | 平台提交 | 组总结 |
| [项目管理/相关截图/](项目管理/相关截图/) | 可选附图 | 分支管理、Contributors、Swagger 等 |

OpenSpec 规格与归档在仓库 **`openspec/`**（不在 `docs/`）：  
https://github.com/niu-spec/home-camera-monitor/tree/dev/openspec

---

## CI/CD 与 Swagger（代码内位置）

| 项 | 位置 |
|----|------|
| GitHub Actions | [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) · [运行记录](https://github.com/niu-spec/home-camera-monitor/actions) |
| Jenkins Pipeline | 根目录 [`Jenkinsfile`](../Jenkinsfile) · 服务 `http://152.136.29.158:8080/` |
| Swagger UI | 生产 `http://152.136.29.158/api/docs/` · 本地 `http://127.0.0.1:8000/api/docs/` |
| 详细查阅路径 | [项目管理/项目基础建设教师查阅说明.md](项目管理/项目基础建设教师查阅说明.md) |

---

## 文档维护约定

1. 结题架构以 **`docs/总体架构说明.md`** 为准  
2. 不要写「双推 GitLab」— 主仓库仅 GitHub  
3. 课程 PDF 放在 `课程要求/`；产品需求 PDF 可放在 `docs/` 根目录  
4. 新增结题说明优先更新本索引与「教师查阅说明」  
5. 部署步骤变更时同步 `deploy/README.md` / `nginx/README.md`

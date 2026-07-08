## 1. 文档产出

- [ ] 1.1 确认 proposal.md、design.md 内容与团队架构一致
- [ ] 1.2 确认 6 个 capability spec 覆盖已实现功能与待接入 AI 扩展点
- [ ] 1.3 确认 openspec/config.yaml 项目上下文完整

## 2. 归档到主 specs 目录

- [ ] 2.1 运行 `openspec archive bootstrap-from-docs`（或 `/opsx-archive`）将 specs 合并到 `openspec/specs/`
- [ ] 2.4 验证 `openspec/specs/` 下存在 6 个 capability 目录

## 3. 下一 change 准备（可选）

- [ ] 3.1 创建 change `ai-video-integration`：C/D 接入 `process_frame()`
- [ ] 3.2 创建 change `user-manage-page`：补全 UserManage.vue

## 4. 团队对齐

- [ ] 4.1 在组内说明 OpenSpec 工作流：propose → apply → archive
- [ ] 4.2 约定每个 feature PR 关联一个 OpenSpec change

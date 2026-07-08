## Why

`UserManage.vue` 目前为占位页，路由 `/users` 未注册，侧边栏缺少统一账户入口。用户需要在同一页面查看账号信息并跳转至个人信息与家庭管理。

## What Changes

- 实现 UserManage.vue：展示手机号、当前家庭、快捷入口
- 注册 `/users` 路由
- 侧边栏「用户管理」菜单项
- 更新 `auth-accounts` spec

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `auth-accounts`: 新增用户管理聚合页需求

## Impact

- `frontend/src/views/UserManage.vue`
- `frontend/src/router/index.js`
- `frontend/src/App.vue`

## Context

项目已有 Profile.vue（换绑手机号）和 HouseholdManage.vue（家庭 CRUD），但缺少统一的账户概览页。README 已约定 `/users` 路径。

## Goals / Non-Goals

**Goals:**
- 单页展示当前登录用户与活跃家庭
- 提供跳转至 Profile、HouseholdManage 的入口

**Non-Goals:**
- 不新增后端 API
- 不实现 Django Admin 级用户管理

## Decisions

UserManage 作为**聚合导航页**，复用现有 `authApi.getMe()` 与 `householdApi.list()`，不重复 Profile/Household 的业务逻辑。

## Risks / Trade-offs

- [activeHouseholdId 未设置] → 回退显示第一个家庭或「未加入家庭」

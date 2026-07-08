## ADDED Requirements

### Requirement: User management hub page

The frontend SHALL provide a `/users` page that displays the logged-in user's phone number and active household, with navigation to profile and household management.

#### Scenario: View account overview

- **WHEN** an authenticated user navigates to `/users`
- **THEN** the page shows their phone number and current household name

#### Scenario: Navigate to profile settings

- **WHEN** user clicks「编辑个人信息」on the user management page
- **THEN** the router navigates to `/profile`

#### Scenario: Navigate to household management

- **WHEN** user clicks「家庭管理」on the user management page
- **THEN** the router navigates to `/households`

### Requirement: User management route and menu

The application SHALL register route `/users` and expose it in the sidebar navigation as「用户管理」.

#### Scenario: Sidebar menu entry

- **WHEN** user is logged in
- **THEN** the sidebar includes a menu item linking to `/users`

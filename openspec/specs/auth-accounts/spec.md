# auth-accounts Specification

## Purpose
TBD - created by archiving change bootstrap-from-docs. Update Purpose after archive.
## Requirements
### Requirement: JWT authentication

The system SHALL authenticate users via JWT tokens obtained from `POST /api/auth/login/`.

#### Scenario: Successful login

- **WHEN** a user submits valid phone and password to `/api/auth/login/`
- **THEN** the response includes access and refresh tokens

#### Scenario: Protected API access

- **WHEN** a client calls a protected endpoint without a valid JWT
- **THEN** the system returns HTTP 401 Unauthorized

### Requirement: Family member management

The system SHALL provide CRUD endpoints at `/api/auth/members/` for registered family members.

#### Scenario: Register family member

- **WHEN** an authenticated client POSTs a member with `name`, `role`, and optional `face_encoding`
- **THEN** the member is created with role one of `adult`, `child`, `elder`, or `guest`

#### Scenario: List active members

- **WHEN** a client GETs `/api/auth/members/`
- **THEN** all active family members are returned

### Requirement: Frontend token handling

The frontend SHALL attach the JWT access token to all API requests and redirect to login on 401.

#### Scenario: Axios interceptor

- **WHEN** any API request is made after login
- **THEN** the Authorization header contains `Bearer {access_token}`

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


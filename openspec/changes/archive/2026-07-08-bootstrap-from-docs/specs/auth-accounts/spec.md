## ADDED Requirements

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

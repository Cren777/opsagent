# OpsAgent Authentication Design

## Goal

Add local login, first-user registration, password changes, username editing, and a signed-in user area in the lower-left sidebar without changing the existing OpsAgent chat, knowledge, logs, diagnostics, indexing, datasource, or LLM workflows.

## Decisions

- Registration uses the "first user only" model.
- The first registered user becomes an `admin`.
- After one active user exists, public registration is closed.
- Authentication uses local SQLite persistence plus JWT Bearer tokens.
- User records live in the existing runtime configuration database at `data/app_config.db`.
- The frontend stores the token in `localStorage` and attaches it to API requests through the existing Axios client.
- Route guards keep users on `/login` until authenticated.
- The existing optional API key middleware remains available for non-debug deployments, but user JWT authentication becomes the primary application login model for `/api/*`.

## Current Context

The backend has FastAPI routes under `ops_agent/api/routes`, SQLAlchemy runtime configuration models in `ops_agent/api/models/config_models.py`, and configuration CRUD helpers in `ops_agent/api/services/config_service.py`. There is an existing `APIKeyMiddleware`, but it only checks `X-API-Key` and does not model users, sessions, password changes, or profile updates.

The frontend is a Vue 3 SPA with Vue Router, Pinia, Element Plus, and an Axios client in `frontend/src/api/client.ts`. The main authenticated application shell is `frontend/src/components/layout/AppLayout.vue`, and the left sidebar is `frontend/src/components/layout/AppSidebar.vue`. The screenshot highlights the lower-left sidebar area as the desired location for signed-in user information.

## Backend Design

### Persistence

Add a `UserModel` to `ops_agent/api/models/config_models.py`:

- `id`: UUID string primary key.
- `username`: unique string, 3-32 characters.
- `password_hash`: hashed password string.
- `role`: string, initially `admin` for the first user.
- `is_active`: boolean.
- `created_at`: timezone-aware datetime.
- `updated_at`: timezone-aware datetime.
- `last_login_at`: nullable datetime.

The existing `init_config_db()` call creates the table on startup through SQLAlchemy metadata, so no external migration tool is required for this project.

### Passwords

Password hashing should use Python standard-library PBKDF2-HMAC-SHA256 with a per-password random salt. Password validation is intentionally modest and local:

- Required.
- Minimum length: 8 characters.
- Maximum length: 128 characters.
- Cannot equal the username case-insensitively.

This is enough for an internal single-instance tool without adding a full account policy engine.

### Tokens

JWT access tokens are signed with a secret derived from configuration. Add these settings:

- `auth_jwt_secret`: defaults to `OPSAGENT_API_KEY` or `demo-key` for local development.
- `auth_token_expire_minutes`: defaults to `1440`.

Token payload includes:

- `sub`: user ID.
- `username`: current username at issuance time.
- `role`: user role.
- `exp`: expiry timestamp.

The backend validates the user ID on each authenticated request so disabled or deleted users cannot keep using old tokens.

### API Endpoints

Create `ops_agent/api/routes/auth.py` with prefix `/api/auth`.

- `GET /api/auth/bootstrap`
  - Returns whether registration is available.
  - Response: `{ "registration_open": true | false }`.

- `POST /api/auth/register`
  - Allowed only when no user exists.
  - Request: `{ "username": "...", "password": "..." }`.
  - Creates the first admin user and returns the same response shape as login.
  - If users already exist, returns `403`.

- `POST /api/auth/login`
  - Request: `{ "username": "...", "password": "..." }`.
  - Validates active user and password, updates `last_login_at`, returns token plus user.
  - Invalid credentials return `401` with a generic message.

- `GET /api/auth/me`
  - Requires Bearer token.
  - Returns the current user profile.

- `PATCH /api/auth/me`
  - Requires Bearer token.
  - Request: `{ "username": "..." }`.
  - Updates username after uniqueness and format validation.
  - Returns the updated profile.

- `POST /api/auth/change-password`
  - Requires Bearer token.
  - Request: `{ "current_password": "...", "new_password": "..." }`.
  - Verifies the current password, validates the new password, updates the hash.
  - Returns `{ "ok": true }`.

### Dependencies

Create `ops_agent/api/services/auth_service.py` for persistence, password hashing, token creation, and token validation. Create `ops_agent/api/dependencies/auth.py` for `get_current_user`, which routes can reuse later if user-specific ownership is added.

### Middleware and Route Protection

Use FastAPI dependencies rather than a new global JWT middleware for business routes. This is more explicit and easier to test with route-level behavior. The auth router remains public for bootstrap, register, and login; all existing `/api/*` routers should require a global dependency after the auth router is mounted.

The application should register routes in this order:

1. Public health and auth routes.
2. Protected application routes under `/api`.
3. Static assets and SPA fallback.

Public paths:

- `/health`
- `/api/auth/bootstrap`
- `/api/auth/register`
- `/api/auth/login`
- `/assets/*`
- SPA fallback routes such as `/` and `/login`
- `/docs`, `/openapi.json`, and `/redoc` in development

## Frontend Design

### Auth Store

Add `frontend/src/stores/auth.ts`:

- State: `token`, `user`, `registrationOpen`, `initialized`, `isLoading`.
- Computed: `isAuthenticated`.
- Actions: `bootstrap`, `login`, `registerFirstUser`, `fetchMe`, `updateUsername`, `changePassword`, `logout`.
- Persistence: token in `localStorage` under `opsagent_auth_token`.

### API Client

Update `frontend/src/api/client.ts` to:

- Attach `Authorization: Bearer <token>` when a token exists.
- On `401`, clear the token and redirect to `/login` unless already on `/login`.

Avoid importing the Pinia store directly in the Axios module during setup to prevent circular initialization. Use small token helper functions in `frontend/src/api/auth.ts` or `frontend/src/stores/auth.ts`.

### Auth Types and API

Add:

- `frontend/src/types/auth.ts`
- `frontend/src/api/auth.ts`

Keep request and response names explicit:

- `AuthUser`
- `AuthResponse`
- `BootstrapResponse`
- `LoginRequest`
- `RegisterRequest`
- `UpdateProfileRequest`
- `ChangePasswordRequest`

### Routes

Add `frontend/src/views/LoginView.vue`.

Router behavior:

- `/login` is public.
- All existing routes require auth.
- On startup, call `authStore.bootstrap()`.
- If no token exists, redirect to `/login`.
- If token exists, call `fetchMe()` before entering protected routes.
- If authenticated user visits `/login`, redirect to `/`.

### Login and First-User Registration UI

The login page should be a functional, restrained internal operations screen rather than a marketing page:

- Show brand name `OpsAgent`.
- If `registrationOpen` is true, show "创建首个管理员账号".
- If false, show "登录 OpsAgent".
- Use Element Plus form validation.
- Include username and password fields.
- Disable submit while loading.
- After successful login or first-user registration, navigate to `/`.

### Sidebar User Area

Update `frontend/src/components/layout/AppSidebar.vue` to add a bottom user panel matching the screenshot's highlighted area:

- Avatar circle with first username letter.
- Username.
- Role label.
- Dropdown/menu actions:
  - 修改用户名
  - 修改密码
  - 退出登录
When the sidebar is collapsed, show only the avatar icon with a tooltip/dropdown. Do not let the user area overlap session history; the sidebar should remain a vertical flex layout with the user panel pinned to the bottom.

### Profile Dialogs

Add small focused components under `frontend/src/components/auth`:

- `UserProfileDialog.vue`: edit username.
- `ChangePasswordDialog.vue`: change password.

Each dialog owns its form validation, calls the auth store, displays success or backend error messages through Element Plus, and closes only after a successful request.

## Security Notes

- Do not store plaintext passwords.
- Do not return `password_hash` in API responses.
- Use generic login failure messages.
- Keep runtime database files out of git.
- Keep tokens out of URL query parameters.
- Do not protect `/login` through the API middleware because it is a SPA route.
- The feature does not add password reset email, MFA, invitation links, user management pages, or per-user data isolation.

## Testing Strategy

Backend tests:

- Registration is open before any user exists.
- First registration creates an admin and returns a token.
- Second registration is rejected.
- Login succeeds with correct credentials.
- Login fails with wrong credentials.
- `/api/auth/me` rejects missing token.
- `/api/auth/me` accepts valid token.
- Username update enforces uniqueness and returns updated user.
- Password change requires current password.
- Old password stops working after password change; new password works.

Frontend verification:

- `npx vue-tsc -p tsconfig.app.json --noEmit`
- `npm run build`
- Manual browser checks for first-user registration, login, refresh persistence, sidebar user menu, username update, password update, logout, and protected-route redirect.

## Risks

- Adding a global dependency in the wrong place could accidentally protect `/api/auth/login`; route registration order must be tested.
- Axios redirects on `401` could interrupt login failures; the client should skip automatic redirect while already on `/login`.
- Existing local chat sessions are stored in browser localStorage and are not user-scoped. This design does not migrate them; it only protects app access.
- Runtime `app_config.db` may already exist. SQLAlchemy metadata creation must be idempotent.

## Out of Scope

- Multi-user administration UI.
- Role-based authorization beyond storing the first user as `admin`.
- Per-user chat history persistence.
- Password reset by email.
- Single sign-on.
- Account lockout and audit logs.



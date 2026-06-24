# OpsAgent Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-user registration, login, authenticated API access, password changes, username editing, and a lower-left sidebar user panel.

**Architecture:** Store local users in the existing SQLite config database and issue HMAC-SHA256 JWT Bearer tokens with Python standard-library code. Protect existing `/api/*` routes through FastAPI dependencies while keeping auth bootstrap, registration, login, health, static assets, and SPA routes public. The Vue app uses a Pinia auth store, route guards, and Axios token injection.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, hashlib/hmac/secrets/base64/json, Vue 3, TypeScript, Pinia, Vue Router 4, Axios, Element Plus, pytest.

---

## File Structure

- Modify: `config/settings.py`
  - Add JWT secret and expiry settings.
- Modify: `ops_agent/api/models/config_models.py`
  - Add `UserModel` table.
- Create: `ops_agent/api/services/auth_service.py`
  - Own username validation, password hashing, JWT creation, JWT validation, and user CRUD.
- Create: `ops_agent/api/dependencies/__init__.py`
  - Mark dependency package.
- Create: `ops_agent/api/dependencies/auth.py`
  - Expose `get_current_user` and `require_current_user`.
- Create: `ops_agent/api/routes/auth.py`
  - Expose `/api/auth/bootstrap`, `/register`, `/login`, `/me`, `/change-password`.
- Modify: `ops_agent/api/main.py`
  - Register auth routes and protect existing app routes.
- Create: `tests/test_auth_service.py`
  - Unit-test registration policy, hashing, token validation, profile update, and password change.
- Create: `tests/test_auth_routes.py`
  - API-test bootstrap, register, login, protected route behavior, profile update, and password change.
- Create: `frontend/src/types/auth.ts`
  - Auth request/response/user types.
- Create: `frontend/src/api/auth.ts`
  - Auth API client helpers and token storage helpers.
- Modify: `frontend/src/api/client.ts`
  - Attach token and handle unauthenticated responses.
- Create: `frontend/src/stores/auth.ts`
  - Pinia auth state and actions.
- Modify: `frontend/src/router/index.ts`
  - Add `/login` and route guard.
- Create: `frontend/src/views/LoginView.vue`
  - Login and first-admin registration form.
- Create: `frontend/src/components/auth/UserProfileDialog.vue`
  - Username edit dialog.
- Create: `frontend/src/components/auth/ChangePasswordDialog.vue`
  - Password change dialog.
- Modify: `frontend/src/components/layout/AppSidebar.vue`
  - Add lower-left user panel and account actions.

---

## Task 1: Backend User Model and Settings

**Files:**
- Modify: `config/settings.py`
- Modify: `ops_agent/api/models/config_models.py`
- Test: `tests/test_auth_service.py`

- [ ] **Step 1: Write failing model/settings test**

Create `tests/test_auth_service.py` with this initial test:

```python
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ops_agent.api.models.config_models import Base, UserModel


def test_user_model_table_can_store_first_admin(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        user = UserModel(
            id="user-1",
            username="admin",
            password_hash="hash",
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.commit()

        saved = session.query(UserModel).filter_by(username="admin").one()

    assert saved.id == "user-1"
    assert saved.role == "admin"
    assert saved.is_active is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_auth_service.py::test_user_model_table_can_store_first_admin -q
```

Expected: FAIL with import error for `UserModel`.

- [ ] **Step 3: Add auth settings**

In `config/settings.py`, add these fields under the `# --- Security ---` section:

```python
    auth_jwt_secret: str = os.getenv("OPSAGENT_AUTH_JWT_SECRET", os.getenv("OPSAGENT_API_KEY", "demo-key"))
    auth_token_expire_minutes: int = int(os.getenv("OPSAGENT_AUTH_TOKEN_EXPIRE_MINUTES", "1440"))
```

- [ ] **Step 4: Add UserModel**

In `ops_agent/api/models/config_models.py`, keep the existing imports and add `UniqueConstraint`:

```python
from sqlalchemy import create_engine, Column, String, Boolean, Float, Integer, Text, DateTime, UniqueConstraint
```

Add this class after `LLMProviderConfigModel`:

```python
class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)

    id = Column(String(36), primary_key=True)
    username = Column(String(32), nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(32), nullable=False, default="admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
pytest tests/test_auth_service.py::test_user_model_table_can_store_first_admin -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add config/settings.py ops_agent/api/models/config_models.py tests/test_auth_service.py
git commit -m "feat: add local user model"
```

---

## Task 2: Auth Service

**Files:**
- Create: `ops_agent/api/services/auth_service.py`
- Modify: `tests/test_auth_service.py`

- [ ] **Step 1: Write failing service tests**

Append these tests to `tests/test_auth_service.py`:

```python
import pytest

from ops_agent.api.services.auth_service import (
    AuthError,
    AuthService,
    RegistrationClosedError,
    UsernameTakenError,
)


def make_auth_service(tmp_path: Path) -> AuthService:
    db_path = tmp_path / "auth.db"
    return AuthService(db_path=db_path, jwt_secret="test-secret", token_expire_minutes=60)


def test_first_user_registration_creates_admin_and_closes_registration(tmp_path: Path):
    service = make_auth_service(tmp_path)

    assert service.is_registration_open() is True
    result = service.register_first_user("admin", "strong-password")

    assert result["user"]["username"] == "admin"
    assert result["user"]["role"] == "admin"
    assert result["access_token"]
    assert service.is_registration_open() is False


def test_second_registration_is_rejected(tmp_path: Path):
    service = make_auth_service(tmp_path)
    service.register_first_user("admin", "strong-password")

    with pytest.raises(RegistrationClosedError):
        service.register_first_user("other", "strong-password")


def test_login_validates_password_and_updates_last_login(tmp_path: Path):
    service = make_auth_service(tmp_path)
    service.register_first_user("admin", "strong-password")

    result = service.login("admin", "strong-password")
    user = service.get_user_by_id(result["user"]["id"])

    assert result["access_token"]
    assert user["last_login_at"] is not None


def test_login_rejects_wrong_password(tmp_path: Path):
    service = make_auth_service(tmp_path)
    service.register_first_user("admin", "strong-password")

    with pytest.raises(AuthError):
        service.login("admin", "wrong-password")


def test_token_round_trip_returns_current_user(tmp_path: Path):
    service = make_auth_service(tmp_path)
    registered = service.register_first_user("admin", "strong-password")

    current = service.get_current_user(registered["access_token"])

    assert current["username"] == "admin"
    assert current["role"] == "admin"


def test_update_username_rejects_duplicate(tmp_path: Path):
    service = make_auth_service(tmp_path)
    admin = service.register_first_user("admin", "strong-password")["user"]
    service._create_user_for_test("ops", "strong-password")

    with pytest.raises(UsernameTakenError):
        service.update_username(admin["id"], "ops")


def test_change_password_requires_current_password(tmp_path: Path):
    service = make_auth_service(tmp_path)
    service.register_first_user("admin", "strong-password")

    with pytest.raises(AuthError):
        service.change_password("admin", "wrong-password", "new-strong-password")


def test_change_password_allows_login_with_new_password(tmp_path: Path):
    service = make_auth_service(tmp_path)
    service.register_first_user("admin", "strong-password")

    assert service.change_password("admin", "strong-password", "new-strong-password") is True

    with pytest.raises(AuthError):
        service.login("admin", "strong-password")
    assert service.login("admin", "new-strong-password")["access_token"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_auth_service.py -q
```

Expected: FAIL because `ops_agent.api.services.auth_service` does not exist.

- [ ] **Step 3: Implement auth service**

Create `ops_agent/api/services/auth_service.py`:

```python
"""Local user authentication service."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config.settings import settings
from ops_agent.api.models.config_models import Base, UserModel


class AuthError(ValueError):
    pass


class RegistrationClosedError(AuthError):
    pass


class UsernameTakenError(AuthError):
    pass


class AuthService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        jwt_secret: str | None = None,
        token_expire_minutes: int | None = None,
    ):
        self.db_path = Path(db_path or settings.config_db_path)
        self.jwt_secret = jwt_secret or settings.auth_jwt_secret
        self.token_expire_minutes = token_expire_minutes or settings.auth_token_expire_minutes
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)

    def is_registration_open(self) -> bool:
        with self._session() as session:
            return session.query(UserModel).count() == 0

    def register_first_user(self, username: str, password: str) -> dict:
        username = self._normalize_username(username)
        self._validate_password(username, password)
        with self._session() as session:
            if session.query(UserModel).count() > 0:
                raise RegistrationClosedError("娉ㄥ唽宸插叧闂?)
            user = self._create_user(session, username, password, role="admin")
            session.commit()
            return self._auth_response(user)

    def login(self, username: str, password: str) -> dict:
        username = self._normalize_username(username)
        with self._session() as session:
            user = session.query(UserModel).filter_by(username=username, is_active=True).first()
            if not user or not self._verify_password(password, user.password_hash):
                raise AuthError("鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒")
            user.last_login_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            session.commit()
            return self._auth_response(user)

    def get_current_user(self, token: str) -> dict:
        payload = self._decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("鏃犳晥鐧诲綍鐘舵€?)
        user = self.get_user_by_id(user_id)
        if not user or not user["is_active"]:
            raise AuthError("鏃犳晥鐧诲綍鐘舵€?)
        return user

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self._session() as session:
            user = session.query(UserModel).filter_by(id=user_id).first()
            return self._user_to_dict(user) if user else None

    def update_username(self, user_id: str, username: str) -> dict:
        username = self._normalize_username(username)
        with self._session() as session:
            user = session.query(UserModel).filter_by(id=user_id, is_active=True).first()
            if not user:
                raise AuthError("鐢ㄦ埛涓嶅瓨鍦?)
            existing = session.query(UserModel).filter(UserModel.username == username, UserModel.id != user_id).first()
            if existing:
                raise UsernameTakenError("鐢ㄦ埛鍚嶅凡瀛樺湪")
            user.username = username
            user.updated_at = datetime.now(timezone.utc)
            session.commit()
            return self._user_to_dict(user)

    def change_password(self, username: str, current_password: str, new_password: str) -> bool:
        username = self._normalize_username(username)
        self._validate_password(username, new_password)
        with self._session() as session:
            user = session.query(UserModel).filter_by(username=username, is_active=True).first()
            if not user or not self._verify_password(current_password, user.password_hash):
                raise AuthError("褰撳墠瀵嗙爜閿欒")
            user.password_hash = self._hash_password(new_password)
            user.updated_at = datetime.now(timezone.utc)
            session.commit()
            return True

    def _create_user_for_test(self, username: str, password: str) -> dict:
        with self._session() as session:
            user = self._create_user(session, self._normalize_username(username), password, role="operator")
            session.commit()
            return self._user_to_dict(user)

    def _session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)

    def _create_user(self, session: Session, username: str, password: str, role: str) -> UserModel:
        if session.query(UserModel).filter_by(username=username).first():
            raise UsernameTakenError("鐢ㄦ埛鍚嶅凡瀛樺湪")
        now = datetime.now(timezone.utc)
        user = UserModel(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        return user

    def _auth_response(self, user: UserModel) -> dict:
        user_dict = self._user_to_dict(user)
        return {
            "access_token": self._encode_token(user_dict),
            "token_type": "bearer",
            "user": user_dict,
        }

    def _encode_token(self, user: dict) -> str:
        header = {"alg": "HS256", "typ": "JWT"}
        exp = datetime.now(timezone.utc) + timedelta(minutes=self.token_expire_minutes)
        payload = {"sub": user["id"], "username": user["username"], "role": user["role"], "exp": int(exp.timestamp())}
        signing_input = f"{self._b64_json(header)}.{self._b64_json(payload)}"
        signature = hmac.new(self.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
        return f"{signing_input}.{self._b64(signature)}"

    def _decode_token(self, token: str) -> dict:
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
            signing_input = f"{header_b64}.{payload_b64}"
            expected = self._b64(hmac.new(self.jwt_secret.encode(), signing_input.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(expected, signature_b64):
                raise AuthError("鏃犳晥鐧诲綍鐘舵€?)
            payload = json.loads(self._b64_decode(payload_b64))
            if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
                raise AuthError("鐧诲綍宸茶繃鏈?)
            return payload
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError("鏃犳晥鐧诲綍鐘舵€?) from exc

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
        return f"pbkdf2_sha256$210000${self._b64(salt)}${self._b64(digest)}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$")
            if algorithm != "pbkdf2_sha256":
                return False
            salt = self._b64_decode(salt_b64)
            expected = self._b64_decode(digest_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
            return secrets.compare_digest(actual, expected)
        except Exception:
            return False

    def _normalize_username(self, username: str) -> str:
        value = username.strip()
        if not 3 <= len(value) <= 32:
            raise AuthError("鐢ㄦ埛鍚嶉暱搴﹂渶涓?3-32 涓瓧绗?)
        if not all(ch.isalnum() or ch in {"_", "-"} for ch in value):
            raise AuthError("鐢ㄦ埛鍚嶄粎鏀寔瀛楁瘝銆佹暟瀛椼€佷笅鍒掔嚎鍜岀煭妯嚎")
        return value

    def _validate_password(self, username: str, password: str) -> None:
        if not 8 <= len(password) <= 128:
            raise AuthError("瀵嗙爜闀垮害闇€涓?8-128 涓瓧绗?)
        if password.lower() == username.lower():
            raise AuthError("瀵嗙爜涓嶈兘涓庣敤鎴峰悕鐩稿悓")

    def _user_to_dict(self, user: UserModel) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": self._dt(user.created_at),
            "updated_at": self._dt(user.updated_at),
            "last_login_at": self._dt(user.last_login_at),
        }

    def _dt(self, value):
        return value.isoformat() if value else None

    def _b64_json(self, value: dict) -> str:
        return self._b64(json.dumps(value, separators=(",", ":")).encode())

    def _b64(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    def _b64_decode(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_auth_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ops_agent/api/services/auth_service.py tests/test_auth_service.py
git commit -m "feat: add local auth service"
```

---

## Task 3: Auth API Routes and Protected API Dependency

**Files:**
- Create: `ops_agent/api/dependencies/__init__.py`
- Create: `ops_agent/api/dependencies/auth.py`
- Create: `ops_agent/api/routes/auth.py`
- Modify: `ops_agent/api/main.py`
- Create: `tests/test_auth_routes.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_auth_routes.py`:

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ops_agent.api.dependencies.auth import require_current_user
from ops_agent.api.routes import auth as auth_routes
from ops_agent.api.services.auth_service import AuthService


def build_client(tmp_path: Path) -> TestClient:
    service = AuthService(db_path=tmp_path / "auth.db", jwt_secret="test-secret", token_expire_minutes=60)
    app = FastAPI()
    app.dependency_overrides[auth_routes.get_auth_service] = lambda: service
    app.include_router(auth_routes.router)

    @app.get("/api/protected", dependencies=[require_current_user])
    def protected():
        return {"ok": True}

    return TestClient(app)


def test_bootstrap_reports_registration_open(tmp_path: Path):
    client = build_client(tmp_path)

    assert client.get("/api/auth/bootstrap").json() == {"registration_open": True}


def test_register_login_and_me_flow(tmp_path: Path):
    client = build_client(tmp_path)
    registered = client.post("/api/auth/register", json={"username": "admin", "password": "strong-password"})

    assert registered.status_code == 200
    token = registered.json()["access_token"]
    assert registered.json()["user"]["role"] == "admin"
    assert client.get("/api/auth/bootstrap").json() == {"registration_open": False}
    assert client.post("/api/auth/register", json={"username": "other", "password": "strong-password"}).status_code == 403

    logged_in = client.post("/api/auth/login", json={"username": "admin", "password": "strong-password"})
    assert logged_in.status_code == 200
    assert logged_in.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_protected_route_requires_token(tmp_path: Path):
    client = build_client(tmp_path)

    assert client.get("/api/protected").status_code == 401


def test_profile_and_password_updates(tmp_path: Path):
    client = build_client(tmp_path)
    token = client.post("/api/auth/register", json={"username": "admin", "password": "strong-password"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    renamed = client.patch("/api/auth/me", json={"username": "ops-admin"}, headers=headers)
    assert renamed.status_code == 200
    assert renamed.json()["username"] == "ops-admin"

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "strong-password", "new_password": "new-strong-password"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json() == {"ok": True}
    assert client.post("/api/auth/login", json={"username": "ops-admin", "password": "strong-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "ops-admin", "password": "new-strong-password"}).status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_auth_routes.py -q
```

Expected: FAIL because auth routes and dependencies do not exist.

- [ ] **Step 3: Add auth dependency**

Create `ops_agent/api/dependencies/__init__.py` as an empty file.

Create `ops_agent/api/dependencies/auth.py`:

```python
"""Authentication dependencies for protected API routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ops_agent.api.services.auth_service import AuthError, AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    return AuthService()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="璇峰厛鐧诲綍")
    try:
        return service.get_current_user(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


require_current_user = Depends(get_current_user)
```

- [ ] **Step 4: Add auth routes**

Create `ops_agent/api/routes/auth.py`:

```python
"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ops_agent.api.dependencies.auth import get_current_user
from ops_agent.api.services.auth_service import AuthError, AuthService, RegistrationClosedError, UsernameTakenError

router = APIRouter(prefix="/api/auth", tags=["璁よ瘉"])


def get_auth_service() -> AuthService:
    return AuthService()


class AuthCredentials(BaseModel):
    username: str
    password: str


class UpdateProfileRequest(BaseModel):
    username: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/bootstrap")
def bootstrap(service: AuthService = Depends(get_auth_service)):
    return {"registration_open": service.is_registration_open()}


@router.post("/register")
def register(data: AuthCredentials, service: AuthService = Depends(get_auth_service)):
    try:
        return service.register_first_user(data.username, data.password)
    except RegistrationClosedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/login")
def login(data: AuthCredentials, service: AuthService = Depends(get_auth_service)):
    try:
        return service.login(data.username, data.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="鐢ㄦ埛鍚嶆垨瀵嗙爜閿欒") from exc


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/me")
def update_me(
    data: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        return service.update_username(current_user["id"], data.username)
    except UsernameTakenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    try:
        service.change_password(current_user["username"], data.current_password, data.new_password)
        return {"ok": True}
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
```

- [ ] **Step 5: Wire auth in main app**

Modify `ops_agent/api/main.py` imports:

```python
from ops_agent.api.routes import auth, chat, health, config, uploads, knowledge, incidents, diagnostics, indexes
from ops_agent.api.dependencies.auth import require_current_user
```

Register routes in this shape:

```python
app.include_router(health.router, tags=["绯荤粺"])
app.include_router(auth.router)
app.include_router(chat.router, prefix="/api", tags=["瀵硅瘽"], dependencies=[require_current_user])
app.include_router(config.router, dependencies=[require_current_user])
app.include_router(uploads.router, dependencies=[require_current_user])
app.include_router(knowledge.router, dependencies=[require_current_user])
app.include_router(incidents.router, dependencies=[require_current_user])
app.include_router(diagnostics.router, dependencies=[require_current_user])
app.include_router(indexes.router, dependencies=[require_current_user])
```

- [ ] **Step 6: Run API tests**

Run:

```bash
pytest tests/test_auth_routes.py -q
```

Expected: PASS.

- [ ] **Step 7: Run backend contract smoke tests**

Run:

```bash
pytest tests/test_auth_service.py tests/test_auth_routes.py tests/test_intent.py tests/test_orchestrator_contract.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add ops_agent/api/dependencies ops_agent/api/routes/auth.py ops_agent/api/main.py tests/test_auth_routes.py
git commit -m "feat: add auth api routes"
```

---

## Task 4: Frontend Auth API, Store, and Route Guard

**Files:**
- Create: `frontend/src/types/auth.ts`
- Create: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add frontend auth types**

Create `frontend/src/types/auth.ts`:

```typescript
export interface AuthUser {
  id: string
  username: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at?: string | null
}

export interface BootstrapResponse {
  registration_open: boolean
}

export interface AuthResponse {
  access_token: string
  token_type: 'bearer'
  user: AuthUser
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface UpdateProfileRequest {
  username: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}
```

- [ ] **Step 2: Add API helpers and token helpers**

Create `frontend/src/api/auth.ts`:

```typescript
import client from './client'
import type {
  AuthResponse,
  BootstrapResponse,
  ChangePasswordRequest,
  LoginRequest,
  RegisterRequest,
  UpdateProfileRequest,
  AuthUser,
} from '@/types/auth'

const TOKEN_KEY = 'opsagent_auth_token'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getAuthBootstrap() {
  return client.get<BootstrapResponse>('/api/auth/bootstrap')
}

export function registerFirstUser(data: RegisterRequest) {
  return client.post<AuthResponse>('/api/auth/register', data)
}

export function login(data: LoginRequest) {
  return client.post<AuthResponse>('/api/auth/login', data)
}

export function fetchCurrentUser() {
  return client.get<AuthUser>('/api/auth/me')
}

export function updateProfile(data: UpdateProfileRequest) {
  return client.patch<AuthUser>('/api/auth/me', data)
}

export function changePassword(data: ChangePasswordRequest) {
  return client.post<{ ok: boolean }>('/api/auth/change-password', data)
}
```

- [ ] **Step 3: Update Axios client**

Modify `frontend/src/api/client.ts` to import token helpers:

```typescript
import { clearStoredToken, getStoredToken } from './auth'
```

Add request interceptor before the response interceptor:

```typescript
client.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

Update the response error branch:

```typescript
  (error) => {
    const status = error.response?.status
    const msg = error.response?.data?.detail || error.message || '璇锋眰澶辫触'
    if (status === 401 && window.location.pathname !== '/login') {
      clearStoredToken()
      window.location.href = '/login'
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
```

- [ ] **Step 4: Add auth store**

Create `frontend/src/stores/auth.ts`:

```typescript
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  changePassword as changePasswordApi,
  clearStoredToken,
  fetchCurrentUser,
  getAuthBootstrap,
  getStoredToken,
  login as loginApi,
  registerFirstUser as registerFirstUserApi,
  setStoredToken,
  updateProfile,
} from '@/api/auth'
import type { AuthUser, ChangePasswordRequest, LoginRequest, RegisterRequest } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getStoredToken())
  const user = ref<AuthUser | null>(null)
  const registrationOpen = ref(false)
  const initialized = ref(false)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  async function bootstrap() {
    const { data } = await getAuthBootstrap()
    registrationOpen.value = data.registration_open
    initialized.value = true
  }

  function setSession(accessToken: string, nextUser: AuthUser) {
    token.value = accessToken
    user.value = nextUser
    setStoredToken(accessToken)
  }

  async function registerFirstUser(payload: RegisterRequest) {
    isLoading.value = true
    try {
      const { data } = await registerFirstUserApi(payload)
      setSession(data.access_token, data.user)
      registrationOpen.value = false
    } finally {
      isLoading.value = false
    }
  }

  async function login(payload: LoginRequest) {
    isLoading.value = true
    try {
      const { data } = await loginApi(payload)
      setSession(data.access_token, data.user)
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMe() {
    if (!token.value) return false
    try {
      const { data } = await fetchCurrentUser()
      user.value = data
      return true
    } catch {
      logout(false)
      return false
    }
  }

  async function updateUsername(username: string) {
    const { data } = await updateProfile({ username })
    user.value = data
    ElMessage.success('鐢ㄦ埛鍚嶅凡鏇存柊')
  }

  async function changePassword(payload: ChangePasswordRequest) {
    await changePasswordApi(payload)
    ElMessage.success('瀵嗙爜宸叉洿鏂?)
  }

  function logout(showMessage = true) {
    token.value = null
    user.value = null
    clearStoredToken()
    if (showMessage) ElMessage.success('宸查€€鍑虹櫥褰?)
  }

  return {
    token,
    user,
    registrationOpen,
    initialized,
    isLoading,
    isAuthenticated,
    bootstrap,
    registerFirstUser,
    login,
    fetchMe,
    updateUsername,
    changePassword,
    logout,
  }
})
```

- [ ] **Step 5: Add route guard**

Modify `frontend/src/router/index.ts` by adding the login route:

```typescript
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
```

Add imports and guard after router creation:

```typescript
import { useAuthStore } from '@/stores/auth'

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!authStore.initialized) {
    await authStore.bootstrap()
  }

  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }

  if (to.meta.public) {
    return authStore.isAuthenticated && to.path === '/login' ? '/' : true
  }

  if (!authStore.isAuthenticated) {
    return '/login'
  }

  return true
})
```

- [ ] **Step 6: Run frontend type check**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
```

Expected: FAIL only because `LoginView.vue` does not exist yet.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/auth.ts frontend/src/api/auth.ts frontend/src/api/client.ts frontend/src/stores/auth.ts frontend/src/router/index.ts
git commit -m "feat: add frontend auth state"
```

---

## Task 5: Login and First-Admin Registration View

**Files:**
- Create: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: Create login view**

Create `frontend/src/views/LoginView.vue`:

```vue
<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const form = reactive({ username: '', password: '' })

const title = computed(() => authStore.registrationOpen ? '鍒涘缓棣栦釜绠＄悊鍛樿处鍙? : '鐧诲綍 OpsAgent')
const buttonText = computed(() => authStore.registrationOpen ? '鍒涘缓骞惰繘鍏? : '鐧诲綍')

const rules: FormRules = {
  username: [
    { required: true, message: '璇疯緭鍏ョ敤鎴峰悕', trigger: 'blur' },
    { min: 3, max: 32, message: '鐢ㄦ埛鍚嶉暱搴﹂渶涓?3-32 涓瓧绗?, trigger: 'blur' },
  ],
  password: [
    { required: true, message: '璇疯緭鍏ュ瘑鐮?, trigger: 'blur' },
    { min: 8, max: 128, message: '瀵嗙爜闀垮害闇€涓?8-128 涓瓧绗?, trigger: 'blur' },
  ],
}

async function submit() {
  await formRef.value?.validate()
  try {
    if (authStore.registrationOpen) {
      await authStore.registerFirstUser(form)
    } else {
      await authStore.login(form)
    }
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '璁よ瘉澶辫触')
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="brand">
        <el-icon :size="28"><Monitor /></el-icon>
        <span>OpsAgent</span>
      </div>
      <h1>{{ title }}</h1>
      <p class="subtitle">鏅鸿兘杩愮淮鍔╂墜璁块棶鍏ュ彛</p>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="鐢ㄦ埛鍚? prop="username">
          <el-input v-model.trim="form.username" autocomplete="username" size="large" />
        </el-form-item>
        <el-form-item label="瀵嗙爜" prop="password">
          <el-input v-model="form.password" type="password" autocomplete="current-password" show-password size="large" />
        </el-form-item>
        <el-button type="primary" size="large" :loading="authStore.isLoading" class="submit-btn" @click="submit">
          {{ buttonText }}
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 18% 12%, rgba(47, 125, 246, 0.14), transparent 30rem),
    linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
}

.login-panel {
  width: min(420px, 100%);
  padding: 32px;
  background: #fff;
  border: 1px solid var(--ops-border);
  border-radius: 8px;
  box-shadow: var(--ops-shadow-md);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ops-primary);
  font-size: 20px;
  font-weight: 800;
  margin-bottom: 24px;
}

h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: var(--ops-text);
}

.subtitle {
  margin: 0 0 24px;
  color: var(--ops-text-secondary);
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
```

- [ ] **Step 2: Run type check**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/LoginView.vue
git commit -m "feat: add login view"
```

---

## Task 6: Sidebar User Panel and Profile Dialogs

**Files:**
- Create: `frontend/src/components/auth/UserProfileDialog.vue`
- Create: `frontend/src/components/auth/ChangePasswordDialog.vue`
- Modify: `frontend/src/components/layout/AppSidebar.vue`

- [ ] **Step 1: Create username dialog**

Create `frontend/src/components/auth/UserProfileDialog.vue`:

```vue
<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const form = reactive({ username: '' })
const isSaving = ref(false)

const rules: FormRules = {
  username: [
    { required: true, message: '璇疯緭鍏ョ敤鎴峰悕', trigger: 'blur' },
    { min: 3, max: 32, message: '鐢ㄦ埛鍚嶉暱搴﹂渶涓?3-32 涓瓧绗?, trigger: 'blur' },
  ],
}

watch(() => props.modelValue, (open) => {
  if (open) form.username = authStore.user?.username || ''
})

async function submit() {
  await formRef.value?.validate()
  isSaving.value = true
  try {
    await authStore.updateUsername(form.username)
    emit('update:modelValue', false)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '鏇存柊澶辫触')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="淇敼鐢ㄦ埛鍚? width="420px" @update:model-value="emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="鐢ㄦ埛鍚? prop="username">
        <el-input v-model.trim="form.username" maxlength="32" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">鍙栨秷</el-button>
      <el-button type="primary" :loading="isSaving" @click="submit">淇濆瓨</el-button>
    </template>
  </el-dialog>
</template>
```

- [ ] **Step 2: Create password dialog**

Create `frontend/src/components/auth/ChangePasswordDialog.vue`:

```vue
<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const isSaving = ref(false)
const form = reactive({ current_password: '', new_password: '', confirm_password: '' })

const rules: FormRules = {
  current_password: [{ required: true, message: '璇疯緭鍏ュ綋鍓嶅瘑鐮?, trigger: 'blur' }],
  new_password: [
    { required: true, message: '璇疯緭鍏ユ柊瀵嗙爜', trigger: 'blur' },
    { min: 8, max: 128, message: '瀵嗙爜闀垮害闇€涓?8-128 涓瓧绗?, trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '璇峰啀娆¤緭鍏ユ柊瀵嗙爜', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        value === form.new_password ? callback() : callback(new Error('涓ゆ杈撳叆鐨勬柊瀵嗙爜涓嶄竴鑷?))
      },
      trigger: 'blur',
    },
  ],
}

watch(() => props.modelValue, (open) => {
  if (!open) {
    form.current_password = ''
    form.new_password = ''
    form.confirm_password = ''
  }
})

async function submit() {
  await formRef.value?.validate()
  isSaving.value = true
  try {
    await authStore.changePassword({
      current_password: form.current_password,
      new_password: form.new_password,
    })
    emit('update:modelValue', false)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '淇敼澶辫触')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <el-dialog :model-value="modelValue" title="淇敼瀵嗙爜" width="420px" @update:model-value="emit('update:modelValue', $event)">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="褰撳墠瀵嗙爜" prop="current_password">
        <el-input v-model="form.current_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="鏂板瘑鐮? prop="new_password">
        <el-input v-model="form.new_password" type="password" show-password />
      </el-form-item>
      <el-form-item label="纭鏂板瘑鐮? prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">鍙栨秷</el-button>
      <el-button type="primary" :loading="isSaving" @click="submit">淇濆瓨</el-button>
    </template>
  </el-dialog>
</template>
```

- [ ] **Step 3: Update AppSidebar script**

In `frontend/src/components/layout/AppSidebar.vue`, add imports:

```typescript
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import UserProfileDialog from '@/components/auth/UserProfileDialog.vue'
import ChangePasswordDialog from '@/components/auth/ChangePasswordDialog.vue'
```

Add state:

```typescript
const authStore = useAuthStore()
const profileDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const avatarLetter = computed(() => (authStore.user?.username || 'U').slice(0, 1).toUpperCase())

function logout() {
  authStore.logout()
  router.push('/login')
}
```

- [ ] **Step 4: Update AppSidebar template**

Add this block after `<SessionList v-show="!collapsed" />`:

```vue
    <div class="sidebar-user">
      <el-dropdown trigger="click">
        <button class="user-button" type="button">
          <span class="avatar">{{ avatarLetter }}</span>
          <span v-show="!collapsed" class="user-meta">
            <span class="username">{{ authStore.user?.username }}</span>
            <span class="role">{{ authStore.user?.role }}</span>
          </span>
          <el-icon v-show="!collapsed"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="profileDialogVisible = true">淇敼鐢ㄦ埛鍚?/el-dropdown-item>
            <el-dropdown-item @click="passwordDialogVisible = true">淇敼瀵嗙爜</el-dropdown-item>
            <el-dropdown-item divided @click="logout">閫€鍑虹櫥褰?/el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <UserProfileDialog v-model="profileDialogVisible" />
    <ChangePasswordDialog v-model="passwordDialogVisible" />
```

- [ ] **Step 5: Add AppSidebar styles**

Append to `frontend/src/components/layout/AppSidebar.vue` scoped styles:

```css
.sidebar-user {
  margin-top: auto;
  padding: 12px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-button {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.user-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.avatar {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--ops-primary);
  color: #fff;
  font-weight: 800;
}

.user-meta {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.username,
.role {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username {
  font-size: 13px;
  font-weight: 700;
}

.role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.app-sidebar.collapsed .sidebar-user {
  padding: 12px 8px;
}

.app-sidebar.collapsed .user-button {
  justify-content: center;
}
```

- [ ] **Step 6: Run frontend type check**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/auth frontend/src/components/layout/AppSidebar.vue
git commit -m "feat: add sidebar account controls"
```

---

## Task 7: End-to-End Verification and Build

**Files:**
- Modify only if verification reveals defects in files changed by Tasks 1-6.

- [ ] **Step 1: Run backend auth tests**

Run:

```bash
pytest tests/test_auth_service.py tests/test_auth_routes.py -q
```

Expected: PASS.

- [ ] **Step 2: Run existing focused backend tests**

Run:

```bash
pytest tests/test_management_services.py tests/test_log_upload_service.py tests/test_incident_case_memory.py -q
```

Expected: PASS.

- [ ] **Step 3: Run intent and orchestrator contract tests**

Run:

```bash
pytest tests/test_intent.py tests/test_orchestrator_contract.py -q
```

Expected: PASS.

- [ ] **Step 4: Run frontend type check**

Run:

```bash
cd frontend
npx vue-tsc -p tsconfig.app.json --noEmit
```

Expected: PASS.

- [ ] **Step 5: Run frontend build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS and output updates under `ops_agent/api/static/dist/`.

- [ ] **Step 6: Run manual browser flow**

Start backend and frontend:

```bash
uvicorn ops_agent.api.main:app --reload --port 8080
cd frontend
npm run dev
```

Check these flows:

```text
Open / and verify redirect to /login.
When no user exists, verify login page says 鍒涘缓棣栦釜绠＄悊鍛樿处鍙?
Create first user admin / strong-password and verify redirect to /.
Refresh / and verify session persists.
Verify lower-left sidebar shows username and role.
Open 淇敼鐢ㄦ埛鍚? change admin to ops-admin, verify sidebar updates.
Open 淇敼瀵嗙爜, change strong-password to new-strong-password.
Logout and verify redirect to /login.
Verify old password fails and new password succeeds.
Verify direct access to /knowledge redirects to /login when logged out.
Verify after first user exists, /login shows 鐧诲綍 OpsAgent rather than registration mode.
```

- [ ] **Step 7: Inspect diff**

Run:

```bash
git diff -- config/settings.py ops_agent/api frontend/src tests
```

Expected:

```text
Only auth-related backend, frontend, and tests changed.
No runtime database files are included.
No unrelated existing changes are reverted.
```

- [ ] **Step 8: Commit verification fixes**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "fix: polish authentication flow"
```

If no fixes were needed, skip this commit.

---

## Acceptance Criteria

- First visit with no users allows creating exactly one admin account.
- Public registration closes after the first user exists.
- Login returns a Bearer token and current user.
- Existing `/api/*` app routes reject requests without a valid token.
- Auth bootstrap, register, login, health, static assets, and SPA routes remain public.
- Frontend redirects unauthenticated users to `/login`.
- Authenticated users can refresh the page without losing session.
- Sidebar lower-left area displays username and role.
- Users can modify username.
- Users can modify password by providing the current password.
- Logout clears token and returns to `/login`.
- Backend tests pass.
- Frontend type check and build pass.

## Plan Self-Review

- Spec coverage: first-user registration, JWT auth, user info in lower-left sidebar, username editing, password changing, protected API, and validation are covered.
- Completeness scan: the plan contains no unfinished markers or unspecified implementation slots.
- Type consistency: backend response names and frontend TypeScript interfaces use `access_token`, `token_type`, and `user` consistently.
- Scope check: user administration, password reset email, MFA, SSO, and per-user data isolation remain out of scope.




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
                raise RegistrationClosedError("注册已关闭")
            user = self._create_user(session, username, password, role="admin")
            session.commit()
            return self._auth_response(user)

    def login(self, username: str, password: str) -> dict:
        username = self._normalize_username(username)
        with self._session() as session:
            user = session.query(UserModel).filter_by(username=username, is_active=True).first()
            if not user or not self._verify_password(password, user.password_hash):
                raise AuthError("用户名或密码错误")
            user.last_login_at = datetime.now(timezone.utc)
            user.updated_at = datetime.now(timezone.utc)
            session.commit()
            return self._auth_response(user)

    def get_current_user(self, token: str) -> dict:
        payload = self._decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("无效登录状态")
        user = self.get_user_by_id(user_id)
        if not user or not user["is_active"]:
            raise AuthError("无效登录状态")
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
                raise AuthError("用户不存在")
            existing = session.query(UserModel).filter(UserModel.username == username, UserModel.id != user_id).first()
            if existing:
                raise UsernameTakenError("用户名已存在")
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
                raise AuthError("当前密码错误")
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
            raise UsernameTakenError("用户名已存在")
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
                raise AuthError("无效登录状态")
            payload = json.loads(self._b64_decode(payload_b64))
            if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
                raise AuthError("登录已过期")
            return payload
        except AuthError:
            raise
        except Exception as exc:
            raise AuthError("无效登录状态") from exc

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
            raise AuthError("用户名长度需为 3-32 个字符")
        if not all(ch.isalnum() or ch in {"_", "-"} for ch in value):
            raise AuthError("用户名仅支持字母、数字、下划线和短横线")
        return value

    def _validate_password(self, username: str, password: str) -> None:
        if not 8 <= len(password) <= 128:
            raise AuthError("密码长度需为 8-128 个字符")
        if password.lower() == username.lower():
            raise AuthError("密码不能与用户名相同")

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

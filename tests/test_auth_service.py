from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ops_agent.api.models.config_models import Base, UserModel
from ops_agent.api.services.auth_service import (
    AuthError,
    AuthService,
    RegistrationClosedError,
    UsernameTakenError,
)


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

from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from ops_agent.api.dependencies import auth as auth_deps
from ops_agent.api.routes import auth as auth_routes
from ops_agent.api.services.auth_service import AuthService


def build_client(tmp_path: Path) -> TestClient:
    service = AuthService(db_path=tmp_path / "auth.db", jwt_secret="test-secret", token_expire_minutes=60)
    app = FastAPI()
    app.dependency_overrides[auth_routes.get_auth_service] = lambda: service
    app.dependency_overrides[auth_deps.get_auth_service] = lambda: service
    app.include_router(auth_routes.router)

    @app.get("/api/protected", dependencies=[Depends(auth_deps.get_current_user)])
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

"""Authentication API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ops_agent.api.dependencies.auth import get_current_user
from ops_agent.api.services.auth_service import AuthError, AuthService, RegistrationClosedError, UsernameTakenError

router = APIRouter(prefix="/api/auth", tags=["认证"])


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误") from exc


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

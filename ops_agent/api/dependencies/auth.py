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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    try:
        return service.get_current_user(credentials.credentials)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


require_current_user = Depends(get_current_user)

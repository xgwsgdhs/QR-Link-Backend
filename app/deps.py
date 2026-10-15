from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .utils.security import decode_access_token

# HTTP Bearer 认证方案 (Swagger UI 会自动显示锁形图标 🔒)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """从 Authorization: Bearer <token> 请求头中解析并校验当前登录用户"""
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再进行此操作 (未提供身份凭证)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证已失效或伪造，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="该用户账户不存在或已被删除",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_user(current_user: User = Depends(get_current_user)) -> User:
    """普通用户及以上权限检查（只要登录即可）"""
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """管理员专用权限检查 (RBAC 拦截器)"""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：该功能仅限管理员 (ADMIN) 访问与操作"
        )
    return current_user

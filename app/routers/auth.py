from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import UserResponse, UserCreate, LoginRequest, TokenResponse
from ..deps import get_current_user, require_user, require_admin
from ..utils.security import verify_password, create_access_token
from .. import crud

router = APIRouter(prefix="/api/auth", tags=["认证与用户 (Authentication & Users)"])


@router.post("/login", response_model=TokenResponse, summary="用户登录 (获取 JWT 访问令牌)")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """
    用户通过学号/教工号和密码进行身份验证，验证成功后签发标准 JWT 访问令牌。
    """
    user = crud.get_user_by_student_id(db, req.student_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="学号或教工号不存在"
        )
    
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码错误，请重新输入"
        )

    # 签发 JWT Token，payload 中包含用户唯一标识 sub 与角色 role
    access_token = create_access_token({
        "sub": str(user.id),
        "student_id": user.student_id,
        "role": user.role,
        "username": user.username
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse, summary="获取当前登录用户的详细档案 (需登录)")
def get_my_profile(current_user: User = Depends(require_user)):
    """任何已登录用户（普通学生或管理员）可调用此接口获取自己的身份信息与角色"""
    return current_user


@router.post("/register", response_model=UserResponse, summary="注册/录入新用户 (🔒 仅限管理员权限)")
def register_user(
    user_in: UserCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    【权限控制】：必须持有管理员 (ADMIN) Token 才能访问。
    支持录入普通学生 (`USER`) 或新增管理员 (`ADMIN`)。
    """
    existing = crud.get_user_by_student_id(db, user_in.student_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"学号/教工号 {user_in.student_id} 已存在，请勿重复注册")
    return crud.create_user(db, user_in)


@router.get("/users", response_model=List[UserResponse], summary="获取所有系统用户列表 (🔒 仅限管理员权限)")
def get_all_users(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：仅限管理员查阅全校/全系用户花名册"""
    return crud.get_users(db)


@router.delete("/users/{user_id}", summary="删除/注销指定用户 (🔒 仅限管理员权限)")
def delete_user_endpoint(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    【权限控制】：必须持有管理员 (ADMIN) Token 才能访问。
    安全规则：
    1. 不能注销当前登录中的管理员自身账号；
    2. 如果该学生尚有未归还的借用设备，系统会自动拦截并提醒先归还设备；
    3. 用户删除后，其历史审计流水中的关联日志会被级联安全处理。
    """
    return crud.delete_user(db, user_id=user_id, current_admin_id=current_admin.id)


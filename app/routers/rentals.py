from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import RentalCheckoutRequest, RentalCheckinRequest, RentalLogResponse, AssetResponse
from ..deps import require_user, require_admin
from .. import crud

router = APIRouter(prefix="/api/rentals", tags=["借还流转与审计 (Rental & Audit)"])


@router.post("/checkout", response_model=RentalLogResponse, summary="执行借出操作 (🔒 需登录：普通学生/管理员)")
def checkout(
    req: RentalCheckoutRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    【普通用户与管理员核心功能】：
    - 普通学生借用：自动绑定为当前登录学生，无法伪造他人身份。
    - 管理员借用：可直接借出，或指定 `user_id` 代他人办理借用。
    - 数据库执行原子事务：锁定资产为 `RENTED` 并生成不可篡改的时间戳流水。
    """
    target_user_id = current_user.id
    if current_user.role == "ADMIN" and req.user_id:
        target_user_id = req.user_id

    return crud.checkout_asset(db, asset_code=req.asset_code, user_id=target_user_id, remark=req.remark)


@router.post("/checkin", response_model=RentalLogResponse, summary="执行归还操作 (🔒 需登录：借阅本人或管理员)")
def checkin(
    req: RentalCheckinRequest,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """
    【归还权限闭环】：
    - 普通学生：只能归还自己名下借用的器材，防止恶意归还他人设备。
    - 管理员：具有全局兜底归还权限，可强制清点与归还。
    - 自动计算并记录归还时间戳，状态恢复为 `AVAILABLE`。
    """
    is_admin = (current_user.role == "ADMIN")
    return crud.checkin_asset(
        db,
        asset_code=req.asset_code,
        user_id=current_user.id,
        is_admin=is_admin,
        remark=req.remark
    )


@router.get("/my-active", response_model=List[AssetResponse], summary="查询我当前借用中的全部器材 (🔒 需登录)")
def get_my_active_rentals(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """【个人中心】：自动返回当前登录人手头借阅未还的所有物资"""
    return crud.get_user_active_rentals(db, user_id=current_user.id)


@router.get("/logs", response_model=List[RentalLogResponse], summary="查询系统全局借还流水记录 (🔒 仅限管理员)")
def get_all_logs(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：仅限管理员查阅全校/全系历史借还审计流水"""
    return crud.get_rental_logs(db, skip=skip, limit=limit)

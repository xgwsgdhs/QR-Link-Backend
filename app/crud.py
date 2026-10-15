from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from fastapi import HTTPException, status

from .models import User, Asset, RentalLog
from .schemas import AssetCreate, AssetUpdate, UserCreate
from .utils.security import hash_password


# ===================== 用户 CRUD =====================
def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_student_id(db: Session, student_id: str) -> Optional[User]:
    return db.query(User).filter(User.student_id == student_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    user_data = user.model_dump(exclude={"password"})
    hashed_pwd = hash_password(user.password or "123456")
    db_user = User(**user_data, password_hash=hashed_pwd)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int, current_admin_id: Optional[int] = None) -> dict:
    """删除指定用户 (包含禁止自删与未还器材校验)"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="该用户不存在")

    if current_admin_id and user.id == current_admin_id:
        raise HTTPException(status_code=400, detail="操作被拦截：禁止删除当前登录中的管理员自身账号")

    # 业务完整性校验：检查该用户当前是否尚有未归还的在借物资
    active_rentals = db.query(Asset).filter(Asset.current_user_id == user.id, Asset.status == "RENTED").count()
    if active_rentals > 0:
        raise HTTPException(
            status_code=400,
            detail=f"操作被拦截：用户【{user.username}】尚有 {active_rentals} 件未归还的借出设备，请先办理设备归还后再注销用户。"
        )

    username = user.username
    db.delete(user)
    db.commit()
    return {"message": f"用户【{username}】已成功注销删除"}


# ===================== 资产 CRUD =====================
def get_assets(
    db: Session,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Asset]:
    query = db.query(Asset)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Asset.asset_name.ilike(search_pattern)) |
            (Asset.asset_code.ilike(search_pattern)) |
            (Asset.location.ilike(search_pattern))
        )
    if category and category != "全部":
        query = query.filter(Asset.category == category)
    if status_filter and status_filter != "ALL":
        query = query.filter(Asset.status == status_filter)
    
    return query.order_by(Asset.id.desc()).offset(skip).limit(limit).all()


def get_asset_by_id(db: Session, asset_id: int) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).first()


def get_asset_by_code(db: Session, asset_code: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.asset_code == asset_code).first()


def create_asset(db: Session, asset: AssetCreate) -> Asset:
    # 如果没有提供编号，则自动按年份生成自增编号
    code = asset.asset_code
    if not code:
        count = db.query(Asset).count() + 1
        year = datetime.now().year
        code = f"AST-{year}-{count:04d}"

    # 检查编号是否冲突
    if db.query(Asset).filter(Asset.asset_code == code).first():
        raise HTTPException(status_code=400, detail=f"资产编号 {code} 已存在")

    data = asset.model_dump(exclude={"asset_code"})
    db_asset = Asset(asset_code=code, **data)
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def update_asset(db: Session, asset_id: int, asset_in: AssetUpdate) -> Asset:
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    update_data = asset_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_asset, field, val)
        
    db.commit()
    db.refresh(db_asset)
    return db_asset


def update_asset_status(db: Session, asset_id: int, new_status: str, remark: Optional[str] = None) -> Asset:
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    old_status = db_asset.status
    db_asset.status = new_status
    if new_status != "RENTED":
        db_asset.current_user_id = None
        # 如果原先是借出状态，管理员强制调度为空闲或检修时，必须同步闭环借还流水记录
        if old_status == "RENTED":
            active_logs = (
                db.query(RentalLog)
                .filter(RentalLog.asset_id == db_asset.id, RentalLog.return_time == None)
                .all()
            )
            now = datetime.now()
            for log in active_logs:
                log.return_time = now
                log.updated_status = new_status
                note = f"[管理员调度归还: {new_status}]"
                if remark:
                    note += f" {remark}"
                log.remark = (log.remark + " | " if log.remark else "") + note
        
    db.commit()
    db.refresh(db_asset)
    return db_asset


def delete_asset(db: Session, asset_id: int):
    db_asset = get_asset_by_id(db, asset_id)
    if not db_asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if db_asset.status == "RENTED":
        raise HTTPException(status_code=400, detail="该物资当前处于借出状态，无法删除")
    db.delete(db_asset)
    db.commit()


# ===================== 借还核心事务 =====================
def checkout_asset(db: Session, asset_code: str, user_id: int, remark: Optional[str] = None) -> RentalLog:
    """原子化借出事务处理"""
    asset = get_asset_by_code(db, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail=f"未找到编号为 {asset_code} 的物资")
    
    if asset.status == "RENTED":
        borrower_name = asset.current_user.username if asset.current_user else "其他用户"
        raise HTTPException(status_code=400, detail=f"该物资已被【{borrower_name}】借用中，暂不可借")
    
    if asset.status == "MAINTENANCE":
        raise HTTPException(status_code=400, detail="该物资正在维修或检修中，暂不可借用")
        
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户信息不存在，请先登录")
        
    # 原子操作: 更新资产状态并插入借阅流水
    old_status = asset.status
    asset.status = "RENTED"
    asset.current_user_id = user.id

    log = RentalLog(
        asset_id=asset.id,
        user_id=user.id,
        rental_time=datetime.now(),
        return_time=None,
        previous_status=old_status,
        updated_status="RENTED",
        remark=remark
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def checkin_asset(db: Session, asset_code: str, user_id: Optional[int] = None, is_admin: bool = False, remark: Optional[str] = None) -> RentalLog:
    """原子化归还事务处理"""
    asset = get_asset_by_code(db, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail=f"未找到编号为 {asset_code} 的物资")
    
    if asset.status != "RENTED":
        raise HTTPException(status_code=400, detail="该物资当前并非借出状态，无需归还")

    # 如果不是管理员，必须是该物品的借用人才能办理归还
    if not is_admin and user_id and asset.current_user_id and asset.current_user_id != user_id:
        borrower_name = asset.current_user.username if asset.current_user else "其他同学"
        raise HTTPException(
            status_code=403,
            detail=f"无权归还：该设备当前由【{borrower_name}】借用，非本人操作。如需强制交还请联系管理员。"
        )
        
    # 查找该资产最近未归还的借出流水记录
    active_log = (
        db.query(RentalLog)
        .filter(RentalLog.asset_id == asset.id, RentalLog.return_time == None)
        .order_by(RentalLog.id.desc())
        .first()
    )
    
    now = datetime.now()
    if active_log:
        active_log.return_time = now
        active_log.updated_status = "AVAILABLE"
        if remark:
            active_log.remark = (active_log.remark or "") + (" | " if active_log.remark else "") + remark
    else:
        # 兼容容错机制
        active_log = RentalLog(
            asset_id=asset.id,
            user_id=asset.current_user_id or 1,
            rental_time=now,
            return_time=now,
            previous_status="RENTED",
            updated_status="AVAILABLE",
            remark=remark or "手动校正归还"
        )
        db.add(active_log)

    # 恢复资产状态
    asset.status = "AVAILABLE"
    asset.current_user_id = None

    db.commit()
    db.refresh(active_log)
    return active_log


def get_user_active_rentals(db: Session, user_id: int) -> List[Asset]:
    """查询指定用户当前借用中的全部物资"""
    return db.query(Asset).filter(Asset.current_user_id == user_id, Asset.status == "RENTED").all()


def get_rental_logs(db: Session, skip: int = 0, limit: int = 50) -> List[RentalLog]:
    """按时间倒序获取借还流水记录"""
    return db.query(RentalLog).order_by(RentalLog.id.desc()).offset(skip).limit(limit).all()


# ===================== 统计数据 =====================
def get_stats_summary(db: Session) -> dict:
    total_assets = db.query(Asset).count()
    available_assets = db.query(Asset).filter(Asset.status == "AVAILABLE").count()
    rented_assets = db.query(Asset).filter(Asset.status == "RENTED").count()
    maintenance_assets = db.query(Asset).filter(Asset.status == "MAINTENANCE").count()
    total_rentals_count = db.query(RentalLog).count()
    active_users_count = db.query(User).count()

    return {
        "total_assets": total_assets,
        "available_assets": available_assets,
        "rented_assets": rented_assets,
        "maintenance_assets": maintenance_assets,
        "total_rentals_count": total_rentals_count,
        "active_users_count": active_users_count
    }


def get_hot_assets(db: Session, limit: int = 5) -> list:
    """获取借用频次最高的物资排行 (用于采购与资源调配决策)"""
    results = (
        db.query(
            Asset.id,
            Asset.asset_code,
            Asset.asset_name,
            Asset.category,
            func.count(RentalLog.id).label("borrow_count")
        )
        .join(RentalLog, Asset.id == RentalLog.asset_id)
        .group_by(Asset.id)
        .order_by(desc("borrow_count"))
        .limit(limit)
        .all()
    )

    return [
        {
            "asset_id": r[0],
            "asset_code": r[1],
            "asset_name": r[2],
            "category": r[3],
            "borrow_count": r[4]
        }
        for r in results
    ]

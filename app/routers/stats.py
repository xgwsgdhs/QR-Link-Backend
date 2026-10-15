from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import StatsSummary, HotAssetItem
from ..deps import require_user, require_admin
from .. import crud

router = APIRouter(prefix="/api/stats", tags=["统计分析与看板 (Stats & Dashboard)"])


@router.get("/summary", response_model=StatsSummary, summary="获取全局核心指标概览 (🔒 需登录)")
def get_summary(
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db)
):
    """【仪表盘看板】：返回总物资数、可用数、在借数、维修数与累计借还量"""
    return crud.get_stats_summary(db)


@router.get("/hot-assets", response_model=List[HotAssetItem], summary="热门借调排行榜 (🔒 仅限管理员)")
def get_hot_assets(
    limit: int = 5,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【决策分析】：按历史借用频次统计高频使用器材，辅助实验室采购与资源再分配"""
    return crud.get_hot_assets(db, limit=limit)

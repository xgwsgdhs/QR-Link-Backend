from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import AssetResponse, AssetCreate, AssetUpdate, AssetStatusUpdate
from ..deps import require_admin
from ..utils.qr_generator import create_qr_code_image
from .. import crud

router = APIRouter(prefix="/api/assets", tags=["物资资产管理 (Assets Management)"])


@router.get("", response_model=List[AssetResponse], summary="查询资产列表 (公开访问：支持搜索/分类/状态筛选)")
def list_assets(
    search: Optional[str] = Query(None, description="搜索关键词 (物资名称 / 资产编号 / 存放地点)"),
    category: Optional[str] = Query(None, description="类别筛选 (如: 实验器材 / 开发套件 / 专业书籍 / 工具设备)"),
    status: Optional[str] = Query(None, description="状态筛选: ALL(全部) / AVAILABLE(可借用) / RENTED(已借出) / MAINTENANCE(维修检修)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    【普通用户与管理员均可查阅】：
    用于移动端或电脑端浏览共享物资库存、空闲可借数量与详细规格。
    """
    return crud.get_assets(db, search=search, category=category, status_filter=status, skip=skip, limit=limit)


@router.get("/by-code/{asset_code}", response_model=AssetResponse, summary="扫码反查资产状态 (公开访问)")
def get_asset_by_code(asset_code: str, db: Session = Depends(get_db)):
    """
    【手机端核心接口】：
    用户手机扫一扫二维码后，直接通过解析出的编号获取该物资当前状态（可借/在借/维修）。
    """
    asset = crud.get_asset_by_code(db, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail=f"未找到编号为 {asset_code} 的物资")
    return asset


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取单个资产详情 (公开访问)")
def get_asset_detail(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@router.post("", response_model=AssetResponse, summary="录入新资产并生成编号 (🔒 仅限管理员)")
def create_new_asset(
    asset_in: AssetCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：必须持有管理员 (ADMIN) Token 才能登记新设备入库"""
    return crud.create_asset(db, asset_in)


@router.put("/{asset_id}", response_model=AssetResponse, summary="编辑物资基本信息 (🔒 仅限管理员)")
def edit_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：仅管理员可修改资产名称、类别、存放地点等"""
    return crud.update_asset(db, asset_id, asset_in)


@router.put("/{asset_id}/status", response_model=AssetResponse, summary="手动强制变更资产状态 (🔒 仅限管理员)")
def change_asset_status(
    asset_id: int,
    status_in: AssetStatusUpdate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：仅管理员可手动报修、检修或锁定设备"""
    return crud.update_asset_status(db, asset_id, status_in.status, status_in.remark)


@router.delete("/{asset_id}", summary="删除资产 (🔒 仅限管理员)")
def delete_asset_endpoint(
    asset_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """【权限控制】：仅管理员可报废/删除未借出的器材"""
    crud.delete_asset(db, asset_id)
    return {"message": "删除成功"}


@router.get("/{asset_id}/qr-image", summary="生成并下载单张规范的资产二维码贴纸 (PNG 物理标签)")
def get_asset_qr_image(asset_id: int, db: Session = Depends(get_db)):
    asset = crud.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    img_bytes = create_qr_code_image(
        content=asset.asset_code,
        label=asset.asset_name,
        sub_label=asset.asset_code
    )
    return Response(content=img_bytes, media_type="image/png")


@router.get("/by-code/{asset_code}/qr-image", summary="通过编号直接获取二维码贴纸 (PNG)")
def get_asset_qr_image_by_code(asset_code: str, db: Session = Depends(get_db)):
    asset = crud.get_asset_by_code(db, asset_code)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")

    img_bytes = create_qr_code_image(
        content=asset.asset_code,
        label=asset.asset_name,
        sub_label=asset.asset_code
    )
    return Response(content=img_bytes, media_type="image/png")

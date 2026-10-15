from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ===================== 用户 Schema =====================
class UserBase(BaseModel):
    username: str
    student_id: str
    role: str = "USER"
    department: str = "软件工程 (소프트웨어공학과)"
    contact: Optional[str] = None


class UserCreate(UserBase):
    password: str = "123456"


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    student_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse



# ===================== 资产 Schema =====================
class AssetBase(BaseModel):
    asset_name: str
    category: str = "实验器材"
    location: str = "艺林馆 1120室 (예림관 1120호)"
    description: Optional[str] = None


class AssetCreate(AssetBase):
    asset_code: Optional[str] = None  # 可由前端传入，或后端自动生成


class AssetUpdate(BaseModel):
    asset_name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class AssetStatusUpdate(BaseModel):
    status: str  # AVAILABLE, RENTED, MAINTENANCE
    remark: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    asset_code: str
    status: str
    current_user_id: Optional[int] = None
    current_user_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================== 借还 Schema =====================
class RentalCheckoutRequest(BaseModel):
    asset_code: str
    user_id: Optional[int] = None  # 可选：普通用户默认自身，管理员可代他人借出
    remark: Optional[str] = None


class RentalCheckinRequest(BaseModel):
    asset_code: str
    remark: Optional[str] = None


class RentalLogResponse(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    asset_name: str
    user_id: int
    username: str
    student_id: str
    rental_time: datetime
    return_time: Optional[datetime] = None
    previous_status: str
    updated_status: str
    remark: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ===================== 数据统计 Schema =====================
class StatsSummary(BaseModel):
    total_assets: int
    available_assets: int
    rented_assets: int
    maintenance_assets: int
    total_rentals_count: int
    active_users_count: int


class HotAssetItem(BaseModel):
    asset_id: int
    asset_code: str
    asset_name: str
    category: str
    borrow_count: int

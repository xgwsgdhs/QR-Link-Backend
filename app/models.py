from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """用户实体 (普通学生 / 管理员)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=False, comment="学生/教师姓名")
    student_id = Column(String(32), unique=True, index=True, nullable=False, comment="学号或教工号")
    password_hash = Column(String(128), nullable=False, default="", comment="加密哈希密码")
    role = Column(String(16), default="USER", nullable=False, comment="角色: USER(普通用户) / ADMIN(管理员)")
    department = Column(String(64), default="软件工程 (소프트웨어공학과)", comment="院系/专业")
    contact = Column(String(32), nullable=True, comment="联系方式")
    created_at = Column(DateTime, default=datetime.now)

    # 关联借阅日志
    rental_logs = relationship("RentalLog", back_populates="user", cascade="all, delete-orphan")
    borrowed_assets = relationship("Asset", back_populates="current_user")


class Asset(Base):
    """共享资产实体"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(64), unique=True, index=True, nullable=False, comment="唯一资产编号，如 AST-2026-0001")
    asset_name = Column(String(128), nullable=False, comment="资产名称")
    category = Column(String(64), nullable=False, default="实验器材", comment="分类: 实验器材/专业书籍/开发套件/工具设备")
    status = Column(String(16), default="AVAILABLE", nullable=False, comment="状态: AVAILABLE(可用) / RENTED(借出) / MAINTENANCE(维修中)")
    location = Column(String(128), default="艺林馆 1120室 (예림관 1120호)", comment="存放位置")
    description = Column(Text, nullable=True, comment="物资规格或借用须知")
    
    # 当前借用人 (如果是借出状态)
    current_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    current_user = relationship("User", back_populates="borrowed_assets")

    @property
    def current_user_name(self):
        return self.current_user.username if self.current_user else None

    created_at = Column(DateTime, default=datetime.now)

    # 关联借还记录
    rental_logs = relationship("RentalLog", back_populates="asset", cascade="all, delete-orphan")


class RentalLog(Base):
    """借还流水审计日志实体"""
    __tablename__ = "rental_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    rental_time = Column(DateTime, default=datetime.now, nullable=False, comment="借出时间戳")
    return_time = Column(DateTime, nullable=True, comment="归还时间戳(归还后填充)")
    
    previous_status = Column(String(16), default="AVAILABLE")
    updated_status = Column(String(16), default="RENTED")
    remark = Column(String(255), nullable=True, comment="归还备注或状态说明")

    asset = relationship("Asset", back_populates="rental_logs")
    user = relationship("User", back_populates="rental_logs")

    @property
    def asset_code(self) -> str:
        return self.asset.asset_code if self.asset else ""

    @property
    def asset_name(self) -> str:
        return self.asset.asset_name if self.asset else ""

    @property
    def username(self) -> str:
        return self.user.username if self.user else ""

    @property
    def student_id(self) -> str:
        return self.user.student_id if self.user else ""


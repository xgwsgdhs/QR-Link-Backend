from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import User, Asset, RentalLog
from ..utils.security import hash_password


def init_database_data(db: Session):
    """如果数据库为空，自动初始化系统基础演示物资与匿名测试账号"""
    if db.query(User).count() > 0:
        return  # 已经有数据，跳过初始化

    default_pwd_hash = hash_password("123456")

    # 1. 插入通用脱敏演示账号 (初始统一默认密码: 123456)
    users = [
        User(username="系统管理员 (Admin)", student_id="admin", password_hash=default_pwd_hash, role="ADMIN", department="信息技术中心 (IT Center)", contact="010-0000-0000"),
        User(username="测试学生A (Student A)", student_id="20240001", password_hash=default_pwd_hash, role="USER", department="软件工程专业 (소프트웨어공학과)", contact="010-0000-0001"),
        User(username="测试学生B (Student B)", student_id="20240002", password_hash=default_pwd_hash, role="USER", department="计算机科学专业 (컴퓨터공학과)", contact="010-0000-0002"),
        User(username="指导教师 (Advisor)", student_id="TEACHER-01", password_hash=default_pwd_hash, role="ADMIN", department="软件工程专业 (소프트웨어공학과)", contact="010-0000-0003"),
    ]
    for u in users:
        db.add(u)
    db.commit()

    # 2. 插入大学实验室与共享空间典型共享物资 (全部附带中文详细标注)
    now = datetime.now()
    user_student_a = db.query(User).filter(User.student_id == "20240001").first()

    assets = [
        Asset(
            asset_code="AST-2026-0001",
            asset_name="索尼 A7M4 专业单反相机套件",
            category="实验器材",
            status="AVAILABLE",
            location="艺林馆 1120室 (예림관 1120호 - 器材柜 A-1)",
            description="含 24-70mm 变焦镜头与备用电池2块，供学术活动宣传拍摄使用。"
        ),
        Asset(
            asset_code="AST-2026-0002",
            asset_name="树莓派 4B 嵌入式边缘计算套件",
            category="开发套件",
            status="RENTED",
            location="软件工程创新实验室 (소프트웨어 실습실 - 工位 B-04)",
            description="8GB 内存版本，带散热铝合金外壳与 64GB TF 卡，预装 Ubuntu Server。",
            current_user_id=user_student_a.id if user_student_a else None
        ),
        Asset(
            asset_code="AST-2026-0003",
            asset_name="Arduino 物联网多传感器实训套件",
            category="开发套件",
            status="AVAILABLE",
            location="艺林馆 1120室 (예림관 1120호 - 开发箱 03)",
            description="包含温湿度传感器、超声波测距模块、RFID读卡模块及扩展面包板。"
        ),
        Asset(
            asset_code="AST-2026-0004",
            asset_name="大疆 DJI Mini 3 航模实训无人机",
            category="实验器材",
            status="AVAILABLE",
            location="创客空间 A区 (메이커스페이스 A구역 - 储物柜 02)",
            description="需向指导老师报备后使用，飞行前请仔细检查螺旋桨与传感器状态。"
        ),
        Asset(
            asset_code="AST-2026-0005",
            asset_name="《深度学习与计算机视觉实战》实验教材",
            category="专业书籍",
            status="AVAILABLE",
            location="实验室资料角 (자료실 도서코너 - 书架 2层)",
            description="专业实训参考书籍，单次最长借用周期 14 天。"
        ),
        Asset(
            asset_code="AST-2026-0006",
            asset_name="3D打印机专用工具箱与数显电烙铁",
            category="工具设备",
            status="MAINTENANCE",
            location="创客空间 B区 (메이커스페이스 B구역 - 工具架)",
            description="电烙铁数显控温模块检修中，预计下周恢复可用状态。"
        )
    ]
    for a in assets:
        db.add(a)
    db.commit()

    # 3. 插入初始借还流水日志 (用于演示历史记录与数据大屏)
    asset_cam = db.query(Asset).filter(Asset.asset_code == "AST-2026-0001").first()
    asset_pi = db.query(Asset).filter(Asset.asset_code == "AST-2026-0002").first()
    user_student_b = db.query(User).filter(User.student_id == "20240002").first()

    logs = []
    # 历史记录1: 相机已借出并已完好归还
    if asset_cam and user_student_b:
        logs.append(RentalLog(
            asset_id=asset_cam.id,
            user_id=user_student_b.id,
            rental_time=now - timedelta(days=3, hours=5),
            return_time=now - timedelta(days=2),
            previous_status="AVAILABLE",
            updated_status="AVAILABLE",
            remark="学院活动宣传拍摄完毕，机身及镜头完好归还"
        ))
    # 历史记录2: 树莓派当前在借中
    if asset_pi and user_student_a:
        logs.append(RentalLog(
            asset_id=asset_pi.id,
            user_id=user_student_a.id,
            rental_time=now - timedelta(days=1, hours=3),
            return_time=None,
            previous_status="AVAILABLE",
            updated_status="RENTED",
            remark="用于物联网课程期末大作业实验验证"
        ))

    for log in logs:
        db.add(log)
    db.commit()
    print(">>> 初始测试数据装载完成：系统管理员 + 测试学生 + 典型物资 + 审计流水")

#!/usr/bin/env python3
"""
QR-Link 管理员账号初始化 / 注册脚本 (Bootstrap Admin Script)
使用场景：
1. 项目刚克隆到新电脑，快速创建首个管理员账号 (admin)
2. 忘记管理员密码时，可通过此脚本直接覆盖重置密码
"""

import sys
import os
import argparse
import getpass

# 确保脚本能在任何工作目录下正确识别 app 模块
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app.database import engine, Base, SessionLocal
from app.models import User
from app.utils.security import hash_password


def init_admin():
    parser = argparse.ArgumentParser(description="QR-Link: 初始化创建系统管理员账号 (Admin)")
    parser.add_argument("--student-id", "-u", dest="student_id", help="管理员登录账号/工号 (默认: admin)")
    parser.add_argument("--name", "-n", dest="username", help="管理员显示姓名 (默认: 超级管理员)")
    parser.add_argument("--password", "-p", dest="password", help="管理员登录密码 (默认交互式输入)")
    parser.add_argument("--dept", "-d", dest="department", default="系统管理中心", help="所属院系/部门")
    parser.add_argument("--contact", "-c", dest="contact", default="010-8888-8888", help="联系电话")
    parser.add_argument("--non-interactive", action="store_true", help="非交互模式 (使用全套默认值一键创建)")

    args = parser.parse_args()

    # 1. 确保数据库与数据表已建立
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("=" * 60)
    print("   QR-Link: 共享资源管理系统 · 首个管理员账号注册工具")
    print("=" * 60)

    try:
        # 2. 获取参数 (支持交互式引导与命令行参数)
        if args.non_interactive:
            student_id = args.student_id or "admin"
            username = args.username or "超级管理员 (Admin)"
            password = args.password or "admin123"
            department = args.department
            contact = args.contact
        else:
            # 交互式引导输入 (按回车使用中括号中的默认推荐值)
            default_id = args.student_id or "admin"
            input_id = input(f"请输入管理员登录账号/工号 [{default_id}]: ").strip()
            student_id = input_id if input_id else default_id

            default_name = args.username or "超级管理员 (Admin)"
            input_name = input(f"请输入管理员姓名 [{default_name}]: ").strip()
            username = input_name if input_name else default_name

            if args.password:
                password = args.password
            else:
                while True:
                    input_pwd = getpass.getpass("请输入管理员密码 (输入时不显式回显，建议至少6位) [admin123]: ").strip()
                    if not input_pwd:
                        password = "admin123"
                        break
                    if len(input_pwd) < 6:
                        print("⚠️  密码长度建议不少于 6 位，请重新输入！")
                        continue
                    confirm_pwd = getpass.getpass("请再次确认密码: ").strip()
                    if input_pwd != confirm_pwd:
                        print("❌ 两次输入的密码不一致，请重新输入！\n")
                        continue
                    password = input_pwd
                    break

            department = args.department
            contact = args.contact

        # 3. 检查账号是否已存在
        existing_user = db.query(User).filter(User.student_id == student_id).first()
        if existing_user:
            print(f"\n⚠️  发现账号【{student_id}】已存在 (当前用户名: {existing_user.username}, 角色: {existing_user.role})")
            if not args.non_interactive:
                choice = input("是否将该账号重置为管理员并更新密码？(y/N): ").strip().lower()
                if choice != 'y':
                    print("已取消操作。")
                    return
            
            # 更新现有账号为 ADMIN 并重置密码
            existing_user.username = username
            existing_user.role = "ADMIN"
            existing_user.password_hash = hash_password(password)
            existing_user.department = department
            existing_user.contact = contact
            db.commit()
            db.refresh(existing_user)
            print("\n✅ 账号已成功重置为管理员并更新密码！")
        else:
            # 创建全新管理员
            new_admin = User(
                username=username,
                student_id=student_id,
                password_hash=hash_password(password),
                role="ADMIN",
                department=department,
                contact=contact
            )
            db.add(new_admin)
            db.commit()
            db.refresh(new_admin)
            print("\n🎉 首个管理员账号创建成功！")

        # 4. 打印凭据与快速使用指引
        print("-" * 60)
        print("【管理员凭据详情】：")
        print(f"  • 登录账号 (student_id) : {student_id}")
        print(f"  • 登录密码 (password)   : {password}")
        print(f"  • 姓名与角色 (role)     : {username} [ADMIN]")
        print("-" * 60)
        print("【下一步测试指引】：")
        print("  1. 启动后端服务: python main.py")
        print("  2. 在浏览器打开接口文档: http://127.0.0.1:8000/docs")
        print("  3. 调用 POST /api/auth/login 接口，使用上述账号密码登录换取 Token！")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\n已取消注册。")
    finally:
        db.close()


if __name__ == "__main__":
    init_admin()

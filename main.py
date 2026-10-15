from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, SessionLocal
from app.utils.init_data import init_database_data
from app.routers import auth, assets, rentals, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动创建所有数据库表并装载测试数据
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_database_data(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="QR-Link: 基于二维码的共享资源管理及租赁追踪系统",
    description="新韩大学 SW中心大学事业团 · 产学联动 SW项目 (Microstone) API 后端服务",
    version="1.0.0",
    lifespan=lifespan
)

# 允许跨域请求 (CORS)，方便前端 Vue 3 本地热开发与手机局域网扫码直连
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册功能路由
app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(rentals.router)
app.include_router(stats.router)


@app.get("/", tags=["系统根路径"])
def root():
    return {
        "project": "QR-Link 共享资源管理与租赁追踪系统 (微石项目 / 마이크로스톤)",
        "status": "online",
        "version": "1.0.0",
        "docs_url": "/docs",
        "message": "后端服务运行正常，请访问 /docs 查看交互式接口文档"
    }


if __name__ == "__main__":
    import uvicorn
    # host 设为 0.0.0.0，使手机和电脑在同一个 WiFi 下可以直接访问
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

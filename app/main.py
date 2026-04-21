# -*- coding: utf-8 -*-
"""
FastAPI主应用入口
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, applications
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import JSONResponse

# 添加xtquant包到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import get_settings
from app.routers import data, health, strategy, trading, websocket
from app.utils.exceptions import XTQuantException
from app.utils.helpers import format_response
from app.utils.logger import configure_logging, logger


def reset_api_docs(swagger_ui_version: str = "5", redoc_version: str = "2") -> None:
    """修复 Swagger UI 和 ReDoc API 文档 CDN 无法访问的问题"""
    swagger_css_url = f"https://unpkg.com/swagger-ui-dist@{swagger_ui_version}/swagger-ui.css"
    swagger_js_url = f"https://unpkg.com/swagger-ui-dist@{swagger_ui_version}/swagger-ui-bundle.js"
    redoc_js_url = f"https://unpkg.com/redoc@{redoc_version}/bundles/redoc.standalone.js"

    def swagger_monkey_patch(*args, **kwargs):
        return get_swagger_ui_html(
            *args, **kwargs,
            swagger_css_url=swagger_css_url,
            swagger_js_url=swagger_js_url,
        )

    def redoc_monkey_patch(*args, **kwargs):
        return get_redoc_html(*args, **kwargs, redoc_js_url=redoc_js_url)

    applications.get_swagger_ui_html = swagger_monkey_patch
    applications.get_redoc_html = redoc_monkey_patch
    logger.debug("API docs CDN URLs have been successfully patched")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    configure_logging(
        log_level=settings.logging.level,
        log_file=settings.logging.file or "logs/app.log",
        error_log_file=settings.logging.error_file or "logs/error.log",
        log_format=settings.logging.format,
        rotation=settings.logging.rotation,
        retention=settings.logging.retention,
        compression=settings.logging.compression,
    )

    import asyncio
    from app.dependencies import get_subscription_manager

    try:
        loop = asyncio.get_running_loop()
        subscription_manager = get_subscription_manager(settings)
        subscription_manager.set_event_loop(loop)
        logger.info("订阅管理器已初始化")
    except Exception as e:
        logger.warning(f"订阅管理器初始化失败: {e}")

    logger.info("REST API 服务已就绪")

    yield

    logger.info("REST API 服务正在关闭...")
    try:
        subscription_manager = get_subscription_manager(settings)
        subscription_manager.shutdown()
        logger.info("订阅管理器已关闭")
    except Exception as e:
        logger.error(f"关闭订阅管理器失败: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="xtquant-proxy",
    description="基于xtquant的量化交易代理服务（支持多策略并行）",
    version="1.1.0",
    lifespan=lifespan,
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

reset_api_docs()


# 全局异常处理
@app.exception_handler(XTQuantException)
async def xtquant_exception_handler(request: Request, exc: XTQuantException):
    return JSONResponse(
        status_code=500,
        content=format_response(data=None, message=exc.message, success=False, code=500),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=format_response(data=None, message=str(exc.detail), success=False, code=exc.status_code),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=format_response(data=None, message=f"内部服务器错误: {str(exc)}", success=False, code=500),
    )


# 注册路由
app.include_router(health.router)
app.include_router(data.router)
app.include_router(trading.router)
app.include_router(websocket.router)
app.include_router(strategy.router)


@app.get("/")
async def root():
    """根路径"""
    settings = get_settings()
    return format_response(
        data={
            "app_name": settings.app.name,
            "app_version": settings.app.version,
            "xtquant_mode": settings.xtquant.mode.value,
            "description": "基于xtquant的量化交易代理服务（支持多策略并行）",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
        },
        message="欢迎使用xtquant-proxy服务",
    )


@app.get("/info")
async def app_info():
    """应用信息"""
    settings = get_settings()
    return format_response(
        data={
            "name": settings.app.name,
            "version": settings.app.version,
            "debug": settings.app.debug,
            "host": settings.app.host,
            "port": settings.app.port,
            "log_level": settings.logging.level,
            "xtquant_mode": settings.xtquant.mode.value,
            "allow_real_trading": settings.xtquant.trading.allow_real_trading,
        },
        message="应用信息获取成功",
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=False,
        reload_includes=None,
        log_level=settings.logging.level.lower(),
    )
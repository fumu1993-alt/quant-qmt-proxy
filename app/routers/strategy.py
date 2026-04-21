# -*- coding: utf-8 -*-
"""
策略管理 REST API 路由
"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_strategy_manager, verify_api_key
from app.models.strategy_models import (
    StrategyActionRequest,
    StrategyInfo,
    StrategyListResponse,
    StrategyPnLReport,
    StrategyRegisterRequest,
    StrategyRegisterResponse,
)
from app.services.strategy_manager import StrategyManager
from app.utils.helpers import format_response

router = APIRouter(prefix="/api/v1/strategy", tags=["策略管理"])


@router.post("/register", response_model=StrategyRegisterResponse, summary="注册策略")
async def register_strategy(
    request: StrategyRegisterRequest,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """注册一个新策略，分配资金和风控参数"""
    result = manager.register_strategy(request)
    return StrategyRegisterResponse(**result)


@router.post("/{strategy_id}/start", summary="启动策略")
async def start_strategy(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """启动已注册的策略"""
    result = manager.start_strategy(strategy_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return format_response(data={"strategy_id": strategy_id}, message=result["message"])


@router.post("/{strategy_id}/pause", summary="暂停策略")
async def pause_strategy(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """暂停策略（保留持仓，停止新交易）"""
    result = manager.pause_strategy(strategy_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return format_response(data={"strategy_id": strategy_id}, message=result["message"])


@router.post("/{strategy_id}/stop", summary="停止策略")
async def stop_strategy(
    strategy_id: str,
    request: StrategyActionRequest = StrategyActionRequest(),
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """停止策略并注销"""
    result = manager.stop_strategy(strategy_id, force_liquidate=request.force_liquidate)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return format_response(data=result, message=result["message"])


@router.get("/list", response_model=StrategyListResponse, summary="列出所有策略")
async def list_strategies(
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """获取所有已注册策略的列表"""
    strategies = manager.list_strategies()
    total_allocated = sum(s.allocated_capital for s in strategies)
    return StrategyListResponse(
        strategies=strategies,
        total_count=len(strategies),
        total_allocated_capital=total_allocated,
    )


@router.get("/{strategy_id}/status", summary="获取策略状态")
async def get_strategy_status(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """获取策略详情和当前状态"""
    info = manager.get_strategy_info(strategy_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return format_response(data=info.model_dump(), message="获取成功")


@router.get("/{strategy_id}/pnl", response_model=StrategyPnLReport, summary="策略盈亏报告")
async def get_strategy_pnl(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """获取策略的详细盈亏报告"""
    report = manager.get_pnl_report(strategy_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return report


@router.get("/{strategy_id}/positions", summary="策略虚拟持仓")
async def get_strategy_positions(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """获取策略的虚拟持仓列表"""
    positions = manager.virtual_account_mgr.get_virtual_positions(strategy_id)
    return format_response(
        data=[p.model_dump() for p in positions],
        message=f"持仓数: {len(positions)}",
    )


@router.get("/{strategy_id}/orders", summary="策略订单查询")
async def get_strategy_orders(
    strategy_id: str,
    api_key: str = Depends(verify_api_key),
    manager: StrategyManager = Depends(get_strategy_manager),
):
    """获取策略的订单列表（从虚拟账户查询）"""
    account = manager.virtual_account_mgr.get_account(strategy_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    return format_response(
        data={
            "strategy_id": strategy_id,
            "total_trades": account.total_trades,
            "win_trades": account.win_trades,
            "loss_trades": account.loss_trades,
        },
        message="获取成功",
    )
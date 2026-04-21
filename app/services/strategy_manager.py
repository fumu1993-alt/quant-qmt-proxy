# -*- coding: utf-8 -*-
"""
策略调度器 — 管理策略的生命周期

职责:
- 策略注册/注销
- 启动/暂停/停止
- 策略状态查询
- 盈亏报告生成
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.models.strategy_models import (
    StrategyConfig,
    StrategyInfo,
    StrategyPnLReport,
    StrategyRegisterRequest,
    StrategyStatus,
    VirtualPosition,
)
from app.services.virtual_account_manager import VirtualAccount, VirtualAccountManager
from app.utils.logger import logger


class StrategyManager:
    """策略生命周期管理器"""

    def __init__(self, total_capital: float = 0.0):
        self.virtual_account_mgr = VirtualAccountManager(total_capital)
        self._strategies: Dict[str, StrategyConfig] = {}  # strategy_id -> config
        self._strategy_names: Dict[str, str] = {}  # strategy_name -> strategy_id

    def set_total_capital(self, total_capital: float):
        """设置总资金（从QMT真实账户获取后设置）"""
        self.virtual_account_mgr.set_total_capital(total_capital)
        logger.info(f"[策略管理器] 总资金设置为: {total_capital:.2f}")

    def register_strategy(self, request: StrategyRegisterRequest) -> dict:
        """
        注册策略

        Returns: {"success": bool, "message": str, "strategy_id": str, "strategy_info": StrategyInfo}
        """
        # 检查名称重复
        if request.strategy_name in self._strategy_names:
            existing_id = self._strategy_names[request.strategy_name]
            return {
                "success": False,
                "message": f"策略名称 '{request.strategy_name}' 已存在 (ID: {existing_id})",
                "strategy_id": None,
                "strategy_info": None,
            }

        # 生成策略ID
        strategy_id = f"strategy_{uuid.uuid4().hex[:8]}"

        # 构建配置
        config = StrategyConfig(
            strategy_name=request.strategy_name,
            strategy_type=request.strategy_type,
            allocated_capital=request.allocated_capital,
            max_positions=request.max_positions,
            max_single_position_ratio=request.max_single_position_ratio,
            description=request.description,
            risk_params=request.risk_params,
        )

        # 创建虚拟账户（会校验资金是否足够）
        try:
            self.virtual_account_mgr.create_account(strategy_id, config)
        except ValueError as e:
            return {
                "success": False,
                "message": str(e),
                "strategy_id": None,
                "strategy_info": None,
            }

        # 注册策略
        self._strategies[strategy_id] = config
        self._strategy_names[request.strategy_name] = strategy_id

        info = self._build_strategy_info(strategy_id, config)

        logger.info(
            f"[策略管理器] 策略已注册: {strategy_id} ({request.strategy_name}), "
            f"分配资金: {request.allocated_capital:.2f}"
        )

        return {
            "success": True,
            "message": "策略注册成功",
            "strategy_id": strategy_id,
            "strategy_info": info,
        }

    def start_strategy(self, strategy_id: str) -> dict:
        """启动策略"""
        account = self.virtual_account_mgr.get_account(strategy_id)
        if account is None:
            return {"success": False, "message": f"策略 {strategy_id} 未注册"}

        if account.status == StrategyStatus.RUNNING:
            return {"success": False, "message": "策略已在运行中"}

        account.status = StrategyStatus.RUNNING
        account.last_update_time = datetime.now()
        logger.info(f"[策略管理器] 策略已启动: {strategy_id}")
        return {"success": True, "message": "策略已启动"}

    def pause_strategy(self, strategy_id: str) -> dict:
        """暂停策略（不平仓，停止新交易）"""
        account = self.virtual_account_mgr.get_account(strategy_id)
        if account is None:
            return {"success": False, "message": f"策略 {strategy_id} 未注册"}

        if account.status != StrategyStatus.RUNNING:
            return {"success": False, "message": f"策略当前状态为 {account.status.value}，无法暂停"}

        account.status = StrategyStatus.PAUSED
        account.last_update_time = datetime.now()
        logger.info(f"[策略管理器] 策略已暂停: {strategy_id}")
        return {"success": True, "message": "策略已暂停（持仓保留，停止新交易）"}

    def stop_strategy(self, strategy_id: str, force_liquidate: bool = False) -> dict:
        """
        停止策略

        force_liquidate: 是否强制平仓（目前仅标记，实际平仓需调用交易接口）
        """
        account = self.virtual_account_mgr.get_account(strategy_id)
        if account is None:
            return {"success": False, "message": f"策略 {strategy_id} 未注册"}

        account.status = StrategyStatus.STOPPED
        account.last_update_time = datetime.now()

        config = self._strategies.get(strategy_id)

        if force_liquidate and account.positions:
            logger.warning(
                f"[策略管理器] 策略 {strategy_id} 请求强制平仓，"
                f"持仓: {list(account.positions.keys())}，需手动执行卖出操作"
            )
            return {
                "success": True,
                "message": f"策略已停止，需手动平仓 {len(account.positions)} 只股票",
                "positions_to_liquidate": list(account.positions.keys()),
            }

        # 移除虚拟账户
        self.virtual_account_mgr.remove_account(strategy_id)
        if config:
            self._strategy_names.pop(config.strategy_name, None)
        self._strategies.pop(strategy_id, None)

        logger.info(f"[策略管理器] 策略已停止并注销: {strategy_id}")
        return {"success": True, "message": "策略已停止并注销"}

    def get_strategy_info(self, strategy_id: str) -> Optional[StrategyInfo]:
        """获取策略详情"""
        config = self._strategies.get(strategy_id)
        if config is None:
            return None
        return self._build_strategy_info(strategy_id, config)

    def list_strategies(self) -> List[StrategyInfo]:
        """列出所有策略"""
        return [
            self._build_strategy_info(sid, cfg)
            for sid, cfg in self._strategies.items()
        ]

    def get_pnl_report(self, strategy_id: str) -> Optional[StrategyPnLReport]:
        """获取策略盈亏报告"""
        account = self.virtual_account_mgr.get_account(strategy_id)
        config = self._strategies.get(strategy_id)
        if account is None or config is None:
            return None

        balance = account.get_balance()
        total_pnl = account.realized_pnl + account.unrealized_pnl
        total_pnl_pct = (
            total_pnl / account.allocated_capital * 100
            if account.allocated_capital > 0 else 0.0
        )
        win_rate = (
            account.win_trades / account.total_trades * 100
            if account.total_trades > 0 else 0.0
        )

        return StrategyPnLReport(
            strategy_id=strategy_id,
            strategy_name=config.strategy_name,
            realized_pnl=account.realized_pnl,
            unrealized_pnl=account.unrealized_pnl,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            win_count=account.win_trades,
            loss_count=account.loss_trades,
            win_rate=win_rate,
            total_trades=account.total_trades,
            positions=list(account.positions.values()),
            balance=balance,
        )

    def _build_strategy_info(self, strategy_id: str, config: StrategyConfig) -> StrategyInfo:
        """构建策略信息"""
        account = self.virtual_account_mgr.get_account(strategy_id)
        return StrategyInfo(
            strategy_id=strategy_id,
            strategy_name=config.strategy_name,
            strategy_type=config.strategy_type,
            status=account.status if account else StrategyStatus.STOPPED,
            allocated_capital=config.allocated_capital,
            max_positions=config.max_positions,
            max_single_position_ratio=config.max_single_position_ratio,
            description=config.description,
            risk_params=config.risk_params,
            created_time=account.created_time if account else datetime.now(),
            last_update_time=account.last_update_time if account else datetime.now(),
            virtual_balance=account.get_balance() if account else None,
            position_count=len(account.positions) if account else 0,
        )
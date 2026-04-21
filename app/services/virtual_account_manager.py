# -*- coding: utf-8 -*-
"""
虚拟账户管理器 — 策略间的资金和持仓隔离

核心规则:
- 同一只股票可被多个策略同时持有 (A)
- 固定金额分配 (B)
- 超限直接拒绝 (A)
"""

import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.utils.logger import logger

from app.models.strategy_models import (
    StrategyConfig,
    StrategyStatus,
    VirtualBalance,
    VirtualPosition,
)


class VirtualAccount:
    """单个策略的虚拟账户"""

    def __init__(self, strategy_id: str, config: StrategyConfig):
        self.strategy_id = strategy_id
        self.config = config
        self.status = StrategyStatus.REGISTERED

        # 资金
        self.allocated_capital = config.allocated_capital
        self.available_capital = config.allocated_capital
        self.frozen_capital = 0.0
        self.realized_pnl = 0.0

        # 持仓: stock_code -> VirtualPosition
        self.positions: Dict[str, VirtualPosition] = {}

        # 交易统计
        self.total_trades = 0
        self.win_trades = 0
        self.loss_trades = 0

        # 时间戳
        self.created_time = datetime.now()
        self.last_update_time = datetime.now()

    @property
    def market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def total_asset(self) -> float:
        return self.available_capital + self.frozen_capital + self.market_value

    def get_balance(self) -> VirtualBalance:
        return VirtualBalance(
            allocated_capital=self.allocated_capital,
            available_capital=self.available_capital,
            frozen_capital=self.frozen_capital,
            market_value=self.market_value,
            total_asset=self.total_asset,
            realized_pnl=self.realized_pnl,
            unrealized_pnl=self.unrealized_pnl,
        )

    def check_buy_permission(self, stock_code: str, volume: int, price: float) -> Tuple[bool, str]:
        if self.status != StrategyStatus.RUNNING:
            return False, f"策略状态为 {self.status.value}，不允许交易"

        if stock_code not in self.positions and len(self.positions) >= self.config.max_positions:
            return False, f"已达最大持仓数 {self.config.max_positions}，拒绝买入"

        order_value = volume * price
        max_single_value = self.allocated_capital * self.config.max_single_position_ratio
        current_holding_value = 0.0
        if stock_code in self.positions:
            current_holding_value = self.positions[stock_code].market_value

        if current_holding_value + order_value > max_single_value:
            return False, (
                f"单股仓位超限: 当前 {current_holding_value:.2f} + "
                f"本次 {order_value:.2f} > 上限 {max_single_value:.2f}"
            )

        if order_value > self.available_capital:
            return False, f"资金不足: 需要 {order_value:.2f}，可用 {self.available_capital:.2f}"

        return True, "允许买入"

    def record_buy(self, stock_code: str, stock_name: str, volume: int, price: float):
        order_value = volume * price

        if stock_code in self.positions:
            pos = self.positions[stock_code]
            total_cost = pos.avg_cost * pos.quantity + price * volume
            pos.quantity += volume
            pos.available_quantity += volume
            pos.avg_cost = total_cost / pos.quantity
            pos.update_price(price)
        else:
            self.positions[stock_code] = VirtualPosition(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=volume,
                available_quantity=volume,
                avg_cost=price,
                current_price=price,
                market_value=volume * price,
                entry_time=datetime.now(),
            )

        self.available_capital -= order_value
        self.total_trades += 1
        self.last_update_time = datetime.now()
        logger.info(
            f"[虚拟账户] {self.strategy_id} 买入 {stock_code} "
            f"{volume}股@{price:.2f} = {order_value:.2f}元"
        )

    def record_sell(self, stock_code: str, volume: int, price: float) -> bool:
        if stock_code not in self.positions:
            return False

        pos = self.positions[stock_code]
        if volume > pos.available_quantity:
            logger.warning(
                f"[虚拟账户] {self.strategy_id} 卖出 {stock_code} {volume}股 "
                f"超过可卖数量 {pos.available_quantity}"
            )
            return False

        sell_value = volume * price
        cost_value = pos.avg_cost * volume
        trade_pnl = sell_value - cost_value

        self.realized_pnl += trade_pnl
        if trade_pnl > 0:
            self.win_trades += 1
        else:
            self.loss_trades += 1

        pos.quantity -= volume
        pos.available_quantity -= volume
        pos.update_price(price)

        if pos.quantity <= 0:
            del self.positions[stock_code]

        self.available_capital += sell_value
        self.total_trades += 1
        self.last_update_time = datetime.now()
        logger.info(
            f"[虚拟账户] {self.strategy_id} 卖出 {stock_code} "
            f"{volume}股@{price:.2f} 盈亏: {trade_pnl:+.2f}元"
        )
        return True


class VirtualAccountManager:
    """虚拟账户管理器 — 管理所有策略的虚拟账户"""

    def __init__(self, total_capital: float = 0.0):
        self.total_capital = total_capital
        self._accounts: Dict[str, VirtualAccount] = {}
        self._lock = threading.Lock()

    def set_total_capital(self, total_capital: float):
        self.total_capital = total_capital

    @property
    def total_allocated(self) -> float:
        return sum(acc.allocated_capital for acc in self._accounts.values())

    @property
    def remaining_capital(self) -> float:
        return self.total_capital - self.total_allocated

    def create_account(self, strategy_id: str, config: StrategyConfig) -> VirtualAccount:
        with self._lock:
            if self.total_capital > 0:
                if config.allocated_capital > self.remaining_capital:
                    raise ValueError(
                        f"分配资金 {config.allocated_capital:.2f} 超过可用资金 "
                        f"{self.remaining_capital:.2f} "
                        f"(总: {self.total_capital:.2f}, 已分配: {self.total_allocated:.2f})"
                    )

            account = VirtualAccount(strategy_id, config)
            self._accounts[strategy_id] = account
            logger.info(
                f"[VAM] 创建虚拟账户: {strategy_id}, "
                f"分配资金: {config.allocated_capital:.2f}"
            )
            return account

    def remove_account(self, strategy_id: str):
        with self._lock:
            if strategy_id in self._accounts:
                del self._accounts[strategy_id]

    def get_account(self, strategy_id: str) -> Optional[VirtualAccount]:
        return self._accounts.get(strategy_id)

    def check_buy_permission(
        self, strategy_id: str, stock_code: str, volume: int, price: float
    ) -> Tuple[bool, str]:
        account = self._accounts.get(strategy_id)
        if account is None:
            return False, f"策略 {strategy_id} 未注册"
        return account.check_buy_permission(stock_code, volume, price)

    def record_buy(
        self, strategy_id: str, stock_code: str,
        stock_name: str, volume: int, price: float
    ) -> Tuple[bool, str]:
        with self._lock:
            account = self._accounts.get(strategy_id)
            if account is None:
                return False, f"策略 {strategy_id} 未注册"

            allowed, reason = account.check_buy_permission(stock_code, volume, price)
            if not allowed:
                return False, reason

            account.record_buy(stock_code, stock_name, volume, price)
            return True, "买入成功"

    def record_sell(
        self, strategy_id: str, stock_code: str, volume: int, price: float
    ) -> Tuple[bool, str]:
        with self._lock:
            account = self._accounts.get(strategy_id)
            if account is None:
                return False, f"策略 {strategy_id} 未注册"

            success = account.record_sell(stock_code, volume, price)
            if not success:
                return False, "卖出失败：持仓不足或不存在"
            return True, "卖出成功"

    def get_virtual_positions(self, strategy_id: str) -> List[VirtualPosition]:
        account = self._accounts.get(strategy_id)
        if account is None:
            return []
        return list(account.positions.values())

    def get_virtual_balance(self, strategy_id: str) -> Optional[VirtualBalance]:
        account = self._accounts.get(strategy_id)
        if account is None:
            return None
        return account.get_balance()

    def list_accounts(self) -> Dict[str, VirtualAccount]:
        return dict(self._accounts)
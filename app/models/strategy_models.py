# -*- coding: utf-8 -*-
"""
策略管理相关数据模型

设计决策:
- 同一只股票可被多个策略同时持有 (A)
- 固定金额分配资金 (B)
- 超限直接拒绝下单 (A)
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== 枚举类型 ====================

class StrategyStatus(str, Enum):
    """策略状态"""
    REGISTERED = "REGISTERED"      # 已注册，未启动
    RUNNING = "RUNNING"            # 运行中
    PAUSED = "PAUSED"              # 已暂停（不平仓，停止新交易）
    STOPPED = "STOPPED"            # 已停止


# ==================== 虚拟账户模型 ====================

class VirtualPosition(BaseModel):
    """虚拟持仓"""
    stock_code: str
    stock_name: str = ""
    quantity: int
    available_quantity: int
    avg_cost: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    entry_time: Optional[datetime] = None

    def update_price(self, current_price: float):
        """更新当前价格和盈亏"""
        self.current_price = current_price
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = (current_price - self.avg_cost) * self.quantity
        self.unrealized_pnl_pct = (
            (current_price - self.avg_cost) / self.avg_cost * 100
            if self.avg_cost > 0 else 0.0
        )


class VirtualBalance(BaseModel):
    """虚拟账户资金"""
    allocated_capital: float = 0.0       # 分配的总资金
    available_capital: float = 0.0       # 可用资金
    frozen_capital: float = 0.0          # 冻结资金
    market_value: float = 0.0            # 持仓市值
    total_asset: float = 0.0             # 总资产
    realized_pnl: float = 0.0            # 已实现盈亏
    unrealized_pnl: float = 0.0          # 未实现盈亏


# ==================== 策略配置 ====================

class StrategyConfig(BaseModel):
    """策略注册配置"""
    strategy_name: str = Field(..., description="策略名称", min_length=1, max_length=50)
    strategy_type: str = Field("CUSTOM", description="策略类型")
    allocated_capital: float = Field(..., description="分配资金（固定金额）", gt=0)
    max_positions: int = Field(5, description="最大持仓数", ge=1, le=50)
    max_single_position_ratio: float = Field(
        0.3, description="单只股票最大仓位比例（占分配资金）", gt=0, le=1.0
    )
    description: str = Field("", description="策略描述")
    risk_params: Dict[str, Any] = Field(default_factory=dict, description="风控参数")

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("策略名称不能为空")
        return v


class StrategyInfo(BaseModel):
    """策略详情"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    status: StrategyStatus
    allocated_capital: float
    max_positions: int
    max_single_position_ratio: float
    description: str = ""
    risk_params: Dict[str, Any] = {}
    created_time: datetime
    last_update_time: datetime
    virtual_balance: Optional[VirtualBalance] = None
    position_count: int = 0


# ==================== 请求/响应模型 ====================

class StrategyRegisterRequest(BaseModel):
    """策略注册请求"""
    strategy_name: str = Field(..., description="策略名称")
    strategy_type: str = Field("CUSTOM", description="策略类型")
    allocated_capital: float = Field(..., description="分配资金（固定金额）", gt=0)
    max_positions: int = Field(5, description="最大持仓数", ge=1, le=50)
    max_single_position_ratio: float = Field(0.3, description="单股最大仓位比例", gt=0, le=1.0)
    description: str = Field("", description="策略描述")
    risk_params: Dict[str, Any] = Field(default_factory=dict, description="风控参数")


class StrategyRegisterResponse(BaseModel):
    """策略注册响应"""
    success: bool
    message: str
    strategy_id: Optional[str] = None
    strategy_info: Optional[StrategyInfo] = None


class StrategyActionRequest(BaseModel):
    """策略操作请求（启动/暂停/停止）"""
    force_liquidate: bool = Field(False, description="停止时是否强制平仓")


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StrategyInfo]
    total_count: int
    total_allocated_capital: float


class StrategyPnLReport(BaseModel):
    """策略盈亏报告"""
    strategy_id: str
    strategy_name: str
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    total_trades: int = 0
    positions: List[VirtualPosition] = []
    balance: Optional[VirtualBalance] = None
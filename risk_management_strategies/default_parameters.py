from dataclasses import dataclass
from typing import Optional


@dataclass
class DefaultRiskParameters:
    """Base class containing default parameters for risk management strategies"""
    max_leverage: float = 1
    min_order_value_usd: float = 10.0
    aggressivity: float = 0.33
    emergency_exit_leverage: float = 2
    early_stopping_margin: float = 0.1
    cancel_orders_every_timestamp: bool = True
    max_order_age: Optional[int] = None
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from logger import MarketMakingLogger

@dataclass
class StrategyParameters:
    """Base class for strategy parameters"""
    pass

@dataclass
class OrderLevel:
    """Represents a single order level with price and size"""
    price: float
    size: float

@dataclass
class StrategyInput:
    """Input for any strategy """
    timestamp: int # is it required ; well maybe if we want to play specific timestamps
    current_price: float
    current_inventory: float
    current_upnl: float #in percent point of balance per symbol = upnl(usd)/(total_balance_usd/n_symbols)
    max_inventory: float
    agressivity : float
    minimal_spread : float
    indicators: Dict[str, float]
    ohlc_history: Optional[Dict[str, List[float]]] = None
    volume_history: Optional[List[float]] = None

    def repr(self) -> str:
        return f"StrategyInput(timestamp={self.timestamp}, current_price={self.current_price}, current_inventory={self.current_inventory}, current_upnl={self.current_upnl}, max_inventory={self.max_inventory}, indicators={self.indicators}, ohlc_history={self.ohlc_history}, volume_history={self.volume_history})"

@dataclass
class StrategyOutput:
    """Output from strategy containing reservation price, order levels and spread information"""
    reservation_price: float #not used in trading, but for visualization)
    buy_levels: List[OrderLevel]  # Sorted by price descending (the first closest to current price): todo
    sell_levels: List[OrderLevel]  # Sorted by price ascending : (same) todo
    spread: float = 0.0  # Current spread value computed by the strategy
    # buys levels guaranteed to be below current_price - minimal_spread
    # sell levels guaranteed to be above current_price + minimal_spread
    def repr(self) -> str:
        return f"StrategyOutput(reservation_price={self.reservation_price}, spread={self.spread}, buy_levels={self.buy_levels}, sell_levels={self.sell_levels})"
        
class BaseStrategy(ABC):
    """Abstract base class for market making strategies"""
    
    def __init__(self, parameters: StrategyParameters):
        self.parameters = parameters
        self.logger = MarketMakingLogger()
        
    def log_strategy_info(self, message: str):
        """Log strategy information message"""
        self.logger.log_strategy_info(self.__class__.__name__, message)
        
    def log_strategy_debug(self, strategy_name: str, message: str):
        """Log strategy debug message"""
        self.logger.log_strategy_debug(strategy_name, message)
    
    @abstractmethod
    def calculate_order_levels(self, ticksize:float, StrategyInput:StrategyInput) -> StrategyOutput:
        """Calculate reservation price and order levels
        Args:
            StrategyInput containing relevant data to compute a prediction
        Returns:
            StrategyOutput containing reservation price and order levels
        """
        pass
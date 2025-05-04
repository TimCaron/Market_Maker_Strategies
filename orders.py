from dataclasses import dataclass
from typing import Optional
from enum import Enum
from abc import ABC, abstractmethod

class OrderSide(Enum):
    BUY = 'BUY'
    SELL = 'SELL'

class OrderStatus(Enum):
    PENDING = 'PENDING'
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'

class OrderType(Enum):
    LIMIT = 'LIMIT'
    MARKET = 'MARKET'

class BaseOrder(ABC):
    symbol: str
    timestamp: int
    side: OrderSide
    quantity: float
    status: OrderStatus
    filled_price: Optional[float]
    filled_timestamp: Optional[int]
    reason: str
    order_type: OrderType

    @abstractmethod
    def check_fill(self, high: float, low: float, current_timestamp: int, ticksize: float) -> bool:
        pass

    def cancel(self):
        """Cancel the pending order"""
        if self.status == OrderStatus.PENDING:
            self.status = OrderStatus.CANCELLED

@dataclass
class LimitOrder(BaseOrder):
    symbol: str
    timestamp: int
    side: OrderSide
    price: float
    quantity: float
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_timestamp: Optional[int] = None
    reason: str = ''
    order_type: OrderType = OrderType.LIMIT
    
    def check_fill(self, high: float, low: float, current_timestamp: int, ticksize: float) -> bool:
        """Check if order should be filled based on price movement
        
        Args:
            high: High price during the period
            low: Low price during the period
            current_timestamp: Current timestamp
            ticksize: Minimum price movement
            
        Returns:
            bool: True if order should be filled
        """
        if self.status != OrderStatus.PENDING:
            return False
            
        if self.side == OrderSide.BUY and low <= self.price - ticksize:
            self.status = OrderStatus.FILLED
            self.filled_price = self.price
            self.filled_timestamp = current_timestamp
            return True
            
        elif self.side == OrderSide.SELL and high >= self.price + ticksize:
            self.status = OrderStatus.FILLED 
            self.filled_price = self.price
            self.filled_timestamp = current_timestamp
            return True
            
        return False

@dataclass
class MarketOrder(BaseOrder):
    symbol: str
    timestamp: int
    side: OrderSide
    quantity: float
    price: float = 0.0  # Will be set to execution price when filled
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_timestamp: Optional[int] = None
    reason: str = ''
    order_type: OrderType = OrderType.MARKET
    
    def check_fill(self, high: float, low: float, current_timestamp: int, ticksize: float) -> bool:
        """Market orders are filled immediately at current price
        
        Args:
            high: High price during the period
            low: Low price during the period
            current_timestamp: Current timestamp
            ticksize: Minimum price movement
            
        Returns:
            bool: True as market orders are always filled
        """
        if self.status != OrderStatus.PENDING:
            return False
            
        # Market orders are filled at the current price
        self.status = OrderStatus.FILLED
        # For market orders, we use the worst case fill price
        self.filled_price = high if self.side == OrderSide.BUY else low
        self.price = self.filled_price  # Set the price to the fill price
        self.filled_timestamp = current_timestamp
        return True
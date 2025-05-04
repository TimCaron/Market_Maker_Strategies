from typing import Dict, List, Optional
from dataclasses import dataclass
from .base_strategy import BaseStrategy, StrategyParameters, StrategyOutput, OrderLevel
import numpy as np

@dataclass
class StoikovParameters(StrategyParameters):
    """Parameters for Stoikov market making strategy"""
    a: float  # Spread factor
    k: float  # Mean reversion factor
    max_orders: int  # Maximum number of orders per side

class StoikovStrategy(BaseStrategy):
    """Implementation of Stoikov market making strategy"""
    ### Not correct, well i dont think it is ; todo
    
    def __init__(self, parameters: StoikovParameters):
        super().__init__(parameters)
        self.params = parameters  # Type hint for IDE support
    
    def calculate_order_levels(
        self,
        timestamp: int,
        current_price: float,
        position_size: float,
        indicators: Dict[str, float],
        ohlc_history: Optional[Dict[str, List[float]]] = None
    ) -> StrategyOutput:
        """Calculate reservation price and order levels using Stoikov model
        
        The strategy places orders symmetrically around a reservation price,
        adjusting spreads based on volatility and inventory.
        """
        # Extract parameters
        a = self.params.a
        k = self.params.k
        ticksize = self.params.ticksize
        max_orders = self.params.max_orders
        max_position = self.params.max_position
        
        # Use volatility from indicators if available
        volatility = indicators.get('volatility', 0.01)
        
        # Calculate reservation price with inventory adjustment
        inventory_impact = k * position_size
        reservation_price = current_price - inventory_impact
        
        # Calculate base spread using volatility
        base_spread = 2 * a * volatility
        
        # Generate order levels
        buy_levels = []
        sell_levels = []
        
        for i in range(max_orders):
            # Increase spread for each level away from reservation price
            level_spread = base_spread * (1 + i * 0.5)
            
            # Calculate prices and round to ticksize
            buy_price = round((reservation_price - level_spread) / ticksize) * ticksize
            sell_price = round((reservation_price + level_spread) / ticksize) * ticksize
            
            # Calculate sizes (decrease as we move away from reservation price)
            size_factor = np.exp(-i * 0.5)  # Exponential decay
            max_trade_size = max_position - abs(position_size)
            
            buy_size = round(max_trade_size * size_factor * 0.2, 8)
            sell_size = round(max_trade_size * size_factor * 0.2, 8)
            
            # Add levels if size is meaningful
            if buy_size >= 0.0001:
                buy_levels.append(OrderLevel(price=buy_price, size=buy_size))
            if sell_size >= 0.0001:
                sell_levels.append(OrderLevel(price=sell_price, size=sell_size))
        
        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels
        )
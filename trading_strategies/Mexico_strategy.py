from typing import Dict, List, Optional
from dataclasses import dataclass
from .base_strategy import BaseStrategy, StrategyParameters, StrategyOutput, OrderLevel, StrategyInput
import numpy as np
from constants import DEFAULT_PARAMS

@dataclass
class MexicoParameters(StrategyParameters):

    # dimensionless parameters for reservation price computation
    q_factor: float  # current inventory size may impact reservation price
    upnl_factor : float# current upnl may impact reservation price
    mean_revert_factor: float  # deviation of current price from a moving average may impact reservation price
    momentum_factor : float # recent momentum  may impact reservation price 
    
    #spread parameters
    constant_spread: float # just have constant spacing as a basis
    vol_factor: float # volatility may impact the the spread
    spread_mom_factor: float # large recent momentum may impact spread
    
    #other parameters
    max_orders: int
    use_adaptive_sizes: bool  # Whether to use adaptive order sizes based on remaining inventory

    # window parameters for indicators
    window_vol : int
    window_sma : int
    window_mom : int
    window_high_low : int

class MexicoStrategy(BaseStrategy):
    """Implementation of very general multi-parameter market making strategy"""
    
    def __init__(self, parameters: MexicoParameters):
        super().__init__(parameters)
        self.params = parameters  # Type hint for IDE support
    
    def calculate_order_levels(
        self,
        ticksize, 
        strategy_input: StrategyInput
    ) -> StrategyOutput:
        """Calculate reservation price and order levels using 'Mexico' model
            1. computes a reservation price
            2. computes a traget inventory
            3. computes a spread
            4. returns buy and sell levels

        Mexico doesn't use volume
        """
        current_price = strategy_input.current_price
        current_upnl = strategy_input.current_upnl

        # in asset unit:
        current_inventory = strategy_input.current_inventory #not necessarily positive
        max_inventory = strategy_input.max_inventory #positive value
        remaining_inventory_buy = max_inventory - current_inventory
        remaining_inventory_sell = max_inventory + current_inventory
        aggressivity = strategy_input.agressivity
        remaining_inventory_buy *= aggressivity
        remaining_inventory_sell *= aggressivity

        # Get indicators for the current timestamp
        indicators = strategy_input.indicators
        q_factor = self.params.q_factor
        upnl_factor = self.params.upnl_factor
        mean_revert_factor = self.params.mean_revert_factor
        momentum_factor = self.params.momentum_factor
        
        # Access indicators directly from the dictionary
        # Format: indicators[indicator_name]
        sma_deviation = indicators.get('sma_deviation', 0.0)
        momentum = indicators.get('momentum', 0.0)
        volatility = indicators.get('volatility', 0.0)

        # compute reservation price
        delta = q_factor*current_inventory + upnl_factor*current_upnl + mean_revert_factor*sma_deviation + momentum_factor*momentum
        reservation_price = current_price*(1 + delta)

        # compute spread 
        max_orders = self.params.max_orders
        minimal_spread = strategy_input.minimal_spread

        constant_spread = self.params.constant_spread
        vol_factor = self.params.vol_factor
        spread_mom_factor = self.params.spread_mom_factor
        # spacing between levels is impacted by current volatility and abs value of recent momemtum
        spacing = constant_spread + vol_factor*volatility + spread_mom_factor*abs(momentum)
        if spacing < minimal_spread:
            spacing = minimal_spread
        # Generate order levels
        buy_levels = []
        sell_levels = []
        self.log_strategy_debug(f"Computed reservation: {reservation_price:.2f} | spacing: {spacing*current_price:.8f} | Volatility: {volatility:.8f} | Momentum: {momentum:.8f}")
        count_buy, count_sell = 0, 0

        #first check valid order numbers
        for i in range(1, max_orders+1):
            level_spread = i*spacing*current_price
            buy_price = round((reservation_price - level_spread) / ticksize) * ticksize
            sell_price = round((reservation_price + level_spread) / ticksize) * ticksize
            if buy_price < current_price - minimal_spread:
                count_buy+=1
            if sell_price > current_price + minimal_spread:
                count_sell+=1

        # Calculate order sizes based on strategy parameter
        if self.params.use_adaptive_sizes:
            # Adaptive sizes based on remaining inventory
            buy_size = remaining_inventory_buy/count_buy if count_buy > 0 else 0
            sell_size = remaining_inventory_sell/count_sell if count_sell > 0 else 0
        else:
            # Fixed sizes based on max inventory
            buy_size = max_inventory/max_orders
            sell_size = max_inventory/max_orders

        # Generate orders
        for i in range(1, max_orders+1):
            level_spread = i*spacing*current_price
            buy_price = round((reservation_price - level_spread) / ticksize) * ticksize
            sell_price = round((reservation_price + level_spread) / ticksize) * ticksize
            if buy_price < current_price - minimal_spread:
                buy_levels.append(OrderLevel(price=buy_price, size=buy_size))
            if sell_price > current_price + minimal_spread:
                sell_levels.append(OrderLevel(price=sell_price, size=sell_size))

        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels
        )
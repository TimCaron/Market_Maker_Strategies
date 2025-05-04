from typing import Dict, List, Optional
from dataclasses import dataclass
from .base_strategy import BaseStrategy, StrategyParameters, StrategyOutput, OrderLevel, StrategyInput
import numpy as np

@dataclass
class StoikovParameters(StrategyParameters):
    risk_aversion: float  # gamma
    market_depth: float   # k
    window_vol: int

    
class StoikovStrategy(BaseStrategy):
    # My understanding of the no time limit Stoikov strategy
    def __init__(self, parameters: StoikovParameters):
        super().__init__(parameters)
        self.params = parameters  # critical to compute indicators

    def calculate_order_levels(self, 
        ticksize, 
        strategy_input: StrategyInput) -> StrategyOutput:
        
        S = strategy_input.current_price #in USD per unit asset, eg. 80000 for 1 BTC -> ok
        q = strategy_input.current_inventory # in asset units, eg. 0.001 BTC
        min_spread = strategy_input.minimal_spread
        indicators = strategy_input.indicators
        sigma = indicators.get('volatility', 0.0) #volatility
        # now i'm not sure this is the right sigma but this will be taken care of by the right gamma
        # in order to make it more realistic
        p = self.parameters
        gamma = p.risk_aversion
        k = p.market_depth

        # My understanding is that Stoikov has no limit on the cumulative inventory
        # which is weird, but leave it for now ; to cope with this i'll keep the aggressivity factor
        # from risk management policy
        aggressivity = strategy_input.agressivity # say 0.1
        buy_size = strategy_input.max_inventory*aggressivity
        sell_size = strategy_input.max_inventory*aggressivity
        # Reservation price shifts against inventory
        reservation_price = S - gamma * sigma**2 * q

        # Optimal spread from Stoikov closed-form
        optimal_spread = (2 / k) + gamma * sigma**2

        # Adjust to enforce minimal spread
        spread = max(optimal_spread, min_spread) #in percentage, so:
        spread = S*spread
        # Determine quote prices
        half_spread = spread / 2
        ask_price = reservation_price + half_spread
        ask_price = round((ask_price) / ticksize) * ticksize

        bid_price = reservation_price - half_spread
        bid_price = round((bid_price) / ticksize) * ticksize

        # quote only one order at a time
        if bid_price < S - min_spread:
            buy_levels = [OrderLevel(price=bid_price, size=buy_size)]
        else:
            buy_levels = []

        if ask_price > S + min_spread:
            sell_levels = [OrderLevel(price=ask_price, size=sell_size)]
        else:
            sell_levels = []

        self.log_strategy_debug(f"reservation_price={reservation_price:.2f}, bid={bid_price:.2f}, ask={ask_price:.2f}, spread={spread:.4f}")

        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels
        )

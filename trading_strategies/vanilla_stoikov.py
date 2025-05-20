from .base_strategy import BaseStrategy, StrategyOutput, OrderLevel, StrategyInput
from .default_parameters import StoikovParameters


class VanillaStoikovStrategy(BaseStrategy):
    """Vanilla implementation of the Stoikov market making strategy with fixed sigma and time dependence"""
    
    def __init__(self, parameters: StoikovParameters):
        super().__init__(parameters)
        self.params = parameters
        self.sigma = 2.0  # Fixed sigma value as requested
        self.T = 10.0  # Total time horizon
        self.dt = 0.001  # Time step size
        # we will check how it relates to the actual volatility of the brownian motion
        # recall parm list is :
        # max_orders, minimal_spread, use_adaptive_sizes, window_vol, window_sma, window_mom, window_high_low, risk_aversion, gamma_spread
    
    def calculate_order_levels(self,
                             ticksize: float,
                             strategy_input: StrategyInput) -> StrategyOutput:
        
        S = strategy_input.current_price  # Current price
        q = strategy_input.current_inventory  # Current inventory
        min_spread = strategy_input.minimal_spread
        aggressivity = strategy_input.agressivity
        buy_size = strategy_input.max_inventory * aggressivity
        sell_size = strategy_input.max_inventory * aggressivity

        # Calculate remaining time
        t = strategy_input.timestamp * self.dt  # Current time
        remaining_time = self.T - t  # Time remaining until horizon

        # Reservation price calculation with fixed sigma and time dependence
        gamma = self.params.risk_aversion
        reservation_price = S - gamma * self.sigma**2 * q * S * remaining_time

        # Optimal spread calculation with fixed sigma and time dependence
        gamma_spread = self.params.gamma_spread
        optimal_spread = min_spread + gamma_spread * self.sigma**2 * remaining_time
        spread = S * optimal_spread

        # Determine quote prices
        half_spread = spread / 2
        ask_price = reservation_price + half_spread
        ask_price = round(ask_price / ticksize) * ticksize

        bid_price = reservation_price - half_spread
        bid_price = round(bid_price / ticksize) * ticksize

        # Create order levels
        if bid_price < S - S * min_spread:
            buy_levels = [OrderLevel(price=bid_price, size=buy_size)]
        else:
            buy_levels = [OrderLevel(price=S - S * min_spread, size=buy_size)]

        if ask_price > S + S * min_spread:
            sell_levels = [OrderLevel(price=ask_price, size=sell_size)]
        else:
            sell_levels = [OrderLevel(price=S + S * min_spread, size=sell_size)]

        # Log strategy details
        message = (
            f"Components| \n"
            f"q: {q:.2f},  sigma: {self.sigma:.4f}\n"
            f"t: {t:.4f}, T: {self.T:.4f}, remaining_time: {remaining_time:.4f}\n"
            f"gamma (res price): {gamma:.4f}, gamma*vol {gamma*self.sigma**2}\n"
            f"S: {S:.2f}, reservation_price: {reservation_price:.2f},\n"
            f"gamma_spread: {gamma_spread:.4f}, gamma*vol {gamma_spread*self.sigma**2}\n"
            f"optimal_spread: {optimal_spread:.8f}, min_spread: {min_spread:.8f}\n"
            f"final spread: {spread:.8f}, buy: {buy_levels[0].price:.8f}, sell: {sell_levels[0].price:.8f}\n"
        )
        self.log_strategy_debug("VanillaStoikov", message)

        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            spread=spread
        ) 
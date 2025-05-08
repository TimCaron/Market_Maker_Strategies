from .base_strategy import BaseStrategy, StrategyOutput, OrderLevel, StrategyInput
from .default_parameters import StoikovParameters


class StoikovStrategy(BaseStrategy):
    """My understanding of the no time limit Stoikov strategy"""
    
    def __init__(self, parameters: StoikovParameters):
        super().__init__(parameters)
        self.params = parameters  # critical to compute indicators

    def calculate_order_levels(self,
                               ticksize: float,
                               strategy_input: StrategyInput) -> StrategyOutput:
        
        S = strategy_input.current_price #in USD per unit asset, eg. 80000 for 1 BTC -> ok
        q = strategy_input.current_inventory # in asset units, eg. 0.001 BTC
        min_spread = strategy_input.minimal_spread
        indicators = strategy_input.indicators
        sigma = indicators.get('volatility', 0.0) #volatility
        # This sigma is the np.std of the log returns
        p = self.parameters
        gamma = p.risk_aversion
        gamma_spread = p.gamma_spread

        # My understanding is that Stoikov has no limit on the cumulative inventory
        # which is weird, but leave it for now ; to cope with this I'll keep the aggressivity factor
        # from risk management policy
        aggressivity = strategy_input.agressivity # say 0.1
        buy_size = strategy_input.max_inventory*aggressivity
        sell_size = strategy_input.max_inventory*aggressivity
        # Reservation price shifts against inventory
        reservation_price = S - gamma * sigma**2 * q * S
        # because q is in asset unit ; and gamma * sigma**2 should be in basis point (my understanding)

        # Optimal spread from Stoikov closed-form
        # optimal_spread = (2 / k) + gamma * sigma**2 # k 'market depth' is the depth of the order book
        # so 2/k is a constant spread in fact
        # 2/k >= my minimal spred means k <= 2/min_spread \approx 2/0.001 = 2000 otherwise doesnt make sense
        # we should probably replace 2/k by minimal spread
        # lets do that,
        # also same gamma is weird and dosent work : lets have two different gamma
        optimal_spread = min_spread + gamma_spread * sigma**2
        # Adjust to enforce minimal spread
        spread = S*optimal_spread
        # Determine quote prices
        half_spread = spread / 2
        ask_price = reservation_price + half_spread
        ask_price = round((ask_price) / ticksize) * ticksize

        bid_price = reservation_price - half_spread
        bid_price = round((bid_price) / ticksize) * ticksize

        # quote only one order at a time
        # now we have a tension between theory and pratcice. q > 0 means we are long, so we should sell
        # but what happens if reservation price is so low that we cant place the sell order ?
        # same for q<0.
        if bid_price < S - S*min_spread:
            buy_levels = [OrderLevel(price=bid_price, size=buy_size)]
        else: #lets enforce the order anyway at minimal spread
            buy_levels = [OrderLevel(price=S - S*min_spread, size=buy_size)]
        buy = buy_levels[0].price
        if ask_price > S + S*min_spread:
            sell_levels = [OrderLevel(price=ask_price, size=sell_size)]
        else:
            sell_levels = [OrderLevel(price= S + S*min_spread, size=sell_size)]
        sell = sell_levels[0].price
        # Log detailed Stoikov formula components
        message = (
            f"Components| \n"
            f"q: {q:.2f},  sigma: {sigma:.4f}\n"
            f"gamma (res price): {gamma:.4f}, gamma*vol {gamma*sigma**2}\n"
            f"S: {S:.2f}, reservation_price: {reservation_price:.2f},\n"
            f"gamma_spread: {gamma_spread:.4f}, gamma*vol {gamma_spread*sigma**2}\n"
            f"optimal_spread: {optimal_spread:.8f}, min_spread: {min_spread:.8f}\n"
            f"final spread: {spread:.8f}, buy: {buy:.8f}, sell: {sell:.8f}\n"
        )
        self.log_strategy_debug("Stoikov", message)
        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            spread=spread  # Store the computed spread
        )

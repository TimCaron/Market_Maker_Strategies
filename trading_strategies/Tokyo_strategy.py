from .base_strategy import BaseStrategy, StrategyOutput, OrderLevel, StrategyInput
from .default_parameters import TokyoParameters

class TokyoStrategy(BaseStrategy):
    """One of the most simple possible market making strategy:
    1. Quote both sided with a symmetric constant spread
    2. Unless you reach your max inventory, then you can only quote one side in order to reduce inventory
    3  We still may quote n orders sell n order buy
    4. Always take the same size for each order
    5. Reservation price is the current price
    6. No indicator used
    """

    def __init__(self, parameters: TokyoParameters):
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
        current_inventory = strategy_input.current_inventory  # not necessarily positive
        max_inventory = strategy_input.max_inventory  # positive valu
        aggressivity = strategy_input.agressivity
        buy_size = max_inventory * aggressivity
        if current_inventory >= max_inventory:
            buy_size = 0
        sell_size = max_inventory * aggressivity
        if current_inventory <= -max_inventory: #check is inventory negative??
            sell_size = 0
        max_orders = self.params.max_orders

        # Fixed sizes based on max inventory
        buy_size = buy_size / max_orders
        sell_size = sell_size / max_orders

        # Fixed spread : let's say minimal spread; we will have to override the default value when calling this startegy
        constant_spread = self.params.minimal_spread

        # Generate order levels
        buy_levels = []
        sell_levels = []

        # Generate orders
        level_spread = constant_spread * current_price
        for i in range(0, int(max_orders)):
            buy_price = round((current_price - i*level_spread - level_spread/2) / ticksize) * ticksize
            sell_price = round((current_price + i*level_spread+level_spread/2) / ticksize) * ticksize
            if buy_size != 0:
                buy_levels.append(OrderLevel(price=buy_price, size=buy_size))
            if sell_size != 0:
                sell_levels.append(OrderLevel(price=sell_price, size=sell_size))

        return StrategyOutput(
            reservation_price=current_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            spread=constant_spread * current_price  # Store the computed spread
        )
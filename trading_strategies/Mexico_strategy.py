from .base_strategy import BaseStrategy, StrategyOutput, OrderLevel, StrategyInput
from .default_parameters import MexicoParameters


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
        upnl_factor = self.params.upnl_factor #is already in percent
        mean_revert_factor = self.params.mean_revert_factor
        momentum_factor = self.params.momentum_factor
        
        # Access indicators directly from the dictionary
        # Format: indicators[indicator_name]
        sma_deviation = indicators.get('sma_deviation', 0.0)
        momentum = indicators.get('momentum', 0.0)
        volatility = indicators.get('volatility', 0.0)

        # compute reservation price
        # inventory factor should in proprtion of current balance, so

        delta = q_factor*current_inventory/max_inventory + upnl_factor*current_upnl + mean_revert_factor*sma_deviation + momentum_factor*momentum
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
        #detailed multiline message:
        message = (f"delta components:  q_factor {q_factor}, cur_inventory {current_inventory}, max_inventory {max_inventory}, {q_factor*current_inventory/max_inventory} \n"
            f"upnl_factor {upnl_factor}, cur_upnl {current_upnl}, {upnl_factor*current_upnl} \n"
            f"mean_revert_factor {mean_revert_factor}, sma_deviation {sma_deviation}, {mean_revert_factor*sma_deviation} \n"
            f"momentum_factor {momentum_factor}, momentum {momentum}, {momentum_factor*momentum} \n"
            f"reservation price: delta {delta} \n"
            f"current price: {current_price:.4f} res_price {reservation_price:.4f} \n")
        self.log_strategy_debug("Mexico", message)

        # same for spacing
        message = (f"spacing components 1 : constant_spread {constant_spread:.4f} \n"
            f" 2 : vol_factor {vol_factor:.4f} volatility {volatility:.4f}, gives {vol_factor*volatility} \n"
            f" 3 : spread_mom_factor {spread_mom_factor:.4f} momentum {abs(momentum):.4f}, gives {spread_mom_factor*abs(momentum)} \n"
            f" 4 : min_spread {minimal_spread:.4f} \n"
            f" 5 : spacing {spacing:.4f} , final {spacing*current_price}\n"
            f"current inventory: {current_inventory:.4f} \n"
            f"remaining inventory buy: {remaining_inventory_buy:.4f} \n"
            f"remaining inventory sell: {remaining_inventory_sell:.4f} \n"
            f"max orders: {max_orders} \n")

        self.log_strategy_debug("Mexico", message)


        # Calculate order sizes based on strategy parameter
        if self.params.use_adaptive_sizes:
            # Adaptive sizes based on remaining inventory
            buy_size = remaining_inventory_buy/max_orders
            sell_size = remaining_inventory_sell/max_orders
        else:
            # Fixed sizes based on max inventory
            buy_size = max_inventory*aggressivity/max_orders
            sell_size = max_inventory*aggressivity/max_orders

        # Generate orders
        for i in range(1, max_orders+1):
            level_spread = i*spacing*current_price
            buy_price = round((reservation_price - level_spread) / ticksize) * ticksize
            sell_price = round((reservation_price + level_spread) / ticksize) * ticksize
            if buy_price < current_price - minimal_spread:
                buy_levels.append(OrderLevel(price=buy_price, size=buy_size))
            else:
                buy_levels.append(OrderLevel(price=current_price - minimal_spread, size=buy_size))
            if sell_price > current_price + minimal_spread:
                sell_levels.append(OrderLevel(price=sell_price, size=sell_size))
            else:
                sell_levels.append(OrderLevel(price=current_price + minimal_spread, size=sell_size))

        return StrategyOutput(
            reservation_price=reservation_price,
            buy_levels=buy_levels,
            sell_levels=sell_levels,
            spread=spacing * current_price  # Store the computed spread
        )
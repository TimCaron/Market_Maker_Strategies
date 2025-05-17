from typing import Dict, List, Any
import constants
from orders import LimitOrder
from logger import MarketMakingLogger
from trading_strategies.base_strategy import BaseStrategy, StrategyInput
from risk_management_strategies.base_risk_strategy import BaseRiskStrategy, RiskMetrics
from order_manager import OrderManager

class MarketMakerSimulation:
    def __init__(
        self,
        strategies: Dict[str, BaseStrategy],
        risk_strategy: BaseRiskStrategy,
        initial_cash: float = 100000.0,
        maker_fee: float = 0.0002,
        taker_fee: float = 0.0005,
        min_start: int = 0,  
        verbosity: int = 2
    ):
        """Initialize market maker simulation
        Note the encoding choice: order.size will always be positive, in asset unit, and has a side BUY or SELL
        But position quantity will be positive for BUY and negative for SELL, or zero for None

        Args:
            strategies: Dictionary mapping symbols to their trading strategies
            risk_strategy: Risk management strategy instance
            initial_cash: Initial cash balance
            maker_fee: Maker fee rate
            taker_fee: Taker fee rate
            min_start: Minimum starting timestamp
            verbosity: Logging level (0=ERROR, 1=INFO, 2=DEBUG)
        """
     
        self.logger = MarketMakingLogger(verbosity=verbosity)
        self.strategies = strategies
        self.symbols = list(self.strategies.keys())
        self.n_symbols = len(self.symbols)
        self.wallet_balance = initial_cash
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.min_start = min_start
        self.risk_strategy = risk_strategy

        # Initialize order manager and positions
        self.order_manager = OrderManager(self.logger, maker_fee, taker_fee)
        self.order_manager.set_wallet_balance(initial_cash)
        for symbol in self.symbols:
            self.order_manager.initialize_position(symbol)
        self.positions = self.order_manager.positions

        # Initialize history trackers
        self.portfolio_value_history: List[Dict] = []
        self.wallet_balance_history: List[float] = []
        self.margin_history: List[float] = []

        # Initialize new history trackers
        self.leverage_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.global_leverage_history: List[float] = []
        self.reservation_price_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.price_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.realized_pnl_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.spread_history: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}  # Track spread history
        self.current_risk_metrics: Dict[str, RiskMetrics] = {}

    # Helpers
    def _log_market_data(self, t, symbol, open_price, high, low, close, current_indicators):
        self.logger.log_market_data(t, symbol, {
            'open': open_price,
            'high': high,
            'low': low,
            'close': close
        })
        self.logger.log_indicators(t, symbol, current_indicators)
        
    def _get_local_margin(self):
        return self.margin_history[-1]

    def _get_position_value(self, symbol: str, price: float) -> float: #in USD, positive or negative or 0
        return self.positions[symbol].current_quantity * price

    def _get_total_position_value(self, opening_prices: Dict[str, float]) -> float:
        return sum(self._get_position_value(symbol, price) for symbol, price in opening_prices.items())

    def _get_per_symbol_leverage(self, position_value: float) -> float:
        return position_value / self.per_symbol_margin if self.per_symbol_margin > 0 else float('inf')

    def _get_total_leverage(self, opening_prices: Dict[str, float]) -> float:
        return self._get_total_position_value(opening_prices) / self.margin if self.margin > 0 else float('inf')

    def _calculate_risk_metrics(self, opening_prices: Dict[str, float]) -> Dict[str, RiskMetrics]:
        """Calculate current risk metrics for all symbols at a given timestamp on a per symbol basis
        """
        risk_metrics = {}
        
        for symbol in self.positions:
            position_value = self._get_position_value(symbol, opening_prices[symbol])
            leverage = self._get_per_symbol_leverage(position_value)
            
            metrics = RiskMetrics(
                current_leverage=leverage,
                current_margin=self.per_symbol_margin,
                position_value=position_value
            )
            risk_metrics[symbol] = metrics
            
        return risk_metrics

    def _extend_histories_with_zeros(self, t: int, timestamps: List[int]) -> None:
        """Fill remaining history arrays with zeros when simulation stops early
        """
        remaining_steps = len(timestamps) - t
        for symbol in self.symbols:
            self.leverage_history[symbol].extend([0.0] * remaining_steps)
            self.reservation_price_history[symbol].extend([0.0] * remaining_steps)
            self.price_history[symbol].extend([0.0] * remaining_steps)
            last_pnl = self.realized_pnl_history[symbol][-1] if self.realized_pnl_history[symbol] else 0.0
            self.realized_pnl_history[symbol].extend([last_pnl] * remaining_steps)
        self.wallet_balance_history.extend([0.0] * remaining_steps)
        self.margin_history.extend([0.0] * remaining_steps)

    def _check_margin_conditions(self, t: int) -> bool:
        """Check if margin conditions are met to continue trading
            Returns True if trading should continue, False if it should stop
        """
        initial_margin = self.wallet_balance if not self.margin_history else self.margin_history[0]
        if not self.risk_strategy.continue_simulation(self.current_risk_metrics, initial_margin):
            self.logger.log_risk_small_margin(t, self.margin)
            return False
        if self.margin <= 0:
            self.logger.log_risk_negative_margin(t, self.margin)
            return False
        return True

    def _process_emergency_exits(self, t:int, emergency_exits: Dict[str, bool], opening_prices: Dict[str, float]) -> None:
        """Process emergency exits for positions that exceed risk limits
        
        Args:
            t: Current timestamp
            emergency_exits: Dictionary mapping symbols to whether they need emergency exit
            opening_prices: Dictionary of current prices for each symbol
        """
        if emergency_exits['Total']:
            # market close all positions
            for symbol, position in self.positions.items():
                if abs(position.current_quantity) > 0:
                    order = self.order_manager.create_market_close_order(
                        t, symbol, position.current_quantity, opening_prices[symbol],
                        reason="Emergency exit - Risk limit exceeded"
                    )
                    self.order_manager.execute_order(order)
            return
        # Else, process individual symbol exits
        for symbol, needs_exit in emergency_exits.items():
            if needs_exit:
                position = self.positions[symbol]
                if abs(position.current_quantity) >0:                
                    order = self.order_manager.create_market_close_order(
                        t, symbol, position.current_quantity, opening_prices[symbol],
                        reason="Emergency exit - Risk limit exceeded"
                    )
                    self.order_manager.execute_order(order)

    def _close_simulation_positions(
        self,
        t: int,
        timestamps: List[int],
        prices: Dict[str, Dict[int, float]]
    ) -> None:
        """Close all positions at the end of simulation
        
        Args:
            t: Current timestamp
            timestamps: List of all timestamps
            prices: Dictionary of opening prices
        """
        self.logger.log_simulation_end()
        
        # Close all positions at opening price
        for symbol, position in self.positions.items():
            if abs(position.current_quantity) > 0:
                open_price = prices[symbol][t]
                order = self.order_manager.create_market_close_order(
                    timestamps[t], symbol, position.current_quantity, open_price,
                    reason="End of simulation"
                )
                if order:
                    self.order_manager.execute_order(order)

        # Get updated wallet balance from order manager
        self.wallet_balance = self.order_manager.wallet_balance

        # Update final PnL values and histories
        total_upnl = 0
        for symbol, position in self.positions.items():
            # Update realized PnL history
            self.realized_pnl_history[symbol].append(position.total_realized_pnl)
            # Update unrealized PnL (should be zero after closing)
            position.update_unrealized_pnl(prices[symbol][t])
            total_upnl += position.unrealized_pnl
        assert total_upnl == 0, "Unrealized PnL should be zero after closing"   
        
        # Calculate final margin
        margin = self.wallet_balance + total_upnl

        # Update portfolio metrics
        metrics = {
            'timestamp': t,
            'wallet_balance': self.wallet_balance,
            'margin': margin,
            'total_unrealized_pnl': total_upnl
        }
        self.portfolio_value_history.append(metrics)
        self.wallet_balance_history.append(self.wallet_balance)
        self.margin_history.append(margin)
        self.logger.log_portfolio_update(t, metrics)

        # Update leverage history (should be zero after closing)
        for symbol in self.symbols:
            self.leverage_history[symbol].append(0.0)
        self.global_leverage_history.append(0.0)

    def _update_end_of_timestamp(
        self,
        t: int,
        timestamps: List[int],
        closes: Dict[str, Dict[int, float]]
    ) -> None:
        """Update state at the end of each timestamp
        
        Args:
            t: Current timestamp
            timestamps: List of all timestamps
            closes: Dictionary of close prices
        """
        # Update PnL history for all symbols
        for symbol in self.symbols:
            self.realized_pnl_history[symbol].append(self.positions[symbol].total_realized_pnl)

        # Update unrealized PnL using close price
        total_upnl = 0
        for symbol, position in self.positions.items():
            close = closes[symbol][t]
            position.update_unrealized_pnl(close)
            total_upnl += position.unrealized_pnl
            # Log position summary for each symbol
            self.logger.log_position_state(
                t, symbol, 
                position.current_quantity,
                position.previous_entry_price or 0.0,
                position.unrealized_pnl,
                position.total_realized_pnl,
                self.current_risk_metrics[symbol].current_leverage,
                position.total_fee_paid,
                is_final=True
            )

        # Get wallet balance from order manager
        self.wallet_balance = self.order_manager.wallet_balance

        # Calculate and store margin
        margin = self.wallet_balance + total_upnl
        metrics = {
            'timestamp': t,
            'wallet_balance': self.wallet_balance,
            'margin': margin,
            'total_unrealized_pnl': total_upnl
        }
        self.portfolio_value_history.append(metrics)
        self.wallet_balance_history.append(self.wallet_balance)
        self.margin_history.append(margin)
        self.logger.log_portfolio_update(t, metrics)

        # Recompute risk metrics with updated positions and prices
        closing_prices = {symbol: closes[symbol][t] for symbol in self.symbols}
        self.current_risk_metrics = self._calculate_risk_metrics(closing_prices)

        # Update leverage history with recomputed metrics
        for symbol, metrics in self.current_risk_metrics.items():
            self.leverage_history[symbol].append(metrics.current_leverage)            
        self.global_leverage_history.append(self._get_total_leverage(closing_prices))

    def _process_one_symbol(self, t, symbol, prices, highs, lows, closes, indicators, strategy):
        # if required, compute a local past ohlc : later todo, not required here we access
        # local past trends with the help of indicators
        # could be required eg. if reservation price and spred are computed using
        # some neuralnetwork(of local past ohlc) + volume maybe / or other prediction methods
        
        # Unpack, get relevant local values, log market data
        local_past_ohlc = None
        open_price = prices[symbol][t]
        high = highs[symbol][t]
        low = lows[symbol][t]
        close = closes[symbol][t]
        current_indicators = indicators[symbol][t]

        # Get current position state and log it
        risk_metric = self.current_risk_metrics[symbol]
        position = self.positions.get(symbol)  
        current_quantity = position.current_quantity
        upnl = position.update_unrealized_pnl(open_price)

        return self._get_new_order_list(t, symbol, strategy, open_price,
            current_indicators, current_quantity, upnl, local_past_ohlc
        )

    def _get_new_order_list(
        self,
        t: int,
        symbol: str,
        strategy: BaseStrategy,
        open_price: float,
        current_indicators: Dict[str, float],
        current_quantity : float,
        upnl: float,
        local_past_ohlc: Any = None
    ) -> List[LimitOrder]:
        """Get list of new orders for a single symbol at the given timestamp,
        given trading_strategy, some of which might later be rejected by OrderManager given RiskMetrics"""
    
        # Calculate max inventory and create strategy input
        aggressivity = self.risk_strategy.parameters.aggressivity
        # max lev per symbol
        max_leverage = self.risk_strategy.parameters.max_leverage
        max_inventory = max_leverage*self.per_symbol_margin/open_price #in abs value in asset unit
        strategy_input = StrategyInput(
            timestamp=t,
            current_price=open_price,
            current_inventory=current_quantity,
            current_upnl=upnl/self.per_symbol_margin, #normalized ; can be useful to decide TP/SL, etc
            max_inventory=max_inventory,
            minimal_spread=strategy.parameters.minimal_spread,
            agressivity=aggressivity,
            indicators=current_indicators,
            ohlc_history=local_past_ohlc[symbol] if local_past_ohlc else None
        )
        
        # Get strategy output and store reservation price and spread
        symbol_enum = next((s for s in constants.Symbol if s.value == symbol), None)
        ticksize = constants.SYMBOL_CONFIGS[symbol_enum].ticksize
        strategy_output = strategy.calculate_order_levels(ticksize, strategy_input)
        self.reservation_price_history[symbol].append(strategy_output.reservation_price)
        self.spread_history[symbol].append(strategy_output.spread)  # Track the computed spread

        # Generate orders using order manager
        new_orders = self.order_manager.generate_limit_orders(
            t, symbol, strategy_output, current_quantity,
            max_inventory, self.current_risk_metrics[symbol], len(self.strategies),
            self.risk_strategy
        )
        
        return new_orders

    ################ MAIN ##################
    def run_simulation(
        self,
        timestamps: List[int],
        prices: Dict[str, Dict[int, float]],
        highs: Dict[str, Dict[int, float]],
        lows: Dict[str, Dict[int, float]],
        closes: Dict[str, Dict[int, float]],
        indicators: Dict[str, Dict[int, Dict[str, float]]],
    ):
        """Run market making simulation for multiple symbols in parallel"""
        # Convert price data to the right format
        for symbol in self.symbols:
            self.price_history[symbol] = list(prices[symbol].values())

        for t in range(len(timestamps)):
            # Get local margin, opening_prices, and risk levels
            self.margin = self.margin_history[-1] if self.margin_history else self.wallet_balance
            self.per_symbol_margin = self.margin/self.n_symbols
            opening_prices = {symbol: prices[symbol][t] for symbol in self.symbols}
            self.current_risk_metrics = self._calculate_risk_metrics(opening_prices)
            
            # Log market data for each symbol at the beginning of timestamp
            for symbol in self.symbols:
                self._log_market_data(
                    t, symbol,
                    prices[symbol][t],
                    highs[symbol][t],
                    lows[symbol][t],
                    closes[symbol][t],
                    indicators[symbol][t]
                )
        
            # if required, end simulation
            if not self._check_margin_conditions(t):
                self._extend_histories_with_zeros(t, timestamps)
                break

            # If this is the last timestamp, just close all positions at opening price
            if t == len(timestamps) - 1:
                if self.margin_history[-1] > 0:
                    self._close_simulation_positions(t, timestamps, prices)  # Use prices for opening price
                    # Update reservation price history for final timestamp
                    for symbol in self.symbols:
                        self.reservation_price_history[symbol].append(opening_prices[symbol])
                        self.spread_history[symbol].append(0.0)  # Zero spread at final timestamp

                break

            # Handle pre-min_start period
            if t < self.min_start:
                # For each symbol, set reservation price to current price and spread to zero
                for symbol in self.symbols:
                    self.reservation_price_history[symbol].append(opening_prices[symbol])
                    self.spread_history[symbol].append(0.0)  # Zero spread before min_start
                # Update end of timestamp state
                self._update_end_of_timestamp(t, timestamps, closes)
                continue

            # Regular trading for t >= min_start
            # Check for emergency exits
            emergency_exits = self.risk_strategy.check_emergency_exit(self.current_risk_metrics, self.n_symbols)
            self._process_emergency_exits(t, emergency_exits, opening_prices)
            
            # Cancel old orders based on risk strategy parameters
            self.order_manager.cancel_old_orders(t, self.risk_strategy)
            
            # And process each symbol : call strategy to get new orders for each symbol
            all_new_orders = []

            for symbol, strategy in self.strategies.items():
                new_orders = self._process_one_symbol(t, symbol, prices, highs, lows, closes, indicators, strategy)
                all_new_orders.extend(new_orders)
            
            # Check for filled orders
            filled_orders = []
            for symbol, strategy in self.strategies.items():
                symbol_enum = next((s for s in constants.Symbol if s.value == symbol), None)
                ticksize = constants.SYMBOL_CONFIGS[symbol_enum].ticksize
                high = highs[symbol][t]
                low = lows[symbol][t]
                filled_orders += self.order_manager.check_order_fills(symbol, high, low, ticksize)

            # Execute filled orders
            for order in filled_orders:
                self.order_manager.execute_order(order)

            # Update end of timestamp state for all timestamps
            self._update_end_of_timestamp(t, timestamps, closes)

        # End of simulation
    
        
        return {
            'wallet_balance': self.wallet_balance,
            'positions': self.positions,
            'order_history': self.order_manager.order_history,
            'wallet_balance_history': self.wallet_balance_history,
            'margin_history': self.margin_history,
            'leverage_history': self.leverage_history,
            'global_leverage_history': self.global_leverage_history,
            'reservation_price_history': self.reservation_price_history,
            'price_history': self.price_history,
            'realized_pnl_history': self.realized_pnl_history,
            'spread_history': self.spread_history  # Add spread history to results
        }
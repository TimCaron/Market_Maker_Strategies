from typing import Dict, List, Optional, Tuple, Union
from orders import LimitOrder, MarketOrder, OrderSide, OrderStatus, OrderType
from logger import MarketMakingLogger
from trading_strategies.base_strategy import OrderLevel, StrategyOutput
from risk_management_strategies.base_risk_strategy import RiskMetrics
from position import Position
import random

class OrderManager:
    """Manages order creation, validation, and execution"""
    
    def __init__(self, logger: MarketMakingLogger, maker_fee: float = 0.0002, taker_fee: float = 0.0005):
        self.positions: Dict[str, Position] = {}
        self.wallet_balance: float = 0.0
        """Initialize order manager
        
        Args:
            logger: Logger instance for recording order events
            maker_fee: Fee rate for maker orders (limit orders)
            taker_fee: Fee rate for taker orders (market orders)
        """
        self.logger = logger
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.active_orders: Dict[str, List[LimitOrder]] = {}
        self.order_history: List[LimitOrder] = []

    def initialize_position(self, symbol: str) -> None:
        """Initialize a new position for a symbol"""
        if symbol not in self.positions:
            self.positions[symbol] = Position()

    def set_wallet_balance(self, balance: float) -> None:
        """Set the initial wallet balance"""
        self.wallet_balance = balance

    def cancel_old_orders(self, timestamp: int, risk_strategy) -> None:
        """Cancel orders based on risk strategy parameters
        
        Args:
            timestamp: Current timestamp
            risk_strategy: Risk management strategy instance
        """
        for symbol in self.active_orders:
            orders_to_keep = []
            for order in self.active_orders[symbol]:
                if not risk_strategy.should_cancel_orders(timestamp, order.timestamp):
                    orders_to_keep.append(order)
                else:
                    order.status = OrderStatus.CANCELLED
                    self.logger.log_order_cancellation(timestamp, symbol, order)
            self.active_orders[symbol] = orders_to_keep

    def get_remaining_capacity(self, timestamp: int, symbol: str, side: OrderSide, max_position: float) -> float:
        """Get remaining capacity for new orders based on active orders
        
        Args:
            timestamp: Current timestamp
            symbol: Trading symbol
            side: Order side (BUY/SELL)
            max_position: Maximum position size allowed
            
        Returns:
            float: Remaining capacity in asset units
        """
        active_orders = self.active_orders.get(symbol, [])
        long_quantity = sum(
            order.quantity for order in active_orders 
            if order.side == OrderSide.BUY and order.status == OrderStatus.PENDING
        )
        short_quantity = sum(
            order.quantity for order in active_orders 
            if order.side == OrderSide.SELL and order.status == OrderStatus.PENDING
        )
        
        # Calculate remaining capacity
        current_position = self.positions[symbol].current_quantity
        remaining_long = max_position - current_position - long_quantity
        remaining_short = max_position + current_position - short_quantity
        
        # Only log when called for buy orders to avoid duplicate logging
        if side == OrderSide.BUY:
            self.logger.log_remaining_positions(timestamp, symbol, remaining_long, remaining_short)
        
        if side == OrderSide.BUY:
            return remaining_long
        else:
            return remaining_short

    def generate_limit_orders(
        self,
        timestamp: int,
        symbol: str,
        strategy_output: StrategyOutput,
        current_position: float,
        max_position: float,
        risk_metrics: RiskMetrics,
        n_symbols: int,
        risk_strategy
    ) -> List[LimitOrder]:
        """Generate new orders from strategy output"""
        potential_orders = []
        
        # Calculate remaining capacity considering active orders
        remaining_long_capacity = self.get_remaining_capacity(timestamp, symbol, OrderSide.BUY, max_position)
        remaining_short_capacity = self.get_remaining_capacity(timestamp, symbol, OrderSide.SELL, max_position)
        
        # Generate buy orders
        for level in strategy_output.buy_levels:
            if remaining_long_capacity > 0:
                order = LimitOrder(
                    timestamp=timestamp,
                    symbol=symbol,
                    side=OrderSide.BUY,
                    price=level.price,
                    quantity=level.size
                )
                potential_orders.append(order)
                remaining_long_capacity -= level.size
                
        # Generate sell orders
        for level in strategy_output.sell_levels:
            if remaining_short_capacity > 0:
                order = LimitOrder(
                    timestamp=timestamp,
                    symbol=symbol,
                    side=OrderSide.SELL,
                    price=level.price,
                    quantity=level.size
                )
                potential_orders.append(order)
                remaining_short_capacity -= level.size
                
        # Validate orders through risk management
        orders = []
        for order in potential_orders:
            if risk_strategy.validate_single_order(order, strategy_output.reservation_price, risk_metrics, n_symbols):
                orders.append(order)

        # Initialize active orders list for symbol if not exists
        if symbol not in self.active_orders:
            self.active_orders[symbol] = []
            
        # Extend active orders and history
        self.active_orders[symbol].extend(orders)
        self.order_history.extend(orders)
        
        # Log orders
        self.logger.log_orders(timestamp, symbol, orders)
        
        return orders

    def create_market_close_order(
        self,
        timestamp: int,
        symbol: str,
        position_size: float,
        close_price: float,
        reason: str = "Position close"
    ) -> Optional[MarketOrder]:
        """Create a market order to close a position
        
        Args:
            timestamp: Current timestamp
            symbol: Trading symbol
            position_size: Current position size
            close_price: Price to close at
            reason: Reason for closing the position (e.g. 'Emergency exit', 'End of simulation')
            
        Returns:
            Market order to close position, or None if no position
        """
        if abs(position_size) > 0:
            side = OrderSide.SELL if position_size > 0 else OrderSide.BUY
            order = MarketOrder(
                timestamp=timestamp,
                symbol=symbol,
                side=side,
                quantity=abs(position_size),
                price=close_price,
                reason=reason
            )
            # Log position closing
            self.logger.log_position_close(timestamp, symbol, reason, position_size, close_price)
            return order
        return None

    def check_order_fills(
        self,
        symbol: str,
        high: float,
        low: float,
        ticksize: float
    ) -> List[LimitOrder]:
        """Check which orders would have been filled
        
        Args:
            symbol: Trading symbol
            high: High price during the period
            low: Low price during the period
            ticksize: Minimum price movement
            
        Returns:
            List of filled orders
        """
        filled_orders = []
        active_orders = self.active_orders.get(symbol, [])
        
        # Separate long and short orders
        long_orders = [order for order in active_orders 
                      if order.side == OrderSide.BUY and order.status == OrderStatus.PENDING]
        short_orders = [order for order in active_orders 
                       if order.side == OrderSide.SELL and order.status == OrderStatus.PENDING]
        
        # Randomly decide whether to execute longs or shorts first
        execute_longs_first = random.random() < 0.5
        
        if execute_longs_first:
            # Execute long orders first
            for order in long_orders:
                if low <= order.price - ticksize:
                    order.status = OrderStatus.FILLED
                    filled_orders.append(order)
            # Then execute short orders
            for order in short_orders:
                if high >= order.price + ticksize:
                    order.status = OrderStatus.FILLED
                    filled_orders.append(order)
        else:
            # Execute short orders first
            for order in short_orders:
                if high >= order.price + ticksize:
                    order.status = OrderStatus.FILLED
                    filled_orders.append(order)
            # Then execute long orders
            for order in long_orders:
                if low <= order.price - ticksize:
                    order.status = OrderStatus.FILLED
                    filled_orders.append(order)
                    
        return filled_orders

    def execute_order(self, order: Union[LimitOrder, MarketOrder]) -> Tuple[bool, float]:
        symbol = order.symbol
        position = self.positions[symbol]
        old_position_size = position.current_quantity
        trade_size = order.quantity if order.side == OrderSide.BUY else -order.quantity
        updated_position_size = old_position_size + trade_size
        fee_rate = self.maker_fee if order.order_type == OrderType.LIMIT else self.taker_fee

        realized_pnl, fee_paid = position.execute_position_change(
            execution_price=order.price,
            old_position_size=old_position_size,
            updated_position_size=updated_position_size,
            trade_size=trade_size,
            fee_rate=fee_rate
        )
        
        # Update wallet balance with realized PnL minus fees
        net_pnl = realized_pnl - fee_paid
        self.wallet_balance += net_pnl
        position.total_realized_pnl += realized_pnl
        position.total_fee_paid += fee_paid

        # Remove the filled order from active orders
        if symbol in self.active_orders:    
            self.active_orders[symbol] = [o for o in self.active_orders[symbol] if o != order]
            
        # Log execution with net PnL (realized PnL minus fees)
        self.logger.log_trade_execution(
            order.timestamp,
            symbol,
            order.side.value,
            order.price,
            order.quantity,
            realized_pnl, 
            fee_paid
        )
        
        # Log position state after execution
        self.logger.log_position_state(
            order.timestamp,
            symbol,
            position.current_quantity,
            position.previous_entry_price or 0.0,
            position.unrealized_pnl,
            position.total_realized_pnl,
            self._get_leverage(symbol, order.price),
            position.total_fee_paid,
            is_final=False  # This is the final position state at the end of the timestamp
        )
        
        return True, net_pnl
        
    def _get_leverage(self, symbol: str, price: float) -> float:
        """Calculate leverage for a symbol at given price"""
        position = self.positions[symbol]
        position_value = position.current_quantity * price
        return abs(position_value) / self.wallet_balance if self.wallet_balance > 0 else 0.0
   
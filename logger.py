import logging
from typing import Dict, Any, List, Union
from datetime import datetime
from orders import LimitOrder, MarketOrder

class MarketMakingLogger:
    def __init__(self, log_file: str = 'market_making.log', verbosity: int = 1):
        """Initialize logger with configurable verbosity
        
        Args:
            log_file: Path to log file
            verbosity: Logging level (0=ERROR, 1=INFO, 2=DEBUG)
        """
        # Map numeric verbosity to logging level
        self.verbosity_levels = {
            0: logging.ERROR,     # Basic error information
            1: logging.INFO,      # Standard information (OHLC, executed orders, final metrics)
            2: logging.DEBUG      # Detailed information (position states, inventory, prices)
        }
        
        # Validate verbosity
        if verbosity not in self.verbosity_levels:
            raise ValueError(f"Invalid verbosity level. Must be one of {list(self.verbosity_levels.keys())}")
        self.verbosity = verbosity
        log_level = self.verbosity_levels[verbosity]
        
        # Get or create logger
        self.logger = logging.getLogger('MarketMaking')
        
        # Only set up handlers if they haven't been set up before
        if not self.logger.handlers:
            self.logger.setLevel(log_level)
            
            # File handler
            fh = logging.FileHandler(log_file)
            fh.setLevel(log_level)
            
            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(log_level)
            
            # Formatter
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            
            # Add handlers
            self.logger.addHandler(fh)
            self.logger.addHandler(ch)
        else:
            # If handlers exist, just update their log levels
            self.logger.setLevel(log_level)
            for handler in self.logger.handlers:
                handler.setLevel(log_level)
    
    def log_market_data(self, timestamp: int, symbol: str, ohlc: Dict[str, float]):
        msg = f"[Market Data] {symbol} - Time: {timestamp} - Open: {ohlc['open']:.2f} High: {ohlc['high']:.2f} Low: {ohlc['low']:.2f} Close: {ohlc['close']:.2f}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)
    
    def log_indicators(self, timestamp: int, symbol: str, indicators: Dict[str, float]):
        if self.verbosity >= 2:  # DEBUG only
            indicator_str = ' '.join([f"{k}: {v:.4f}" for k, v in indicators.items()])
            msg = f"[Indicators] {symbol} - Time: {timestamp} - {indicator_str}"
            self.logger.debug(msg)
    
    def log_position_state(
        self,
        timestamp: int,
        symbol: str,
        size: float,
        avg_entry: float,
        unrealized_pnl: float,
        realized_pnl: float,
        leverage: float,
        fees: float,
        is_final: bool = False
    ) -> None:
        """Log position state
        
        Args:
            is_final: If True, indicates this is the final position state at the end of the timestamp
        """
        prefix = "[Position at end of timestamp]" if is_final else "[Position]"
        message = (
            f"{prefix} {symbol} - Time: {timestamp} - "
            f"Size: {size:.4f} AvgEntry: {avg_entry:.2f} "
            f"uPnL: {unrealized_pnl:.2f} rPnL: {realized_pnl:.2f} "
            f"Fees: {fees:.2f} Leverage: {leverage:.2f}x"
        )
        self.logger.info(message)

    def log_trade_execution(self, timestamp: int, symbol: str, side: str, price: float,
                           quantity: float, pnl: float, fee: float = 0.0):
        msg = f"[Executed Order] {symbol} - Time: {timestamp} - {side.upper()} Price: {price:.2f} Qty: {quantity:.4f} Fee: {fee:.4f} PnL: {pnl:.2f}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)
    
    def log_portfolio_update(self, timestamp: int, metrics: Dict[str, float]):
        metrics_str = ' '.join([f"{k}: {v:.2f}" for k, v in metrics.items()])
        msg = f"[Portfolio] Time: {timestamp} - {metrics_str}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)
            
    def log_orders(self, timestamp: int, symbol: str, orders: List):
        if self.verbosity >= 2:  # DEBUG only
            for order in orders:
                msg = f"[Posting Order] {symbol} - Time: {timestamp} - {order.side.value.upper()} {order.order_type.value} - Price: {order.price:.2f} Qty: {order.quantity:.4f} Status: {order.status.value}"
                self.logger.info(msg)

    # Risk Management Logging Methods
    def log_risk_order_validation(self, order, value: float, min_value: float):
        """Log order validation details"""
        msg = (f"Risk Management: Order rejected - Value (${value:.2f}) below minimum (${min_value:.2f})")
        if self.verbosity >= 1:
            self.logger.info(msg)
            
    def log_simulation_end(self):
        """Log end of simulation marker and final summary"""
        msg = "[Simulation] Simulation completed successfully"
        if self.verbosity >= 1:
            self.logger.info(msg)
        self.logger.debug(msg)

    def log_risk_leverage_validation(self, order, new_leverage: float, max_leverage: float):
        """Log leverage validation details"""
        msg = (f"Risk Management: Order rejected - New leverage ({new_leverage:.2f}) would exceed max ({max_leverage:.2f})"
               f" Symbol: {order.symbol}, Side: {order.side.value}, Price: {order.price:.2f}, Quantity: {order.quantity:.8f}")
        self.logger.debug(msg)

    def log_risk_order_accepted(self, order, new_leverage: float):
        """Log successful order validation"""
        msg = (f"Risk Management: Order validated - Symbol: {order.symbol}, Side: {order.side.value}, "
               f"Price: {order.price:.2f}, Quantity: {order.quantity:.8f}, New Leverage: {new_leverage:.2f}")
        self.logger.debug(msg)

    def log_risk_emergency_exit(self, symbol: str, current_leverage: float, threshold: float):
        """Log emergency exit trigger"""
        msg = (f"Risk Management: Emergency exit needed for {symbol} - "
               f"Current leverage ({current_leverage:.2f}) exceeds emergency threshold ({threshold:.2f})")
        self.logger.warning(msg)

    def log_risk_simulation_stop(self, timestamp: int, metrics: Dict[str, Any]):
        """Log simulation stop due to risk limits"""
        self.logger.error(f"Risk Management: Simulation stopped at timestamp {timestamp}")
        self.logger.info("Risk Management Metrics at stop:")
        for symbol, m in metrics.items():
            self.logger.info(f"  {symbol}:")
            self.logger.info(f"    Leverage: {m.current_leverage:.2f}")
            self.logger.info(f"    Position Value: {m.position_value:.2f}")
            self.logger.info(f"    Current Margin: {m.current_margin:.2f}")

    def log_risk_negative_margin(self, timestamp: int, margin: float):
        """Log negative margin detection"""
        msg = f"Risk Management: Negative margin ({margin:.2f}) detected at timestamp {timestamp}. Stopping simulation."
        self.logger.error(msg)
    
    def log_risk_small_margin(self, timestamp: int, margin: float):
        """Log too small margin detection"""
        msg = f"Risk Management: too small margin ({margin:.2f}) detected at timestamp {timestamp}. Stopping simulation."
        self.logger.error(msg)

    def log_risk_margin_ratio(self, margin_ratio: float, threshold: float):
        """Log margin ratio status"""
        msg = (f"Risk Management: Simulation continues - "
               f"Current margin ratio: {margin_ratio:.2%}, Threshold: {threshold:.2%}")
        self.logger.debug(msg)

    # Strategy Logging Methods
    def log_strategy_info(self, strategy_name: str, message: str):
        """Log strategy-specific information"""
        msg = f"[{strategy_name}] {message}"
        self.logger.info(msg)

    def log_strategy_debug(self, strategy_name: str, message: str):
        """Log strategy-specific debug information with enhanced formatting for formula components"""
        # Split message into lines for better formatting
        lines = message.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Check if this is a formula component line (starts with spaces)
            if line.startswith('  '):
                # Keep the indentation and formatting
                formatted_lines.append(line)
            else:
                # Main headers get special formatting
                formatted_lines.append(line)
        
        # Join lines back together
        formatted_msg = '\n'.join(formatted_lines)
        msg = f"[{strategy_name}] {formatted_msg}"
        
        # Log with special handling for formula debug info
        if 'Formula Components' in message:
            # Write to both debug and info levels for formula components
            self.logger.info(msg)  # Make sure formula components are always visible
            self.logger.debug(msg)  # Also keep in debug log
        else:
            self.logger.debug(msg)

    def log_position_close(self, timestamp: int, symbol: str, reason: str, position_size: float, close_price: float):
        """Log position closing details"""
        msg = f"[Position Close] {symbol} - Time: {timestamp} - Size: {position_size:.4f} Price: {close_price:.2f} - Reason: {reason}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)

    def log_remaining_positions(self, timestamp: int, symbol: str, long_quantity: float, short_quantity: float):
        """Log remaining long and short positions for a symbol"""
        msg = f"[Remaining possible qty] {symbol} - Time: {timestamp} - Long: {long_quantity:.4f} Short: {short_quantity:.4f}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)

    def log_order_cancellation(self, timestamp: int, symbol: str, order: Union[LimitOrder, MarketOrder]):
        """Log order cancellation details"""
        msg = f"[Order Cancellation] {symbol} - Time: {timestamp} - {order.side.value.upper()} {order.order_type.value} - Price: {order.price:.2f} Qty: {order.quantity:.4f}"
        if self.verbosity >= 1:  # INFO and DEBUG
            self.logger.info(msg)
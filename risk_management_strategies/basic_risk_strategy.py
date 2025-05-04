from typing import Dict, List, Any
from orders import LimitOrder, OrderSide
from .base_risk_strategy import BaseRiskStrategy, RiskStrategyParameters, RiskMetrics

class BasicRiskStrategy(BaseRiskStrategy):
    """Basic implementation of risk management strategy"""
    
    def validate_single_order(
        self,
        order: LimitOrder,
        current_price: float,
        risk_metrics: RiskMetrics,
        n_symbols: int
    ) -> bool:
        """
        Validate a single order based on basic risk rules:
        - Check minimum order value
        - Check if new position would exceed leverage limits
        """
        # Check minimum order value
        order_value = order.quantity * current_price
        if order_value < self.parameters.min_order_value_usd:
            self.logger.log_risk_order_validation(order, order_value, self.parameters.min_order_value_usd)
            return False
            
        # Calculate new position value if order is executed
        new_position_value = risk_metrics.position_value
        if order.side == OrderSide.BUY:
            new_position_value += order_value
        else:
            new_position_value -= order_value
        
        # is already normalized by n_symbols
        allowed_margin_per_symbol = risk_metrics.current_margin
        # Calculate new leverage on a per symbol basis
        new_leverage = abs(new_position_value) / allowed_margin_per_symbol
        max_leverage_per_symbol = self.parameters.max_leverage/n_symbols
        
        # Check if new leverage would exceed limit per symbol
        if new_leverage > max_leverage_per_symbol:
            self.logger.log_risk_leverage_validation(order, new_leverage, max_leverage_per_symbol)
            return False
            
        self.logger.log_risk_order_accepted(order, new_leverage)
        return True
    
    def check_emergency_exit(
        self,
        risk_metrics: Dict[str, RiskMetrics],
        n_symbols: int
    ) -> Dict[str, bool]:
        """Check if any positions exceed emergency exit leverage"""
        emergency_exits = {'Total': False}
        emergency_leverage_per_symbol = self.parameters.emergency_exit_leverage/n_symbols
        
        for symbol, metrics in risk_metrics.items():
            current_leverage = abs(metrics.current_leverage)
            needs_exit = current_leverage >= emergency_leverage_per_symbol
            emergency_exits[symbol] = needs_exit
            if needs_exit:
                self.logger.log_risk_emergency_exit(symbol, current_leverage, emergency_leverage_per_symbol)
        # Also check the total leverage
        total_leverage = sum([metrics.current_leverage for metrics in risk_metrics.values()])
        if abs(total_leverage) >= self.parameters.max_leverage:
            self.logger.log_risk_emergency_exit('Total', total_leverage, self.parameters.max_leverage)
            emergency_exits['Total'] = True
            
        return emergency_exits
    
    def should_stop_trading(
        self,
        risk_metrics: Dict[str, RiskMetrics],
    ) -> bool:
        """Stop trading if ... write logic ; for instance could be too much volatility / crashes"""
        raise NotImplementedError

    def continue_simulation(
        self,
        risk_metrics: Dict[str, RiskMetrics],
        initial_margin: float
    ) -> bool:
        """
        Determine if simulation should continue based on risk metrics:
        Stop if total margin falls below early stopping threshold
        """
        # Calculate total margin across all symbols
        total_margin = sum(metrics.current_margin for metrics in risk_metrics.values())
        margin_ratio = total_margin / initial_margin
        
        if margin_ratio <= self.parameters.early_stopping_margin:
            self.logger.log_risk_margin_ratio(margin_ratio, self.parameters.early_stopping_margin)
            return False
            
        self.logger.log_risk_margin_ratio(margin_ratio, self.parameters.early_stopping_margin)
        return True
from dataclasses import dataclass
from typing import Dict
from orders import LimitOrder
from logger import MarketMakingLogger
from .default_parameters import DefaultRiskParameters

@dataclass
class RiskMetrics: # is on a per symbol basis
    current_leverage: float
    current_margin: float
    position_value: float #used

class BaseRiskStrategy:
    """Base class for risk management strategies"""
    
    def __init__(self, parameters: DefaultRiskParameters):
        self.parameters = parameters
        self.logger = MarketMakingLogger(verbosity=2)  # Default to DEBUG level
    
    def validate_single_order(
        self,
        order: LimitOrder,
        current_price: float,
        risk_metrics: RiskMetrics,
        n_symbols: int
    ) -> bool:
        """
        Validate if a single order complies with risk management rules.
        
        Args:
            order: Order to validate
            current_price: Current price for the symbol
            risk_metrics: Current risk metrics for the symbol
            n_symbols: Number of symbols in the portfolio
        Returns:
            bool: True if order is valid, False otherwise
        """
        raise NotImplementedError("Subclasses must implement validate_single_order")
    
    def check_emergency_exit(
        self,
        risk_metrics: Dict[str, RiskMetrics],
        n_symbols: int
    ) -> Dict[str, bool]:
        """
        Check if any positions need emergency exit.
        
        Args:
            risk_metrics: Current risk metrics for each symbol
            n_symbols: Number of symbols in the portfolio
            
        Returns:
            Dictionary mapping symbol to boolean indicating if emergency exit is needed
        """
        raise NotImplementedError("Subclasses must implement check_emergency_exit")
    
    def should_stop_trading(
        self,
        risk_metrics: Dict[str, RiskMetrics]
    ) -> bool:
        """
        Check if trading should be stopped due to risk limits.
        
        Args:
            risk_metrics: Current risk metrics for each symbol
            
        Returns:
            True if trading should be stopped
        """
        raise NotImplementedError("Subclasses must implement should_stop_trading")

    def continue_simulation(
        self,
        risk_metrics: Dict[str, RiskMetrics],
        initial_margin: float
    ) -> bool:
        """
        Determine if simulation should continue based on risk metrics.
        
        Args:
            risk_metrics: Current risk metrics for each symbol
            n_symbols: Number of symbols in the portfolio
            initial_margin: Initial margin at start of simulation
            
        Returns:
            bool: True if simulation should continue, False if it should stop
        """
        raise NotImplementedError("Subclasses must implement continue_simulation")

    def should_cancel_orders(self, timestamp: int, order_timestamp: int) -> bool:
        """Check if orders should be canceled based on strategy parameters"""
        if self.parameters.cancel_orders_every_timestamp:
            return True
        if self.parameters.max_order_age is not None:
            return timestamp - order_timestamp >= self.parameters.max_order_age
        return False 
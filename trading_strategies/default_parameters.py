from dataclasses import dataclass
from typing import Dict, Any
from constants import DEFAULT_PARAMS

@dataclass
class DefaultParameters:
    """Base class containing default parameters for all strategies; 
    """
    # max_orders : Number of quote orders per symbol
    # Meaning ou will quote eg bid at price - spread/2 - i*spread, i=0,1,2,..., max_orders - 1
    max_orders: int = 1

    # Minimum spread between orders: if set to : 2*DEFAULT_PARAMS['maker_fee'], 
    # the spread you win exactly compensate the fees ; lets take 4
    minimal_spread: float = 4*DEFAULT_PARAMS['maker_fee']

    use_adaptive_sizes: bool = False #if False, all orders will have the same size given by max_inventory / max_orders
    # else it will be max_remaining_inventory / max_orders (per side)
    
    # Window parameters for indicators: volatility, sma, momentum, high-low sma, etc.
    # Change this at will
    window_vol: int = 7
    window_sma: int = 7
    window_mom: int = 7
    window_high_low: int = 3
    
@dataclass
class StoikovParameters(DefaultParameters):
    # Stoikov-specific parameters
    risk_aversion: float = 0.1
    gamma_spread: float = 0.1


@dataclass
class TokyoParameters(DefaultParameters):
    # Tokyo-specific parameters : None
    # Explore Tokyo free parameters : max_order and constant spread 
    # By modifying the default parameters
    pass

@dataclass
class MexicoParameters(DefaultParameters):
    # Mexico specific parameters
    q_factor: float = 0.01
    upnl_factor: float = 0.1
    mean_revert_factor: float = 0.2
    momentum_factor: float = 0.1
    
    # Spread parameters
    constant_spread: float = 0.005
    vol_factor: float = 0.1
    spread_mom_factor: float = 0.05
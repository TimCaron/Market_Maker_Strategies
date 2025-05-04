"""Module for calculating advanced performance metrics."""
import numpy as np
from typing import List, Dict

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from a list of returns.
    
    Args:
        returns: List of period returns
        risk_free_rate: Risk-free rate (annualized)
        
    Returns:
        Sharpe ratio (annualized)
    """
    if not returns:
        return 0.0
    returns = np.array(returns)
    excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
    if len(excess_returns) < 2:
        return 0.0
    return np.sqrt(252) * np.mean(excess_returns) / (np.std(excess_returns, ddof=1) + 1e-10)

def calculate_sortino_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Calculate Sortino ratio from a list of returns.
    
    Args:
        returns: List of period returns
        risk_free_rate: Risk-free rate (annualized)
        
    Returns:
        Sortino ratio (annualized)
    """
    if not returns:
        return 0.0
    returns = np.array(returns)
    excess_returns = returns - (risk_free_rate / 252)
    if len(excess_returns) < 2:
        return 0.0
    downside_returns = excess_returns[excess_returns < 0]
    downside_std = np.std(downside_returns, ddof=1) if len(downside_returns) > 1 else 1e-10
    return np.sqrt(252) * np.mean(excess_returns) / (downside_std + 1e-10)

def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Calculate maximum drawdown from equity curve.
    
    Args:
        equity_curve: List of portfolio values
        
    Returns:
        Maximum drawdown as a percentage
    """
    if not equity_curve:
        return 0.0
    equity_curve = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    return abs(min(drawdown, default=0.0))

def calculate_fee_breakdown(order_history: List[Dict]) -> Dict[str, float]:
    """Calculate detailed fee breakdown from order history.
    
    Args:
        order_history: List of order dictionaries
        
    Returns:
        Dictionary containing fee breakdowns
    """
    maker_fees = 0.0
    taker_fees = 0.0
    total_volume = 0.0
    
    for order in order_history:
        if order.status == 'FILLED':
            fee = order['fee'] if 'fee' in order else 0.0
            volume = order['quantity'] * order['price']
            total_volume += volume
            
            if order.get('is_maker', True):
                maker_fees += fee
            else:
                taker_fees += fee
    
    return {
        'maker_fees': maker_fees,
        'taker_fees': taker_fees,
        'total_fees': maker_fees + taker_fees,
        'total_volume': total_volume,
        'fee_to_volume_bps': ((maker_fees + taker_fees) / (total_volume + 1e-10)) * 10000
    }
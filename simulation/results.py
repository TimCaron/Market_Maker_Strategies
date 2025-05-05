"""
Module for processing and reporting simulation results.
"""
from typing import Dict, List
from constants import DEFAULT_PARAMS
from visualization import plot_strategy_metrics
from simulation.performance_metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_fee_breakdown
)


def process_results(results: Dict, symbols: List[str], strategies: Dict, risk_params: Dict) -> None:
    """
    Process and display simulation results.
    
    Args:
        results: Dictionary containing simulation results
        symbols: List of symbols that were simulated
        strategies: Dictionary containing strategy configurations
        risk_params: Dictionary containing risk strategy parameters
    """
    # Calculate returns and performance metrics
    wallet_history = results['wallet_balance_history']
    returns = [(wallet_history[i] - wallet_history[i-1]) / wallet_history[i-1] 
              for i in range(1, len(wallet_history))]
    
    sharpe = calculate_sharpe_ratio(returns)
    sortino = calculate_sortino_ratio(returns)
    max_dd = calculate_max_drawdown(wallet_history)
    fee_metrics = calculate_fee_breakdown(results['order_history'])
    
    # Print portfolio summary
    print("\nPortfolio Summary:")
    print(f"Initial Balance: {DEFAULT_PARAMS['initial_cash']:.2f}")
    print(f"Final Wallet Balance: {results['wallet_balance']:.2f}")
    print(f"Final Margin: {results['margin_history'][-1]:.2f}")
    print(f"Total Number of Trades: {len(results['order_history'])}")
    
    # Print performance metrics
    print("\nPerformance Metrics:")
    print(f"Sharpe Ratio: {sharpe:.4f}")
    print(f"Sortino Ratio: {sortino:.4f}")
    print(f"Maximum Drawdown: {max_dd*100:.2f}%")
    
    # Print fee breakdown
    print("\nFee Analysis:")
    print(f"Maker Fees: {fee_metrics['maker_fees']:.4f}")
    print(f"Taker Fees: {fee_metrics['taker_fees']:.4f}")
    print(f"Total Fees: {fee_metrics['total_fees']:.4f}")
    print(f"Fee/Volume (bps): {fee_metrics['fee_to_volume_bps']:.2f}")
    
    # Calculate total PnL
    total_realized_pnl = 0.0
    total_unrealized_pnl = 0.0
    
    # Print position details for each symbol
    print("\nPosition Details:")
    for symbol in symbols:
        if symbol in results['positions']:
            pos = results['positions'][symbol]
            total_realized_pnl += pos.total_realized_pnl
            total_unrealized_pnl += pos.unrealized_pnl
            print(f"\n{symbol}:")
            print(f"  Realized PnL: {pos.total_realized_pnl:.2f}")
            print(f"  Unrealized PnL: {pos.unrealized_pnl:.2f}")
    
    # Print total PnL summary
    print(f"\nTotal PnL Summary:")
    print(f"Total Realized PnL: {total_realized_pnl:.2f}")
    print(f"Total Unrealized PnL: {total_unrealized_pnl:.2f}")
    print(f"Total PnL: {(total_realized_pnl + total_unrealized_pnl):.2f}")

    # Create price dictionary for visualization
    symbol_prices = {
        'BTCUSDT': results['price_history']['BTCUSDT']
    }

    # Print information about visualization arguments
    print("\nVisualization Arguments:")
    print("-" * 50)
    
    viz_args = {
        'prices': symbol_prices,
        'wallet_balance_history': results['wallet_balance_history'],
        'margin_history': results['margin_history'], 
        'positions': results['positions'],
        'initial_cash': DEFAULT_PARAMS['initial_cash'],
        'leverage_history': results['leverage_history'],
        'global_leverage_history': results['global_leverage_history'],
        'reservation_price_history': results['reservation_price_history'],
        'price_history': results['price_history'],
        'realized_pnl_history': results['realized_pnl_history'],
        'spread_history': results['spread_history'],
        'params': strategies,
        'risk_params': risk_params
    }
   
   
    # Generate visualization
    plot_strategy_metrics(
        prices=symbol_prices,
        wallet_balance_history=results['wallet_balance_history'],
        margin_history=results['margin_history'],
        positions=results['positions'],
        initial_cash=DEFAULT_PARAMS['initial_cash'],
        leverage_history=results['leverage_history'],
        global_leverage_history=results['global_leverage_history'],
        reservation_price_history=results['reservation_price_history'],
        price_history=results['price_history'],
        realized_pnl_history=results['realized_pnl_history'],
        spread_history=results['spread_history'],
        params=strategies,
        risk_params=risk_params
    )
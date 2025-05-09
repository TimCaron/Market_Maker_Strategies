import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Union, Optional
from position import Position
from constants import DEFAULT_PARAMS

def plot_strategy_metrics(
    prices: Dict[str, List[float]],
    wallet_balance_history: List[float],
    margin_history: List[float],
    positions: Dict[str, Position],
    initial_cash: float,
    leverage_history: Dict[str, List[float]],
    global_leverage_history: List[float],
    reservation_price_history: Dict[str, List[float]],
    price_history: Dict[str, List[float]],
    realized_pnl_history: Dict[str, List[float]],
    spread_history: Dict[str, List[float]],
    params: Optional[Dict[str, Dict[str, Dict[str, Union[float, int]]]]] = None,
    risk_params: Optional[Dict] = None
):
    """Plot key metrics from market making strategy simulation."""
    # Create figure with subplots (2x2 grid)
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle('Market Making Strategy Performance')
    
    # Plot 1: Portfolio Value vs Price (normalized)
    ax1 = plt.subplot(2, 2, 1)
    
    # Plot each symbol's price normalized to initial cash
    for symbol, symbol_prices in prices.items():
        norm_prices = np.array(symbol_prices) / symbol_prices[0] * initial_cash
        ax1.plot(norm_prices, label=f'{symbol} Price', alpha=0.7)
    
    # Plot wallet balance and margin
    ax1.plot(wallet_balance_history, label='Wallet Balance', linewidth=2, color='blue')
    ax1.plot(margin_history, label='Margin', linewidth=2, color='orange')
    
    ax1.set_title('Portfolio Value vs Asset Prices (Normalized)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot 2: Cumulative Realized PnL History
    ax2 = plt.subplot(2, 2, 2)
    
    # Plot cumulative realized PnL for each symbol as percentage of initial margin
    initial_margin = margin_history[0] if margin_history else initial_cash
    for symbol, pnl_history in realized_pnl_history.items():
        pnl_percent = 100 * np.array(pnl_history) / initial_margin
        ax2.plot(pnl_percent, label=f'{symbol} PnL %', alpha=0.7)
    
    # Plot total cumulative PnL as percentage
    total_pnl = np.zeros(len(next(iter(realized_pnl_history.values()))))
    for pnl_history in realized_pnl_history.values():
        total_pnl += np.array(pnl_history)
    total_pnl_percent = 100 * total_pnl / initial_margin
    ax2.plot(total_pnl_percent, label='Total PnL %', color='black', linewidth=2)
    
    ax2.set_title('Cumulative Realized PnL History (%)')
    ax2.legend()
    ax2.grid(True)
    
    # Plot 3: Historical Leverage
    ax3 = plt.subplot(2, 2, 3)
    # Plot per-symbol leverage
    n_symbols = len(leverage_history)
    for symbol, leverage in leverage_history.items():
        # leverage is per symbol basis, transform it back to global leverage
        global_leverage = [leverage[i] / n_symbols for i in range(len(leverage))]
        ax3.plot(global_leverage, label=f'{symbol} Leverage', alpha=0.5)
    # Plot global leverage with thicker line
    ax3.plot(global_leverage_history, label='Global Leverage', color='black', linewidth=2)
    ax3.set_title('Historical Leverage')
    ax3.legend()
    ax3.grid(True)
    
    # Plot 4: Spread History and Price Differences
    ax4 = plt.subplot(2, 2, 4)
    data_length = len(next(iter(price_history.values())))
    for symbol in realized_pnl_history.keys():
        # Plot spread history as percentage of current price
        price_arr = np.array(price_history[symbol])
        spread_arr = np.array(spread_history[symbol])
        rel_spread = 100 * spread_arr / price_arr  # Spread in percent
        ax4.plot(rel_spread, label=f'{symbol} Spread %', color='blue', alpha=0.7)
        
        # Extract minimal spread from strategy parameters
        minimal_spreads = []
        for symbol_params in params.values():
            for strategy_params in symbol_params.values():
                # Handle both dict and object parameter formats
                if isinstance(strategy_params, dict):
                    if 'minimal_spread' in strategy_params:
                        minimal_spreads.append(strategy_params['minimal_spread'])
                else:
                    if hasattr(strategy_params, 'minimal_spread'):
                        minimal_spreads.append(strategy_params.minimal_spread)
        
        # Plot minimal spread lines if available
        for minimal_spread in minimal_spreads:
            ax4.axhline(y=100 * minimal_spread, color='gray', linestyle='--', alpha=0.3, label=f'{symbol} Min Spread %')
        
        # Calculate and plot relative price difference in percent
        if price_history[symbol][0] != 0:
            res_arr = np.array(reservation_price_history[symbol])
            rel_diff = 100 * (res_arr - price_arr) / price_arr  # Difference in percent
            ax4.plot(rel_diff, label=f'{symbol} Res-Price Diff %', color='red', linestyle='--', alpha=0.7)
        else:
            print(f"Warning: Initial price for {symbol} is zero, skipping relative difference")
    
    ax4.set_xlim(0, data_length)
    ax4.set_title('Spread and Reservation Price Difference (%)')
    ax4.legend()
    ax4.grid(True)
    
    plt.tight_layout()
    plt.show()

def save_strategy_plots(
    prices: Dict[str, List[float]],
    wallet_balance_history: List[float],
    margin_history: List[float],
    positions: Dict[str, Position],
    initial_cash: float,
    leverage_history: Dict[str, List[float]],
    global_leverage_history: List[float],
    reservation_price_history: Dict[str, List[float]],
    price_history: Dict[str, List[float]],
    realized_pnl_history: Dict[str, List[float]],
    params: Optional[Dict[str, Dict[str, Dict[str, Union[float, int]]]]] = None,
    filename: str = 'strategy_plots.png'
):
    """Save strategy metrics plots to a file.
    
    Args:
        prices: Dictionary of price history for each symbol
        wallet_balance_history: History of wallet balance
        margin_history: History of margin values
        positions: Dictionary of final positions for each symbol
        initial_cash: Initial cash balance
        leverage_history: Historical leverage values per symbol
        global_leverage_history: Historical global leverage values
        reservation_price_history: Historical reservation prices per symbol
        price_history: Historical prices per symbol
        realized_pnl_history: Historical realized PnL history per symbol
        params: Dictionary of strategy parameters used in simulation
               Structure: {symbol: {strategy_name: {param_name: param_value}}}
        filename: Output file path for the plot
    """
    plot_strategy_metrics(
        prices=prices,
        wallet_balance_history=wallet_balance_history,
        margin_history=margin_history,
        positions=positions,
        initial_cash=initial_cash,
        leverage_history=leverage_history,
        global_leverage_history=global_leverage_history,
        reservation_price_history=reservation_price_history,
        price_history=price_history,
        realized_pnl_history=realized_pnl_history,
        params=params
    )
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
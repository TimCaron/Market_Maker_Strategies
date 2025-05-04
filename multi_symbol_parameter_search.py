from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import itertools
from market_maker import MarketMakerSimulation
from trading_strategies.stoikov_strategy import StoikovStrategy, StoikovParameters
from constants import Symbol, SYMBOL_CONFIGS, DEFAULT_PARAMS

# see comment below
#   # indicators format is like :
    # {
    # 'BTCUSDT': {
    #    0: {'volatility': 0.1, 'momentum': 0.05},
    #    1: {'volatility': 0.12, 'momentum': 0.03},
    #    ...
    # },
    # 'ETHUSDT': {
    #    0: {'volatility': 0.15,'momentum': 0.08},
    #    1: {'volatility': 0.14,'momentum': 0.06},
    #   ...
    # } 

#   # price_data format is like :
    # timestamp | BTCUSDT_open | BTCUSDT_high | BTCUSDT_low | ETHUSDT_open | ETHUSDT_high | ETHUSDT_low
    # previous data management has ensured all data is synched when multi symbol data is loaded


def run_multi_symbol_parameter_search(
    price_data: pd.DataFrame,  # DataFrame with timestamp index and symbol columns
    symbols: List[str],       # List of symbols to include in search
    indicators: Dict[str, Dict[int, Dict[str, float]]],  # Dict[symbol][timestamp][indicator_name] = value
    a_range: List[float] = None,
    k_range: List[float] = None,
    max_orders_range: List[int] = None,
    fee_rate: float = None,
    initial_cash: float = None
) -> pd.DataFrame:
    """Run grid search over market making parameters for multiple symbols
    
    Args:
        price_data: DataFrame with timestamp index and columns for each symbol's OHLC data
                   Expected format: timestamp index with columns like 'BTCUSDT_open', 'BTCUSDT_high', etc.
        symbols: List of symbols to include in parameter search
        indicators: Nested dict mapping symbol -> timestamp -> indicator_name -> value
        a_range: List of spread factor values to test
        k_range: List of mean reversion factor values to test
        max_orders_range: List of max orders per side values to test
        fee_rate: Trading fee rate
        initial_cash: Initial capital
        
    Returns:
        DataFrame containing results for each parameter combination
    """
    from strategies.strategy_factory import StrategyFactory
    factory = StrategyFactory()
    results = []
    
    # Use sequential integer timestamps
    timestamps = list(range(len(price_data)))
    
    # Prepare price dictionaries for each symbol
    symbol_data = {}
    for symbol in symbols:
        symbol_data[symbol] = {
            'prices': dict(zip(timestamps, price_data[f'{symbol}_open'])),
            'highs': dict(zip(timestamps, price_data[f'{symbol}_high'])),
            'lows': dict(zip(timestamps, price_data[f'{symbol}_low']))
        }
    
    # Generate all parameter combinations
    # Use default ranges if not provided
    a_range = a_range or [0.0005, 0.001, 0.002]
    k_range = k_range or [0.01, 0.02, 0.04]
    max_orders_range = max_orders_range or [3, 5, 7]
    fee_rate = fee_rate or DEFAULT_PARAMS['fee_rate']
    initial_cash = initial_cash or DEFAULT_PARAMS['initial_cash']
    
    param_combinations = itertools.product(
        a_range,
        k_range,
        max_orders_range
    )
    
    for a, k, max_orders in param_combinations:
        # Create base parameters
        base_params = {
            'a': a,
            'k': k,
            'max_orders': max_orders,
            'max_position': 100.0
        }
        
        # Create strategy instances for each symbol
        strategies = factory.create_strategies(
            strategy_class=StoikovStrategy,
            symbols=symbols,
            base_params=base_params
        )
        
        # Initialize simulation
        sim = MarketMakerSimulation(
            strategy=strategies[Symbol(symbols[0])],  # Use first strategy for initialization
            initial_cash=initial_cash,
            fee_rate=fee_rate
        )
        
        # Run simulation for all symbols
        total_pnl = 0
        total_trades = 0
        final_positions = {}
        daily_returns = []
        current_cash = initial_cash
        
        for symbol in symbols:
            results_dict = sim.run_simulation(
                symbol=symbol,
                timestamps=timestamps,
                prices=symbol_data[symbol]['prices'],
                highs=symbol_data[symbol]['highs'],
                lows=symbol_data[symbol]['lows'],
                indicators=indicators[symbol]
            )
            
            # Accumulate metrics
            positions = results_dict['positions']
            order_history = results_dict['order_history']
            
            # Get final position for this symbol
            position = positions.get(symbol)
            if position:
                total_pnl += position.realized_pnl
                final_positions[symbol] = position.size
            else:
                final_positions[symbol] = 0.0
                
            total_trades += len(order_history)
            
            # Calculate daily returns for this symbol
            if len(order_history) > 1:
                for order in order_history:
                    if order.status == 'FILLED':
                        if order.side == 'BUY':
                            current_cash -= order.quantity * order.price
                        else:
                            current_cash += order.quantity * order.price
                        daily_returns.append((current_cash - initial_cash) / initial_cash)
        
        # Calculate aggregate metrics
        total_pnl += current_cash - initial_cash
        returns = total_pnl / initial_cash
        
        # Calculate portfolio Sharpe ratio
        if daily_returns:
            sharpe = np.mean(daily_returns) / (np.std(daily_returns) + 1e-9) * np.sqrt(252)
        else:
            sharpe = 0.0
            
        # Store results
        result_dict = {
            'a': a,
            'k': k,
            'ticksize': ticksize,
            'max_orders': max_orders,
            'total_pnl': total_pnl,
            'sharpe_ratio': sharpe,
            'return': returns,
            'num_trades': total_trades
        }
        
        # Add final positions for each symbol
        for symbol, pos in final_positions.items():
            result_dict[f'{symbol}_final_pos'] = pos
            
        results.append(result_dict)
        
    # Convert to DataFrame and sort by combined score
    df = pd.DataFrame(results)
    
    # Score considers Sharpe ratio and penalizes high position risk across all symbols
    position_penalty = sum(df[f'{symbol}_final_pos'].abs() for symbol in symbols)
    df['score'] = df['sharpe_ratio'] - 2 * position_penalty / len(symbols)
    
    return df.sort_values('score', ascending=False)

# Example usage:
'''
Example price_data DataFrame format:

timestamp | BTCUSDT_open | BTCUSDT_high | BTCUSDT_low | ETHUSDT_open | ETHUSDT_high | ETHUSDT_low
1234567   | 50000.0      | 50100.0      | 49900.0     | 3000.0       | 3010.0       | 2990.0
1234568   | 50050.0      | 50150.0      | 49950.0     | 3005.0       | 3015.0       | 2995.0

Example indicators format:
indicators = {
    'BTCUSDT': {
        1234567: {'volatility': 0.1, 'momentum': 0.05},
        1234568: {'volatility': 0.12, 'momentum': 0.03}
    },
    'ETHUSDT': {
        1234567: {'volatility': 0.15, 'momentum': 0.08},
        1234568: {'volatility': 0.14, 'momentum': 0.06}
    }
}

results = run_multi_symbol_parameter_search(
    price_data=price_data,
    symbols=['BTCUSDT', 'ETHUSDT'],
    indicators=indicators,
    a_range=[0.0005, 0.001, 0.002],
    k_range=[0.01, 0.02, 0.03],
    max_position_range=[50.0, 100.0]
)

print(results.head())
'''
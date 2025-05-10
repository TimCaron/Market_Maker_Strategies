import numpy as np
import pandas as pd
from typing import Dict, Tuple
from market_maker import MarketMakerSimulation
from trading_strategies.stoikov_strategy import StoikovStrategy
from trading_strategies.Mexico_strategy import MexicoStrategy
from trading_strategies.Tokyo_strategy import TokyoStrategy
from risk_management_strategies.default_parameters import DefaultRiskParameters
from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
from constants import DEFAULT_PARAMS, Symbol
from trading_strategies.strategy_factory import StrategyFactory
from util_data import calculate_all_indicators
from simulation import execute_simulation
from simulation.results import process_results
from simulation.performance_metrics import calculate_sharpe_ratio, calculate_max_drawdown

def estimate_initial_parameters(price_data: pd.DataFrame, indicators: Dict, symbol: str, strategy_type: str, min_start:int) -> Dict:
    """Estimate initial parameters based on historical data analysis.
    
    Args:
        price_data: DataFrame with OHLC data
        indicators: Dictionary of technical indicators
        symbol: Trading symbol
        strategy_type: 'Stoikov' or 'Mexico'
        
    Returns:
        Dictionary of estimated parameters
    """
    # Calculate average price, volatility and spreads
    # fill nan with 0
    avg_price = price_data[f'{symbol}_close'].mean()
    avg_vol = np.mean([indicators[symbol][t]['volatility'] for t in indicators[symbol].keys()])
    avg_mom = np.mean([indicators[symbol][t]['momentum'] for t in indicators[symbol].keys()])
    avg_sma_dev = np.mean([indicators[symbol][t]['sma_deviation'] for t in indicators[symbol].keys()])
    
    # Calculate mean relative spread from high/low prices
    high_spread = (price_data[f'{symbol}_high'] - price_data[f'{symbol}_close']) / price_data[f'{symbol}_close']
    low_spread = (price_data[f'{symbol}_close'] - price_data[f'{symbol}_low']) / price_data[f'{symbol}_close']
    avg_spread = (high_spread.mean() + low_spread.mean()) / 2
    
    # tailor factors like alpha*vol such that alpha*mean(vol) = 0.1
    # Estimate Mexico parameters to achieve ~0.1 impact for each component #todo
    mean_revert_factor = 0.1 / (abs(avg_sma_dev) + 1e-6)
    momentum_factor = 0.1 / (abs(avg_mom) + 1e-6)
    vol_factor = 0.1 / (avg_vol + 1e-6)

    # in stoikov todo
    risk_aversion = 0.001 * avg_price / (avg_vol + 1e-6)
    gamma_spread = 0.001 * avg_price / (avg_vol + 1e-6)
    
    # max_orders
    max_orders = 1
    # typical spread
    minimal_spread = max(avg_spread, 2 * DEFAULT_PARAMS['maker_fee'])
        
    if strategy_type == 'Stoikov':
        return {
            'risk_aversion': risk_aversion,
            'gamma_spread': gamma_spread
        }
    elif strategy_type == 'Tokyo':
        return {
            'minimal_spread': minimal_spread,
            'max_orders': max_orders
        }
    elif strategy_type == 'Mexico':
        return {
            'q_factor': 0.1,
            'upnl_factor': 0.1,
            'mean_revert_factor': mean_revert_factor,
            'momentum_factor': momentum_factor,
            'vol_factor': vol_factor
        }
    else:
        raise ValueError(f"Unsupported strategy type: {strategy_type}")


def run_parameter_search(
    price_data: pd.DataFrame,
    symbol_data: Dict[str, pd.DataFrame],
    symbol: str,
    strategy_name: str,
    indicators: Dict,
    min_start: int,
    n_grid_points: int = 10
) -> Tuple[Dict, DefaultRiskParameters, pd.DataFrame]:
    """Run grid search for strategy and risk parameters.
    
    Args:
        price_data: DataFrame with OHLC data
        symbol: Trading symbol
        strategy_type: 'Stoikov' or 'Mexico' or 'Tokyo', ...
        indicators: Dictionary of technical indicators
        n_grid_points: Number of points per dimension in grid search
        
    Returns:
        Tuple of (best strategy parameters, best risk parameters, results DataFrame)
    """
    # Get initial parameter estimates
    init_params = estimate_initial_parameters(price_data, indicators, symbol, strategy_name, min_start)
    # Create parameter grid
    param_grid = []
    param_names = []
    
    if strategy_name == 'Stoikov':
        param_names = ['risk_aversion', 'gamma_spread']
        for param in param_names:
            base_val = init_params[param]
            param_grid.append(np.logspace(np.log10(base_val/10), np.log10(base_val*10), n_grid_points))
            
    elif strategy_name == 'Tokyo':
        param_names = ['minimal_spread', 'max_orders']
        for param in param_names:
            base_val = init_params[param]
            if param == 'minimal_spread':
                # Spread should not go below maker fee
                min_val = DEFAULT_PARAMS['maker_fee'] * 2
                param_grid.append(np.logspace(np.log10(base_val/10), np.log10(base_val*10), n_grid_points))
            elif param =='max_orders':
                param_grid.append([1 + i for i in range(n_grid_points)])
            else:
                param_grid.append(np.logspace(np.log10(base_val/5), np.log10(base_val*5), n_grid_points))

    elif strategy_name == 'Mexico':
        param_names = ['q_factor', 'upnl_factor', 'mean_revert_factor', 'momentum_factor', 'vol_factor']
        for param in param_names:
            base_val = init_params[param]
            param_grid.append(np.logspace(np.log10(base_val/10), np.log10(base_val*10), n_grid_points))
    
    # Risk parameter grid -> no grid just set default risk:
    risk_params = DefaultRiskParameters()
    risk_strategy = BasicRiskStrategy(risk_params)

    # Initialize results storage
    all_results = []  # List to store simulation results for each parameter combination
    factory = StrategyFactory()
    # Run grid search
    for params in np.array(np.meshgrid(*param_grid)).T.reshape(-1, len(param_grid)):
        print('running simulation on parameters: ', params)
        strategy_instances = {}

        # Create parameter dictionaries
        strategy_params = init_params.copy()
        for i, param in enumerate(param_names):
            strategy_params[param] = params[i]

        strategy_class = {
            'Mexico': MexicoStrategy,
            'Stoikov': StoikovStrategy,
            'Tokyo': TokyoStrategy
        }.get(strategy_name)
        if not strategy_class:
            raise NotImplementedError(f"Not implemented strategy: {strategy_name}")
        
        symbol_strategies = factory.add_strategy(
            strategy_class=strategy_class,
            symbols=[symbol],
            base_params=strategy_params
        )
      
        strategy_instances.update(symbol_strategies)
        # Use strategy_instances directly since it already has Symbol enum keys
        strategy_dict = strategy_instances
        
        indicators = calculate_all_indicators(symbol_data, strategy_dict)
        
        # Execute simulation
        results = execute_simulation(
            symbols=[symbol],
            strategy_instances=strategy_instances,
            verbosity=0,
            risk_strategy=risk_strategy,
            price_data=price_data,
            indicators=indicators
        )

        # Process results using the process_results function
        # Convert strategy object to parameter dictionary for visualization
        strategy_params_dict = {symbol: {strategy_name: strategy_params}}
        process_results(results, [symbol], strategy_params_dict, risk_params.__dict__)
        
        # Calculate metrics for parameter search
        wallet_history = results['wallet_balance_history']
        returns = [(wallet_history[i] - wallet_history[i-1]) / wallet_history[i-1] if wallet_history[i-1] != 0 else 0
                  for i in range(1, len(wallet_history))]
       
        sharpe = calculate_sharpe_ratio(returns)
        max_drawdown = calculate_max_drawdown(wallet_history)
        
        # Calculate total PnL
        total_pnl = 0.0
        for symbol_str in [symbol]:
            if symbol_str in results['positions']:
                pos = results['positions'][symbol_str]
                total_pnl += pos.total_realized_pnl + pos.unrealized_pnl
        
        # Calculate average spread
        spread_history = results['spread_history']
        if spread_history:
            # Flatten the nested lists and calculate average
            all_spreads = [spread for spreads in spread_history.values() for spread in (spreads if isinstance(spreads, list) else [spreads])]
            avg_spread = sum(all_spreads) / len(all_spreads) if all_spreads else 0
        else:
            avg_spread = 0
        
        # Calculate win rate from realized PnL history
        realized_pnl_history = results['realized_pnl_history']
        # Flatten the nested PnL lists and count winning trades
        win_trades = 0
        total_trades = 0
        for pnl_list in realized_pnl_history.values():
            if isinstance(pnl_list, list):
                win_trades += sum(1 for pnl in pnl_list if pnl > 0)
                total_trades += len(pnl_list)
            else:
                win_trades += 1 if pnl_list > 0 else 0
                total_trades += 1
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        print(f'results: sharpe {sharpe}, max_drawdown {max_drawdown}, totalpnl {total_pnl}')
        # Store results for this parameter combination
        result = {
            'pnl': total_pnl,
            'sharpe': sharpe,
            'max_drawdown': max_drawdown,
            'avg_spread': avg_spread,
            'win_rate': win_rate,
            **{f'strategy_{p}': v for p, v in strategy_params.items()},
            **{f'risk_{p}': v for p, v in risk_params.__dict__.items()}
        }
        all_results.append(result)  # Append result dictionary to results list

    
    # Convert to DataFrame and find best parameters
    results_df = pd.DataFrame(all_results)
    results_df['score'] = results_df['sharpe'] * (1 - results_df['max_drawdown'])
    best_row = results_df.loc[results_df['score'].idxmax()]
    
    # Extract best parameters
    best_strategy_params = {}
    best_risk_params = {}
    for col in results_df.columns:
        if col.startswith('strategy_'):
            param = col.replace('strategy_', '')
            best_strategy_params[param] = best_row[col]
        elif col.startswith('risk_'):
            param = col.replace('risk_', '')
            best_risk_params[param] = best_row[col]
    
    return best_strategy_params, DefaultRiskParameters(**best_risk_params), results_df
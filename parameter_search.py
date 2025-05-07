import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from market_maker import MarketMakerSimulation
from trading_strategies.stoikov_strategy import StoikovStrategy
from trading_strategies.Mexico_strategy import MexicoStrategy
from risk_management_strategies.base_risk_strategy import RiskStrategyParameters
from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
from constants import DEFAULT_PARAMS, Symbol
from trading_strategies.strategy_factory import StrategyFactory
from util_data import calculate_all_indicators

def estimate_initial_parameters(price_data: pd.DataFrame, indicators: Dict, symbol: str, strategy_type: str) -> Dict:
    """Estimate initial parameters based on historical data analysis.
    
    Args:
        price_data: DataFrame with OHLC data
        indicators: Dictionary of technical indicators
        symbol: Trading symbol
        strategy_type: 'Stoikov' or 'Mexico'
        
    Returns:
        Dictionary of estimated parameters
    """
    # Calculate average price and volatility
    avg_price = price_data[f'{symbol}_close'].mean()
    avg_vol = np.mean([indicators[symbol][t]['volatility'] for t in indicators[symbol].keys()])
    avg_mom = np.mean([indicators[symbol][t]['momentum'] for t in indicators[symbol].keys()])
    avg_sma_dev = np.mean([indicators[symbol][t]['sma_deviation'] for t in indicators[symbol].keys()])
    
    if strategy_type == 'Stoikov':
        # Estimate Stoikov parameters
        # risk_aversion: aim for price impact of ~0.1% of price
        risk_aversion = 0.001 * avg_price / (avg_vol + 1e-6)
        # gamma_spread: target spread of ~0.1% of price
        gamma_spread = 0.001 * avg_price / (avg_vol + 1e-6)
        
        return {
            'risk_aversion': risk_aversion,
            'gamma_spread': gamma_spread,
            'window_vol': 7  # Keep default window
        }
        
    elif strategy_type == 'Mexico':
        # Estimate Mexico parameters to achieve ~0.1 impact for each component
        q_factor = 0.1 / (avg_vol + 1e-6)
        upnl_factor = 0.1 / (avg_vol + 1e-6)
        mean_revert_factor = 0.1 / (abs(avg_sma_dev) + 1e-6)
        momentum_factor = 0.1 / (abs(avg_mom) + 1e-6)
        vol_factor = 0.1 / (avg_vol + 1e-6)
        
        return {
            'q_factor': q_factor,
            'upnl_factor': upnl_factor, 
            'mean_revert_factor': mean_revert_factor,
            'momentum_factor': momentum_factor,
            'constant_spread': 0.001,  # Base 0.1% spread
            'vol_factor': vol_factor,
            'spread_mom_factor': 0.1,
            'max_orders': 5,
            'window_vol': 7,
            'window_sma': 7,
            'window_mom': 7,
            'window_high_low': 3,
            'use_adaptive_sizes': True
        }

def estimate_risk_parameters(price_data: pd.DataFrame, symbol: str) -> RiskStrategyParameters:
    """Estimate initial risk parameters based on historical data."""
    avg_price = price_data[f'{symbol}_close'].mean()
    daily_vol = price_data[f'{symbol}_close'].pct_change().std()
    
    # Conservative initial estimates
    return RiskStrategyParameters(
        max_leverage=3.0,  # Conservative leverage
        min_order_value_usd=100,  # Minimum viable order
        aggressivity=0.5,  # Moderate aggressivity
        emergency_exit_leverage=2.7,  # 90% of max leverage
        early_stopping_margin=0.2,  # 20% drawdown limit
        cancel_orders_every_timestamp=True,
        max_order_age=None
    )

def run_parameter_search(
    price_data: pd.DataFrame,
    symbol: str,
    strategy_type: str,
    indicators: Dict,
    n_grid_points: int = 5
) -> Tuple[Dict, RiskStrategyParameters, pd.DataFrame]:
    """Run grid search for strategy and risk parameters.
    
    Args:
        price_data: DataFrame with OHLC data
        symbol: Trading symbol
        strategy_type: 'Stoikov' or 'Mexico'
        indicators: Dictionary of technical indicators
        n_grid_points: Number of points per dimension in grid search
        
    Returns:
        Tuple of (best strategy parameters, best risk parameters, results DataFrame)
    """
    # Get initial parameter estimates
    init_params = estimate_initial_parameters(price_data, indicators, symbol, strategy_type)
    init_risk_params = estimate_risk_parameters(price_data, symbol)
    
    # Create parameter grid
    param_grid = []
    param_names = []
    
    if strategy_type == 'Stoikov':
        param_names = ['risk_aversion', 'gamma_spread']
        for param in param_names:
            base_val = init_params[param]
            param_grid.append(np.logspace(np.log10(base_val/10), np.log10(base_val*10), n_grid_points))
            
    elif strategy_type == 'Mexico':
        param_names = ['q_factor', 'upnl_factor', 'mean_revert_factor', 'momentum_factor', 'vol_factor']
        for param in param_names:
            base_val = init_params[param]
            param_grid.append(np.logspace(np.log10(base_val/10), np.log10(base_val*10), n_grid_points))
    
    # Risk parameter grid
    risk_param_names = ['max_leverage', 'aggressivity']
    risk_param_grid = []
    for param in risk_param_names:
        base_val = getattr(init_risk_params, param)
        risk_param_grid.append(np.linspace(base_val*0.5, base_val*1.5, n_grid_points))
    
    # Initialize results storage
    results = []
    factory = StrategyFactory()
    
    # Run grid search
    for params in np.array(np.meshgrid(*param_grid)).T.reshape(-1, len(param_grid)):
        for risk_params in np.array(np.meshgrid(*risk_param_grid)).T.reshape(-1, len(risk_param_grid)):
            # Create parameter dictionaries
            strategy_params = init_params.copy()
            for i, param in enumerate(param_names):
                strategy_params[param] = params[i]
                
            risk_params_dict = init_risk_params.__dict__.copy()
            for i, param in enumerate(risk_param_names):
                risk_params_dict[param] = risk_params[i]
            
            # Create strategies
            strategy_config = {symbol: {strategy_type: strategy_params}}
            strategy_class = StoikovStrategy if strategy_type == 'Stoikov' else MexicoStrategy
            strategy_instances = factory.add_strategy(
                strategy_class=strategy_class,
                symbols=[symbol],
                base_params=strategy_params
            )
            
            # Create risk strategy
            risk_strategy = BasicRiskStrategy(RiskStrategyParameters(**risk_params_dict))
            
            # Run simulation
            sim = MarketMakerSimulation(
                strategies=strategy_instances,
                initial_cash=DEFAULT_PARAMS['initial_cash'],
                maker_fee=DEFAULT_PARAMS['maker_fee'],
                taker_fee=DEFAULT_PARAMS['taker_fee'],
                min_start=0,
                verbosity=0,
                risk_strategy=risk_strategy
            )
            
            # Prepare data for simulation
            timestamps = list(range(len(price_data)))
            prices = {symbol: dict(zip(timestamps, price_data[f'{symbol}_open']))}
            highs = {symbol: dict(zip(timestamps, price_data[f'{symbol}_high']))}
            lows = {symbol: dict(zip(timestamps, price_data[f'{symbol}_low']))}
            closes = {symbol: dict(zip(timestamps, price_data[f'{symbol}_close']))}
            
            # Run simulation
            sim_results = sim.run_simulation(
                timestamps=timestamps,
                prices=prices,
                highs=highs,
                lows=lows,
                closes=closes,
                indicators=indicators
            )
            
            # Calculate metrics
            pnl = sim_results['total_pnl']
            sharpe = sim_results.get('sharpe_ratio', 0)
            max_drawdown = sim_results.get('max_drawdown', 0)
            
            # Store results
            result = {
                'pnl': pnl,
                'sharpe': sharpe,
                'max_drawdown': max_drawdown,
                **{f'strategy_{p}': v for p, v in strategy_params.items()},
                **{f'risk_{p}': v for p, v in risk_params_dict.items()}
            }
            results.append(result)
    
    # Convert to DataFrame and find best parameters
    results_df = pd.DataFrame(results)
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
    
    return best_strategy_params, RiskStrategyParameters(**best_risk_params), results_df
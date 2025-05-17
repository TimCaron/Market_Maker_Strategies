import os
import pandas as pd
from typing import Dict, List
from util_data import load_symbol_data, prepare_price_data, calculate_all_indicators
from trading_strategies.stoikov_strategy import StoikovStrategy
from trading_strategies.Mexico_strategy import MexicoStrategy
from constants import DEFAULT_PARAMS
from trading_strategies.strategy_factory import StrategyFactory
from risk_management_strategies.base_risk_strategy import BaseRiskStrategy
from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
from risk_management_strategies.default_parameters import DefaultRiskParameters
from simulation.executor import execute_simulation
from simulation.results import process_results
from trading_strategies.default_parameters import StoikovParameters, MexicoParameters, TokyoParameters, DefaultParameters
from trading_strategies.Tokyo_strategy import TokyoStrategy, TokyoParameters
from parameter_search import run_parameter_search
from simulation.executor import get_starting_timestamp


def instantiate_strategies(trading_strategies: Dict[str, Dict[str, DefaultParameters]], symbols: List[str]) -> Dict:
    """
    Instantiate trading strategies based on the provided configurations.

    Args:
        trading_strategies: Dictionary symbol -> strategy_name -> parameters
        symbols: List of symbols to trade

    Returns:    
        Dict: Dictionary of instantiated trading strategies
    """
     # Initialize strategy factory and create strategy instances
    factory = StrategyFactory()
    strategy_instances = {}
    print('la', trading_strategies)
    # Create strategy instances for each symbol
    for symbol in symbols:
        symbol_config = trading_strategies[symbol]
        strategy_name = list(symbol_config.keys())[0]
        strategy_params = symbol_config[strategy_name]
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

    return strategy_instances

def validate_args(period: str, trading_strategies: Dict[str, Dict[str, DefaultParameters]], risk_strategy: BaseRiskStrategy, mode: str, symbols: List[str], verbosity: int):
    """
    Validate the arguments passed to the main function.

    Args:
        period: Time period for data ('1d' or minutes), see constants.py
        trading_strategies: Dictionary of trading strategies : symbol -> strategy_name -> parameters
        risk_strategy: Risk management strategy instance
        mode: 'parameter_search' or'single_run'
        symbols: List of symbols to trade
        verbosity: Logging level (0=ERROR, 1=INFO, 2=DEBUG)
    """
    data_dir = 'data'
    assert os.path.exists(data_dir), f"Data directory '{data_dir}' not found!"
    assert mode in ['parameter_search', 'single_run'], f"Invalid mode: {mode}"
    assert type(period) == str, f"Invalid period type: {type(period)}"
    assert period in DEFAULT_PARAMS['valid_periods'], f"Invalid period: {period}"
    assert verbosity in [0,1,2], f"Invalid verbosity level: {verbosity}"
    assert len(symbols) == len(trading_strategies), f"Number of symbols and strategies must be the same"
    for symbol in symbols:
        assert symbol in trading_strategies, f"No strategy configuration found for symbol {symbol}"
    # Check if all trading strategies are implemented
    for symbol in symbols:
        strategy_name = list(trading_strategies[symbol].keys())[0]
        assert strategy_name in ['Stoikov', 'Mexico', 'Tokyo'], f"Not implemented strategy: {strategy_name}"

    # Check if risk strategy is implemented
    assert isinstance(risk_strategy, BaseRiskStrategy), f"Invalid risk strategy type: {type(risk_strategy)}"
    assert risk_strategy.__class__.__name__ in ['BasicRiskStrategy', 'BasicRiskStrategy'], f"Not implemented risk strategy: {risk_strategy.__class__.__name__}"


def display_parameter_search_results(symbol: str, strategy_name: str, period: str, best_strategy_params: Dict, best_risk_params: DefaultRiskParameters, results_df: pd.DataFrame):
    """Display the results of parameter search including best parameters and top combinations.
    
    Args:
        symbol: Trading symbol
        strategy_name: Name of the strategy
        period: Time period used
        best_strategy_params: Best strategy parameters found
        best_risk_params: Best risk parameters found
        results_df: DataFrame containing all parameter combinations and their scores
    """
    print(f"Running parameter search for {strategy_name} strategy on {symbol} with period {period}")
    
    print("\nBest Strategy Parameters:")
    for param, value in best_strategy_params.items():
        print(f"{param}: {value:.6f}" if isinstance(value, float) else f"{param}: {value}")
        
    print("\nBest Risk Parameters:")
    for param, value in best_risk_params.__dict__.items():
        print(f"{param}: {value:.6f}" if isinstance(value, float) else f"{param}: {value}")
        
    print("\nTop 5 Parameter Combinations by Score:")
    print(results_df.sort_values('score', ascending=False).head())

def main(period: str, trading_strategies: Dict[str, Dict[str, DefaultParameters]] , risk_strategy: BaseRiskStrategy, mode: str, symbols: List[str], verbosity = 2):
    """Main entry point for market making simulation
    
    Args:
        period: Time period for data ('1d' or minutes), see constants.py
        trading_strategies: Dictionary of trading strategies : symbol -> strategy_name -> parameters
        risk_strategy: Risk management strategy instance
        mode: 'parameter_search' or 'single_run'
        symbols: List of symbols to trade
        verbosity: Logging level (0=ERROR, 1=INFO, 2=DEBUG)
    """
    # Validate arguments
    validate_args(period, trading_strategies, risk_strategy, mode, symbols, verbosity)
    data_dir = 'data'

    if mode == 'parameter_search':
        assert len(symbols) == 1, "Parameter search can only be executed for one symbol at a time"
        symbol = symbols[0]
        strategy_name = list(trading_strategies[symbol].keys())[0]
        
        # Load and prepare data
        symbol_data = load_symbol_data(data_dir, period, symbols, revert=True)
        price_data = prepare_price_data(symbol_data)
        
        # Calculate initial indicators
        strategy_instances = instantiate_strategies({symbol:{'Mexico':MexicoParameters()}}, symbols)
        # we need a general strategy to calculate indicators, lets take the most general one
        indicators = calculate_all_indicators(symbol_data, strategy_instances)
        min_start = get_starting_timestamp(strategy_instances)
        
        # Run parameter search
        best_strategy_params, best_risk_params, results_df = run_parameter_search(
            price_data=price_data,
            symbol_data=symbol_data,
            symbol=symbol,
            strategy_name=strategy_name,
            indicators=indicators,
            min_start=min_start,
            n_grid_points=5
        )
        
        # Display results
        display_parameter_search_results(symbol, strategy_name, period, best_strategy_params, best_risk_params, results_df)
        
        # Update strategies with best parameters
        trading_strategies[symbol][strategy_type] = best_strategy_params
        risk_strategy = BasicRiskStrategy(best_risk_params)
        
        return trading_strategies, risk_strategy

    if mode == 'single_run':
        print(f"Running single run for symbols {symbols} with period {period}")
     
        # Load and prepare data
        symbol_data = load_symbol_data(data_dir, period, symbols, revert=True)
        price_data = prepare_price_data(symbol_data)
        
        # Instantiate strategies
        strategy_instances = instantiate_strategies(trading_strategies, symbols)

        # Calculate indicators
        indicators = calculate_all_indicators(symbol_data, strategy_instances)
        
        # Execute simulation
        results = execute_simulation(
            symbols=symbols,
            strategy_instances=strategy_instances,
            verbosity=verbosity,
            risk_strategy=risk_strategy,
            price_data=price_data,
            indicators=indicators
        )
        
        # Process and display results with both text and plots enabled
        process_results(results, symbols, trading_strategies, risk_strategy.parameters.__dict__, display_text=True, display_img=True)

    elif mode != 'single_run':
        raise ValueError(f"Invalid mode: {mode}. Must be 'parameter_search' or 'single_run'")
    
    return trading_strategies, risk_strategy

    
if __name__ == '__main__':
    # Example configuration
    period = '1d'
    mode = 'parameter_search' # la {'BTCUSDT': {'Mexico': MexicoParameters(max_orders=1, minimal_spread=0.0008, use_adaptive_sizes=False, window_vol=7, window_sma=7, window_mom=7, window_high_low=3, q_factor=0.1, upnl_factor=0.05, mean_revert_factor=0.2, momentum_factor=0.1, constant_spread=0.005, vol_factor=0.1, spread_mom_factor=0.05)}}
    mode = 'single_run'
    # Example usage :
    # This will use default parameters from DefaultParameters class
    btc_stoikov_params = StoikovParameters()
    eth_stoikov_params = StoikovParameters()
    # Override parameters if needed with commands like:
    # btc_stoikov_params.max_orders = 5
    # To see default parameters:
    # print(btc_stoikov_params.__dict__)
    # To change them directly, go to trading_strategies/default_parameters.py and edit the class
    #q_factor: 0.100000
    #upnl_factor: -0.100000
    #mean_revert_factor: -0.279895
    #momentum_factor: 0.281831
    #vol_factor: 0.677907

    btc_mexico_params = MexicoParameters()
    best_params = {'q_factor':0.01 , 'upnl_factor': 0.1, 'mean_revert_factor':  0.5597, 'momentum_factor': -0.1409, 'vol_factor':0.677907}
    for k,v in best_params.items():
        setattr(btc_mexico_params, k, v)
    # most likely very much overfitted
    eth_mexico_params = MexicoParameters()
    for k,v in best_params.items():
        setattr(eth_mexico_params, k, v)
    btc_tokyo_params = TokyoParameters()
    eth_tokyo_params = TokyoParameters()

    # Configure symbols and strategies ; example call
    mono_symbol = 0
    if mode == 'parameter_search':
        assert mono_symbol == True, "Parameter search can only be executed for one symbol at a time"
    
    strategy = 'Mexico'
    if strategy == 'Stoikov':
        if mono_symbol:
            symbols = ['BTCUSDT']
            trading_strategies = {'BTCUSDT': {'Stoikov': btc_stoikov_params}}
        else:
            symbols = ['BTCUSDT', 'ETHUSDT']
            trading_strategies = {
                'BTCUSDT': {'Stoikov': btc_stoikov_params},
                'ETHUSDT': {'Stoikov': eth_stoikov_params}      
            }
    elif strategy == 'Mixed':
        symbols = ['BTCUSDT', 'ETHUSDT']
        trading_strategies = {
            'BTCUSDT': {'Stoikov': btc_mexico_params},
            'ETHUSDT': {'Tokyo': eth_tokyo_params}
        }
    elif strategy == 'Mexico':
        if mono_symbol:
            symbols = ['BTCUSDT']
            trading_strategies = {'BTCUSDT': {'Mexico': btc_mexico_params}}
        else:
            symbols = ['BTCUSDT', 'ETHUSDT']
            trading_strategies = {
                'BTCUSDT': {'Mexico': btc_mexico_params},
                'ETHUSDT': {'Mexico': eth_mexico_params}
            }
    elif strategy == 'Tokyo':
        if mono_symbol:
            symbols = ['BTCUSDT']
            trading_strategies = {'BTCUSDT': {'Tokyo': btc_tokyo_params}}
        else:
            symbols = ['BTCUSDT', 'ETHUSDT']
            trading_strategies = {
                'BTCUSDT': {'Tokyo': btc_tokyo_params},
                'ETHUSDT': {'Tokyo': eth_tokyo_params}
            }
    else:
        raise ValueError(f"Invalid strategy: {strategy}. Must be 'Stoikov', 'Mexico' or 'Tokyo'")
        
    # Initialize risk management strategy
    risk_params = DefaultRiskParameters()
    risk_strategy = BasicRiskStrategy(risk_params)

    # Run simulation
    trading_strategies, risk_strategy = main(period, trading_strategies, risk_strategy, mode, symbols, verbosity=0)
  
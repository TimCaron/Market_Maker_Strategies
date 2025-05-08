import os
from typing import Dict, List
from util_data import load_symbol_data, prepare_price_data, calculate_all_indicators
from trading_strategies.stoikov_strategy import StoikovStrategy
from trading_strategies.Mexico_strategy import MexicoStrategy
from constants import DEFAULT_PARAMS
from trading_strategies.strategy_factory import StrategyFactory
from risk_management_strategies.base_risk_strategy import RiskStrategyParameters, BaseRiskStrategy
from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
from simulation.executor import execute_simulation
from simulation.results import process_results
from trading_strategies.default_parameters import StoikovParameters, MexicoParameters, TokyoParameters
from trading_strategies.Tokyo_strategy import TokyoStrategy, TokyoParameters


def main(period: str, trading_strategies: Dict, risk_strategy: BaseRiskStrategy, mode: str, symbols: List[str], verbosity = 2):
    """Main entry point for market making simulation
    
    Args:
        period: Time period for data ('1d' or minutes)
        trading_strategies: Dictionary mapping symbols to their strategy configurations
        risk_strategy: Optional risk management strategy instance
        mode: 'parameter_search' or 'single_run'
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
    
    if mode == 'parameter_search':
        assert len(symbols) == 1, "Parameter search can only be executed for one symbol at a time"
        symbol = symbols[0]
        strategy_type = list(trading_strategies[symbol].keys())[0]
        print(f"Running parameter search for {strategy_type} strategy on {symbol} with period {period}")
        
        # Load and prepare data
        symbol_data = load_symbol_data(data_dir, period, symbols, revert=True)
        price_data = prepare_price_data(symbol_data)
        
        # Calculate initial indicators
        indicators = calculate_all_indicators(symbol_data)
        
        # Run parameter search
        from parameter_search import run_parameter_search
        best_strategy_params, best_risk_params, results_df = run_parameter_search(
            price_data=price_data,
            symbol=symbol,
            strategy_type=strategy_type,
            indicators=indicators,
            n_grid_points=5
        )
        
        print("\nBest Strategy Parameters:")
        for param, value in best_strategy_params.items():
            print(f"{param}: {value}")
            
        print("\nBest Risk Parameters:")
        for param, value in best_risk_params.__dict__.items():
            print(f"{param}: {value}")
            
        print("\nTop 5 Parameter Combinations by Score:")
        print(results_df.sort_values('score', ascending=False).head())
        
        # Update strategies with best parameters
        trading_strategies[symbol][strategy_type] = best_strategy_params
        risk_strategy = BasicRiskStrategy(best_risk_params)

    if mode == 'single_run':
        print(f"Running single run for symbols {symbols} with period {period}")
        
        # Load and prepare data
        symbol_data = load_symbol_data(data_dir, period, symbols, revert=True)
        price_data = prepare_price_data(symbol_data)

        # Initialize strategy factory and create strategy instances
        factory = StrategyFactory()
        strategy_instances = {}
        
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
        
        # Calculate indicators
        strategy_dict = {}
        for symbol_str in symbols:
            for symbol_enum, strategy in strategy_instances.items():
                if symbol_enum.value == symbol_str:
                    strategy_dict[symbol_str] = strategy
                    break
        
        indicators = calculate_all_indicators(symbol_data, strategy_dict)
        
        # Execute simulation
        results = execute_simulation(
            symbols=symbols,
            strategy_instances=strategy_instances,
            verbosity=verbosity,
            risk_strategy=risk_strategy,
            price_data=price_data,
            indicators=indicators
        )
        
        # Process and display results
        process_results(results, symbols, trading_strategies, risk_strategy.parameters.__dict__)

    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'single_run'")


if __name__ == '__main__':
    # Configuration
    period = '1d'
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
    
    btc_mexico_params = MexicoParameters()
    eth_mexico_params = MexicoParameters()
    btc_tokyo_params = TokyoParameters()
    eth_tokyo_params = TokyoParameters()
    btc_stoikov_params = StoikovParameters()
    eth_stoikov_params = StoikovParameters()

    # Configure symbols and strategies ; example call
    mono_symbol = False
    strat = 'Stoikov'

    if strat == 'Stoikov':
        if mono_symbol:
            symbols = ['BTCUSDT']
            trading_strategies = {'BTCUSDT': {'Stoikov': btc_stoikov_params}}
        else:
            symbols = ['BTCUSDT', 'ETHUSDT']
            trading_strategies = {
                'BTCUSDT': {'Stoikov': btc_stoikov_params},
                'ETHUSDT': {'Stoikov': eth_stoikov_params}      
            }
    elif strat == 'Mixed':
        symbols = ['BTCUSDT', 'ETHUSDT']
        trading_strategies = {
            'BTCUSDT': {'Stoikov': btc_mexico_params},
            'ETHUSDT': {'Tokyo': eth_tokyo_params}
        }
    elif strat == 'Mexico':
        if mono_symbol:
            symbols = ['BTCUSDT']
            trading_strategies = {'BTCUSDT': {'Mexico': btc_params}}
        else:
            symbols = ['BTCUSDT', 'ETHUSDT']
            trading_strategies = {
                'BTCUSDT': {'Mexico': btc_params},
                'ETHUSDT': {'Mexico': eth_params}
            }

    # Initialize risk management strategy
    risk_params = RiskStrategyParameters(
        max_leverage=DEFAULT_PARAMS['max_leverage'],
        min_order_value_usd=DEFAULT_PARAMS['min_order_value_usd'],
        aggressivity=DEFAULT_PARAMS['aggressivity'],
        emergency_exit_leverage=DEFAULT_PARAMS['emergency_exit_leverage'],
        early_stopping_margin=DEFAULT_PARAMS['early_stopping_margin'],
        cancel_orders_every_timestamp=True,  # Cancel orders at each new timestamp
        max_order_age=None  # No maximum age limit
    )
    risk_strategy = BasicRiskStrategy(risk_params)

    # Run simulation
    main(period, trading_strategies, risk_strategy, mode, symbols, verbosity=2)
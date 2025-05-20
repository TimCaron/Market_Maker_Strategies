import pandas as pd
from util_data import load_symbol_data, prepare_price_data, calculate_all_indicators
from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
from risk_management_strategies.default_parameters import DefaultRiskParameters
from simulation.executor import execute_simulation
from simulation.results import process_results
from trading_strategies.default_parameters import StoikovParameters
from main import validate_args, instantiate_strategies

if __name__ == '__main__':

    period = '1d'
    mode = 'single_run' #single_run, parameter_search, backtest
    symbols = ['BROWNIANUSDT']    
    verbosity = 0
    # Load data to get actual size
    df = pd.read_csv('data/BROWNIANUSDT/1d/data.csv')
    n_candles = len(df)
    
    # Time parameters matching the Brownian motion generation
    T = 10.0  # Total time horizon (from Brownian generation) 
    dt = T / n_candles  # Time step size adjusted to actual data size
    
    print(f"Data size: {n_candles} candles")
    print(f"Time parameters: T={T}, dt={dt}")
    
    vanilla_stoikov_params = StoikovParameters()
    # Set time parameters
    vanilla_stoikov_params.T = T
    vanilla_stoikov_params.dt = dt
    
    # print these params
    print('Vanilla Stoikov params:', vanilla_stoikov_params)

    strategy = 'VanillaStoikov'
    trading_strategies = {'BROWNIANUSDT': {'VanillaStoikov': vanilla_stoikov_params}}
        
    # Initialize risk management strategy
    risk_params = DefaultRiskParameters()
    risk_strategy = BasicRiskStrategy(risk_params)

    validate_args(period, trading_strategies, risk_strategy, mode, symbols, verbosity)
    data_dir = 'data'
    # Run simulation
    # Load and prepare data
    symbol_data = load_symbol_data(data_dir, period, symbols, revert=True)
    price_data = prepare_price_data(symbol_data)
    
    # Instantiate strategies
    strategy_instances = instantiate_strategies(trading_strategies, symbols)

    # Calculate indicators
    indicators = calculate_all_indicators(symbol_data, strategy_instances)
    # retrieve volatility from indicators
    volatility = indicators['BROWNIANUSDT']['volatility']
    print('volatility:', volatility)
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

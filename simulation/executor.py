"""
Module for handling simulation execution logic.
"""
from typing import List, Dict
from market_maker import MarketMakerSimulation
from constants import DEFAULT_PARAMS, Symbol
from risk_management_strategies.base_risk_strategy import BaseRiskStrategy
from trading_strategies.base_strategy import BaseStrategy


def get_starting_timestamp(strategy_dict: Dict) -> int:
    """
    Calculate the minimum starting timestamp based on strategy parameters, 
    as the maximal window len + 1 used in all indicators
    since indicators are Nan s when they cannot yet be computed
    Args:
        strategy_dict: Dictionary of strategies with their parameters
        
    Returns:
        int: Minimum starting timestamp
    """
    # later todo : have a constant list of indicators and associated window_len dictionnary
    print('check', strategy_dict)
    min_start = 0
    for _, strategy in strategy_dict.items():
        strategy_params = strategy.parameters
        window_vol = getattr(strategy_params, 'window_vol', 0)
        window_sma = getattr(strategy_params, 'window_sma', 0)
        window_mom = getattr(strategy_params, 'window_mom', 0)
        window_high_low = getattr(strategy_params, 'window_high_low', 0)
       
        min_start = max(min_start, window_sma, window_vol, window_mom, window_high_low+1)
    return min_start

def execute_simulation(
    symbols: List[str],
    strategy_instances: Dict[Symbol, BaseStrategy],
    verbosity: int,
    risk_strategy: BaseRiskStrategy,
    price_data: Dict,
    indicators: Dict
) -> Dict:
    """
    Execute a single simulation run for multiple symbols simultaneously on a given timeframe.
    Multiple timeframes not supported.
    Args:
        symbols: List of symbols to simulate
        strategy_instances: Dictionary mapping Symbol enums to strategy instances
        verbosity: Logging level (0=ERROR, 1=INFO, 2=DEBUG)
        risk_strategy: Risk management strategy instance
        price_data: DataFrame with columns like BTCUSDT_open, BTCUSDT_high, etc on a given timeframe.
        indicators: Dictionary containing technical indicators for all symbols
        
    Returns:
        Dictionary containing simulation results
    """
    # Convert string symbols to Symbol enum for strategy dictionary
    strategy_dict = {}
    for symbol_str in symbols:
        for symbol_enum, strategy in strategy_instances.items():
            if symbol_enum.value == symbol_str:
                strategy_dict[symbol_str] = strategy
                break

    # Prepare data in the format required by the multi-symbol simulation
    timestamps = list(range(len(price_data)))
    prices = {}
    highs = {}
    lows = {}
    closes = {}
    
    for symbol in symbols:
        # prices is open price; simulation will act at every opening bar
        prices[symbol] = {t: price_data[f'{symbol}_open'][t] for t in range(len(price_data))}
        highs[symbol] = {t: price_data[f'{symbol}_high'][t] for t in range(len(price_data))}
        lows[symbol] = {t: price_data[f'{symbol}_low'][t] for t in range(len(price_data))}
        closes[symbol] = {t: price_data[f'{symbol}_close'][t] for t in range(len(price_data))}

    # Initialize simulation
    min_start = get_starting_timestamp(strategy_dict)

    simulation = MarketMakerSimulation(
        strategies=strategy_dict,
        initial_cash=DEFAULT_PARAMS['initial_cash'],
        maker_fee=DEFAULT_PARAMS['maker_fee'],
        taker_fee=DEFAULT_PARAMS['taker_fee'],
        min_start=min_start,
        verbosity=verbosity,
        risk_strategy=risk_strategy
    )
    
    # Run simulation
    results = simulation.run_simulation(
        timestamps=timestamps,
        prices=prices,
        highs=highs,
        lows=lows,
        closes=closes,
        indicators=indicators,
    )

    return results 
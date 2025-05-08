import os
import pandas as pd
from typing import Dict, List
from indicators import IndicatorManager, IndicatorConfig
from trading_strategies.base_strategy import BaseStrategy
from constants import DEFAULT_PARAMS

def load_symbol_data(data_dir: str, period: str, symbols: List[str], revert = False) -> Dict[str, pd.DataFrame]:
    """Load OHLC data for specified symbols
    
    Args:
        data_dir: Base directory containing symbol data
        period: Time period identifier
        symbols: List of symbol names to load
        revert: If data is downloaded form most recent to old, then should be set to True
    Returns:
        Dictionary mapping symbols to their OHLC DataFrames
        
    Raises:
        FileNotFoundError: If data for any symbol is not found
    """
    symbol_data = {}
    reference_index = None  # Will store the first symbol's index for comparison

    for symbol in symbols:
        symbol_path = os.path.join(data_dir, symbol, period)
        data_file = os.path.join(symbol_path, 'data.csv')
        if not os.path.isdir(symbol_path) or not os.path.isfile(data_file):
            raise FileNotFoundError(f"Data not found for symbol {symbol} in {symbol_path}")
            
        # Load OHLC data
        df = pd.read_csv(data_file)
        #select only the first x rows
        if DEFAULT_PARAMS['data_size'] != -1:
            df = df.iloc[:DEFAULT_PARAMS['data_size']]
        df = df[['Unix', 'Open', 'High', 'Low', 'Close']]
        df.columns = df.columns.str.lower()
        
        if revert:
            df = df.iloc[::-1].reset_index(drop=True)  # Reverse and reset index
        else:
            df.reset_index(drop=True, inplace=True)  # Just reset index

        # Print head for debug
        print(f"Loaded data for {symbol}:\n", df.head())

        # Check consistency
        if reference_index is None:
            reference_index = df.index
            reference_shape = df.shape
        else:
            assert df.shape == reference_shape, f"Shape mismatch for {symbol}"
            assert df.index.equals(reference_index), f"Timestamps mismatch for {symbol}"

        symbol_data[symbol] = df

    return symbol_data

def prepare_price_data(symbol_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Prepare combined price DataFrame in required format
    
    Args:
        symbol_data: Dictionary of symbol -> OHLC DataFrame
        
    Returns:
        Combined DataFrame with columns like BTCUSDT_open, BTCUSDT_high, etc.
    """
    combined_data = pd.DataFrame()
    
    for symbol, df in symbol_data.items():
        # Add columns with symbol prefix
        combined_data[f'{symbol}_open'] = df['open']
        combined_data[f'{symbol}_high'] = df['high']
        combined_data[f'{symbol}_low'] = df['low']
        combined_data[f'{symbol}_close'] = df['close']
        
    # Ensure index is integer (0, 1, 2, ...)
    combined_data.reset_index(drop=True, inplace=True)

    return combined_data

def calculate_all_indicators(symbol_data: Dict[str, pd.DataFrame], strategies: Dict[str, BaseStrategy] = None) -> Dict[str, Dict[int, Dict[str, float]]]:
    """Calculate indicators for all symbols
    
    Args:
        symbol_data: Dictionary of symbol -> OHLC DataFrame
        strategies: Dictionary mapping symbols to their strategy instances
        
    Returns:
        Nested dictionary: symbol -> timestamp -> indicator_name -> value
    """
    indicator_manager = IndicatorManager()
    all_indicators = {}
    
    # Get default window lengths
    default_window = DEFAULT_PARAMS['default_window']  # Default window length if no strategy specified

    # Prepare OHLC data and configs for each symbol
    ohlc_dict = {}
    symbol_configs = {}
    
    for symbol, df in symbol_data.items():
        # Convert DataFrame to numpy array with OHLC columns
        ohlc_dict[symbol] = df[['open', 'high', 'low', 'close']].values
        
        # Get window lengths from strategy parameters if available
        window_vol = default_window
        window_sma = default_window
        window_mom = default_window
        window_high_low = default_window

        if symbol in strategies:
            strategy = strategies[symbol]
            if hasattr(strategy, 'params'):
                window_vol = getattr(strategy.params, 'window_vol', default_window)
                window_sma = getattr(strategy.params, 'window_sma', default_window)
                window_mom = getattr(strategy.params, 'window_mom', default_window)
                window_high_low = getattr(strategy.params, 'window_high_low', default_window)
        
        # Create symbol-specific indicator configs
        symbol_configs[symbol] = [
            IndicatorConfig(name='volatility', params={}, window=window_vol),
            IndicatorConfig(name='momentum', params={}, window=window_mom),
            IndicatorConfig(name='sma_deviation', params={}, window=window_sma),
            IndicatorConfig(name='hlma', params={}, window=window_high_low),
            IndicatorConfig(name='hlsd', params={}, window=window_high_low)
        ]
    
    # Calculate indicators using IndicatorManager with symbol-specific configs
    indicator_results = {}
    for symbol, configs in symbol_configs.items():
        symbol_results = indicator_manager.calculate_indicators({symbol: ohlc_dict[symbol]}, configs)
        indicator_results.update(symbol_results)
    # format is symbol -> indicator_name -> values
    #for indic in indicator_results['BTCUSDT'].keys():
    #    # print the firts 10 values
    #    for i in range(10):
    #        print(indic, indicator_results['BTCUSDT'][indic][i])

    # Convert numpy array results to required dictionary format
    for symbol in symbol_data.keys():
        symbol_indicators = {}
        # Get all indicator names for this symbol
        indicator_names = list(indicator_results[symbol].keys())
        
        # For each timestamp index
        for idx in range(len(symbol_data[symbol])):
            symbol_indicators[idx] = {}
            # For each indicator, get its value at this timestamp
            for indicator_name in indicator_names:
                val = indicator_results[symbol][indicator_name][idx]
                symbol_indicators[idx][indicator_name] = float(val)
        
        all_indicators[symbol] = symbol_indicators
        print(all_indicators[symbol])
    # format is like :
    # {
    # 'BTCUSDT': {
    #    0: {'volatility': 0.1, 'momentum': 0.05},
    #    1: {'volatility': 0.12, 'momentum': 0.03},
    #    ...
    #}
    return all_indicators

import numpy as np
from typing import Dict, List, Callable
from dataclasses import dataclass

@dataclass
class IndicatorConfig:
    name: str
    params: Dict[str, any]
    window: int

@dataclass
class IndicatorValue:
    name: str
    value: float
    timestamp: int
    symbol: str

class IndicatorCalculator:
    @staticmethod
    def calculate_volatility(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate rolling volatility using log returns of open prices"""
        open_prices = ohlc[:, 0]  # Use open prices
        if len(open_prices) < window + 1:  # Need extra point for log returns
            return np.full(len(open_prices), np.nan)
            
        # Calculate log returns
        log_returns = np.full(len(open_prices), np.nan)
        log_returns[1:] = np.log(open_prices[1:] / open_prices[:-1])
        
        # Calculate rolling standard deviation of log returns
        volatility = np.full(len(log_returns), np.nan)
        for i in range(window, len(log_returns)):
            window_data = log_returns[i-window+1:i+1]
            if np.sum(~np.isnan(window_data)) >= window // 2:  # Require at least half the window
                volatility[i] = np.nanstd(window_data)
                
        return volatility

    @staticmethod
    def calculate_hlma(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate High-Low Moving Average using previous timestamp's range normalized by current open"""
        if len(ohlc) < window + 1:  # Need extra point for shift
            return np.full(len(ohlc), np.nan)
            
        high, low = ohlc[:, 1], ohlc[:, 2]
        open_prices = ohlc[:, 0]
        
        # Shift high-low range back by 1 to prevent lookahead bias
        hl_range = np.full(len(high), np.nan)  # Initialize with NaN
        hl_range[1:] = (high[:-1] - low[:-1]) / open_prices[1:]
        
        # Pre-allocate output array
        hlma = np.full(len(hl_range), np.nan)
        
        # Calculate moving average only where we have enough data
        for i in range(window, len(hl_range)):
            window_data = hl_range[i-window+1:i+1]
            if np.sum(~np.isnan(window_data)) >= window // 2:  # Require at least half the window
                hlma[i] = np.nanmean(window_data)
                
        return hlma

    @staticmethod
    def calculate_hlsd(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate High-Low Standard Deviation using previous timestamp's range normalized by current open"""
        if len(ohlc) < window + 1:  # Need extra point for shift
            return np.full(len(ohlc), np.nan)
            
        high, low = ohlc[:, 1], ohlc[:, 2]
        open_prices = ohlc[:, 0]
        
        # Shift high-low range back by 1 to prevent lookahead bias
        hl_range = np.full(len(high), np.nan)  # Initialize with NaN
        hl_range[1:] = (high[:-1] - low[:-1]) / open_prices[1:]
        
        # Pre-allocate output array
        hlsd = np.full(len(hl_range), np.nan)
        
        # Calculate standard deviation only where we have enough data
        for i in range(window, len(hl_range)):
            window_data = hl_range[i-window+1:i+1]
            if np.sum(~np.isnan(window_data)) >= window // 2:  # Require at least half the window
                hlsd[i] = np.nanstd(window_data)
                
        return hlsd
    
    @staticmethod
    def calculate_sma_deviation(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate percentage deviation from SMA using open price"""
        open_prices = ohlc[:, 0]  # Use open prices
        if len(open_prices) < window:
            return np.full(len(open_prices), np.nan)
            
        sma = np.full(len(open_prices), np.nan)
        for i in range(window-1, len(open_prices)):
            sma[i] = np.mean(open_prices[i-window+1:i+1])
        deviation = np.full(len(open_prices), np.nan)
        deviation[window-1:] = (open_prices[window-1:] - sma[window-1:]) / sma[window-1:]
        return deviation
    
    @staticmethod
    def calculate_momentum(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate momentum indicator using open prices"""
        open_prices = ohlc[:, 0]  # Use open prices
        if len(open_prices) < window:
            return np.full(len(open_prices), np.nan)
            
        momentum = np.full(len(open_prices), np.nan)
        momentum[window:] = (open_prices[window:] - open_prices[:-window]) / open_prices[:-window]
        return momentum

class IndicatorManager:
    def __init__(self):
        self.indicators: Dict[str, Callable] = {
            'volatility': IndicatorCalculator.calculate_volatility,
            'sma_deviation': IndicatorCalculator.calculate_sma_deviation,
            'momentum': IndicatorCalculator.calculate_momentum,
            'hlma': IndicatorCalculator.calculate_hlma,
            'hlsd': IndicatorCalculator.calculate_hlsd
        }
        
    def calculate_indicators(self, 
                            ohlc_dict: Dict[str, np.ndarray],
                            configs: List[IndicatorConfig]) -> Dict[str, Dict[str, np.ndarray]]:
        """Calculate multiple indicators for multiple symbols
        
        Args:
            ohlc_dict: Dictionary of symbol -> OHLC data
            configs: List of indicator configurations
            
        Returns:
            Dictionary of symbol -> indicator name -> indicator values
        """
        results = {}
        for symbol, ohlc in ohlc_dict.items():
            # Initialize empty dictionary for each timestamp index
            results[symbol] = {}
            
            # Initialize all configured indicators with NaN arrays
            for config in configs:
                if config.name not in self.indicators:
                    raise ValueError(f"Unknown indicator: {config.name}")
                
                # Create NaN array of same length as input data
                results[symbol][config.name] = np.full(len(ohlc), np.nan)
                
                # Only attempt calculation if we have enough data points
                if len(ohlc) >= config.window:
                    calc_func = self.indicators[config.name]
                    try:
                        values = calc_func(ohlc, config.window)
                        # Ensure the calculated values array is the same length as input data
                        if len(values) == len(ohlc):
                            results[symbol][config.name] = values
                        else:
                            print(f"Warning: Calculated values length mismatch for {config.name} on {symbol}")
                    except Exception as e:
                        print(f"Warning: Failed to calculate {config.name} for {symbol}: {str(e)}")
                else:
                    print(f"Warning: Insufficient data points for {config.name} on {symbol}. Need {config.window}, got {len(ohlc)}")

        return results
    
    def register_indicator(self, name: str, calc_func: Callable):
        """Register a new indicator calculation function"""
        self.indicators[name] = calc_func
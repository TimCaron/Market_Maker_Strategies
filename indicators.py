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
            return np.zeros(len(open_prices))  # Return zeros for insufficient data
            
        # Calculate log returns
        log_returns = np.zeros(len(open_prices))  # Initialize with zeros
        log_returns[1:] = np.log(open_prices[1:] / open_prices[:-1])
        
        # Calculate rolling standard deviation of log returns
        volatility = np.zeros(len(log_returns))  # Initialize with zeros
        for i in range(window, len(log_returns)):
            window_data = log_returns[i-window+1:i+1]
            if np.sum(window_data != 0) >= window // 2:  # Require at least half non-zero values
                volatility[i] = np.std(window_data)  # Use std since we've already handled NaNs
                
        return volatility

    @staticmethod
    def calculate_hlma(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate High-Low Moving Average using previous timestamp's range normalized by current open"""
        if len(ohlc) < window + 1:  # Need extra point for shift
            return np.zeros(len(ohlc))  # Return zeros for insufficient data
            
        high, low = ohlc[:, 1], ohlc[:, 2]
        open_prices = ohlc[:, 0]
        
        # Initialize with zeros
        hl_range = np.zeros(len(high))
        
        # Calculate range only for valid price triplets
        valid_high = ~np.isnan(high[:-1])
        valid_low = ~np.isnan(low[:-1])
        valid_open = ~np.isnan(open_prices[1:])
        valid_triplets = valid_high & valid_low & valid_open
        
        # Calculate normalized range where all values are valid
        hl_range[1:] = np.where(
            valid_triplets,
            (high[:-1] - low[:-1]) / np.maximum(np.abs(open_prices[1:]), 1e-6),
            0  # Use 0 for invalid triplets
        )
        
        # Calculate moving average
        hlma = np.zeros(len(hl_range))
        for i in range(window, len(hl_range)):
            window_data = hl_range[i-window+1:i+1]
            if np.sum(window_data != 0) >= window // 2:  # Require at least half non-zero values
                hlma[i] = np.mean(window_data)  # Use mean since we've already handled NaNs
                
        return hlma

    @staticmethod
    def calculate_hlsd(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate High-Low Standard Deviation using previous timestamp's range normalized by current open"""
        if len(ohlc) < window + 1:  # Need extra point for shift
            return np.zeros(len(ohlc))  # Return zeros for insufficient data
            
        high, low = ohlc[:, 1], ohlc[:, 2]
        open_prices = ohlc[:, 0]
        
        # Initialize with zeros
        hl_range = np.zeros(len(high))
        
        # Calculate range only for valid price triplets
        valid_high = ~np.isnan(high[:-1])
        valid_low = ~np.isnan(low[:-1])
        valid_open = ~np.isnan(open_prices[1:])
        valid_triplets = valid_high & valid_low & valid_open
        
        # Calculate normalized range where all values are valid
        hl_range[1:] = np.where(
            valid_triplets,
            (high[:-1] - low[:-1]) / np.maximum(np.abs(open_prices[1:]), 1e-6),
            0  # Use 0 for invalid triplets
        )
        
        # Calculate standard deviation
        hlsd = np.zeros(len(hl_range))
        for i in range(window, len(hl_range)):
            window_data = hl_range[i-window+1:i+1]
            if np.sum(window_data != 0) >= window // 2:  # Require at least half non-zero values
                hlsd[i] = np.std(window_data)  # Use std since we've already handled NaNs
                
        return hlsd
    
    @staticmethod
    def calculate_sma_deviation(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate percentage deviation from SMA using open price"""
        open_prices = ohlc[:, 0]  # Use open prices
        if len(open_prices) < window:
            return np.zeros(len(open_prices))  # Return zeros for insufficient data
            
        # Fill NaN values with the last valid price
        filled_prices = open_prices.copy()
        last_valid = np.nan
        for i in range(len(filled_prices)):
            if np.isnan(filled_prices[i]):
                filled_prices[i] = last_valid if not np.isnan(last_valid) else filled_prices[i]
            else:
                last_valid = filled_prices[i]
        
        # Calculate SMA using filled prices
        sma = np.zeros(len(filled_prices))
        for i in range(window-1, len(filled_prices)):
            window_data = filled_prices[i-window+1:i+1]
            sma[i] = np.mean(window_data)
        
        # Calculate deviation using filled prices
        deviation = np.zeros(len(filled_prices))
        valid_sma = sma != 0
        deviation[window-1:] = np.where(
            valid_sma[window-1:],
            (filled_prices[window-1:] - sma[window-1:]) / sma[window-1:],
            0  # Use 0 when SMA is zero
        )
        return deviation
    
    @staticmethod
    def calculate_momentum(ohlc: np.ndarray, window: int) -> np.ndarray:
        """Calculate momentum indicator using open prices"""
        open_prices = ohlc[:, 0]  # Use open prices
        if len(open_prices) < window:
            return np.zeros(len(open_prices))  # Return zeros for insufficient data
            
        # Initialize with zeros
        momentum = np.zeros(len(open_prices))
        
        # Calculate momentum only for valid price pairs
        valid_current = ~np.isnan(open_prices[window:])
        valid_past = ~np.isnan(open_prices[:-window])
        valid_pairs = valid_current & valid_past
        
        # Calculate momentum where both prices are valid
        momentum[window:] = np.where(
            valid_pairs,
            (open_prices[window:] - open_prices[:-window]) / np.maximum(np.abs(open_prices[:-window]), 1e-6),
            0  # Use 0 for invalid pairs
        )
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
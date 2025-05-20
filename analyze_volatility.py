import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from indicators import IndicatorCalculator, IndicatorConfig
from indicators import IndicatorManager

def calculate_annualized_volatility(returns, window):
    """Calculate annualized volatility from returns"""
    # Calculate rolling standard deviation
    vol = np.zeros(len(returns))
    for i in range(window, len(returns)):
        window_data = returns[i-window+1:i+1]
        if np.sum(window_data != 0) >= window // 2:
            # Annualize the volatility (multiply by sqrt(252) for daily data)
            vol[i] = np.std(window_data) * np.sqrt(252)
    return vol

def analyze_volatility():
    # Load the Brownian motion data
    df = pd.read_csv('data/BROWNIANUSDT/1d/data.csv')
    
    # Calculate returns
    returns = np.zeros(len(df))
    returns[1:] = np.log(df['Close'].values[1:] / df['Close'].values[:-1])
    
    # Calculate volatility using different windows
    windows = [7, 14, 30, 60]
    volatilities = {}
    
    for window in windows:
        vol = calculate_annualized_volatility(returns, window)
        volatilities[f'vol_{window}'] = vol
    
    # Plot the results
    plt.figure(figsize=(15, 10))
    
    # Plot price
    plt.subplot(2, 1, 1)
    plt.plot(df['Unix'], df['Close'], label='Close Price', alpha=0.7)
    plt.title('Brownian Motion Price')
    plt.grid(True)
    plt.legend()
    
    # Plot volatilities
    plt.subplot(2, 1, 2)
    for window, vol in volatilities.items():
        plt.plot(df['Unix'], vol, label=f'Volatility (window={window})', alpha=0.7)
    
    # Add horizontal line for sigma=2
    plt.axhline(y=2.0, color='r', linestyle='--', label='Brownian sigma=2')
    
    plt.title('Volatility Comparison')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.show()
    
    # Print statistics
    print("\nVolatility Statistics:")
    print("-" * 50)
    print(f"Brownian sigma: 2.0")
    for window, vol in volatilities.items():
        mean_vol = np.mean(vol[~np.isnan(vol)])
        std_vol = np.std(vol[~np.isnan(vol)])
        print(f"{window}:")
        print(f"  Mean: {mean_vol:.4f}")
        print(f"  Std: {std_vol:.4f}")
        print(f"  Max: {np.max(vol[~np.isnan(vol)]):.4f}")
        print(f"  Min: {np.min(vol[~np.isnan(vol)]):.4f}")
        print()

if __name__ == '__main__':
    analyze_volatility() 
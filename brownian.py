# Credits : https://github.com/fedecaccia/avellaneda-stoikov/blob/master/src/brownian.py
# with a small adaptation to formt this fake data in timestamps, ohlc format ; lets take slices of size 4
# and redefine open high low close with a random walk, also make sure close == next open
# let use this function to generate Brownian motion and backtest (vanilla stoikov)

"""
brownian() implements one dimensional Brownian motion (i.e. the Wiener process).
"""

# File: brownian.py

from math import sqrt
from scipy.stats import norm
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
from indicators import IndicatorCalculator
import scipy.special
from scipy.optimize import curve_fit

def brownian(x0, n, dt, delta, out=None):
    """
    Generate an instance of Brownian motion (i.e. the Wiener process):

        X(t) = X(0) + N(0, delta**2 * t; 0, t)

    where N(a,b; t0, t1) is a normally distributed random variable with mean a and
    variance b.  The parameters t0 and t1 make explicit the statistical
    independence of N on different time intervals; that is, if [t0, t1) and
    [t2, t3) are disjoint intervals, then N(a, b; t0, t1) and N(a, b; t2, t3)
    are independent.
    
    Written as an iteration scheme,

        X(t + dt) = X(t) + N(0, delta**2 * dt; t, t+dt)

    If `x0` is an array (or array-like), each value in `x0` is treated as
    an initial condition, and the value returned is a numpy array with one
    more dimension than `x0`.

    Arguments
    ---------
    x0 : float or numpy array (or something that can be converted to a numpy array
         using numpy.asarray(x0)).
        The initial condition(s) (i.e. position(s)) of the Brownian motion.
    n : int
        The number of steps to take.
    dt : float
        The time step.
    delta : float
        delta determines the "speed" of the Brownian motion.  The random variable
        of the position at time t, X(t), has a normal distribution whose mean is
        the position at time t=0 and whose variance is delta**2*t.
    out : numpy array or None
        If `out` was not given, create an output array.

    Returns
    -------
    A numpy array of floats with shape `x0.shape + (n,)`.
    
    Note that the initial value `x0` is not included in the returned array.
    """

    x0 = np.asarray(x0)

    # For each element of x0, generate a sample of n numbers from a
    # normal distribution.
    r = norm.rvs(size=x0.shape + (n,), scale=delta*sqrt(dt))

    # If `out` was not given, create an output array.
    if out is None:
        out = np.empty(r.shape)

    # This computes the Brownian motion by forming the cumulative sum of
    # the random samples. 
    np.cumsum(r, axis=-1, out=out)

    # Add the initial condition.
    out += np.expand_dims(x0, axis=-1)

    return out

# The Wiener process parameter.
delta = 2
# Total time.
T = 10000
# Number of steps.
N = T
# Time step size : = 1 
dt = T/N
# Number of realizations to generate.
m = 1
# Create an empty array to store the realizations.
x = np.empty((m,N+1))
# Initial values of x.
x[:, 0] = 80000 #say btc like 8k

x = brownian(x[:,0], N, dt, delta, out=x[:,1:])[0, :]
plt.plot(x)
plt.show()


print(x.shape)
window = 2
returns = np.zeros(len(x))  # Initialize with zeros
returns[1:] = (x[1:] - x[:-1]) / x[:-1]
log_returns = np.zeros(len(x))  # Initialize with zeros
log_returns[1:] = np.log(x[1:] / x[:-1])
# given def above of broownian, this should have a mean of 0 and a std of delta * sqrt(1)
print(x, np.min(x), np.max(x), np.mean(x))
print('la', np.mean(returns[1:]), np.std(returns[1:])*np.mean(x))
print('vs', np.mean(log_returns[1:]), np.std(log_returns[1:])*np.mean(x)) #ok tres proche

# Calculate local volatility
local_vol = np.zeros(len(returns))
window = 10
for i in range(window, len(returns)):
    local_vol[i] = np.std(returns[i-window:i]) * np.mean(x[i-window:i])  
# Calculate mean only of the non-zero values (after window)
valid_vol = local_vol[window:]  # Only take values after the window
mean_local_vol = np.mean(valid_vol)

# Correct for bias in sample standard deviation
# c4 correction factor = sqrt(2/(n-1)) * gamma(n/2) / gamma((n-1)/2)
c4 = np.sqrt(2/(window-1)) * scipy.special.gamma(window/2) / scipy.special.gamma((window-1)/2)
print('Bias correction factor (c4):', c4)
print('Mean of local volatility (uncorrected):', mean_local_vol)
print('Mean of local volatility (corrected):', mean_local_vol/c4)
print('Std of local volatility:', np.std(valid_vol))

# Load data and analyze returns
import os
import glob

def analyze_returns(symbol, period):
    # Find the data file
    data_path = f'data/{symbol}/{period}/data.csv'
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return
    
    # Load data
    df = pd.read_csv(data_path)
    open_prices = df['Open'].values[::-1]
    high_prices = df['High'].values[::-1]
    low_prices = df['Low'].values[::-1]
    
    # Calculate simple returns instead of log returns
    returns = (open_prices[1:] - open_prices[:-1]) / open_prices[:-1]
    
    # Calculate high-low ranges
    hl_range = high_prices - low_prices
    hl_range_normalized = hl_range / open_prices
    
    # Calculate mean absolute high-low ranges
    mean_hl_range = np.mean(hl_range)
    mean_hl_range_normalized = np.mean(hl_range_normalized)
    
    # Plot histogram of returns
    plt.figure(figsize=(12, 6))
    plt.hist(returns, bins=500, density=True, alpha=0.7, label='Returns')
    
    # Fit Gaussian using curve_fit
    def gaussian(x, mu, sigma, amplitude):
        return amplitude * np.exp(-(x - mu)**2 / (2 * sigma**2))
    
    # Get histogram data for curve_fit
    hist, bin_edges = np.histogram(returns, bins=500, density=True)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Initial guess for parameters
    p0 = [np.mean(returns), np.std(returns), 1.0]
    
    # Fit the curve
    popt, pcov = curve_fit(gaussian, bin_centers, hist, p0=p0)
    mu_fit, sigma_fit, amp_fit = popt
    
    # Plot the curve_fit result
    x_fine = np.linspace(min(returns), max(returns), 1000)
    plt.plot(x_fine, gaussian(x_fine, mu_fit, sigma_fit, amp_fit), 
             'g--', lw=2, label=f'Gaussian fit (μ={mu_fit:.4f}, σ={sigma_fit:.4f})')
    
    # Calculate delta from standard deviation
    # For Brownian motion with dt=1, delta = sigma
    delta_est = sigma_fit
    delta_actual = delta_est * np.mean(open_prices)
    
    plt.title(f'Simple Returns Distribution\nEstimated delta = {delta_est:.4f}')
    plt.xlabel('Simple Returns')
    plt.ylabel('Density')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    return delta_est, delta_actual, mean_hl_range, mean_hl_range_normalized

# Analyze returns for BTCUSDT
delta_est, delta_actual, mean_hl_range, mean_hl_range_normalized = analyze_returns('BTCUSDT', '1d')
print(f"\nEstimated normalized delta from returns: {delta_est:.4f}")
print(f"Estimated actual delta from returns: {delta_actual:.4f}")
print(f"Mean absolute high-low range: {mean_hl_range:.4f}")
print(f"Mean absolute high-low range (normalized by open): {mean_hl_range_normalized:.4f}")



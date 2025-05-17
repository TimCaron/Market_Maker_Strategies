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
import time
import os

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
T = 10.0
# Number of steps.
N = 10000
# Time step size
dt = T/N
# Number of realizations to generate.
m = 1
# Create an empty array to store the realizations.
x = np.empty((m,N+1))
# Initial values of x.
x[:, 0] = 80000 #say btc like 80k

x = brownian(x[:,0], N, dt, delta, out=x[:,1:])[0, :]
# save data to have the same format as the real data:
# Unix,Date,Symbol,Open,High,Low,Close,Volume BTC,Volume USDT,tradecount

# Create lists to store OHLC data
opens = []
highs = []
lows = []
closes = []

# Process data in overlapping groups of 4
for i in range(0, len(x)-3, 3):  # Step by 3 to create overlapping groups
    sublist = x[i:i+4]  # Take 4 consecutive points
    if i == 0:
        opens.append(sublist[0])
    else:
        opens.append(closes[-1])  # Use previous close as current open
    highs.append(np.max(sublist))
    lows.append(np.min(sublist))
    closes.append(sublist[-1])

# Create a dataframe with the OHLC data
df = pd.DataFrame({
    'Open': opens,
    'High': highs,
    'Low': lows,
    'Close': closes
})

# Add timestamps (simple integers starting from 0)
df['Unix'] = range(len(df))  # Sequential integers starting from 0
df['Symbol'] = 'BTCUSDT'
df['Volume BTC'] = 0.0  # Placeholder
df['Volume USDT'] = 0.0  # Placeholder
df['tradecount'] = 0  # Placeholder

# Reorder columns to match the desired format
df = df[['Unix', 'Symbol', 'Open', 'High', 'Low', 'Close', 'Volume BTC', 'Volume USDT', 'tradecount']]

# reverse the dataframe, reset index (reversed to be consistent with actual data format)
df = df.iloc[::-1].reset_index(drop=True)
# Save to CSV
#makdir brownian/1d
os.makedirs('BROWNIANUSDT/1d', exist_ok=True)
df.to_csv('BROWNIANUSDT/1d/data.csv', index=False)
print(df.head())
# Plot the data
plt.figure(figsize=(15, 7))
plt.plot(df['Unix'], df['Close'], label='Close Price')
plt.xlabel('Time', fontsize=12)
plt.ylabel('Price', fontsize=12)
plt.title('Brownian Motion OHLC Data', fontsize=14)
plt.grid(True)
plt.legend()
plt.show()
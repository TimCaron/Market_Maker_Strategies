# Market Making Strategy Backtesting Framework

A Python-based framework for backtesting sophisticated market making strategies across multiple cryptocurrency pairs. This tool implements limit order-based market making simulations with configurable risk management and trading strategies, inspired by Stoikov's "Avellaneda-Stoikov" model (Stoikov, 2006). Still under massive development ; this readme is AI generated and not entirely accurate. Lots of todos.

## Project Scope

This project provides a framework for:
- Backtesting market making strategies on historical cryptocurrency data
- Implementing and testing sophisticated market making models (e.g., Stoikov's model)
- Managing multiple trading pairs simultaneously
- Implementing custom risk management rules
- Analyzing performance metrics and visualizing results

## Core Components

### 1. Market Maker Simulation (`market_maker.py`)
The main simulation engine that:
- Manages positions across multiple symbols
- Handles order execution and fills
- Tracks portfolio metrics (wallet balance, margin, leverage)
- Implements the main simulation loop

### 2. Risk Management (`risk_management_strategies/`)
Base and implementation classes for risk management:
- `BaseRiskStrategy`: Abstract base class defining risk management interface
- `BasicRiskStrategy`: Implementation with basic risk rules:
  - Maximum leverage per symbol
  - Emergency exit conditions
  - Early stopping based on margin ratio
  - Minimum order value requirements

### 3. Trading Strategies (`trading_strategies/`)
Base and implementation classes for trading strategies:
- `BaseStrategy`: Abstract base class defining trading strategy interface
- Strategy Factory: Enables parallel backtesting of different strategies:
  - Run multiple strategies simultaneously on the same data
  - Compare performance across different parameter sets
  - Test different models (e.g., Stoikov, Mexico) in parallel
  - Support for symbol-specific strategy selection

### 4. Order Management (`orders.py`, `order_manager.py`)
Handles order creation, validation, and execution:
- `LimitOrder`: Class representing limit orders
- `OrderManager`: Manages order lifecycle and execution

### 5. Performance Analysis (`simulation/`)
Tools for analyzing simulation results:
- `performance_metrics.py`: Calculates Sharpe ratio, Sortino ratio, drawdown
- `results.py`: Processes and displays simulation results
- `visualization.py`: Creates performance visualizations

## Implementation Guide

### 1. Creating a Custom Risk Strategy

Extend `BaseRiskStrategy` and implement required methods:

```python
from risk_management_strategies.base_risk_strategy import BaseRiskStrategy

class CustomRiskStrategy(BaseRiskStrategy):
    def validate_single_order(self, order, current_price, risk_metrics, n_symbols):
        # Implement order validation logic
        pass
        
    def check_emergency_exit(self, risk_metrics, n_symbols):
        # Implement emergency exit conditions
        pass
        
    def continue_simulation(self, risk_metrics, initial_margin):
        # Implement simulation continuation rules
        pass
```

### 2. Running a Simulation with Multiple Strategies

```python
from market_maker import MarketMakerSimulation
from risk_management_strategies import BasicRiskStrategy
from trading_strategies import Mexico, StoikovStrategy

# Initialize strategies
risk_strategy = BasicRiskStrategy()
trading_strategies = {
    'BTCUSDT': Mexico(
        gamma=0.1,  # Risk aversion parameter
        kappa=1.5,  # Order book resilience
        sigma=0.02,  # Volatility estimate
        T=1.0,      # Time horizon
        dt=1/24     # Time step (1 hour)
    ),
    'ETHUSDT': StoikovStrategy(
        risk_aversion=0.1,
        inventory_penalty=0.01,
        volatility_estimate=0.02
    )
}

# Create simulation
simulation = MarketMakerSimulation(
    strategies=trading_strategies,
    risk_strategy=risk_strategy,
    initial_cash=100000.0,
    maker_fee=0.0002,
    taker_fee=0.0005
)

# Run simulation
results = simulation.run_simulation(
    timestamps=timestamps,
    prices=prices,
    highs=highs,
    lows=lows,
    closes=closes,
    indicators=indicators
)
```

## Key Features

### Risk Management
- Per-symbol leverage limits
- Total portfolio leverage limits
- Emergency exit conditions
- Early stopping based on margin ratio
- Minimum order value requirements

### Trading Strategy
- Generic "Mexico" class with parameter-based calculations:
  - Dynamic spread calculation based on historical volatility
  - Reservation price computation using multiple indicators
  - Order size optimization based on market conditions
  - Aggressivity adjustment using market impact models
  - Multiple order level placement strategies
- Stoikov-inspired market making:
  - Inventory-based spread adjustment
  - Risk-averse reservation price calculation
  - Dynamic order sizing based on market conditions
  - Time-based parameter decay

### Performance Analysis
- Sharpe and Sortino ratios
- Maximum drawdown
- Fee analysis
- Position-level PnL tracking
- Visualization of key metrics

## Data Requirements

The simulation requires the following data for each symbol:
- Timestamps
- Open prices
- High prices
- Low prices
- Close prices
- Technical indicators

## Example Usage: Stoikov Strategy Implementation

```python
from market_maker import MarketMakerSimulation
from risk_management_strategies import BasicRiskStrategy
from trading_strategies import Mexico

# Initialize strategies
risk_strategy = BasicRiskStrategy()
trading_strategies = {
    'BTCUSDT': Mexico(
        gamma=0.1,  # Risk aversion parameter
        kappa=1.5,  # Order book resilience
        sigma=0.02,  # Volatility estimate
        T=1.0,      # Time horizon
        dt=1/24     # Time step (1 hour)
    ),
    'ETHUSDT': Mexico(
        gamma=0.15,
        kappa=1.2,
        sigma=0.025,
        T=1.0,
        dt=1/24
    )
}

# Create simulation
simulation = MarketMakerSimulation(
    strategies=trading_strategies,
    risk_strategy=risk_strategy,
    initial_cash=100000.0,
    maker_fee=0.0002,
    taker_fee=0.0005
)

# Run simulation
results = simulation.run_simulation(
    timestamps=timestamps,
    prices=prices,
    highs=highs,
    lows=lows,
    closes=closes,
    indicators=indicators
)
```

## References

- Avellaneda, M., & Stoikov, S. (2006). High-frequency trading in a limit order book.

## Performance Metrics

The simulation tracks and calculates:
1. Portfolio Metrics:
   - Wallet balance
   - Margin
   - Leverage (per symbol and total)
   - Realized and unrealized PnL

2. Risk Metrics:
   - Maximum drawdown
   - Sharpe ratio
   - Sortino ratio
   - Risk-adjusted returns

## Visualization

The results include visualizations of:
- Price history
- Wallet balance
- Margin
- Leverage
- Reservation prices
- Realized PnL

## TODOS
1. Work on trading Strategies; make simple examples with city names 
2. Actually implement Stoikov , not done yet
3. This readme is AI generated and will be updated later
## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Submit a pull request

## License

MIT Licence

## Contact

timcaron373@gmail.com

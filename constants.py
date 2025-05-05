from enum import Enum
from dataclasses import dataclass
from typing import Dict

class Symbol(Enum):
    # deribit most common symbols
    BTC = 'BTCUSDT'
    ETH = 'ETHUSDT'
    SOL = 'SOLUSDT'
    XRP = 'XRPUSDT'
    ADA = 'ADAUSDT'
    DOT = 'DOTUSDT'
    LINK = 'LINKUSDT'
    BCH = 'BCHUSDT'
    LTC = 'LTCUSDT'
    DOGE = 'DOGEUSDT'

    @staticmethod
    def get_all_symbols():
        return list(Symbol)

@dataclass
class SymbolConfig:
    ticksize: float

# Symbol-specific configurations
# Add a minimal quantity if you want
SYMBOL_CONFIGS: Dict[Symbol, SymbolConfig] = {
    Symbol.BTC: SymbolConfig(
        ticksize=1.0,
    ),
    Symbol.ETH: SymbolConfig(
        ticksize=0.5,
    )
}

# Default values for parameters that are common across symbols
# Simulation does not allow for multiple timeframes at once
DEFAULT_PARAMS = {
    'initial_cash': 100000,
    'maker_fee': 0.0002,  # Lower fee for limit orders that provide liquidity
    'taker_fee': 0.0005,  # Higher fee for market orders that take liquidity
    'minimal_spread': 2*0.0005, #dont quote too close to current price; use taker fee as reference
    # what i call spread here is not half of the spread, but the full spread ie first buy - first sell,
    # in basis point
    'valid_periods': ['1', '3', '5', '15', '30', '60', '120', '240', '360', '720', '1d'],
    'default_window' : 14, #default window length for any indicator when not specified
    'data_size' : 20, # debug parameter, to be removed later : on how many data points to run the simulation
    # Risk management parameters
    'max_leverage': 1.0,  # Maximum allowed total leverage accross all symbols (when opening new positions)
    'aggressivity': 0.1, # at each timestamp the total new buy or total new sell order cannot exceed
    #max_leverage*aggressivity (small aggresivity builds slowly the position like a grid bot would)
    'emergency_exit_leverage': 2.0,  # Total leverage level that triggers emergency exit
    'early_stopping_margin': 0.1, # stop simulation if margin ratio is less than 10% of initial margin
    'min_order_value_usd': 10.0,  # Minimum order value in USD
}
# these risk parameters will be probed as well in aparameter search
from typing import Dict, Type, List, Union
from trading_strategies.base_strategy import BaseStrategy
from trading_strategies.stoikov_strategy import StoikovStrategy, StoikovParameters
from trading_strategies.Mexico_strategy import MexicoStrategy, MexicoParameters
from trading_strategies.Tokyo_strategy import TokyoStrategy, TokyoParameters
from constants import Symbol, SYMBOL_CONFIGS

class StrategyFactory:
    """Factory class for creating and managing multiple strategy instances"""
    
    def __init__(self):
        self.strategies: Dict[Symbol, BaseStrategy] = {}
        
    def add_strategy(
        self,
        strategy_class: Type[BaseStrategy],
        symbols: Union[List[str], str],
        base_params: Union[StoikovParameters, MexicoParameters, TokyoParameters]
    ) -> Dict[Symbol, BaseStrategy]:
        """Add strategy instance for given symbols
        
        Args:
            strategy_class: Strategy class to instantiate
            symbols: List of symbol strings or single symbol string
            base_params: Base parameters for the strategy
            
        Returns:
            Dictionary mapping symbols to strategy instances
        """
        # Handle both single symbol string and list of symbols
        if isinstance(symbols, str):
            symbols = [symbols]
            
        for symbol_str in symbols:
            symbol = Symbol(symbol_str)
            
            # Create strategy with appropriate parameter class
            if isinstance(base_params, dict):
                # Convert dict to appropriate parameter class
                if strategy_class == StoikovStrategy:
                    params = StoikovParameters(**base_params)
                elif strategy_class == MexicoStrategy:
                    params = MexicoParameters(**base_params)
                elif strategy_class == TokyoStrategy:
                    params = TokyoParameters(**base_params)
                else:
                    raise NotImplementedError(f"Strategy class {strategy_class} not supported")
            else:
                # Use provided parameter instance directly
                params = base_params
            
            strategy = strategy_class(params)
            self.strategies[symbol] = strategy
            
        return self.strategies
                
    def get_strategy(self, symbol: str) -> BaseStrategy:
        """Get strategy instance for a specific symbol"""
        return self.strategies[Symbol(symbol)]
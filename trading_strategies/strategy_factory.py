from typing import Dict, Type, List, Union
from trading_strategies.base_strategy import BaseStrategy
from trading_strategies.stoikov_strategy import StoikovStrategy, StoikovParameters
from trading_strategies.Mexico_strategy import MexicoStrategy, MexicoParameters
from constants import Symbol, SYMBOL_CONFIGS, DEFAULT_PARAMS

class StrategyFactory:
    """Factory class for creating and managing multiple strategy instances"""
    
    def __init__(self):
        self.strategies: Dict[Symbol, BaseStrategy] = {}
        
    def add_strategy(
        self,
        strategy_class: Type[BaseStrategy],
        symbols: Union[List[str], str],
        base_params: dict
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
            
            # Create symbol-specific parameters
            params = base_params.copy()
            
            if strategy_class == StoikovStrategy:
                strategy = strategy_class(StoikovParameters(**params))
            elif strategy_class == MexicoStrategy:
                strategy = strategy_class(MexicoParameters(**params))
            else:
                raise NotImplementedError(f"Strategy class {strategy_class} not supported")    
            self.strategies[symbol] = strategy
            
        return self.strategies
                
    def get_strategy(self, symbol: str) -> BaseStrategy:
        """Get strategy instance for a specific symbol"""
        return self.strategies[Symbol(symbol)]
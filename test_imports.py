"""
Test script to verify imports are working correctly.
"""

def test_imports():
    print("Testing imports...")
    
    # Test main imports
    try:
        from trading_strategies import (
            BaseStrategy,
            StoikovStrategy,
            StoikovParameters,
            MexicoStrategy,
            MexicoParameters,
            StrategyFactory
        )
        print("✓ trading_strategies package imports successful")
    except ImportError as e:
        print("✗ trading_strategies package imports failed:", str(e))
        return False

    # Test risk management imports
    try:
        from risk_management_strategies.base_risk_strategy import RiskParameters
        from risk_management_strategies.basic_risk_strategy import BasicRiskStrategy
        print("✓ risk_management_strategies imports successful")
    except ImportError as e:
        print("✗ risk_management_strategies imports failed:", str(e))
        return False

    # Test market maker and utils imports
    try:
        from market_maker import MarketMakerSimulation
        from util_data import load_symbol_data, prepare_price_data, calculate_all_indicators
        print("✓ market maker and utils imports successful")
    except ImportError as e:
        print("✗ market maker and utils imports failed:", str(e))
        return False

    # Test strategy factory functionality
    try:
        factory = StrategyFactory()
        btc_params = {
            'q_factor': 0,
            'upnl_factor': 0,
            'mean_revert_factor': 0,
            'momentum_factor': 0,
            'constant_spread': 0.005,
            'vol_factor': 0,
            'spread_mom_factor': 0,
            'max_leverage': 1,
            'max_orders': 10,
            'window_vol': 7,
            'window_sma': 7,
            'window_mom': 7,
            'window_high_low': 3
        }
        strategies = factory.add_strategy(
            strategy_class=MexicoStrategy,
            symbols=['BTCUSDT'],
            base_params=btc_params
        )
        print("✓ strategy factory functionality test successful")
    except Exception as e:
        print("✗ strategy factory functionality test failed:", str(e))
        return False

    # Test risk management functionality
    try:
        risk_params = RiskParameters(
            max_leverage=1.0,
            emergency_exit_leverage=3.0,
            min_margin_ratio=0.1,
            max_position_value=100000.0,
            min_order_value_usd=10.0
        )
        risk_strategy = BasicRiskStrategy(risk_params)
        print("✓ risk management functionality test successful")
    except Exception as e:
        print("✗ risk management functionality test failed:", str(e))
        return False

    print("\nAll import tests passed successfully!")
    return True

if __name__ == "__main__":
    test_imports() 
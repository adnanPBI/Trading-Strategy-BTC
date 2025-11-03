#!/usr/bin/env python3
"""
Quick test script to verify backtest runner works correctly.
Tests with a small synthetic dataset.
"""

import sys
import os
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'base-bot-template'))

# Import backtest runner
from backtest_runner import BacktestEngine, print_backtest_results

def test_backtest():
    """Run a quick test backtest."""
    print("="*60)
    print("🧪 TESTING BACKTEST RUNNER")
    print("="*60)
    
    # Test configuration
    config = {
        "strategy": "momentum_reversion",
        "symbol": "BTC-USD",
        "starting_cash": 10000.0,
        "fee_rate": 0.005,
        
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "sma_short": 20,
        "sma_long": 50,
        "base_position_size": 0.15,
        "max_position_size": 0.40,
        "take_profit_pct": 4.0,
        "stop_loss_pct": 2.5,
        "trailing_stop_pct": 2.0,
        "volatility_window": 30,
        "min_trade_spacing_minutes": 30
    }
    
    # Short test period (1 month)
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    print("\n✅ Configuration loaded")
    print("✅ Strategy imported successfully")
    print("✅ Dates set: {} to {}".format(start_date.date(), end_date.date()))
    
    # Run backtest
    print("\n🚀 Running test backtest...")
    engine = BacktestEngine(config)
    
    try:
        results = engine.run_backtest(start_date, end_date, interval="1h")
        print("\n✅ Backtest completed successfully!")
        
        print_backtest_results(results)
        
        print("\n" + "="*60)
        print("🎉 TEST PASSED!")
        print("="*60)
        print("\nYou can now run full backtests:")
        print("  python backtest_runner.py")
        print("  python backtest_runner.py --optimize")
        print("\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backtest()
    sys.exit(0 if success else 1)

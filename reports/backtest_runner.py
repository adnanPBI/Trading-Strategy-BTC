#!/usr/bin/env python3
"""
OPTIMIZED Backtest Runner - TARGET: 25-35% Returns
Uses adaptive_trend_strategy_OPTIMIZED.py
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
import statistics

# Import OPTIMIZED strategy
strategy_path = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, strategy_path)

from adaptive_trend_strategy_OPTIMIZED import AdaptiveTrendStrategyOptimized


@dataclass 
class Portfolio:
    """Portfolio state."""
    symbol: str
    cash: float
    quantity: float
    
    def value(self, current_price: float) -> float:
        return self.cash + (self.quantity * current_price)


@dataclass
class Signal:
    """Trading signal."""
    action: str  # buy, sell, hold
    size: float = 0.0
    reason: str = ""
    entry_price: float = 0.0


@dataclass
class MarketSnapshot:
    """Market data snapshot."""
    symbol: str
    prices: List[float]
    current_price: float
    timestamp: datetime


@dataclass
class BacktestResults:
    """Results."""
    starting_capital: float
    ending_capital: float
    total_return_pct: float
    total_pnl: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    avg_win: float
    avg_loss: float


class HistoricalDataGenerator:
    """Generate Jan-Jun 2024 market data."""
    
    def generate_bullish_market(self, days: int = 90) -> List[Dict[str, Any]]:
        """Bull market Jan-Mar (45k→70k)."""
        import random
        
        candles = []
        start_price = 45000
        current_price = start_price
        target_price = 70000
        daily_increase = (target_price - start_price) / days
        current_time = datetime(2024, 1, 1)
        
        for day in range(days):
            for hour in range(24):
                trend = daily_increase / 24
                noise = random.gauss(0, current_price * 0.01)
                new_price = current_price + trend + noise
                new_price = max(new_price, current_price * 0.98)
                
                high = max(current_price, new_price) * (1 + random.uniform(0, 0.005))
                low = min(current_price, new_price) * (1 - random.uniform(0, 0.005))
                
                candles.append({
                    "timestamp": current_time,
                    "open": current_price,
                    "high": high,
                    "low": low,
                    "close": new_price,
                    "volume": random.uniform(100, 1000)
                })
                
                current_price = new_price
                current_time += timedelta(hours=1)
        
        return candles
    
    def generate_correction_market(self, days: int = 90) -> List[Dict[str, Any]]:
        """Correction Apr-Jun (70k→60k)."""
        import random
        
        candles = []
        start_price = 70000
        current_price = start_price
        target_price = 60000
        daily_decrease = (start_price - target_price) / days
        current_time = datetime(2024, 4, 1)
        
        for day in range(days):
            for hour in range(24):
                trend = -daily_decrease / 24
                noise = random.gauss(0, current_price * 0.015)
                
                # Occasional bounces
                if random.random() < 0.2:
                    noise += current_price * random.uniform(0.01, 0.02)
                
                new_price = current_price + trend + noise
                new_price = max(new_price, target_price * 0.95)
                
                high = max(current_price, new_price) * (1 + random.uniform(0, 0.008))
                low = min(current_price, new_price) * (1 - random.uniform(0, 0.008))
                
                candles.append({
                    "timestamp": current_time,
                    "open": current_price,
                    "high": high,
                    "low": low,
                    "close": new_price,
                    "volume": random.uniform(100, 1000)
                })
                
                current_price = new_price
                current_time += timedelta(hours=1)
        
        return candles
    
    def generate_full_period(self) -> List[Dict[str, Any]]:
        """Generate Jan-Jun 2024."""
        print("📊 Generating Jan-Jun 2024 data...")
        bull = self.generate_bullish_market(90)
        correction = self.generate_correction_market(90)
        all_candles = bull + correction
        print(f"   ✅ {len(all_candles)} hourly candles\n")
        return all_candles


class BacktestEngine:
    """Optimized backtest engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = config.get("symbol", "BTC-USD")
        self.starting_cash = config.get("starting_cash", 10000.0)
        self.fee_rate = config.get("fee_rate", 0.005)
        self.data_generator = HistoricalDataGenerator()
    
    def run_backtest(self) -> BacktestResults:
        """Run optimized backtest."""
        print("\n" + "="*70)
        print("🚀 OPTIMIZED BACKTEST - TARGET: 25-35% RETURNS")
        print("="*70)
        print(f"Strategy: Adaptive Trend OPTIMIZED")
        print(f"Period: Jan-Jun 2024 (BTC 45k→70k→60k)")
        print(f"Starting Capital: ${self.starting_cash:,.2f}")
        print(f"Fee Rate: {self.fee_rate*100}%")
        print("="*70)
        
        print("\n🔧 OPTIMIZATIONS:")
        print("  ✅ 30% initial → 80% max position (vs 10%→50%)")
        print("  ✅ 5% trailing, 7% stop loss (vs 1.5%/3%)")
        print("  ✅ Profit at 10%/20%/40% (vs 2%/4%/8%)")
        print("  ✅ Direct uptrend entries (NEW)")
        print("  ✅ 5min trade spacing (vs 15min)")
        print("="*70 + "\n")
        
        historical_data = self.data_generator.generate_full_period()
        
        # Initialize OPTIMIZED strategy
        strategy = AdaptiveTrendStrategyOptimized(self.config, exchange=None)
        
        portfolio = Portfolio(
            symbol=self.symbol,
            cash=self.starting_cash,
            quantity=0.0
        )
        
        trades = []
        equity_curve = []
        price_history = []
        trade_count = 0
        
        print("🔄 Running backtest...\n")
        
        # Run simulation
        for i, candle in enumerate(historical_data):
            price_history.append(candle["close"])
            
            snapshot = MarketSnapshot(
                symbol=self.symbol,
                prices=price_history.copy(),
                current_price=candle["close"],
                timestamp=candle["timestamp"]
            )
            
            signal = strategy.generate_signal(snapshot, portfolio)
            
            # Execute BUY
            if signal.action == "buy" and signal.size > 0 and portfolio.cash > 0:
                max_size = portfolio.cash / (candle["close"] * (1 + self.fee_rate))
                trade_size = min(signal.size, max_size)
                
                if trade_size > 0:
                    trade_value = trade_size * candle["close"]
                    fee = trade_value * self.fee_rate
                    total_cost = trade_value + fee
                    
                    if total_cost <= portfolio.cash:
                        portfolio.cash -= total_cost
                        portfolio.quantity += trade_size
                        trade_count += 1
                        
                        trades.append({
                            "side": "buy",
                            "price": candle["close"],
                            "size": trade_size,
                            "timestamp": candle["timestamp"]
                        })
                        
                        strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                        
                        if trade_count <= 10 or trade_count % 10 == 0:
                            print(f"  #{trade_count:3d} BUY  @ ${candle['close']:8,.2f} | {signal.reason}")
            
            # Execute SELL
            elif signal.action == "sell" and signal.size > 0 and portfolio.quantity > 0:
                trade_size = min(signal.size, portfolio.quantity)
                
                if trade_size > 0:
                    trade_value = trade_size * candle["close"]
                    fee = trade_value * self.fee_rate
                    proceeds = trade_value - fee
                    
                    portfolio.quantity -= trade_size
                    portfolio.cash += proceeds
                    trade_count += 1
                    
                    trades.append({
                        "side": "sell",
                        "price": candle["close"],
                        "size": trade_size,
                        "timestamp": candle["timestamp"]
                    })
                    
                    strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                    
                    if trade_count <= 10 or trade_count % 10 == 0:
                        print(f"  #{trade_count:3d} SELL @ ${candle['close']:8,.2f} | {signal.reason}")
            
            equity_curve.append(portfolio.value(candle["close"]))
        
        print(f"\n✅ Backtest complete: {trade_count} trades\n")
        
        return self._calculate_results(trades, equity_curve, historical_data, portfolio)
    
    def _calculate_results(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        historical_data: List[Dict],
        final_portfolio: Portfolio
    ) -> BacktestResults:
        """Calculate metrics."""
        
        final_price = historical_data[-1]["close"]
        ending_capital = final_portfolio.value(final_price)
        
        # Match trades
        buy_trades = [t for t in trades if t["side"] == "buy"]
        sell_trades = [t for t in trades if t["side"] == "sell"]
        
        wins = []
        losses = []
        
        for sell in sell_trades:
            if buy_trades:
                buy = buy_trades.pop(0)
                pnl_pct = (sell["price"] - buy["price"]) / buy["price"] * 100
                
                if pnl_pct > 0:
                    wins.append(pnl_pct)
                else:
                    losses.append(abs(pnl_pct))
        
        winning_trades = len(wins)
        losing_trades = len(losses)
        total_pairs = winning_trades + losing_trades
        win_rate = (winning_trades / total_pairs * 100) if total_pairs > 0 else 0
        
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0
        
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = sum(losses) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        
        total_return_pct = (ending_capital - self.starting_cash) / self.starting_cash * 100
        total_pnl = ending_capital - self.starting_cash
        
        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # Sharpe ratio
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(ret)
            
            if returns and len(returns) > 1:
                mean_ret = statistics.mean(returns)
                std_ret = statistics.stdev(returns)
                sharpe = (mean_ret / std_ret) * (8760 ** 0.5) if std_ret > 0 else 0.0
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0
        
        return BacktestResults(
            starting_capital=self.starting_cash,
            ending_capital=ending_capital,
            total_return_pct=total_return_pct,
            total_pnl=total_pnl,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss
        )



def print_results(results: BacktestResults):
    """Print formatted results with comparison."""
    print("="*70)
    print("📊 OPTIMIZED BACKTEST RESULTS")
    print("="*70)
    
    print(f"\n💰 PERFORMANCE")
    print(f"Starting Capital:    ${results.starting_capital:,.2f}")
    print(f"Ending Capital:      ${results.ending_capital:,.2f}")
    print(f"Total P&L:           ${results.total_pnl:+,.2f}")
    print(f"Total Return:        {results.total_return_pct:+.2f}%")
    
    # Comparison with original
    original_return = 6.42
    improvement = results.total_return_pct - original_return
    improvement_factor = results.total_return_pct / original_return if original_return > 0 else 0
    
    print(f"\n📈 VS ORIGINAL STRATEGY")
    print(f"Original Return:     +{original_return:.2f}%")
    print(f"Optimized Return:    {results.total_return_pct:+.2f}%")
    print(f"Improvement:         {improvement:+.2f}% ({improvement_factor:.1f}x)")
    
    print(f"\n⚠️ RISK METRICS")
    print(f"Max Drawdown:        {results.max_drawdown_pct:.2f}%")
    print(f"Sharpe Ratio:        {results.sharpe_ratio:.2f}")
    print(f"Profit Factor:       {results.profit_factor:.2f}")
    
    print(f"\n📊 TRADING ACTIVITY")
    print(f"Total Trades:        {results.total_trades}")
    print(f"Winning Trades:      {results.winning_trades}")
    print(f"Losing Trades:       {results.losing_trades}")
    print(f"Win Rate:            {results.win_rate:.1f}%")
    print(f"Average Win:         {results.avg_win:+.2f}%")
    print(f"Average Loss:        {results.avg_loss:+.2f}%")
    
    print(f"\n✅ CONTEST REQUIREMENTS")
    trades_pass = "✅ PASS" if results.total_trades >= 10 else "❌ FAIL"
    dd_pass = "✅ PASS" if results.max_drawdown_pct < 50 else "❌ FAIL"
    return_pass = "✅ PASS" if results.total_return_pct > 0 else "❌ FAIL"
    
    print(f"Min 10 trades:       {trades_pass} ({results.total_trades} trades)")
    print(f"Max DD < 50%:        {dd_pass} ({results.max_drawdown_pct:.1f}%)")
    print(f"Positive returns:    {return_pass} ({results.total_return_pct:+.2f}%)")
    
    print("="*70 + "\n")


def main():
    """Main execution with OPTIMIZED configuration."""
    
    # OPTIMIZED CONFIG
    config = {
        "symbol": "BTC-USD",
        "starting_cash": 10000.0,
        "fee_rate": 0.005,
        
        # Trend detection (same)
        "ema_fast": 12,
        "ema_slow": 26,
        "trend_strength_threshold": 0.015,  # Lower = more sensitive
        
        # OPTIMIZED: More aggressive entries
        "pullback_pct": 1.0,  # 1% (vs 2%)
        "breakout_threshold": 0.8,  # 0.8% (vs 1.5%)
        
        # OPTIMIZED: Aggressive position sizing
        "initial_position_pct": 0.30,  # 30% (vs 10%)
        "max_position_pct": 0.80,  # 80% (vs 50%)
        "pyramid_size_pct": 0.15,  # 15% (vs 10%)
        
        # OPTIMIZED: Later profit taking
        "profit_level_1": 10.0,  # 10% (vs 2%)
        "profit_level_2": 20.0,  # 20% (vs 4%)
        "profit_level_3": 40.0,  # 40% (vs 8%)
        
        # OPTIMIZED: Wider stops
        "stop_loss_pct": 7.0,  # 7% (vs 3%)
        "trailing_stop_pct": 5.0,  # 5% (vs 1.5%)
        
        # OPTIMIZED: Faster execution
        "min_trade_spacing_minutes": 5,  # 5min (vs 15min)
        "max_positions": 6,  # 6 (vs 5)
        
        # NEW: Volatility
        "volatility_window": 24,
        "high_volatility_threshold": 0.04
    }
    
    print("\n🔧 OPTIMIZED CONFIGURATION")
    print("="*70)
    print("Designed to capture 45-65% of major moves")
    print("Target: 25-35% return (vs original 6.42%)")
    print("="*70 + "\n")
    
    engine = BacktestEngine(config)
    results = engine.run_backtest()
    print_results(results)
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "OPTIMIZED",
        "config": config,
        "results": {
            "starting_capital": results.starting_capital,
            "ending_capital": results.ending_capital,
            "total_return_pct": results.total_return_pct,
            "total_pnl": results.total_pnl,
            "max_drawdown_pct": results.max_drawdown_pct,
            "sharpe_ratio": results.sharpe_ratio,
            "profit_factor": results.profit_factor,
            "total_trades": results.total_trades,
            "win_rate": results.win_rate,
            "improvement_vs_original": results.total_return_pct - 6.42
        }
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "backtest_results_OPTIMIZED.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"💾 Results saved to: {output_path}")
    
    # Performance summary
    if results.total_return_pct > 20:
        print("\n🏆 EXCELLENT! Target achieved (>20% return)")
    elif results.total_return_pct > 15:
        print("\n✅ GOOD! Strong improvement over original")
    elif results.total_return_pct > 10:
        print("\n⚠️ OK, but room for improvement")
    else:
        print("\n❌ Needs further optimization")
    
    print()


if __name__ == "__main__":
    main()

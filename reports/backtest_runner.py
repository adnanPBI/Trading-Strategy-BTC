#!/usr/bin/env python3
"""
BUY-AND-HOLD MAXIMIZER Backtest - Match +26.70% Winner

WINNER'S APPROACH:
- Buy early in bull run (Jan)
- HOLD through entire move (45k→70k)
- Exit only on catastrophic crash (>40%)
- Result: +26.70% (BTC: +26.41%, ETH: +27.00%)

TARGET: >=+20% return
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass
import statistics

strategy_path = os.path.join(os.path.dirname(__file__), '..', 'adaptive-trend-strategy')
sys.path.insert(0, strategy_path)

from buyhold_maximizer import BuyAndHoldMaximizer


@dataclass
class Portfolio:
    symbol: str
    cash: float
    quantity: float
    
    def value(self, current_price: float) -> float:
        return self.cash + (self.quantity * current_price)


@dataclass
class Signal:
    action: str
    size: float = 0.0
    reason: str = ""
    entry_price: float = 0.0


@dataclass
class MarketSnapshot:
    symbol: str
    prices: List[float]
    current_price: float
    timestamp: datetime


@dataclass
class BacktestResults:
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
    """Generate HOURLY data for Jan 1 - June 30, 2024."""
    
    def generate_bullish_market(self, days: int = 90) -> List[Dict[str, Any]]:
        """Bull market Jan-Mar (45k→70k) - HOURLY data."""
        import random
        
        candles = []
        start_price = 45000
        current_price = start_price
        target_price = 70000
        daily_increase = (target_price - start_price) / days
        current_time = datetime(2024, 1, 1, 0, 0, 0)
        
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
                current_time += timedelta(hours=1)  # HOURLY
        
        return candles
    
    def generate_correction_market(self, days: int = 90) -> List[Dict[str, Any]]:
        """Correction Apr-Jun 30 (70k→60k) - HOURLY data."""
        import random
        
        candles = []
        start_price = 70000
        current_price = start_price
        target_price = 60000
        daily_decrease = (start_price - target_price) / days
        current_time = datetime(2024, 4, 1, 0, 0, 0)
        
        for day in range(days):
            for hour in range(24):
                # STOP AT JUNE 30
                if current_time >= datetime(2024, 7, 1):
                    break
                
                trend = -daily_decrease / 24
                noise = random.gauss(0, current_price * 0.015)
                
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
                current_time += timedelta(hours=1)  # HOURLY
            
            if current_time >= datetime(2024, 7, 1):
                break
        
        return candles
    
    def generate_full_period(self) -> List[Dict[str, Any]]:
        """Generate HOURLY data for Jan 1 - June 30, 2024."""
        print("📊 Generating HOURLY data: Jan 1 - June 30, 2024...")
        bull = self.generate_bullish_market(90)
        correction = self.generate_correction_market(90)
        all_candles = bull + correction
        
        # Ensure ends June 30
        all_candles = [c for c in all_candles if c["timestamp"] < datetime(2024, 7, 1)]
        
        print(f"   ✅ {len(all_candles)} HOURLY candles generated\n")
        return all_candles


class BacktestEngine:
    """Buy-and-hold maximizer backtest engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = config.get("symbol", "BTC-USD")
        self.starting_cash = config.get("starting_cash", 10000.0)
        self.fee_rate = config.get("fee_rate", 0.005)
        self.data_generator = HistoricalDataGenerator()
    
    def run_backtest(self) -> BacktestResults:
        """Run buy-and-hold maximizer backtest."""
        print("\n" + "="*70)
        print("🏆 BUY-AND-HOLD MAXIMIZER - Match +26.70% Winner")
        print("="*70)
        print(f"Strategy: Buy early, HOLD through trends, exit only on crash")
        print(f"Period: Jan 1 - June 30, 2024 (HOURLY data)")
        print(f"Starting Capital: ${self.starting_cash:,.2f}")
        print(f"Position Size: 55% (contest rule)")
        print(f"Exit Trigger: >40% crash OR strong downtrend")
        print("="*70)
        
        print("\n🎯 WINNER'S FORMULA:")
        print("  ✅ Enter immediately in uptrend")
        print("  ✅ HOLD through small dips (NO 4% trailing stop)")
        print("  ✅ NO profit taking at 5%/10%/20%")
        print("  ✅ Exit only on catastrophic crash (>40%)")
        print("  ✅ Target: >=+20% (winner got +26.70%)")
        print("="*70 + "\n")
        
        historical_data = self.data_generator.generate_full_period()
        
        # Initialize strategy
        strategy = BuyAndHoldMaximizer(self.config, exchange=None)
        
        portfolio = Portfolio(
            symbol=self.symbol,
            cash=self.starting_cash,
            quantity=0.0
        )
        
        trades = []
        equity_curve = []
        price_history = []
        trade_count = 0
        
        print("🔄 Running buy-and-hold maximizer...\n")
        
        # Run simulation on HOURLY data
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
                            "timestamp": candle["timestamp"],
                            "reason": signal.reason
                        })
                        
                        strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                        
                        print(f"  #{trade_count:3d} BUY  @ ${candle['close']:8,.2f} | {candle['timestamp'].strftime('%Y-%m-%d %H:%M')} | {signal.reason}")
            
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
                        "timestamp": candle["timestamp"],
                        "reason": signal.reason
                    })
                    
                    strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                    
                    print(f"  #{trade_count:3d} SELL @ ${candle['close']:8,.2f} | {candle['timestamp'].strftime('%Y-%m-%d %H:%M')} | {signal.reason}")
            
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
        """Calculate results."""
        
        final_price = historical_data[-1]["close"]
        ending_capital = final_portfolio.value(final_price)
        
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
    """Print results."""
    print("="*70)
    print("🏆 BUY-AND-HOLD MAXIMIZER RESULTS")
    print("="*70)
    
    print(f"\n💰 PERFORMANCE")
    print(f"Starting Capital:    ${results.starting_capital:,.2f}")
    print(f"Ending Capital:      ${results.ending_capital:,.2f}")
    print(f"Total P&L:           ${results.total_pnl:+,.2f}")
    print(f"Total Return:        {results.total_return_pct:+.2f}%")
    
    winner_return = 26.70
    target_return = 20.0
    
    print(f"\n📈 VS TARGET")
    print(f"Winner's Return:     +{winner_return:.2f}%")
    print(f"Target (Minimum):    +{target_return:.2f}%")
    print(f"Your Return:         {results.total_return_pct:+.2f}%")
    
    if results.total_return_pct >= winner_return:
        status = "🏆 MATCH OR BEAT WINNER!"
        print(f"\n{status}")
    elif results.total_return_pct >= target_return:
        status = "✅ TARGET ACHIEVED!"
        print(f"\n{status}")
    elif results.total_return_pct >= 15:
        status = "⚠️ CLOSE TO TARGET"
        print(f"\n{status}")
    else:
        status = "❌ BELOW TARGET"
        print(f"\n{status}")
    
    print(f"\n⚠️ RISK METRICS")
    print(f"Max Drawdown:        {results.max_drawdown_pct:.2f}%")
    print(f"Sharpe Ratio:        {results.sharpe_ratio:.2f}")
    print(f"Profit Factor:       {results.profit_factor:.2f}")
    
    print(f"\n📊 TRADING STATS")
    print(f"Total Trades:        {results.total_trades}")
    print(f"Winning Trades:      {results.winning_trades}")
    print(f"Losing Trades:       {results.losing_trades}")
    print(f"Win Rate:            {results.win_rate:.1f}%")
    print(f"Average Win:         {results.avg_win:+.2f}%")
    print(f"Average Loss:        -{results.avg_loss:.2f}%")
    
    print(f"\n✅ CONTEST REQUIREMENTS")
    print(f"Min 10 trades:       {'✅' if results.total_trades >= 10 else '❌'} ({results.total_trades})")
    print(f"Max DD < 50%:        {'✅' if results.max_drawdown_pct < 50 else '❌'} ({results.max_drawdown_pct:.1f}%)")
    print(f"Return >= 20%:       {'✅' if results.total_return_pct >= 20 else '❌'} ({results.total_return_pct:+.2f}%)")
    
    print(f"\n🎯 STATUS: {status}")
    print("="*70 + "\n")


def main():
    """Main execution."""
    
    # BUY-AND-HOLD MAXIMIZER CONFIG
    config = {
        "symbol": "BTC-USD",
        "starting_cash": 10000.0,
        "fee_rate": 0.005,
        
        # Simple trend detection
        "ema_fast": 12,
        "ema_slow": 26,
        "min_trend_strength": 0.02,  # 2% for clear uptrend
        
        # Position sizing (CONTEST RULE: 55%)
        "initial_position_pct": 0.55,  # 55% immediately
        "max_position_pct": 0.55,  # 55% max
        
        # Exit only on catastrophic events
        "catastrophic_crash_pct": 40.0,  # 40% crash
        "strong_downtrend_threshold": 0.05,  # 5% EMA reversal
        
        # Trade management
        "min_trade_spacing_hours": 4,  # 4 hours between trades
        "reentry_dip_pct": 3.0  # 3% dip for re-entry
    }
    
    print("\n🔧 BUY-AND-HOLD MAXIMIZER CONFIG")
    print("="*70)
    print("Match winner's +26.70% with simple buy-and-hold")
    print("="*70 + "\n")
    
    engine = BacktestEngine(config)
    results = engine.run_backtest()
    print_results(results)
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "BUY_AND_HOLD_MAXIMIZER",
        "contest_rules": {
            "max_position": "55%",
            "end_date": "2024-06-30",
            "data_interval": "HOURLY"
        },
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
            "vs_winner": results.total_return_pct - 26.70
        }
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "backtest_results_BUYHOLD.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"💾 Results saved to: {output_path}\n")
    
    if results.total_return_pct >= 26:
        print("🏆 EXCELLENT! Matched or beat the winner!")
    elif results.total_return_pct >= 20:
        print("✅ GREAT! Target achieved (>=20%)")
    elif results.total_return_pct >= 15:
        print("⚠️ CLOSE! Minor tuning needed")
    else:
        print("❌ Below target - review strategy")


if __name__ == "__main__":
    main()

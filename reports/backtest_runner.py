#!/usr/bin/env python3
"""
PROFITABLE Backtesting Framework - Optimized for Adaptive Trend Strategy
Focus: MAKING MONEY in Jan-Jun 2024 crypto markets
"""

import json
import sys
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import statistics
import logging

# Add base template to path
base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    base_path = '/app/base'
sys.path.insert(0, base_path)

# Import NEW profitable strategy
adaptive_strategy_path = os.path.join(os.path.dirname(__file__), '..', 'adaptive-trend-strategy')
sys.path.insert(0, adaptive_strategy_path)
import adaptive_trend_strategy

from strategy_interface import Portfolio, Signal, create_strategy
from exchange_interface import MarketSnapshot


@dataclass
class BacktestResults:
    """Complete backtest results."""
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


class RealDataFetcher:
    """
    Fetch REAL historical data from Coinbase Pro API.
    This replaces synthetic data for realistic backtesting.
    """

    def __init__(self):
        self.coinbase_url = "https://api.exchange.coinbase.com"
        self.logger = logging.getLogger(__name__)

    def fetch_real_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        granularity: int = 3600
    ) -> List[Dict[str, Any]]:
        """Fetch real historical data from Coinbase Pro."""
        try:
            import requests

            self.logger.info(f"Fetching REAL data for {symbol} from Coinbase...")

            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

            all_candles = []
            max_candles_per_request = 300
            chunk_duration = max_candles_per_request * granularity

            current = start
            request_count = 0

            while current < end:
                next_time = min(current + timedelta(seconds=chunk_duration), end)

                url = f"{self.coinbase_url}/products/{symbol}/candles"
                params = {
                    'start': current.isoformat(),
                    'end': next_time.isoformat(),
                    'granularity': granularity
                }

                try:
                    response = requests.get(url, params=params, timeout=30)
                    response.raise_for_status()
                    raw_candles = response.json()

                    for candle in raw_candles:
                        all_candles.append({
                            'timestamp': datetime.fromtimestamp(candle[0], tz=timezone.utc),
                            'open': float(candle[3]),
                            'high': float(candle[2]),
                            'low': float(candle[1]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })

                    self.logger.info(f"Fetched {len(raw_candles)} candles ({current.date()} to {next_time.date()})")

                    request_count += 1
                    if request_count % 3 == 0:
                        time.sleep(1)  # Rate limiting

                except Exception as e:
                    self.logger.error(f"Error fetching chunk: {e}")

                current = next_time

            all_candles.sort(key=lambda x: x['timestamp'])
            self.logger.info(f"✅ Fetched {len(all_candles)} REAL candles from Coinbase")
            return all_candles

        except ImportError:
            self.logger.warning("requests library not available, using synthetic data")
            return None
        except Exception as e:
            self.logger.error(f"Failed to fetch real data: {e}, using synthetic data")
            return None


class HistoricalDataGenerator:
    """
    Generate realistic historical crypto price data.
    FALLBACK: Used only if real data fetch fails.

    For Jan-Jun 2024: Bull market with correction
    - Jan-March: Strong uptrend (45k → 70k)
    - April-June: Correction and consolidation (70k → 60k)
    """
    
    def generate_bullish_market(self, days: int = 60) -> List[Dict[str, Any]]:
        """Generate bullish trending market (Jan-March 2024)."""
        import random
        
        candles = []
        start_price = 45000
        current_price = start_price
        target_price = 70000
        
        # Daily increase to reach target
        daily_increase = (target_price - start_price) / days

        current_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        for day in range(days):
            # 24 hourly candles per day
            for hour in range(24):
                # Trend + noise
                trend_component = daily_increase / 24
                noise = random.gauss(0, current_price * 0.01)  # 1% volatility
                
                new_price = current_price + trend_component + noise
                new_price = max(new_price, current_price * 0.98)  # Max 2% drop per hour
                
                # Generate OHLC
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
        """Generate correction market (April-June 2024)."""
        import random
        
        candles = []
        start_price = 70000
        current_price = start_price
        target_price = 60000
        
        # Gradual decline with volatility
        daily_decrease = (start_price - target_price) / days

        current_time = datetime(2024, 4, 1, tzinfo=timezone.utc)
        
        for day in range(days):
            for hour in range(24):
                # Downtrend + volatility + occasional bounces
                trend_component = -daily_decrease / 24
                noise = random.gauss(0, current_price * 0.015)  # 1.5% volatility (higher in corrections)
                
                # Occasional strong bounces (20% of time)
                if random.random() < 0.2:
                    noise += current_price * random.uniform(0.01, 0.02)
                
                new_price = current_price + trend_component + noise
                new_price = max(new_price, target_price * 0.95)  # Floor
                
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
        """Generate complete Jan-Jun 2024 market."""
        print("📊 Generating Jan-Jun 2024 market data...")
        print("   Jan-March: Bull market (45k → 70k)")
        print("   April-June: Correction (70k → 60k)")
        
        bull_market = self.generate_bullish_market(days=90)  # Jan-March
        correction = self.generate_correction_market(days=90)  # April-June
        
        all_candles = bull_market + correction
        print(f"   ✅ Generated {len(all_candles)} hourly candles\n")
        
        return all_candles


class EnhancedExecutionModel:
    """
    Realistic execution model with slippage and spreads.

    Models real-world trading costs beyond just fees:
    - Bid-ask spread (wider in low volume)
    - Slippage (worse for larger orders)
    - Market impact
    """

    def __init__(self, base_fee: float = 0.005, base_spread: float = 0.0005):
        self.base_fee = base_fee  # 0.5% taker fee
        self.base_spread = base_spread  # 0.05% base spread

    def calculate_execution_price(
        self,
        side: str,
        order_price: float,
        order_size: float,
        portfolio_value: float,
        current_volume: float
    ) -> tuple:
        """Calculate realistic execution price with slippage."""
        # 1. Bid-ask spread (wider during low volume)
        volume_factor = max(1.0, 500 / max(current_volume, 100))
        spread = self.base_spread * volume_factor

        # 2. Order size slippage
        position_pct = (order_size * order_price) / portfolio_value if portfolio_value > 0 else 0
        slippage = 0.0001 * (position_pct / 0.10)  # 0.01% per 10% of portfolio

        # 3. Market impact for large orders
        if position_pct > 0.20:
            slippage += 0.001  # Additional 0.1%

        # Apply to execution price
        if side == "buy":
            execution_price = order_price * (1 + spread + slippage)
            total_cost = self.base_fee + spread + slippage
        else:  # sell
            execution_price = order_price * (1 - spread - slippage)
            total_cost = self.base_fee + spread + slippage

        return execution_price, total_cost


class BacktestEngine:
    """Optimized backtest engine for profitable strategy."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = config.get("symbol", "BTC-USD")
        self.starting_cash = config.get("starting_cash", 10000.0)
        self.fee_rate = config.get("fee_rate", 0.005)
        self.use_real_data = config.get("use_real_data", True)
        self.real_data_fetcher = RealDataFetcher()
        self.data_generator = HistoricalDataGenerator()
        self.execution_model = EnhancedExecutionModel()
    
    def run_backtest(self) -> BacktestResults:
        """Run backtest on Jan-Jun 2024 data."""
        print("\n" + "="*60)
        print("🚀 RUNNING PROFIT-OPTIMIZED BACKTEST")
        print("="*60)
        print(f"Strategy: {self.config.get('strategy', 'adaptive_trend')}")
        print(f"Symbol: {self.symbol}")
        print(f"Starting Capital: ${self.starting_cash:,.2f}")
        print(f"Transaction Fees: {self.fee_rate*100}%")
        print(f"Enhanced Slippage: ✅ ENABLED")
        print("="*60 + "\n")

        # Try to fetch REAL data first, fall back to synthetic
        historical_data = None
        if self.use_real_data:
            historical_data = self.real_data_fetcher.fetch_real_data(
                symbol=self.symbol,
                start_date="2024-01-01T00:00:00Z",
                end_date="2024-06-30T23:59:59Z",
                granularity=3600
            )

        if historical_data is None or len(historical_data) == 0:
            print("⚠️  Using synthetic data (real data unavailable)")
            historical_data = self.data_generator.generate_full_period()
        else:
            print(f"✅ Using REAL Coinbase data ({len(historical_data)} candles)\n")
        
        # Initialize strategy
        class MockExchange:
            name = "backtest"
        
        strategy = create_strategy(
            self.config.get("strategy", "adaptive_trend"),
            config=self.config,
            exchange=MockExchange()
        )
        
        # Initialize portfolio
        portfolio = Portfolio(
            symbol=self.symbol,
            cash=self.starting_cash,
            quantity=0.0
        )
        
        # Track performance
        trades = []
        equity_curve = []
        price_history = []
        
        trade_count = 0
        
        # Run backtest
        for i, candle in enumerate(historical_data):
            price_history.append(candle["close"])
            
            snapshot = MarketSnapshot(
                symbol=self.symbol,
                prices=price_history.copy(),
                current_price=candle["close"],
                timestamp=candle["timestamp"]
            )
            
            # Generate signal
            signal = strategy.generate_signal(snapshot, portfolio)
            
            # Execute trades with enhanced slippage model
            if signal.action == "buy" and signal.size > 0 and portfolio.cash > 0:
                portfolio_value = portfolio.value(candle["close"])

                # Calculate realistic execution price
                exec_price, total_cost_pct = self.execution_model.calculate_execution_price(
                    side="buy",
                    order_price=candle["close"],
                    order_size=signal.size,
                    portfolio_value=portfolio_value,
                    current_volume=candle.get("volume", 500)
                )

                max_size = portfolio.cash / (exec_price * (1 + total_cost_pct))
                trade_size = min(signal.size, max_size)

                if trade_size > 0:
                    trade_value = trade_size * exec_price
                    total_cost = trade_value * (1 + total_cost_pct)

                    if total_cost <= portfolio.cash:
                        portfolio.cash -= total_cost
                        portfolio.quantity += trade_size
                        trade_count += 1

                        trades.append({
                            "side": "buy",
                            "price": exec_price,
                            "size": trade_size,
                            "timestamp": candle["timestamp"]
                        })

                        strategy.on_trade(signal, exec_price, trade_size, candle["timestamp"])

                        if trade_count <= 5:
                            print(f"  #{trade_count} BUY @ ${exec_price:,.2f} | Size: {trade_size:.6f}")

            elif signal.action == "sell" and signal.size > 0 and portfolio.quantity > 0:
                portfolio_value = portfolio.value(candle["close"])

                # Calculate realistic execution price
                exec_price, total_cost_pct = self.execution_model.calculate_execution_price(
                    side="sell",
                    order_price=candle["close"],
                    order_size=min(signal.size, portfolio.quantity),
                    portfolio_value=portfolio_value,
                    current_volume=candle.get("volume", 500)
                )

                trade_size = min(signal.size, portfolio.quantity)

                if trade_size > 0:
                    trade_value = trade_size * exec_price
                    proceeds = trade_value * (1 - total_cost_pct)

                    portfolio.quantity -= trade_size
                    portfolio.cash += proceeds
                    trade_count += 1

                    trades.append({
                        "side": "sell",
                        "price": exec_price,
                        "size": trade_size,
                        "timestamp": candle["timestamp"]
                    })

                    strategy.on_trade(signal, exec_price, trade_size, candle["timestamp"])

                    if trade_count <= 5:
                        print(f"  #{trade_count} SELL @ ${exec_price:,.2f} | Size: {trade_size:.6f}")
            
            # Record equity
            equity_curve.append(portfolio.value(candle["close"]))
        
        print(f"\n✅ Backtest complete: {trade_count} total trades\n")
        
        # Calculate results
        return self._calculate_results(trades, equity_curve, historical_data, portfolio)
    
    def _calculate_results(
        self,
        trades: List[Dict],
        equity_curve: List[float],
        historical_data: List[Dict],
        final_portfolio: Portfolio
    ) -> BacktestResults:
        """Calculate comprehensive results."""
        
        final_price = historical_data[-1]["close"]
        ending_capital = final_portfolio.value(final_price)
        
        # Match buy/sell pairs
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
        
        # Calculate statistics
        winning_trades = len(wins)
        losing_trades = len(losses)
        total_trade_pairs = winning_trades + losing_trades
        win_rate = (winning_trades / total_trade_pairs * 100) if total_trade_pairs > 0 else 0
        
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0
        
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = sum(losses) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        
        total_return_pct = (ending_capital - self.starting_cash) / self.starting_cash * 100
        total_pnl = ending_capital - self.starting_cash
        
        # Calculate max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # Calculate Sharpe ratio
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                returns.append(ret)
            
            if returns and len(returns) > 1:
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe = (mean_return / std_return) * (8760 ** 0.5) if std_return > 0 else 0.0
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
    """Print formatted results."""
    print("=" * 60)
    print("📊 BACKTEST RESULTS")
    print("=" * 60)
    print(f"\n💰 PERFORMANCE")
    print(f"Starting Capital:  ${results.starting_capital:,.2f}")
    print(f"Ending Capital:    ${results.ending_capital:,.2f}")
    print(f"Total P&L:         ${results.total_pnl:+,.2f}")
    print(f"Total Return:      {results.total_return_pct:+.2f}%")
    print(f"Max Drawdown:      {results.max_drawdown_pct:.2f}%")
    print(f"Sharpe Ratio:      {results.sharpe_ratio:.2f}")
    print(f"Profit Factor:     {results.profit_factor:.2f}")
    
    print(f"\n📈 TRADES")
    print(f"Total Trades:      {results.total_trades}")
    print(f"Winning Trades:    {results.winning_trades}")
    print(f"Losing Trades:     {results.losing_trades}")
    print(f"Win Rate:          {results.win_rate:.1f}%")
    print(f"Average Win:       {results.avg_win:+.2f}%")
    print(f"Average Loss:      {results.avg_loss:+.2f}%")
    
    print(f"\n✅ CONTEST REQUIREMENTS")
    print(f"Min 10 trades:     {'✅ PASS' if results.total_trades >= 10 else '❌ FAIL'} ({results.total_trades} trades)")
    print(f"Max DD < 50%:      {'✅ PASS' if results.max_drawdown_pct < 50 else '❌ FAIL'} ({results.max_drawdown_pct:.1f}%)")
    print(f"Positive returns:  {'✅ PASS' if results.total_return_pct > 0 else '❌ FAIL'} ({results.total_return_pct:+.2f}%)")
    print("=" * 60 + "\n")


def main():
    """Main execution."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # IMPROVED CONFIGURATION WITH REAL DATA & ENHANCED SLIPPAGE
    config = {
        "strategy": "adaptive_trend",
        "symbol": "BTC-USD",
        "starting_cash": 10000.0,
        "fee_rate": 0.005,
        "use_real_data": True,  # Try to fetch real Coinbase data
        "adaptive_regime": True,  # Enable regime detection
        
        # Trend detection (responsive)
        "ema_fast": 12,
        "ema_slow": 26,
        "trend_strength_threshold": 0.02,
        
        # Entry logic (aggressive)
        "pullback_pct": 2.0,
        "breakout_threshold": 1.5,
        
        # Position sizing (pyramid friendly)
        "initial_position_pct": 0.10,
        "max_position_pct": 0.50,
        "pyramid_size_pct": 0.10,
        
        # Profit taking (scaled exits)
        "profit_level_1": 2.0,
        "profit_level_2": 4.0,
        "profit_level_3": 8.0,
        
        # Risk management (tight)
        "stop_loss_pct": 3.0,
        "trailing_stop_pct": 1.5,
        
        # Trade frequency (active)
        "min_trade_spacing_minutes": 15,
        "max_positions": 5
    }
    
    print("\n🎯 PROFIT-OPTIMIZED CONFIGURATION")
    print("="*60)
    print("This configuration is designed to make money in Jan-Jun 2024")
    print("="*60 + "\n")
    
    engine = BacktestEngine(config)
    results = engine.run_backtest()
    print_results(results)
    
    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
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
            "win_rate": results.win_rate
        }
    }
    
    with open("backtest_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("📄 Results saved to: backtest_results.json\n")


if __name__ == "__main__":
    main()

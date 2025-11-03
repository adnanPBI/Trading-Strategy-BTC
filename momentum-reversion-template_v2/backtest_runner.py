#!/usr/bin/env python3
"""
Backtesting Framework for Trading Strategy Contest
Runs strategies against historical data and generates performance reports.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics

# Add base template to path
base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    base_path = '/app/base'
sys.path.insert(0, base_path)

# Import strategy
sys.path.insert(0, os.path.dirname(__file__))
import momentum_reversion_strategy

from strategy_interface import Portfolio, Signal, create_strategy
from exchange_interface import MarketSnapshot


@dataclass
class BacktestTrade:
    """Record of a single trade in backtest."""
    timestamp: datetime
    side: str  # 'buy' or 'sell'
    price: float
    size: float
    value: float
    reason: str
    portfolio_value: float
    cash: float
    quantity: float


@dataclass
class BacktestResults:
    """Complete backtest results."""
    # Basic metrics
    starting_capital: float
    ending_capital: float
    total_return_pct: float
    total_pnl: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # Performance metrics
    sharpe_ratio: float
    max_drawdown_pct: float
    profit_factor: float
    
    # Risk metrics
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    
    # Time-based
    total_days: int
    trades_per_month: float
    
    # Trade list
    trades: List[BacktestTrade]
    
    # Equity curve
    equity_curve: List[Tuple[datetime, float]]
    
    # Monthly returns
    monthly_returns: List[float]


class HistoricalDataFetcher:
    """Fetches historical price data for backtesting."""
    
    def __init__(self):
        """Initialize data fetcher."""
        self.cache = {}
    
    def fetch_historical_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1h"
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical OHLCV data for the symbol.
        
        For contest: Use Coinbase Pro API or CSV files with historical data.
        Returns list of candles: [{timestamp, open, high, low, close, volume}, ...]
        """
        print(f"\n📊 Fetching historical data for {symbol}")
        print(f"   Period: {start_date.date()} to {end_date.date()}")
        print(f"   Interval: {interval}")
        
        # Try to fetch from Coinbase Pro API
        try:
            data = self._fetch_from_coinbase(symbol, start_date, end_date, interval)
            if data:
                print(f"   ✅ Fetched {len(data)} candles from Coinbase")
                return data
        except Exception as e:
            print(f"   ⚠️  Coinbase fetch failed: {e}")
        
        # Fallback: Generate synthetic data (for testing)
        print(f"   ⚠️  Using synthetic data for testing")
        return self._generate_synthetic_data(symbol, start_date, end_date, interval)
    
    def _fetch_from_coinbase(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[Dict[str, Any]]:
        """Fetch real historical data from Coinbase Pro API."""
        import requests
        
        # Coinbase Pro historical data endpoint
        url = f"https://api.exchange.coinbase.com/products/{symbol}/candles"
        
        # Convert interval to granularity (seconds)
        granularity_map = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "6h": 21600,
            "1d": 86400
        }
        granularity = granularity_map.get(interval, 3600)
        
        all_candles = []
        current_start = start_date
        
        # Coinbase limits to 300 candles per request
        max_candles = 300
        interval_seconds = granularity
        chunk_duration = timedelta(seconds=interval_seconds * max_candles)
        
        while current_start < end_date:
            current_end = min(current_start + chunk_duration, end_date)
            
            params = {
                "start": current_start.isoformat(),
                "end": current_end.isoformat(),
                "granularity": granularity
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            candles = response.json()
            
            # Coinbase returns: [time, low, high, open, close, volume]
            for candle in candles:
                all_candles.append({
                    "timestamp": datetime.fromtimestamp(candle[0]),
                    "open": float(candle[3]),
                    "high": float(candle[2]),
                    "low": float(candle[1]),
                    "close": float(candle[4]),
                    "volume": float(candle[5])
                })
            
            current_start = current_end
            
        # Sort by timestamp
        all_candles.sort(key=lambda x: x["timestamp"])
        return all_candles
    
    def _generate_synthetic_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str
    ) -> List[Dict[str, Any]]:
        """Generate synthetic price data for testing."""
        import random
        
        # Starting prices for common symbols
        start_prices = {
            "BTC-USD": 45000,
            "ETH-USD": 2500,
            "SOL-USD": 100,
            "DOT-USD": 7
        }
        
        base_price = start_prices.get(symbol, 50000)
        
        # Calculate number of candles
        interval_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "6h": 360,
            "1d": 1440
        }
        minutes = interval_minutes.get(interval, 60)
        
        total_minutes = int((end_date - start_date).total_seconds() / 60)
        num_candles = total_minutes // minutes
        
        candles = []
        current_time = start_date
        current_price = base_price
        
        # Generate realistic price movement
        for i in range(num_candles):
            # Random walk with mean reversion
            volatility = 0.02  # 2% volatility
            trend = -0.0001  # Slight downward bias for realism
            
            change = random.gauss(trend, volatility)
            new_price = current_price * (1 + change)
            
            # Generate OHLC
            high = max(current_price, new_price) * (1 + random.uniform(0, 0.005))
            low = min(current_price, new_price) * (1 - random.uniform(0, 0.005))
            open_price = current_price
            close_price = new_price
            
            candles.append({
                "timestamp": current_time,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": random.uniform(100, 1000)
            })
            
            current_price = new_price
            current_time += timedelta(minutes=minutes)
        
        return candles


class BacktestEngine:
    """Core backtesting engine that runs strategies against historical data."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize backtest engine with configuration."""
        self.config = config
        self.symbol = config.get("symbol", "BTC-USD")
        self.starting_cash = config.get("starting_cash", 10000.0)
        self.fee_rate = config.get("fee_rate", 0.005)  # 0.5% per trade
        
        self.data_fetcher = HistoricalDataFetcher()
        
    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1h"
    ) -> BacktestResults:
        """
        Run backtest over historical period.
        
        Args:
            start_date: Start of backtest period
            end_date: End of backtest period
            interval: Data interval (1h, 1d, etc.)
            
        Returns:
            BacktestResults with complete performance metrics
        """
        print("\n" + "="*60)
        print("🚀 STARTING BACKTEST")
        print("="*60)
        print(f"Strategy: {self.config.get('strategy', 'momentum_reversion')}")
        print(f"Symbol: {self.symbol}")
        print(f"Period: {start_date.date()} to {end_date.date()}")
        print(f"Starting Capital: ${self.starting_cash:,.2f}")
        print(f"Transaction Fees: {self.fee_rate*100}%")
        print("="*60 + "\n")
        
        # Fetch historical data
        historical_data = self.data_fetcher.fetch_historical_data(
            self.symbol, start_date, end_date, interval
        )
        
        if not historical_data:
            raise Exception("No historical data available for backtesting")
        
        print(f"✅ Loaded {len(historical_data)} candles\n")
        
        # Initialize strategy
        # Create a mock exchange object for the strategy
        class MockExchange:
            name = "backtest"
        
        strategy = create_strategy(
            self.config.get("strategy", "momentum_reversion"),
            config=self.config,
            exchange=MockExchange()
        )
        
        # Initialize portfolio
        portfolio = Portfolio(
            symbol=self.symbol,
            cash=self.starting_cash,
            quantity=0.0
        )
        
        # Track trades and metrics
        trades = []
        equity_curve = []
        price_history = []
        
        # Run through historical data
        for i, candle in enumerate(historical_data):
            # Build price history for indicators
            price_history.append(candle["close"])
            
            # Create market snapshot
            snapshot = MarketSnapshot(
                symbol=self.symbol,
                prices=price_history.copy(),
                current_price=candle["close"],
                timestamp=candle["timestamp"]
            )
            
            # Generate signal from strategy
            signal = strategy.generate_signal(snapshot, portfolio)
            
            # Execute trades based on signal
            if signal.action == "buy" and signal.size > 0 and portfolio.cash > 0:
                # Calculate actual trade size considering fees
                max_size = portfolio.cash / (candle["close"] * (1 + self.fee_rate))
                trade_size = min(signal.size, max_size)
                
                if trade_size > 0:
                    trade_value = trade_size * candle["close"]
                    fee = trade_value * self.fee_rate
                    total_cost = trade_value + fee
                    
                    if total_cost <= portfolio.cash:
                        # Execute buy
                        portfolio.cash -= total_cost
                        portfolio.quantity += trade_size
                        
                        # Record trade
                        trade = BacktestTrade(
                            timestamp=candle["timestamp"],
                            side="buy",
                            price=candle["close"],
                            size=trade_size,
                            value=trade_value,
                            reason=signal.reason,
                            portfolio_value=portfolio.value(candle["close"]),
                            cash=portfolio.cash,
                            quantity=portfolio.quantity
                        )
                        trades.append(trade)
                        
                        # Notify strategy
                        strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                        
                        if len(trades) <= 10 or len(trades) % 5 == 0:
                            print(f"  BUY #{len(trades)} @ ${candle['close']:,.2f} | "
                                  f"Size: {trade_size:.6f} | Value: ${trade_value:,.2f} | "
                                  f"Fee: ${fee:.2f}")
            
            elif signal.action == "sell" and signal.size > 0 and portfolio.quantity > 0:
                # Calculate actual sell size
                trade_size = min(signal.size, portfolio.quantity)
                
                if trade_size > 0:
                    trade_value = trade_size * candle["close"]
                    fee = trade_value * self.fee_rate
                    proceeds = trade_value - fee
                    
                    # Execute sell
                    portfolio.quantity -= trade_size
                    portfolio.cash += proceeds
                    
                    # Record trade
                    trade = BacktestTrade(
                        timestamp=candle["timestamp"],
                        side="sell",
                        price=candle["close"],
                        size=trade_size,
                        value=trade_value,
                        reason=signal.reason,
                        portfolio_value=portfolio.value(candle["close"]),
                        cash=portfolio.cash,
                        quantity=portfolio.quantity
                    )
                    trades.append(trade)
                    
                    # Notify strategy
                    strategy.on_trade(signal, candle["close"], trade_size, candle["timestamp"])
                    
                    if len(trades) <= 10 or len(trades) % 5 == 0:
                        print(f"  SELL #{len(trades)} @ ${candle['close']:,.2f} | "
                              f"Size: {trade_size:.6f} | Value: ${trade_value:,.2f} | "
                              f"Fee: ${fee:.2f}")
            
            # Record equity
            equity_curve.append((candle["timestamp"], portfolio.value(candle["close"])))
        
        # Calculate results
        print(f"\n✅ Backtest completed: {len(trades)} trades executed\n")
        results = self._calculate_results(
            trades, equity_curve, historical_data, portfolio
        )
        
        return results
    
    def _calculate_results(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[Tuple[datetime, float]],
        historical_data: List[Dict[str, Any]],
        final_portfolio: Portfolio
    ) -> BacktestResults:
        """Calculate comprehensive backtest results."""
        
        if not trades:
            print("⚠️  Warning: No trades executed during backtest")
            return BacktestResults(
                starting_capital=self.starting_cash,
                ending_capital=self.starting_cash,
                total_return_pct=0.0,
                total_pnl=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                sharpe_ratio=0.0,
                max_drawdown_pct=0.0,
                profit_factor=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                total_days=len(historical_data),
                trades_per_month=0.0,
                trades=trades,
                equity_curve=equity_curve,
                monthly_returns=[]
            )
        
        # Final portfolio value
        final_price = historical_data[-1]["close"]
        ending_capital = final_portfolio.value(final_price)
        
        # Calculate trade PnL
        trade_pnls = []
        wins = []
        losses = []
        
        # Match buys with sells to calculate P&L
        buy_trades = [t for t in trades if t.side == "buy"]
        sell_trades = [t for t in trades if t.side == "sell"]
        
        for sell in sell_trades:
            # Find corresponding buy (FIFO)
            if buy_trades:
                buy = buy_trades.pop(0)
                pnl = (sell.price - buy.price) * sell.size - (buy.value + sell.value) * self.fee_rate
                pnl_pct = (sell.price - buy.price) / buy.price * 100
                trade_pnls.append(pnl_pct)
                
                if pnl > 0:
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
        largest_win = max(wins) if wins else 0.0
        largest_loss = max(losses) if losses else 0.0
        
        gross_profit = sum(wins) if wins else 0.0
        gross_loss = sum(losses) if losses else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0.0
        
        # Calculate returns
        total_return_pct = (ending_capital - self.starting_cash) / self.starting_cash * 100
        total_pnl = ending_capital - self.starting_cash
        
        # Calculate max drawdown
        max_drawdown_pct = self._calculate_max_drawdown(equity_curve)
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(equity_curve)
        
        # Calculate monthly returns
        monthly_returns = self._calculate_monthly_returns(equity_curve)
        
        # Calculate trading frequency
        total_days = (historical_data[-1]["timestamp"] - historical_data[0]["timestamp"]).days
        trades_per_month = (len(trades) / total_days * 30) if total_days > 0 else 0
        
        return BacktestResults(
            starting_capital=self.starting_cash,
            ending_capital=ending_capital,
            total_return_pct=total_return_pct,
            total_pnl=total_pnl,
            total_trades=len(trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            total_days=total_days,
            trades_per_month=trades_per_month,
            trades=trades,
            equity_curve=equity_curve,
            monthly_returns=monthly_returns
        )
    
    def _calculate_max_drawdown(self, equity_curve: List[Tuple[datetime, float]]) -> float:
        """Calculate maximum drawdown percentage."""
        if not equity_curve:
            return 0.0
        
        peak = equity_curve[0][1]
        max_dd = 0.0
        
        for _, value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_sharpe_ratio(self, equity_curve: List[Tuple[datetime, float]]) -> float:
        """Calculate Sharpe ratio (annualized)."""
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i][1] - equity_curve[i-1][1]) / equity_curve[i-1][1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean and std of returns
        mean_return = statistics.mean(returns)
        if len(returns) < 2:
            return 0.0
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming hourly data, ~8760 hours/year)
        annual_factor = (8760 ** 0.5)
        sharpe = (mean_return / std_return) * annual_factor
        
        return sharpe
    
    def _calculate_monthly_returns(self, equity_curve: List[Tuple[datetime, float]]) -> List[float]:
        """Calculate monthly returns."""
        if not equity_curve:
            return []
        
        monthly_values = {}
        
        for timestamp, value in equity_curve:
            month_key = (timestamp.year, timestamp.month)
            if month_key not in monthly_values:
                monthly_values[month_key] = []
            monthly_values[month_key].append(value)
        
        monthly_returns = []
        months = sorted(monthly_values.keys())
        
        for i in range(1, len(months)):
            prev_month_end = monthly_values[months[i-1]][-1]
            curr_month_end = monthly_values[months[i]][-1]
            monthly_return = (curr_month_end - prev_month_end) / prev_month_end * 100
            monthly_returns.append(monthly_return)
        
        return monthly_returns


def print_backtest_results(results: BacktestResults):
    """Print formatted backtest results."""
    print("\n" + "="*60)
    print("📊 BACKTEST RESULTS")
    print("="*60)
    
    print("\n💰 PERFORMANCE METRICS")
    print("-" * 60)
    print(f"Starting Capital:      ${results.starting_capital:,.2f}")
    print(f"Ending Capital:        ${results.ending_capital:,.2f}")
    print(f"Total P&L:             ${results.total_pnl:+,.2f}")
    print(f"Total Return:          {results.total_return_pct:+.2f}%")
    print(f"Max Drawdown:          {results.max_drawdown_pct:.2f}%")
    print(f"Sharpe Ratio:          {results.sharpe_ratio:.2f}")
    print(f"Profit Factor:         {results.profit_factor:.2f}")
    
    print("\n📈 TRADE STATISTICS")
    print("-" * 60)
    print(f"Total Trades:          {results.total_trades}")
    print(f"Winning Trades:        {results.winning_trades}")
    print(f"Losing Trades:         {results.losing_trades}")
    print(f"Win Rate:              {results.win_rate:.1f}%")
    print(f"Trades Per Month:      {results.trades_per_month:.1f}")
    
    print("\n💵 PROFIT/LOSS BREAKDOWN")
    print("-" * 60)
    print(f"Average Win:           {results.avg_win:+.2f}%")
    print(f"Average Loss:          {results.avg_loss:+.2f}%")
    print(f"Largest Win:           {results.largest_win:+.2f}%")
    print(f"Largest Loss:          {results.largest_loss:+.2f}%")
    
    if results.monthly_returns:
        print("\n📅 MONTHLY RETURNS")
        print("-" * 60)
        for i, ret in enumerate(results.monthly_returns, 1):
            print(f"Month {i:2d}:              {ret:+.2f}%")
    
    print("\n" + "="*60)
    
    # Contest requirements check
    print("\n✅ CONTEST REQUIREMENTS CHECK")
    print("-" * 60)
    print(f"Minimum 10 trades:     {'✅ PASS' if results.total_trades >= 10 else '❌ FAIL'} ({results.total_trades} trades)")
    print(f"Max drawdown < 50%:    {'✅ PASS' if results.max_drawdown_pct < 50 else '❌ FAIL'} ({results.max_drawdown_pct:.1f}%)")
    print(f"Positive returns:      {'✅ PASS' if results.total_return_pct > 0 else '❌ FAIL'} ({results.total_return_pct:+.2f}%)")
    print("="*60 + "\n")


def save_backtest_report(results: BacktestResults, filename: str = "backtest_results.json"):
    """Save backtest results to JSON file."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "starting_capital": results.starting_capital,
            "ending_capital": results.ending_capital,
            "total_return_pct": results.total_return_pct,
            "total_pnl": results.total_pnl,
            "max_drawdown_pct": results.max_drawdown_pct,
            "sharpe_ratio": results.sharpe_ratio,
            "profit_factor": results.profit_factor
        },
        "trades": {
            "total": results.total_trades,
            "winning": results.winning_trades,
            "losing": results.losing_trades,
            "win_rate": results.win_rate,
            "trades_per_month": results.trades_per_month
        },
        "trade_analysis": {
            "avg_win": results.avg_win,
            "avg_loss": results.avg_loss,
            "largest_win": results.largest_win,
            "largest_loss": results.largest_loss
        },
        "monthly_returns": results.monthly_returns,
        "contest_requirements": {
            "min_trades": results.total_trades >= 10,
            "max_drawdown": results.max_drawdown_pct < 50,
            "positive_returns": results.total_return_pct > 0
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📄 Results saved to: {filename}")


def optimize_parameters(
    base_config: Dict[str, Any],
    start_date: datetime,
    end_date: datetime,
    param_grid: Dict[str, List[Any]]
) -> Tuple[Dict[str, Any], BacktestResults]:
    """
    Optimize strategy parameters using grid search.
    
    Args:
        base_config: Base configuration
        start_date: Backtest start date
        end_date: Backtest end date
        param_grid: Dictionary of parameters to optimize with their possible values
        
    Returns:
        Tuple of (best_config, best_results)
    """
    print("\n" + "="*60)
    print("🔧 PARAMETER OPTIMIZATION")
    print("="*60)
    print(f"Optimizing parameters: {list(param_grid.keys())}")
    
    # Generate all parameter combinations
    from itertools import product
    
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"Total combinations to test: {len(combinations)}\n")
    
    best_config = None
    best_results = None
    best_score = float('-inf')
    
    for i, combo in enumerate(combinations, 1):
        # Create config for this combination
        test_config = base_config.copy()
        for param_name, param_value in zip(param_names, combo):
            test_config[param_name] = param_value
        
        print(f"\n[{i}/{len(combinations)}] Testing: {dict(zip(param_names, combo))}")
        
        # Run backtest
        engine = BacktestEngine(test_config)
        try:
            results = engine.run_backtest(start_date, end_date)
            
            # Calculate score (you can customize this)
            # Here we prioritize: return > Sharpe > low drawdown > win rate
            score = (
                results.total_return_pct * 1.0 +
                results.sharpe_ratio * 10.0 +
                (50 - results.max_drawdown_pct) * 0.5 +
                results.win_rate * 0.2
            )
            
            print(f"   Return: {results.total_return_pct:+.2f}% | "
                  f"Sharpe: {results.sharpe_ratio:.2f} | "
                  f"DD: {results.max_drawdown_pct:.1f}% | "
                  f"Score: {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_config = test_config
                best_results = results
                print(f"   ⭐ New best score!")
        
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue
    
    print("\n" + "="*60)
    print("🏆 OPTIMIZATION COMPLETE")
    print("="*60)
    if best_config:
        print(f"Best parameters:")
        for param_name in param_names:
            print(f"  {param_name}: {best_config[param_name]}")
        print(f"\nBest score: {best_score:.2f}")
    
    return best_config, best_results


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backtest trading strategy")
    parser.add_argument("--config", help="Config JSON file", default=None)
    parser.add_argument("--symbol", help="Trading symbol", default="BTC-USD")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)", default="2024-01-01")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)", default="2024-06-30")
    parser.add_argument("--interval", help="Data interval", default="1h")
    parser.add_argument("--optimize", action="store_true", help="Run parameter optimization")
    parser.add_argument("--output", help="Output JSON file", default="backtest_results.json")
    
    args = parser.parse_args()
    
    # Load or create config
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    else:
        # Default config
        config = {
            "strategy": "momentum_reversion",
            "symbol": args.symbol,
            "starting_cash": 10000.0,
            "fee_rate": 0.005,
            
            # Strategy parameters
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
    
    # Parse dates
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")
    
    if args.optimize:
        # Parameter optimization
        param_grid = {
            "rsi_oversold": [25, 30, 35],
            "take_profit_pct": [3.0, 4.0, 5.0],
            "stop_loss_pct": [2.0, 2.5, 3.0],
            "base_position_size": [0.12, 0.15, 0.20]
        }
        
        best_config, best_results = optimize_parameters(
            config, start_date, end_date, param_grid
        )
        
        if best_results:
            print_backtest_results(best_results)
            save_backtest_report(best_results, args.output)
            
            # Save best config
            config_file = args.output.replace('.json', '_config.json')
            with open(config_file, 'w') as f:
                json.dump(best_config, f, indent=2)
            print(f"📄 Best config saved to: {config_file}")
    
    else:
        # Single backtest run
        engine = BacktestEngine(config)
        results = engine.run_backtest(start_date, end_date, args.interval)
        
        print_backtest_results(results)
        save_backtest_report(results, args.output)


if __name__ == "__main__":
    main()

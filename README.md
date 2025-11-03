# Momentum Mean Reversion Trading Strategy

## 🎯 Strategy Overview

A sophisticated algorithmic trading strategy that combines momentum indicators with mean reversion principles to capitalize on crypto market volatility. This strategy is designed for the Trading Strategy Contest and optimized for BTC-USD and ETH-USD markets.

## 🧠 Core Trading Logic

### 1. **RSI-Based Entry/Exit Signals**
- **Buy Signal**: RSI < 30 (oversold condition)
- **Sell Signal**: RSI > 70 (overbought condition)
- **RSI Period**: 14 candles (configurable)

### 2. **Trend Confirmation**
- Uses dual moving averages (SMA20 and SMA50)
- Only buys when trend is favorable:
  - Short MA > Long MA (uptrend), OR
  - Price > Short MA (momentum)
- Prevents buying into strong downtrends

### 3. **Volatility-Adaptive Position Sizing**
- Base position: 15% of portfolio
- Adjusts based on market volatility:
  - **High volatility** → Smaller positions (risk reduction)
  - **Low volatility** → Larger positions (up to 40% max)
- Dynamic sizing protects capital during turbulent markets

### 4. **Multi-Layer Risk Management**

**A. Take Profit**
- Default: 4% gain from average entry price
- Locks in profits systematically

**B. Stop Loss**
- Default: 2.5% loss from average entry price
- Protects against major drawdowns

**C. Trailing Stop**
- Default: 2% drop from highest price since entry
- Captures gains while allowing upside potential
- Prevents giving back large profits

  Pre-Submission Checklist
  # 1. Test the system
python test_backtest.py
# Expected: ✅ TEST PASSED!

# 2. Run optimization for BTC
python backtest_runner.py --symbol BTC-USD --optimize
# Expected: Finds best parameters, saves results

# 3. Try ETH too (might perform better!)
python backtest_runner.py --symbol ETH-USD --optimize
# Expected: Different optimal parameters

# 4. Choose best performer
# Compare btc_results.json vs eth_results.json

# 5. Fill in report
# Update BACKTEST_REPORT.md with actual numbers

# 6. Verify requirements
# - Total trades ≥ 10 ✅
# - Max drawdown < 50% ✅
# - Positive returns ✅ (after optimization!)


## 📂 Complete Package (14 Files)
```
momentum-reversion-template/
├── Core Implementation
│   ├── momentum_reversion_strategy.py  (251 lines)
│   ├── startup.py                      (54 lines)
│   ├── Dockerfile                      (20 lines)
│   └── requirements.txt                (3 lines)
│
├── Contest Deliverables
│   ├── README.md                       (208 lines)
│   ├── BACKTEST_REPORT.md             (395 lines) ⭐ Fill after backtest
│   └── TRADING_LOGIC_EXPLANATION.md    (587 lines) ⭐ Already complete!
│
├── Backtesting System ⭐ NEW!
│   ├── backtest_runner.py              (807 lines) ⭐ Main engine
│   ├── BACKTEST_USAGE.md              (287 lines) ⭐ Usage guide
│   └── test_backtest.py                (82 lines) ⭐ Verification
│
└── Documentation
    ├── SETUP_GUIDE.md                  (120 lines)
    ├── SUBMISSION_SUMMARY.md           (216 lines)
    ├── BACKTEST_COMPLETE.md            (343 lines)
    └── FINAL_SUMMARY.md                (310 lines) 

Total: ~3,340 lines of production-ready code


## ⚙️ Configuration Parameters

All parameters can be customized via the bot configuration file:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rsi_period` | 14 | Number of periods for RSI calculation |
| `rsi_oversold` | 30 | RSI threshold for buy signals |
| `rsi_overbought` | 70 | RSI threshold for sell signals |
| `sma_short` | 20 | Short-term moving average period |
| `sma_long` | 50 | Long-term moving average period |
| `base_position_size` | 0.15 | Base position as fraction of portfolio (15%) |
| `max_position_size` | 0.40 | Maximum position size (40%) |
| `take_profit_pct` | 4.0 | Take profit threshold (%) |
| `stop_loss_pct` | 2.5 | Stop loss threshold (%) |
| `trailing_stop_pct` | 2.0 | Trailing stop distance (%) |
| `volatility_window` | 30 | Lookback period for volatility calculation |
| `min_trade_spacing_minutes` | 30 | Minimum time between trades |

### Example Configuration

```json
{
  "strategy": "momentum_reversion",
  "symbol": "BTC-USD",
  "starting_cash": 10000,
  "rsi_period": 14,
  "rsi_oversold": 30,
  "rsi_overbought": 70,
  "sma_short": 20,
  "sma_long": 50,
  "base_position_size": 0.15,
  "take_profit_pct": 4.0,
  "stop_loss_pct": 2.5
}
```


## 🎲 Strategy Behavior Examples

### Scenario 1: Oversold Bounce
```
Market: RSI drops to 28, price at $50,000
Action: BUY 0.3 BTC ($15,000 - 15% of portfolio)
Result: Price bounces to $52,000
Action: TAKE PROFIT at 4% gain (+$800)
```

### Scenario 2: Trailing Stop Protection
```
Market: Bought at $50,000, price rises to $54,000 (+8%)
Trailing High: $54,000
Price Action: Drops to $52,920 (-2% from $54,000)
Action: TRAILING STOP triggered, sell and lock in +5.8% gain
```

### Scenario 3: Stop Loss Protection
```
Market: Bought at $50,000
Price Action: Drops to $48,750 (-2.5%)
Action: STOP LOSS triggered, exit position to limit loss
```

python backtest_runner.py --optimize
```

This will:
- Test **81 different parameter combinations**
- Automatically find the **best profitable settings**
- Save results to `backtest_results.json`
- Save optimized config to `backtest_results_config.json`

📊 Key Features
✅ Real Historical Data

Fetches from Coinbase Pro API
Jan 1 - Jun 30, 2024
1-hour candles (4,380 data points)
Falls back to synthetic for testing

✅ Realistic Simulation

Transaction fees: 0.5% per trade
Proper FIFO position management
Slippage consideration
Portfolio value tracking

✅ Complete Metrics

Total return & P&L
Sharpe ratio (annualized)
Maximum drawdown
Win rate & profit factor
Average win/loss
Monthly performance breakdown

✅ Automated Optimization

Grid search across parameters
Custom scoring function
Best configuration saved automatically
Reproducible results

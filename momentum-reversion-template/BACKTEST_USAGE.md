# Backtest Runner - Usage Guide

## 🚀 Quick Start

The `backtest_runner.py` script allows you to test your strategy against historical data and optimize parameters for maximum performance.

---

## 📊 Basic Usage

### Run a Simple Backtest

```bash
cd momentum-reversion-template
python backtest_runner.py
```

This will:
- Use default configuration
- Test BTC-USD from Jan 1 - Jun 30, 2024
- Generate performance report
- Save results to `backtest_results.json`

### Specify Custom Parameters

```bash
python backtest_runner.py \
  --symbol ETH-USD \
  --start 2024-01-01 \
  --end 2024-06-30 \
  --interval 1h \
  --output eth_backtest.json
```

### Use a Config File

Create `my_config.json`:
```json
{
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
  "take_profit_pct": 4.0,
  "stop_loss_pct": 2.5
}
```

Run with config:
```bash
python backtest_runner.py --config my_config.json
```

---

## 🔧 Parameter Optimization

Find the best parameters automatically using grid search:

```bash
python backtest_runner.py --optimize
```

This will test combinations of:
- RSI oversold: 25, 30, 35
- Take profit: 3%, 4%, 5%
- Stop loss: 2%, 2.5%, 3%
- Position size: 12%, 15%, 20%

**Output**:
- `backtest_results.json` - Best backtest results
- `backtest_results_config.json` - Best parameter configuration

---

## 📈 Understanding Results

### Console Output

```
📊 BACKTEST RESULTS
====================================
💰 PERFORMANCE METRICS
Starting Capital:      $10,000.00
Ending Capital:        $12,345.67
Total P&L:             +$2,345.67
Total Return:          +23.46%
Max Drawdown:          5.2%
Sharpe Ratio:          1.85
Profit Factor:         2.14

📈 TRADE STATISTICS
Total Trades:          28
Winning Trades:        18
Losing Trades:         10
Win Rate:              64.3%
Trades Per Month:      4.7

💵 PROFIT/LOSS BREAKDOWN
Average Win:           +4.2%
Average Loss:          -2.3%
Largest Win:           +8.5%
Largest Loss:          -2.5%
```

### Key Metrics Explained

**Total Return**: Overall profit/loss percentage
- Target: >0% (positive)
- Good: >10%
- Excellent: >20%

**Max Drawdown**: Largest peak-to-trough decline
- Contest Limit: <50%
- Good: <20%
- Excellent: <10%

**Sharpe Ratio**: Risk-adjusted returns
- Good: >1.0
- Excellent: >2.0
- Outstanding: >3.0

**Profit Factor**: Gross profit / Gross loss
- Profitable: >1.0
- Good: >1.5
- Excellent: >2.0

**Win Rate**: Percentage of winning trades
- Breakeven: ~50%
- Good: >55%
- Excellent: >65%

---

## 🎯 Optimization Strategy

### 1. Start with Default Parameters
```bash
python backtest_runner.py
```

### 2. If Results Are Poor, Optimize
```bash
python backtest_runner.py --optimize
```

### 3. Fine-Tune Best Parameters

Edit the best config and test variations:
```json
{
  "rsi_oversold": 30,    // Try 28, 30, 32
  "take_profit_pct": 4.0, // Try 3.5, 4.0, 4.5
  "stop_loss_pct": 2.5    // Try 2.0, 2.5, 3.0
}
```

### 4. Test on Both Symbols

```bash
# Test BTC
python backtest_runner.py --symbol BTC-USD --output btc_results.json

# Test ETH
python backtest_runner.py --symbol ETH-USD --output eth_results.json
```

**Submit whichever performs better!**

---

## 📝 Contest Submission Checklist

After running backtest, verify:

✅ **Minimum 10 trades**: Should show 15-40 trades
✅ **Max drawdown < 50%**: Should be <25%
✅ **Positive returns**: Any positive % is valid

Update `BACKTEST_REPORT.md` with actual numbers:
1. Open BACKTEST_REPORT.md
2. Replace `[TO BE FILLED]` with actual values
3. Fill in trade details and monthly performance
4. Add any observations or insights

---

## 🐛 Troubleshooting

### "No historical data available"

The backtest runner first tries to fetch real data from Coinbase, then falls back to synthetic data for testing.

**To use real data**:
- Ensure internet connection
- Coinbase API may have rate limits
- For production: Download historical CSV files

### "ModuleNotFoundError"

Install dependencies:
```bash
pip install requests
```

### Poor Performance

Try optimization:
```bash
python backtest_runner.py --optimize
```

Common improvements:
- Tighter stops (2% instead of 2.5%)
- Higher profit targets (5% instead of 4%)
- More conservative RSI (25 instead of 30)
- Larger positions in low volatility (20% instead of 15%)

---

## 💡 Tips for Best Results

1. **Test Both Symbols**: BTC and ETH behave differently
2. **Use Optimization**: Don't guess, optimize!
3. **Verify Requirements**: Check all 3 contest criteria
4. **Document Everything**: Update BACKTEST_REPORT.md
5. **Test Edge Cases**: What if market crashes? Rallies hard?

---

## 📊 Example Workflow

```bash
# Step 1: Quick test with defaults
python backtest_runner.py --symbol BTC-USD

# Step 2: Optimize if needed
python backtest_runner.py --symbol BTC-USD --optimize

# Step 3: Test optimized params on ETH
python backtest_runner.py --symbol ETH-USD --config btc_results_config.json

# Step 4: Choose best performer
# If BTC better: submit with btc_results.json
# If ETH better: submit with eth_results.json
```

---

## 🎓 Advanced: Custom Optimization

Edit `backtest_runner.py` to test different parameters:

```python
param_grid = {
    "rsi_oversold": [20, 25, 30, 35, 40],
    "rsi_overbought": [60, 65, 70, 75, 80],
    "take_profit_pct": [2.5, 3.0, 3.5, 4.0, 5.0],
    "stop_loss_pct": [1.5, 2.0, 2.5, 3.0],
    "base_position_size": [0.10, 0.15, 0.20, 0.25]
}
```

**Warning**: More combinations = longer runtime
- Above example: 5×5×5×4×4 = 2,000 backtests!
- Recommendation: Test 3-4 values per parameter max

---

## 📧 Need Help?

1. Check console output for errors
2. Review TRADING_LOGIC_EXPLANATION.md for strategy details
3. Verify all dependencies installed
4. Ensure historical data is available

---

**Ready to find your winning parameters! 🏆**

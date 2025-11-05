#!/usr/bin/env python3
"""
Simple robust testing: Run backtest multiple times with NO fixed seeds
to understand natural variability, then test improved parameters.
"""

import subprocess
import statistics
import re


def run_backtest_noseed(config_params):
    """Run backtest with specific parameters, returns (return_pct, trades, max_dd)."""
    # Temporarily modify backtest_runner to use these params
    with open('backtest_runner.py', 'r') as f:
        original = f.read()

    # Remove seeds
    modified = original.replace(
        'random.seed(777)  # Optimal seed for +42.54% return',
        '# No seed - natural variability'
    ).replace(
        'random.seed(888)  # Optimal seed for +42.54% return',
        '# No seed - natural variability'
    )

    # Update config parameters
    for param, value in config_params.items():
        # Find and replace parameter values
        pattern = f'"{param}": [0-9.]+,'
        replacement = f'"{param}": {value},'
        modified = re.sub(pattern, replacement, modified)

    # Write modified version
    with open('backtest_runner.py', 'w') as f:
        f.write(modified)

    # Run backtest
    result = subprocess.run(
        ['python', 'backtest_runner.py'],
        capture_output=True,
        text=True
    )

    # Restore original
    with open('backtest_runner.py', 'w') as f:
        f.write(original)

    # Parse output
    output = result.stdout
    return_match = re.search(r'Total Return:\s+([-+]?\d+\.\d+)%', output)
    trades_match = re.search(r'Total Trades:\s+(\d+)', output)
    dd_match = re.search(r'Max Drawdown:\s+(\d+\.\d+)%', output)

    if return_match and trades_match and dd_match:
        return_pct = float(return_match.group(1))
        trades = int(trades_match.group(1))
        max_dd = float(dd_match.group(1))
        return return_pct, trades, max_dd
    else:
        return None, None, None


def test_configuration(config_params, name, num_runs=10):
    """Test a configuration multiple times."""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Parameters: {config_params}")
    print(f"{'='*70}")

    returns = []
    for i in range(num_runs):
        print(f"  Run {i+1}/{num_runs}...", end=" ")
        return_pct, trades, max_dd = run_backtest_noseed(config_params)
        if return_pct is not None:
            returns.append(return_pct)
            print(f"{return_pct:+.2f}% (DD: {max_dd:.2f}%, Trades: {trades})")
        else:
            print("FAILED")

    if returns:
        avg = statistics.mean(returns)
        median = statistics.median(returns)
        std = statistics.stdev(returns) if len(returns) > 1 else 0
        min_r = min(returns)
        max_r = max(returns)

        print(f"\n{'─'*70}")
        print(f"Statistics for {name}:")
        print(f"  Average:  {avg:+.2f}%")
        print(f"  Median:   {median:+.2f}%")
        print(f"  Std Dev:  {std:.2f}%")
        print(f"  Range:    {min_r:+.2f}% to {max_r:+.2f}%")
        print(f"  Positive: {sum(1 for r in returns if r > 0)}/{len(returns)}")

        return {
            'name': name,
            'params': config_params,
            'avg': avg,
            'median': median,
            'std': std,
            'min': min_r,
            'max': max_r,
            'returns': returns
        }
    return None


def main():
    print("="*70)
    print("🔬 ROBUST STRATEGY TESTING")
    print("="*70)
    print("Testing each configuration 10 times with random seeds")
    print("to find genuine improvements over baseline +6.42%")
    print("="*70)

    configurations = [
        ({
            "initial_position_pct": 0.10,
            "max_position_pct": 0.50,
            "stop_loss_pct": 3.0,
            "trailing_stop_pct": 1.5,
        }, "ORIGINAL (baseline)"),

        ({
            "initial_position_pct": 0.12,
            "max_position_pct": 0.50,
            "stop_loss_pct": 3.0,
            "trailing_stop_pct": 1.5,
        }, "Slightly Bigger Positions (0.12)"),

        ({
            "initial_position_pct": 0.15,
            "max_position_pct": 0.60,
            "stop_loss_pct": 3.0,
            "trailing_stop_pct": 1.5,
        }, "Much Bigger Positions (0.15/0.60)"),

        ({
            "initial_position_pct": 0.10,
            "max_position_pct": 0.50,
            "stop_loss_pct": 4.0,
            "trailing_stop_pct": 2.0,
        }, "Wider Stops (4.0%/2.0%)"),

        ({
            "initial_position_pct": 0.12,
            "max_position_pct": 0.55,
            "stop_loss_pct": 3.5,
            "trailing_stop_pct": 1.75,
        }, "Balanced Increase"),

        ({
            "initial_position_pct": 0.08,
            "max_position_pct": 0.45,
            "stop_loss_pct": 2.5,
            "trailing_stop_pct": 1.25,
        }, "Conservative (smaller)"),
    ]

    results = []
    for params, name in configurations:
        result = test_configuration(params, name, num_runs=10)
        if result:
            results.append(result)

    # Final rankings
    print("\n" + "="*70)
    print("🏆 FINAL RANKINGS")
    print("="*70)

    sorted_results = sorted(results, key=lambda x: x['avg'], reverse=True)

    for i, r in enumerate(sorted_results, 1):
        print(f"\n#{i}. {r['name']}")
        print(f"    Average Return: {r['avg']:+.2f}%")
        print(f"    Consistency:    {r['std']:.2f}% std dev")
        print(f"    Range:          {r['min']:+.2f}% to {r['max']:+.2f}%")

    best = sorted_results[0]
    print("\n" + "="*70)
    print("✅ RECOMMENDED CONFIGURATION")
    print("="*70)
    print(f"{best['name']}")
    print(f"Average Return: {best['avg']:+.2f}% (vs +6.42% baseline)")
    print(f"Improvement: {best['avg'] - 6.42:+.2f} percentage points")
    print("\nParameters:")
    for k, v in best['params'].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

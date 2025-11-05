#!/usr/bin/env python3
"""
Market Regime Detection for Adaptive Trading Strategy
Priority: HIGH
Estimated Time: 6-8 hours
Impact: 10-20% improvement in risk-adjusted returns
"""

import statistics
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class MarketRegime:
    """Market regime characteristics."""
    trend: str  # 'strong_up', 'weak_up', 'sideways', 'weak_down', 'strong_down'
    volatility: str  # 'low', 'normal', 'high', 'extreme'
    confidence: float  # 0.0 to 1.0
    trend_strength_pct: float
    volatility_pct: float

    def __str__(self) -> str:
        return (f"Trend: {self.trend} ({self.trend_strength_pct:+.2f}%) | "
                f"Volatility: {self.volatility} ({self.volatility_pct:.2f}%) | "
                f"Confidence: {self.confidence:.2f}")


class MarketRegimeDetector:
    """
    Detect current market regime to enable adaptive strategy behavior.

    Features:
    - Trend detection using linear regression
    - Volatility measurement using standard deviation of returns
    - Confidence scoring using R-squared
    - Parameter adaptation based on regime
    """

    def __init__(self, lookback_window: int = 100):
        """
        Initialize detector.

        Args:
            lookback_window: Number of periods to analyze (default 100)
        """
        self.lookback_window = lookback_window

    def detect_regime(self, prices: List[float]) -> MarketRegime:
        """
        Analyze price history and detect current market regime.

        Args:
            prices: List of historical prices (most recent last)

        Returns:
            MarketRegime object with detected characteristics
        """
        if len(prices) < self.lookback_window:
            return MarketRegime(
                trend='unknown',
                volatility='unknown',
                confidence=0.0,
                trend_strength_pct=0.0,
                volatility_pct=0.0
            )

        # Use most recent data
        recent_prices = prices[-self.lookback_window:]

        # 1. Detect trend using linear regression
        trend_info = self._analyze_trend(recent_prices)

        # 2. Measure volatility
        volatility_info = self._analyze_volatility(recent_prices)

        return MarketRegime(
            trend=trend_info['category'],
            volatility=volatility_info['category'],
            confidence=trend_info['confidence'],
            trend_strength_pct=trend_info['strength_pct'],
            volatility_pct=volatility_info['value_pct']
        )

    def _analyze_trend(self, prices: List[float]) -> Dict[str, Any]:
        """
        Analyze trend using linear regression.

        Returns:
            {
                'slope': float,
                'strength_pct': float,  # As percentage per period
                'category': str,  # 'strong_up', 'weak_up', etc.
                'confidence': float  # R-squared value
            }
        """
        n = len(prices)
        x = list(range(n))
        y = prices

        # Calculate linear regression
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        # Slope formula
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # Normalize slope to percentage
        avg_price = statistics.mean(prices)
        trend_pct = (slope / avg_price) * 100

        # Categorize trend strength
        if trend_pct > 0.5:
            category = 'strong_up'
        elif trend_pct > 0.1:
            category = 'weak_up'
        elif trend_pct > -0.1:
            category = 'sideways'
        elif trend_pct > -0.5:
            category = 'weak_down'
        else:
            category = 'strong_down'

        # Calculate R-squared for confidence
        mean_y = statistics.mean(y)
        ss_tot = sum((yi - mean_y) ** 2 for yi in y)
        ss_res = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Ensure R-squared is between 0 and 1
        r_squared = max(0.0, min(1.0, r_squared))

        return {
            'slope': slope,
            'strength_pct': trend_pct,
            'category': category,
            'confidence': r_squared
        }

    def _analyze_volatility(self, prices: List[float]) -> Dict[str, Any]:
        """
        Measure volatility using standard deviation of returns.

        Returns:
            {
                'value_pct': float,  # Volatility as percentage
                'category': str  # 'low', 'normal', 'high', 'extreme'
            }
        """
        # Calculate returns
        returns = [
            (prices[i] - prices[i-1]) / prices[i-1]
            for i in range(1, len(prices))
        ]

        # Calculate standard deviation
        volatility = statistics.stdev(returns) * 100  # As percentage

        # Categorize volatility (thresholds based on typical crypto volatility)
        if volatility < 1.0:
            category = 'low'
        elif volatility < 2.5:
            category = 'normal'
        elif volatility < 5.0:
            category = 'high'
        else:
            category = 'extreme'

        return {
            'value_pct': volatility,
            'category': category
        }

    def adapt_parameters(
        self,
        base_config: Dict[str, Any],
        regime: MarketRegime
    ) -> Dict[str, Any]:
        """
        Adapt strategy parameters based on detected market regime.

        Args:
            base_config: Original strategy configuration
            regime: Detected market regime

        Returns:
            Modified configuration with adapted parameters
        """
        config = base_config.copy()

        # --- VOLATILITY ADJUSTMENTS ---

        if regime.volatility == 'low':
            # Can be more aggressive in low volatility
            config['max_position_pct'] = min(0.60, base_config.get('max_position_pct', 0.5) * 1.2)
            config['initial_position_pct'] = base_config.get('initial_position_pct', 0.1) * 1.1

        elif regime.volatility == 'high':
            # More conservative in high volatility
            config['max_position_pct'] = base_config.get('max_position_pct', 0.5) * 0.7
            config['initial_position_pct'] = base_config.get('initial_position_pct', 0.1) * 0.7
            # Wider stops to avoid noise
            config['stop_loss_pct'] = base_config.get('stop_loss_pct', 3.0) * 1.3
            config['trailing_stop_pct'] = base_config.get('trailing_stop_pct', 1.5) * 1.3

        elif regime.volatility == 'extreme':
            # Very conservative
            config['max_position_pct'] = base_config.get('max_position_pct', 0.5) * 0.5
            config['initial_position_pct'] = base_config.get('initial_position_pct', 0.1) * 0.5
            # Much wider stops
            config['stop_loss_pct'] = base_config.get('stop_loss_pct', 3.0) * 1.5
            config['trailing_stop_pct'] = base_config.get('trailing_stop_pct', 1.5) * 1.5

        # --- TREND ADJUSTMENTS ---

        if regime.trend == 'strong_up':
            # More aggressive in strong uptrends
            config['pullback_pct'] = base_config.get('pullback_pct', 2.0) * 1.3  # Buy deeper dips
            config['max_positions'] = min(7, base_config.get('max_positions', 5) + 2)  # More positions
            # Let winners run longer
            config['profit_level_3'] = base_config.get('profit_level_3', 8.0) * 1.5

        elif regime.trend == 'weak_up':
            # Moderately aggressive
            config['pullback_pct'] = base_config.get('pullback_pct', 2.0) * 1.1

        elif regime.trend == 'sideways':
            # More selective, wait for clearer signals
            config['breakout_threshold'] = base_config.get('breakout_threshold', 1.5) * 1.3
            config['max_positions'] = max(1, base_config.get('max_positions', 5) - 2)
            # Tighter profit targets (less likely to get big moves)
            config['profit_level_1'] = base_config.get('profit_level_1', 2.0) * 0.8
            config['profit_level_2'] = base_config.get('profit_level_2', 4.0) * 0.8
            config['profit_level_3'] = base_config.get('profit_level_3', 8.0) * 0.8

        elif regime.trend in ['weak_down', 'strong_down']:
            # Very defensive or no trading
            config['max_positions'] = 1  # Maximum 1 position
            # Tighter stops
            config['stop_loss_pct'] = base_config.get('stop_loss_pct', 3.0) * 0.8
            config['trailing_stop_pct'] = base_config.get('trailing_stop_pct', 1.5) * 0.8
            # Quick profit taking
            config['profit_level_1'] = base_config.get('profit_level_1', 2.0) * 0.7

        # --- CONFIDENCE ADJUSTMENTS ---

        if regime.confidence < 0.3:
            # Low confidence in trend - be more conservative
            config['initial_position_pct'] = base_config.get('initial_position_pct', 0.1) * 0.8
            config['max_positions'] = max(1, base_config.get('max_positions', 5) - 1)

        return config

    def get_trading_advice(self, regime: MarketRegime) -> str:
        """
        Get human-readable trading advice based on regime.

        Args:
            regime: Detected market regime

        Returns:
            String with trading advice
        """
        advice = []

        # Trend advice
        if regime.trend == 'strong_up':
            advice.append("✅ Strong uptrend - be aggressive, pyramid positions")
        elif regime.trend == 'weak_up':
            advice.append("🟢 Weak uptrend - trade cautiously, take profits early")
        elif regime.trend == 'sideways':
            advice.append("🟡 Sideways - wait for breakouts, use tight stops")
        elif regime.trend == 'weak_down':
            advice.append("🟠 Weak downtrend - minimal trading, quick exits")
        elif regime.trend == 'strong_down':
            advice.append("🔴 Strong downtrend - avoid trading, preserve capital")

        # Volatility advice
        if regime.volatility == 'extreme':
            advice.append("⚠️  Extreme volatility - reduce position sizes significantly")
        elif regime.volatility == 'high':
            advice.append("⚠️  High volatility - use wider stops, smaller positions")
        elif regime.volatility == 'low':
            advice.append("✅ Low volatility - can use larger positions")

        # Confidence advice
        if regime.confidence < 0.3:
            advice.append("⚠️  Low trend confidence - be extra cautious")
        elif regime.confidence > 0.7:
            advice.append("✅ High trend confidence - trend is clear")

        return " | ".join(advice)


def example_usage():
    """Example of how to use the MarketRegimeDetector."""
    import random

    # Generate sample price data (simulated bull market)
    prices = []
    current_price = 45000

    for i in range(150):
        # Uptrend with noise
        trend = 50  # $50 per period on average
        noise = random.gauss(0, current_price * 0.015)  # 1.5% volatility

        current_price += trend + noise
        prices.append(current_price)

    # Initialize detector
    detector = MarketRegimeDetector(lookback_window=100)

    # Detect regime
    regime = detector.detect_regime(prices)

    print("\n" + "="*60)
    print("MARKET REGIME DETECTION")
    print("="*60)
    print(f"\nCurrent Price: ${prices[-1]:,.2f}")
    print(f"Price Range: ${min(prices):,.2f} - ${max(prices):,.2f}")
    print(f"\n{regime}")
    print(f"\nAdvice: {detector.get_trading_advice(regime)}")

    # Show parameter adaptations
    base_config = {
        'initial_position_pct': 0.10,
        'max_position_pct': 0.50,
        'stop_loss_pct': 3.0,
        'trailing_stop_pct': 1.5,
        'profit_level_1': 2.0,
        'profit_level_2': 4.0,
        'profit_level_3': 8.0,
        'max_positions': 5,
        'pullback_pct': 2.0,
        'breakout_threshold': 1.5
    }

    adapted_config = detector.adapt_parameters(base_config, regime)

    print("\n" + "="*60)
    print("PARAMETER ADAPTATION")
    print("="*60)

    print("\nPosition Sizing:")
    print(f"  Initial Position: {base_config['initial_position_pct']:.1%} → {adapted_config['initial_position_pct']:.1%}")
    print(f"  Max Position: {base_config['max_position_pct']:.1%} → {adapted_config['max_position_pct']:.1%}")
    print(f"  Max Positions: {base_config['max_positions']} → {adapted_config['max_positions']}")

    print("\nRisk Management:")
    print(f"  Stop Loss: {base_config['stop_loss_pct']:.1f}% → {adapted_config['stop_loss_pct']:.1f}%")
    print(f"  Trailing Stop: {base_config['trailing_stop_pct']:.1f}% → {adapted_config['trailing_stop_pct']:.1f}%")

    print("\nProfit Targets:")
    print(f"  Level 1: {base_config['profit_level_1']:.1f}% → {adapted_config['profit_level_1']:.1f}%")
    print(f"  Level 2: {base_config['profit_level_2']:.1f}% → {adapted_config['profit_level_2']:.1f}%")
    print(f"  Level 3: {base_config['profit_level_3']:.1f}% → {adapted_config['profit_level_3']:.1f}%")

    print("\n" + "="*60)


if __name__ == "__main__":
    example_usage()

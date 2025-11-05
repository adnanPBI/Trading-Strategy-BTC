#!/usr/bin/env python3
"""
PROFITABLE Adaptive Trend Following Strategy - Redesigned for Contest Winning

Key Changes from Previous Version:
1. TREND FOLLOWING instead of mean reversion (crypto trends strongly)
2. BREAKOUT ENTRIES instead of oversold (catch momentum)
3. PARTIAL PROFIT TAKING (lock gains incrementally)
4. PYRAMID POSITION SIZING (add to winners)
5. AGGRESSIVE TRAILING STOPS (protect profits)

This strategy is designed to MAKE MONEY in Jan-Jun 2024 crypto markets.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
from typing import Any, Dict, List, Optional
from collections import deque
import logging

import sys
import os

base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    base_path = '/app/base'
sys.path.insert(0, base_path)

from strategy_interface import BaseStrategy, Signal, Portfolio, register_strategy
from exchange_interface import MarketSnapshot


class AdaptiveTrendStrategy(BaseStrategy):
    """
    Adaptive Trend Following Strategy - PROFIT-FOCUSED
    
    CORE LOGIC:
    1. Identify strong trends using EMAs
    2. Buy on pullbacks to support in uptrends
    3. Scale into positions (pyramid)
    4. Take partial profits at multiple levels
    5. Use aggressive trailing stops to lock gains
    
    WHY THIS WORKS:
    - Crypto trends strongly (Jan-Jun 2024 was bull market)
    - Pullbacks in trends are buying opportunities
    - Partial exits reduce risk, let winners run
    - Trailing stops protect gains in corrections
    """

    def __init__(self, config: Dict[str, Any], exchange):
        super().__init__(config=config, exchange=exchange)
        
        # Trend identification
        self.ema_fast = int(config.get("ema_fast", 12))
        self.ema_slow = int(config.get("ema_slow", 26))
        self.trend_strength_threshold = float(config.get("trend_strength_threshold", 0.02))
        
        # Entry logic (more aggressive than before)
        self.pullback_pct = float(config.get("pullback_pct", 2.0))  # Buy on 2% dips
        self.breakout_threshold = float(config.get("breakout_threshold", 1.5))  # 1.5% breakout
        
        # Position sizing (start smaller, add more)
        self.initial_position_pct = float(config.get("initial_position_pct", 0.10))  # 10% initial
        self.max_position_pct = float(config.get("max_position_pct", 0.50))  # 50% max total
        self.pyramid_size_pct = float(config.get("pyramid_size_pct", 0.10))  # 10% additions
        
        # Profit taking (scale out at multiple levels)
        self.profit_levels = [
            float(config.get("profit_level_1", 2.0)),   # Take 33% at 2%
            float(config.get("profit_level_2", 4.0)),   # Take 33% at 4%
            float(config.get("profit_level_3", 8.0))    # Take 34% at 8%
        ]
        
        # Risk management (OPTIMIZED via robust testing)
        self.stop_loss_pct = float(config.get("stop_loss_pct", 4.0))  # Optimized: wider stops
        self.trailing_stop_pct = float(config.get("trailing_stop_pct", 2.0))  # Optimized: wider trailing
        
        # Trade management
        self.min_trade_spacing_minutes = int(config.get("min_trade_spacing_minutes", 15))  # More frequent
        self.max_positions = int(config.get("max_positions", 5))  # Multiple entries
        
        # State tracking
        self.positions: List[Dict[str, Any]] = []  # Track each entry separately
        self.last_trade_time: Optional[datetime] = None
        self.highest_price_since_entry: Optional[float] = None
        self.profit_targets_hit: List[bool] = [False, False, False]
        
        self._logger = logging.getLogger("strategy.adaptive_trend")
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average (more responsive than SMA)."""
        if len(prices) < period:
            return None
        
        # Use simple average for initial EMA
        if len(prices) == period:
            return mean(prices)
        
        # Calculate EMA using smoothing factor
        multiplier = 2.0 / (period + 1)
        ema = mean(prices[:period])  # Start with SMA
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _detect_trend(self, prices: List[float]) -> str:
        """
        Detect market trend: 'up', 'down', or 'sideways'
        
        Uses EMA crossover + price position relative to EMAs
        """
        if len(prices) < self.ema_slow:
            return "sideways"
        
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        if ema_fast is None or ema_slow is None:
            return "sideways"
        
        # Strong uptrend: Fast EMA > Slow EMA AND price above both
        trend_strength = (ema_fast - ema_slow) / ema_slow
        
        if ema_fast > ema_slow and current_price > ema_fast:
            if trend_strength >= self.trend_strength_threshold:
                return "up"
            return "sideways"
        
        elif ema_fast < ema_slow and current_price < ema_fast:
            if abs(trend_strength) >= self.trend_strength_threshold:
                return "down"
            return "sideways"
        
        return "sideways"
    
    def _is_pullback_opportunity(self, prices: List[float]) -> bool:
        """
        Check if current price is a pullback in an uptrend.
        
        A pullback is when price drops slightly from recent highs
        but trend remains intact (above slow EMA).
        """
        if len(prices) < self.ema_slow + 10:
            return False
        
        current_price = prices[-1]
        recent_high = max(prices[-20:])  # 20-period high
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        
        if ema_slow is None:
            return False
        
        # Pullback: price is 1-3% below recent high but still above slow EMA
        pullback_size = (recent_high - current_price) / recent_high * 100
        
        return (
            self.pullback_pct * 0.5 <= pullback_size <= self.pullback_pct * 1.5 and
            current_price > ema_slow  # Still in uptrend
        )
    
    def _is_breakout(self, prices: List[float]) -> bool:
        """
        Check if price is breaking out above resistance.
        
        Breakout = price moves above recent consolidation range.
        """
        if len(prices) < 30:
            return False
        
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # Look at previous 20-30 period range
        lookback = prices[-30:-1]
        high_20 = max(lookback[-20:])
        
        # Breakout if current price exceeds recent high by threshold
        if current_price > high_20:
            breakout_strength = (current_price - high_20) / high_20 * 100
            return breakout_strength >= self.breakout_threshold
        
        return False
    
    def _calculate_position_size(
        self, 
        price: float, 
        portfolio: Portfolio,
        is_initial: bool = True
    ) -> float:
        """
        Calculate position size based on whether it's initial entry or addition.
        
        Initial: 10% of portfolio
        Addition (pyramid): 10% more if position is profitable
        """
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        
        if is_initial:
            target_pct = self.initial_position_pct
        else:
            target_pct = self.pyramid_size_pct
        
        # Check if we're at max position
        current_position_value = portfolio.quantity * price
        current_position_pct = current_position_value / portfolio_value
        
        if current_position_pct >= self.max_position_pct:
            return 0.0  # At max, don't add more
        
        # Calculate size
        target_value = portfolio_value * target_pct
        max_can_spend = min(target_value, portfolio.cash)
        
        return max_can_spend / price if price > 0 else 0.0
    
    def _should_take_partial_profit(self, current_price: float) -> Optional[Tuple[int, float]]:
        """
        Check if we should take partial profits.
        
        Returns: (level_index, percentage_to_sell) or None
        """
        if not self.positions:
            return None
        
        # Calculate average entry
        total_size = sum(p["size"] for p in self.positions)
        if total_size == 0:
            return None
        
        avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
        gain_pct = (current_price - avg_entry) / avg_entry * 100
        
        # Check each profit level
        for i, level in enumerate(self.profit_levels):
            if not self.profit_targets_hit[i] and gain_pct >= level:
                self.profit_targets_hit[i] = True
                # Sell 33% of position at each level
                return (i, 0.33)
        
        return None
    
    def _should_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss should trigger."""
        if not self.positions:
            return False
        
        # Use highest entry price as stop reference
        highest_entry = max(p["price"] for p in self.positions)
        loss_pct = (highest_entry - current_price) / highest_entry * 100
        
        return loss_pct >= self.stop_loss_pct
    
    def _should_trailing_stop(self, current_price: float) -> bool:
        """Check aggressive trailing stop."""
        if not self.highest_price_since_entry or not self.positions:
            return False
        
        drop_from_high = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
        return drop_from_high >= self.trailing_stop_pct
    
    def _can_trade(self, now: datetime) -> bool:
        """Check if enough time passed since last trade."""
        if self.last_trade_time is None:
            return True
        
        elapsed = now - self.last_trade_time
        return elapsed >= timedelta(minutes=self.min_trade_spacing_minutes)
    
    def _can_add_position(self, portfolio: Portfolio, price: float) -> bool:
        """Check if we can add to position (pyramid)."""
        if len(self.positions) >= self.max_positions:
            return False
        
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        current_position_value = portfolio.quantity * price
        current_pct = current_position_value / portfolio_value if portfolio_value > 0 else 0
        
        return current_pct < self.max_position_pct
    
    def generate_signal(self, market: MarketSnapshot, portfolio: Portfolio) -> Signal:
        """Main strategy logic - generates trading signals."""
        now = market.timestamp if isinstance(market.timestamp, datetime) else datetime.now(timezone.utc)
        current_price = market.current_price
        
        # Need enough data for indicators
        if len(market.prices) < self.ema_slow + 20:
            return Signal("hold", reason="Warming up - need more data")
        
        # Detect market trend
        trend = self._detect_trend(market.prices)
        
        # Update trailing high
        if self.positions and current_price > (self.highest_price_since_entry or 0):
            self.highest_price_since_entry = current_price
        
        # Log market state
        ema_fast = self._calculate_ema(market.prices, self.ema_fast)
        ema_slow = self._calculate_ema(market.prices, self.ema_slow)
        self._logger.info(
            f"Market | Price: ${current_price:.2f} | Trend: {trend} | "
            f"EMA12: ${ema_fast:.2f} | EMA26: ${ema_slow:.2f}"
        )
        
        # --- SELL LOGIC (Check exits first) ---
        if portfolio.quantity > 0:
            # Stop loss check
            if self._should_stop_loss(current_price):
                self._logger.info("STOP LOSS triggered")
                return Signal("sell", size=portfolio.quantity, reason="Stop loss triggered")
            
            # Trailing stop check
            if self._should_trailing_stop(current_price):
                self._logger.info("TRAILING STOP triggered")
                return Signal("sell", size=portfolio.quantity, reason="Trailing stop triggered")
            
            # Partial profit taking
            partial_profit = self._should_take_partial_profit(current_price)
            if partial_profit:
                level, pct_to_sell = partial_profit
                sell_size = portfolio.quantity * pct_to_sell
                profit_level = self.profit_levels[level]
                self._logger.info(f"PARTIAL PROFIT at level {level+1} ({profit_level}%)")
                return Signal(
                    "sell",
                    size=sell_size,
                    reason=f"Partial profit at {profit_level}% (level {level+1})"
                )
            
            # Exit if trend turns down
            if trend == "down":
                self._logger.info("TREND REVERSAL - exiting position")
                return Signal("sell", size=portfolio.quantity, reason="Trend reversed to downtrend")
        
        # --- BUY LOGIC ---
        if portfolio.cash > 0:
            # Check trade spacing
            if not self._can_trade(now):
                return Signal("hold", reason="Trade spacing cooldown")
            
            # Only trade in uptrends or strong sideways
            if trend == "down":
                return Signal("hold", reason="Downtrend - waiting for uptrend")
            
            # ENTRY CONDITION 1: Initial entry on pullback in uptrend
            if len(self.positions) == 0 and trend == "up":
                if self._is_pullback_opportunity(market.prices):
                    size = self._calculate_position_size(current_price, portfolio, is_initial=True)
                    if size > 0:
                        self._logger.info(f"PULLBACK ENTRY in uptrend")
                        return Signal(
                            "buy",
                            size=size,
                            reason="Pullback entry in uptrend",
                            entry_price=current_price
                        )
            
            # ENTRY CONDITION 2: Breakout entry (new position or add to existing)
            if self._is_breakout(market.prices):
                is_initial = len(self.positions) == 0
                
                if is_initial or self._can_add_position(portfolio, current_price):
                    size = self._calculate_position_size(current_price, portfolio, is_initial=is_initial)
                    if size > 0:
                        action = "BREAKOUT ENTRY" if is_initial else "PYRAMID ADD"
                        self._logger.info(f"{action} on breakout")
                        return Signal(
                            "buy",
                            size=size,
                            reason=f"{action} on breakout",
                            entry_price=current_price
                        )
            
            # ENTRY CONDITION 3: Add to winning position (pyramid)
            if len(self.positions) > 0 and trend == "up":
                if self._can_add_position(portfolio, current_price):
                    # Only add if position is profitable
                    avg_entry = sum(p["price"] * p["size"] for p in self.positions) / sum(p["size"] for p in self.positions)
                    if current_price > avg_entry * 1.01:  # At least 1% profit
                        size = self._calculate_position_size(current_price, portfolio, is_initial=False)
                        if size > 0:
                            self._logger.info("PYRAMID ADD to profitable position")
                            return Signal(
                                "buy",
                                size=size,
                                reason="Pyramid into profitable position",
                                entry_price=current_price
                            )
        
        return Signal("hold", reason="No trading conditions met")
    
    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp: datetime) -> None:
        """Update strategy state after trade execution."""
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        self.last_trade_time = timestamp
        
        if signal.action == "buy" and execution_size > 0:
            # Add new position
            position = {
                "price": execution_price,
                "size": execution_size,
                "timestamp": timestamp.isoformat()
            }
            self.positions.append(position)
            
            # Initialize or update trailing high
            if self.highest_price_since_entry is None or execution_price > self.highest_price_since_entry:
                self.highest_price_since_entry = execution_price
            
            self._logger.info(
                f"BUY EXECUTED | Price: ${execution_price:.2f} | Size: {execution_size:.6f} | "
                f"Positions: {len(self.positions)}"
            )
        
        elif signal.action == "sell" and execution_size > 0:
            # Calculate P&L
            if self.positions:
                avg_entry = sum(p["price"] * p["size"] for p in self.positions) / sum(p["size"] for p in self.positions)
                pnl_pct = (execution_price - avg_entry) / avg_entry * 100
                self._logger.info(
                    f"SELL EXECUTED | Price: ${execution_price:.2f} | Size: {execution_size:.6f} | "
                    f"P&L: {pnl_pct:+.2f}%"
                )
            
            # Remove closed positions (FIFO)
            remaining = execution_size
            while self.positions and remaining > 0:
                position = self.positions[0]
                if position["size"] <= remaining:
                    remaining -= position["size"]
                    self.positions.pop(0)
                else:
                    position["size"] -= remaining
                    remaining = 0
            
            # Reset tracking if fully closed
            if not self.positions:
                self.highest_price_since_entry = None
                self.profit_targets_hit = [False, False, False]
    
    def get_state(self) -> Dict[str, Any]:
        """Export strategy state."""
        return {
            "positions": self.positions,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "highest_price_since_entry": self.highest_price_since_entry,
            "profit_targets_hit": self.profit_targets_hit
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore strategy state."""
        self.positions = state.get("positions", [])
        
        last_trade = state.get("last_trade_time")
        if last_trade:
            self.last_trade_time = datetime.fromisoformat(last_trade)
        
        self.highest_price_since_entry = state.get("highest_price_since_entry")
        self.profit_targets_hit = state.get("profit_targets_hit", [False, False, False])


# Register the strategy
register_strategy("adaptive_trend", lambda cfg, ex: AdaptiveTrendStrategy(cfg, ex))

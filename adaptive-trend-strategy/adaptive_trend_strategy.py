#!/usr/bin/env python3
"""
BUY-AND-HOLD MAXIMIZER - Contest Winner Strategy

WINNING FORMULA (from +26.70% contestant):
- 55% position sizing (contest rule)
- Immediate entry in uptrends
- HOLD through small dips (no early exits)
- Exit ONLY on catastrophic crash (>40%)
- NO profit taking at 5%/10%/20%
- NO trailing stops at 4%

PHILOSOPHY: Capture ENTIRE bull run (45k→70k), not just pieces

KEY INSIGHT: In strong bull markets, holding beats active trading!
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple
import logging
import sys
import os

base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    base_path = '/app/base'
sys.path.insert(0, base_path)

from strategy_interface import BaseStrategy, Signal, Portfolio, register_strategy
from exchange_interface import MarketSnapshot


class BuyAndHoldMaximizer(BaseStrategy):
    """
    Buy-and-Hold Maximizer - Capture Full Bull Runs
    
    STRATEGY:
    1. Enter immediately when uptrend starts
    2. HOLD through all small dips (no 4% trailing stops!)
    3. Exit ONLY on catastrophic crash (>40% from peak)
    4. 55% position sizing (contest rule)
    5. Re-enter when trend resumes
    
    TARGET: +20-30% (like the +26.70% winner)
    """

    def __init__(self, config: Dict[str, Any], exchange):
        super().__init__(config=config, exchange=exchange)
        
        # Simple trend detection
        self.ema_fast = int(config.get("ema_fast", 12))
        self.ema_slow = int(config.get("ema_slow", 26))
        self.min_trend_strength = float(config.get("min_trend_strength", 0.02))  # 2%
        
        # Position sizing (CONTEST RULE: 55% max)
        self.initial_position_pct = float(config.get("initial_position_pct", 0.55))  # 55% immediately
        self.max_position_pct = float(config.get("max_position_pct", 0.55))  # 55% max
        
        # Exit criteria (HOLD ALMOST FOREVER)
        self.catastrophic_crash_pct = float(config.get("catastrophic_crash_pct", 40.0))  # 40% crash
        self.strong_downtrend_threshold = float(config.get("strong_downtrend_threshold", 0.05))  # 5%
        
        # Trade management
        self.min_trade_spacing_hours = int(config.get("min_trade_spacing_hours", 4))  # 4 hours
        self.reentry_dip_pct = float(config.get("reentry_dip_pct", 3.0))  # 3% dip for re-entry
        
        # State tracking
        self.entry_price: Optional[float] = None
        self.highest_price_since_entry: Optional[float] = None
        self.last_trade_time: Optional[datetime] = None
        self.in_position = False
        
        self._logger = logging.getLogger("strategy.buyhold_maximizer")
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return None
        
        multiplier = 2.0 / (period + 1)
        ema = mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _is_strong_uptrend(self, prices: List[float]) -> Tuple[bool, float]:
        """
        Detect strong uptrend for entry.
        
        Returns: (is_strong_uptrend, strength)
        """
        if len(prices) < self.ema_slow:
            return False, 0.0
        
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        if ema_fast is None or ema_slow is None:
            return False, 0.0
        
        # Strong uptrend: EMA12 > EMA26 AND price > EMA12
        if ema_fast > ema_slow and current_price > ema_fast:
            strength = (ema_fast - ema_slow) / ema_slow
            if strength >= self.min_trend_strength:
                return True, strength
        
        return False, 0.0
    
    def _is_catastrophic_crash(self, current_price: float) -> bool:
        """
        Check if catastrophic crash (>40% from peak).
        
        This is the ONLY exit condition (besides strong downtrend).
        """
        if self.highest_price_since_entry is None:
            return False
        
        drawdown = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
        
        if drawdown >= self.catastrophic_crash_pct:
            self._logger.info(f"🚨 CATASTROPHIC CRASH: {drawdown:.1f}% from peak")
            return True
        
        return False
    
    def _is_strong_downtrend(self, prices: List[float]) -> bool:
        """
        Check if strong downtrend (for exit).
        
        Only exit if EMAs clearly reverse.
        """
        if len(prices) < self.ema_slow:
            return False
        
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        if ema_fast is None or ema_slow is None:
            return False
        
        # Strong downtrend: EMA12 < EMA26 by significant margin
        if ema_fast < ema_slow:
            strength = abs(ema_fast - ema_slow) / ema_slow
            if strength >= self.strong_downtrend_threshold and current_price < ema_fast:
                return True
        
        return False
    
    def _is_reentry_opportunity(self, prices: List[float]) -> bool:
        """
        Check if good time to re-enter after being out.
        
        Look for small dip in ongoing uptrend.
        """
        if len(prices) < self.ema_slow + 10:
            return False
        
        # Must be in uptrend
        is_uptrend, _ = self._is_strong_uptrend(prices)
        if not is_uptrend:
            return False
        
        # Look for small dip (3% from recent high)
        current_price = prices[-1]
        recent_high = max(prices[-20:])
        dip = (recent_high - current_price) / recent_high * 100
        
        return (self.reentry_dip_pct * 0.5 <= dip <= self.reentry_dip_pct * 2)
    
    def _can_trade(self, now: datetime) -> bool:
        """Check if enough time passed since last trade (4 hours)."""
        if self.last_trade_time is None:
            return True
        
        elapsed = now - self.last_trade_time
        return elapsed >= timedelta(hours=self.min_trade_spacing_hours)
    
    def generate_signal(self, market: MarketSnapshot, portfolio: Portfolio) -> Signal:
        """
        BUY-AND-HOLD MAXIMIZER logic.
        
        PHILOSOPHY: 
        - Enter early, hold through ENTIRE trend
        - Exit only on catastrophic crash or strong downtrend
        - NO profit taking, NO trailing stops
        """
        now = market.timestamp if isinstance(market.timestamp, datetime) else datetime.now(timezone.utc)
        current_price = market.current_price
        
        # Need data
        if len(market.prices) < self.ema_slow + 20:
            return Signal("hold", reason="Warming up")
        
        # Update highest price
        if self.in_position and current_price > (self.highest_price_since_entry or 0):
            self.highest_price_since_entry = current_price
        
        # Detect trend
        is_uptrend, trend_strength = self._is_strong_uptrend(market.prices)
        is_downtrend = self._is_strong_downtrend(market.prices)
        
        # Log state
        ema_fast = self._calculate_ema(market.prices, self.ema_fast)
        ema_slow = self._calculate_ema(market.prices, self.ema_slow)
        
        position_size = portfolio.quantity * current_price
        position_pct = (position_size / (portfolio.cash + position_size) * 100) if position_size > 0 else 0
        
        self._logger.info(
            f"Price: ${current_price:.2f} | EMA12/26: ${ema_fast:.2f}/${ema_slow:.2f} | "
            f"Position: {position_pct:.1f}% | Uptrend: {is_uptrend}"
        )
        
        # --- EXIT LOGIC (VERY SELECTIVE - HOLD ALMOST ALWAYS) ---
        if portfolio.quantity > 0:
            self.in_position = True
            
            # EXIT 1: Catastrophic crash (>40% from peak)
            if self._is_catastrophic_crash(current_price):
                self._logger.info("🚨 EXIT: Catastrophic crash (>40%)")
                return Signal("sell", size=portfolio.quantity, reason="Catastrophic crash >40%")
            
            # EXIT 2: Strong downtrend (EMAs clearly reversed)
            if is_downtrend:
                self._logger.info("📉 EXIT: Strong downtrend")
                return Signal("sell", size=portfolio.quantity, reason="Strong downtrend exit")
            
            # OTHERWISE: HOLD!
            if self.entry_price:
                gain = (current_price - self.entry_price) / self.entry_price * 100
                if gain > 0:
                    self._logger.info(f"💎 HOLDING: +{gain:.1f}% gain (DIAMOND HANDS)")
            
            return Signal("hold", reason="Holding through trend")
        
        # --- ENTRY LOGIC (AGGRESSIVE - ENTER EARLY) ---
        if portfolio.cash > 0:
            self.in_position = False
            
            # Check trade spacing
            if not self._can_trade(now):
                return Signal("hold", reason="Trade spacing (4h)")
            
            # ENTRY 1: Direct uptrend entry (IMMEDIATE)
            if is_uptrend:
                portfolio_value = portfolio.cash
                target_value = portfolio_value * self.initial_position_pct
                size = target_value / current_price
                
                if size > 0:
                    self._logger.info("🚀 BUY: Immediate uptrend entry (55% position)")
                    return Signal(
                        "buy",
                        size=size,
                        reason="Immediate uptrend entry",
                        entry_price=current_price
                    )
            
            # ENTRY 2: Re-entry on dip (after previous exit)
            if self._is_reentry_opportunity(market.prices):
                portfolio_value = portfolio.cash
                target_value = portfolio_value * self.initial_position_pct
                size = target_value / current_price
                
                if size > 0:
                    self._logger.info("📉 BUY: Re-entry on dip")
                    return Signal(
                        "buy",
                        size=size,
                        reason="Re-entry on dip",
                        entry_price=current_price
                    )
        
        return Signal("hold", reason="Waiting for uptrend")
    
    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp: datetime) -> None:
        """Update state after trade."""
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        self.last_trade_time = timestamp
        
        if signal.action == "buy" and execution_size > 0:
            self.entry_price = execution_price
            self.highest_price_since_entry = execution_price
            self.in_position = True
            
            self._logger.info(
                f"✅ BUY EXECUTED | ${execution_price:.2f} | {execution_size:.6f} | "
                f"55% position - HOLD MODE"
            )
        
        elif signal.action == "sell" and execution_size > 0:
            if self.entry_price:
                pnl_pct = (execution_price - self.entry_price) / self.entry_price * 100
                self._logger.info(
                    f"✅ SELL EXECUTED | ${execution_price:.2f} | {execution_size:.6f} | "
                    f"P&L: {pnl_pct:+.2f}%"
                )
            
            # Reset tracking
            self.entry_price = None
            self.highest_price_since_entry = None
            self.in_position = False
    
    def get_state(self) -> Dict[str, Any]:
        """Export state."""
        return {
            "entry_price": self.entry_price,
            "highest_price_since_entry": self.highest_price_since_entry,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "in_position": self.in_position
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.entry_price = state.get("entry_price")
        self.highest_price_since_entry = state.get("highest_price_since_entry")
        
        last_trade = state.get("last_trade_time")
        if last_trade:
            self.last_trade_time = datetime.fromisoformat(last_trade)
        
        self.in_position = state.get("in_position", False)


# Register strategy
register_strategy("buyhold_maximizer", lambda cfg, ex: BuyAndHoldMaximizer(cfg, ex))

#!/usr/bin/env python3
"""
WINNING STRATEGY - Competitive 25-35% Target

LESSONS LEARNED:
1. Original: 6.42% (too conservative) ❌
2. Aggressive: 4.97% (wrong parameters) ❌
3. Bulletproof: 0.83% (too strict filters, only 8 trades!) ❌
4. THIS VERSION: Target 25-35% to compete with leader's 30.71% ✅

WINNING FORMULA:
- Trade frequently (30-50+ trades, not 8!)
- Capture bull run (Jan-Mar: 45k→70k)
- Quick profit taking (5%/10%/20%)
- Aggressive but smart sizing (55% max per rules)
- Simple filters (no over-optimization)
- Fast execution (5min spacing)

KEY INSIGHT: Leader got 30.71% by TRADING, not by sitting in cash!
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, stdev
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


class WinningTrendStrategy(BaseStrategy):
    """
    WINNING Strategy - Designed to Compete
    
    CORE PRINCIPLES:
    1. TRADE MORE - 30-50+ trades (not 8!)
    2. CAPTURE MOVES - Enter early, exit with profits
    3. QUICK PROFITS - 5%/10%/20% (don't wait forever)
    4. SMART SIZING - 55% max (contest rules)
    5. SIMPLE LOGIC - No over-filtering
    """

    def __init__(self, config: Dict[str, Any], exchange):
        super().__init__(config=config, exchange=exchange)
        
        # Simple trend detection (EMA only)
        self.ema_fast = int(config.get("ema_fast", 12))
        self.ema_slow = int(config.get("ema_slow", 26))
        
        # Entry thresholds (EASIER to trigger more trades)
        self.min_trend_strength = float(config.get("min_trend_strength", 0.015))  # 1.5% (easier)
        self.pullback_pct = float(config.get("pullback_pct", 2.0))  # 2%
        self.breakout_threshold = float(config.get("breakout_threshold", 1.0))  # 1%
        
        # Position sizing (contest rules: max 55%)
        self.initial_position_pct = float(config.get("initial_position_pct", 0.25))  # 25%
        self.max_position_pct = float(config.get("max_position_pct", 0.55))  # 55% (RULE)
        self.pyramid_size_pct = float(config.get("pyramid_size_pct", 0.15))  # 15%
        
        # Profit taking (BALANCED - capture moves but exit with gains)
        self.profit_levels = [
            float(config.get("profit_level_1", 5.0)),   # 5%
            float(config.get("profit_level_2", 10.0)),  # 10%
            float(config.get("profit_level_3", 20.0))   # 20%
        ]
        self.profit_take_portions = [0.30, 0.30, 0.40]  # 30%, 30%, 40%
        
        # Risk management (BALANCED)
        self.stop_loss_pct = float(config.get("stop_loss_pct", 6.0))  # 6%
        self.trailing_stop_pct = float(config.get("trailing_stop_pct", 4.0))  # 4%
        
        # Trade management (TRADE MORE)
        self.min_trade_spacing_minutes = int(config.get("min_trade_spacing_minutes", 5))  # 5min
        self.max_positions = int(config.get("max_positions", 5))  # 5
        
        # State tracking
        self.positions: List[Dict[str, Any]] = []
        self.last_trade_time: Optional[datetime] = None
        self.highest_price_since_entry: Optional[float] = None
        self.profit_targets_hit: List[bool] = [False, False, False]
        
        self._logger = logging.getLogger("strategy.winning")
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return None
        
        multiplier = 2.0 / (period + 1)
        ema = mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _is_uptrend(self, prices: List[float]) -> Tuple[bool, float]:
        """
        Simple uptrend detection.
        Returns: (is_uptrend, strength)
        """
        if len(prices) < self.ema_slow:
            return False, 0.0
        
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        if ema_fast is None or ema_slow is None:
            return False, 0.0
        
        # Simple criteria: EMA12 > EMA26 and price > EMA12
        if ema_fast > ema_slow and current_price > ema_fast:
            strength = (ema_fast - ema_slow) / ema_slow
            if strength >= self.min_trend_strength:
                return True, strength
        
        return False, 0.0
    
    def _is_pullback(self, prices: List[float]) -> bool:
        """Check for pullback in uptrend."""
        if len(prices) < self.ema_slow + 10:
            return False
        
        current_price = prices[-1]
        recent_high = max(prices[-15:])
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        
        if ema_slow is None:
            return False
        
        pullback_size = (recent_high - current_price) / recent_high * 100
        
        # Pullback range: 1-3%
        return (1.0 <= pullback_size <= 3.0 and current_price > ema_slow)
    
    def _is_breakout(self, prices: List[float]) -> bool:
        """Check for breakout."""
        if len(prices) < 25:
            return False
        
        current_price = prices[-1]
        lookback = prices[-25:-1]
        high_15 = max(lookback[-15:])
        
        if current_price <= high_15:
            return False
        
        breakout_strength = (current_price - high_15) / high_15 * 100
        return breakout_strength >= self.breakout_threshold
    
    def _calculate_position_size(
        self,
        price: float,
        portfolio: Portfolio,
        trend_strength: float,
        is_initial: bool = True
    ) -> float:
        """Calculate position size (contest max: 55%)."""
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        
        if is_initial:
            base_pct = self.initial_position_pct  # 25%
        else:
            base_pct = self.pyramid_size_pct  # 15%
        
        # Slight boost in strong trends
        strength_multiplier = 1.0 + min(trend_strength * 8, 0.3)
        adjusted_pct = base_pct * strength_multiplier
        
        # Check limits
        current_position_value = portfolio.quantity * price
        current_pct = current_position_value / portfolio_value if portfolio_value > 0 else 0
        
        if current_pct >= self.max_position_pct:
            return 0.0
        
        target_value = portfolio_value * adjusted_pct
        max_can_spend = min(target_value, portfolio.cash)
        
        return max_can_spend / price if price > 0 else 0.0
    
    def _should_take_partial_profit(self, current_price: float) -> Optional[Tuple[int, float]]:
        """Take profits at 5%/10%/20%."""
        if not self.positions:
            return None
        
        total_size = sum(p["size"] for p in self.positions)
        if total_size == 0:
            return None
        
        avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
        gain_pct = (current_price - avg_entry) / avg_entry * 100
        
        for i, level in enumerate(self.profit_levels):
            if not self.profit_targets_hit[i] and gain_pct >= level:
                self.profit_targets_hit[i] = True
                return (i, self.profit_take_portions[i])
        
        return None
    
    def _should_stop_loss(self, current_price: float) -> bool:
        """Stop loss: 6%."""
        if not self.positions:
            return False
        
        highest_entry = max(p["price"] for p in self.positions)
        loss_pct = (highest_entry - current_price) / highest_entry * 100
        
        return loss_pct >= self.stop_loss_pct
    
    def _should_trailing_stop(self, current_price: float) -> bool:
        """Trailing stop: 4%."""
        if not self.highest_price_since_entry or not self.positions:
            return False
        
        drop_from_high = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
        return drop_from_high >= self.trailing_stop_pct
    
    def _can_trade(self, now: datetime) -> bool:
        """5min spacing."""
        if self.last_trade_time is None:
            return True
        
        elapsed = now - self.last_trade_time
        return elapsed >= timedelta(minutes=self.min_trade_spacing_minutes)
    
    def _can_pyramid(self, portfolio: Portfolio, price: float) -> bool:
        """Check if can add to position."""
        if len(self.positions) >= self.max_positions:
            return False
        
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        current_position_value = portfolio.quantity * price
        current_pct = current_position_value / portfolio_value if portfolio_value > 0 else 0
        
        if current_pct >= self.max_position_pct:
            return False
        
        # Must be at least breakeven
        if self.positions:
            total_size = sum(p["size"] for p in self.positions)
            avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
            if price < avg_entry:
                return False
        
        return True
    
    def generate_signal(self, market: MarketSnapshot, portfolio: Portfolio) -> Signal:
        """
        WINNING signal generation - TRADES MORE, CAPTURES MOVES
        
        PHILOSOPHY: Enter trends early, take profits at 5%/10%/20%, move on to next trade
        """
        now = market.timestamp if isinstance(market.timestamp, datetime) else datetime.now(timezone.utc)
        current_price = market.current_price
        
        # Need data
        if len(market.prices) < self.ema_slow + 20:
            return Signal("hold", reason="Warming up")
        
        # Update trailing high
        if self.positions and current_price > (self.highest_price_since_entry or 0):
            self.highest_price_since_entry = current_price
        
        # Detect trend
        is_uptrend, trend_strength = self._is_uptrend(market.prices)
        
        # Log
        ema_fast = self._calculate_ema(market.prices, self.ema_fast)
        ema_slow = self._calculate_ema(market.prices, self.ema_slow)
        self._logger.info(
            f"Price: ${current_price:.2f} | EMA12/26: ${ema_fast:.2f}/${ema_slow:.2f} | "
            f"Uptrend: {is_uptrend} | Strength: {trend_strength:.3f}"
        )
        
        # --- EXIT LOGIC ---
        if portfolio.quantity > 0:
            # Stop loss
            if self._should_stop_loss(current_price):
                self._logger.info("🛑 STOP LOSS (6%)")
                return Signal("sell", size=portfolio.quantity, reason="Stop loss")
            
            # Trailing stop
            if self._should_trailing_stop(current_price):
                self._logger.info("🛑 TRAILING STOP (4%)")
                return Signal("sell", size=portfolio.quantity, reason="Trailing stop")
            
            # Partial profits
            partial = self._should_take_partial_profit(current_price)
            if partial:
                level, pct = partial
                sell_size = portfolio.quantity * pct
                self._logger.info(f"💰 PROFIT {self.profit_levels[level]}%")
                return Signal(
                    "sell",
                    size=sell_size,
                    reason=f"Partial profit {self.profit_levels[level]}%"
                )
            
            # Exit if downtrend
            if not is_uptrend:
                self._logger.info("⚠️ DOWNTREND EXIT")
                return Signal("sell", size=portfolio.quantity, reason="Downtrend exit")
        
        # --- ENTRY LOGIC (TRADE MORE!) ---
        if portfolio.cash > 0:
            # Check spacing
            if not self._can_trade(now):
                return Signal("hold", reason="Trade spacing")
            
            # Only trade in uptrends
            if not is_uptrend:
                return Signal("hold", reason="No uptrend")
            
            # ENTRY 1: Direct uptrend entry (NEW - AGGRESSIVE)
            if len(self.positions) == 0:
                size = self._calculate_position_size(
                    current_price, portfolio, trend_strength, is_initial=True
                )
                if size > 0:
                    self._logger.info("🚀 DIRECT UPTREND ENTRY")
                    return Signal(
                        "buy",
                        size=size,
                        reason="Direct uptrend entry",
                        entry_price=current_price
                    )
            
            # ENTRY 2: Pullback entry
            if len(self.positions) == 0 and self._is_pullback(market.prices):
                size = self._calculate_position_size(
                    current_price, portfolio, trend_strength, is_initial=True
                )
                if size > 0:
                    self._logger.info("📉 PULLBACK ENTRY")
                    return Signal(
                        "buy",
                        size=size,
                        reason="Pullback entry",
                        entry_price=current_price
                    )
            
            # ENTRY 3: Breakout entry
            if self._is_breakout(market.prices):
                is_initial = len(self.positions) == 0
                
                if is_initial or self._can_pyramid(portfolio, current_price):
                    size = self._calculate_position_size(
                        current_price, portfolio, trend_strength, is_initial=is_initial
                    )
                    if size > 0:
                        action = "BREAKOUT" if is_initial else "PYRAMID"
                        self._logger.info(f"⚡ {action}")
                        return Signal(
                            "buy",
                            size=size,
                            reason=f"{action} entry",
                            entry_price=current_price
                        )
            
            # ENTRY 4: Pyramid (if profitable)
            if len(self.positions) > 0 and self._can_pyramid(portfolio, current_price):
                total_size = sum(p["size"] for p in self.positions)
                avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
                profit_pct = (current_price - avg_entry) / avg_entry * 100
                
                # Add if 1%+ profitable
                if profit_pct >= 1.0:
                    size = self._calculate_position_size(
                        current_price, portfolio, trend_strength, is_initial=False
                    )
                    if size > 0:
                        self._logger.info("➕ PYRAMID ADD")
                        return Signal(
                            "buy",
                            size=size,
                            reason="Pyramid add",
                            entry_price=current_price
                        )
        
        return Signal("hold", reason="No setup")
    
    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp: datetime) -> None:
        """Update state after trade."""
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        self.last_trade_time = timestamp
        
        if signal.action == "buy" and execution_size > 0:
            position = {
                "price": execution_price,
                "size": execution_size,
                "timestamp": timestamp.isoformat()
            }
            self.positions.append(position)
            
            if self.highest_price_since_entry is None or execution_price > self.highest_price_since_entry:
                self.highest_price_since_entry = execution_price
            
            self._logger.info(f"✅ BUY | ${execution_price:.2f} | {execution_size:.6f}")
        
        elif signal.action == "sell" and execution_size > 0:
            if self.positions:
                total_size = sum(p["size"] for p in self.positions)
                avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
                pnl_pct = (execution_price - avg_entry) / avg_entry * 100
                
                self._logger.info(f"✅ SELL | ${execution_price:.2f} | P&L: {pnl_pct:+.2f}%")
            
            # Remove positions (FIFO)
            remaining = execution_size
            while self.positions and remaining > 0:
                position = self.positions[0]
                if position["size"] <= remaining:
                    remaining -= position["size"]
                    self.positions.pop(0)
                else:
                    position["size"] -= remaining
                    remaining = 0
            
            # Reset on full close
            if not self.positions:
                self.highest_price_since_entry = None
                self.profit_targets_hit = [False, False, False]
    
    def get_state(self) -> Dict[str, Any]:
        """Export state."""
        return {
            "positions": self.positions,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "highest_price_since_entry": self.highest_price_since_entry,
            "profit_targets_hit": self.profit_targets_hit
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.positions = state.get("positions", [])
        
        last_trade = state.get("last_trade_time")
        if last_trade:
            self.last_trade_time = datetime.fromisoformat(last_trade)
        
        self.highest_price_since_entry = state.get("highest_price_since_entry")
        self.profit_targets_hit = state.get("profit_targets_hit", [False, False, False])


# Register winning strategy
register_strategy("winning_trend", lambda cfg, ex: WinningTrendStrategy(cfg, ex))

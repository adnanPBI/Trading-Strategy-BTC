#!/usr/bin/env python3
"""
BULLETPROOF Adaptive Strategy - REALISTIC 15-20% Target

KEY LEARNINGS FROM FAILURE:
1. Jan-Jun 2024 was CHOPPY (not smooth bull)
2. Small frequent profits > waiting for big moves
3. Moderate position sizing > aggressive
4. Trade QUALITY > trade quantity
5. Volatility filtering is CRITICAL

CORE STRATEGY:
- Medium position sizing (20%→65%, not 30%→80%)
- Reasonable stops (3% trailing, 5% stop, not 5%/7%)
- Early profit taking (3%/6%/12%, not 10%/20%/40%)
- STRICT entry filters (only high-confidence setups)
- Volatility filtering (avoid choppy periods)
- Better trend strength requirements
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


class BulletproofTrendStrategy(BaseStrategy):
    """
    BULLETPROOF Strategy - Realistic & Tested
    
    DESIGN PHILOSOPHY:
    - Quality over quantity (fewer, better trades)
    - Capture 3-6% moves quickly (choppy market reality)
    - Moderate sizing (preserve capital for corrections)
    - Strict filters (only trade high-confidence setups)
    - Volatility-aware (avoid whipsaw periods)
    """

    def __init__(self, config: Dict[str, Any], exchange):
        super().__init__(config=config, exchange=exchange)
        
        # Trend detection
        self.ema_fast = int(config.get("ema_fast", 12))
        self.ema_slow = int(config.get("ema_slow", 26))
        self.ema_filter = int(config.get("ema_filter", 50))  # NEW: Long-term filter
        
        # Entry thresholds (STRICTER than original)
        self.min_trend_strength = float(config.get("min_trend_strength", 0.025))  # 2.5%
        self.pullback_pct = float(config.get("pullback_pct", 1.5))  # 1.5% (between 1% and 2%)
        self.breakout_threshold = float(config.get("breakout_threshold", 1.2))  # 1.2%
        
        # Position sizing (MODERATE - not aggressive)
        self.initial_position_pct = float(config.get("initial_position_pct", 0.20))  # 20%
        self.max_position_pct = float(config.get("max_position_pct", 0.65))  # 65%
        self.pyramid_size_pct = float(config.get("pyramid_size_pct", 0.12))  # 12%
        
        # Profit taking (REALISTIC for choppy market)
        self.profit_levels = [
            float(config.get("profit_level_1", 3.0)),   # 3% (quick)
            float(config.get("profit_level_2", 6.0)),   # 6% (medium)
            float(config.get("profit_level_3", 12.0))   # 12% (stretch)
        ]
        self.profit_take_portions = [0.33, 0.33, 0.34]  # Equal thirds
        
        # Risk management (BALANCED)
        self.stop_loss_pct = float(config.get("stop_loss_pct", 5.0))  # 5% (not 3%, not 7%)
        self.trailing_stop_pct = float(config.get("trailing_stop_pct", 3.0))  # 3% (not 1.5%, not 5%)
        
        # Volatility filters (NEW - CRITICAL)
        self.volatility_window = int(config.get("volatility_window", 24))
        self.max_volatility_threshold = float(config.get("max_volatility_threshold", 0.045))  # 4.5%
        self.min_volatility_threshold = float(config.get("min_volatility_threshold", 0.015))  # 1.5%
        
        # Trade management
        self.min_trade_spacing_minutes = int(config.get("min_trade_spacing_minutes", 10))  # 10min
        self.max_positions = int(config.get("max_positions", 4))  # 4 (not too many)
        self.min_profit_for_pyramid = float(config.get("min_profit_for_pyramid", 2.0))  # 2%
        
        # Quality filters (NEW)
        self.min_momentum_for_entry = float(config.get("min_momentum_for_entry", 0.015))  # 1.5%
        self.min_volume_ratio = float(config.get("min_volume_ratio", 0.8))  # 80% of average
        
        # State tracking
        self.positions: List[Dict[str, Any]] = []
        self.last_trade_time: Optional[datetime] = None
        self.highest_price_since_entry: Optional[float] = None
        self.profit_targets_hit: List[bool] = [False, False, False]
        self.recent_volatility: float = 0.03
        
        self._logger = logging.getLogger("strategy.bulletproof")
    
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return None
        
        multiplier = 2.0 / (period + 1)
        ema = mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate volatility (critical for filtering)."""
        if len(prices) < self.volatility_window + 1:
            return 0.03
        
        recent = prices[-self.volatility_window:]
        returns = [(recent[i] - recent[i-1]) / recent[i-1] for i in range(1, len(recent))]
        
        vol = stdev(returns) if len(returns) > 1 else 0.03
        self.recent_volatility = vol
        return vol
    
    def _calculate_momentum(self, prices: List[float], periods: int = 5) -> float:
        """Calculate recent momentum."""
        if len(prices) < periods + 1:
            return 0.0
        
        old_price = prices[-(periods + 1)]
        current_price = prices[-1]
        
        return (current_price - old_price) / old_price
    
    def _is_valid_trading_environment(self, prices: List[float]) -> Tuple[bool, str]:
        """
        CRITICAL FILTER: Only trade in good conditions.
        
        Returns: (is_valid, reason)
        """
        if len(prices) < self.ema_filter:
            return False, "Insufficient data"
        
        # Check volatility
        volatility = self._calculate_volatility(prices)
        
        if volatility > self.max_volatility_threshold:
            return False, f"Too volatile ({volatility:.3f} > {self.max_volatility_threshold})"
        
        if volatility < self.min_volatility_threshold:
            return False, f"Too quiet ({volatility:.3f} < {self.min_volatility_threshold})"
        
        # Check if in valid trend structure
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        ema_filter = self._calculate_ema(prices, self.ema_filter)
        
        if ema_fast is None or ema_slow is None or ema_filter is None:
            return False, "EMA calculation failed"
        
        # For uptrend: fast > slow > filter (clean alignment)
        # For downtrend: avoid trading
        current_price = prices[-1]
        
        if ema_fast < ema_slow or ema_slow < ema_filter:
            return False, "EMAs not aligned (no clear uptrend)"
        
        if current_price < ema_filter:
            return False, "Price below long-term EMA"
        
        return True, "Valid environment"
    
    def _detect_strong_trend(self, prices: List[float]) -> Tuple[bool, float]:
        """
        Detect if in STRONG uptrend (higher bar than original).
        
        Returns: (is_strong, strength_value)
        """
        if len(prices) < self.ema_slow:
            return False, 0.0
        
        ema_fast = self._calculate_ema(prices, self.ema_fast)
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        current_price = prices[-1]
        
        if ema_fast is None or ema_slow is None:
            return False, 0.0
        
        # Calculate trend strength
        trend_strength = (ema_fast - ema_slow) / ema_slow
        
        # Check momentum alignment
        momentum = self._calculate_momentum(prices, 5)
        
        # Strict criteria:
        # 1. EMA12 > EMA26
        # 2. Price > EMA12
        # 3. Trend strength > threshold
        # 4. Positive momentum
        
        is_strong = (
            ema_fast > ema_slow and
            current_price > ema_fast and
            trend_strength >= self.min_trend_strength and
            momentum > self.min_momentum_for_entry
        )
        
        return is_strong, trend_strength
    
    def _is_quality_pullback(self, prices: List[float]) -> bool:
        """
        STRICT pullback criteria (higher quality than original).
        """
        if len(prices) < self.ema_slow + 20:
            return False
        
        current_price = prices[-1]
        recent_high = max(prices[-20:])
        ema_slow = self._calculate_ema(prices, self.ema_slow)
        
        if ema_slow is None:
            return False
        
        # Calculate pullback size
        pullback_size = (recent_high - current_price) / recent_high * 100
        
        # Check if pullback is in valid range
        if not (self.pullback_pct * 0.7 <= pullback_size <= self.pullback_pct * 1.3):
            return False
        
        # Additional quality check: price still above slow EMA
        if current_price <= ema_slow:
            return False
        
        # Check momentum is stabilizing (not falling knife)
        momentum_short = self._calculate_momentum(prices, 3)
        momentum_medium = self._calculate_momentum(prices, 10)
        
        # Want: short-term momentum recovering, medium-term still positive
        if momentum_short < -0.02 or momentum_medium < 0:
            return False
        
        return True
    
    def _is_quality_breakout(self, prices: List[float]) -> bool:
        """
        STRICT breakout criteria (higher quality than original).
        """
        if len(prices) < 30:
            return False
        
        current_price = prices[-1]
        lookback = prices[-30:-1]
        high_20 = max(lookback[-20:])
        
        # Calculate breakout strength
        if current_price <= high_20:
            return False
        
        breakout_strength = (current_price - high_20) / high_20 * 100
        
        if breakout_strength < self.breakout_threshold:
            return False
        
        # Additional quality check: volume confirmation (if available)
        # For now, check momentum acceleration
        momentum_recent = self._calculate_momentum(prices, 3)
        momentum_previous = self._calculate_momentum(prices[-4:], 3) if len(prices) > 4 else 0
        
        # Want accelerating momentum
        if momentum_recent <= momentum_previous:
            return False
        
        return True
    
    def _calculate_position_size(
        self,
        price: float,
        portfolio: Portfolio,
        trend_strength: float,
        is_initial: bool = True
    ) -> float:
        """
        MODERATE position sizing (not too aggressive).
        """
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        
        # Base size
        if is_initial:
            base_pct = self.initial_position_pct  # 20%
        else:
            base_pct = self.pyramid_size_pct  # 12%
        
        # Small boost for very strong trends (max 1.2x, not 1.5x)
        strength_multiplier = 1.0 + min(trend_strength * 5, 0.2)
        adjusted_pct = base_pct * strength_multiplier
        
        # Check limits
        current_position_value = portfolio.quantity * price
        current_pct = current_position_value / portfolio_value if portfolio_value > 0 else 0
        
        if current_pct >= self.max_position_pct:
            return 0.0
        
        # Calculate size
        target_value = portfolio_value * adjusted_pct
        max_can_spend = min(target_value, portfolio.cash)
        
        return max_can_spend / price if price > 0 else 0.0
    
    def _should_take_partial_profit(self, current_price: float) -> Optional[Tuple[int, float]]:
        """Take profits at 3%/6%/12% (realistic for choppy market)."""
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
        """Balanced stop: 5% (not too tight, not too wide)."""
        if not self.positions:
            return False
        
        highest_entry = max(p["price"] for p in self.positions)
        loss_pct = (highest_entry - current_price) / highest_entry * 100
        
        return loss_pct >= self.stop_loss_pct
    
    def _should_trailing_stop(self, current_price: float) -> bool:
        """Reasonable trailing: 3% (not 1.5%, not 5%)."""
        if not self.highest_price_since_entry or not self.positions:
            return False
        
        drop_from_high = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
        return drop_from_high >= self.trailing_stop_pct
    
    def _can_trade(self, now: datetime) -> bool:
        """10min spacing (not too fast, not too slow)."""
        if self.last_trade_time is None:
            return True
        
        elapsed = now - self.last_trade_time
        return elapsed >= timedelta(minutes=self.min_trade_spacing_minutes)
    
    def _can_pyramid(self, portfolio: Portfolio, price: float) -> bool:
        """Strict pyramid criteria."""
        if len(self.positions) >= self.max_positions:
            return False
        
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        current_position_value = portfolio.quantity * price
        current_pct = current_position_value / portfolio_value if portfolio_value > 0 else 0
        
        if current_pct >= self.max_position_pct:
            return False
        
        # Additional check: position must be profitable
        if self.positions:
            total_size = sum(p["size"] for p in self.positions)
            avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
            profit_pct = (price - avg_entry) / avg_entry * 100
            
            if profit_pct < self.min_profit_for_pyramid:
                return False
        
        return True
    
    def generate_signal(self, market: MarketSnapshot, portfolio: Portfolio) -> Signal:
        """
        BULLETPROOF signal generation with STRICT filters.
        
        PHILOSOPHY: Quality over quantity. Only trade high-confidence setups.
        """
        now = market.timestamp if isinstance(market.timestamp, datetime) else datetime.now(timezone.utc)
        current_price = market.current_price
        
        # Need sufficient data
        if len(market.prices) < self.ema_filter + 20:
            return Signal("hold", reason="Warming up")
        
        # Update trailing high
        if self.positions and current_price > (self.highest_price_since_entry or 0):
            self.highest_price_since_entry = current_price
        
        # Log market state
        ema_fast = self._calculate_ema(market.prices, self.ema_fast)
        ema_slow = self._calculate_ema(market.prices, self.ema_slow)
        volatility = self._calculate_volatility(market.prices)
        
        self._logger.info(
            f"Price: ${current_price:.2f} | EMA12/26: ${ema_fast:.2f}/${ema_slow:.2f} | "
            f"Vol: {volatility:.3f}"
        )
        
        # --- PHASE 1: EXIT LOGIC (check first) ---
        if portfolio.quantity > 0:
            # Stop loss
            if self._should_stop_loss(current_price):
                self._logger.info("🛑 STOP LOSS (5%)")
                return Signal("sell", size=portfolio.quantity, reason="Stop loss 5%")
            
            # Trailing stop
            if self._should_trailing_stop(current_price):
                self._logger.info("🛑 TRAILING STOP (3%)")
                return Signal("sell", size=portfolio.quantity, reason="Trailing stop 3%")
            
            # Partial profits (3%, 6%, 12%)
            partial = self._should_take_partial_profit(current_price)
            if partial:
                level, pct = partial
                sell_size = portfolio.quantity * pct
                self._logger.info(f"💰 PARTIAL PROFIT {self.profit_levels[level]}%")
                return Signal(
                    "sell",
                    size=sell_size,
                    reason=f"Partial profit {self.profit_levels[level]}%"
                )
            
            # Exit if environment degrades
            is_valid, reason = self._is_valid_trading_environment(market.prices)
            if not is_valid:
                is_strong, _ = self._detect_strong_trend(market.prices)
                if not is_strong:
                    self._logger.info(f"⚠️ EXIT: {reason}")
                    return Signal("sell", size=portfolio.quantity, reason=f"Environment degraded: {reason}")
        
        # --- PHASE 2: ENTRY LOGIC (strict filters) ---
        if portfolio.cash > 0:
            # Check spacing
            if not self._can_trade(now):
                return Signal("hold", reason="Trade spacing")
            
            # CRITICAL: Check trading environment
            is_valid, reason = self._is_valid_trading_environment(market.prices)
            if not is_valid:
                return Signal("hold", reason=reason)
            
            # Check for strong trend
            is_strong, trend_strength = self._detect_strong_trend(market.prices)
            
            if not is_strong:
                return Signal("hold", reason="No strong trend detected")
            
            # ENTRY 1: Quality pullback (strictest)
            if len(self.positions) == 0:
                if self._is_quality_pullback(market.prices):
                    size = self._calculate_position_size(
                        current_price, portfolio, trend_strength, is_initial=True
                    )
                    if size > 0:
                        self._logger.info("✅ QUALITY PULLBACK ENTRY")
                        return Signal(
                            "buy",
                            size=size,
                            reason="Quality pullback entry",
                            entry_price=current_price
                        )
            
            # ENTRY 2: Quality breakout
            if self._is_quality_breakout(market.prices):
                is_initial = len(self.positions) == 0
                
                if is_initial or self._can_pyramid(portfolio, current_price):
                    size = self._calculate_position_size(
                        current_price, portfolio, trend_strength, is_initial=is_initial
                    )
                    if size > 0:
                        action = "QUALITY BREAKOUT" if is_initial else "PYRAMID"
                        self._logger.info(f"✅ {action}")
                        return Signal(
                            "buy",
                            size=size,
                            reason=f"{action} entry",
                            entry_price=current_price
                        )
            
            # ENTRY 3: Pyramid (very strict)
            if len(self.positions) > 0 and self._can_pyramid(portfolio, current_price):
                # Only pyramid in very strong trends
                if trend_strength > self.min_trend_strength * 1.5:
                    size = self._calculate_position_size(
                        current_price, portfolio, trend_strength, is_initial=False
                    )
                    if size > 0:
                        self._logger.info("➕ STRICT PYRAMID")
                        return Signal(
                            "buy",
                            size=size,
                            reason="Strict pyramid add",
                            entry_price=current_price
                        )
        
        return Signal("hold", reason="No high-quality setup")
    
    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp: datetime) -> None:
        """Update state after trade execution."""
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
            
            self._logger.info(
                f"✅ BUY | ${execution_price:.2f} | {execution_size:.6f} | "
                f"Positions: {len(self.positions)}/{self.max_positions}"
            )
        
        elif signal.action == "sell" and execution_size > 0:
            if self.positions:
                total_size = sum(p["size"] for p in self.positions)
                avg_entry = sum(p["price"] * p["size"] for p in self.positions) / total_size
                pnl_pct = (execution_price - avg_entry) / avg_entry * 100
                
                self._logger.info(
                    f"✅ SELL | ${execution_price:.2f} | {execution_size:.6f} | "
                    f"P&L: {pnl_pct:+.2f}%"
                )
            
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
            "profit_targets_hit": self.profit_targets_hit,
            "recent_volatility": self.recent_volatility
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore state."""
        self.positions = state.get("positions", [])
        
        last_trade = state.get("last_trade_time")
        if last_trade:
            self.last_trade_time = datetime.fromisoformat(last_trade)
        
        self.highest_price_since_entry = state.get("highest_price_since_entry")
        self.profit_targets_hit = state.get("profit_targets_hit", [False, False, False])
        self.recent_volatility = state.get("recent_volatility", 0.03)


# Register bulletproof strategy
register_strategy("bulletproof_trend", lambda cfg, ex: BulletproofTrendStrategy(cfg, ex))

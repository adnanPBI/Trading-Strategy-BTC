#!/usr/bin/env python3
"""Momentum Mean Reversion Strategy - Contest Submission.

A sophisticated trading strategy combining:
- RSI-based oversold/overbought detection
- Moving average trend confirmation
- Volatility-adaptive position sizing
- Dynamic stop-loss and take-profit management
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
from typing import Any, Deque, Dict, Optional, List
from collections import deque
import logging

# Import base infrastructure from base-bot-template
import sys
import os

# Handle both local development and Docker container paths
base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    # In Docker container, base template is at /app/base/
    base_path = '/app/base'

sys.path.insert(0, base_path)

from strategy_interface import BaseStrategy, Signal, Portfolio, register_strategy
from exchange_interface import MarketSnapshot


class MomentumReversionStrategy(BaseStrategy):
    """
    Momentum Mean Reversion Strategy with adaptive risk management.
    
    CORE LOGIC:
    1. RSI Signals: Buy when oversold (RSI < 30), sell when overbought (RSI > 70)
    2. Trend Filter: Use moving averages to confirm trend direction
    3. Position Sizing: Scale based on market volatility
    4. Risk Management: Dynamic stop-loss and take-profit bands
    """

    def __init__(self, config: Dict[str, Any], exchange):
        super().__init__(config=config, exchange=exchange)
        
        # Strategy parameters (configurable via config)
        self.rsi_period = int(config.get("rsi_period", 14))
        self.rsi_oversold = float(config.get("rsi_oversold", 30))
        self.rsi_overbought = float(config.get("rsi_overbought", 70))
        
        self.sma_short = int(config.get("sma_short", 20))
        self.sma_long = int(config.get("sma_long", 50))
        
        self.base_position_size = float(config.get("base_position_size", 0.15))  # 15% of capital
        self.max_position_size = float(config.get("max_position_size", 0.40))    # 40% max
        
        self.take_profit_pct = float(config.get("take_profit_pct", 4.0))
        self.stop_loss_pct = float(config.get("stop_loss_pct", 2.5))
        self.trailing_stop_pct = float(config.get("trailing_stop_pct", 2.0))
        
        self.volatility_window = int(config.get("volatility_window", 30))
        self.min_trade_spacing_minutes = int(config.get("min_trade_spacing_minutes", 30))
        
        # State tracking
        self.entries: List[Dict[str, Any]] = []
        self.last_trade_time: Optional[datetime] = None
        self.highest_price_since_entry: Optional[float] = None
        
        self._logger = logging.getLogger("strategy.momentum_reversion")
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(len(prices) - period, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = mean(gains) if gains else 0
        avg_loss = mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return mean(prices[-period:])
    
    def _calculate_volatility(self, prices: List[float], window: int = 30) -> float:
        """Calculate price volatility (standard deviation of returns)."""
        if len(prices) < window + 1:
            return 0.02  # Default 2% volatility
        
        recent_prices = prices[-window:]
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i - 1] > 0:
                returns.append((recent_prices[i] - recent_prices[i - 1]) / recent_prices[i - 1])
        
        return pstdev(returns) if len(returns) > 1 else 0.02
    
    def _adaptive_position_size(self, volatility: float, portfolio: Portfolio, price: float) -> float:
        """Calculate position size based on volatility - higher vol = smaller position."""
        # Normalize volatility (typical crypto daily vol is 2-5%)
        vol_factor = max(0.5, min(1.5, 1.0 - (volatility - 0.02) * 10))
        
        # Base position as percentage of portfolio value
        portfolio_value = portfolio.cash + (portfolio.quantity * price)
        target_notional = portfolio_value * self.base_position_size * vol_factor
        
        # Cap at max position size
        max_notional = portfolio_value * self.max_position_size
        target_notional = min(target_notional, max_notional)
        
        # Ensure we have enough cash
        target_notional = min(target_notional, portfolio.cash)
        
        return target_notional / price if price > 0 else 0
    
    def _should_take_profit(self, current_price: float) -> bool:
        """Check if we should take profit based on entry price."""
        if not self.entries:
            return False
        
        avg_entry = mean([e["price"] for e in self.entries])
        gain_pct = (current_price - avg_entry) / avg_entry * 100
        
        return gain_pct >= self.take_profit_pct
    
    def _should_stop_loss(self, current_price: float) -> bool:
        """Check if stop-loss should be triggered."""
        if not self.entries:
            return False
        
        avg_entry = mean([e["price"] for e in self.entries])
        loss_pct = (avg_entry - current_price) / avg_entry * 100
        
        return loss_pct >= self.stop_loss_pct
    
    def _should_trailing_stop(self, current_price: float) -> bool:
        """Check trailing stop condition."""
        if not self.highest_price_since_entry or not self.entries:
            return False
        
        drop_from_high = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
        return drop_from_high >= self.trailing_stop_pct
    
    def _can_trade(self, now: datetime) -> bool:
        """Check if enough time has passed since last trade."""
        if self.last_trade_time is None:
            return True
        
        elapsed = now - self.last_trade_time
        return elapsed >= timedelta(minutes=self.min_trade_spacing_minutes)
    
    def generate_signal(self, market: MarketSnapshot, portfolio: Portfolio) -> Signal:
        """Main strategy logic - generates buy/sell/hold signals."""
        now = market.timestamp if isinstance(market.timestamp, datetime) else datetime.now(timezone.utc)
        current_price = market.current_price
        
        # Ensure we have enough data
        if len(market.prices) < max(self.rsi_period + 1, self.sma_long):
            return Signal("hold", reason="Warming up - insufficient price history")
        
        # Calculate indicators
        rsi = self._calculate_rsi(market.prices, self.rsi_period)
        sma_short = self._calculate_sma(market.prices, self.sma_short)
        sma_long = self._calculate_sma(market.prices, self.sma_long)
        volatility = self._calculate_volatility(market.prices, self.volatility_window)
        
        if rsi is None or sma_short is None or sma_long is None:
            return Signal("hold", reason="Indicators not ready")
        
        # Log current state
        self._logger.info(f"Market State | Price: ${current_price:.2f} | RSI: {rsi:.2f} | "
                         f"SMA20: ${sma_short:.2f} | SMA50: ${sma_long:.2f} | Vol: {volatility:.4f}")
        
        # Update trailing high
        if self.entries and current_price > (self.highest_price_since_entry or 0):
            self.highest_price_since_entry = current_price
        
        # --- SELL LOGIC ---
        if portfolio.quantity > 0:
            # Take profit check
            if self._should_take_profit(current_price):
                sell_size = portfolio.quantity
                avg_entry = mean([e["price"] for e in self.entries])
                gain = (current_price - avg_entry) / avg_entry * 100
                self._logger.info(f"TAKE PROFIT | Gain: {gain:.2f}% | Size: {sell_size:.8f}")
                return Signal("sell", size=sell_size, reason=f"Take profit at {gain:.2f}%")
            
            # Stop loss check
            if self._should_stop_loss(current_price):
                sell_size = portfolio.quantity
                avg_entry = mean([e["price"] for e in self.entries])
                loss = (avg_entry - current_price) / avg_entry * 100
                self._logger.info(f"STOP LOSS | Loss: {loss:.2f}% | Size: {sell_size:.8f}")
                return Signal("sell", size=sell_size, reason=f"Stop loss at {loss:.2f}%")
            
            # Trailing stop check
            if self._should_trailing_stop(current_price):
                sell_size = portfolio.quantity
                drop = (self.highest_price_since_entry - current_price) / self.highest_price_since_entry * 100
                self._logger.info(f"TRAILING STOP | Drop from high: {drop:.2f}% | Size: {sell_size:.8f}")
                return Signal("sell", size=sell_size, reason=f"Trailing stop - drop {drop:.2f}%")
            
            # Overbought exit (RSI signal)
            if rsi > self.rsi_overbought and current_price > sma_short:
                sell_size = portfolio.quantity
                self._logger.info(f"RSI OVERBOUGHT EXIT | RSI: {rsi:.2f} | Size: {sell_size:.8f}")
                return Signal("sell", size=sell_size, reason=f"RSI overbought at {rsi:.2f}")
        
        # --- BUY LOGIC ---
        if portfolio.cash > 0:
            # Check trade spacing
            if not self._can_trade(now):
                return Signal("hold", reason="Trade spacing cooldown")
            
            # RSI Oversold signal
            is_oversold = rsi < self.rsi_oversold
            
            # Trend confirmation: price above short-term MA or short MA trending up
            trend_up = sma_short > sma_long or current_price > sma_short
            
            if is_oversold and trend_up:
                # Calculate position size based on volatility
                size = self._adaptive_position_size(volatility, portfolio, current_price)
                
                if size > 0:
                    # Calculate entry targets for logging
                    target_price = current_price * (1 + self.take_profit_pct / 100)
                    stop_price = current_price * (1 - self.stop_loss_pct / 100)
                    
                    self._logger.info(f"BUY SIGNAL | RSI: {rsi:.2f} | Size: {size:.8f} | "
                                    f"Target: ${target_price:.2f} | Stop: ${stop_price:.2f}")
                    
                    return Signal(
                        "buy", 
                        size=size, 
                        reason=f"RSI oversold ({rsi:.2f}) + trend up",
                        target_price=target_price,
                        stop_loss=stop_price,
                        entry_price=current_price
                    )
        
        return Signal("hold", reason="No trading conditions met")
    
    def on_trade(self, signal: Signal, execution_price: float, execution_size: float, timestamp: datetime) -> None:
        """Called after trade execution - update internal state."""
        # Ensure timestamp is timezone-aware
        if isinstance(timestamp, datetime) and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        self.last_trade_time = timestamp
        
        if signal.action == "buy" and execution_size > 0:
            entry = {
                "price": execution_price,
                "size": execution_size,
                "timestamp": timestamp.isoformat()
            }
            self.entries.append(entry)
            
            # Initialize trailing high
            if self.highest_price_since_entry is None:
                self.highest_price_since_entry = execution_price
            
            self._logger.info(f"BUY EXECUTED | Price: ${execution_price:.2f} | Size: {execution_size:.8f}")
        
        elif signal.action == "sell" and execution_size > 0:
            # Calculate profit/loss
            if self.entries:
                avg_entry = mean([e["price"] for e in self.entries])
                pnl_pct = (execution_price - avg_entry) / avg_entry * 100
                self._logger.info(f"SELL EXECUTED | Price: ${execution_price:.2f} | "
                                f"Size: {execution_size:.8f} | PnL: {pnl_pct:+.2f}%")
            
            # Remove closed positions
            remaining = execution_size
            while self.entries and remaining > 0:
                position = self.entries[0]
                if position["size"] <= remaining:
                    remaining -= position["size"]
                    self.entries.pop(0)
                else:
                    position["size"] -= remaining
                    remaining = 0
            
            # Reset trailing high if all positions closed
            if not self.entries:
                self.highest_price_since_entry = None
    
    def get_state(self) -> Dict[str, Any]:
        """Export strategy state for persistence."""
        return {
            "entries": self.entries,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None,
            "highest_price_since_entry": self.highest_price_since_entry
        }
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore strategy state from persistence."""
        self.entries = state.get("entries", [])
        
        last_trade = state.get("last_trade_time")
        if last_trade:
            self.last_trade_time = datetime.fromisoformat(last_trade)
        
        self.highest_price_since_entry = state.get("highest_price_since_entry")


# Register the strategy
register_strategy("momentum_reversion", lambda cfg, ex: MomentumReversionStrategy(cfg, ex))

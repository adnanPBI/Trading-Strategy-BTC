#!/usr/bin/env python3
"""Momentum Mean Reversion Strategy - Contest Entry Point."""

from __future__ import annotations

import sys
import os

# Import base infrastructure from base-bot-template
base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    # In Docker container, base template is at /app/base/
    base_path = '/app/base'

sys.path.insert(0, base_path)

# Import our strategy (this registers it)
import momentum_reversion_strategy

# Import base bot infrastructure
from universal_bot import UniversalBot


def main() -> None:
    """Main entry point for Momentum Reversion Trading Bot."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    bot = UniversalBot(config_path)

    # Print startup info
    print("=" * 60)
    print("🚀 MOMENTUM MEAN REVERSION STRATEGY")
    print("=" * 60)
    print(f"🆔 Bot ID: {bot.config.bot_instance_id}")
    print(f"👤 User ID: {bot.config.user_id}")
    print(f"📈 Strategy: {bot.config.strategy}")
    print(f"💰 Symbol: {bot.config.symbol}")
    print(f"🏦 Exchange: {bot.config.exchange}")
    print(f"💵 Starting Cash: ${bot.config.starting_cash:,.2f}")
    print()
    print("📊 Strategy Features:")
    print("  • RSI-based oversold/overbought detection")
    print("  • Moving average trend confirmation")
    print("  • Volatility-adaptive position sizing")
    print("  • Dynamic stop-loss and take-profit")
    print("  • Trailing stop protection")
    print("=" * 60)

    bot.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Adaptive Trend Following Strategy - PROFIT-FOCUSED Contest Entry."""

from __future__ import annotations

import sys
import os

# Import base infrastructure
base_path = os.path.join(os.path.dirname(__file__), '..', 'base-bot-template')
if not os.path.exists(base_path):
    base_path = '/app/base'

sys.path.insert(0, base_path)

# Import NEW profitable strategy
import adaptive_trend_strategy

# Import base bot infrastructure
from universal_bot import UniversalBot


def main() -> None:
    """Main entry point for Adaptive Trend Strategy."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else None

    bot = UniversalBot(config_path)

    # Print startup info
    print("=" * 60)
    print("🚀 ADAPTIVE TREND FOLLOWING STRATEGY - PROFIT EDITION")
    print("=" * 60)
    print(f"🆔 Bot ID: {bot.config.bot_instance_id}")
    print(f"👤 User ID: {bot.config.user_id}")
    print(f"📈 Strategy: {bot.config.strategy}")
    print(f"💰 Symbol: {bot.config.symbol}")
    print(f"🏦 Exchange: {bot.config.exchange}")
    print(f"💵 Starting Cash: ${bot.config.starting_cash:,.2f}")
    print()
    print("📊 Strategy Features (REDESIGNED FOR PROFITS):")
    print("  ✅ Trend following (not mean reversion)")
    print("  ✅ Pullback entries in uptrends")
    print("  ✅ Breakout detection & entries")
    print("  ✅ Position pyramiding (add to winners)")
    print("  ✅ Partial profit taking (2%, 4%, 8%)")
    print("  ✅ Aggressive trailing stops (1.5%)")
    print("  ✅ Fast trade execution (15min spacing)")
    print("=" * 60)

    bot.run()


if __name__ == "__main__":
    main()

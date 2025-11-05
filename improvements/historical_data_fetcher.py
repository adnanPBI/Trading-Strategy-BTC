#!/usr/bin/env python3
"""
Real Historical Data Fetcher for BTC Trading Strategy
Priority: CRITICAL
Estimated Time: 4-6 hours
Impact: Makes backtest results reliable and realistic
"""

import requests
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging


class HistoricalDataFetcher:
    """
    Fetch real historical OHLCV data from Coinbase Pro API.

    Features:
    - Handles API rate limits
    - Chunks large date ranges
    - Caches results to disk
    - Fallback to saved data
    """

    def __init__(self, cache_dir: str = "./data_cache"):
        self.coinbase_url = "https://api.exchange.coinbase.com"
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)

        # Create cache directory
        import os
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_coinbase_candles(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        granularity: int = 3600,  # 1 hour
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Fetch historical candles from Coinbase Pro API.

        Args:
            symbol: Trading pair (e.g., "BTC-USD")
            start_date: ISO format "2024-01-01T00:00:00Z"
            end_date: ISO format "2024-06-30T23:59:59Z"
            granularity: Candle size in seconds (3600 = 1 hour)
            use_cache: Whether to use cached data if available

        Returns:
            List of candle dictionaries with OHLCV data
        """
        # Check cache first
        cache_filename = f"{self.cache_dir}/{symbol}_{start_date[:10]}_{end_date[:10]}_{granularity}.json"

        if use_cache:
            cached_data = self._load_from_cache(cache_filename)
            if cached_data:
                self.logger.info(f"Loaded {len(cached_data)} candles from cache")
                return cached_data

        self.logger.info(f"Fetching {symbol} data from {start_date} to {end_date}")

        # Parse dates
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))

        # Coinbase limits to 300 candles per request
        # Calculate chunk size based on granularity
        max_candles_per_request = 300
        chunk_duration_seconds = max_candles_per_request * granularity

        all_candles = []
        current = start
        request_count = 0

        while current < end:
            # Calculate next chunk end
            next_time = min(
                current + timedelta(seconds=chunk_duration_seconds),
                end
            )

            # Fetch chunk
            try:
                chunk_candles = self._fetch_chunk(
                    symbol=symbol,
                    start=current,
                    end=next_time,
                    granularity=granularity
                )

                all_candles.extend(chunk_candles)

                self.logger.info(
                    f"Fetched {len(chunk_candles)} candles "
                    f"({current.date()} to {next_time.date()}) "
                    f"- Total: {len(all_candles)}"
                )

                request_count += 1

                # Rate limiting: Coinbase allows ~10 requests/second
                # Be conservative with 3 requests/second
                if request_count % 3 == 0:
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error fetching chunk: {e}")
                # Continue with next chunk

            current = next_time

        # Sort by timestamp
        all_candles.sort(key=lambda x: x['timestamp'])

        # Save to cache
        self._save_to_cache(cache_filename, all_candles)

        self.logger.info(f"Fetched total of {len(all_candles)} candles")

        return all_candles

    def _fetch_chunk(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        granularity: int
    ) -> List[Dict]:
        """Fetch a single chunk of candles from Coinbase API."""
        url = f"{self.coinbase_url}/products/{symbol}/candles"

        params = {
            'start': start.isoformat(),
            'end': end.isoformat(),
            'granularity': granularity
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        # Coinbase returns [[time, low, high, open, close, volume], ...]
        raw_candles = response.json()

        # Convert to our format
        candles = []
        for candle in raw_candles:
            candles.append({
                'timestamp': datetime.fromtimestamp(candle[0], tz=timezone.utc),
                'open': float(candle[3]),
                'high': float(candle[2]),
                'low': float(candle[1]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })

        return candles

    def _save_to_cache(self, filename: str, candles: List[Dict]):
        """Save candles to cache file."""
        # Convert datetime to ISO string for JSON serialization
        serializable = []
        for candle in candles:
            c = candle.copy()
            c['timestamp'] = c['timestamp'].isoformat()
            serializable.append(c)

        with open(filename, 'w') as f:
            json.dump(serializable, f, indent=2)

        self.logger.info(f"Saved {len(candles)} candles to cache: {filename}")

    def _load_from_cache(self, filename: str) -> Optional[List[Dict]]:
        """Load candles from cache file if it exists."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)

            # Convert ISO strings back to datetime
            for candle in data:
                candle['timestamp'] = datetime.fromisoformat(candle['timestamp'])

            return data

        except FileNotFoundError:
            return None
        except Exception as e:
            self.logger.error(f"Error loading cache: {e}")
            return None

    def validate_data(self, candles: List[Dict]) -> Dict[str, any]:
        """
        Validate fetched data for completeness and quality.

        Returns dict with validation results.
        """
        if not candles:
            return {
                'valid': False,
                'error': 'No candles provided',
                'issues': []
            }

        issues = []

        # Check for gaps
        sorted_candles = sorted(candles, key=lambda x: x['timestamp'])

        expected_interval = timedelta(hours=1)  # Assuming hourly data
        gaps = []

        for i in range(1, len(sorted_candles)):
            actual_interval = sorted_candles[i]['timestamp'] - sorted_candles[i-1]['timestamp']

            if actual_interval > expected_interval * 1.5:  # Allow some tolerance
                gaps.append({
                    'after': sorted_candles[i-1]['timestamp'],
                    'before': sorted_candles[i]['timestamp'],
                    'size_hours': actual_interval.total_seconds() / 3600
                })

        if gaps:
            issues.append(f"Found {len(gaps)} gaps in data")

        # Check for unrealistic prices
        prices = [c['close'] for c in candles]

        for i in range(1, len(prices)):
            change_pct = abs(prices[i] - prices[i-1]) / prices[i-1] * 100

            if change_pct > 20:  # More than 20% change in 1 hour
                issues.append(f"Suspicious price move at {sorted_candles[i]['timestamp']}: {change_pct:.1f}%")

        # Check for zero volumes
        zero_volume_count = sum(1 for c in candles if c['volume'] == 0)
        if zero_volume_count > 0:
            issues.append(f"{zero_volume_count} candles with zero volume")

        return {
            'valid': len(issues) == 0,
            'total_candles': len(candles),
            'date_range': {
                'start': sorted_candles[0]['timestamp'],
                'end': sorted_candles[-1]['timestamp']
            },
            'gaps': len(gaps),
            'issues': issues
        }


def example_usage():
    """Example of how to use the HistoricalDataFetcher."""

    # Initialize fetcher
    fetcher = HistoricalDataFetcher(cache_dir="./historical_data")

    # Fetch BTC-USD data for Jan-Jun 2024
    candles = fetcher.fetch_coinbase_candles(
        symbol="BTC-USD",
        start_date="2024-01-01T00:00:00Z",
        end_date="2024-06-30T23:59:59Z",
        granularity=3600,  # 1 hour
        use_cache=True
    )

    # Validate data
    validation = fetcher.validate_data(candles)

    print("\n" + "="*60)
    print("DATA VALIDATION RESULTS")
    print("="*60)
    print(f"Total Candles: {validation['total_candles']}")
    print(f"Date Range: {validation['date_range']['start']} to {validation['date_range']['end']}")
    print(f"Valid: {'✅ YES' if validation['valid'] else '❌ NO'}")

    if validation['gaps'] > 0:
        print(f"Gaps Found: {validation['gaps']}")

    if validation['issues']:
        print("\nIssues:")
        for issue in validation['issues']:
            print(f"  - {issue}")

    # Print sample candles
    print("\n" + "="*60)
    print("SAMPLE DATA (First 5 candles)")
    print("="*60)
    for i, candle in enumerate(candles[:5]):
        print(f"{i+1}. {candle['timestamp']} | "
              f"O: ${candle['open']:,.2f} | "
              f"H: ${candle['high']:,.2f} | "
              f"L: ${candle['low']:,.2f} | "
              f"C: ${candle['close']:,.2f} | "
              f"V: {candle['volume']:,.0f}")

    return candles


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run example
    candles = example_usage()

    print(f"\n✅ Successfully fetched {len(candles)} candles")
    print("Data cached for future use")

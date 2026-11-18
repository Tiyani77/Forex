"""Collect separately versioned forward research signals on completed bars.

Run with --dry-run to preview. WAIT signals are counted but not saved by
default. Historical completed bars are not backfilled as new predictions.
"""
import argparse
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf
from prediction_store import config, prediction_exists, save_prediction
from forecast_engine import latest_signal
from signal_models import (
    BASELINE_VERSION, MOMENTUM_VERSION, CHANNEL_VERSION,
    SUPPLY_DEMAND_VERSION, STRUCTURE_VERSION, LIQUIDITY_SWEEP_VERSION,
    CONFLUENCE_VERSION,
    apply_research_model,
)

MARKETS = {
    'EUR/USD':'EURUSD=X','GBP/USD':'GBPUSD=X','USD/JPY':'JPY=X',
    'USD/CHF':'CHF=X','AUD/USD':'AUDUSD=X','USD/CAD':'CAD=X',
    'NZD/USD':'NZDUSD=X','EUR/GBP':'EURGBP=X','EUR/JPY':'EURJPY=X',
    'GBP/JPY':'GBPJPY=X','EUR/AUD':'EURAUD=X','AUD/JPY':'AUDJPY=X',
    'GBP/AUD':'GBPAUD=X','EUR/CHF':'EURCHF=X','NZD/JPY':'NZDJPY=X',
    'USD/ZAR':'ZAR=X','USD/MXN':'MXN=X','USD/TRY':'TRY=X',
    'USD/SGD':'SGD=X','Gold Futures':'GC=F','Silver Futures':'SI=F',
    'S&P 500':'^GSPC','NASDAQ 100':'^NDX','Dow Jones':'^DJI',
    'DAX':'^GDAXI','BTC/USD':'BTC-USD','ETH/USD':'ETH-USD',
    'SOL/USD':'SOL-USD',
}
TIMEFRAMES = {'1d':('1d','2y')}  # Start with daily only; add intraday after validation.
MODEL_VERSION = BASELINE_VERSION
HORIZON_BARS = 5


def download(ticker, interval, period):
    df = yf.download(ticker, interval=interval, period=period,
                     auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if not {'Open','High','Low','Close'}.issubset(df.columns):
        return pd.DataFrame()
    df = df.dropna(subset=['Open','High','Low','Close']).sort_index()
    return df[~df.index.duplicated(keep='last')]


def prediction(name, ticker, timeframe, df, model_version=BASELINE_VERSION):
    if timeframe != "1d":
        raise ValueError("Collector supports completed daily candles only")
    signal = latest_signal(df, model_version, timeframe="1d")
    if signal is None:
        return None
    return {
        "instrument": name, "ticker": ticker, "timeframe": timeframe,
        "signal": signal["signal"], "model_version": model_version,
        "signal_bar_at": signal["signal_bar_at"],
        "reference_close": signal["reference_close"],
        "horizon_bars": HORIZON_BARS,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Print candidates without saving to Supabase')
    parser.add_argument('--include-wait', action='store_true',
                        help='Also store WAIT abstentions (default: BUY/SELL only)')
    args = parser.parse_args()
    if not args.dry_run and not config():
        raise RuntimeError('Supabase environment variables are missing')
    existing = set()  # in-run duplicate guard; persistent check queries Supabase
    counts = {'saved':0, 'duplicate':0, 'wait_skipped':0, 'errors':0, 'candidates':0}
    model_counts = {}
    latest_bar_by_market = {}
    now = pd.Timestamp.now(tz="UTC")
    for timeframe, (interval, period) in TIMEFRAMES.items():
        for name, ticker in MARKETS.items():
            try:
                candles = download(ticker, interval, period)
            except Exception as exc:
                counts['errors'] += 1
                print(f'ERROR downloading {name} {timeframe}: {type(exc).__name__}: {exc}')
                continue

            for model_version in (
                BASELINE_VERSION, MOMENTUM_VERSION,
                CHANNEL_VERSION, SUPPLY_DEMAND_VERSION, STRUCTURE_VERSION,
                LIQUIDITY_SWEEP_VERSION, CONFLUENCE_VERSION,
            ):
                try:
                    payload = prediction(name, ticker, timeframe, candles, model_version)
                    if payload is None:
                        print(f'{name} {timeframe}: insufficient candles')
                        continue
                    counts['candidates'] += 1
                    model_row = model_counts.setdefault(
                        model_version, {'BUY': 0, 'SELL': 0, 'WAIT': 0}
                    )
                    model_row[payload['signal']] += 1
                    latest_bar_by_market[name] = payload['signal_bar_at']
                    print(f"{name} {timeframe} {model_version}: {payload['signal']} @ {payload['signal_bar_at']}")
                    if payload['signal'] == 'WAIT' and not args.include_wait:
                        counts['wait_skipped'] += 1
                        continue
                    key = (ticker, timeframe,
                           str(pd.Timestamp(payload['signal_bar_at']).tz_convert('UTC')),
                           model_version, HORIZON_BARS)
                    if key in existing:
                        counts['duplicate'] += 1
                        continue
                    if not args.dry_run:
                        if prediction_exists(
                            ticker, timeframe, payload['signal_bar_at'],
                            model_version, HORIZON_BARS,
                        ):
                            counts['duplicate'] += 1
                            existing.add(key)
                            continue
                        save_prediction(payload)
                        existing.add(key)
                        counts['saved'] += 1
                except Exception as exc:
                    counts['errors'] += 1
                    print(f'ERROR {name} {timeframe} {model_version}: {type(exc).__name__}: {exc}')
    print('Collection summary:', counts)
    print('Research signal coverage (including WAIT abstentions):')
    for version, row in sorted(model_counts.items()):
        total = sum(row.values())
        print(
            f"  {version}: evaluated_markets={total} "
            f"BUY={row['BUY']} SELL={row['SELL']} WAIT={row['WAIT']}"
        )
    print(f"Markets with completed-bar data: {len(latest_bar_by_market)}")
    if counts['candidates'] == 0:
        print("WARNING: no markets produced completed-bar research candidates")
    if counts['errors']:
        sys.exit(1)


if __name__ == '__main__':
    main()

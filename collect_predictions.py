"""Collect forward predictions using the app's EMA/engulfing rule.

Run with --dry-run first. Requires prediction_store.py in repository root.
"""
import argparse
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import yfinance as yf
from prediction_store import config, list_predictions, save_prediction
from signal_models import BASELINE_VERSION, MOMENTUM_VERSION, momentum_signals

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
    if timeframe != '1d':
        raise ValueError('Collector currently supports completed daily bars only')
    if df.empty:
        return None

    # Yahoo may include the still-forming daily bar or end with the most
    # recent completed one. Choose by timestamp rather than always -2.
    now = pd.Timestamp.now(tz='UTC')
    index_utc = pd.to_datetime(df.index, utc=True)
    completed = (index_utc + pd.Timedelta(days=1) <= now)
    df = df.loc[completed].copy()
    if len(df) < 60:
        return None
    df['EMA20'] = df.Close.ewm(span=20, adjust=False).mean()
    df['EMA50'] = df.Close.ewm(span=50, adjust=False).mean()
    previous = df.shift(1)
    bull = ((previous.Close < previous.Open) & (df.Close > df.Open)
            & (df.Open <= previous.Close) & (df.Close >= previous.Open))
    bear = ((previous.Close > previous.Open) & (df.Close < df.Open)
            & (df.Open >= previous.Close) & (df.Close <= previous.Open))
    # Latest actually completed bar; never the forming daily candle.
    anchor = df.iloc[-1]
    if model_version == MOMENTUM_VERSION:
        buys, sells = momentum_signals(df)
        buy, sell = bool(buys.iloc[-1]), bool(sells.iloc[-1])
    else:
        buy = anchor.EMA20 > anchor.EMA50 and bool(bull.iloc[-1])
        sell = anchor.EMA20 < anchor.EMA50 and bool(bear.iloc[-1])
    signal = 'BUY' if buy else ('SELL' if sell else 'WAIT')
    at = pd.Timestamp(df.index[-1])
    at = at.tz_localize('UTC') if at.tzinfo is None else at.tz_convert('UTC')
    return {
        'instrument': name, 'ticker': ticker, 'timeframe': timeframe,
        'signal': signal, 'model_version': model_version,
        'signal_bar_at': at.isoformat(),
        'reference_close': float(anchor.Close),
        'horizon_bars': HORIZON_BARS,
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
    existing = set()
    if not args.dry_run:
        for rec in list_predictions():
            existing.add((rec.get('ticker'), rec.get('timeframe'),
                          str(pd.Timestamp(rec['signal_bar_at']).tz_convert('UTC')),
                          rec.get('model_version'), int(rec.get('horizon_bars', 0))))
    counts = {'saved':0, 'duplicate':0, 'wait_skipped':0, 'errors':0, 'candidates':0}
    for timeframe, (interval, period) in TIMEFRAMES.items():
        for name, ticker in MARKETS.items():
            try:
                candles = download(ticker, interval, period)
            except Exception as exc:
                counts['errors'] += 1
                print(f'ERROR downloading {name} {timeframe}: {type(exc).__name__}: {exc}')
                continue

            for model_version in (BASELINE_VERSION, MOMENTUM_VERSION):
                try:
                    payload = prediction(name, ticker, timeframe, candles, model_version)
                    if payload is None:
                        print(f'{name} {timeframe}: insufficient candles')
                        continue
                    counts['candidates'] += 1
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
                        save_prediction(payload)
                        existing.add(key)
                        counts['saved'] += 1
                except Exception as exc:
                    counts['errors'] += 1
                    print(f'ERROR {name} {timeframe} {model_version}: {type(exc).__name__}: {exc}')
    print('Collection summary:', counts)
    if counts['errors']:
        sys.exit(1)


if __name__ == '__main__':
    main()

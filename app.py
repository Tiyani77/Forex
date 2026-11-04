import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title='Forex Intelligence | Trading Terminal', page_icon='📈', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
.stApp {background:#0a1020;color:#e9effb}
[data-testid="stSidebar"] {background:#101a2d;border-right:1px solid #25334b}
[data-testid="stMetric"] {background:#141f34;border:1px solid #273750;border-radius:14px;padding:15px}
[data-testid="stMetricLabel"] {color:#9aacc8}
h1,h2,h3 {letter-spacing:-.025em}
.block-container {padding-top:1.8rem;max-width:1550px}
div[data-testid="stAlert"] {border-radius:12px}
</style>''', unsafe_allow_html=True)

GROUPS = {
    'Major Forex': {'EUR/USD':'EURUSD=X','GBP/USD':'GBPUSD=X','USD/JPY':'JPY=X','USD/CHF':'CHF=X','AUD/USD':'AUDUSD=X','USD/CAD':'CAD=X','NZD/USD':'NZDUSD=X'},
    'Minor Forex': {'EUR/GBP':'EURGBP=X','EUR/JPY':'EURJPY=X','GBP/JPY':'GBPJPY=X','EUR/AUD':'EURAUD=X','AUD/JPY':'AUDJPY=X','GBP/AUD':'GBPAUD=X','EUR/CHF':'EURCHF=X','NZD/JPY':'NZDJPY=X'},
    'Exotic Forex': {'USD/ZAR':'ZAR=X','USD/MXN':'MXN=X','USD/TRY':'TRY=X','USD/SGD':'SGD=X'},
    'Metals (futures proxies)': {'Gold Futures':'GC=F','Silver Futures':'SI=F'},
    'Indices': {'S&P 500':'^GSPC','NASDAQ 100':'^NDX','Dow Jones':'^DJI','DAX':'^GDAXI'},
    'Crypto': {'BTC/USD':'BTC-USD','ETH/USD':'ETH-USD','SOL/USD':'SOL-USD'},
}
ALL = {name:(ticker,group) for group,items in GROUPS.items() for name,ticker in items.items()}
TIMEFRAMES = {'5m':('5m','5d'),'15m':('15m','1mo'),'1h':('60m','3mo'),'4h':('60m','3mo'),'1d':('1d','2y')}

@st.cache_data(ttl=900,show_spinner=False)
def fetch(ticker, interval, period):
    data=yf.download(ticker,period=period,interval=interval,auto_adjust=False,progress=False,threads=False)
    if data is None or data.empty: return pd.DataFrame()
    if isinstance(data.columns,pd.MultiIndex): data.columns=data.columns.get_level_values(0)
    required=['Open','High','Low','Close']
    if any(x not in data for x in required): return pd.DataFrame()
    data=data.dropna(subset=required).sort_index()
    data=data[~data.index.duplicated(keep='last')]
    if interval=='60m' and period=='3mo':
        pass
    return data

def resample_4h(data):
    if data.empty: return data
    df=data.copy()
    # Yahoo hourly candles can have exchange-local or timezone-aware indices.
    cols={'Open':'first','High':'max','Low':'min','Close':'last'}
    if 'Volume' in df: cols['Volume']='sum'
    df=df.resample('4h',origin='start_day').agg(cols).dropna(subset=['Open','High','Low','Close'])
    return df

def indicators(data):
    df=data.copy()
    df['EMA20']=df.Close.ewm(span=20,adjust=False).mean()
    df['EMA50']=df.Close.ewm(span=50,adjust=False).mean()
    prev=df.shift(1)
    # Two-candle body engulfing (a deliberately narrow, reproducible definition).
    bull=(prev.Close<prev.Open)&(df.Close>df.Open)&(df.Open<=prev.Close)&(df.Close>=prev.Open)
    bear=(prev.Close>prev.Open)&(df.Close<df.Open)&(df.Open>=prev.Close)&(df.Close<=prev.Open)
    df['BullEngulf']=bull.fillna(False)
    df['BearEngulf']=bear.fillna(False)
    df['Buy']=(df.EMA20>df.EMA50)&df.BullEngulf
    df['Sell']=(df.EMA20<df.EMA50)&df.BearEngulf
    # Three-candle FVG: gap between bar i-2 and bar i, known at close of i.
    df['BullFVG']=(df.Low>df.High.shift(2)).fillna(False)
    df['BearFVG']=(df.High<df.Low.shift(2)).fillna(False)
    df['PriorHigh20']=df.High.shift(1).rolling(20).max()
    df['PriorLow20']=df.Low.shift(1).rolling(20).min()
    df['BreakUp']=(df.Close>df.PriorHigh20).fillna(False)
    df['BreakDown']=(df.Close<df.PriorLow20).fillna(False)
    return df

def backtest(df,horizon=5):
    """One signal per completed bar, entry next open, exit after horizon bars.
    Overlapping signals are skipped so trade count reflects sequential positions.
    Returns are gross price changes, NOT executable P&L.
    """
    out=[]; next_allowed=50
    for i in range(50,len(df)-horizon):
        if i<next_allowed: continue
        side=1 if bool(df.Buy.iloc[i]) else (-1 if bool(df.Sell.iloc[i]) else 0)
        if not side: continue
        entry=float(df.Open.iloc[i+1]); exit_=float(df.Close.iloc[i+horizon])
        if not np.isfinite(entry) or entry<=0 or not np.isfinite(exit_): continue
        ret=100*side*(exit_-entry)/entry
        out.append({'Signal time':str(df.index[i]),'Direction':'BUY' if side==1 else 'SELL',
                    'Entry':entry,'Exit':exit_,'Gross return %':ret,'Win':ret>0})
        next_allowed=i+horizon+1
    return pd.DataFrame(out)

def stats(trades):
    if trades.empty:return None
    rets=trades['Gross return %'].astype(float)
    wins=rets[rets>0].sum(); losses=-rets[rets<0].sum()
    profit_factor=wins/losses if losses>0 else np.nan
    # Approximate compounded gross return equity, no leverage or trading costs.
    equity=(1+rets/100).cumprod()
    dd=(equity/equity.cummax()-1)*100
    return {'Trades':len(trades),'Win rate %':round(float((rets>0).mean()*100),1),
            'Avg gross return %':round(float(rets.mean()),3),
            'Profit factor':round(float(profit_factor),2) if np.isfinite(profit_factor) else None,
            'Max drawdown %':round(float(dd.min()),2)}

def fmt_price(v,name):
    if not np.isfinite(v):return '—'
    if name in GROUPS['Indices'] or name in GROUPS['Metals (futures proxies)'] or name in GROUPS['Crypto']:
        return f'{v:,.2f}'
    if 'JPY' in name:return f'{v:,.3f}'
    return f'{v:,.5f}'

st.sidebar.markdown('## 📈 Forex Intelligence')
st.sidebar.caption('Research terminal · V2')
page=st.sidebar.radio('Navigation',['Dashboard','Market Analysis','Backtesting','Accuracy Leaderboard'])
category=st.sidebar.selectbox('Market category',list(GROUPS))
market=st.sidebar.selectbox('Search instrument',list(GROUPS[category]))
custom=st.sidebar.text_input('Custom Yahoo Finance symbol (optional)',placeholder='e.g. EURUSD=X')
tf=st.sidebar.selectbox('Timeframe',list(TIMEFRAMES),index=4)
horizon=st.sidebar.slider('Backtest holding period (bars)',2,20,5)
st.sidebar.caption('Intraday data availability is limited by Yahoo Finance. Gold and silver are futures proxies, not spot XAU/USD or XAG/USD.')

symbol=custom.strip().upper() if custom.strip() else ALL[market][0]
interval,period=TIMEFRAMES[tf]
with st.spinner('Loading historical candles…'):
    raw=fetch(symbol,interval,period)
    if tf=='4h' and not raw.empty:raw=resample_4h(raw)
if len(raw)<60:
    st.error('Not enough candles were returned for this market/timeframe. Try Daily, another symbol, or wait and retry.')
    st.stop()
df=indicators(raw)
trades=backtest(df,horizon)
result=stats(trades)
last=df.iloc[-1]
label=custom.strip().upper() if custom.strip() else market
signal='BUY' if bool(last.Buy) else ('SELL' if bool(last.Sell) else 'WAIT')
trend='Bullish' if last.EMA20>last.EMA50 else 'Bearish'

st.title('Forex Intelligence')
st.caption('Technical analysis · Research signals · Historical evaluation | Not financial advice')
if page in ['Dashboard','Market Analysis']:
    a,b,c,d=st.columns(4)
    a.metric('Instrument',label)
    b.metric('Latest candle close',fmt_price(float(last.Close),market))
    c.metric('EMA trend',trend)
    d.metric('Strategy signal',signal)
    st.caption(f'Timeframe: {tf}  ·  Last candle: {df.index[-1]}  ·  Source: Yahoo Finance (delayed/historical)')
    fig=go.Figure()
    view=df.tail(140)
    fig.add_trace(go.Candlestick(x=view.index,open=view.Open,high=view.High,low=view.Low,close=view.Close,name='Candles',increasing_line_color='#22c7a3',decreasing_line_color='#f16b75'))
    fig.add_trace(go.Scatter(x=view.index,y=view.EMA20,name='EMA 20',line=dict(color='#f9b44b',width=1.6)))
    fig.add_trace(go.Scatter(x=view.index,y=view.EMA50,name='EMA 50',line=dict(color='#6ba7ff',width=1.6)))
    buy=view[view.Buy]; sell=view[view.Sell]
    fig.add_trace(go.Scatter(x=buy.index,y=buy.Low,name='BUY setup',mode='markers',marker=dict(symbol='triangle-up',size=12,color='#22c7a3')))
    fig.add_trace(go.Scatter(x=sell.index,y=sell.High,name='SELL setup',mode='markers',marker=dict(symbol='triangle-down',size=12,color='#f16b75')))
    fig.update_layout(template='plotly_dark',paper_bgcolor='#0a1020',plot_bgcolor='#101a2d',height=570,
                      margin=dict(l=15,r=15,t=25,b=10),xaxis_rangeslider_visible=False,
                      legend=dict(orientation='h',y=1.08,x=0),font=dict(color='#d7e4fa'))
    st.plotly_chart(fig,use_container_width=True)
    x,y,z=st.columns(3)
    x.metric('Bullish FVG on last bar','Yes' if bool(last.BullFVG) else 'No')
    y.metric('Bearish FVG on last bar','Yes' if bool(last.BearFVG) else 'No')
    z.metric('20-bar structure break','Up' if bool(last.BreakUp) else ('Down' if bool(last.BreakDown) else 'None'))
    st.info('BUY/SELL requires a body-engulfing candle aligned with EMA20/EMA50. FVG and structure detections are shown as context, not yet combined into a validated trading system.')
    if page=='Market Analysis':
        st.subheader('Recent detected events')
        recent=df.tail(60)[['BullEngulf','BearEngulf','BullFVG','BearFVG','BreakUp','BreakDown']]
        events=recent[recent.any(axis=1)].tail(20)
        st.dataframe(events.iloc[::-1],use_container_width=True)

elif page=='Backtesting':
    st.subheader(f'Backtesting · {label} · {tf}')
    st.caption(f'Signals at candle close, entry at next candle open, exit at close {horizon} bars after signal. Non-overlapping positions. No spreads, slippage, commissions, swaps or leverage.')
    if result is None:st.warning('No completed historical trades for this market/timeframe.')
    else:
        a,b,c,d=st.columns(4)
        a.metric('Completed trades',result['Trades'])
        b.metric('Gross win rate',f"{result['Win rate %']:.1f}%")
        c.metric('Avg gross return',f"{result['Avg gross return %']:+.3f}%")
        d.metric('Max gross drawdown',f"{result['Max drawdown %']:.2f}%")
        equity=(1+trades['Gross return %']/100).cumprod()
        st.line_chart(pd.DataFrame({'Gross equity (starting at 1)':equity.values}),use_container_width=True)
        st.dataframe(trades.iloc[::-1],use_container_width=True,hide_index=True)
        st.download_button('Download trade history CSV',trades.to_csv(index=False),'forex_backtest.csv','text/csv')

else:
    st.subheader('Market Accuracy Leaderboard')
    st.caption('Historical signal win rates, not live prediction accuracy. Comparing instruments on the same selected timeframe and holding period.')
    min_trades=st.slider('Minimum completed trades to rank',1,30,10)
    st.info('For fairer comparisons, use Daily candles. Intraday history can be very short, and a high win rate on a small sample is unreliable.')
    if st.button('Run comparison across all supported markets',type='primary'):
        rows=[]; failures=[]
        progress=st.progress(0)
        items=list(ALL.items())
        for j,(name,(ticker,group)) in enumerate(items):
            try:
                history=fetch(ticker,interval,period)
                if tf=='4h' and not history.empty:history=resample_4h(history)
                if len(history)<60:failures.append(name)
                else:
                    t=backtest(indicators(history),horizon)
                    s=stats(t)
                    if s:rows.append({'Market':name,'Category':group,**s})
                    else:failures.append(name)
            except Exception:failures.append(name)
            progress.progress((j+1)/len(items))
        st.session_state['leaderboard']=pd.DataFrame(rows)
        st.session_state['leaderboard_key']=(tf,horizon)
        st.session_state['leaderboard_failures']=failures
    board=st.session_state.get('leaderboard',pd.DataFrame())
    if not board.empty:
        if st.session_state.get('leaderboard_key')!=(tf,horizon):
            st.warning('Settings changed. Run the comparison again for the selected timeframe and holding period.')
        else:
            ranked=board[board.Trades>=min_trades].sort_values(['Win rate %','Trades'],ascending=[False,False])
            st.metric('Markets with enough observations',len(ranked))
            if ranked.empty:st.warning('No market met the minimum trade count. Try a lower threshold or Daily candles.')
            else:
                st.dataframe(ranked,use_container_width=True,hide_index=True)
                chart=px.bar(ranked.head(15),x='Market',y='Win rate %',color='Category',template='plotly_dark')
                chart.update_layout(paper_bgcolor='#0a1020',plot_bgcolor='#101a2d',height=400)
                st.plotly_chart(chart,use_container_width=True)
                st.download_button('Download leaderboard CSV',ranked.to_csv(index=False),'market_accuracy.csv','text/csv')
            failures=st.session_state.get('leaderboard_failures',[])
            if failures:st.caption('Insufficient data or failed downloads: '+', '.join(failures))
    else:st.caption('Press the button to download and compare available markets. This can take a little while.')

st.divider()
st.caption('Prototype research tool. Data may be delayed, incomplete or revised. No model accuracy or profitability is guaranteed. Backtests are in-sample, gross of costs and should not be used as live trading evidence.')

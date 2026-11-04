import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title='Forex Intelligence | Trading Terminal', page_icon='📈', layout='wide', initial_sidebar_state='expanded')

st.markdown("""<style>
.stApp {background:#080d18;color:#edf3ff}
[data-testid="stSidebar"] {background:#101827;border-right:1px solid #25324b}
[data-testid="stSidebar"] * {color:#e4ecfc!important}
[data-testid="stSidebar"] input {color:#111827!important}
[data-testid="stSidebar"] [data-baseweb="select"] * {color:#111827!important}
[data-testid="stMetric"] {background:#141e30;border:1px solid #273653;border-radius:14px;padding:13px}
[data-testid="stMetricLabel"] {color:#9eafc9!important}
[data-testid="stMetricValue"] {color:#eef5ff!important}
.block-container {padding-top:1.3rem;max-width:1750px}
h1,h2,h3 {letter-spacing:-.025em;color:#f2f6ff!important}
div[data-testid="stAlert"] {border-radius:12px}
.terminal-card {background:linear-gradient(145deg,#141d2d,#0e1522);border:1px solid #293852;border-radius:18px;padding:18px;margin-bottom:13px;box-shadow:0 10px 24px #0003}
.card-label {font-size:.78rem;color:#a8b8d3;letter-spacing:.045em;font-weight:650}
.card-title {font-size:1.25rem;color:#f0f5ff;font-weight:750;margin:7px 0}
.signal-buy {color:#62e4a2!important}
.signal-sell {color:#ff7e95!important}
.signal-wait {color:#eabf6b!important}
.signal-big {font-size:3.8rem;line-height:1.25;font-weight:850;text-align:center;padding:15px 0}
.signal-caption {text-align:center;color:#a4b5d0;font-size:.85rem}
.signal-panel {background:radial-gradient(circle at center,#1b3040,#111a29 70%);border:1px solid #34445d;border-radius:18px;padding:24px 14px;margin:12px 0}
.pill {display:inline-block;padding:6px 11px;border:1px solid #364660;border-radius:20px;background:#1b2740;color:#d7e8ff;font-size:.78rem;margin:3px}
.rule {font-size:.87rem;color:#c6d3e8;line-height:1.65}
.small-note {color:#94a6c2;font-size:.78rem}
</style>""",unsafe_allow_html=True)

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

st.sidebar.markdown('## ✦ Forex Intelligence')
st.sidebar.caption('Market intelligence · V3 terminal')
page=st.sidebar.radio('Navigation',['Trading Terminal','Market Analysis','Backtesting','Accuracy Leaderboard'])
category=st.sidebar.selectbox('Market category',list(GROUPS))
market=st.sidebar.selectbox('Search instrument',list(GROUPS[category]))
custom=st.sidebar.text_input('Custom Yahoo Finance ticker (optional)',placeholder='EURUSD=X')
tf=st.sidebar.selectbox('Timeframe',list(TIMEFRAMES),index=4)
horizon=st.sidebar.slider('Backtest holding period (bars)',2,20,5)
st.sidebar.caption('Market data is delayed/historical. Intraday history varies. Gold/silver use futures proxies, not spot prices.')

symbol=custom.strip().upper() if custom.strip() else ALL[market][0]
interval,period=TIMEFRAMES[tf]
try:
    with st.spinner('Loading market candles…'):
        raw=fetch(symbol,interval,period)
        if tf=='4h' and not raw.empty: raw=resample_4h(raw)
except Exception as exc:
    st.error(f'Data provider error: {exc}')
    st.stop()
if len(raw)<60:
    st.error('Insufficient market data for this instrument/timeframe. Try Daily or another symbol.')
    st.stop()
df=indicators(raw)
trades=backtest(df,horizon)
result=stats(trades)
last=df.iloc[-1]
label=custom.strip().upper() if custom.strip() else market
signal='BUY' if bool(last.Buy) else ('SELL' if bool(last.Sell) else 'WAIT')
trend='Bullish' if last.EMA20>last.EMA50 else 'Bearish'
color_class={'BUY':'signal-buy','SELL':'signal-sell','WAIT':'signal-wait'}[signal]

# RSI, MACD and ATR use only historical candles; they are context, not validated confidence.
delta=df.Close.diff()
gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
rsi=100-100/(1+gain/loss.replace(0,np.nan))
macd=df.Close.ewm(span=12,adjust=False).mean()-df.Close.ewm(span=26,adjust=False).mean()
macd_sig=macd.ewm(span=9,adjust=False).mean()
tr=pd.concat([(df.High-df.Low),(df.High-df.Close.shift()).abs(),(df.Low-df.Close.shift()).abs()],axis=1).max(axis=1)
atr=tr.ewm(alpha=1/14,adjust=False).mean()
atr_pct=100*float(atr.iloc[-1])/float(last.Close)

st.markdown('## ✦ Forex Intelligence')
st.caption('Trading terminal · Market research · Historical testing | Not financial advice')

if page in ['Trading Terminal','Market Analysis']:
    left,center,right=st.columns([1.05,1.8,1.1],gap='medium')
    with left:
        st.markdown('<div class="terminal-card"><div class="card-label">MARKET OVERVIEW</div><div class="card-title">'+label+'</div><div class="rule">Category: '+category+'<br>Timeframe: '+tf+'<br>Source: Yahoo Finance</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="terminal-card"><div class="card-label">MARKET TREND</div><div class="card-title">'+trend+'</div><div class="rule">EMA 20: '+fmt_price(float(last.EMA20),market)+'<br>EMA 50: '+fmt_price(float(last.EMA50),market)+'</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="terminal-card"><div class="card-label">MARKET STRUCTURE</div><div class="rule">20-bar break: <b>'+('Up' if bool(last.BreakUp) else ('Down' if bool(last.BreakDown) else 'None'))+'</b><br>Bullish FVG: <b>'+('Detected' if bool(last.BullFVG) else 'Not detected')+'</b><br>Bearish FVG: <b>'+('Detected' if bool(last.BearFVG) else 'Not detected')+'</b></div></div>',unsafe_allow_html=True)
        if result:
            st.metric('Historical gross win rate',f"{result['Win rate %']:.1f}%",help=f"{result['Trades']} completed in-sample signals; no trading costs")
            st.caption(f"Based on {result['Trades']} non-overlapping completed historical trades. Not signal confidence.")
        else:
            st.info('No completed backtest trades for these settings.')
    with center:
        st.markdown('<div class="terminal-card"><div class="card-label" style="text-align:center">SELECTED INSTRUMENT</div><div class="card-title" style="text-align:center;font-size:1.7rem">'+label+'</div><div class="signal-panel"><div class="signal-big '+color_class+'">'+signal+'</div><div class="signal-caption">'+('EMA trend + engulfing confirmation' if signal!='WAIT' else 'No confirmed EMA + engulfing setup on the latest bar')+'</div></div><div class="signal-caption">Last candle: '+str(df.index[-1])+'</div></div>',unsafe_allow_html=True)
        st.metric('Last candle close',fmt_price(float(last.Close),market))
        st.caption('Historical candle close, not a live executable quote.')
    with right:
        st.markdown('<div class="terminal-card"><div class="card-label">AI TRADE SIGNAL · RULE-BASED V3</div><div class="card-title '+color_class+'">'+signal+'</div><div class="rule">'+('Bullish EMA alignment and bullish body engulfing.' if signal=='BUY' else ('Bearish EMA alignment and bearish body engulfing.' if signal=='SELL' else 'Waiting for both trend alignment and a qualifying engulfing candle.'))+'</div></div>',unsafe_allow_html=True)
        x,y=st.columns(2)
        with x:
            st.metric('RSI (14)',f'{float(rsi.iloc[-1]):.1f}' if np.isfinite(rsi.iloc[-1]) else '—')
            st.metric('EMA trend',trend)
        with y:
            st.metric('ATR / Price',f'{atr_pct:.2f}%')
            st.metric('MACD', 'Above signal' if macd.iloc[-1]>macd_sig.iloc[-1] else 'Below signal')
        st.markdown('<div class="terminal-card"><div class="card-label">SIGNAL QUALITY</div><div class="rule">No calibrated confidence percentage yet. We will calculate it only after out-of-sample validation across markets and timeframes.</div></div>',unsafe_allow_html=True)
    st.markdown('### Price action & detected setups')
    fig=go.Figure()
    view=df.tail(130)
    fig.add_trace(go.Candlestick(x=view.index,open=view.Open,high=view.High,low=view.Low,close=view.Close,name='Candles',increasing_line_color='#36d6b0',decreasing_line_color='#fa718b'))
    fig.add_trace(go.Scatter(x=view.index,y=view.EMA20,name='EMA 20',line=dict(color='#eeb85c',width=1.6)))
    fig.add_trace(go.Scatter(x=view.index,y=view.EMA50,name='EMA 50',line=dict(color='#79a8ff',width=1.6)))
    buys=view[view.Buy];sells=view[view.Sell]
    fig.add_trace(go.Scatter(x=buys.index,y=buys.Low,mode='markers',name='BUY setup',marker=dict(symbol='triangle-up',size=11,color='#36d6b0')))
    fig.add_trace(go.Scatter(x=sells.index,y=sells.High,mode='markers',name='SELL setup',marker=dict(symbol='triangle-down',size=11,color='#fa718b')))
    fig.update_layout(template='plotly_dark',paper_bgcolor='#080d18',plot_bgcolor='#111b2c',height=520,margin=dict(l=8,r=8,t=35,b=10),xaxis_rangeslider_visible=False,legend=dict(orientation='h',y=1.09),font=dict(color='#d7e5fa'))
    st.plotly_chart(fig,use_container_width=True)
    if page=='Market Analysis':
        st.subheader('Recent price-action detections')
        recent=df.tail(100)[['BullEngulf','BearEngulf','BullFVG','BearFVG','BreakUp','BreakDown']]
        events=recent[recent.any(axis=1)].tail(25)
        st.dataframe(events.iloc[::-1],use_container_width=True)
    st.info('Signals are rule-based research observations. FVG and structure are context only; QM/MPL, liquidity sweeps and supply/demand confluence are planned for later versions.')

elif page=='Backtesting':
    st.subheader(f'Historical Backtesting · {label} · {tf}')
    st.caption(f'Signal on completed candle; entry next candle open; exit at close {horizon} bars after signal. Non-overlapping trades; gross price returns, without spreads, commissions, slippage, financing or leverage.')
    if result is None: st.warning('No completed historical trades for this instrument and timeframe.')
    else:
        a,b,c,d=st.columns(4)
        a.metric('Completed trades',result['Trades'])
        b.metric('Gross win rate',f"{result['Win rate %']:.1f}%")
        c.metric('Avg gross return',f"{result['Avg gross return %']:+.3f}%")
        d.metric('Max gross drawdown',f"{result['Max drawdown %']:.2f}%")
        equity=(1+trades['Gross return %']/100).cumprod()
        st.line_chart(pd.DataFrame({'Gross equity (starts at 1)':equity.values}),use_container_width=True)
        st.dataframe(trades.iloc[::-1],use_container_width=True,hide_index=True)
        st.download_button('Download trades CSV',trades.to_csv(index=False),'backtest_trades.csv','text/csv')
else:
    st.subheader('Accuracy Leaderboard · Historical market comparison')
    st.caption('Compares completed historical gross-return signals on the same timeframe and holding period. Not live prediction accuracy.')
    min_trades=st.slider('Minimum completed trades to rank',1,30,10)
    if st.button('Analyze all supported markets',type='primary'):
        rows=[];failures=[];items=list(ALL.items());progress=st.progress(0)
        for j,(name,(ticker,group)) in enumerate(items):
            try:
                history=fetch(ticker,interval,period)
                if tf=='4h' and not history.empty:history=resample_4h(history)
                if len(history)<60:failures.append(name)
                else:
                    result_market=stats(backtest(indicators(history),horizon))
                    if result_market:rows.append({'Market':name,'Category':group,**result_market})
                    else:failures.append(name)
            except Exception:failures.append(name)
            progress.progress((j+1)/len(items))
        st.session_state['board']=pd.DataFrame(rows)
        st.session_state['board_key']=(tf,horizon)
        st.session_state['failures']=failures
    board=st.session_state.get('board',pd.DataFrame())
    if not board.empty:
        if st.session_state.get('board_key')!=(tf,horizon):
            st.warning('Timeframe or holding period changed; rerun the comparison.')
        else:
            ranked=board[board.Trades>=min_trades].sort_values(['Win rate %','Trades'],ascending=[False,False])
            st.metric('Markets meeting sample threshold',len(ranked))
            if ranked.empty:st.warning('No markets meet this trade-count threshold. Try Daily candles or lower the threshold.')
            else:
                st.dataframe(ranked,use_container_width=True,hide_index=True)
                chart=px.bar(ranked.head(15),x='Market',y='Win rate %',color='Category',template='plotly_dark')
                chart.update_layout(paper_bgcolor='#080d18',plot_bgcolor='#111b2c',height=400)
                st.plotly_chart(chart,use_container_width=True)
                st.download_button('Download leaderboard CSV',ranked.to_csv(index=False),'accuracy_leaderboard.csv','text/csv')
            if st.session_state.get('failures'):st.caption('Unavailable/insufficient data: '+', '.join(st.session_state['failures']))
    else:st.caption('Click Analyze all supported markets to begin the comparison.')

st.divider()
st.caption('Forex Intelligence V3 · Experimental research tool · Data may be delayed, incomplete or revised · In-sample gross backtests are not evidence of future profitability.')

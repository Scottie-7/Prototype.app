# =============================
# Imports
# =============================
import os
import time
import queue
import threading
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# Optional fallback for minute/daily data
try:
    import yfinance as yf  # type: ignore
except Exception:
    yf = None

# Optional: Plotly (used for charts)
try:
    import plotly.graph_objects as go  # noqa: F401
except Exception:
    go = None

# =============================
# Project Modules (your code)
# =============================
from src.data_sources import StockDataManager
from src.order_book import OrderBookAnalyzer
from src.anomaly_detection import AnomalyDetector
from src.news_scraper import NewsMonitor
from src.database import DatabaseManager
from src.alerts import AlertManager
from src.visualization import ChartGenerator
from src.notifications import NotificationManager

# =============================
# Page Config (must be before any Streamlit output)
# =============================
st.set_page_config(
    page_title="LLM Stock Monitoring Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================
# Session State (idempotent)
# =============================
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.watchlist = ["SPY", "QQQ", "TSLA", "NVDA", "META", "OSTX"]
    st.session_state.alerts = []
    st.session_state.monitoring = False
    st.session_state.cached_stock_data = {}
    st.session_state.last_update_time = {}
    st.session_state.data_queue = queue.Queue()
    st.session_state.notification_settings = {
        "email_enabled": False,
        "email_address": "",
        "from_email": "alerts@ziacapital.com",
        "sms_enabled": False,
        "phone_number": "",
    }

# =============================
# Components
# =============================
@st.cache_resource
def init_components():
    db = DatabaseManager()
    data_manager = StockDataManager()
    order_book = OrderBookAnalyzer()
    anomaly_detector = AnomalyDetector()
    news_monitor = NewsMonitor()
    alert_manager = AlertManager()
    chart_generator = ChartGenerator()
    notification_manager = NotificationManager()
    return (
        db,
        data_manager,
        order_book,
        anomaly_detector,
        news_monitor,
        alert_manager,
        chart_generator,
        notification_manager,
    )

(
    db,
    data_manager,
    order_book,
    anomaly_detector,
    news_monitor,
    alert_manager,
    chart_generator,
    notification_manager,
) = init_components()

# =============================
# Header
# =============================
st.markdown(
    """
    <div style="text-align:center;">
        <h1 style="margin-bottom:4px;">Ai Stock Trading Dashboard</h1>
        <p style="margin-top:0;opacity:0.8;">
            Real-time monitoring • Order Book Analysis • Alerts • News • Statistical Analysis Tools
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================
# Sidebar Controls
# =============================
st.sidebar.title("⚙️ Controls")

# Monitoring toggle button
st.sidebar.subheader("Monitoring")
if st.sidebar.button("Start Monitoring" if not st.session_state.monitoring else "Stop Monitoring"):
    st.session_state.monitoring = not st.session_state.monitoring
    st.sidebar.success("Monitoring Started" if st.session_state.monitoring else "Monitoring Stopped")

# Thresholds
st.sidebar.subheader("Alert Thresholds")
price_change_threshold = st.sidebar.slider("Price Change Alert (%)", 1, 100, 25)
volume_multiplier = st.sidebar.slider("Volume Spike ×", 1, 20, 5)
max_watch = st.sidebar.slider("Max Stocks to Monitor", 1, 50, 10)

# store thresholds for use elsewhere
st.session_state.price_change_threshold = price_change_threshold
st.session_state.volume_multiplier = volume_multiplier
st.session_state.max_watch = max_watch

# Watchlist editor
st.sidebar.subheader("Watchlist")
new_sym = st.sidebar.text_input("Add Symbol").upper().strip()
if st.sidebar.button("Add"):
    if new_sym and new_sym not in st.session_state.watchlist:
        st.session_state.watchlist.append(new_sym)
        st.sidebar.success(f"Added {new_sym}")

# Show & remove entries
for i, sym in enumerate(list(st.session_state.watchlist)):
    c1, c2 = st.sidebar.columns([4, 1])
    c1.write(sym)
    if c2.button("✖", key=f"rm_{i}"):
        st.session_state.watchlist.remove(sym)
        st.rerun()

# =============================
# Tabs (must be above any `with tabX:` usage)
# =============================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📊 Live Monitor", "📈 Order Books", "⚠️ Alerts", "📰 News", "📉 Analysis", "test"]
)

# =============================
# Chart Helpers (top-level to avoid indentation/cache issues)
# =============================
@st.cache_data(ttl=60)
def _fetch_hist_yf(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Fetch OHLCV using yfinance with smart fallbacks."""
    if yf is None:
        return pd.DataFrame()

    s = (symbol or "").strip().upper()
    if not s:
        return pd.DataFrame()

    # Primary + safe fallbacks
    attempts = [
        (period, interval),
        (period, "1d"),  # if intraday fails, try daily for same period
        ("1y", "1d"),    # broad fallback
        ("5d", "5m"),    # intraday fallback
    ]

    for p, i in attempts:
        try:
            df = yf.download(
                s, period=p, interval=i,
                progress=False, auto_adjust=False, group_by="column"
            )
            if isinstance(df, pd.DataFrame) and not df.empty and not df.dropna(how="all").empty:
                df.attrs["yf_period"] = p
                df.attrs["yf_interval"] = i
                return df
        except Exception:
            continue

    return pd.DataFrame()


def _make_fig(df: pd.DataFrame, symbol: str, chart_type: str):
    """Build a Plotly chart from a yfinance-style DF. Falls back to Close-only line."""
    try:
        import plotly.graph_objects as go  # local import to avoid hard dependency if missing
    except Exception:
        st.error("Plotly is required for charts. Try: pip install plotly")
        return None

    if df is None or df.empty:
        return None

    # Normalize MultiIndex columns to last level (Open/High/Low/Close/Adj Close/etc.)
    if getattr(df.columns, "nlevels", 1) > 1:
        try:
            df = df.copy()
            df.columns = [c[-1] if isinstance(c, (tuple, list)) else c for c in df.columns]
        except Exception:
            pass

    cmap = {str(c).strip().lower(): c for c in df.columns}
    open_col  = cmap.get("open")
    high_col  = cmap.get("high")
    low_col   = cmap.get("low")
    close_col = cmap.get("close") or cmap.get("adj close") or cmap.get("adj_close")

    have_ohlc = all([open_col, high_col, low_col, close_col])
    use_candle = (chart_type == "Candlestick" and have_ohlc)

    if use_candle:
        fig = go.Figure([
            go.Candlestick(
                x=df.index,
                open=df[open_col], high=df[high_col],
                low=df[low_col], close=df[close_col],
                name=symbol
            )
        ])
    else:
        # Fallback to a line chart on Close or first numeric column
        yseries = df[close_col] if close_col is not None else None
        if yseries is None:
            for c in df.columns:
                try:
                    if pd.api.types.is_numeric_dtype(df[c]):
                        yseries = df[c]
                        break
                except Exception:
                    pass
        if yseries is None or yseries.dropna(how="all").empty:
            return None
        fig = go.Figure([go.Scatter(x=df.index, y=yseries, mode="lines", name=symbol)])

    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        height=360,
        xaxis_title=None, yaxis_title=None,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08)
    )

    yf_p = df.attrs.get("yf_period")
    yf_i = df.attrs.get("yf_interval")
    if yf_p and yf_i:
        fig.update_layout(title_text=f"{symbol}  •  {yf_p} / {yf_i}")

    return fig







# =============================
#     Tab 1: Live Market Monitor
# =============================










import contextlib
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

with tab1:
    st.subheader("Live Market Monitor")

    st.sidebar.subheader("Data Provider")
    provider = st.sidebar.selectbox(
        "Price source",
        ["Auto (Yahoo → Alpha Vantage)", "Yahoo only", "Alpha Vantage only"],
        index=0,
        help="Auto tries Yahoo first, then Alpha Vantage if Yahoo returns no data."
    )
    av_key = st.sidebar.text_input(
        "Alpha Vantage API key",
        value=st.session_state.get("alpha_vantage_key", ""),
        type="password",
        help="Get a free key at https://www.alphavantage.co. Needed for Alpha Vantage.",
    )
    st.session_state["alpha_vantage_key"] = av_key.strip()

    k0, k1, k2, k3 = st.columns([1.2, 1, 1, 1])
    with k0:
        st.session_state.monitoring = st.toggle(
            "Monitoring",
            value=st.session_state.get("monitoring", True),
            help="Toggle live data fetch on/off."
        )
    with k1:
        st.metric("Monitoring",
                  "ACTIVE" if st.session_state.monitoring else "IDLE",
                  "✅" if st.session_state.monitoring else "⏸️")
    with k2:
        st.metric("Tracked", len(st.session_state.get("watchlist", [])))
    with k3:
        st.metric("Active Alerts", len(st.session_state.get("alerts", [])))

    if st.session_state.monitoring:
        live_rows, errors = [], []
        watch = st.session_state.get("watchlist", [])

        for sym in watch:
            data = None

            try:
                if "data_manager" in globals() and hasattr(data_manager, "get_real_time_data"):
                    data = data_manager.get_real_time_data(sym)
            except Exception as e:
                errors.append(f"{sym}: get_real_time_data error: {e}")

            if not data:
                try:
                    import yfinance as yf
                    tk = yf.Ticker(sym)

                    snap = {}
                    try:
                        fast = getattr(tk, "fast_info", None) or {}
                        if fast:
                            snap = dict(fast)
                    except Exception:
                        pass
                    if not snap:
                        try:
                            snap = tk.info or {}
                        except Exception:
                            snap = {}

                    def _get(keys, default=None):
                        for k in keys:
                            v = snap.get(k)
                            if v is not None:
                                return v
                        return default

                    current_price = float(_get(["last_price", "lastPrice", "regularMarketPrice", "currentPrice"], 0.0) or 0.0)
                    previous_close = float(_get(["previousClose"], current_price) or current_price)
                    day_high = float(_get(["dayHigh", "day_high"], current_price) or current_price)
                    day_low  = float(_get(["dayLow", "day_low"], current_price) or current_price)
                    volume   = float(_get(["lastVolume", "volume"], 0.0) or 0.0)

                    if current_price > 0:
                        price_change   = current_price - previous_close
                        change_percent = (price_change / previous_close) * 100 if previous_close else 0.0
                        data = {
                            "symbol": sym,
                            "price": current_price,
                            "previous_close": previous_close,
                            "price_change": price_change,
                            "change_percent": change_percent,
                            "volume": volume,
                            "high": day_high,
                            "low": day_low,
                            "timestamp": datetime.now(),
                        }
                except Exception as e:
                    errors.append(f"{sym}: yfinance snapshot error: {e}")

            if data:
                try:
                    if "db" in globals() and hasattr(db, "store_stock_data"):
                        db.store_stock_data(data)
                except Exception:
                    pass

                st.session_state.setdefault("cached_stock_data", {})[sym] = data
                st.session_state.setdefault("last_update_time", {})[sym] = datetime.now()
                live_rows.append(data)

                try:
                    if "alert_manager" in globals() and hasattr(alert_manager, "check_alerts"):
                        pct = st.session_state.get("price_change_threshold", 25)
                        vm  = st.session_state.get("volume_multiplier", 5)
                        alert = alert_manager.check_alerts(data, pct, vm)
                        if alert:
                            st.session_state.setdefault("alerts", []).append(alert)
                except Exception:
                    pass

        if live_rows:
            df = pd.DataFrame(live_rows)
            cols = ["symbol","price","change_percent","volume","high","low"]
            df = df[[c for c in cols if c in df.columns]].copy()
            if "price" in df:           df["price"]          = df["price"].astype(float).map(lambda x: f"${x:.2f}")
            if "change_percent" in df:  df["change_percent"] = df["change_percent"].astype(float).map(lambda x: f"{x:+.2f}%")
            if "volume" in df:          df["volume"]         = df["volume"].astype(float).map(lambda x: f"{x:,.0f}")
            if "high" in df:            df["high"]           = df["high"].astype(float).map(lambda x: f"${x:.2f}")
            if "low" in df:             df["low"]            = df["low"].astype(float).map(lambda x: f"${x:.2f}")
            st.dataframe(df, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                fresh = sum(
                    1 for s in watch
                    if s in st.session_state.get("last_update_time", {})
                    and (datetime.now() - st.session_state["last_update_time"][s]).total_seconds() < 60
                )
                st.caption(f"🟢 {fresh}/{len(watch)} live feeds in last 60s")
            with c2:
                if st.button("🔄 Force Refresh Page"):
                    st.rerun()
        else:
            st.warning("No data received yet for the selected symbols.")
            if errors:
                with st.expander("Show fetch errors"):
                    for err in errors:
                        st.code(err)
    else:
        st.info("Monitoring is paused. Toggle it on to fetch live data.")

    def _flatten(df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df, pd.DataFrame) and not df.empty and getattr(df.columns, "nlevels", 1) > 1:
            df = df.copy()
            df.columns = [c[-1] if isinstance(c, (tuple, list)) else c for c in df.columns]
        return df

    def _yf_fetch(symbol: str, period: str, interval: str) -> pd.DataFrame:
        s = (symbol or "").strip().upper()
        if not s:
            return pd.DataFrame()
        try:
            import yfinance as yf
        except Exception:
            return pd.DataFrame()

        with contextlib.suppress(Exception):
            tk = yf.Ticker(s)
            df = tk.history(period=period, interval=interval, auto_adjust=False)
            if isinstance(df, pd.DataFrame) and not df.empty and not df.dropna(how="all").empty:
                return _flatten(df)
        with contextlib.suppress(Exception):
            df = yf.download(s, period=period, interval=interval,
                             progress=False, auto_adjust=False, group_by="column")
            if isinstance(df, pd.DataFrame) and not df.empty and not df.dropna(how="all").empty:
                return _flatten(df)
        return pd.DataFrame()

    def _av_intraday(symbol: str, minutes: int, api_key: str) -> pd.DataFrame:
        if not api_key:
            return pd.DataFrame()
        s = (symbol or "").strip().upper()
        interval = f"{minutes}min"
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": s,
            "interval": interval,
            "outputsize": "full",
            "apikey": api_key,
        }
        try:
            r = requests.get(url, params=params, timeout=20)
            j = r.json()
            key = f"Time Series ({interval})"
            if key not in j:
                return pd.DataFrame()
            df = pd.DataFrame.from_dict(j[key], orient="index")
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            df.rename(columns={
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close",
                "5. volume": "Volume",
            }, inplace=True)
            for col in ["Open","High","Low","Close","Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df
        except Exception:
            return pd.DataFrame()

    def _av_daily(symbol: str, api_key: str) -> pd.DataFrame:
        if not api_key:
            return pd.DataFrame()
        s = (symbol or "").strip().upper()
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": s,
            "outputsize": "full",
            "apikey": api_key,
        }
        try:
            r = requests.get(url, params=params, timeout=20)
            j = r.json()
            key = "Time Series (Daily)"
            if key not in j:
                return pd.DataFrame()
            df = pd.DataFrame.from_dict(j[key], orient="index")
            df.index = pd.to_datetime(df.index)
            df.sort_index(inplace=True)
            rename_map = {
                "1. open": "Open",
                "2. high": "High",
                "3. low": "Low",
                "4. close": "Close",
                "6. volume": "Volume",
            }
            df.rename(columns=rename_map, inplace=True)
            for col in ["Open","High","Low","Close","Volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            return df[["Open","High","Low","Close","Volume"]].dropna(how="all", axis=1)
        except Exception:
            return pd.DataFrame()

    def _clip_latest_session(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return df
        idx = pd.to_datetime(df.index)
        last = idx[-1].date()
        return df[idx.date == last]

    def _load_timeframe(symbol: str, timeframe: str) -> tuple[pd.DataFrame, str]:
        tf = timeframe.upper()
        s = (symbol or "").strip().upper()
        api = st.session_state.get("alpha_vantage_key", "")

        order = []
        if provider.startswith("Auto"):
            order = ["yahoo", "av"] if api else ["yahoo"]
        elif provider.startswith("Yahoo"):
            order = ["yahoo"]
        else:
            order = ["av"]

        df = pd.DataFrame()
        used = ""

        for prov in order:
            if tf == "1D":
                if prov == "yahoo":
                    df = _yf_fetch(s, "5d", "1m")
                    if not df.empty:
                        df = _clip_latest_session(df)
                elif prov == "av":
                    df = _av_intraday(s, 1, api)
                    if not df.empty:
                        df = _clip_latest_session(df)
            elif tf == "5D":
                if prov == "yahoo":
                    df = _yf_fetch(s, "5d", "5m")
                elif prov == "av":
                    df = _av_intraday(s, 5, api)
            else:
                if prov == "yahoo":
                    period = {"1M":"1mo","6M":"6mo","1Y":"1y","ALL":"max"}.get(tf, "1y")
                    df = _yf_fetch(s, period, "1d")
                elif prov == "av":
                    df = _av_daily(s, api)
                    if not df.empty:
                        days = {"1M":30, "6M":182, "1Y":365, "ALL":None}.get(tf, 365)
                        if days is not None:
                            cutoff = pd.Timestamp.utcnow().normalize() - pd.Timedelta(days=days)
                            df = df[df.index >= cutoff]

            if not df.empty:
                used = prov
                break

        return df, used

    def _make_chart(df: pd.DataFrame, symbol: str, chart_type: str, timeframe: str, indicators: list = [], theme: str = "Black", show_grid: bool = True, grid_style: str = "solid", grid_density: str = "Medium"):
        try:
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
        except Exception:
            st.error("Plotly is required for charts. Try: pip install plotly")
            return None

        if df is None or df.empty:
            return None

        cmap = {str(c).strip().lower(): c for c in df.columns}
        O = cmap.get("open")
        H = cmap.get("high")
        L = cmap.get("low")
        C = cmap.get("close") or cmap.get("adj close") or cmap.get("adj_close")
        V = cmap.get("volume")

        if C is None:
            for c in df.columns:
                with contextlib.suppress(Exception):
                    if pd.api.types.is_numeric_dtype(df[c]):
                        C = c
                        break
        if C is None:
            return None

        overlays = [i for i in indicators if i in ["SMA", "EMA", "VWAP"]]
        oscillators = [i for i in indicators if i in ["Aroon", "RSI", "MACD"]]
        has_volume = "Volume" in indicators and V is not None
        num_osc_rows = len(oscillators)
        rows = 1 + (1 if has_volume else 0) + num_osc_rows
        if rows == 1:
            row_heights = [1.0]
        else:
            row_heights = [0.6] + [0.15] * (rows - 1)
        height = 430 + 90 * (rows - 1)

        fig = make_subplots(
            rows=rows, cols=1, shared_xaxes=True,
            row_heights=row_heights,
            vertical_spacing=0.03
        )

        if chart_type == "Candlestick" and all([O, H, L, C]):
            price = go.Candlestick(x=df.index, open=df[O], high=df[H], low=df[L], close=df[C],
                                   name=symbol.upper(), showlegend=False)
        else:
            price = go.Scatter(x=df.index, y=df[C], mode="lines", name=symbol.upper(), showlegend=False)
        fig.add_trace(price, row=1, col=1)

        # Add open price line
        if O is not None:
            open_price = df[O].iloc[0]
            last_close = df[C].iloc[-1]
            line_color = 'green' if last_close > open_price else 'red'
            fig.add_hline(y=open_price, line_dash="dot", line_color=line_color, row=1, col=1)

        if "SMA" in overlays:
            sma_period = 20
            df["SMA"] = df[C].rolling(window=sma_period, min_periods=1).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df["SMA"], name=f"SMA{sma_period}", line=dict(color="orange"), showlegend=False), row=1, col=1)

        if "EMA" in overlays:
            ema_period = 20
            df["EMA"] = df[C].ewm(span=ema_period, adjust=False, min_periods=1).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df["EMA"], name=f"EMA{ema_period}", line=dict(color="blue"), showlegend=False), row=1, col=1)

        if "VWAP" in overlays and V is not None and all([H, L, C]):
            tp = (df[H] + df[L] + df[C]) / 3
            df["VWAP"] = (tp * df[V]).cumsum() / df[V].cumsum()
            fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(color="purple"), showlegend=False), row=1, col=1)

        current_row = 2

        if has_volume:
            fig.add_trace(go.Bar(x=df.index, y=df[V], name="Volume", marker_opacity=0.45, showlegend=False),
                          row=current_row, col=1)
            fig.update_yaxes(title_text="Vol", row=current_row, col=1)
            current_row += 1

        if num_osc_rows > 0:
            for osc in oscillators:
                if osc == "RSI":
                    rsi_period = 14
                    delta = df[C].diff()
                    gain = delta.where(delta > 0, 0).fillna(0)
                    loss = -delta.where(delta < 0, 0).fillna(0)
                    avg_gain = gain.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
                    avg_loss = loss.ewm(com=rsi_period - 1, min_periods=rsi_period).mean()
                    rs = avg_gain / avg_loss
                    df["RSI"] = 100 - 100 / (1 + rs)
                    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color="cyan"), showlegend=False), row=current_row, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=current_row, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=current_row, col=1)
                    fig.update_yaxes(title_text="RSI", row=current_row, col=1)

                elif osc == "Aroon":
                    aroon_period = 25
                    df["aroon_up"] = 100 * (aroon_period - df[H].rolling(window=aroon_period).apply(lambda x: x.argmax()) - 1) / aroon_period
                    df["aroon_down"] = 100 * (aroon_period - df[L].rolling(window=aroon_period).apply(lambda x: x.argmin()) - 1) / aroon_period
                    fig.add_trace(go.Scatter(x=df.index, y=df["aroon_up"], name="Aroon Up", line=dict(color="green"), showlegend=False), row=current_row, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["aroon_down"], name="Aroon Down", line=dict(color="red"), showlegend=False), row=current_row, col=1)
                    fig.update_yaxes(title_text="Aroon", row=current_row, col=1)

                elif osc == "MACD":
                    macd_short = 12
                    macd_long = 26
                    macd_signal = 9
                    df["EMA_short"] = df[C].ewm(span=macd_short, adjust=False).mean()
                    df["EMA_long"] = df[C].ewm(span=macd_long, adjust=False).mean()
                    df["MACD"] = df["EMA_short"] - df["EMA_long"]
                    df["MACD_signal"] = df["MACD"].ewm(span=macd_signal, adjust=False).mean()
                    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
                    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="blue"), showlegend=False), row=current_row, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="Signal", line=dict(color="orange"), showlegend=False), row=current_row, col=1)
                    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="Histogram", showlegend=False), row=current_row, col=1)
                    fig.update_yaxes(title_text="MACD", row=current_row, col=1)

                current_row += 1

        # Define theme colors
        themes = {
            "Black": {"plot_bgcolor": "#000000", "paper_bgcolor": "#000000", "gridcolor": "#444444", "font_color": "#FFFFFF"},
            "White": {"plot_bgcolor": "#FFFFFF", "paper_bgcolor": "#FFFFFF", "gridcolor": "#CCCCCC", "font_color": "#000000"},
            "Blue": {"plot_bgcolor": "#1E3A8A", "paper_bgcolor": "#1E3A8A", "gridcolor": "#93C5FD", "font_color": "#FFFFFF"},
            "Teal Blue": {"plot_bgcolor": "#0D9488", "paper_bgcolor": "#0D9488", "gridcolor": "#5EEAD4", "font_color": "#FFFFFF"},
            "Purple": {"plot_bgcolor": "#4C1D95", "paper_bgcolor": "#4C1D95", "gridcolor": "#C084FC", "font_color": "#FFFFFF"},
            "More Green": {"plot_bgcolor": "#065F46", "paper_bgcolor": "#065F46", "gridcolor": "#6EE7B7", "font_color": "#FFFFFF"},
            "Red": {"plot_bgcolor": "#991B1B", "paper_bgcolor": "#991B1B", "gridcolor": "#FCA5A5", "font_color": "#FFFFFF"},
            "Yellow": {"plot_bgcolor": "#78350F", "paper_bgcolor": "#78350F", "gridcolor": "#FDBA74", "font_color": "#FFFFFF"},
            "Pink": {"plot_bgcolor": "#831843", "paper_bgcolor": "#831843", "gridcolor": "#F9A8D4", "font_color": "#FFFFFF"},
            "Gray": {"plot_bgcolor": "#4B5563", "paper_bgcolor": "#4B5563", "gridcolor": "#D1D5DB", "font_color": "#FFFFFF"}
        }
        theme_colors = themes.get(theme, themes["Black"])

        fig.update_layout(
            margin=dict(l=10, r=10, t=8, b=10),
            height=height,
            hovermode="x unified",
            xaxis_rangeslider_visible=True,
            showlegend=False,
            plot_bgcolor=theme_colors["plot_bgcolor"],
            paper_bgcolor=theme_colors["paper_bgcolor"],
            font=dict(color=theme_colors["font_color"]),
        )

        # Apply grid settings to all axes
        griddash = {"solid": "solid", "dash": "dash", "dot": "dot"}.get(grid_style, "solid")
        nticks_map = {"Low": 5, "Medium": 10, "High": 20}
        nticks = nticks_map.get(grid_density, 10)
        for i in range(1, rows + 1):
            fig.update_xaxes(showgrid=show_grid, gridcolor=theme_colors["gridcolor"], griddash=griddash, nticks=nticks, row=i, col=1)
            fig.update_yaxes(showgrid=show_grid, gridcolor=theme_colors["gridcolor"], griddash=griddash, nticks=nticks, row=i, col=1)

        fig.update_yaxes(title_text=None, row=1, col=1)

        rb = [dict(bounds=["sat","mon"])]
        if timeframe.upper() in ("1D","5D"):
            rb.append(dict(pattern="hour", bounds=[16, 9.5]))
        fig.update_xaxes(rangebreaks=rb)

        st.caption(f"{symbol.upper()} • {timeframe.upper()}")
        return fig

    # === Live Charts Section ===
    st.markdown("### 📈 Live Charts")
    _watch = st.session_state.get("watchlist", []) or ["SPY", "QQQ"]

    # Display charts side by side
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("**Chart 1**")
        with st.spinner("Loading Chart 1…"):
            df1, used1 = _load_timeframe(st.session_state.get("c1_sym", _watch[0]), st.session_state.get("c1_tf", "1M"))
        fig1 = _make_chart(df1, st.session_state.get("c1_sym", _watch[0]), st.session_state.get("c1_type", "Candlestick"), st.session_state.get("c1_tf", "1M"), st.session_state.get("ind1", ["Volume"]), st.session_state.get("theme", "Black"), st.session_state.get("show_grid", True), st.session_state.get("grid_style", "solid"), st.session_state.get("grid_density", "Medium"))
        if fig1:
            st.plotly_chart(fig1, use_container_width=True, key="chart_left", config={
                "scrollZoom": True,
                "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                "modeBarButtonsToRemove": ["zoomIn2d", "zoomOut2d"],
                "displayModeBar": True,
                "dragmode": "pan"
            })
            if used1:
                st.caption(f"Source: {'Yahoo' if used1=='yahoo' else 'Alpha Vantage'}")
        else:
            src_hint = " (set an Alpha Vantage key in the sidebar)" if provider != "Yahoo only" and not av_key else ""
            st.error(f"No data for {st.session_state.get('c1_sym', '—')} ({st.session_state.get('c1_tf', '1M')}).{src_hint}")

    with right_col:
        st.markdown("**Chart 2**")
        with st.spinner("Loading Chart 2…"):
            c2_sym_value = st.session_state.get("c1_sym", _watch[0]) if st.session_state.get("sync_symbols", True) else st.session_state.get("c2_sym", _watch[min(1, len(_watch)-1)])
            df2, used2 = _load_timeframe(c2_sym_value, st.session_state.get("c2_tf", "1Y"))
        fig2 = _make_chart(df2, c2_sym_value, st.session_state.get("c2_type", "Candlestick"), st.session_state.get("c2_tf", "1Y"), st.session_state.get("ind2", ["Volume"]), st.session_state.get("theme", "Black"), st.session_state.get("show_grid", True), st.session_state.get("grid_style", "solid"), st.session_state.get("grid_density", "Medium"))
        if fig2:
            st.plotly_chart(fig2, use_container_width=True, key="chart_right", config={
                "scrollZoom": True,
                "modeBarButtonsToAdd": ["select2d", "lasso2d"],
                "modeBarButtonsToRemove": ["zoomIn2d", "zoomOut2d"],
                "displayModeBar": True,
                "dragmode": "pan"
            })
            if used2:
                st.caption(
                    f"{'Synced • ' if st.session_state.get('sync_symbols', True) else ''}Source: "
                    f"{'Yahoo' if used2=='yahoo' else 'Alpha Vantage'}"
                )
        else:
            src_hint = " (set an Alpha Vantage key in the sidebar)" if provider != "Yahoo only" and not av_key else ""
            st.error(f"No data for {c2_sym_value or '—'} ({st.session_state.get('c2_tf', '1Y')}).{src_hint}")

    # Minimal controls below each chart
    st.markdown("### Chart Controls")
    sync_symbols = st.checkbox(
        "🔗 Sync Chart 2 symbol with Chart 1",
        value=True,
        key="sync_symbols",
        help="When enabled, both charts use the same symbol. Chart 2 symbol input is disabled."
    )

    left_control, right_control = st.columns(2)

    with left_control:
        st.markdown("**Chart 1 Controls**")
        c1_sym = st.text_input("🔍 Symbol", value=_watch[0], key="c1_sym", label_visibility="collapsed").strip().upper()
        c1_type = st.radio("", ["Candlestick", "Line"], index=0, horizontal=True, key="c1_type", label_visibility="collapsed")
        c1_tf = st.radio("", ["1D", "5D", "1M", "6M", "1Y", "All"], index=2, horizontal=True, key="c1_tf", label_visibility="collapsed")
        indicators1 = st.multiselect("", options=["Volume", "VWAP", "SMA", "EMA", "Aroon", "RSI", "MACD"], default=["Volume"], key="ind1", label_visibility="collapsed")

    with right_control:
        st.markdown("**Chart 2 Controls**")
        default_right = _watch[min(1, len(_watch)-1)]
        c2_sym_disabled = st.session_state.get("sync_symbols", True)
        c2_sym_value = c1_sym if c2_sym_disabled else default_right
        c2_sym = st.text_input("🔍 Symbol", value=c2_sym_value, key="c2_sym", disabled=c2_sym_disabled, label_visibility="collapsed").strip().upper()
        c2_type = st.radio("", ["Candlestick", "Line"], index=0, horizontal=True, key="c2_type", label_visibility="collapsed")
        c2_tf = st.radio("", ["1D", "5D", "1M", "6M", "1Y", "All"], index=4, horizontal=True, key="c2_tf", label_visibility="collapsed")
        indicators2 = st.multiselect("", options=["Volume", "VWAP", "SMA", "EMA", "Aroon", "RSI", "MACD"], default=["Volume"], key="ind2", label_visibility="collapsed")

    st.markdown('<p style="font-size:12px;">Grid Options</p>', unsafe_allow_html=True)
    show_grid = st.checkbox("Show Gridlines", value=True, key="show_grid")
    grid_style = st.selectbox("Grid Style", options=["solid", "dash", "dot"], index=0, key="grid_style")
    grid_density = st.selectbox("Grid Density", options=["Low", "Medium", "High"], index=1, key="grid_density")

    theme = st.selectbox(
        "Chart Theme",
        options=["Black", "White", "Blue", "Teal Blue", "Purple", "More Green", "Red", "Yellow", "Pink", "Gray"],
        index=0,
        key="theme",
        help="Select a color theme for the chart background and gridlines."
    )
















# =============================
# TAB 2: Order Books
# =============================
with tab2:
    st.subheader("📈 Level 2 Order Book Analysis")
    if st.session_state.watchlist:
        c1, c2 = st.columns([2, 1])
        with c1:
            ob_symbol = st.selectbox("Symbol",
                                     st.session_state.watchlist,
                                     key="ob_symbol")
        with c2:
            auto_load = st.toggle("Auto-load", value=True)

        load = auto_load or st.button("Load Order Book & Charts")

        if load and ob_symbol:
            try:
                with st.spinner(f"Loading order book for {ob_symbol}..."):
                    ob = order_book.get_order_book_data(ob_symbol)
                    snap = st.session_state.cached_stock_data.get(
                        ob_symbol) or data_manager.get_real_time_data(
                            ob_symbol)

                    chart_col, info_col = st.columns([2, 1])
                    with chart_col:
                        if ob:
                            try:
                                fig = chart_generator.create_order_book_chart(
                                    ob)
                                st.plotly_chart(fig, use_container_width=True)
                            except Exception as e:
                                st.warning(
                                    f"Order book chart unavailable: {e}")
                        else:
                            st.info(
                                "Order book data unavailable; showing recent price history."
                            )
                            try:
                                hist = data_manager.get_historical_data(
                                    ob_symbol, period="5d")
                                if isinstance(hist,
                                              pd.DataFrame) and not hist.empty:
                                    fig2 = chart_generator.create_candlestick_chart(
                                        hist, ob_symbol)
                                    st.plotly_chart(fig2,
                                                    use_container_width=True)
                            except Exception as e:
                                st.warning(f"Price chart unavailable: {e}")

                    with info_col:
                        st.subheader(f"{ob_symbol} Snapshot")
                        if isinstance(snap, dict) and snap:
                            st.metric(
                                "Price", f"${snap.get('price', 0):.2f}",
                                f"{snap.get('change_percent', 0):+.2f}%")
                        else:
                            st.caption("No snapshot available.")

                        # Book metrics
                        if ob:
                            try:
                                bid_press = order_book.calculate_bid_pressure(
                                    ob)
                                ask_press = order_book.calculate_ask_pressure(
                                    ob)
                                spread = order_book.calculate_spread(ob)
                                imb = order_book.calculate_order_imbalance(ob)
                                m1, m2 = st.columns(2)
                                with m1:
                                    st.metric("Bid Pressure",
                                              f"{bid_press:.1f}%")
                                    st.metric("Spread", f"${spread:.4f}")
                                with m2:
                                    st.metric("Ask Pressure",
                                              f"{ask_press:.1f}%")
                                    st.metric("Imbalance", f"{imb:.2f}")
                            except Exception:
                                st.caption("Order book metrics unavailable.")
            except Exception as e:
                st.error(f"Order book error: {e}")
    else:
        st.info("Add symbols to your watchlist to analyze order books.")

# =============================
# TAB 3: Alerts
# =============================
with tab3:
    st.subheader("⚠️ Alerts & Notifications")

    c1, c2 = st.columns(2)
    with c1:
        st.write("**Email Alerts**")
        email_ok = notification_manager.is_email_configured()
        st.session_state.notification_settings["email_enabled"] = st.checkbox(
            "Enable Email",
            value=st.session_state.notification_settings["email_enabled"],
            disabled=not email_ok)
        if st.session_state.notification_settings["email_enabled"]:
            st.session_state.notification_settings[
                "email_address"] = st.text_input(
                    "Recipient Email",
                    value=st.session_state.
                    notification_settings["email_address"])
            st.session_state.notification_settings[
                "from_email"] = st.text_input(
                    "From Email",
                    value=st.session_state.notification_settings["from_email"])
        st.markdown("""
            **Enable Email:** set `SENDGRID_API_KEY` and restart the app.
            """)
    with c2:
        st.write("**SMS Alerts**")
        sms_ok = notification_manager.is_sms_configured()
        st.session_state.notification_settings["sms_enabled"] = st.checkbox(
            "Enable SMS",
            value=st.session_state.notification_settings["sms_enabled"],
            disabled=not sms_ok)
        if st.session_state.notification_settings["sms_enabled"]:
            st.session_state.notification_settings[
                "phone_number"] = st.text_input(
                    "Phone Number",
                    value=st.session_state.
                    notification_settings["phone_number"],
                    placeholder="+1234567890")
        st.markdown("""
            **Enable SMS:** set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` and restart.
            """)

    st.write("---")
    st.subheader("Recent Alerts")
    if st.session_state.alerts:
        for a in reversed(st.session_state.alerts[-20:]):
            ts = a.get("timestamp", datetime.now())
            sym = a.get("symbol", "?")
            typ = a.get("type", "alert")
            msg = a.get("message", "")
            st.write(f"• {pd.to_datetime(ts)} — **{sym}** — {typ}: {msg}")
    else:
        st.info("No alerts yet. Start monitoring to generate alerts.")

# =============================
# TAB 4: News (Traditional + AI Sentiment)
# =============================
with tab4:
    st.subheader("📰 News & Sentiment")

    news_tab, sentiment_tab = st.tabs(
        ["Traditional News", "AI Market Sentiment"])

    with news_tab:
        if st.button("Fetch Latest Headlines"):
            try:
                all_news = []
                for sym in st.session_state.watchlist:
                    items = news_monitor.get_stock_news(
                        sym,
                        sources=["Yahoo Finance", "MarketWatch", "Reuters"])
                    for it in items:
                        it["symbol"] = sym
                        all_news.append(it)
                if all_news:
                    all_news.sort(
                        key=lambda x: x.get("timestamp", datetime.min),
                        reverse=True)
                    for news in all_news[:25]:
                        with st.expander(
                                f"{news.get('symbol','?')} — {news.get('title','No title')}"
                        ):
                            st.write(
                                f"**Source:** {news.get('source','Unknown')}")
                            st.write(
                                f"**Time:** {news.get('timestamp','Unknown')}")
                            st.write(
                                f"**Summary:** {news.get('summary','No summary available')}"
                            )
                            if news.get("url"):
                                st.write(f"[Read]({news['url']})")
                else:
                    st.info("No recent news found.")
            except Exception as e:
                st.error(f"News error: {e}")

    with sentiment_tab:
        c1, c2 = st.columns([2, 1])
        with c1:
            s_symbol = st.selectbox("Symbol",
                                    st.session_state.watchlist,
                                    key="sent_symbol")
        with c2:
            period = st.selectbox("Period", ["1d", "5d", "1mo", "3mo"],
                                  index=1)

        if st.button("Analyze Sentiment"):
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                st.warning("Set OPENAI_API_KEY to enable AI sentiment.")
            else:
                try:
                    # Lazy import to avoid startup failures
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=api_key)
                        use_new = True
                    except Exception:
                        import openai
                        openai.api_key = api_key
                        use_new = False

                    prompt = f"""
                    Analyze the market sentiment for {s_symbol} over the last {period}.
                    Provide:
                    1) Sentiment score (-1..+1) and overall stance
                    2) Key drivers (news, macro, technical)
                    3) Social buzz (retail vs. institutional tone)
                    4) Near-term catalysts and risks
                    5) A concise recommendation and rationale
                    """
                    with st.spinner(f"Analyzing sentiment for {s_symbol}..."):
                        if use_new:
                            resp = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {
                                        "role":
                                        "system",
                                        "content":
                                        "You are a professional market sentiment analyst."
                                    },
                                    {
                                        "role": "user",
                                        "content": prompt
                                    },
                                ],
                                temperature=0.2,
                                max_tokens=900,
                            )
                            content = resp.choices[0].message.content
                        else:
                            resp = openai.ChatCompletion.create(
                                model="gpt-4",
                                messages=[
                                    {
                                        "role":
                                        "system",
                                        "content":
                                        "You are a professional market sentiment analyst."
                                    },
                                    {
                                        "role": "user",
                                        "content": prompt
                                    },
                                ],
                                temperature=0.2,
                                max_tokens=900,
                            )
                            content = resp.choices[0].message.content
                    st.success(f"Sentiment for {s_symbol}")
                    st.write(content)
                except Exception as e:
                    st.error(f"Sentiment error: {e}")

# =============================
# TAB 5: Historical Analysis
# =============================
with tab5:
    st.subheader("📉 Historical Analysis & Patterns")
    if st.session_state.watchlist:
        sym = st.selectbox("Symbol",
                           st.session_state.watchlist,
                           key="hist_sym")
        c1, c2 = st.columns(2)
        with c1:
            period = st.selectbox("Period",
                                  ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
                                  index=2)
        with c2:
            chart = st.selectbox(
                "Chart", ["Candlestick", "Line", "Volume", "Technical"])

        if st.button("Generate Analysis"):
            try:
                data = data_manager.get_historical_data(sym, period=period)
                if isinstance(data, pd.DataFrame) and not data.empty:
                    if chart == "Candlestick":
                        fig = chart_generator.create_candlestick_chart(
                            data, sym)
                    elif chart == "Line":
                        fig = chart_generator.create_line_chart(data, sym)
                    elif chart == "Volume":
                        fig = chart_generator.create_volume_chart(data, sym)
                    else:
                        fig = chart_generator.create_technical_chart(data, sym)
                    st.plotly_chart(fig, use_container_width=True)

                    st.write("### Key Metrics")
                    k1, k2, k3, k4 = st.columns(4)
                    with k1:
                        st.metric("Avg Volume",
                                  f"{data['Volume'].mean():,.0f}")
                    with k2:
                        st.metric(
                            "Volatility",
                            f"{data['Close'].pct_change().std() * 100:.2f}%")
                    with k3:
                        pct = (data['Close'].iloc[-1] -
                               data['Close'].iloc[0]) / max(
                                   1e-9, data['Close'].iloc[0]) * 100
                        st.metric("Period Return", f"{pct:.2f}%")
                    with k4:
                        spike = data['Volume'].max() / max(
                            1, data['Volume'].mean())
                        st.metric("Max Vol Spike", f"{spike:.1f}x")
                else:
                    st.info("No historical data.")
            except Exception as e:
                st.error(f"Analysis error: {e}")
    else:
        st.info("Add symbols to your watchlist to analyze.")


# =============================
# TAB 6: Statistical Analysis ("test")
# =============================
def _safe_now():
    try:
        return datetime.now()
    except Exception:
        return pd.Timestamp.utcnow().to_pydatetime()


@st.cache_data(ttl=60)
def _load_history(symbol: str, lookback_minutes: int = 240) -> pd.DataFrame:
    # DB first
    try:
        if hasattr(db, "get_stock_history"):
            df = db.get_stock_history(symbol=symbol,
                                      lookback_minutes=int(lookback_minutes))
            if isinstance(df, pd.DataFrame) and not df.empty:
                df = df.copy()
                # normalize
                ren = {}
                for key in [
                        "timestamp", "open", "high", "low", "close", "volume"
                ]:
                    for c in df.columns:
                        if c.lower() == key:
                            ren[c] = key
                if ren:
                    df = df.rename(columns=ren)
                if "timestamp" not in df.columns and isinstance(
                        df.index, pd.DatetimeIndex):
                    df = df.reset_index().rename(
                        columns={"index": "timestamp"})
                if "close" not in df.columns and "price" in df.columns:
                    df = df.rename(columns={"price": "close"})
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(
                        df["timestamp"]).dt.tz_localize(None)
                keep = [
                    c for c in
                    ["timestamp", "open", "high", "low", "close", "volume"]
                    if c in df.columns
                ]
                out = df[keep].dropna(how="all")
                if not out.empty:
                    return out
    except Exception:
        pass
    # yfinance fallback
    try:
        if yf is not None:
            days = max(1, min(7, int(np.ceil(lookback_minutes / 390))))
            interval = "1m" if lookback_minutes <= 390 * 7 else "5m"
            raw = yf.download(symbol,
                              period=f"{days}d",
                              interval=interval,
                              progress=False)
            if isinstance(raw, pd.DataFrame) and not raw.empty:
                raw = raw.reset_index()
                ren = {
                    "Datetime": "timestamp",
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume"
                }
                for k, v in ren.items():
                    if k in raw.columns:
                        raw = raw.rename(columns={k: v})
                raw["timestamp"] = pd.to_datetime(
                    raw["timestamp"]).dt.tz_localize(None)
                keep = [
                    c for c in
                    ["timestamp", "open", "high", "low", "close", "volume"]
                    if c in raw.columns
                ]
                out = raw[keep].dropna(how="all")
                if not out.empty:
                    return out
    except Exception:
        pass
    # last cached tick
    row = st.session_state.get("cached_stock_data", {}).get(symbol)
    if row:
        ts = row.get("timestamp", _safe_now())
        price = float(row.get("price", row.get("close", 0) or 0))
        vol = float(row.get("volume", 0))
        return pd.DataFrame([{
            "timestamp": pd.to_datetime(ts).tz_localize(None),
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": vol
        }])
    return pd.DataFrame(
        columns=["timestamp", "open", "high", "low", "close", "volume"])


def _compute_features(df: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.sort_values("timestamp").copy()
    eps = 1e-12
    df["ret"] = np.log(df["close"].clip(lower=eps)) - np.log(
        df["close"].shift(1).clip(lower=eps))
    df["rv_window"] = df["ret"].rolling(window,
                                        min_periods=max(5, window // 3)).std()
    if "volume" in df.columns:
        mean = df["volume"].rolling(window,
                                    min_periods=max(5, window // 3)).mean()
        std = df["volume"].rolling(window, min_periods=max(5,
                                                           window // 3)).std()
        df["vol_z"] = (df["volume"] - mean) / (std + 1e-9)
    # AC(1)
    try:
        df["ret_lag1"] = df["ret"].shift(1)
        df["ret_ac1"] = df["ret"].rolling(window).corr(df["ret_lag1"])
    except Exception:
        df["ret_ac1"] = np.nan
    return df


def _orderbook_snapshot(symbol: str):
    try:
        ob = order_book.get_order_book_data(symbol)
        if isinstance(ob, dict):
            bid_p = ob.get("bid_price") or ob.get("best_bid_price") or (
                ob.get("bid") or {}).get("price")
            ask_p = ob.get("ask_price") or ob.get("best_ask_price") or (
                ob.get("ask") or {}).get("price")
            bid_sz = ob.get("bid_size") or ob.get("best_bid_size") or (
                ob.get("bid") or {}).get("size")
            ask_sz = ob.get("ask_size") or ob.get("best_ask_size") or (
                ob.get("ask") or {}).get("size")
            return bid_p, ask_p, bid_sz, ask_sz
    except Exception:
        pass
    return None, None, None, None


def _microprice_and_obi(bid_p, ask_p, bid_sz, ask_sz):
    try:
        if None in (bid_p, ask_p, bid_sz, ask_sz):
            return None, None, None
        spread = float(ask_p) - float(bid_p)
        depth = float(bid_sz) + float(ask_sz)
        if depth <= 0:
            return None, None, float(spread)
        obi = (float(bid_sz) - float(ask_sz)) / depth
        micro = (float(ask_p) * float(bid_sz) +
                 float(bid_p) * float(ask_sz)) / depth
        return micro, obi, float(spread)
    except Exception:
        return None, None, None


def _as_float(x):
    try:
        if isinstance(x, pd.Series):
            x = x.dropna()
            x = x.iloc[-1] if not x.empty else np.nan
        elif isinstance(x, (list, tuple, np.ndarray)):
            arr = np.array(x, dtype=float)
            x = arr.ravel()[-1] if arr.size else np.nan
        return float(x)
    except Exception:
        return np.nan


with tab6:
    st.subheader("🧪 Test / Statistical Analysis")

    wl = st.session_state.get("watchlist", [])
    if not wl:
        st.info("Add symbols to your watchlist to begin.")
    else:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            stats_symbol = st.selectbox("Symbol", wl, key="stats_symbol")
        with c2:
            lookback = st.number_input("Lookback (min)",
                                       min_value=30,
                                       max_value=10080,
                                       value=240,
                                       step=30)
        with c3:
            win = st.number_input("Rolling Window (min)",
                                  min_value=5,
                                  max_value=240,
                                  value=30,
                                  step=5)
        with c4:
            horizon_min = st.number_input("Alert horizon (min)",
                                          min_value=1,
                                          max_value=240,
                                          value=15,
                                          step=1)

        df_hist = _load_history(stats_symbol, lookback_minutes=int(lookback))
        feats = _compute_features(
            df_hist, window=int(win)) if not df_hist.empty else pd.DataFrame()

        # Order book snapshot
        bid_p, ask_p, bid_sz, ask_sz = _orderbook_snapshot(stats_symbol)
        micro, obi, spread = _microprice_and_obi(bid_p, ask_p, bid_sz, ask_sz)

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            last_px = _as_float(
                df_hist["close"].tail(1) if not df_hist.empty else np.nan)
            st.metric("Last Price",
                      f"${last_px:.2f}" if np.isfinite(last_px) else "—")
        with k2:
            st.metric("Spread (TOB)",
                      f"{spread:.4f}" if spread is not None else "—")
        with k3:
            st.metric("Order Book Imbalance",
                      f"{obi:.3f}" if obi is not None else "—")
        with k4:
            rv = _as_float(feats["rv_window"].tail(1) if (
                "rv_window" in feats and not feats.empty) else np.nan)
            st.metric("Realized Vol (roll)",
                      f"{rv:.4f}" if np.isfinite(rv) else "—")
        with k5:
            ac1 = _as_float(feats["ret_ac1"].tail(1) if (
                "ret_ac1" in feats and not feats.empty) else np.nan)
            st.metric("Return AC(1)",
                      f"{ac1:.3f}" if np.isfinite(ac1) else "—")

        # Charts
        if not df_hist.empty:
            st.markdown("**Price (close)**")
            st.line_chart(df_hist.set_index("timestamp")["close"])
        if not feats.empty and "rv_window" in feats:
            st.markdown("**Rolling Realized Volatility**")
            st.line_chart(feats.set_index("timestamp")["rv_window"])
        if obi is not None:
            st.caption(
                "Order book metrics are live at load; time-series OBI requires historical L2 captures."
            )

        # Alert Diagnostics
        st.markdown("### Alert Diagnostics")
        alerts = [
            a for a in st.session_state.get("alerts", [])
            if isinstance(a, dict) and a.get("symbol") == stats_symbol
        ]
        if alerts and not df_hist.empty:
            try:
                hist = df_hist[[
                    "timestamp", "close"
                ]].sort_values("timestamp").reset_index(drop=True)

                def fwd_ret(ts, horizon_m):
                    tgt = pd.to_datetime(ts).to_pydatetime() + timedelta(
                        minutes=int(horizon_m))
                    row0 = hist[hist["timestamp"] >= pd.to_datetime(ts)].head(
                        1)
                    rowH = hist[hist["timestamp"] >= tgt].head(1)
                    if row0.empty or rowH.empty:
                        return np.nan
                    p0 = float(row0["close"].values[0])
                    pH = float(rowH["close"].values[0])
                    if p0 <= 0:
                        return np.nan
                    return (pH / p0) - 1.0

                move_bp = st.number_input(
                    "Move threshold (bp)",
                    min_value=5,
                    max_value=5000,
                    value=50,
                    step=5,
                    help=
                    "Basis points move (e.g., 50 = 0.50%) to count as 'hit'.")

                out_rows = []
                for a in alerts:
                    ts = a.get("timestamp") or a.get("time") or _safe_now()
                    side = (a.get("side") or a.get("direction") or "").lower()
                    prob = a.get("prob") or a.get("probability")
                    fwd = fwd_ret(ts, horizon_min)
                    hit = np.nan
                    if pd.notnull(fwd):
                        thr = float(move_bp) / 10000.0
                        if side in ("long", "buy", "bullish"):
                            hit = float(fwd >= thr)
                        elif side in ("short", "sell", "bearish"):
                            hit = float((-fwd) >= thr)
                        else:
                            hit = float(abs(fwd) >= thr)
                    out_rows.append({
                        "timestamp": pd.to_datetime(ts),
                        "symbol": stats_symbol,
                        "side": side,
                        "prob": prob,
                        f"forward_ret_{int(horizon_min)}m": fwd,
                        f"hit_bp≥{int(move_bp)}": hit
                    })

                eval_df = pd.DataFrame(out_rows)
                hit_col = f"hit_bp≥{int(move_bp)}"
                hit_rate = eval_df[hit_col].mean() if (
                    hit_col in eval_df
                    and not eval_df[hit_col].isna().all()) else np.nan
                st.metric(
                    "Alert Hit-Rate",
                    f"{hit_rate*100:,.1f}%" if pd.notnull(hit_rate) else "—",
                    help=
                    f"Reached ±{int(move_bp)} bp within {int(horizon_min)} min (direction-aware if side given)."
                )

                # Calibration curve
                if "prob" in eval_df.columns and eval_df["prob"].notna().any():
                    try:
                        bins = np.linspace(0, 1, 11)
                        eval_df["p_bin"] = pd.cut(
                            eval_df["prob"].astype(float).clip(0, 1),
                            bins=bins,
                            include_lowest=True)
                        calib = eval_df.groupby(
                            "p_bin",
                            dropna=True)[hit_col].mean().reset_index()
                        calib["center"] = calib["p_bin"].apply(
                            lambda x: x.mid if hasattr(x, "mid") else np.nan)
                        calib = calib.dropna(subset=["center"])
                        st.markdown("**Reliability (Calibration) Curve**")
                        st.line_chart(calib.set_index("center")[hit_col])
                        st.caption(
                            "If well-calibrated, the curve should lie near the diagonal y=x."
                        )
                    except Exception:
                        st.caption(
                            "Not enough probability data for calibration.")

                # Details
                st.dataframe(eval_df.sort_values("timestamp", ascending=False),
                             use_container_width=True)

                # Export
                with st.expander("Export"):
                    st.download_button(
                        label="⬇️ Download Alert Evaluation CSV",
                        data=eval_df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{stats_symbol}_alert_eval.csv",
                        mime="text/csv")
            except Exception as e:
                st.info(f"Alert evaluation unavailable: {e}")
        else:
            st.caption(
                "No alerts for this symbol yet, or insufficient history to evaluate outcomes."
            )

        with st.expander("Integration tips"):
            st.markdown("""
                - Provide `db.get_stock_history(symbol, lookback_minutes)` for better minute-level history.
                - To track time-series OBI/microprice, store L2 snapshots and expose `db.get_orderbook_history(...)`.
                - Alerts assumed as dicts in `st.session_state.alerts` with keys like `symbol`, `timestamp`, `side`, optional `prob`.
                - Move threshold uses **basis points** (50 bp = 0.50%).
                - Read-only: doesn't modify your existing monitoring or DB pipeline.
                """)

# =============================
# Auto-refresh & Footer
# =============================
if st.session_state.monitoring:
    time.sleep(1)
    st.rerun()

st.markdown("---")

st.caption("Developed by Zia Quant Fund · 2025")


if __name__ == "__main__":
    try:
        from pathlib import Path
        from streamlit.web import bootstrap

        bootstrap.run(str(Path(__file__).resolve()), "", [], {})
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Streamlit is not installed. Install dependencies with `pip install -r requirements.txt`."
        ) from exc

"""
Streamlit Dashboard for Pairs Trading Analytics
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import asyncio
import threading
import time
from datetime import datetime, timedelta
import io

from src.pipeline import MarketDataPipeline
from src.storage import DataStore

st.set_page_config(
    page_title="Quant Pairs Trading Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Header styling */
    .main-header {
        font-size: 4rem;
        font-weight: 800;
        color: white;
        margin: 0.1rem 0;
        text-align: center;
        padding: 0rem 0;
    }
    
    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.2rem;
        margin: 0.1rem 0 0.5rem 0;
        font-weight: 400;
    }
    
    /* Metric cards */
    .stMetric {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .stMetric:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(59, 130, 246, 0.2);
        border-color: #3b82f6;
    }
    
    /* Metric labels */
    .stMetric label {
        color: #94a3b8 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }
    
    /* Metric values */
    .stMetric [data-testid="stMetricValue"] {
        color: #e0e7ff !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    
    /* Alert box */
    .alert-box {
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #ef4444;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(239, 68, 68, 0.2);
        transition: all 0.3s ease;
    }
    
    .alert-box:hover {
        transform: translateX(5px);
        box-shadow: 0 6px 12px rgba(239, 68, 68, 0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: 2px solid transparent;
        transition: all 0.3s ease;
        padding: 0.5rem 1.5rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #0f172a;
        padding: 0.5rem;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        border-radius: 8px;
        padding: 0 24px;
        background: #1e293b;
        border: 1px solid #334155;
        color: #94a3b8;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white;
        border-color: #3b82f6;
        box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #3b82f6, transparent);
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Cards */
    .info-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #334155;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }
    
    /* Plotly charts background */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None
if 'pipeline_running' not in st.session_state:
    st.session_state.pipeline_running = False
if 'alerts' not in st.session_state:
    st.session_state.alerts = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = None
if 'adf_results' not in st.session_state:
    st.session_state.adf_results = None
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'using_uploaded_data' not in st.session_state:
    st.session_state.using_uploaded_data = False


def run_pipeline_async(pipeline, timeframes):
    """Run pipeline in background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(pipeline.start(timeframes))


def start_pipeline(symbols, timeframes):
    """Start the data collection pipeline"""
    if st.session_state.pipeline_running:
        return
    
    st.session_state.pipeline = MarketDataPipeline(
        symbols=symbols,
        db_path="market_data.db"
    )
    
    # Run in background thread
    thread = threading.Thread(
        target=run_pipeline_async,
        args=(st.session_state.pipeline, timeframes),
        daemon=True
    )
    thread.start()
    
    st.session_state.pipeline_running = True
    st.session_state.last_update = datetime.now()


def check_alerts(z_score, threshold, symbol_a, symbol_b):
    """Check for alert conditions"""
    if pd.notna(z_score):
        current_z = float(z_score)
        
        if abs(current_z) > threshold:
            alert_msg = f"⚠️ Z-Score Alert: {symbol_a}/{symbol_b} z-score = {current_z:.2f} (threshold: ±{threshold})"
            
            # Add to alerts if not duplicate
            if not st.session_state.alerts or st.session_state.alerts[-1] != alert_msg:
                # Keep only the most recent 5 alerts
                if len(st.session_state.alerts) >= 5:
                    st.session_state.alerts.pop(0)  # Remove oldest
                st.session_state.alerts.append(alert_msg)
                
                # Log to database
                if st.session_state.pipeline:
                    try:
                        st.session_state.pipeline.data_store.log_alert(
                            alert_type='z_score_breach',
                            message=alert_msg,
                            symbol=f"{symbol_a}/{symbol_b}",
                            value=current_z,
                            threshold=threshold
                        )
                    except:
                        pass
            
            return True
    return False


st.markdown('<h1 class="main-header">📈 Quant Pairs Trading Analytics</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">🚀 Real-time Statistical Arbitrage • Live Market Data • Advanced Analytics</p>', unsafe_allow_html=True)
st.markdown("---")

st.sidebar.markdown('<h2 style="color: #3b82f6; font-weight: 700;">⚙️ Controls</h2>', unsafe_allow_html=True)

st.sidebar.markdown('<h4 style="color: #8b5cf6; margin-top: 1.5rem;">🎯 Symbol Selection</h4>', unsafe_allow_html=True)
symbol_a = st.sidebar.text_input("🅰️ Symbol A", value="btcusdt", help="First trading pair").lower()
symbol_b = st.sidebar.text_input("🅱️ Symbol B", value="ethusdt", help="Second trading pair").lower()

st.sidebar.markdown('<h4 style="color: #8b5cf6; margin-top: 1.5rem;">⏱️ Timeframe</h4>', unsafe_allow_html=True)
timeframe = st.sidebar.selectbox(
    "Select Analysis Timeframe",
    options=['1s', '1m', '5m', '15m'],
    index=1,
    help="Choose the timeframe for analytics"
)

st.sidebar.markdown('<h4 style="color: #8b5cf6; margin-top: 1.5rem;">📊 Analytics Parameters</h4>', unsafe_allow_html=True)
rolling_window = st.sidebar.slider(
    "📍 Rolling Window",
    min_value=10,
    max_value=200,
    value=20,
    step=5,
    help="Window size for rolling calculations"
)

alert_threshold = st.sidebar.slider(
    "🔔 Z-Score Alert Threshold",
    min_value=1.0,
    max_value=5.0,
    value=2.0,
    step=0.1,
    help="Trigger alerts when |z-score| exceeds this value"
)

data_limit = st.sidebar.slider(
    "📄 Number of Bars",
    min_value=50,
    max_value=1000,
    value=200,
    step=50,
    help="Maximum bars to load for analysis"
)

st.sidebar.markdown('<h4 style="color: #8b5cf6; margin-top: 1.5rem;">🎬 Data Collection</h4>', unsafe_allow_html=True)

col1, col2 = st.sidebar.columns(2)

with col1:
    start_btn = st.button(
        "▶️ Start",
        disabled=st.session_state.pipeline_running,
        use_container_width=True,
        type="primary"
    )
    if start_btn:
        symbols = [symbol_a, symbol_b]
        timeframes = ['1s', '1m', '5m']
        start_pipeline(symbols, timeframes)
        st.success("✅ Pipeline started!")
        st.rerun()

with col2:
    stop_btn = st.button(
        "⏸️ Stop",
        disabled=not st.session_state.pipeline_running,
        use_container_width=True
    )
    if stop_btn:
        if st.session_state.pipeline:
            st.session_state.pipeline.stop_sync()
        st.session_state.pipeline_running = False
        st.info("⏹️ Pipeline stopped")
        st.rerun()

if st.session_state.pipeline_running:
    st.sidebar.markdown(
        '<div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); '
        'padding: 0.8rem; border-radius: 10px; text-align: center; margin: 1rem 0; '
        'box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);">' 
        '<span style="font-size: 1.1rem; font-weight: 700; color: white;">🟢 PIPELINE RUNNING</span></div>',
        unsafe_allow_html=True
    )
    if st.session_state.last_update:
        elapsed = (datetime.now() - st.session_state.last_update).seconds
        st.sidebar.caption(f"⏱️ Running for {elapsed}s")
else:
    st.sidebar.markdown(
        '<div style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%); '
        'padding: 0.8rem; border-radius: 10px; text-align: center; margin: 1rem 0; '
        'box-shadow: 0 4px 6px rgba(107, 114, 128, 0.3);">' 
        '<span style="font-size: 1.1rem; font-weight: 700; color: white;">🔴 PIPELINE STOPPED</span></div>',
        unsafe_allow_html=True
    )

st.sidebar.markdown("---")

st.sidebar.markdown('<h4 style="color: #8b5cf6;">🔄 Auto Controls</h4>', unsafe_allow_html=True)
auto_refresh = st.sidebar.checkbox("⏰ Auto-refresh (every 2s)", value=True)

if st.sidebar.button("🔄 Refresh Now", use_container_width=True, type="secondary"):
    st.rerun()

st.sidebar.markdown("---")

st.sidebar.markdown('<h4 style="color: #8b5cf6;">🧪 Advanced Actions</h4>', unsafe_allow_html=True)

run_adf = st.sidebar.button("📊 Run ADF Stationarity Test", use_container_width=True)

if not st.session_state.pipeline:
    st.session_state.pipeline = MarketDataPipeline(
        symbols=[symbol_a, symbol_b],
        db_path="market_data.db"
    )

if st.session_state.using_uploaded_data and st.session_state.uploaded_data is not None:
    # Use uploaded data
    uploaded_data = st.session_state.uploaded_data
    
    # Filter data for selected symbols if needed
    # For simplicity, we'll treat the uploaded data as belonging to symbol_a
    # In a more advanced implementation, you might have separate columns for each symbol
    
    # Resample uploaded data to selected timeframe
    try:
        # Assuming the uploaded data is for symbol_a
        ohlcv_a = uploaded_data.copy()
        ohlcv_a.set_index('timestamp', inplace=True)
        
        # Resample to selected timeframe
        if timeframe == '1s':
            resampled_data = ohlcv_a
        else:
            resample_rule = {
                '1m': '1T',
                '5m': '5T',
                '15m': '15T'
            }.get(timeframe, '1T')
            
            resampled_data = ohlcv_a.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        
        # Create analytics dict
        analytics = {}
        
        # Simple analytics for demonstration
        # In a full implementation, you'd calculate all the same metrics as with live data
        if len(resampled_data) > 0:
            analytics['price_series_a'] = resampled_data['close']
            
            # Calculate basic statistics
            if len(resampled_data) > 1:
                returns = resampled_data['close'].pct_change().dropna()
                analytics['volatility'] = returns.std() * (252**0.5)  # Annualized volatility
                analytics['returns'] = returns.mean() * 252  # Annualized return
                
            # Set some default values for display
            analytics['hedge_ratio'] = {'beta': 1.0, 'r_squared': 0.5}
            analytics['correlation'] = 0.5
            analytics['z_score'] = pd.Series([0]*min(20, len(resampled_data)), index=resampled_data.index[-min(20, len(resampled_data)):])
            analytics['half_life'] = 100
            
        # For symbol_b, we'll need another dataset or generate synthetic data
        analytics['price_series_b'] = resampled_data['close'] * 1.1  # Simple multiplier
        
    except Exception as e:
        st.error(f"Error processing uploaded data: {e}")
        analytics = {}
else:
    try:
        analytics = st.session_state.pipeline.calculate_pairs_analytics(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            timeframe=timeframe,
            window=rolling_window,
            limit=data_limit
        )
        
        if not analytics:
            data_a = st.session_state.pipeline.get_resampled_data(symbol_a, timeframe, limit=10)
            data_b = st.session_state.pipeline.get_resampled_data(symbol_b, timeframe, limit=10)
            st.warning(f"📊 Data Status: {symbol_a}={len(data_a)} bars, {symbol_b}={len(data_b)} bars, timeframe={timeframe}")
            st.info("⏳ Collecting data... Need at least 10+ bars for analytics. Current bars will appear above.")
            
    except Exception as e:
        st.error(f"Error calculating analytics: {e}")
        import traceback
        st.code(traceback.format_exc())
        analytics = {}

# Display metrics
if analytics:
    # Key metrics row with enhanced styling
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    metric_cols = st.columns(5)
    
    hedge_ratio = analytics.get('hedge_ratio', {})
    
    with metric_cols[0]:
        beta = hedge_ratio.get('beta', 0)
        st.metric("🎯 Hedge Ratio (β)", f"{beta:.4f}", help="OLS regression coefficient")
    
    with metric_cols[1]:
        r2 = hedge_ratio.get('r_squared', 0)
        st.metric("🎯 R² Score", f"{r2:.4f}", help="Goodness of fit measure")
    
    with metric_cols[2]:
        correlation = analytics.get('correlation', 0)
        color = "🟢" if correlation > 0.7 else "🟡" if correlation > 0.5 else "🔴"
        st.metric(f"{color} Correlation", f"{correlation:.4f}", help="Pearson correlation coefficient")
    
    with metric_cols[3]:
        z_score = analytics.get('z_score')
        if z_score is not None and len(z_score) > 0:
            current_z = z_score.iloc[-1]
            z_color = "🔴" if abs(current_z) > alert_threshold else "🟢"
            st.metric(f"{z_color} Current Z-Score", f"{current_z:.2f}", help="Normalized spread deviation")
            
            # Check alerts
            check_alerts(current_z, alert_threshold, symbol_a, symbol_b)
        else:
            st.metric("⚪ Current Z-Score", "N/A")
    
    with metric_cols[4]:
        half_life = analytics.get('half_life', 0)
        if pd.notna(half_life):
            st.metric("⏳ Half-Life", f"{half_life:.1f}", help="Mean reversion speed (bars)")
        else:
            st.metric("⏳ Half-Life", "N/A")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ADF Test results
    if run_adf:
        spread = analytics.get('spread')
        if spread is not None and len(spread) > 0:
            st.session_state.adf_results = st.session_state.pipeline.run_adf_test(spread)
        
        # Show info message when test is initiated
        st.info("ADF test initiated. Results will appear below after completion.")
    
    # ADF Test results (if available)
    if st.session_state.adf_results:
        st.markdown("### 📊 Augmented Dickey-Fuller Test (Stationarity)")
        adf_results = st.session_state.adf_results
        
        # Check if there was an error in the ADF test
        if 'error' in adf_results:
            st.error(f"ADF Test Error: {adf_results['error']}")
        else:
            adf_cols = st.columns(4)
            
            with adf_cols[0]:
                adf_stat = adf_results.get('adf_statistic', np.nan)
                if pd.isna(adf_stat):
                    st.metric("ADF Statistic", "N/A")
                else:
                    st.metric("ADF Statistic", f"{adf_stat:.4f}")
            
            with adf_cols[1]:
                p_value = adf_results.get('p_value', np.nan)
                if pd.isna(p_value):
                    st.metric("P-Value", "N/A")
                else:
                    st.metric("P-Value", f"{p_value:.4f}")
            
            with adf_cols[2]:
                is_stationary = adf_results.get('is_stationary', False)
                status = "Yes" if is_stationary else "No"
                st.metric("Stationary?", status)
            
            with adf_cols[3]:
                critical_vals = adf_results.get('critical_values', {})
                if critical_vals and '5%' in critical_vals:
                    crit_val = critical_vals.get('5%', np.nan)
                    if pd.isna(crit_val):
                        st.metric("Critical Value (5%)", "N/A")
                    else:
                        st.metric("Critical Value (5%)", f"{crit_val:.4f}")
                else:
                    st.metric("Critical Value (5%)", "N/A")
            
            if is_stationary:
                st.success("✅ Spread is stationary - good for mean reversion strategy")
            else:
                st.info("⚠️ Spread is not stationary - pairs may not be cointegrated")
    
    if st.session_state.alerts:
        st.markdown("### ⚠️ Recent Z-Score Alerts")
        # Show only the most recent alert
        latest_alert = st.session_state.alerts[-1]
        st.warning(latest_alert)
    
    st.markdown("---")
    
    chart_tabs = st.tabs([
        "📊 Prices", 
        "📉 Spread & Z-Score", 
        "🔗 Correlation",
        "📈 Statistics"
    ])
    
    with chart_tabs[0]:
        ohlcv_a = analytics.get('ohlcv_a')
        ohlcv_b = analytics.get('ohlcv_b')
        
        if ohlcv_a is not None and not ohlcv_a.empty and ohlcv_b is not None and not ohlcv_b.empty:
            st.markdown("### Individual Price Views")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.caption(f"{symbol_a.upper()} OHLC (last {min(50, len(ohlcv_a))} bars)")
                ohlcv_a_display = ohlcv_a.tail(50).reset_index()
                
                # Filter out invalid data (zero or negative prices)
                ohlcv_a_display = ohlcv_a_display[
                    (ohlcv_a_display['open'] > 0) & 
                    (ohlcv_a_display['high'] > 0) & 
                    (ohlcv_a_display['low'] > 0) & 
                    (ohlcv_a_display['close'] > 0)
                ]
                
                if len(ohlcv_a_display) > 0:
                    latest_row = ohlcv_a_display.iloc[-1]
                    current_price = latest_row['close']
                    open_price = latest_row['open']
                    price_change = current_price - open_price
                    price_change_pct = (price_change / open_price) * 100 if open_price != 0 else 0
                    
                    # Display current price and change
                    color = "#10b981" if price_change >= 0 else "#ef4444"
                    st.markdown(f"""
                        <div style='font-size: 1.5rem; font-weight: bold; color: {color};'>
                            ${current_price:.2f}
                            <span style='font-size: 1rem;'>
                                {'+' if price_change >= 0 else ''}{price_change:.2f} 
                                ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    fig_a = go.Figure(
                        data=[
                            go.Candlestick(
                                x=ohlcv_a_display["timestamp"],
                                open=ohlcv_a_display["open"],
                                high=ohlcv_a_display["high"],
                                low=ohlcv_a_display["low"],
                                close=ohlcv_a_display["close"],
                                name=f"{symbol_a.upper()}",
                                increasing_line_color='#10b981',
                                decreasing_line_color='#ef4444'
                            )
                        ]
                    )
                    y_min = ohlcv_a_display['low'].min()
                    y_max = ohlcv_a_display['high'].max()
                    y_padding = (y_max - y_min) * 0.1  # 10% padding
                    
                    fig_a.update_layout(
                        xaxis_title="Time",
                        yaxis_title="Price",
                        template='plotly_dark',
                        height=400,
                        xaxis_rangeslider_visible=False,
                        yaxis=dict(
                            range=[y_min - y_padding, y_max + y_padding],
                            autorange=False  # Disable auto-range to prevent including zero
                        )
                    )
                    st.plotly_chart(fig_a, use_container_width=True)
                else:
                    st.warning(f"No valid data for {symbol_a.upper()} yet. Waiting for clean bars...")
            
            with col_b:
                st.caption(f"{symbol_b.upper()} OHLC (last {min(50, len(ohlcv_b))} bars)")
                ohlcv_b_display = ohlcv_b.tail(50).reset_index()
                
                # Filter out invalid data (zero or negative prices)
                ohlcv_b_display = ohlcv_b_display[
                    (ohlcv_b_display['open'] > 0) & 
                    (ohlcv_b_display['high'] > 0) & 
                    (ohlcv_b_display['low'] > 0) & 
                    (ohlcv_b_display['close'] > 0)
                ]
                
                if len(ohlcv_b_display) > 0:
                    latest_row = ohlcv_b_display.iloc[-1]
                    current_price = latest_row['close']
                    open_price = latest_row['open']
                    price_change = current_price - open_price
                    price_change_pct = (price_change / open_price) * 100 if open_price != 0 else 0
                    
                    # Display current price and change
                    color = "#10b981" if price_change >= 0 else "#ef4444"
                    st.markdown(f"""
                        <div style='font-size: 1.5rem; font-weight: bold; color: {color};'>
                            ${current_price:.2f}
                            <span style='font-size: 1rem;'>
                                {'+' if price_change >= 0 else ''}{price_change:.2f} 
                                ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%)
                            </span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    fig_b = go.Figure(
                        data=[
                            go.Candlestick(
                                x=ohlcv_b_display["timestamp"],
                                open=ohlcv_b_display["open"],
                                high=ohlcv_b_display["high"],
                                low=ohlcv_b_display["low"],
                                close=ohlcv_b_display["close"],
                                name=f"{symbol_b.upper()}",
                                increasing_line_color='#10b981',
                                decreasing_line_color='#ef4444'
                            )
                        ]
                    )
                    y_min = ohlcv_b_display['low'].min()
                    y_max = ohlcv_b_display['high'].max()
                    y_padding = (y_max - y_min) * 0.1  # 10% padding
                    
                    fig_b.update_layout(
                        xaxis_title="Time",
                        yaxis_title="Price",
                        template='plotly_dark',
                        height=400,
                        xaxis_rangeslider_visible=False,
                        yaxis=dict(
                            range=[y_min - y_padding, y_max + y_padding],
                            autorange=False  # Disable auto-range to prevent including zero
                        )
                    )
                    st.plotly_chart(fig_b, use_container_width=True)
                else:
                    st.warning(f"No valid data for {symbol_b.upper()} yet. Waiting for clean bars...")
    
    with chart_tabs[1]:
        spread = analytics.get('spread')
        z_score = analytics.get('z_score')
        
        if spread is not None and z_score is not None:
            st.markdown("### 📈 Time Series Analysis")
            
            col_spread, col_zscore = st.columns(2)
            
            with col_spread:
                st.caption("Spread Over Time")
                
                if len(spread) > 0:
                    current_spread = spread.iloc[-1]
                    st.markdown(f"""
                        <div style='font-size: 1.5rem; font-weight: bold; color: #8b5cf6;'>
                            {current_spread:.4f}
                        </div>
                    """, unsafe_allow_html=True)
                
                fig_spread = go.Figure()
                fig_spread.add_trace(
                    go.Scatter(
                        x=spread.index,
                        y=spread.values,
                        name='Spread',
                        line=dict(color='#8b5cf6', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(139, 92, 246, 0.1)'
                    )
                )
                fig_spread.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Spread",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=40)
                )
                st.plotly_chart(fig_spread, use_container_width=True)
            
            with col_zscore:
                st.caption("Z-Score Over Time")
                
                if len(z_score) > 0:
                    current_z = z_score.iloc[-1]
                    color = "#10b981" if abs(current_z) <= alert_threshold else "#ef4444"
                    st.markdown(f"""
                        <div style='font-size: 1.5rem; font-weight: bold; color: {color};'>
                            {current_z:.2f}
                        </div>
                    """, unsafe_allow_html=True)
                
                fig_zscore = go.Figure()
                fig_zscore.add_trace(
                    go.Scatter(
                        x=z_score.index,
                        y=z_score.values,
                        name='Z-Score',
                        line=dict(color='#10b981', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(16, 185, 129, 0.1)'
                    )
                )
                
                fig_zscore.add_hline(
                    y=alert_threshold,
                    line_dash="dash",
                    line_color="#ef4444",
                    line_width=2,
                    annotation_text=f"+{alert_threshold}",
                    annotation_position="right"
                )
                fig_zscore.add_hline(
                    y=-alert_threshold,
                    line_dash="dash",
                    line_color="#10b981",
                    line_width=2,
                    annotation_text=f"-{alert_threshold}",
                    annotation_position="right"
                )
                fig_zscore.add_hline(
                    y=0,
                    line_dash="dot",
                    line_color="gray",
                    line_width=1
                )
                
                fig_zscore.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Z-Score",
                    template='plotly_dark',
                    height=350,
                    hovermode='x unified',
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=40)
                )
                st.plotly_chart(fig_zscore, use_container_width=True)
            
            st.markdown("---")
            
            # Section 2: Scatter Plot (Z-Score vs Spread)
            st.markdown("### 📊 Z-Score vs Spread Analysis")
            
            # Align spread and z_score data
            aligned_data = pd.DataFrame({
                'spread': spread,
                'z_score': z_score
            }).dropna()
            
            # Create attractive scatter plot
            fig = go.Figure()
            
            # Color points based on z-score threshold with gradient
            colors = []
            hover_texts = []
            for idx, row in aligned_data.iterrows():
                z = row['z_score']
                s = row['spread']
                
                # Color gradient based on intensity
                if z > alert_threshold:
                    # Red intensity increases with z-score
                    intensity = min((z - alert_threshold) / alert_threshold, 1.0)
                    colors.append(f'rgba(239, 68, 68, {0.5 + intensity * 0.5})')  # Red
                    signal = "🔴 SHORT SIGNAL"
                elif z < -alert_threshold:
                    # Green intensity increases with |z-score|
                    intensity = min((abs(z) - alert_threshold) / alert_threshold, 1.0)
                    colors.append(f'rgba(16, 185, 129, {0.5 + intensity * 0.5})')  # Green
                    signal = "🟢 LONG SIGNAL"
                else:
                    # Gray for neutral
                    colors.append('rgba(107, 114, 128, 0.4)')  # Gray
                    signal = "⚪ NEUTRAL"
                
                hover_texts.append(f'{signal}<br>Spread: {s:.4f}<br>Z-Score: {z:.2f}')
            
            # Add main scatter plot
            fig.add_trace(
                go.Scatter(
                    x=aligned_data['spread'],
                    y=aligned_data['z_score'],
                    mode='markers',
                    name='Data Points',
                    marker=dict(
                        size=10,
                        color=colors,
                        line=dict(width=1, color='rgba(255, 255, 255, 0.3)'),
                        symbol='circle'
                    ),
                    text=hover_texts,
                    hovertemplate='%{text}<extra></extra>',
                    showlegend=False
                )
            )
            
            # Add threshold zones with shading
            spread_range = aligned_data['spread'].max() - aligned_data['spread'].min()
            spread_min = aligned_data['spread'].min() - spread_range * 0.05
            spread_max = aligned_data['spread'].max() + spread_range * 0.05
            
            # Overbought zone (red)
            fig.add_trace(
                go.Scatter(
                    x=[spread_min, spread_max, spread_max, spread_min],
                    y=[alert_threshold, alert_threshold, 5, 5],
                    fill='toself',
                    fillcolor='rgba(239, 68, 68, 0.1)',
                    line=dict(width=0),
                    name='Overbought Zone',
                    showlegend=True,
                    hoverinfo='skip'
                )
            )
            
            # Oversold zone (green)
            fig.add_trace(
                go.Scatter(
                    x=[spread_min, spread_max, spread_max, spread_min],
                    y=[-alert_threshold, -alert_threshold, -5, -5],
                    fill='toself',
                    fillcolor='rgba(16, 185, 129, 0.1)',
                    line=dict(width=0),
                    name='Oversold Zone',
                    showlegend=True,
                    hoverinfo='skip'
                )
            )
            
            # Add threshold lines with shapes (no annotations to avoid error)
            fig.add_hline(
                y=alert_threshold,
                line=dict(dash="dash", color="rgba(239, 68, 68, 0.8)", width=2)
            )
            
            fig.add_hline(
                y=-alert_threshold,
                line=dict(dash="dash", color="rgba(16, 185, 129, 0.8)", width=2)
            )
            
            fig.add_hline(
                y=0,
                line=dict(dash="dot", color="rgba(156, 163, 175, 0.5)", width=1)
            )
            
            # Calculate and add trend line
            if len(aligned_data) > 10:
                from scipy import stats
                slope, intercept, r_value, _, _ = stats.linregress(aligned_data['spread'], aligned_data['z_score'])
                
                x_trend = [aligned_data['spread'].min(), aligned_data['spread'].max()]
                y_trend = [slope * x + intercept for x in x_trend]
                
                fig.add_trace(
                    go.Scatter(
                        x=x_trend,
                        y=y_trend,
                        mode='lines',
                        name=f'Trend Line (R²={r_value**2:.3f})',
                        line=dict(color='rgba(139, 92, 246, 0.6)', width=2, dash='dot'),
                        showlegend=True,
                        hoverinfo='skip'
                    )
                )
            
            # Update layout for attractive appearance
            fig.update_layout(
                title=dict(
                    text='<b>Z-Score vs Spread Analysis</b><br><sub>Color intensity indicates signal strength</sub>',
                    x=0.5,
                    xanchor='center',
                    font=dict(size=20, color='#e6edf3')
                ),
                xaxis=dict(
                    title='<b>Spread</b>',
                    titlefont=dict(size=14),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(75, 85, 99, 0.2)',
                    zeroline=True,
                    zerolinecolor='rgba(156, 163, 175, 0.3)'
                ),
                yaxis=dict(
                    title='<b>Z-Score</b>',
                    titlefont=dict(size=14),
                    showgrid=True,
                    gridwidth=1,
                    gridcolor='rgba(75, 85, 99, 0.2)',
                    zeroline=True,
                    zerolinecolor='rgba(156, 163, 175, 0.3)'
                ),
                height=600,
                hovermode='closest',
                template='plotly_dark',
                plot_bgcolor='rgba(15, 23, 42, 0.8)',
                paper_bgcolor='rgba(15, 23, 42, 1)',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    font=dict(size=10)
                ),
                annotations=[]  # Removed annotations to prevent xref validation errors
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add interpretation guide with stats
            col1, col2, col3 = st.columns(3)
            
            # Calculate percentages safely
            total_points = len(aligned_data)
            
            with col1:
                red_count = sum(1 for z in aligned_data['z_score'] if z > alert_threshold)
                red_pct = f"{red_count/total_points*100:.1f}% of data" if total_points > 0 else "0% of data"
                st.metric(
                    "🔴 Short Signals",
                    f"{red_count}",
                    red_pct
                )
            
            with col2:
                neutral_count = sum(1 for z in aligned_data['z_score'] if -alert_threshold <= z <= alert_threshold)
                neutral_pct = f"{neutral_count/total_points*100:.1f}% of data" if total_points > 0 else "0% of data"
                st.metric(
                    "⚪ Neutral Range",
                    f"{neutral_count}",
                    neutral_pct
                )
            
            with col3:
                green_count = sum(1 for z in aligned_data['z_score'] if z < -alert_threshold)
                green_pct = f"{green_count/total_points*100:.1f}% of data" if total_points > 0 else "0% of data"
                st.metric(
                    "🟢 Long Signals",
                    f"{green_count}",
                    green_pct
                )
    
    # Tab 3: Correlation
    with chart_tabs[2]:
        rolling_corr = analytics.get('rolling_correlation')
        
        if rolling_corr is not None:
            fig = go.Figure()
            
            fig.add_trace(
                go.Scatter(
                    x=rolling_corr.index,
                    y=rolling_corr.values,
                    name=f'Rolling Correlation ({rolling_window})',
                    line=dict(color='#ec4899', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(236, 72, 153, 0.1)'
                )
            )
            
            fig.update_layout(
                title='Rolling Correlation',
                height=400,
                showlegend=True,
                hovermode='x unified',
                template='plotly_dark',
                yaxis=dict(range=[-1, 1])
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Tab 4: Statistics
    with chart_tabs[3]:
        stats_cols = st.columns(2)
        
        stats_a = analytics.get('stats_a', {})
        stats_b = analytics.get('stats_b', {})
        
        with stats_cols[0]:
            st.subheader(f"{symbol_a.upper()} Statistics")
            if stats_a:
                st.json(stats_a)
        
        with stats_cols[1]:
            st.subheader(f"{symbol_b.upper()} Statistics")
            if stats_b:
                st.json(stats_b)
    
else:
    st.info("⏳ Waiting for data... Start the pipeline or wait for data to accumulate.")
    st.markdown("""
    ### Getting Started
    1. **Start Pipeline**: Click "▶️ Start" in the sidebar to begin collecting live data
    2. **Configure**: Adjust symbols, timeframe, and parameters
    3. **Analyze**: View real-time charts and analytics
    4. **Monitor**: Set alert thresholds for trading signals
    """)

# Data export section
st.sidebar.markdown("---")
st.sidebar.subheader("📤 Upload Data")

# File uploader for OHLC data
uploaded_file = st.sidebar.file_uploader(
    "Upload OHLC CSV File",
    type=["csv"],
    key="ohlc_uploader",
    help="Upload CSV with columns: timestamp, open, high, low, close, volume"
)

if uploaded_file is not None:
    try:
        # Read the uploaded CSV file
        df = pd.read_csv(uploaded_file)
        
        # Validate required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            st.sidebar.error("Missing required columns. Need: timestamp, open, high, low, close, volume")
        else:
            # Convert timestamp column to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Store in session state
            st.session_state.uploaded_data = df
            st.session_state.using_uploaded_data = True
            
            st.sidebar.success(f"✅ Uploaded {len(df)} rows of OHLC data")
            st.sidebar.info("Using uploaded data for analysis. Toggle 'Use Uploaded Data' to switch back to live data.")
    except Exception as e:
        st.sidebar.error(f"Error processing file: {str(e)}")

# Toggle for using uploaded data vs live data
if 'uploaded_data' in st.session_state and st.session_state.uploaded_data is not None:
    use_uploaded = st.sidebar.toggle("Use Uploaded Data", value=st.session_state.get('using_uploaded_data', False))
    st.session_state.using_uploaded_data = use_uploaded

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Export Data")

if st.sidebar.button("Download Spread & Z-Score"):
    if analytics:
        spread = analytics.get('spread')
        z_score = analytics.get('z_score')
        
        if spread is not None and z_score is not None:
            export_df = pd.DataFrame({
                'timestamp': spread.index,
                'spread': spread.values,
                'z_score': z_score.values
            })
            
            csv = export_df.to_csv(index=False)
            st.sidebar.download_button(
                label="📄 Download CSV",
                data=csv,
                file_name=f"spread_zscore_{symbol_a}_{symbol_b}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

if st.sidebar.button("Download Alert History"):
    try:
        data_store = DataStore()
        alerts_df = data_store.get_alerts(limit=500)
        data_store.close()
        
        if not alerts_df.empty:
            csv = alerts_df.to_csv(index=False)
            st.sidebar.download_button(
                label="📄 Download Alerts CSV",
                data=csv,
                file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# Auto-refresh
if auto_refresh:
    time.sleep(2)
    st.rerun()

# Footer
st.markdown("---")
st.caption("Quant Pairs Trading Analytics Dashboard | Built with Streamlit + Plotly")

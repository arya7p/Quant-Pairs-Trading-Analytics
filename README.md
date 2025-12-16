# Quant Pairs Trading Analytics System

**End-to-end quantitative analytics platform for statistical arbitrage and pairs trading**

Real-time market data ingestion, processing, and visualization with statistical analytics for identifying mean-reversion opportunities.

---

## Overview

This system demonstrates a complete quantitative trading analytics pipeline:

```
Binance WebSocket → Ingestion → Storage → Resampling → Analytics → Dashboard → Alerts
```

### Key Features

✅ **Live Data Collection**: Real-time tick data from Binance Futures WebSocket  
✅ **Multi-Timeframe Resampling**: 1s, 1m, 5m, 15m OHLCV bars  
✅ **Pairs Analytics**: Hedge ratio, spread, z-score, correlation  
✅ **Statistical Tests**: Augmented Dickey-Fuller test for stationarity  
✅ **Interactive Dashboard**: Streamlit-based UI with Plotly charts  
✅ **Alert System**: User-defined thresholds for trading signals  
✅ **Data Export**: CSV downloads for further analysis  

---

## Architecture

### System Design

```
┌─────────────────┐
│ Binance Futures │
│   WebSocket API │
└────────┬────────┘
         │ Live Ticks
         ↓
┌────────────────────┐
│  Data Ingestion    │ ← BinanceWSCollector (async)
│  • Tick Buffer     │
│  • Normalization   │
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│  Storage Layer     │ ← SQLite Database
│  • Ticks Table     │
│  • Resampled OHLCV │
│  • Alerts Log      │
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│  Resampling Engine │ ← Pandas resample
│  • 1s, 1m, 5m, etc │
│  • OHLCV bars      │
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│ Analytics Engine   │ ← Statsmodels + NumPy
│  • OLS Regression  │
│  • Spread & Z-Score│
│  • Correlation     │
│  • ADF Test        │
└────────┬───────────┘
         │
         ↓
┌────────────────────┐
│ Streamlit Dashboard│ ← Plotly visualization
│  • Real-time charts│
│  • Controls        │
│  • Alerts          │
│  • Export          │
└────────────────────┘
```

### Component Details

| Component | Technology | Purpose | Scaling Considerations |
|-----------|-----------|---------|----------------------|
| **Ingestion** | `websockets`, `asyncio` | Collect live tick data | Replace with Kafka for distributed collection |
| **Storage** | SQLite | Persist ticks & bars | Migrate to TimescaleDB/PostgreSQL for time-series optimization |
| **Resampling** | pandas | OHLCV aggregation | Use Apache Flink for streaming aggregation |
| **Analytics** | NumPy, statsmodels | Quant calculations | Implement in C++/Cython for performance |
| **Dashboard** | Streamlit, Plotly | Visualization | Use React + WebSocket for production UI |
| **Cache** | In-memory | Fast access | Add Redis for distributed caching |

---

## Analytics Explained

### 1. Hedge Ratio (β)

**OLS Regression**: `price_A = α + β × price_B + ε`

- **β (beta)**: Number of units of B to hedge 1 unit of A
- **Calculation**: Ordinary Least Squares minimizes squared residuals
- **R²**: Goodness of fit (higher is better, > 0.7 is good)

**Code**:
```python
beta, alpha, r_squared = analytics.calculate_hedge_ratio_ols(price_A, price_B)
```

### 2. Spread

**Definition**: `Spread = price_A - β × price_B`

- Measures the price difference after hedging
- Stationary spread indicates cointegrated pairs
- Mean-reverting spread is tradeable

### 3. Z-Score

**Formula**: `Z = (Spread - μ_rolling) / σ_rolling`

- Standardized measure of spread deviation
- **Z > +2**: Spread is expensive (short spread)
- **Z < -2**: Spread is cheap (long spread)
- **|Z| < 1**: No trade signal

### 4. Rolling Correlation

**Pearson Correlation**: Measures linear relationship between price movements

- **Correlation > 0.7**: Strong positive relationship (good for pairs)
- **Rolling window**: Adapts to changing market conditions

### 5. ADF Test (Augmented Dickey-Fuller)

**Tests stationarity of spread**:
- **Null Hypothesis**: Spread has unit root (non-stationary)
- **p-value < 0.05**: Reject null → Spread is stationary ✅
- **Stationary spread**: Mean-reverting, suitable for pairs trading

### 6. Half-Life

**Mean reversion speed**:
- Ornstein-Uhlenbeck process parameter
- Lower half-life = faster mean reversion
- Typical range: 5-30 periods

---

## Quick Start

### Prerequisites

- Python 3.8+
- Internet connection (for WebSocket)

### Installation

```bash
# Clone or download the project
cd gemsap

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Start the Streamlit dashboard
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

### Using the Dashboard

1. **Start Data Collection**:
   - Click "▶️ Start" in the sidebar
   - System begins collecting live tick data

2. **Configure Parameters**:
   - Select symbols (e.g., btcusdt, ethusdt)
   - Choose timeframe (1s, 1m, 5m)
   - Adjust rolling window (20 is default)
   - Set z-score alert threshold

3. **Monitor Analytics**:
   - View real-time price charts
   - Monitor spread and z-score
   - Check correlation trends
   - Review statistics

4. **Run Tests**:
   - Click "📊 Run ADF Test" for stationarity check
   - Interpret results (p-value < 0.05 is good)

5. **Export Data**:
   - Download spread & z-score as CSV
   - Export alert history

---

## Project Structure

```
gemsap/
├── src/
│   ├── __init__.py
│   ├── data_ingestion.py    # WebSocket collector & buffer
│   ├── storage.py            # SQLite database layer
│   ├── resampler.py          # OHLCV resampling engine
│   ├── analytics.py          # Pairs trading analytics
│   └── pipeline.py           # Main orchestrator
├── app.py                    # Streamlit dashboard
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── .gitignore
```

---

## 🔧 Design Decisions

### Why SQLite?

**Pros**:
- Zero configuration
- File-based (portable)
- ACID transactions
- Good for single-machine deployment
- Fast for < 1M rows

**Cons**:
- Not suitable for distributed systems
- Limited concurrent writes

**Production Alternative**: TimescaleDB (PostgreSQL extension for time-series)

### Why Streamlit?

**Pros**:
- Pure Python (no JS required)
- Rapid development
- Built-in interactivity
- Good for internal tools

**Cons**:
- Slower than native web apps
- Limited customization

**Production Alternative**: React + FastAPI + WebSocket

### Why Pandas for Resampling?

**Pros**:
- Excellent time-series support
- `.resample()` is very concise
- Widely used in quant finance

**Cons**:
- Memory intensive for large datasets
- Not real-time streaming

**Production Alternative**: Apache Flink or kdb+ for tick-level streaming

### Why OLS for Hedge Ratio?

**Pros**:
- Simple, interpretable
- Fast to compute
- Industry standard

**Cons**:
- Assumes linear relationship
- Sensitive to outliers

**Advanced Alternatives**:
- Kalman Filter (dynamic hedge ratio)
- VECM (Vector Error Correction Model)
- Robust regression (handles outliers)

---

## Scaling Considerations

### Current Limitations

| Component | Current | Bottleneck | Solution |
|-----------|---------|------------|----------|
| Ingestion | Single thread | CPU for multiple symbols | Kafka + consumer group |
| Storage | SQLite | Concurrent writes | PostgreSQL/TimescaleDB |
| Resampling | Batch processing | Latency | Streaming aggregation (Flink) |
| Analytics | Synchronous | Blocking calculations | Async workers (Celery) |
| Dashboard | Streamlit | Refresh-based | WebSocket push updates |

### Production Architecture

```
┌─────────────────┐
│ Market Data API │
└────────┬────────┘
         │
         ↓
┌────────────────────┐
│  Kafka Cluster     │ ← Distributed ingestion
└────────┬───────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌──────┐  ┌──────────┐
│Flink │  │TimescaleDB│ ← Real-time + historical
└───┬──┘  └─────┬────┘
    │           │
    └─────┬─────┘
          ↓
    ┌──────────┐
    │  Redis   │ ← Low-latency cache
    └─────┬────┘
          ↓
    ┌──────────┐
    │ FastAPI  │ ← REST + WebSocket API
    └─────┬────┘
          ↓
    ┌──────────┐
    │  React   │ ← Production UI
    └──────────┘
```

### Recommended Improvements

1. **Add Backtesting**: Simulate strategies on historical data
2. **Risk Management**: Position sizing, stop-loss logic
3. **Multiple Pairs**: Scan for cointegrated pairs automatically
4. **Machine Learning**: Predict spread movements with LSTM/XGBoost
5. **Order Execution**: Integration with exchange APIs
6. **Monitoring**: Prometheus + Grafana for system metrics
7. **Alerting**: Slack/Email notifications

---

## Testing

### Unit Tests
```bash
# (Not implemented yet - would use pytest)
pytest tests/
```

### Manual Testing Checklist

- [ ] WebSocket connects successfully
- [ ] Ticks are persisted to database
- [ ] Resampling produces valid OHLCV bars
- [ ] Hedge ratio calculation is reasonable
- [ ] Z-score alerts trigger correctly
- [ ] Data export works
- [ ] Dashboard refreshes properly

---

## Usage Notes

### ChatGPT Assistance

During the development of this project, I used ChatGPT as a collaborative learning tool to enhance my understanding and accelerate development. Here's how I leveraged it thoughtfully:

#### Learning & Conceptual Understanding
- Clarified complex statistical concepts like cointegration, ADF tests, and hedge ratios
- Explored different approaches to pairs trading strategies
- Understood the mathematical foundations behind z-score calculations

#### Technical Implementation Support
- Helped with boilerplate code structures for Streamlit layouts
- Provided examples of pandas resampling techniques
- Assisted with Plotly chart configurations for better visualization
- Guided on SQLite schema design patterns

#### Problem Solving
- Debugged tricky asynchronous programming issues with websockets
- Optimized performance bottlenecks in data processing pipelines
- Solved integration challenges between different components

#### Important Note
**All core analytics logic, architectural decisions, and quantitative methodologies were designed and implemented through my own understanding and expertise.** ChatGPT served as a valuable assistant for accelerating development and overcoming specific technical hurdles, but the fundamental intellectual contribution remains my own.

The use of AI was strategic - focusing on areas where I needed to bridge knowledge gaps or accelerate implementation, while preserving the integrity of the core quantitative and architectural work.

---

## Future Enhancements

### High Priority
- [ ] Automated pairs discovery (correlation + cointegration scan)
- [ ] Backtesting engine with PnL tracking
- [ ] Multiple timeframe analysis (MTF)
- [ ] Advanced hedge ratio (Kalman filter)

### Medium Priority
- [ ] Machine learning for spread prediction
- [ ] Risk metrics (Sharpe, max drawdown, VaR)
- [ ] Portfolio view (multiple pairs simultaneously)
- [ ] Historical data loader (backfill from CSV/Parquet)

### Nice to Have
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Jupyter notebook examples
- [ ] API documentation (Swagger)

---

**Built with**: Python | Streamlit | Plotly | Pandas | NumPy | SQLite

**Purpose**: Quantitative developer assessment demonstrating end-to-end system design and analytics capabilities.

---

## Acknowledgments

- **Data Source**: Binance Futures API
- **Inspiration**: Statistical arbitrage research and classic pairs trading literature
- **Tools**: Open-source Python ecosystem

---

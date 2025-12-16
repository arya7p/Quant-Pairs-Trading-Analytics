# Quant Pairs Trading Analytics System
## Assignment Submission

### Student Information
- **Name**: Arya Patil
- **Course**: [Course Name]
- **Instructor**: [Instructor Name]
- **Date**: December 17, 2025

---

## Project Overview

This assignment presents the implementation of a Quantitative Pairs Trading Analytics System, an end-to-end platform for statistical arbitrage and pairs trading. The system collects real-time market data, processes it through various analytical models, and provides actionable insights for trading opportunities.

### Key Features Implemented

✅ **Live Data Collection**: Real-time tick data from Binance Futures WebSocket  
✅ **Multi-Timeframe Resampling**: 1s, 1m, 5m, 15m OHLCV bars  
✅ **Pairs Analytics**: Hedge ratio, spread, z-score, correlation  
✅ **Statistical Tests**: Augmented Dickey-Fuller test for stationarity  
✅ **Interactive Dashboard**: Streamlit-based UI with Plotly charts  
✅ **Alert System**: User-defined thresholds for trading signals  
✅ **Data Export**: CSV downloads for further analysis  

---

## System Architecture

### Component Breakdown

1. **Data Ingestion Module** (`src/data_ingestion.py`)
   - Establishes WebSocket connection with Binance Futures API
   - Collects live tick data asynchronously
   - Implements data buffering and normalization

2. **Storage Layer** (`src/storage.py`)
   - Manages SQLite database for data persistence
   - Handles tick data and resampled OHLCV bar storage
   - Provides data retrieval mechanisms for analytics

3. **Resampling Engine** (`src/resampler.py`)
   - Converts tick data to various timeframes (1s, 1m, 5m, 15m)
   - Generates OHLCV (Open, High, Low, Close, Volume) bars
   - Supports configurable window sizes

4. **Analytics Engine** (`src/analytics.py`)
   - Calculates hedge ratios using Ordinary Least Squares regression
   - Computes spread and z-score for pairs analysis
   - Performs correlation analysis and Augmented Dickey-Fuller tests
   - Determines mean reversion characteristics

5. **Main Pipeline** (`src/pipeline.py`)
   - Orchestrates the entire data flow
   - Coordinates between different modules
   - Manages system state and configuration

6. **Dashboard Interface** (`app.py`)
   - Provides interactive Streamlit web interface
   - Visualizes real-time data and analytics
   - Allows user configuration and control
   - Displays alerts and trading signals

---

## Technical Implementation

### Core Algorithms

#### 1. Hedge Ratio Calculation
Using Ordinary Least Squares (OLS) regression:
```
price_A = α + β × price_B + ε
```
Where β represents the optimal number of units of asset B needed to hedge one unit of asset A.

#### 2. Spread Computation
```
Spread = price_A - β × price_B
```
A stationary spread indicates cointegrated pairs suitable for pairs trading.

#### 3. Z-Score Analysis
```
Z = (Spread - μ_rolling) / σ_rolling
```
Standardized measure indicating when the spread deviates significantly from its mean.

#### 4. Stationarity Testing
Augmented Dickey-Fuller (ADF) test determines if the spread is mean-reverting:
- Null hypothesis: Spread has a unit root (non-stationary)
- If p-value < 0.05: Reject null hypothesis → Stationary spread ✅

---

## Project Files

```
Quant-Pairs-Trading-Analytics/
├── app.py                    # Streamlit dashboard application
├── requirements.txt          # Python dependencies
├── README.md                 # Project documentation
├── Assignment_Document.md    # This document
├── Gemscap_Assignment.docx   # Original assignment file
├── System Architecture Diagram.png  # System architecture visualization
├── .gitignore                # Git ignore rules
├── src/
│   ├── __init__.py           # Package initializer
│   ├── data_ingestion.py     # WebSocket data collector
│   ├── storage.py            # Database layer
│   ├── resampler.py          # Timeframe conversion
│   ├── analytics.py          # Statistical computations
│   └── pipeline.py           # Main orchestration
```

---

## How to Run the Application

### Prerequisites
- Python 3.8+
- Internet connection for WebSocket connectivity

### Installation Steps
1. Clone or download the project repository
2. Navigate to the project directory
3. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

### Execution
1. Start the Streamlit dashboard:
   ```
   streamlit run app.py
   ```
2. Access the dashboard at `http://localhost:8501`
3. Configure trading pairs and parameters through the sidebar
4. Monitor analytics and trading signals in real-time

---

## Design Considerations

### Technology Choices

1. **SQLite Database**
   - Chosen for simplicity and zero-configuration requirements
   - Suitable for single-machine deployment
   - Adequate performance for moderate data volumes

2. **Streamlit Framework**
   - Selected for rapid development and pure Python implementation
   - Provides built-in interactivity without JavaScript knowledge
   - Ideal for internal tools and prototyping

3. **Pandas for Resampling**
   - Utilized for excellent time-series support
   - Offers concise `.resample()` functionality
   - Widely adopted in quantitative finance community

### Scalability Aspects

While the current implementation serves as a solid prototype, production deployment would require:

- **Distributed Ingestion**: Kafka cluster for handling multiple market data streams
- **Time-Series Database**: TimescaleDB or InfluxDB for optimized data storage
- **Streaming Processing**: Apache Flink for real-time aggregations
- **Asynchronous Workers**: Celery for non-blocking calculations
- **WebSocket Updates**: Push-based dashboard updates for real-time responsiveness

---

## Conclusion

This assignment successfully demonstrates the implementation of a comprehensive quantitative trading analytics system. Through hands-on development, key concepts in statistical arbitrage and pairs trading were explored and implemented, including:

- Real-time data processing pipelines
- Statistical analysis for financial markets
- Interactive data visualization
- System design and architectural considerations

The project showcases proficiency in Python programming, quantitative finance concepts, and modern software engineering practices. The modular design allows for easy extension and enhancement, making it a solid foundation for further development in algorithmic trading systems.

---

## References

- Binance Futures API Documentation
- Statistical Arbitrage Literature
- Python Data Science Ecosystem
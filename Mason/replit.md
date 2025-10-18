# Stock Monitoring Dashboard

## Overview

This is a comprehensive real-time stock monitoring dashboard built with Streamlit that provides advanced market surveillance capabilities. The application tracks stock price movements, detects anomalies, monitors news sentiment, and sends alerts for significant market events. It's designed for traders and analysts who need to monitor multiple stocks simultaneously and receive immediate notifications when predefined conditions are met.

The system integrates multiple data sources including Yahoo Finance, Alpha Vantage, and Polygon.io to provide comprehensive market coverage. It features real-time price tracking, volume analysis, order book monitoring, news sentiment analysis, and sophisticated anomaly detection algorithms.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit Framework**: Web-based dashboard providing real-time data visualization and user interaction
- **Interactive Charts**: Plotly-based candlestick charts, volume indicators, and anomaly visualization
- **Session State Management**: Maintains user watchlists, alert settings, and cached data across page refreshes
- **Real-time Updates**: Auto-refreshing components that update stock data every second during monitoring

### Backend Architecture
- **Modular Component Design**: Separated concerns across specialized modules for data fetching, analysis, alerts, and notifications
- **Multi-threaded Processing**: Concurrent data fetching and processing using ThreadPoolExecutor for multiple stocks
- **Queue-based Data Flow**: Thread-safe communication between data fetchers and UI components using Python queue
- **Caching Strategy**: In-memory caching of stock data to reduce API calls and improve performance

### Data Sources Integration
- **Primary Source**: Yahoo Finance API (yfinance) for real-time stock data and historical information
- **Secondary Sources**: Alpha Vantage and Polygon.io APIs for enhanced data coverage and order book information
- **Rate Limiting**: Built-in request throttling to respect API limits across all data sources
- **Fallback Mechanisms**: Graceful degradation when primary data sources are unavailable

### Analytics Engine
- **Anomaly Detection**: Statistical analysis using Isolation Forest and z-score calculations to identify unusual price and volume patterns
- **Volume Analysis**: Rolling average comparisons and ratio calculations to detect volume spikes
- **Price Movement Detection**: Percentage-based thresholds for identifying significant price changes
- **Pattern Recognition**: Historical pattern matching for recurring market behaviors

### Alert System
- **Threshold-based Triggers**: Configurable price change and volume spike alerts
- **Cooldown Mechanisms**: Prevents alert spam by implementing time-based cooldown periods
- **Severity Classification**: Multi-level alert system (low, medium, high, critical) based on magnitude of changes
- **Historical Tracking**: Complete audit trail of all triggered alerts with timestamps and conditions

### News Monitoring
- **Multi-source RSS Feeds**: Aggregates news from Yahoo Finance, MarketWatch, Seeking Alpha, and Reuters
- **Keyword Analysis**: Scans headlines for high-impact keywords that could affect stock prices
- **Symbol-specific Filtering**: Associates news articles with relevant stock symbols
- **Sentiment Context**: Provides news context for price movements and anomalies

### Data Persistence
- **SQLite Database**: Local storage for historical stock data, alerts, order book information, and news articles
- **Automated Cleanup**: Configurable data retention policies to manage database size
- **Schema Design**: Optimized table structures for quick queries and efficient storage
- **Data Integrity**: Transaction-based operations ensuring consistent data state

## External Dependencies

### Market Data APIs
- **Yahoo Finance (yfinance)**: Primary data source for real-time stock prices, historical data, and company information
- **Alpha Vantage API**: Secondary data source for enhanced market data and technical indicators
- **Polygon.io API**: Level 2 market data and order book information for advanced analysis
- **Federal Reserve Economic Data (FRED)**: Economic indicators and market context data

### Communication Services
- **Twilio SMS API**: SMS alert delivery for critical stock events and threshold breaches
- **SendGrid Email API**: Email notifications with detailed alert information and charts
- **Multi-channel Notifications**: Configurable notification preferences per user

### News and Information Sources
- **RSS Feed Aggregation**: Real-time news monitoring from major financial news outlets
- **Web Scraping**: BeautifulSoup-based content extraction from financial websites
- **News API Integration**: Structured news data retrieval for sentiment analysis

### Data Processing Libraries
- **Pandas/NumPy**: Core data manipulation and numerical computations
- **Scikit-learn**: Machine learning algorithms for anomaly detection
- **SciPy**: Statistical analysis and signal processing
- **Plotly**: Interactive chart generation and data visualization

### Infrastructure Components
- **SQLite**: Embedded database for local data persistence
- **Streamlit**: Web application framework and user interface
- **Threading/Concurrent.futures**: Multi-threaded processing for real-time data handling
- **Requests**: HTTP client for API communications with rate limiting and error handling
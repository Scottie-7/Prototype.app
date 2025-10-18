import os
from datetime import timedelta
from typing import Dict, List, Optional

# Application Settings
SETTINGS = {
    # Application Configuration
    'app_name': 'Stock Monitoring Dashboard',
    'version': '1.0.0',
    'debug': os.getenv('DEBUG', 'False').lower() == 'true',
    
    # API Configuration
    'api_keys': {
        'alpha_vantage': os.getenv('ALPHA_VANTAGE_API_KEY', 'demo'),
        'polygon': os.getenv('POLYGON_API_KEY', ''),
        'fred': os.getenv('FRED_API_KEY', ''),
        'openai': os.getenv('OPENAI_API_KEY', '')
    },
    
    # Rate Limiting
    'rate_limits': {
        'alpha_vantage_calls_per_minute': 5,
        'yahoo_finance_calls_per_minute': 60,
        'polygon_calls_per_minute': 100,
        'news_scraping_delay': 1.0  # seconds between requests
    },
    
    # Alert Thresholds
    'alert_thresholds': {
        'default_price_change_percent': 25.0,
        'default_volume_multiplier': 5.0,
        'small_cap_threshold': 1e9,  # $1B market cap
        'extreme_volume_threshold': 20.0,
        'alert_cooldown_minutes': 5
    },
    
    # Monitoring Settings
    'monitoring': {
        'max_symbols_to_track': 50,
        'update_interval_seconds': 1,
        'historical_data_days': 30,
        'order_book_levels': 20,
        'anomaly_detection_window': 20
    },
    
    # Database Configuration
    'database': {
        'path': 'stock_monitor.db',
        'cleanup_interval_days': 30,
        'max_alerts_to_keep': 1000,
        'backup_enabled': True
    },
    
    # News Configuration
    'news': {
        'sources': [
            'yahoo_finance',
            'marketwatch', 
            'seeking_alpha',
            'reuters'
        ],
        'keywords': [
            'earnings', 'merger', 'acquisition', 'buyout', 'takeover',
            'FDA approval', 'clinical trial', 'breakthrough', 'patent',
            'lawsuit', 'settlement', 'bankruptcy', 'restructuring',
            'guidance', 'outlook', 'forecast', 'upgrade', 'downgrade',
            'split', 'dividend', 'spinoff', 'partnership', 'contract',
            'recall', 'investigation', 'SEC', 'regulatory',
            'surge', 'plunge', 'spike', 'crash', 'rally'
        ],
        'sentiment_threshold': 0.1,
        'max_news_items_per_symbol': 10
    },
    
    # Technical Analysis
    'technical_analysis': {
        'sma_periods': [20, 50, 200],
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'bollinger_bands_period': 20,
        'bollinger_bands_std': 2
    },
    
    # Order Book Analysis
    'order_book': {
        'max_levels_to_analyze': 20,
        'spoofing_detection': {
            'large_order_multiplier': 5.0,
            'cluster_threshold': 3,
            'spread_threshold_percent': 0.5
        },
        'pressure_calculation_levels': 10
    },
    
    # Anomaly Detection
    'anomaly_detection': {
        'volume_spike_threshold': 5.0,
        'price_change_z_score_threshold': 2.0,
        'gap_threshold_percent': 10.0,
        'correlation_threshold': 0.2,
        'isolation_forest_contamination': 0.1
    },
    
    # Visualization
    'charts': {
        'default_height': 500,
        'candlestick_height': 600,
        'technical_chart_height': 700,
        'color_scheme': {
            'bullish': '#00ff88',
            'bearish': '#ff4444',
            'neutral': '#888888',
            'volume': '#1f77b4',
            'background': '#0e1117',
            'grid': '#262730',
            'text': '#ffffff'
        }
    },
    
    # Cache Settings
    'cache': {
        'default_ttl_seconds': 300,  # 5 minutes
        'stock_data_ttl_seconds': 60,  # 1 minute
        'news_data_ttl_seconds': 900,  # 15 minutes
        'order_book_ttl_seconds': 30,  # 30 seconds
        'cleanup_interval_minutes': 60
    },
    
    # Security Settings
    'security': {
        'max_input_length': 100,
        'session_timeout_minutes': 60,
        'max_watchlist_size': 100,
        'allowed_symbols_pattern': r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$'
    },
    
    # Performance Settings
    'performance': {
        'max_concurrent_requests': 10,
        'request_timeout_seconds': 30,
        'retry_attempts': 3,
        'retry_delay_seconds': 1
    },
    
    # Logging Configuration
    'logging': {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_enabled': True,
        'file_path': 'logs/stock_monitor.log',
        'max_file_size_mb': 100,
        'backup_count': 5
    },
    
    # Default Watchlist
    'default_watchlist': [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',
        'NVDA', 'META', 'SPY', 'QQQ', 'IWM'
    ],
    
    # Market Data Sources Priority
    'data_source_priority': [
        'polygon',  # Best quality, requires API key
        'alpha_vantage',  # Good quality, free tier available
        'yahoo_finance'  # Reliable, completely free
    ],
    
    # Feature Flags
    'features': {
        'enable_order_book_analysis': True,
        'enable_news_sentiment': True,
        'enable_anomaly_detection': True,
        'enable_technical_analysis': True,
        'enable_correlation_analysis': True,
        'enable_options_analysis': False,  # Requires additional data source
        'enable_dark_pool_detection': False,  # Requires premium data
        'enable_insider_trading_alerts': False,  # Requires SEC filing data
        'enable_earnings_calendar': True,
        'enable_economic_indicators': True
    },
    
    # Small Cap Monitoring (Focus area for the application)
    'small_cap_monitoring': {
        'market_cap_threshold': 2e9,  # $2B and below
        'min_volume_threshold': 100000,  # Minimum daily volume
        'float_threshold': 50e6,  # $50M float or less for "small float"
        'price_range': {'min': 1.0, 'max': 50.0},  # Focus on $1-$50 stocks
        'squeeze_indicators': {
            'short_interest_threshold': 20.0,  # 20% or higher
            'days_to_cover_threshold': 3.0,  # 3+ days to cover
            'volume_spike_multiplier': 10.0  # 10x normal volume
        }
    },
    
    # LLM Integration (Future Implementation)
    'llm_integration': {
        'model': 'gpt-5',  # Latest OpenAI model as of August 7, 2025
        'max_tokens': 1000,
        'temperature': 0.1,  # Low temperature for factual analysis
        'system_prompt': """You are an expert financial analyst specializing in small-cap stock analysis and anomaly detection. 
                           Analyze the provided market data and identify potential trading opportunities, focusing on:
                           1. Unusual volume spikes and price movements
                           2. Order book irregularities and potential squeezes
                           3. News correlation with price action
                           4. Technical pattern recognition
                           5. Risk assessment for retail traders""",
        'analysis_types': [
            'volume_anomaly_analysis',
            'price_action_analysis', 
            'news_sentiment_analysis',
            'order_book_analysis',
            'squeeze_probability_assessment'
        ]
    },
    
    # Error Handling
    'error_handling': {
        'max_retries': 3,
        'exponential_backoff': True,
        'fallback_to_cached_data': True,
        'graceful_degradation': True,
        'alert_on_api_failures': True
    }
}

# Environment-specific overrides
if SETTINGS['debug']:
    # Development settings
    SETTINGS['rate_limits']['alpha_vantage_calls_per_minute'] = 1
    SETTINGS['monitoring']['update_interval_seconds'] = 5
    SETTINGS['cache']['default_ttl_seconds'] = 60
    SETTINGS['logging']['level'] = 'DEBUG'

# Validation functions
def validate_settings():
    """Validate critical settings"""
    errors = []
    
    # Check required API keys for production features
    if SETTINGS['features']['enable_order_book_analysis'] and not SETTINGS['api_keys']['polygon']:
        errors.append("Polygon API key required for order book analysis")
    
    # Validate thresholds
    if SETTINGS['alert_thresholds']['default_price_change_percent'] < 1:
        errors.append("Price change threshold too low")
    
    if SETTINGS['monitoring']['max_symbols_to_track'] > 100:
        errors.append("Too many symbols to track efficiently")
    
    # Check database path is writable
    db_dir = os.path.dirname(SETTINGS['database']['path'])
    if db_dir and not os.access(db_dir, os.W_OK):
        errors.append(f"Database directory not writable: {db_dir}")
    
    return errors

def get_active_features() -> List[str]:
    """Get list of enabled features"""
    return [feature for feature, enabled in SETTINGS['features'].items() if enabled]

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a specific feature is enabled"""
    return SETTINGS['features'].get(feature_name, False)

def get_api_key(service: str) -> Optional[str]:
    """Get API key for a specific service"""
    return SETTINGS['api_keys'].get(service)

def update_setting(path: str, value) -> bool:
    """Update a setting value using dot notation (e.g., 'alert_thresholds.default_price_change_percent')"""
    try:
        keys = path.split('.')
        current = SETTINGS
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key in current:
                current = current[key]
            else:
                return False
        
        # Set the final value
        current[keys[-1]] = value
        return True
        
    except Exception:
        return False

# Export commonly used settings
DEFAULT_WATCHLIST = SETTINGS['default_watchlist']
ALERT_THRESHOLDS = SETTINGS['alert_thresholds']
MONITORING_CONFIG = SETTINGS['monitoring']
CACHE_CONFIG = SETTINGS['cache']
CHART_COLORS = SETTINGS['charts']['color_scheme']

# Initialize validation on import
validation_errors = validate_settings()
if validation_errors:
    print("⚠️  Configuration validation warnings:")
    for error in validation_errors:
        print(f"   - {error}")

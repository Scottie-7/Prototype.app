import pandas as pd
import numpy as np
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
import hashlib
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    """Utility class for data processing and manipulation"""
    
    @staticmethod
    def clean_symbol(symbol: str) -> str:
        """Clean and validate stock symbol"""
        if not symbol:
            return ""
        
        # Remove whitespace and convert to uppercase
        cleaned = symbol.strip().upper()
        
        # Remove special characters except dots and hyphens
        cleaned = re.sub(r'[^A-Z0-9.\-]', '', cleaned)
        
        # Validate symbol format (basic validation)
        if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$', cleaned):
            logger.warning(f"Potentially invalid symbol format: {cleaned}")
        
        return cleaned
    
    @staticmethod
    def validate_price_data(price: Union[str, float, int]) -> Optional[float]:
        """Validate and convert price data"""
        try:
            if price is None or price == '':
                return None
            
            # Convert to float
            if isinstance(price, str):
                # Remove currency symbols and commas
                price = re.sub(r'[$,]', '', price)
                price = float(price)
            else:
                price = float(price)
            
            # Check for reasonable price range
            if price < 0:
                logger.warning(f"Negative price detected: {price}")
                return None
            elif price > 1000000:  # $1M per share seems unreasonable
                logger.warning(f"Extremely high price detected: {price}")
            
            return round(price, 4)  # Round to 4 decimal places
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating price data: {price}, error: {str(e)}")
            return None
    
    @staticmethod
    def validate_volume_data(volume: Union[str, int, float]) -> Optional[int]:
        """Validate and convert volume data"""
        try:
            if volume is None or volume == '':
                return None
            
            # Convert to int
            if isinstance(volume, str):
                # Remove commas and convert
                volume = re.sub(r'[,]', '', volume)
                volume = int(float(volume))  # Handle decimal strings
            else:
                volume = int(volume)
            
            # Check for reasonable volume range
            if volume < 0:
                logger.warning(f"Negative volume detected: {volume}")
                return None
            
            return volume
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error validating volume data: {volume}, error: {str(e)}")
            return None
    
    @staticmethod
    def calculate_percentage_change(current: float, previous: float) -> Optional[float]:
        """Calculate percentage change between two values"""
        try:
            if previous == 0:
                return None
            
            change = ((current - previous) / previous) * 100
            return round(change, 2)
            
        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating percentage change: {str(e)}")
            return None
    
    @staticmethod
    def normalize_timestamp(timestamp: Union[str, datetime, int, float]) -> Optional[datetime]:
        """Normalize various timestamp formats to datetime"""
        try:
            if timestamp is None:
                return None
            
            if isinstance(timestamp, datetime):
                return timestamp
            elif isinstance(timestamp, str):
                # Try common timestamp formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y'
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(timestamp, fmt)
                    except ValueError:
                        continue
                
                # If no format worked, try pandas
                return pd.to_datetime(timestamp)
            elif isinstance(timestamp, (int, float)):
                # Assume Unix timestamp
                if timestamp > 1e10:  # Milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
            
            return None
            
        except Exception as e:
            logger.error(f"Error normalizing timestamp: {timestamp}, error: {str(e)}")
            return None

class MarketDataValidator:
    """Validator for market data integrity"""
    
    @staticmethod
    def validate_stock_data(stock_data: Dict) -> Dict:
        """Validate and clean stock data dictionary"""
        validated_data = {}
        
        # Required fields
        required_fields = ['symbol', 'price', 'volume']
        for field in required_fields:
            if field not in stock_data:
                logger.error(f"Missing required field: {field}")
                return {}
        
        # Validate symbol
        validated_data['symbol'] = DataProcessor.clean_symbol(stock_data['symbol'])
        if not validated_data['symbol']:
            logger.error("Invalid symbol")
            return {}
        
        # Validate price
        validated_data['price'] = DataProcessor.validate_price_data(stock_data['price'])
        if validated_data['price'] is None:
            logger.error("Invalid price data")
            return {}
        
        # Validate volume
        validated_data['volume'] = DataProcessor.validate_volume_data(stock_data['volume'])
        if validated_data['volume'] is None:
            logger.error("Invalid volume data")
            return {}
        
        # Optional fields with validation
        optional_fields = {
            'open': DataProcessor.validate_price_data,
            'high': DataProcessor.validate_price_data,
            'low': DataProcessor.validate_price_data,
            'previous_close': DataProcessor.validate_price_data,
            'market_cap': lambda x: DataProcessor.validate_volume_data(x),  # Similar to volume
            'timestamp': DataProcessor.normalize_timestamp
        }
        
        for field, validator in optional_fields.items():
            if field in stock_data:
                validated_value = validator(stock_data[field])
                if validated_value is not None:
                    validated_data[field] = validated_value
        
        # Calculate derived fields
        if 'previous_close' in validated_data:
            validated_data['price_change'] = validated_data['price'] - validated_data['previous_close']
            validated_data['change_percent'] = DataProcessor.calculate_percentage_change(
                validated_data['price'], validated_data['previous_close']
            )
        
        # Validate timestamp or set current time
        if 'timestamp' not in validated_data:
            validated_data['timestamp'] = datetime.now()
        
        return validated_data

class PerformanceCalculator:
    """Calculate various performance metrics"""
    
    @staticmethod
    def calculate_volatility(prices: pd.Series, window: int = 20) -> float:
        """Calculate annualized volatility"""
        try:
            if len(prices) < window:
                return 0.0
            
            returns = prices.pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # Annualized
            return round(volatility * 100, 2)  # As percentage
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        try:
            if returns.empty:
                return 0.0
            
            excess_returns = returns.mean() * 252 - risk_free_rate  # Annualized
            volatility = returns.std() * np.sqrt(252)  # Annualized
            
            if volatility == 0:
                return 0.0
            
            return round(excess_returns / volatility, 2)
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_max_drawdown(prices: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if prices.empty:
                return 0.0
            
            cumulative = (1 + prices.pct_change()).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            return round(abs(drawdown.min()) * 100, 2)  # As percentage
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
        """Calculate beta coefficient"""
        try:
            if len(stock_returns) != len(market_returns) or stock_returns.empty:
                return 1.0
            
            # Align the series
            aligned_data = pd.concat([stock_returns, market_returns], axis=1).dropna()
            if len(aligned_data) < 2:
                return 1.0
            
            covariance = aligned_data.iloc[:, 0].cov(aligned_data.iloc[:, 1])
            market_variance = aligned_data.iloc[:, 1].var()
            
            if market_variance == 0:
                return 1.0
            
            return round(covariance / market_variance, 2)
            
        except Exception as e:
            logger.error(f"Error calculating beta: {str(e)}")
            return 1.0

class TextProcessor:
    """Utility functions for text processing"""
    
    @staticmethod
    def extract_tickers_from_text(text: str) -> List[str]:
        """Extract stock tickers from text"""
        if not text:
            return []
        
        # Pattern to match stock tickers ($ followed by 1-5 letters)
        pattern = r'\$([A-Z]{1,5})\b'
        tickers = re.findall(pattern, text.upper())
        
        # Also look for standalone tickers
        words = text.upper().split()
        for word in words:
            # Clean word and check if it looks like a ticker
            cleaned = re.sub(r'[^A-Z]', '', word)
            if 1 <= len(cleaned) <= 5 and cleaned.isalpha():
                tickers.append(cleaned)
        
        # Remove duplicates and return
        return list(set(tickers))
    
    @staticmethod
    def extract_numbers_with_units(text: str) -> List[Dict]:
        """Extract numbers with units (percentages, dollars, etc.)"""
        if not text:
            return []
        
        results = []
        
        # Percentage pattern
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*%'
        percentages = re.findall(percentage_pattern, text)
        for pct in percentages:
            results.append({'value': float(pct), 'unit': 'percent'})
        
        # Dollar amount pattern
        dollar_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(million|billion|M|B|K|thousand)?'
        dollars = re.findall(dollar_pattern, text)
        for amount, unit in dollars:
            amount = float(amount.replace(',', ''))
            if unit.lower() in ['million', 'm']:
                amount *= 1e6
            elif unit.lower() in ['billion', 'b']:
                amount *= 1e9
            elif unit.lower() in ['thousand', 'k']:
                amount *= 1e3
            results.append({'value': amount, 'unit': 'dollars'})
        
        return results
    
    @staticmethod
    def clean_news_text(text: str) -> str:
        """Clean news text for analysis"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-$%]', '', text)
        
        return text.strip()

class CacheManager:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        expiry = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expiry)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
    
    def cleanup_expired(self) -> None:
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [key for key, (_, expiry) in self.cache.items() if now >= expiry]
        for key in expired_keys:
            del self.cache[key]

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    def can_make_call(self) -> bool:
        """Check if we can make an API call"""
        now = time.time()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        return len(self.calls) < self.calls_per_minute
    
    def record_call(self) -> None:
        """Record that an API call was made"""
        self.calls.append(time.time())
    
    def wait_time(self) -> float:
        """Get wait time until next call can be made"""
        if self.can_make_call():
            return 0.0
        
        # Find the oldest call and calculate wait time
        oldest_call = min(self.calls)
        wait_time = 60 - (time.time() - oldest_call)
        return max(0.0, wait_time)

class SecurityUtils:
    """Security and validation utilities"""
    
    @staticmethod
    def sanitize_input(user_input: str, max_length: int = 100) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not user_input:
            return ""
        
        # Limit length
        user_input = user_input[:max_length]
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';(){}]', '', user_input)
        
        # Remove SQL injection patterns
        sql_patterns = [
            r'union\s+select',
            r'drop\s+table',
            r'delete\s+from',
            r'insert\s+into',
            r'update\s+set',
            r'--',
            r'/\*',
            r'\*/',
            r'xp_',
            r'sp_'
        ]
        
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session ID"""
        timestamp = str(time.time())
        random_data = str(np.random.random())
        
        hash_input = (timestamp + random_data).encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()[:16]
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Basic API key validation"""
        if not api_key or len(api_key) < 10:
            return False
        
        # Check for suspicious patterns
        if api_key.lower() in ['demo', 'test', 'example', 'sample']:
            logger.warning("Using demo/test API key")
            return True  # Allow demo keys but warn
        
        return True

# Utility functions for common operations
def format_large_number(number: Union[int, float]) -> str:
    """Format large numbers with appropriate suffixes"""
    try:
        if number is None:
            return "N/A"
        
        number = float(number)
        
        if abs(number) >= 1e12:
            return f"{number/1e12:.1f}T"
        elif abs(number) >= 1e9:
            return f"{number/1e9:.1f}B"
        elif abs(number) >= 1e6:
            return f"{number/1e6:.1f}M"
        elif abs(number) >= 1e3:
            return f"{number/1e3:.1f}K"
        else:
            return f"{number:.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_percentage(value: Union[int, float]) -> str:
    """Format percentage values"""
    try:
        if value is None:
            return "N/A"
        
        value = float(value)
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.2f}%"
    except (ValueError, TypeError):
        return "N/A"

def safe_divide(numerator: Union[int, float], denominator: Union[int, float], default: float = 0.0) -> float:
    """Safely divide two numbers"""
    try:
        if denominator == 0:
            return default
        return float(numerator) / float(denominator)
    except (ValueError, TypeError, ZeroDivisionError):
        return default

def get_market_hours() -> Dict[str, datetime]:
    """Get market open and close times for today"""
    today = datetime.now().date()
    
    # Standard market hours (EST/EDT)
    market_open = datetime.combine(today, datetime.min.time().replace(hour=9, minute=30))
    market_close = datetime.combine(today, datetime.min.time().replace(hour=16, minute=0))
    
    return {
        'open': market_open,
        'close': market_close,
        'is_weekend': today.weekday() >= 5
    }

def is_market_open() -> bool:
    """Check if market is currently open"""
    market_hours = get_market_hours()
    now = datetime.now()
    
    if market_hours['is_weekend']:
        return False
    
    return market_hours['open'] <= now <= market_hours['close']

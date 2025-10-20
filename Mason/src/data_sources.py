import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import json

class StockDataManager:
    """Manages data from multiple sources including Yahoo Finance and Alpha Vantage"""
    
    def __init__(self):
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
        self.last_request_time = {}
        
    def get_real_time_data(self, symbol: str) -> Optional[Dict]:
        """Get real-time stock data from Yahoo Finance"""
        try:
            # Rate limiting
            now = time.time()
            if symbol in self.last_request_time:
                if now - self.last_request_time[symbol] < 1:  # 1 second rate limit
                    time.sleep(1)
            
            self.last_request_time[symbol] = now
            
            ticker = yf.Ticker(symbol)
            
            # Get current price info
            info = ticker.info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return None
                
            current_data = hist.iloc[-1]
            previous_data = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
            
            # Calculate metrics
            current_price = current_data['Close']
            previous_close = previous_data['Close']
            price_change = current_price - previous_close
            change_percent = (price_change / previous_close) * 100
            
            volume = current_data['Volume']
            avg_volume = hist['Volume'].rolling(window=min(20, len(hist))).mean().iloc[-1]
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            
            return {
                'symbol': symbol,
                'price': current_price,
                'previous_close': previous_close,
                'price_change': price_change,
                'change_percent': change_percent,
                'volume': volume,
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'high': current_data['High'],
                'low': current_data['Low'],
                'open': current_data['Open'],
                'timestamp': datetime.now(),
                'market_cap': info.get('marketCap', 0),
                'float_shares': info.get('floatShares', 0)
            }
            
        except Exception as e:
            print(f"Error fetching real-time data for {symbol}: {str(e)}")
            return None
    
    def get_volume_history(self, symbol: str, period: str = "6mo") -> pd.DataFrame:
        """Get volume history for analysis"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            return hist[['Volume']] if not hist.empty else pd.DataFrame()
        except Exception as e:
            print(f"Error fetching volume history for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_historical_data(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        """Get historical stock data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            # Add technical indicators
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['Volume_SMA'] = data['Volume'].rolling(window=20).mean()
            data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']
            data['Price_Change_Pct'] = data['Close'].pct_change() * 100
            
            return data
            
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_intraday_data(self, symbol: str) -> pd.DataFrame:
        """Get intraday data from Alpha Vantage"""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TIME_SERIES_INTRADAY',
                'symbol': symbol,
                'interval': '1min',
                'apikey': self.alpha_vantage_key,
                'outputsize': 'compact'
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'Time Series (1min)' in data:
                time_series = data['Time Series (1min)']
                df = pd.DataFrame.from_dict(time_series, orient='index')
                df.index = pd.to_datetime(df.index)
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df.astype(float)
                df = df.sort_index()
                
                return df
            else:
                print(f"No intraday data available for {symbol}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error fetching intraday data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_company_overview(self, symbol: str) -> Dict:
        """Get company overview from Alpha Vantage"""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            return data
            
        except Exception as e:
            print(f"Error fetching company overview for {symbol}: {str(e)}")
            return {}
    
    def get_top_gainers(self) -> List[Dict]:
        """Get top gaining stocks from Alpha Vantage"""
        try:
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'TOP_GAINERS_LOSERS',
                'apikey': self.alpha_vantage_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'top_gainers' in data:
                gainers = []
                for stock in data['top_gainers'][:20]:  # Top 20 gainers
                    try:
                        change_percent = float(stock.get('change_percentage', '0%').replace('%', ''))
                        if change_percent >= 25:  # Focus on 25%+ gainers
                            gainers.append({
                                'symbol': stock.get('ticker', ''),
                                'price': float(stock.get('price', 0)),
                                'change_amount': float(stock.get('change_amount', 0)),
                                'change_percent': change_percent,
                                'volume': int(stock.get('volume', 0))
                            })
                    except (ValueError, KeyError):
                        continue
                
                return sorted(gainers, key=lambda x: x['change_percent'], reverse=True)
            
            return []
            
        except Exception as e:
            print(f"Error fetching top gainers: {str(e)}")
            return []
    
    def get_market_status(self) -> Dict:
        """Get current market status"""
        try:
            # Use a major index to determine market status
            spy = yf.Ticker("SPY")
            hist = spy.history(period="1d", interval="1m")
            
            if not hist.empty:
                last_update = hist.index[-1]
                now = datetime.now()
                
                # Check if last update was within the last 5 minutes
                time_diff = now - last_update.replace(tzinfo=None)
                is_open = time_diff.total_seconds() < 300  # 5 minutes
                
                return {
                    'is_open': is_open,
                    'last_update': last_update,
                    'status': 'OPEN' if is_open else 'CLOSED'
                }
            
            return {'is_open': False, 'status': 'UNKNOWN'}
            
        except Exception as e:
            print(f"Error checking market status: {str(e)}")
            return {'is_open': False, 'status': 'ERROR'}
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a stock symbol exists"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return 'regularMarketPrice' in info or 'currentPrice' in info
        except:
            return False
    
    def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get quotes for multiple symbols efficiently"""
        results = {}
        
        for symbol in symbols:
            data = self.get_real_time_data(symbol)
            if data:
                results[symbol] = data
                time.sleep(0.1)  # Small delay to avoid rate limits
        
        return results
    
    def get_economic_indicators(self) -> Dict:
        """Get key economic indicators that might affect stock prices"""
        try:
            # Use FRED API for economic data
            fred_key = os.getenv("FRED_API_KEY", "")
            
            if not fred_key:
                return {}
                
            indicators = {
                'DGS10': 'Treasury_10Y',
                'VIXCLS': 'VIX',
                'UNRATE': 'Unemployment_Rate'
            }
            
            results = {}
            
            for series_id, name in indicators.items():
                try:
                    url = f"https://api.stlouisfed.org/fred/series/observations"
                    params = {
                        'series_id': series_id,
                        'api_key': fred_key,
                        'file_type': 'json',
                        'limit': 1,
                        'sort_order': 'desc'
                    }
                    
                    response = requests.get(url, params=params)
                    data = response.json()
                    
                    if 'observations' in data and data['observations']:
                        obs = data['observations'][0]
                        if obs['value'] != '.':
                            results[name] = {
                                'value': float(obs['value']),
                                'date': obs['date']
                            }
                except Exception as e:
                    print(f"Error fetching {name}: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Error fetching economic indicators: {str(e)}")
            return {}

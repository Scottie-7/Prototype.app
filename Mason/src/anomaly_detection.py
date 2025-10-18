import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import scipy.stats as stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class AnomalyDetector:
    """Detects anomalies in stock price and volume data"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        
    def detect_volume_anomalies(self, data: pd.DataFrame, threshold: float = 5.0) -> pd.DataFrame:
        """Detect volume anomalies using statistical methods"""
        try:
            if data.empty or 'Volume' not in data.columns:
                return pd.DataFrame()
            
            # Calculate rolling average volume
            data = data.copy()
            data['Volume_MA'] = data['Volume'].rolling(window=20, min_periods=5).mean()
            data['Volume_Ratio'] = data['Volume'] / data['Volume_MA']
            
            # Detect anomalies where volume is X times above average
            anomalies = data[data['Volume_Ratio'] > threshold].copy()
            
            if not anomalies.empty:
                # Add price change information
                anomalies['Price_Change'] = anomalies['Close'].pct_change() * 100
                
                # Calculate z-scores
                volume_mean = data['Volume'].mean()
                volume_std = data['Volume'].std()
                anomalies['Volume_ZScore'] = (anomalies['Volume'] - volume_mean) / volume_std
                
                # Reset index to get dates as a column
                anomalies = anomalies.reset_index()
                anomalies = anomalies.rename(columns={'Date': 'date'})
                
                # Select relevant columns
                result_columns = ['date', 'Volume', 'Volume_Ratio', 'Price_Change', 'Volume_ZScore', 'Close']
                available_columns = [col for col in result_columns if col in anomalies.columns]
                anomalies = anomalies[available_columns]
                
                # Add additional metrics
                anomalies['volume_ratio'] = anomalies['Volume_Ratio']
                anomalies['price_change'] = anomalies.get('Price_Change', 0)
                
                return anomalies
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error detecting volume anomalies: {str(e)}")
            return pd.DataFrame()
    
    def detect_price_anomalies(self, data: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Detect price anomalies using rolling statistics"""
        try:
            if data.empty or 'Close' not in data.columns:
                return pd.DataFrame()
            
            data = data.copy()
            
            # Calculate price change percentages
            data['Price_Change_Pct'] = data['Close'].pct_change() * 100
            
            # Calculate rolling statistics
            data['Price_Mean'] = data['Price_Change_Pct'].rolling(window=window).mean()
            data['Price_Std'] = data['Price_Change_Pct'].rolling(window=window).std()
            data['Price_ZScore'] = (data['Price_Change_Pct'] - data['Price_Mean']) / data['Price_Std']
            
            # Detect anomalies (Z-score > 2 or < -2)
            anomalies = data[abs(data['Price_ZScore']) > 2].copy()
            
            if not anomalies.empty:
                anomalies = anomalies.reset_index()
                anomalies = anomalies.rename(columns={'Date': 'date'})
                
                return anomalies[['date', 'Close', 'Price_Change_Pct', 'Price_ZScore', 'Volume']]
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error detecting price anomalies: {str(e)}")
            return pd.DataFrame()
    
    def detect_gap_anomalies(self, data: pd.DataFrame, min_gap_percent: float = 10.0) -> List[Dict]:
        """Detect significant price gaps"""
        try:
            if data.empty or len(data) < 2:
                return []
            
            gaps = []
            
            for i in range(1, len(data)):
                prev_close = data.iloc[i-1]['Close']
                current_open = data.iloc[i]['Open']
                
                gap_percent = ((current_open - prev_close) / prev_close) * 100
                
                if abs(gap_percent) >= min_gap_percent:
                    gaps.append({
                        'date': data.index[i],
                        'gap_percent': gap_percent,
                        'prev_close': prev_close,
                        'current_open': current_open,
                        'gap_type': 'Gap Up' if gap_percent > 0 else 'Gap Down',
                        'volume': data.iloc[i]['Volume']
                    })
            
            return gaps
            
        except Exception as e:
            print(f"Error detecting gap anomalies: {str(e)}")
            return []
    
    def detect_intraday_anomalies(self, data: pd.DataFrame) -> List[Dict]:
        """Detect intraday price/volume anomalies"""
        try:
            if data.empty:
                return []
            
            anomalies = []
            
            # High-Low range analysis
            data = data.copy()
            data['Range_Pct'] = ((data['High'] - data['Low']) / data['Close']) * 100
            range_mean = data['Range_Pct'].mean()
            range_std = data['Range_Pct'].std()
            
            # Detect days with unusually high intraday volatility
            high_volatility = data[data['Range_Pct'] > range_mean + 2 * range_std]
            
            for idx, row in high_volatility.iterrows():
                anomalies.append({
                    'date': idx,
                    'type': 'High Intraday Volatility',
                    'range_percent': row['Range_Pct'],
                    'volume': row['Volume'],
                    'close': row['Close']
                })
            
            # Volume-Price correlation anomalies
            if len(data) > 20:
                data['Price_Change'] = data['Close'].pct_change()
                correlation = data['Volume'].corr(abs(data['Price_Change']))
                
                if correlation < 0.2:  # Low correlation might indicate manipulation
                    anomalies.append({
                        'date': data.index[-1],
                        'type': 'Low Volume-Price Correlation',
                        'correlation': correlation,
                        'significance': 'Potential manipulation or unusual trading pattern'
                    })
            
            return anomalies
            
        except Exception as e:
            print(f"Error detecting intraday anomalies: {str(e)}")
            return []
    
    def detect_patterns(self, data: pd.DataFrame) -> List[str]:
        """Detect trading patterns that might indicate opportunities or risks"""
        try:
            if data.empty or len(data) < 20:
                return []
            
            patterns = []
            
            # Calculate technical indicators
            data = data.copy()
            data['SMA_20'] = data['Close'].rolling(window=20).mean()
            data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
            data['Price_Change'] = data['Close'].pct_change()
            
            # Pattern 1: Breakout with volume
            latest = data.iloc[-1]
            recent = data.iloc[-5:]  # Last 5 days
            
            if latest['Close'] > latest['SMA_20'] and latest['Volume'] > latest['Volume_MA'] * 2:
                patterns.append("Bullish breakout with high volume confirmed")
            
            # Pattern 2: Consecutive volume spikes
            volume_spikes = sum(1 for i in range(-5, 0) if data.iloc[i]['Volume'] > data.iloc[i-1]['Volume'] * 1.5)
            if volume_spikes >= 3:
                patterns.append("Consistent volume increase pattern detected")
            
            # Pattern 3: Price consolidation
            recent_high = recent['High'].max()
            recent_low = recent['Low'].min()
            consolidation_range = (recent_high - recent_low) / recent['Close'].mean()
            
            if consolidation_range < 0.05:  # Less than 5% range
                patterns.append("Price consolidation pattern - potential breakout setup")
            
            # Pattern 4: Divergence detection
            if len(data) > 10:
                price_trend = data['Close'].iloc[-10:].corr(pd.Series(range(10)))
                volume_trend = data['Volume'].iloc[-10:].corr(pd.Series(range(10)))
                
                if price_trend > 0.5 and volume_trend < -0.5:
                    patterns.append("Bearish divergence - price rising but volume declining")
                elif price_trend < -0.5 and volume_trend > 0.5:
                    patterns.append("Volume accumulation during price decline - potential reversal")
            
            # Pattern 5: Unusual after-hours activity (if intraday data available)
            if 'timestamp' in data.columns:
                # This would require intraday timestamp data
                patterns.append("Pattern detection requires intraday timestamp data for after-hours analysis")
            
            return patterns
            
        except Exception as e:
            print(f"Error detecting patterns: {str(e)}")
            return []
    
    def analyze_short_squeeze_potential(self, symbol_data: Dict, order_book_data: Dict = None) -> Dict:
        """Analyze potential for short squeeze based on available data"""
        try:
            analysis = {
                'squeeze_probability': 0,
                'risk_factors': [],
                'bullish_indicators': [],
                'metrics': {}
            }
            
            if not symbol_data:
                return analysis
            
            # Factor 1: High volume relative to float
            volume = symbol_data.get('volume', 0)
            float_shares = symbol_data.get('float_shares', 0)
            
            if float_shares > 0:
                volume_to_float = volume / float_shares
                analysis['metrics']['volume_to_float_ratio'] = volume_to_float
                
                if volume_to_float > 0.1:  # 10% of float traded
                    analysis['bullish_indicators'].append(f"High volume: {volume_to_float:.1%} of float traded")
                    analysis['squeeze_probability'] += 20
            
            # Factor 2: Price momentum
            price_change = symbol_data.get('change_percent', 0)
            if price_change > 25:
                analysis['bullish_indicators'].append(f"Strong upward momentum: +{price_change:.1f}%")
                analysis['squeeze_probability'] += 30
            elif price_change > 10:
                analysis['bullish_indicators'].append(f"Positive momentum: +{price_change:.1f}%")
                analysis['squeeze_probability'] += 15
            
            # Factor 3: Small float (if available)
            market_cap = symbol_data.get('market_cap', 0)
            if market_cap > 0 and market_cap < 1e9:  # Less than $1B market cap
                analysis['bullish_indicators'].append("Small cap stock with potential for high volatility")
                analysis['squeeze_probability'] += 15
            
            # Factor 4: Order book pressure (if available)
            if order_book_data:
                bid_pressure = order_book_data.get('bid_pressure', 50)
                if bid_pressure > 70:
                    analysis['bullish_indicators'].append(f"Strong buying pressure: {bid_pressure:.1f}%")
                    analysis['squeeze_probability'] += 20
            
            # Factor 5: Volume anomaly
            volume_ratio = symbol_data.get('volume_ratio', 1)
            if volume_ratio > 5:
                analysis['bullish_indicators'].append(f"Volume spike: {volume_ratio:.1f}x normal volume")
                analysis['squeeze_probability'] += 25
            
            # Risk factors
            if price_change > 100:
                analysis['risk_factors'].append("Extreme price increase - high volatility risk")
            
            if volume_ratio > 20:
                analysis['risk_factors'].append("Extreme volume - potential pump and dump risk")
            
            # Cap probability at 100
            analysis['squeeze_probability'] = min(analysis['squeeze_probability'], 100)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing short squeeze potential: {str(e)}")
            return {'squeeze_probability': 0, 'risk_factors': [], 'bullish_indicators': [], 'metrics': {}}
    
    def detect_unusual_options_activity(self, symbol: str) -> List[Dict]:
        """Detect unusual options activity (placeholder for future implementation)"""
        # This would require options data from a provider like CBOE or paid API
        # For now, return empty list as options data is not available in free APIs
        return []
    
    def calculate_volatility_metrics(self, data: pd.DataFrame) -> Dict:
        """Calculate various volatility metrics"""
        try:
            if data.empty or 'Close' not in data.columns:
                return {}
            
            # Calculate returns
            returns = data['Close'].pct_change().dropna()
            
            if len(returns) < 2:
                return {}
            
            # Calculate metrics
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            avg_return = returns.mean() * 252  # Annualized return
            
            # Risk metrics
            downside_returns = returns[returns < 0]
            downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            
            # Maximum drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()
            
            return {
                'volatility': volatility,
                'annual_return': avg_return,
                'sharpe_ratio': avg_return / volatility if volatility > 0 else 0,
                'downside_volatility': downside_volatility,
                'max_drawdown': abs(max_drawdown),
                'current_drawdown': abs(drawdown.iloc[-1]) if len(drawdown) > 0 else 0
            }
            
        except Exception as e:
            print(f"Error calculating volatility metrics: {str(e)}")
            return {}

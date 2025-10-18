import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import Dict, List, Optional, Tuple
import json

class OrderBookAnalyzer:
    """Analyzes Level 2 order book data and detects market manipulation"""
    
    def __init__(self):
        self.polygon_key = os.getenv("POLYGON_API_KEY", "")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
        self.last_request_time = {}
        
    def get_order_book_data(self, symbol: str) -> Optional[Dict]:
        """Get Level 2 order book data"""
        try:
            # Try Polygon.io first (if API key available)
            if self.polygon_key:
                return self._get_polygon_order_book(symbol)
            else:
                # Fallback to simulated order book from price action
                return self._simulate_order_book(symbol)
                
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {str(e)}")
            return None
    
    def _get_polygon_order_book(self, symbol: str) -> Optional[Dict]:
        """Get real Level 2 data from Polygon.io"""
        try:
            url = f"https://api.polygon.io/v3/quotes/{symbol}"
            params = {
                'apikey': self.polygon_key,
                'limit': 50
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'results' in data and data['results']:
                    quotes = data['results']
                    
                    # Process into order book format
                    bids = []
                    asks = []
                    
                    for quote in quotes:
                        if 'bid' in quote and 'bid_size' in quote:
                            bids.append({
                                'price': quote['bid'],
                                'size': quote['bid_size'],
                                'timestamp': quote.get('participant_timestamp', int(time.time() * 1000))
                            })
                        
                        if 'ask' in quote and 'ask_size' in quote:
                            asks.append({
                                'price': quote['ask'],
                                'size': quote['ask_size'],
                                'timestamp': quote.get('participant_timestamp', int(time.time() * 1000))
                            })
                    
                    return {
                        'symbol': symbol,
                        'bids': sorted(bids, key=lambda x: x['price'], reverse=True),
                        'asks': sorted(asks, key=lambda x: x['price']),
                        'timestamp': datetime.now()
                    }
            
            return None
            
        except Exception as e:
            print(f"Error fetching Polygon order book: {str(e)}")
            return None
    
    def _simulate_order_book(self, symbol: str) -> Optional[Dict]:
        """Create simulated order book based on current market data"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                return None
                
            current_price = hist['Close'].iloc[-1]
            volume = hist['Volume'].iloc[-1]
            volatility = hist['Close'].pct_change().std()
            
            # Generate realistic order book levels
            spread_pct = max(0.001, volatility * 0.1)  # Minimum 0.1% spread
            spread = current_price * spread_pct
            
            bids = []
            asks = []
            
            # Generate 20 levels each side
            for i in range(20):
                # Bid side (below current price)
                bid_price = current_price - spread/2 - (i * spread * 0.1)
                bid_size = max(100, int(volume * np.random.exponential(0.01)))
                
                bids.append({
                    'price': round(bid_price, 2),
                    'size': bid_size,
                    'timestamp': int(time.time() * 1000)
                })
                
                # Ask side (above current price)
                ask_price = current_price + spread/2 + (i * spread * 0.1)
                ask_size = max(100, int(volume * np.random.exponential(0.01)))
                
                asks.append({
                    'price': round(ask_price, 2),
                    'size': ask_size,
                    'timestamp': int(time.time() * 1000)
                })
            
            return {
                'symbol': symbol,
                'bids': bids,
                'asks': asks,
                'timestamp': datetime.now(),
                'simulated': True
            }
            
        except Exception as e:
            print(f"Error simulating order book: {str(e)}")
            return None
    
    def calculate_bid_pressure(self, order_book: Dict) -> float:
        """Calculate buying pressure from order book"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Calculate total bid volume vs total ask volume
            total_bid_volume = sum(bid['size'] for bid in bids[:10])  # Top 10 levels
            total_ask_volume = sum(ask['size'] for ask in asks[:10])  # Top 10 levels
            
            total_volume = total_bid_volume + total_ask_volume
            
            if total_volume == 0:
                return 50.0
            
            bid_pressure = (total_bid_volume / total_volume) * 100
            return bid_pressure
            
        except Exception as e:
            print(f"Error calculating bid pressure: {str(e)}")
            return 0.0
    
    def calculate_ask_pressure(self, order_book: Dict) -> float:
        """Calculate selling pressure from order book"""
        return 100.0 - self.calculate_bid_pressure(order_book)
    
    def calculate_spread(self, order_book: Dict) -> float:
        """Calculate bid-ask spread"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            best_bid = max(bids, key=lambda x: x['price'])['price']
            best_ask = min(asks, key=lambda x: x['price'])['price']
            
            return best_ask - best_bid
            
        except Exception as e:
            print(f"Error calculating spread: {str(e)}")
            return 0.0
    
    def calculate_order_imbalance(self, order_book: Dict) -> float:
        """Calculate order imbalance ratio"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Weight by distance from mid-price
            if not bids or not asks:
                return 0.0
                
            best_bid = max(bids, key=lambda x: x['price'])['price']
            best_ask = min(asks, key=lambda x: x['price'])['price']
            mid_price = (best_bid + best_ask) / 2
            
            weighted_bid_volume = 0
            weighted_ask_volume = 0
            
            for bid in bids[:10]:
                distance = abs(bid['price'] - mid_price) / mid_price
                weight = 1 / (1 + distance * 10)  # Closer orders get higher weight
                weighted_bid_volume += bid['size'] * weight
            
            for ask in asks[:10]:
                distance = abs(ask['price'] - mid_price) / mid_price
                weight = 1 / (1 + distance * 10)
                weighted_ask_volume += ask['size'] * weight
            
            total_weighted = weighted_bid_volume + weighted_ask_volume
            
            if total_weighted == 0:
                return 0.0
            
            imbalance = (weighted_bid_volume - weighted_ask_volume) / total_weighted
            return imbalance * 100  # Convert to percentage
            
        except Exception as e:
            print(f"Error calculating order imbalance: {str(e)}")
            return 0.0
    
    def detect_spoofing(self, order_book: Dict) -> List[str]:
        """Detect potential spoofing patterns in order book"""
        alerts = []
        
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return alerts
            
            # Check for unusually large orders at best bid/ask
            best_bid = max(bids, key=lambda x: x['price'])
            best_ask = min(asks, key=lambda x: x['price'])
            
            # Calculate average order sizes
            avg_bid_size = np.mean([bid['size'] for bid in bids])
            avg_ask_size = np.mean([ask['size'] for ask in asks])
            
            # Alert if best bid/ask is significantly larger than average
            if best_bid['size'] > avg_bid_size * 5:
                alerts.append(f"Large bid order detected: {best_bid['size']:,} shares at ${best_bid['price']}")
            
            if best_ask['size'] > avg_ask_size * 5:
                alerts.append(f"Large ask order detected: {best_ask['size']:,} shares at ${best_ask['price']}")
            
            # Check for order clustering (multiple large orders at same price)
            bid_prices = {}
            ask_prices = {}
            
            for bid in bids:
                price = bid['price']
                if price not in bid_prices:
                    bid_prices[price] = []
                bid_prices[price].append(bid['size'])
            
            for ask in asks:
                price = ask['price']
                if price not in ask_prices:
                    ask_prices[price] = []
                ask_prices[price].append(ask['size'])
            
            # Alert if multiple large orders at same price level
            for price, sizes in bid_prices.items():
                if len(sizes) > 3 and sum(sizes) > avg_bid_size * 10:
                    alerts.append(f"Bid clustering detected: {len(sizes)} orders totaling {sum(sizes):,} shares at ${price}")
            
            for price, sizes in ask_prices.items():
                if len(sizes) > 3 and sum(sizes) > avg_ask_size * 10:
                    alerts.append(f"Ask clustering detected: {len(sizes)} orders totaling {sum(sizes):,} shares at ${price}")
            
            # Check for wide spread manipulation
            spread = self.calculate_spread(order_book)
            mid_price = (best_bid['price'] + best_ask['price']) / 2
            spread_pct = (spread / mid_price) * 100
            
            if spread_pct > 0.5:  # Alert if spread > 0.5%
                alerts.append(f"Wide spread detected: {spread_pct:.2f}% (${spread:.4f})")
            
        except Exception as e:
            print(f"Error detecting spoofing: {str(e)}")
        
        return alerts
    
    def analyze_order_flow(self, order_book_history: List[Dict]) -> Dict:
        """Analyze order flow patterns over time"""
        try:
            if len(order_book_history) < 2:
                return {}
            
            # Track order additions, cancellations, and modifications
            flow_analysis = {
                'bid_additions': 0,
                'ask_additions': 0,
                'bid_cancellations': 0,
                'ask_cancellations': 0,
                'price_improvements': 0,
                'aggressive_orders': 0
            }
            
            for i in range(1, len(order_book_history)):
                current_book = order_book_history[i]
                previous_book = order_book_history[i-1]
                
                # Compare bid sides
                current_bids = {bid['price']: bid['size'] for bid in current_book.get('bids', [])}
                previous_bids = {bid['price']: bid['size'] for bid in previous_book.get('bids', [])}
                
                # Count new bids
                for price in current_bids:
                    if price not in previous_bids:
                        flow_analysis['bid_additions'] += 1
                
                # Count cancelled bids
                for price in previous_bids:
                    if price not in current_bids:
                        flow_analysis['bid_cancellations'] += 1
                
                # Similar analysis for asks
                current_asks = {ask['price']: ask['size'] for ask in current_book.get('asks', [])}
                previous_asks = {ask['price']: ask['size'] for ask in previous_book.get('asks', [])}
                
                for price in current_asks:
                    if price not in previous_asks:
                        flow_analysis['ask_additions'] += 1
                
                for price in previous_asks:
                    if price not in current_asks:
                        flow_analysis['ask_cancellations'] += 1
            
            return flow_analysis
            
        except Exception as e:
            print(f"Error analyzing order flow: {str(e)}")
            return {}
    
    def calculate_market_depth(self, order_book: Dict, depth_levels: int = 10) -> Dict:
        """Calculate market depth metrics"""
        try:
            bids = order_book.get('bids', [])[:depth_levels]
            asks = order_book.get('asks', [])[:depth_levels]
            
            if not bids or not asks:
                return {}
            
            # Calculate cumulative volume at each level
            cumulative_bid_volume = 0
            cumulative_ask_volume = 0
            
            bid_levels = []
            ask_levels = []
            
            for bid in bids:
                cumulative_bid_volume += bid['size']
                bid_levels.append({
                    'price': bid['price'],
                    'size': bid['size'],
                    'cumulative': cumulative_bid_volume
                })
            
            for ask in asks:
                cumulative_ask_volume += ask['size']
                ask_levels.append({
                    'price': ask['price'],
                    'size': ask['size'],
                    'cumulative': cumulative_ask_volume
                })
            
            return {
                'bid_depth': bid_levels,
                'ask_depth': ask_levels,
                'total_bid_volume': cumulative_bid_volume,
                'total_ask_volume': cumulative_ask_volume,
                'depth_ratio': cumulative_bid_volume / cumulative_ask_volume if cumulative_ask_volume > 0 else 0
            }
            
        except Exception as e:
            print(f"Error calculating market depth: {str(e)}")
            return {}

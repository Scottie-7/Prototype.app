import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math

class ChartGenerator:
    """Generates interactive charts and visualizations for stock data"""
    
    def __init__(self):
        # Define color schemes for different chart types
        self.colors = {
            'bullish': '#00ff88',
            'bearish': '#ff4444',
            'neutral': '#888888',
            'volume': '#1f77b4',
            'background': '#0e1117',
            'grid': '#262730',
            'text': '#ffffff'
        }
        
        # Default layout settings
        self.default_layout = {
            'plot_bgcolor': self.colors['background'],
            'paper_bgcolor': self.colors['background'],
            'font': {'color': self.colors['text']},
            'xaxis': {
                'gridcolor': self.colors['grid'],
                'zerolinecolor': self.colors['grid']
            },
            'yaxis': {
                'gridcolor': self.colors['grid'],
                'zerolinecolor': self.colors['grid']
            }
        }
    
    def create_candlestick_chart(self, data: pd.DataFrame, symbol: str) -> go.Figure:
        """Create candlestick chart with volume"""
        try:
            if data.empty:
                return self._create_empty_chart("No data available for candlestick chart")
            
            # Create subplots: price chart and volume chart
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{symbol} Price Chart', 'Volume'),
                row_heights=[0.7, 0.3]
            )
            
            # Candlestick chart
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name=symbol,
                    increasing_line_color=self.colors['bullish'],
                    decreasing_line_color=self.colors['bearish']
                ),
                row=1, col=1
            )
            
            # Add moving averages if available
            if 'SMA_20' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['SMA_20'],
                        mode='lines',
                        name='SMA 20',
                        line=dict(color='orange', width=1)
                    ),
                    row=1, col=1
                )
            
            if 'SMA_50' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['SMA_50'],
                        mode='lines',
                        name='SMA 50',
                        line=dict(color='purple', width=1)
                    ),
                    row=1, col=1
                )
            
            # Volume chart
            colors = [self.colors['bullish'] if close >= open_price else self.colors['bearish'] 
                     for close, open_price in zip(data['Close'], data['Open'])]
            
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['Volume'],
                    name='Volume',
                    marker_color=colors,
                    showlegend=False
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Candlestick Chart with Volume',
                **self.default_layout,
                height=600,
                xaxis_rangeslider_visible=False
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating candlestick chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_line_chart(self, data: pd.DataFrame, symbol: str) -> go.Figure:
        """Create simple line chart"""
        try:
            if data.empty:
                return self._create_empty_chart("No data available for line chart")
            
            fig = go.Figure()
            
            # Price line
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    mode='lines',
                    name=f'{symbol} Price',
                    line=dict(color=self.colors['bullish'], width=2)
                )
            )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Price Chart',
                **self.default_layout,
                height=400,
                xaxis_title='Date',
                yaxis_title='Price ($)'
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating line chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_volume_chart(self, data: pd.DataFrame, symbol: str) -> go.Figure:
        """Create volume analysis chart"""
        try:
            if data.empty:
                return self._create_empty_chart("No data available for volume chart")
            
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=(f'{symbol} Volume', 'Volume Ratio'),
                row_heights=[0.6, 0.4]
            )
            
            # Volume bars
            colors = [self.colors['bullish'] if vol > avg_vol else self.colors['neutral'] 
                     for vol, avg_vol in zip(data['Volume'], data.get('Volume_SMA', data['Volume']))]
            
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['Volume'],
                    name='Volume',
                    marker_color=colors
                ),
                row=1, col=1
            )
            
            # Average volume line
            if 'Volume_SMA' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['Volume_SMA'],
                        mode='lines',
                        name='Avg Volume',
                        line=dict(color='yellow', width=2)
                    ),
                    row=1, col=1
                )
            
            # Volume ratio
            if 'Volume_Ratio' in data.columns:
                ratio_colors = [self.colors['bearish'] if ratio > 5 else self.colors['bullish'] if ratio > 2 else self.colors['neutral']
                               for ratio in data['Volume_Ratio']]
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['Volume_Ratio'],
                        mode='markers+lines',
                        name='Volume Ratio',
                        line=dict(color=self.colors['volume']),
                        marker=dict(color=ratio_colors, size=6)
                    ),
                    row=2, col=1
                )
                
                # Add threshold lines
                fig.add_hline(y=5, line_dash="dash", line_color=self.colors['bearish'], 
                             annotation_text="5x Threshold", row=2, col=1)
                fig.add_hline(y=2, line_dash="dash", line_color=self.colors['bullish'], 
                             annotation_text="2x Threshold", row=2, col=1)
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Volume Analysis',
                **self.default_layout,
                height=500
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating volume chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_technical_chart(self, data: pd.DataFrame, symbol: str) -> go.Figure:
        """Create technical analysis chart with indicators"""
        try:
            if data.empty:
                return self._create_empty_chart("No data available for technical chart")
            
            # Create subplots
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{symbol} Price & Moving Averages', 'RSI', 'MACD'),
                row_heights=[0.6, 0.2, 0.2]
            )
            
            # Price and moving averages
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    mode='lines',
                    name='Close Price',
                    line=dict(color=self.colors['bullish'], width=2)
                ),
                row=1, col=1
            )
            
            # Moving averages
            if 'SMA_20' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['SMA_20'],
                        mode='lines',
                        name='SMA 20',
                        line=dict(color='orange', width=1)
                    ),
                    row=1, col=1
                )
            
            if 'SMA_50' in data.columns:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=data['SMA_50'],
                        mode='lines',
                        name='SMA 50',
                        line=dict(color='purple', width=1)
                    ),
                    row=1, col=1
                )
            
            # Calculate and add RSI
            rsi = self._calculate_rsi(data['Close'])
            if not rsi.empty:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=rsi,
                        mode='lines',
                        name='RSI',
                        line=dict(color=self.colors['volume'])
                    ),
                    row=2, col=1
                )
                
                # RSI levels
                fig.add_hline(y=70, line_dash="dash", line_color=self.colors['bearish'], 
                             annotation_text="Overbought", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color=self.colors['bullish'], 
                             annotation_text="Oversold", row=2, col=1)
            
            # Calculate and add MACD
            macd_line, signal_line, histogram = self._calculate_macd(data['Close'])
            if not macd_line.empty:
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=macd_line,
                        mode='lines',
                        name='MACD',
                        line=dict(color=self.colors['bullish'])
                    ),
                    row=3, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index,
                        y=signal_line,
                        mode='lines',
                        name='Signal',
                        line=dict(color=self.colors['bearish'])
                    ),
                    row=3, col=1
                )
                
                # MACD histogram
                histogram_colors = [self.colors['bullish'] if h > 0 else self.colors['bearish'] for h in histogram]
                fig.add_trace(
                    go.Bar(
                        x=data.index,
                        y=histogram,
                        name='Histogram',
                        marker_color=histogram_colors,
                        showlegend=False
                    ),
                    row=3, col=1
                )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Technical Analysis',
                **self.default_layout,
                height=700
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating technical chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_order_book_chart(self, order_book: Dict) -> go.Figure:
        """Create order book visualization"""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return self._create_empty_chart("No order book data available")
            
            fig = go.Figure()
            
            # Prepare bid data
            bid_prices = [bid['price'] for bid in bids[:20]]  # Top 20 levels
            bid_sizes = [bid['size'] for bid in bids[:20]]
            bid_cumulative = np.cumsum(bid_sizes)
            
            # Prepare ask data
            ask_prices = [ask['price'] for ask in asks[:20]]  # Top 20 levels
            ask_sizes = [ask['size'] for ask in asks[:20]]
            ask_cumulative = np.cumsum(ask_sizes)
            
            # Bid side (green)
            fig.add_trace(
                go.Scatter(
                    x=bid_prices,
                    y=bid_cumulative,
                    mode='lines+markers',
                    name='Bids (Cumulative)',
                    line=dict(color=self.colors['bullish'], width=3),
                    fill='tonexty',
                    fillcolor='rgba(0, 255, 136, 0.1)'
                )
            )
            
            # Ask side (red)
            fig.add_trace(
                go.Scatter(
                    x=ask_prices,
                    y=ask_cumulative,
                    mode='lines+markers',
                    name='Asks (Cumulative)',
                    line=dict(color=self.colors['bearish'], width=3),
                    fill='tonexty',
                    fillcolor='rgba(255, 68, 68, 0.1)'
                )
            )
            
            # Add individual order levels as bars
            fig.add_trace(
                go.Bar(
                    x=bid_prices,
                    y=bid_sizes,
                    name='Bid Levels',
                    marker_color=self.colors['bullish'],
                    opacity=0.6,
                    yaxis='y2'
                )
            )
            
            fig.add_trace(
                go.Bar(
                    x=ask_prices,
                    y=ask_sizes,
                    name='Ask Levels',
                    marker_color=self.colors['bearish'],
                    opacity=0.6,
                    yaxis='y2'
                )
            )
            
            # Mark best bid and ask
            if bids and asks:
                best_bid = max(bids, key=lambda x: x['price'])['price']
                best_ask = min(asks, key=lambda x: x['price'])['price']
                
                fig.add_vline(x=best_bid, line_dash="dash", line_color=self.colors['bullish'], 
                             annotation_text=f"Best Bid: ${best_bid:.2f}")
                fig.add_vline(x=best_ask, line_dash="dash", line_color=self.colors['bearish'], 
                             annotation_text=f"Best Ask: ${best_ask:.2f}")
            
            # Update layout with dual y-axis
            fig.update_layout(
                title=f"{order_book.get('symbol', 'Unknown')} - Order Book Depth",
                **self.default_layout,
                height=500,
                xaxis_title='Price ($)',
                yaxis=dict(title='Cumulative Size', side='left'),
                yaxis2=dict(title='Order Size', side='right', overlaying='y'),
                legend=dict(x=0, y=1)
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating order book chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_anomaly_chart(self, data: pd.DataFrame, anomalies: pd.DataFrame) -> go.Figure:
        """Create chart highlighting anomalies"""
        try:
            if data.empty:
                return self._create_empty_chart("No data available for anomaly chart")
            
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=('Price with Anomalies', 'Volume with Anomalies'),
                row_heights=[0.6, 0.4]
            )
            
            # Price chart
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Close'],
                    mode='lines',
                    name='Price',
                    line=dict(color=self.colors['bullish'])
                ),
                row=1, col=1
            )
            
            # Volume chart
            fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['Volume'],
                    name='Volume',
                    marker_color=self.colors['volume'],
                    opacity=0.6
                ),
                row=2, col=1
            )
            
            # Highlight anomalies
            if not anomalies.empty:
                for _, anomaly in anomalies.iterrows():
                    anomaly_date = anomaly['date']
                    
                    # Find corresponding data point
                    if anomaly_date in data.index:
                        price = data.loc[anomaly_date, 'Close']
                        volume = data.loc[anomaly_date, 'Volume']
                        
                        # Add anomaly markers
                        fig.add_trace(
                            go.Scatter(
                                x=[anomaly_date],
                                y=[price],
                                mode='markers',
                                name=f'Price Anomaly',
                                marker=dict(
                                    color=self.colors['bearish'],
                                    size=15,
                                    symbol='triangle-up'
                                ),
                                showlegend=False
                            ),
                            row=1, col=1
                        )
                        
                        fig.add_trace(
                            go.Scatter(
                                x=[anomaly_date],
                                y=[volume],
                                mode='markers',
                                name=f'Volume Anomaly',
                                marker=dict(
                                    color=self.colors['bearish'],
                                    size=15,
                                    symbol='triangle-up'
                                ),
                                showlegend=False
                            ),
                            row=2, col=1
                        )
            
            # Update layout
            fig.update_layout(
                title='Stock Anomaly Detection',
                **self.default_layout,
                height=500
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating anomaly chart: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_correlation_heatmap(self, correlation_matrix: pd.DataFrame) -> go.Figure:
        """Create correlation heatmap for multiple stocks"""
        try:
            if correlation_matrix.empty:
                return self._create_empty_chart("No correlation data available")
            
            fig = go.Figure(data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale='RdBu',
                zmid=0,
                text=correlation_matrix.values,
                texttemplate='%{text:.2f}',
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title='Stock Correlation Matrix',
                **self.default_layout,
                height=500
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating correlation heatmap: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def create_performance_comparison(self, performance_data: Dict) -> go.Figure:
        """Create performance comparison chart"""
        try:
            if not performance_data:
                return self._create_empty_chart("No performance data available")
            
            symbols = list(performance_data.keys())
            returns = [performance_data[symbol].get('return', 0) for symbol in symbols]
            volatilities = [performance_data[symbol].get('volatility', 0) for symbol in symbols]
            
            fig = go.Figure()
            
            # Scatter plot of return vs volatility
            fig.add_trace(
                go.Scatter(
                    x=volatilities,
                    y=returns,
                    mode='markers+text',
                    text=symbols,
                    textposition='top center',
                    marker=dict(
                        size=12,
                        color=returns,
                        colorscale='RdYlGn',
                        colorbar=dict(title='Returns (%)')
                    ),
                    name='Stocks'
                )
            )
            
            fig.update_layout(
                title='Risk vs Return Analysis',
                **self.default_layout,
                height=500,
                xaxis_title='Volatility (%)',
                yaxis_title='Returns (%)'
            )
            
            return fig
            
        except Exception as e:
            print(f"Error creating performance comparison: {str(e)}")
            return self._create_empty_chart(f"Error creating chart: {str(e)}")
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            print(f"Error calculating RSI: {str(e)}")
            return pd.Series()
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            print(f"Error calculating MACD: {str(e)}")
            return pd.Series(), pd.Series(), pd.Series()
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message"""
        fig = go.Figure()
        
        fig.add_annotation(
            x=0.5,
            y=0.5,
            xref='paper',
            yref='paper',
            text=message,
            showarrow=False,
            font=dict(size=16, color=self.colors['text'])
        )
        
        fig.update_layout(
            **self.default_layout,
            height=400,
            showlegend=False
        )
        
        return fig

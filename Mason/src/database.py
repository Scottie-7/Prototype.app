import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os

class DatabaseManager:
    """Manages SQLite database for storing stock data, alerts, and historical patterns"""
    
    def __init__(self, db_path: str = "stock_monitor.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Stock data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        price REAL,
                        volume INTEGER,
                        price_change REAL,
                        change_percent REAL,
                        volume_ratio REAL,
                        high REAL,
                        low REAL,
                        open REAL,
                        market_cap INTEGER,
                        float_shares INTEGER
                    )
                ''')
                
                # Order book data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS order_book_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        bid_data TEXT,  -- JSON string of bid levels
                        ask_data TEXT,  -- JSON string of ask levels
                        spread REAL,
                        bid_pressure REAL,
                        ask_pressure REAL,
                        order_imbalance REAL
                    )
                ''')
                
                # Alerts table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        price REAL,
                        volume INTEGER,
                        trigger_value REAL,
                        status TEXT DEFAULT 'active'
                    )
                ''')
                
                # News data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS news_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT,
                        title TEXT NOT NULL,
                        summary TEXT,
                        url TEXT,
                        source TEXT,
                        timestamp DATETIME NOT NULL,
                        impact_score REAL,
                        relevance_score REAL,
                        sentiment REAL
                    )
                ''')
                
                # Anomalies table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS anomalies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        anomaly_type TEXT NOT NULL,
                        description TEXT,
                        timestamp DATETIME NOT NULL,
                        severity INTEGER,  -- 1-10 scale
                        price REAL,
                        volume INTEGER,
                        metadata TEXT  -- JSON string for additional data
                    )
                ''')
                
                # Trading patterns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trading_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        pattern_type TEXT NOT NULL,
                        pattern_data TEXT,  -- JSON string
                        start_date DATETIME,
                        end_date DATETIME,
                        confidence_score REAL,
                        outcome TEXT  -- For tracking pattern success
                    )
                ''')
                
                # Watchlist table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE NOT NULL,
                        added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        priority INTEGER DEFAULT 1,
                        notes TEXT
                    )
                ''')
                
                # System metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        metric_name TEXT NOT NULL,
                        metric_value REAL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                ''')
                
                conn.commit()
                print("Database initialized successfully")
                
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
    
    def store_stock_data(self, stock_data: Dict) -> bool:
        """Store real-time stock data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO stock_data (
                        symbol, timestamp, price, volume, price_change, change_percent,
                        volume_ratio, high, low, open, market_cap, float_shares
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    stock_data.get('symbol'),
                    stock_data.get('timestamp', datetime.now()),
                    stock_data.get('price'),
                    stock_data.get('volume'),
                    stock_data.get('price_change'),
                    stock_data.get('change_percent'),
                    stock_data.get('volume_ratio'),
                    stock_data.get('high'),
                    stock_data.get('low'),
                    stock_data.get('open'),
                    stock_data.get('market_cap'),
                    stock_data.get('float_shares')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error storing stock data: {str(e)}")
            return False
    
    def store_order_book_data(self, symbol: str, order_book: Dict) -> bool:
        """Store order book data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO order_book_data (
                        symbol, timestamp, bid_data, ask_data, spread,
                        bid_pressure, ask_pressure, order_imbalance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    order_book.get('timestamp', datetime.now()),
                    json.dumps(order_book.get('bids', [])),
                    json.dumps(order_book.get('asks', [])),
                    order_book.get('spread'),
                    order_book.get('bid_pressure'),
                    order_book.get('ask_pressure'),
                    order_book.get('order_imbalance')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error storing order book data: {str(e)}")
            return False
    
    def store_alert(self, alert_data: Dict) -> bool:
        """Store alert data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO alerts (
                        symbol, alert_type, message, timestamp, price,
                        volume, trigger_value, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    alert_data.get('symbol'),
                    alert_data.get('type'),
                    alert_data.get('message'),
                    alert_data.get('timestamp', datetime.now()),
                    alert_data.get('price'),
                    alert_data.get('volume'),
                    alert_data.get('trigger_value'),
                    'active'
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error storing alert: {str(e)}")
            return False
    
    def store_news_data(self, news_items: List[Dict]) -> bool:
        """Store news data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for news_item in news_items:
                    cursor.execute('''
                        INSERT OR IGNORE INTO news_data (
                            symbol, title, summary, url, source, timestamp,
                            impact_score, relevance_score, sentiment
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        news_item.get('symbol'),
                        news_item.get('title'),
                        news_item.get('summary'),
                        news_item.get('url'),
                        news_item.get('source'),
                        news_item.get('timestamp', datetime.now()),
                        news_item.get('impact_score'),
                        news_item.get('relevance_score'),
                        news_item.get('sentiment')
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error storing news data: {str(e)}")
            return False
    
    def store_anomaly(self, anomaly_data: Dict) -> bool:
        """Store anomaly detection results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO anomalies (
                        symbol, anomaly_type, description, timestamp,
                        severity, price, volume, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    anomaly_data.get('symbol'),
                    anomaly_data.get('type'),
                    anomaly_data.get('description'),
                    anomaly_data.get('timestamp', datetime.now()),
                    anomaly_data.get('severity', 5),
                    anomaly_data.get('price'),
                    anomaly_data.get('volume'),
                    json.dumps(anomaly_data.get('metadata', {}))
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error storing anomaly: {str(e)}")
            return False
    
    def get_historical_data(self, symbol: str, hours_back: int = 24) -> pd.DataFrame:
        """Get historical stock data for a symbol"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT * FROM stock_data 
                    WHERE symbol = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                '''
                
                df = pd.read_sql_query(query, conn, params=(symbol, cutoff_time))
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                return df
                
        except Exception as e:
            print(f"Error getting historical data: {str(e)}")
            return pd.DataFrame()
    
    def get_recent_alerts(self, hours_back: int = 24) -> List[Dict]:
        """Get recent alerts"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM alerts 
                    WHERE timestamp >= ? AND status = 'active'
                    ORDER BY timestamp DESC
                ''', (cutoff_time,))
                
                columns = [description[0] for description in cursor.description]
                alerts = []
                
                for row in cursor.fetchall():
                    alert_dict = dict(zip(columns, row))
                    alert_dict['timestamp'] = datetime.fromisoformat(alert_dict['timestamp'])
                    alerts.append(alert_dict)
                
                return alerts
                
        except Exception as e:
            print(f"Error getting recent alerts: {str(e)}")
            return []
    
    def get_top_performers(self, hours_back: int = 24, limit: int = 10) -> List[Dict]:
        """Get top performing stocks by percentage change"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, MAX(change_percent) as max_change, 
                           MAX(volume_ratio) as max_volume_ratio,
                           MAX(price) as current_price
                    FROM stock_data 
                    WHERE timestamp >= ?
                    GROUP BY symbol
                    ORDER BY max_change DESC
                    LIMIT ?
                ''', (cutoff_time, limit))
                
                columns = [description[0] for description in cursor.description]
                performers = []
                
                for row in cursor.fetchall():
                    performer_dict = dict(zip(columns, row))
                    performers.append(performer_dict)
                
                return performers
                
        except Exception as e:
            print(f"Error getting top performers: {str(e)}")
            return []
    
    def get_volume_leaders(self, hours_back: int = 24, limit: int = 10) -> List[Dict]:
        """Get stocks with highest volume ratios"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT symbol, MAX(volume_ratio) as max_volume_ratio,
                           MAX(volume) as max_volume,
                           MAX(change_percent) as max_change
                    FROM stock_data 
                    WHERE timestamp >= ?
                    GROUP BY symbol
                    ORDER BY max_volume_ratio DESC
                    LIMIT ?
                ''', (cutoff_time, limit))
                
                columns = [description[0] for description in cursor.description]
                leaders = []
                
                for row in cursor.fetchall():
                    leader_dict = dict(zip(columns, row))
                    leaders.append(leader_dict)
                
                return leaders
                
        except Exception as e:
            print(f"Error getting volume leaders: {str(e)}")
            return []
    
    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old data to keep database size manageable"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up old stock data (keep more recent data)
                cursor.execute('DELETE FROM stock_data WHERE timestamp < ?', (cutoff_date,))
                
                # Clean up old order book data
                cursor.execute('DELETE FROM order_book_data WHERE timestamp < ?', (cutoff_date,))
                
                # Clean up old news data
                cursor.execute('DELETE FROM news_data WHERE timestamp < ?', (cutoff_date,))
                
                # Keep alerts for longer (90 days)
                alert_cutoff = datetime.now() - timedelta(days=90)
                cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (alert_cutoff,))
                
                conn.commit()
                print(f"Cleaned up data older than {days_old} days")
                
        except Exception as e:
            print(f"Error cleaning up old data: {str(e)}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Count records in each table
                tables = ['stock_data', 'order_book_data', 'alerts', 'news_data', 'anomalies', 'trading_patterns']
                
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Get database file size
                if os.path.exists(self.db_path):
                    stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
                
                # Get date range of data
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM stock_data')
                result = cursor.fetchone()
                if result[0] and result[1]:
                    stats['data_date_range'] = {
                        'start': result[0],
                        'end': result[1]
                    }
                
                return stats
                
        except Exception as e:
            print(f"Error getting database stats: {str(e)}")
            return {}
    
    def export_data(self, table_name: str, symbol: str = None, hours_back: int = 24) -> pd.DataFrame:
        """Export data from a specific table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if symbol:
                    cutoff_time = datetime.now() - timedelta(hours=hours_back)
                    query = f'''
                        SELECT * FROM {table_name} 
                        WHERE symbol = ? AND timestamp >= ?
                        ORDER BY timestamp DESC
                    '''
                    df = pd.read_sql_query(query, conn, params=(symbol, cutoff_time))
                else:
                    query = f'SELECT * FROM {table_name} ORDER BY timestamp DESC'
                    df = pd.read_sql_query(query, conn)
                
                return df
                
        except Exception as e:
            print(f"Error exporting data from {table_name}: {str(e)}")
            return pd.DataFrame()

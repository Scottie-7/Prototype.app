from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time

class AlertManager:
    """Manages alerts and notifications for stock monitoring"""
    
    def __init__(self):
        self.active_alerts = []
        self.alert_history = []
        self.alert_cooldowns = {}  # Prevent spam alerts
        self.cooldown_period = 300  # 5 minutes between same alerts
        
    def check_alerts(self, stock_data: Dict, price_threshold: float = 25.0, volume_threshold: float = 5.0) -> Optional[Dict]:
        """Check if stock data triggers any alerts"""
        try:
            symbol = stock_data.get('symbol')
            if not symbol:
                return None
            
            current_time = datetime.now()
            alerts_triggered = []
            
            # Price change alerts
            change_percent = stock_data.get('change_percent', 0)
            if abs(change_percent) >= price_threshold:
                alert_key = f"{symbol}_price_{change_percent > 0}"
                
                if self._should_trigger_alert(alert_key, current_time):
                    alert = {
                        'symbol': symbol,
                        'type': 'price_spike',
                        'message': f"{symbol} {'surged' if change_percent > 0 else 'plunged'} {abs(change_percent):.2f}%",
                        'timestamp': current_time,
                        'price': stock_data.get('price'),
                        'change_percent': change_percent,
                        'trigger_value': price_threshold,
                        'severity': self._calculate_price_severity(abs(change_percent))
                    }
                    alerts_triggered.append(alert)
                    self.alert_cooldowns[alert_key] = current_time
            
            # Volume spike alerts
            volume_ratio = stock_data.get('volume_ratio', 1)
            if volume_ratio >= volume_threshold:
                alert_key = f"{symbol}_volume_{volume_ratio:.1f}"
                
                if self._should_trigger_alert(alert_key, current_time):
                    alert = {
                        'symbol': symbol,
                        'type': 'volume_spike',
                        'message': f"{symbol} volume spike: {volume_ratio:.1f}x normal volume",
                        'timestamp': current_time,
                        'price': stock_data.get('price'),
                        'volume': stock_data.get('volume'),
                        'volume_ratio': volume_ratio,
                        'trigger_value': volume_threshold,
                        'severity': self._calculate_volume_severity(volume_ratio)
                    }
                    alerts_triggered.append(alert)
                    self.alert_cooldowns[alert_key] = current_time
            
            # Combination alerts (high price change + high volume)
            if abs(change_percent) >= 15 and volume_ratio >= 3:
                alert_key = f"{symbol}_combo_alert"
                
                if self._should_trigger_alert(alert_key, current_time):
                    alert = {
                        'symbol': symbol,
                        'type': 'combo_alert',
                        'message': f"{symbol} ALERT: {abs(change_percent):.1f}% move with {volume_ratio:.1f}x volume",
                        'timestamp': current_time,
                        'price': stock_data.get('price'),
                        'change_percent': change_percent,
                        'volume_ratio': volume_ratio,
                        'severity': 8  # High severity for combo alerts
                    }
                    alerts_triggered.append(alert)
                    self.alert_cooldowns[alert_key] = current_time
            
            # Unusual market cap alerts (for small caps)
            market_cap = stock_data.get('market_cap', 0)
            if market_cap > 0 and market_cap < 1e9 and abs(change_percent) >= 20:  # Small cap with big move
                alert_key = f"{symbol}_smallcap_move"
                
                if self._should_trigger_alert(alert_key, current_time):
                    alert = {
                        'symbol': symbol,
                        'type': 'smallcap_alert',
                        'message': f"Small cap {symbol} (${market_cap/1e6:.1f}M) moved {change_percent:.1f}%",
                        'timestamp': current_time,
                        'price': stock_data.get('price'),
                        'market_cap': market_cap,
                        'change_percent': change_percent,
                        'severity': 7
                    }
                    alerts_triggered.append(alert)
                    self.alert_cooldowns[alert_key] = current_time
            
            # Return the most severe alert if any
            if alerts_triggered:
                # Sort by severity and return the highest
                alerts_triggered.sort(key=lambda x: x.get('severity', 0), reverse=True)
                selected_alert = alerts_triggered[0]
                
                # Store in active alerts
                self.active_alerts.append(selected_alert)
                self.alert_history.append(selected_alert)
                
                # Keep only last 100 active alerts
                if len(self.active_alerts) > 100:
                    self.active_alerts = self.active_alerts[-100:]
                
                return selected_alert
            
            return None
            
        except Exception as e:
            print(f"Error checking alerts for {stock_data.get('symbol', 'Unknown')}: {str(e)}")
            return None
    
    def _should_trigger_alert(self, alert_key: str, current_time: datetime) -> bool:
        """Check if enough time has passed since last alert of this type"""
        if alert_key not in self.alert_cooldowns:
            return True
        
        last_alert_time = self.alert_cooldowns[alert_key]
        time_since_last = (current_time - last_alert_time).total_seconds()
        
        return time_since_last >= self.cooldown_period
    
    def _calculate_price_severity(self, change_percent: float) -> int:
        """Calculate alert severity based on price change"""
        if change_percent >= 100:
            return 10  # Extreme
        elif change_percent >= 75:
            return 9   # Very High
        elif change_percent >= 50:
            return 8   # High
        elif change_percent >= 35:
            return 7   # Significant
        elif change_percent >= 25:
            return 6   # Moderate High
        else:
            return 5   # Moderate
    
    def _calculate_volume_severity(self, volume_ratio: float) -> int:
        """Calculate alert severity based on volume ratio"""
        if volume_ratio >= 50:
            return 10  # Extreme volume
        elif volume_ratio >= 30:
            return 9   # Very high volume
        elif volume_ratio >= 20:
            return 8   # High volume
        elif volume_ratio >= 15:
            return 7   # Significant volume
        elif volume_ratio >= 10:
            return 6   # Moderate high volume
        else:
            return 5   # Moderate volume
    
    def create_custom_alert(self, symbol: str, condition: Dict, message: str) -> bool:
        """Create a custom alert condition"""
        try:
            custom_alert = {
                'symbol': symbol,
                'condition': condition,
                'message': message,
                'created_time': datetime.now(),
                'active': True
            }
            
            # Store custom alert (would typically go to database)
            if not hasattr(self, 'custom_alerts'):
                self.custom_alerts = []
            
            self.custom_alerts.append(custom_alert)
            return True
            
        except Exception as e:
            print(f"Error creating custom alert: {str(e)}")
            return False
    
    def check_custom_alerts(self, stock_data: Dict) -> List[Dict]:
        """Check if stock data triggers any custom alerts"""
        try:
            if not hasattr(self, 'custom_alerts'):
                return []
            
            triggered_alerts = []
            
            for custom_alert in self.custom_alerts:
                if not custom_alert.get('active'):
                    continue
                
                symbol = custom_alert['symbol']
                if symbol != stock_data.get('symbol'):
                    continue
                
                condition = custom_alert['condition']
                
                # Check if condition is met
                if self._evaluate_condition(condition, stock_data):
                    alert = {
                        'symbol': symbol,
                        'type': 'custom_alert',
                        'message': custom_alert['message'],
                        'timestamp': datetime.now(),
                        'condition': condition,
                        'stock_data': stock_data
                    }
                    triggered_alerts.append(alert)
            
            return triggered_alerts
            
        except Exception as e:
            print(f"Error checking custom alerts: {str(e)}")
            return []
    
    def _evaluate_condition(self, condition: Dict, stock_data: Dict) -> bool:
        """Evaluate if a custom condition is met"""
        try:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not all([field, operator, value is not None]):
                return False
            
            stock_value = stock_data.get(field)
            if stock_value is None:
                return False
            
            if operator == '>':
                return stock_value > value
            elif operator == '<':
                return stock_value < value
            elif operator == '>=':
                return stock_value >= value
            elif operator == '<=':
                return stock_value <= value
            elif operator == '==':
                return stock_value == value
            elif operator == '!=':
                return stock_value != value
            
            return False
            
        except Exception as e:
            print(f"Error evaluating condition: {str(e)}")
            return False
    
    def get_active_alerts(self, hours_back: int = 24) -> List[Dict]:
        """Get active alerts from the last N hours"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            recent_alerts = [
                alert for alert in self.active_alerts
                if alert.get('timestamp', datetime.min) >= cutoff_time
            ]
            
            # Sort by timestamp descending (most recent first)
            recent_alerts.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
            
            return recent_alerts
            
        except Exception as e:
            print(f"Error getting active alerts: {str(e)}")
            return []
    
    def get_alert_summary(self) -> Dict:
        """Get summary statistics of alerts"""
        try:
            now = datetime.now()
            last_hour = now - timedelta(hours=1)
            last_day = now - timedelta(days=1)
            
            alerts_last_hour = [
                alert for alert in self.active_alerts
                if alert.get('timestamp', datetime.min) >= last_hour
            ]
            
            alerts_last_day = [
                alert for alert in self.active_alerts
                if alert.get('timestamp', datetime.min) >= last_day
            ]
            
            # Group by type
            alert_types = {}
            for alert in alerts_last_day:
                alert_type = alert.get('type', 'unknown')
                if alert_type not in alert_types:
                    alert_types[alert_type] = 0
                alert_types[alert_type] += 1
            
            # Top symbols with most alerts
            symbol_counts = {}
            for alert in alerts_last_day:
                symbol = alert.get('symbol', 'unknown')
                if symbol not in symbol_counts:
                    symbol_counts[symbol] = 0
                symbol_counts[symbol] += 1
            
            top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'total_alerts_last_hour': len(alerts_last_hour),
                'total_alerts_last_day': len(alerts_last_day),
                'alert_types': alert_types,
                'top_alert_symbols': top_symbols,
                'average_severity': sum(alert.get('severity', 5) for alert in alerts_last_day) / len(alerts_last_day) if alerts_last_day else 0
            }
            
        except Exception as e:
            print(f"Error getting alert summary: {str(e)}")
            return {}
    
    def clear_old_alerts(self, hours_old: int = 48):
        """Clear old alerts to prevent memory buildup"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_old)
            
            # Clear old active alerts
            self.active_alerts = [
                alert for alert in self.active_alerts
                if alert.get('timestamp', datetime.min) >= cutoff_time
            ]
            
            # Clear old cooldowns
            self.alert_cooldowns = {
                key: timestamp for key, timestamp in self.alert_cooldowns.items()
                if timestamp >= cutoff_time
            }
            
            print(f"Cleared alerts older than {hours_old} hours")
            
        except Exception as e:
            print(f"Error clearing old alerts: {str(e)}")
    
    def export_alerts(self, format: str = 'json') -> str:
        """Export alerts in specified format"""
        try:
            import json
            
            export_data = {
                'active_alerts': self.active_alerts,
                'alert_history': self.alert_history[-100:],  # Last 100 historical alerts
                'export_timestamp': datetime.now().isoformat()
            }
            
            if format == 'json':
                return json.dumps(export_data, default=str, indent=2)
            else:
                return str(export_data)
                
        except Exception as e:
            print(f"Error exporting alerts: {str(e)}")
            return ""
    
    def get_alert_performance_metrics(self) -> Dict:
        """Calculate performance metrics for alert system"""
        try:
            if not self.alert_history:
                return {}
            
            # Calculate metrics over last 7 days
            week_ago = datetime.now() - timedelta(days=7)
            recent_alerts = [
                alert for alert in self.alert_history
                if alert.get('timestamp', datetime.min) >= week_ago
            ]
            
            if not recent_alerts:
                return {}
            
            # Alert frequency
            alert_frequency = len(recent_alerts) / 7  # Alerts per day
            
            # Average severity
            avg_severity = sum(alert.get('severity', 5) for alert in recent_alerts) / len(recent_alerts)
            
            # Most common alert types
            type_distribution = {}
            for alert in recent_alerts:
                alert_type = alert.get('type', 'unknown')
                type_distribution[alert_type] = type_distribution.get(alert_type, 0) + 1
            
            return {
                'alerts_per_day': alert_frequency,
                'average_severity': avg_severity,
                'total_alerts_week': len(recent_alerts),
                'type_distribution': type_distribution,
                'unique_symbols': len(set(alert.get('symbol') for alert in recent_alerts))
            }
            
        except Exception as e:
            print(f"Error calculating alert performance metrics: {str(e)}")
            return {}

import os
import sys
from typing import Optional
from datetime import datetime

# Twilio integration - based on twilio_send_message blueprint
from twilio.rest import Client

# SendGrid integration - based on python_sendgrid blueprint
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

class NotificationManager:
    """Handles email and SMS notifications for stock alerts"""
    
    def __init__(self):
        # Twilio configuration
        self.twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
        
        # SendGrid configuration
        self.sendgrid_api_key = os.environ.get("SENDGRID_API_KEY")
        
        # Initialize clients if credentials are available
        self.twilio_client = None
        self.sendgrid_client = None
        
        if all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
            try:
                self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            except Exception as e:
                print(f"Failed to initialize Twilio client: {e}")
        
        if self.sendgrid_api_key:
            try:
                self.sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
            except Exception as e:
                print(f"Failed to initialize SendGrid client: {e}")
    
    def is_sms_configured(self) -> bool:
        """Check if SMS notifications are properly configured"""
        return self.twilio_client is not None
    
    def is_email_configured(self) -> bool:
        """Check if email notifications are properly configured"""
        return self.sendgrid_client is not None
    
    def send_sms_alert(self, to_phone_number: str, alert_data: dict) -> bool:
        """Send SMS alert for stock event"""
        if not self.twilio_client:
            print("SMS not configured - missing Twilio credentials")
            return False
        
        try:
            # Format alert message
            symbol = alert_data.get('symbol', 'Unknown')
            alert_type = alert_data.get('type', 'Alert')
            message_text = alert_data.get('message', 'Stock alert triggered')
            price = alert_data.get('price', 0)
            change_percent = alert_data.get('change_percent', 0)
            
            # Create SMS message
            sms_message = f"""
🚨 STOCK ALERT: {symbol}
{alert_type.upper()}: {message_text}
Price: ${price:.2f} ({change_percent:+.2f}%)
Time: {datetime.now().strftime('%H:%M:%S')}
            """.strip()
            
            # Send SMS
            message = self.twilio_client.messages.create(
                body=sms_message,
                from_=self.twilio_phone_number,
                to=to_phone_number
            )
            
            print(f"SMS alert sent successfully. SID: {message.sid}")
            return True
            
        except Exception as e:
            print(f"Failed to send SMS alert: {e}")
            return False
    
    def send_email_alert(self, to_email: str, from_email: str, alert_data: dict) -> bool:
        """Send email alert for stock event"""
        if not self.sendgrid_client:
            print("Email not configured - missing SendGrid API key")
            return False
        
        try:
            # Format alert data
            symbol = alert_data.get('symbol', 'Unknown')
            alert_type = alert_data.get('type', 'Alert')
            message_text = alert_data.get('message', 'Stock alert triggered')
            price = alert_data.get('price', 0)
            change_percent = alert_data.get('change_percent', 0)
            volume = alert_data.get('volume', 0)
            timestamp = alert_data.get('timestamp', datetime.now())
            
            # Create email subject
            subject = f"🚨 Stock Alert: {symbol} - {alert_type.title()}"
            
            # Create HTML email content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🚨 Stock Alert</h1>
                    <h2 style="color: white; margin: 10px 0 0 0;">{symbol}</h2>
                </div>
                
                <div style="padding: 20px; background-color: #f8f9fa;">
                    <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h3 style="color: #333; margin-top: 0;">Alert Details</h3>
                        
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px; font-weight: bold; color: #555;">Alert Type:</td>
                                <td style="padding: 8px; color: #333;">{alert_type.title()}</td>
                            </tr>
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 8px; font-weight: bold; color: #555;">Message:</td>
                                <td style="padding: 8px; color: #333;">{message_text}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold; color: #555;">Current Price:</td>
                                <td style="padding: 8px; color: #333; font-weight: bold;">${price:.2f}</td>
                            </tr>
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 8px; font-weight: bold; color: #555;">Change:</td>
                                <td style="padding: 8px; font-weight: bold; color: {'green' if change_percent > 0 else 'red'};">{change_percent:+.2f}%</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px; font-weight: bold; color: #555;">Volume:</td>
                                <td style="padding: 8px; color: #333;">{volume:,}</td>
                            </tr>
                            <tr style="background-color: #f8f9fa;">
                                <td style="padding: 8px; font-weight: bold; color: #555;">Time:</td>
                                <td style="padding: 8px; color: #333;">{timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px; border-left: 4px solid #2196f3;">
                        <p style="margin: 0; color: #1976d2;">
                            <strong>📊 Trading Tip:</strong> Always verify alerts with additional research before making trading decisions.
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; padding: 20px; color: #666; font-size: 12px;">
                    <p>This alert was generated by your AI Stock Monitoring Dashboard</p>
                    <p>Developed by Zia Quant Fund-2025</p>
                </div>
            </body>
            </html>
            """
            
            # Create text content as fallback
            text_content = f"""
STOCK ALERT: {symbol}

Alert Type: {alert_type.title()}
Message: {message_text}
Current Price: ${price:.2f}
Change: {change_percent:+.2f}%
Volume: {volume:,}
Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

This alert was generated by your AI Stock Monitoring Dashboard.
            """.strip()
            
            # Create and send email
            message = Mail(
                from_email=Email(from_email),
                to_emails=To(to_email),
                subject=subject
            )
            
            # Add both HTML and text content
            message.content = [
                Content("text/plain", text_content),
                Content("text/html", html_content)
            ]
            
            response = self.sendgrid_client.send(message)
            print(f"Email alert sent successfully. Status code: {response.status_code}")
            return True
            
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
    
    def send_alert(self, alert_data: dict, email_config: Optional[dict] = None, sms_config: Optional[dict] = None) -> dict:
        """Send alert via configured notification methods"""
        results = {
            'email_sent': False,
            'sms_sent': False,
            'errors': []
        }
        
        # Send email if configured
        if email_config and email_config.get('enabled') and email_config.get('to_email'):
            try:
                from_email = email_config.get('from_email', 'alerts@ziacapital.com')
                results['email_sent'] = self.send_email_alert(
                    email_config['to_email'], 
                    from_email, 
                    alert_data
                )
            except Exception as e:
                results['errors'].append(f"Email error: {str(e)}")
        
        # Send SMS if configured
        if sms_config and sms_config.get('enabled') and sms_config.get('phone_number'):
            try:
                results['sms_sent'] = self.send_sms_alert(
                    sms_config['phone_number'], 
                    alert_data
                )
            except Exception as e:
                results['errors'].append(f"SMS error: {str(e)}")
        
        return results
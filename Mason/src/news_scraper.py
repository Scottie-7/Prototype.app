import requests
import feedparser
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from typing import Dict, List, Optional
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

class NewsMonitor:
    """Monitors financial news from multiple sources"""
    
    def __init__(self):
        self.news_sources = {
            'yahoo_finance': {
                'rss_url': 'https://feeds.finance.yahoo.com/rss/2.0/headline',
                'search_url': 'https://finance.yahoo.com/lookup?s={symbol}'
            },
            'marketwatch': {
                'rss_url': 'http://feeds.marketwatch.com/marketwatch/topstories/',
                'search_url': 'https://www.marketwatch.com/investing/stock/{symbol}'
            },
            'seeking_alpha': {
                'rss_url': 'https://seekingalpha.com/market_currents.xml',
                'search_url': 'https://seekingalpha.com/symbol/{symbol}/news'
            },
            'reuters': {
                'rss_url': 'http://feeds.reuters.com/reuters/businessNews',
                'search_url': 'https://www.reuters.com/companies/{symbol}'
            }
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Keywords that indicate significant market events
        self.high_impact_keywords = [
            'earnings', 'merger', 'acquisition', 'buyout', 'takeover',
            'FDA approval', 'clinical trial', 'breakthrough', 'patent',
            'lawsuit', 'settlement', 'bankruptcy', 'restructuring',
            'guidance', 'outlook', 'forecast', 'upgrade', 'downgrade',
            'split', 'dividend', 'spinoff', 'partnership', 'contract',
            'recall', 'investigation', 'SEC', 'regulatory',
            'surge', 'plunge', 'spike', 'crash', 'rally'
        ]
    
    def get_stock_news(self, symbol: str, sources: List[str] = None, hours_back: int = 24) -> List[Dict]:
        """Get news for a specific stock symbol"""
        try:
            if sources is None:
                sources = ['Yahoo Finance', 'MarketWatch']
            
            all_news = []
            
            # Get general financial news
            general_news = self._get_general_news(hours_back)
            
            # Filter news that mentions the symbol
            symbol_news = []
            for news_item in general_news:
                title = news_item.get('title', '').lower()
                summary = news_item.get('summary', '').lower()
                
                # Check if symbol is mentioned in title or summary
                if (symbol.lower() in title or 
                    symbol.lower() in summary or
                    f'${symbol.lower()}' in title or 
                    f'${symbol.lower()}' in summary):
                    
                    news_item['relevance_score'] = self._calculate_relevance_score(news_item, symbol)
                    symbol_news.append(news_item)
            
            # Try to get symbol-specific news from Yahoo Finance
            yahoo_news = self._get_yahoo_symbol_news(symbol)
            symbol_news.extend(yahoo_news)
            
            # Remove duplicates based on title similarity
            unique_news = self._deduplicate_news(symbol_news)
            
            # Sort by relevance and timestamp
            unique_news.sort(key=lambda x: (x.get('relevance_score', 0), x.get('timestamp', datetime.min)), reverse=True)
            
            return unique_news[:10]  # Return top 10 most relevant
            
        except Exception as e:
            print(f"Error fetching stock news for {symbol}: {str(e)}")
            return []
    
    def _get_general_news(self, hours_back: int = 24) -> List[Dict]:
        """Get general financial news from RSS feeds"""
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        def fetch_rss_news(source_name, source_info):
            try:
                feed = feedparser.parse(source_info['rss_url'])
                source_news = []
                
                for entry in feed.entries:
                    try:
                        # Parse publication date
                        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                        
                        if pub_date >= cutoff_time:
                            news_item = {
                                'title': entry.title if hasattr(entry, 'title') else 'No title',
                                'summary': entry.summary if hasattr(entry, 'summary') else 'No summary',
                                'url': entry.link if hasattr(entry, 'link') else '',
                                'source': source_name,
                                'timestamp': pub_date,
                                'impact_score': self._calculate_impact_score(entry.title if hasattr(entry, 'title') else '')
                            }
                            source_news.append(news_item)
                    except Exception as e:
                        continue
                
                return source_news
            except Exception as e:
                print(f"Error fetching RSS from {source_name}: {str(e)}")
                return []
        
        # Use ThreadPoolExecutor for parallel RSS fetching
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(fetch_rss_news, name, info): name 
                for name, info in self.news_sources.items()
            }
            
            for future in as_completed(futures):
                try:
                    news_items = future.result(timeout=10)
                    all_news.extend(news_items)
                except Exception as e:
                    print(f"Error processing news source: {str(e)}")
                    continue
        
        return all_news
    
    def _get_yahoo_symbol_news(self, symbol: str) -> List[Dict]:
        """Get symbol-specific news from Yahoo Finance"""
        try:
            # Yahoo Finance news API endpoint (unofficial)
            url = f"https://query2.finance.yahoo.com/v1/finance/search"
            params = {
                'q': symbol,
                'quotes_count': 1,
                'news_count': 10,
                'enable_fuzzy_query': False
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                news_items = []
                
                if 'news' in data:
                    for item in data['news']:
                        try:
                            news_item = {
                                'title': item.get('title', 'No title'),
                                'summary': item.get('summary', 'No summary'),
                                'url': item.get('link', ''),
                                'source': 'Yahoo Finance',
                                'timestamp': datetime.fromtimestamp(item.get('providerPublishTime', time.time())),
                                'impact_score': self._calculate_impact_score(item.get('title', '')),
                                'relevance_score': 10  # High relevance for symbol-specific news
                            }
                            news_items.append(news_item)
                        except Exception as e:
                            continue
                
                return news_items
            
        except Exception as e:
            print(f"Error fetching Yahoo Finance news for {symbol}: {str(e)}")
        
        return []
    
    def _calculate_impact_score(self, text: str) -> float:
        """Calculate the potential market impact of a news item"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        impact_score = 0.0
        
        # High impact keywords
        for keyword in self.high_impact_keywords:
            if keyword in text_lower:
                if keyword in ['earnings', 'merger', 'acquisition', 'FDA approval']:
                    impact_score += 3.0
                elif keyword in ['upgrade', 'downgrade', 'guidance', 'breakthrough']:
                    impact_score += 2.0
                else:
                    impact_score += 1.0
        
        # Check for percentage mentions (often indicate significant moves)
        percentage_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', text_lower)
        if percentage_matches:
            max_percentage = max(float(p) for p in percentage_matches)
            if max_percentage > 20:
                impact_score += 2.0
            elif max_percentage > 10:
                impact_score += 1.0
        
        # Check for dollar amounts (M/B indicates large deals)
        if re.search(r'\$\d+(?:\.\d+)?\s*(?:billion|million|b|m)\b', text_lower):
            impact_score += 1.5
        
        return min(impact_score, 10.0)  # Cap at 10
    
    def _calculate_relevance_score(self, news_item: Dict, symbol: str) -> float:
        """Calculate how relevant a news item is to a specific symbol"""
        relevance_score = 0.0
        
        title = news_item.get('title', '').lower()
        summary = news_item.get('summary', '').lower()
        symbol_lower = symbol.lower()
        
        # Direct symbol mentions
        if symbol_lower in title:
            relevance_score += 5.0
        if f'${symbol_lower}' in title:
            relevance_score += 6.0
        
        if symbol_lower in summary:
            relevance_score += 3.0
        if f'${symbol_lower}' in summary:
            relevance_score += 4.0
        
        # Company name matching would require a symbol-to-company mapping
        # For now, we'll use the impact score as a relevance booster
        relevance_score += news_item.get('impact_score', 0) * 0.5
        
        # Recent news gets higher relevance
        timestamp = news_item.get('timestamp', datetime.min)
        hours_old = (datetime.now() - timestamp).total_seconds() / 3600
        
        if hours_old < 1:
            relevance_score += 2.0
        elif hours_old < 6:
            relevance_score += 1.0
        
        return relevance_score
    
    def _deduplicate_news(self, news_list: List[Dict]) -> List[Dict]:
        """Remove duplicate news items based on title similarity"""
        if not news_list:
            return []
        
        unique_news = []
        seen_titles = set()
        
        for news_item in news_list:
            title = news_item.get('title', '').lower()
            
            # Create a normalized version of the title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', title)
            words = set(normalized_title.split())
            
            # Check if this title is too similar to existing ones
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                
                # Calculate Jaccard similarity
                intersection = words.intersection(seen_words)
                union = words.union(seen_words)
                
                if union and len(intersection) / len(union) > 0.7:  # 70% similarity threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_news.append(news_item)
                seen_titles.add(normalized_title)
        
        return unique_news
    
    def get_breaking_news(self, keywords: List[str] = None) -> List[Dict]:
        """Get breaking financial news based on keywords"""
        try:
            if keywords is None:
                keywords = ['breaking', 'alert', 'surge', 'plunge', 'halted']
            
            # Get recent news (last 2 hours)
            recent_news = self._get_general_news(hours_back=2)
            
            breaking_news = []
            
            for news_item in recent_news:
                title = news_item.get('title', '').lower()
                summary = news_item.get('summary', '').lower()
                
                # Check for breaking news keywords
                for keyword in keywords:
                    if keyword in title or keyword in summary:
                        news_item['breaking_keyword'] = keyword
                        breaking_news.append(news_item)
                        break
            
            # Sort by impact score and timestamp
            breaking_news.sort(key=lambda x: (x.get('impact_score', 0), x.get('timestamp', datetime.min)), reverse=True)
            
            return breaking_news[:5]  # Return top 5 breaking news items
            
        except Exception as e:
            print(f"Error fetching breaking news: {str(e)}")
            return []
    
    def monitor_earnings_calendar(self) -> List[Dict]:
        """Monitor upcoming earnings announcements (basic implementation)"""
        try:
            # This would typically require a paid API like Alpha Vantage or Financial Modeling Prep
            # For now, we'll search for earnings-related news
            earnings_news = []
            
            recent_news = self._get_general_news(hours_back=48)
            
            for news_item in recent_news:
                title = news_item.get('title', '').lower()
                summary = news_item.get('summary', '').lower()
                
                earnings_keywords = ['earnings', 'results', 'quarterly', 'q1', 'q2', 'q3', 'q4']
                
                if any(keyword in title or keyword in summary for keyword in earnings_keywords):
                    earnings_news.append(news_item)
            
            return earnings_news[:10]
            
        except Exception as e:
            print(f"Error monitoring earnings calendar: {str(e)}")
            return []
    
    def analyze_news_sentiment(self, news_items: List[Dict]) -> Dict:
        """Analyze sentiment of news items (basic implementation)"""
        try:
            if not news_items:
                return {'overall_sentiment': 0, 'positive_count': 0, 'negative_count': 0, 'neutral_count': 0}
            
            positive_words = ['surge', 'rally', 'gain', 'rise', 'up', 'bull', 'positive', 'strong', 'growth', 'beat']
            negative_words = ['plunge', 'crash', 'fall', 'drop', 'down', 'bear', 'negative', 'weak', 'loss', 'miss']
            
            sentiment_scores = []
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for news_item in news_items:
                text = f"{news_item.get('title', '')} {news_item.get('summary', '')}".lower()
                
                positive_score = sum(1 for word in positive_words if word in text)
                negative_score = sum(1 for word in negative_words if word in text)
                
                if positive_score > negative_score:
                    sentiment = 1
                    positive_count += 1
                elif negative_score > positive_score:
                    sentiment = -1
                    negative_count += 1
                else:
                    sentiment = 0
                    neutral_count += 1
                
                sentiment_scores.append(sentiment)
                news_item['sentiment'] = sentiment
            
            overall_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            return {
                'overall_sentiment': overall_sentiment,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count,
                'sentiment_distribution': sentiment_scores
            }
            
        except Exception as e:
            print(f"Error analyzing news sentiment: {str(e)}")
            return {'overall_sentiment': 0, 'positive_count': 0, 'negative_count': 0, 'neutral_count': 0}

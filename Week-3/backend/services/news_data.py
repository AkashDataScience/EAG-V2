#!/usr/bin/env python3
"""
News data fetching service
"""

import requests
import yfinance as yf
from typing import List
from datetime import datetime, timedelta

from models import NewsItem
from config import config
from utils.logger import logger

class NewsDataService:
    """Handles fetching news data from various sources"""
    
    @staticmethod
    def fetch_news(symbol: str, days: int = 30) -> List[NewsItem]:
        """Fetch news headlines for a stock symbol using intelligent sampling strategy"""
        try:
            # Check if NewsAPI key is configured
            if not config.NEWS_API_KEY or config.NEWS_API_KEY == 'your-news-api-key-here':
                raise ValueError("NewsAPI key not configured. Please set NEWS_API_KEY in your .env file")
            
            # Get company name for better search results
            company_name = NewsDataService._get_company_name(symbol)
            logger.info(f"Fetching news for {symbol} ({company_name}) using intelligent sampling")
            
            # Use intelligent sampling strategy
            all_articles = NewsDataService._fetch_with_intelligent_sampling(
                symbol, company_name, days
            )
            
            if not all_articles:
                logger.warning(f"No news articles found for {symbol}")
                return []
            
            # Convert to NewsItem objects
            news_items = []
            for article in all_articles:
                try:
                    news_items.append(NewsItem(
                        headline=article['title'],
                        date=article['publishedAt'],
                        url=article['url'],
                        source=article['source']['name']
                    ))
                except KeyError as e:
                    logger.warning(f"Skipping article with missing field: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(news_items)} news items for {symbol} using intelligent sampling")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            raise

    @staticmethod
    def _fetch_with_intelligent_sampling(symbol: str, company_name: str, days: int) -> List[dict]:
        """Fetch news using intelligent sampling strategy to get diverse, representative articles"""
        
        # High-impact financial news sources (prioritize these)
        priority_sources = [
            'Reuters', 'Bloomberg', 'Wall Street Journal', 'Financial Times', 
            'MarketWatch', 'Yahoo Finance', 'CNBC', 'Seeking Alpha',
            'The Motley Fool', 'Benzinga', 'Barron\'s'
        ]
        
        all_articles = []
        
        # Strategy 1: Get recent high-priority articles (last 7 days)
        recent_articles = NewsDataService._fetch_news_batch(
            symbol, company_name, 
            days=min(7, days), 
            page_size=50,
            sort_by='publishedAt',
            sources=priority_sources
        )
        all_articles.extend(recent_articles)
        logger.info(f"Fetched {len(recent_articles)} recent priority articles")
        
        # Strategy 2: Get popular articles (sorted by popularity) from full period
        if days > 7:
            popular_articles = NewsDataService._fetch_news_batch(
                symbol, company_name,
                days=days,
                page_size=30,
                sort_by='popularity'
            )
            # Remove duplicates
            existing_urls = {article['url'] for article in all_articles}
            unique_popular = [a for a in popular_articles if a['url'] not in existing_urls]
            all_articles.extend(unique_popular)
            logger.info(f"Fetched {len(unique_popular)} additional popular articles")
        
        # Strategy 3: Time-distributed sampling for longer periods
        if days > 14:
            distributed_articles = NewsDataService._fetch_time_distributed_articles(
                symbol, company_name, days, target_count=20
            )
            # Remove duplicates
            existing_urls = {article['url'] for article in all_articles}
            unique_distributed = [a for a in distributed_articles if a['url'] not in existing_urls]
            all_articles.extend(unique_distributed)
            logger.info(f"Fetched {len(unique_distributed)} time-distributed articles")
        
        # Sort by date (most recent first) and limit total
        all_articles.sort(key=lambda x: x['publishedAt'], reverse=True)
        
        # Intelligent limit: more articles for longer periods
        max_articles = min(100, max(30, days * 2))  # 30-100 articles based on period
        final_articles = all_articles[:max_articles]
        
        logger.info(f"Final selection: {len(final_articles)} articles from {len(all_articles)} total")
        return final_articles

    @staticmethod
    def _fetch_news_batch(symbol: str, company_name: str, days: int, page_size: int = 30, 
                         sort_by: str = 'publishedAt', sources: List[str] = None) -> List[dict]:
        """Fetch a batch of news articles with specific parameters"""
        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': f'"{company_name}" OR "{symbol}"',
                'apiKey': config.NEWS_API_KEY,
                'language': 'en',
                'sortBy': sort_by,
                'pageSize': min(page_size, 100),  # NewsAPI max is 100
                'from': (datetime.now() - timedelta(days=days)).isoformat()
            }
            
            # Add source filtering if specified
            if sources:
                # NewsAPI expects comma-separated source domains/names
                source_domains = []
                for source in sources:
                    if source.lower() == 'reuters':
                        source_domains.append('reuters.com')
                    elif source.lower() == 'bloomberg':
                        source_domains.append('bloomberg.com')
                    elif source.lower() == 'wall street journal':
                        source_domains.append('wsj.com')
                    elif source.lower() == 'financial times':
                        source_domains.append('ft.com')
                    elif source.lower() == 'marketwatch':
                        source_domains.append('marketwatch.com')
                    elif source.lower() == 'yahoo finance':
                        source_domains.append('finance.yahoo.com')
                    elif source.lower() == 'cnbc':
                        source_domains.append('cnbc.com')
                
                if source_domains:
                    params['domains'] = ','.join(source_domains[:20])  # Limit to avoid URL length issues
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"NewsAPI batch request failed: {response.status_code}")
                return []
            
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.warning(f"NewsAPI batch error: {data.get('message', 'Unknown error')}")
                return []
            
            return data.get('articles', [])
            
        except Exception as e:
            logger.warning(f"Error in news batch fetch: {str(e)}")
            return []

    @staticmethod
    def _fetch_time_distributed_articles(symbol: str, company_name: str, days: int, target_count: int = 20) -> List[dict]:
        """Fetch articles distributed across the time period to avoid recency bias"""
        articles = []
        
        # Divide the time period into segments
        segments = min(4, days // 7)  # Up to 4 segments, each at least a week
        if segments < 2:
            return []
        
        articles_per_segment = target_count // segments
        
        for i in range(segments):
            # Calculate date range for this segment
            segment_end_days = days * i // segments
            segment_start_days = days * (i + 1) // segments
            
            segment_articles = NewsDataService._fetch_news_batch(
                symbol, company_name,
                days=segment_start_days,
                page_size=articles_per_segment * 2,  # Fetch extra to account for filtering
                sort_by='relevancy'
            )
            
            # Filter to articles within this segment's date range
            segment_start_date = datetime.now() - timedelta(days=segment_start_days)
            segment_end_date = datetime.now() - timedelta(days=segment_end_days)
            
            filtered_articles = []
            for article in segment_articles:
                try:
                    article_date = datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00'))
                    if segment_start_date <= article_date <= segment_end_date:
                        filtered_articles.append(article)
                        if len(filtered_articles) >= articles_per_segment:
                            break
                except:
                    continue
            
            articles.extend(filtered_articles)
            logger.info(f"Segment {i+1}: {len(filtered_articles)} articles")
        
        return articles

    @staticmethod
    def _get_company_name(symbol: str) -> str:
        """Get company name from symbol for better news search"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('longName', symbol)
        except:
            return symbol
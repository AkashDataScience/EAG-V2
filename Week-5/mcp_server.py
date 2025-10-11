#!/usr/bin/env python3
"""
Stock Analysis MCP Server
MCP-powered stock analysis with news sentiment correlation
"""

from mcp.server.fastmcp import FastMCP
import yfinance as yf
import requests
from google import genai
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Any
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("StockAnalysisServer")

# Global configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Global storage for analysis data
analysis_context = {}

@mcp.tool()
def fetch_stock_data(symbol: str, period: str = "1mo", interval: str = "1h") -> str:
    """Fetch stock price data from Yahoo Finance for Indian stocks"""
    print(f"CALLED: fetch_stock_data(symbol='{symbol}', period='{period}', interval='{interval}') -> str:")
    
    try:
        # Clean symbol
        symbol = symbol.upper().strip()
        
        print(f"Fetching data for stock: {symbol}")
        
        # Create ticker object
        ticker = yf.Ticker(symbol)
        
        # Fetch historical data
        hist = ticker.history(period=period, interval=interval)
        
        if hist.empty:
            return f"Error: No data found for symbol {symbol}. Please check if it's a valid stock symbol."
        
        # Convert to list of dictionaries for easier processing
        candles = []
        for timestamp, row in hist.iterrows():
            candles.append({
                'timestamp': timestamp.isoformat(),
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume'])
            })
        
        # Store in global context
        analysis_context['stock_data'] = {
            'symbol': symbol,
            'period': period,
            'interval': interval,
            'candles': candles,
            'current_price': candles[-1]['close'] if candles else 0,
            'price_change': ((candles[-1]['close'] - candles[0]['close']) / candles[0]['close'] * 100) if len(candles) > 1 else 0
        }
        
        return f"Successfully fetched {len(candles)} price points for {symbol}. Current price: ₹{candles[-1]['close']:.2f}"
        
    except Exception as e:
        return f"Error fetching stock data: {str(e)}"

@mcp.tool()
def fetch_news_data(symbol: str, days: int = 7) -> str:
    """Fetch recent news for an Indian stock symbol using intelligent sampling strategy"""
    print(f"CALLED: fetch_news_data(symbol='{symbol}', days={days}) -> str:")
    
    try:
        # Clean symbol
        symbol = symbol.upper().strip()
        
        # Check if NewsAPI key is configured
        if not NEWS_API_KEY or NEWS_API_KEY == 'your-news-api-key-here':
            return "Error: NewsAPI key not configured. Please set NEWS_API_KEY in .env file"
        
        # Get company info for better news search
        ticker = yf.Ticker(symbol)
        info = ticker.info
        company_name = info.get('longName', symbol.replace('.NS', '').replace('.BO', ''))
        
        # For news search, use clean symbol (without .NS/.BO suffix)
        search_symbol = symbol.replace('.NS', '').replace('.BO', '')
        
        print(f"Fetching news for stock {symbol} ({company_name}) using intelligent sampling")
        
        # Use intelligent sampling strategy
        all_articles = _fetch_with_intelligent_sampling(search_symbol, company_name, days)
        
        if not all_articles:
            return f"No news articles found for {company_name} ({symbol}) in the last {days} days"
        
        # Convert to our format and store in global context
        news_articles = []
        for article in all_articles:
            try:
                news_articles.append({
                    'title': article['title'],
                    'summary': article.get('description', ''),
                    'published': article['publishedAt'],
                    'source': article['source']['name'],
                    'url': article['url'],
                    'author': article.get('author', 'Unknown')
                })
            except KeyError as e:
                print(f"Skipping article with missing field: {e}")
                continue
        
        # Store in global context
        analysis_context['news_data'] = {
            'symbol': symbol,
            'search_symbol': search_symbol,
            'company_name': company_name,
            'articles': news_articles,
            'total_articles': len(news_articles),
            'source': 'NewsAPI (Intelligent Sampling)',
            'sampling_strategy': 'Priority sources + Popular + Time-distributed',
            'date_range': f"{(datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
        }
        
        return f"Successfully fetched {len(news_articles)} news articles for {company_name} ({symbol}) using intelligent sampling"
        
    except Exception as e:
        return f"Error fetching news data: {str(e)}"


def _fetch_with_intelligent_sampling(symbol: str, company_name: str, days: int) -> List[Dict[str, Any]]:
    """Fetch news using intelligent sampling strategy to get diverse, representative articles"""
    
    # High-impact financial news sources (Indian market focused)
    priority_sources = [
        'Reuters', 'Bloomberg', 'Economic Times', 'Business Standard',
        'Mint', 'Financial Express', 'MoneyControl', 'CNBC TV18',
        'Business Today', 'Forbes India', 'Yahoo Finance', 'CNBC'
    ]
    
    all_articles = []
    
    # Strategy 1: Get recent high-priority articles (last 7 days)
    recent_articles = _fetch_news_batch(
        symbol, company_name, 
        days=min(7, days), 
        page_size=50,
        sort_by='publishedAt',
        sources=priority_sources
    )
    all_articles.extend(recent_articles)
    print(f"Fetched {len(recent_articles)} recent priority articles")
    
    # Strategy 2: Get popular articles (sorted by popularity) from full period
    if days > 7:
        popular_articles = _fetch_news_batch(
            symbol, company_name,
            days=days,
            page_size=30,
            sort_by='popularity'
        )
        # Remove duplicates
        existing_urls = {article['url'] for article in all_articles}
        unique_popular = [a for a in popular_articles if a['url'] not in existing_urls]
        all_articles.extend(unique_popular)
        print(f"Fetched {len(unique_popular)} additional popular articles")
    
    # Strategy 3: Time-distributed sampling for longer periods
    if days > 14:
        distributed_articles = _fetch_time_distributed_articles(
            symbol, company_name, days, target_count=20
        )
        # Remove duplicates
        existing_urls = {article['url'] for article in all_articles}
        unique_distributed = [a for a in distributed_articles if a['url'] not in existing_urls]
        all_articles.extend(unique_distributed)
        print(f"Fetched {len(unique_distributed)} time-distributed articles")
    
    # Sort by date (most recent first) and limit total
    all_articles.sort(key=lambda x: x['publishedAt'], reverse=True)
    
    # Intelligent limit: more articles for longer periods
    max_articles = min(100, max(30, days * 2))  # 30-100 articles based on period
    final_articles = all_articles[:max_articles]
    
    print(f"Final selection: {len(final_articles)} articles from {len(all_articles)} total")
    return final_articles


def _fetch_news_batch(symbol: str, company_name: str, days: int, page_size: int = 30, 
                     sort_by: str = 'publishedAt', sources: List[str] = None) -> List[Dict[str, Any]]:
    """Fetch a batch of news articles with specific parameters"""
    try:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': f'"{company_name}" OR "{symbol}"',
            'apiKey': NEWS_API_KEY,
            'language': 'en',
            'sortBy': sort_by,
            'pageSize': min(page_size, 100),  # NewsAPI max is 100
            'from': (datetime.now() - timedelta(days=days)).isoformat()
        }
        
        # Add source filtering if specified
        if sources:
            # NewsAPI expects comma-separated source domains/names (Indian market focused)
            source_domains = []
            for source in sources:
                if source.lower() == 'reuters':
                    source_domains.append('reuters.com')
                elif source.lower() == 'bloomberg':
                    source_domains.append('bloomberg.com')
                elif source.lower() == 'economic times':
                    source_domains.append('economictimes.indiatimes.com')
                elif source.lower() == 'business standard':
                    source_domains.append('business-standard.com')
                elif source.lower() == 'mint':
                    source_domains.append('livemint.com')
                elif source.lower() == 'financial express':
                    source_domains.append('financialexpress.com')
                elif source.lower() == 'moneycontrol':
                    source_domains.append('moneycontrol.com')
                elif source.lower() == 'cnbc tv18':
                    source_domains.append('cnbctv18.com')
                elif source.lower() == 'business today':
                    source_domains.append('businesstoday.in')
                elif source.lower() == 'forbes india':
                    source_domains.append('forbesindia.com')
                elif source.lower() == 'yahoo finance':
                    source_domains.append('finance.yahoo.com')
                elif source.lower() == 'cnbc':
                    source_domains.append('cnbc.com')
            
            if source_domains:
                params['domains'] = ','.join(source_domains[:20])  # Limit to avoid URL length issues
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"NewsAPI batch request failed: {response.status_code}")
            return []
        
        data = response.json()
        
        if data.get('status') != 'ok':
            print(f"NewsAPI batch error: {data.get('message', 'Unknown error')}")
            return []
        
        return data.get('articles', [])
        
    except Exception as e:
        print(f"Error in news batch fetch: {str(e)}")
        return []


def _fetch_time_distributed_articles(symbol: str, company_name: str, days: int, target_count: int = 20) -> List[Dict[str, Any]]:
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
        
        segment_articles = _fetch_news_batch(
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
        print(f"Segment {i+1}: {len(filtered_articles)} articles")
    
    return articles

@mcp.tool()
def analyze_sentiment(batch_size: int = 10) -> str:
    """Analyze sentiment of news articles using Gemini AI"""
    print(f"CALLED: analyze_sentiment(batch_size={batch_size}) -> str:")
    
    try:
        if 'news_data' not in analysis_context:
            return "Error: No news data available. Please fetch news first."
        
        if not GEMINI_API_KEY or GEMINI_API_KEY == 'your-gemini-api-key-here':
            return "Error: Gemini API key not configured"
        
        articles = analysis_context['news_data']['articles']
        if not articles:
            return "Error: No articles to analyze"
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        sentiment_results = []
        
        # Process articles in batches
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            
            # Prepare batch prompt
            headlines = []
            for j, article in enumerate(batch):
                headlines.append(f"{j+1}. {article['title']}")
                if article['summary']:
                    headlines.append(f"   Summary: {article['summary'][:200]}...")
            
            prompt = f"""
            Analyze the sentiment of these financial news headlines and summaries. 
            For each item, provide sentiment as: positive, negative, or neutral.
            Also provide a confidence score from 0.0 to 1.0.
            
            Headlines:
            {chr(10).join(headlines)}
            
            Respond with JSON array format:
            [
                {{"item": 1, "sentiment": "positive", "confidence": 0.8, "reasoning": "brief explanation"}},
                ...
            ]
            """
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                
                # Parse response
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()
                
                batch_results = json.loads(response_text)
                
                # Merge with articles
                for j, result in enumerate(batch_results):
                    if j < len(batch):
                        article_with_sentiment = batch[j].copy()
                        article_with_sentiment.update({
                            'sentiment': result.get('sentiment', 'neutral'),
                            'confidence': result.get('confidence', 0.5),
                            'reasoning': result.get('reasoning', '')
                        })
                        sentiment_results.append(article_with_sentiment)
                
            except Exception as e:
                print(f"Error processing batch {i//batch_size + 1}: {e}")
                # Add neutral sentiment for failed batch
                for article in batch:
                    article_with_sentiment = article.copy()
                    article_with_sentiment.update({
                        'sentiment': 'neutral',
                        'confidence': 0.0,
                        'reasoning': f'Analysis failed: {str(e)}'
                    })
                    sentiment_results.append(article_with_sentiment)
        
        # Calculate sentiment statistics
        sentiments = [article['sentiment'] for article in sentiment_results]
        sentiment_counts = {
            'positive': sentiments.count('positive'),
            'negative': sentiments.count('negative'),
            'neutral': sentiments.count('neutral')
        }
        
        total = len(sentiment_results)
        sentiment_percentages = {
            'positive': (sentiment_counts['positive'] / total * 100) if total > 0 else 0,
            'negative': (sentiment_counts['negative'] / total * 100) if total > 0 else 0,
            'neutral': (sentiment_counts['neutral'] / total * 100) if total > 0 else 0
        }
        
        # Store results
        analysis_context['sentiment_data'] = {
            'articles': sentiment_results,
            'statistics': {
                'total_articles': total,
                'sentiment_counts': sentiment_counts,
                'sentiment_percentages': sentiment_percentages,
                'overall_sentiment': max(sentiment_counts, key=sentiment_counts.get)
            }
        }
        
        return f"Analyzed sentiment for {total} articles. Overall: {sentiment_percentages['positive']:.1f}% positive, {sentiment_percentages['negative']:.1f}% negative, {sentiment_percentages['neutral']:.1f}% neutral"
        
    except Exception as e:
        return f"Error analyzing sentiment: {str(e)}"

@mcp.tool()
def calculate_correlations() -> str:
    """Calculate correlations between news sentiment and stock price movements"""
    print("CALLED: calculate_correlations() -> str:")
    
    try:
        if 'stock_data' not in analysis_context or 'sentiment_data' not in analysis_context:
            return "Error: Missing stock data or sentiment data. Please fetch both first."
        
        # Use the analyze_correlations function (matching Week-3 pattern)
        correlation_results = analyze_correlations(
            analysis_context['stock_data']['candles'],
            analysis_context['sentiment_data']['articles']
        )
        
        # Store results in context
        analysis_context['correlation_data'] = correlation_results
        
        total = correlation_results['total_analyzed']
        rate = correlation_results['correlation_rate']
        strength = correlation_results['strength']
        
        return f"Calculated correlations for {total} data points. {rate:.1%} correlation match ({strength})"
        
    except Exception as e:
        return f"Error calculating correlations: {str(e)}"


def analyze_correlations(candles: List[Dict[str, Any]], news_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find correlations between news sentiment and price movements (matches Week-3 implementation)"""
    try:
        correlations = []
        
        # Convert candles to DataFrame for easier analysis
        df_data = []
        for candle in candles:
            df_data.append({
                'timestamp': pd.to_datetime(candle['timestamp']),
                'close': candle['close']
            })
        
        df = pd.DataFrame(df_data)
        df = df.set_index('timestamp').sort_index()
        df['price_change'] = df['close'].pct_change() * 100
        
        # Analyze each news item
        for news in news_analysis:
            try:
                news_date = pd.to_datetime(news['published'])
                
                # Find closest price data
                closest_idx = df.index.get_indexer([news_date], method='nearest')[0]
                if closest_idx >= 0 and closest_idx < len(df):
                    price_change = df.iloc[closest_idx]['price_change']
                    
                    # Determine if sentiment matches price movement
                    sentiment = news['sentiment']
                    correlation_match = False
                    
                    if sentiment == 'positive' and price_change > 0:
                        correlation_match = True
                    elif sentiment == 'negative' and price_change < 0:
                        correlation_match = True
                    elif sentiment == 'neutral' and abs(price_change) < 1:
                        correlation_match = True
                    
                    correlations.append({
                        'date': news['published'],
                        'headline': news['title'],
                        'sentiment': sentiment,
                        'confidence': news.get('confidence', 0.5),
                        'price_change': float(price_change) if not pd.isna(price_change) else 0.0,
                        'correlation_match': correlation_match
                    })
            except Exception as e:
                print(f"Error processing news item for correlation: {e}")
                continue
        
        # Calculate overall correlation metrics
        matches = sum(1 for c in correlations if c['correlation_match'])
        total = len(correlations)
        correlation_rate = matches / total if total > 0 else 0
        
        # Determine correlation strength (matching Week-3 thresholds)
        if correlation_rate >= 0.7:
            strength = "Strong"
        elif correlation_rate >= 0.5:
            strength = "Moderate"
        elif correlation_rate >= 0.3:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        return {
            'correlations': correlations,
            'correlation_rate': correlation_rate,
            'strength': strength,
            'total_analyzed': total
        }
        
    except Exception as e:
        print(f"Error in correlation analysis: {str(e)}")
        return {
            'correlations': [],
            'correlation_rate': 0.0,
            'strength': 'Unknown',
            'total_analyzed': 0
        }

@mcp.tool()
def run_backtest(initial_capital: float = 10000.0, confidence_threshold: float = 0.6) -> str:
    """Run sentiment-based trading strategy backtest"""
    print(f"CALLED: run_backtest(initial_capital={initial_capital}, confidence_threshold={confidence_threshold}) -> str:")
    
    try:
        if 'correlation_data' not in analysis_context or 'stock_data' not in analysis_context:
            return "Error: Missing correlation data or stock data. Please run correlation analysis first."
        
        # Use the backtest_engine function (matching Week-3 pattern)
        backtest_results = backtest_engine(
            analysis_context['stock_data']['candles'],
            analysis_context['correlation_data']['correlations'],
            initial_capital,
            confidence_threshold
        )
        
        # Store results in context
        analysis_context['backtest_data'] = backtest_results
        
        total_return = backtest_results['total_pnl']
        total_trades = backtest_results['total_trades']
        win_rate = backtest_results['win_rate']
        
        return f"Backtest completed: {total_return:.2f}% return, {total_trades} trades, {win_rate:.1%} win rate"
        
    except Exception as e:
        return f"Error running backtest: {str(e)}"


def backtest_engine(candles: List[Dict[str, Any]], correlations: List[Dict[str, Any]], 
                   initial_capital: float = 10000.0, confidence_threshold: float = 0.6) -> Dict[str, Any]:
    """Run simple sentiment-based trading strategy backtest (matches Week-3 implementation)"""
    try:
        # Convert to DataFrame
        df_data = []
        for candle in candles:
            df_data.append({
                'timestamp': pd.to_datetime(candle['timestamp']),
                'close': candle['close']
            })
        
        df = pd.DataFrame(df_data)
        df = df.set_index('timestamp').sort_index()
        
        # Initialize backtest variables
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0
        trades = []
        portfolio_value = initial_capital
        
        # Process each correlation/signal
        for corr in correlations:
            try:
                signal_date = pd.to_datetime(corr['date'])
                sentiment = corr['sentiment']
                confidence = corr['confidence']
                
                # Find price at signal time
                closest_idx = df.index.get_indexer([signal_date], method='nearest')[0]
                if closest_idx >= 0 and closest_idx < len(df):
                    current_price = df.iloc[closest_idx]['close']
                    
                    # Simple strategy: Buy on positive sentiment, sell on negative
                    if sentiment == 'positive' and confidence > confidence_threshold and position <= 0:
                        # Enter long position
                        if position == -1:  # Close short first
                            pnl = (entry_price - current_price) / entry_price
                            trades.append({
                                'type': 'close_short',
                                'date': signal_date,
                                'price': current_price,
                                'pnl': pnl
                            })
                            portfolio_value *= (1 + pnl)
                        
                        # Open long
                        position = 1
                        entry_price = current_price
                        trades.append({
                            'type': 'buy',
                            'date': signal_date,
                            'price': current_price,
                            'pnl': 0
                        })
                        
                    elif sentiment == 'negative' and confidence > confidence_threshold and position >= 0:
                        # Enter short position
                        if position == 1:  # Close long first
                            pnl = (current_price - entry_price) / entry_price
                            trades.append({
                                'type': 'close_long',
                                'date': signal_date,
                                'price': current_price,
                                'pnl': pnl
                            })
                            portfolio_value *= (1 + pnl)
                        
                        # Open short
                        position = -1
                        entry_price = current_price
                        trades.append({
                            'type': 'sell',
                            'date': signal_date,
                            'price': current_price,
                            'pnl': 0
                        })
            except Exception as e:
                print(f"Error processing signal for backtest: {e}")
                continue
        
        # Close final position
        if position != 0 and len(df) > 0:
            final_price = df.iloc[-1]['close']
            if position == 1:
                pnl = (final_price - entry_price) / entry_price
            else:
                pnl = (entry_price - final_price) / entry_price
            
            trades.append({
                'type': 'close_final',
                'date': df.index[-1],
                'price': final_price,
                'pnl': pnl
            })
            portfolio_value *= (1 + pnl)
        
        # Calculate metrics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        total_trades = [t for t in trades if t['pnl'] != 0]
        
        win_rate = len(winning_trades) / len(total_trades) if total_trades else 0
        total_return = (portfolio_value - initial_capital) / initial_capital
        
        # Simple Sharpe ratio calculation
        returns = [t['pnl'] for t in total_trades]
        if returns:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': len(total_trades),
            'winning_trades': len(winning_trades),
            'win_rate': win_rate,
            'total_pnl': total_return * 100,
            'sharpe_ratio': sharpe_ratio,
            'final_portfolio_value': portfolio_value,
            'trades': trades
        }
        
    except Exception as e:
        print(f"Error in backtesting: {str(e)}")
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'final_portfolio_value': initial_capital,
            'trades': []
        }

@mcp.tool()
def generate_analysis_report() -> str:
    """Generate a comprehensive analysis report"""
    print("CALLED: generate_analysis_report() -> str:")
    
    try:
        if not analysis_context:
            return "Error: No analysis data available. Please run the analysis pipeline first."
        
        # Use Gemini to generate comprehensive report
        if not GEMINI_API_KEY or GEMINI_API_KEY == 'your-gemini-api-key-here':
            return "Error: Gemini API key not configured for report generation"
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Prepare data summary for the model
        data_summary = {
            'stock_info': analysis_context.get('stock_data', {}),
            'news_summary': analysis_context.get('news_data', {}),
            'sentiment_summary': analysis_context.get('sentiment_data', {}).get('statistics', {}),
            'correlation_summary': analysis_context.get('correlation_data', {}).get('statistics', {}),
            'backtest_summary': analysis_context.get('backtest_data', {})
        }
        
        prompt = f"""
        Generate a comprehensive stock analysis report based on the following data:
        
        Stock Data: {json.dumps(data_summary['stock_info'], indent=2)}
        
        News Summary: {json.dumps(data_summary['news_summary'], indent=2)}
        
        Sentiment Analysis: {json.dumps(data_summary['sentiment_summary'], indent=2)}
        
        Correlation Analysis: {json.dumps(data_summary['correlation_summary'], indent=2)}
        
        Backtest Results: {json.dumps(data_summary['backtest_summary'], indent=2)}
        
        Please provide:
        1. Executive Summary
        2. Stock Performance Analysis
        3. News Sentiment Analysis
        4. Correlation Insights
        5. Trading Strategy Performance
        6. Risk Assessment
        7. Recommendations
        
        Format the report professionally with clear sections and actionable insights.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        report = response.text.strip()
        
        # Store the report
        analysis_context['final_report'] = {
            'report': report,
            'generated_at': datetime.now().isoformat(),
            'data_summary': data_summary
        }
        
        return f"Analysis report generated successfully ({len(report)} characters)"
        
    except Exception as e:
        return f"Error generating report: {str(e)}"

@mcp.tool()
def get_analysis_summary() -> str:
    """Get a summary of all analysis results"""
    print("CALLED: get_analysis_summary() -> str:")
    
    try:
        if not analysis_context:
            return "No analysis data available"
        
        summary_parts = []
        
        # Stock data summary
        if 'stock_data' in analysis_context:
            stock = analysis_context['stock_data']
            summary_parts.append(f"📊 Stock: {stock['symbol']} - Current: ${stock['current_price']:.2f} ({stock['price_change']:+.2f}%)")
        
        # News summary
        if 'news_data' in analysis_context:
            news = analysis_context['news_data']
            summary_parts.append(f"📰 News: {news['total_articles']} articles analyzed")
        
        # Sentiment summary
        if 'sentiment_data' in analysis_context:
            sentiment = analysis_context['sentiment_data']['statistics']
            summary_parts.append(f"🧠 Sentiment: {sentiment['sentiment_percentages']['positive']:.1f}% positive, {sentiment['sentiment_percentages']['negative']:.1f}% negative")
        
        # Correlation summary
        if 'correlation_data' in analysis_context:
            corr_data = analysis_context['correlation_data']
            if 'statistics' in corr_data:
                corr = corr_data['statistics']
                summary_parts.append(f"🔗 Correlation: {corr['correlation_percentage']:.1f}% match ({corr['correlation_strength']})")
            else:
                # Handle the new correlation data format
                rate = corr_data.get('correlation_rate', 0) * 100
                strength = corr_data.get('strength', 'Unknown')
                summary_parts.append(f"🔗 Correlation: {rate:.1f}% match ({strength})")
        
        # Backtest summary
        if 'backtest_data' in analysis_context:
            backtest = analysis_context['backtest_data']
            summary_parts.append(f"📈 Backtest: {backtest['total_return']:+.2f}% return, {backtest['win_rate']:.1%} win rate")
        
        # Technical indicators summary
        if 'rsi_data' in analysis_context:
            rsi = analysis_context['rsi_data']
            rsi_signal = "Overbought" if rsi['current_rsi'] > 70 else ("Oversold" if rsi['current_rsi'] < 30 else "Neutral")
            summary_parts.append(f"📈 RSI: {rsi['current_rsi']:.1f} ({rsi_signal})")
        
        if 'macd_data' in analysis_context:
            macd = analysis_context['macd_data']
            macd_signal = "Bullish" if macd['current_macd'] > macd['current_signal'] else "Bearish"
            summary_parts.append(f"📊 MACD: {macd_signal} trend")
        
        if 'bollinger_data' in analysis_context:
            bb = analysis_context['bollinger_data']
            bb_signal = "Upper Band" if bb['current_position'] > 0.8 else ("Lower Band" if bb['current_position'] < 0.2 else "Normal Range")
            summary_parts.append(f"📉 Bollinger: {bb_signal}")
        
        # Algo strategy summary
        if 'algo_strategy' in analysis_context:
            strategy = analysis_context['algo_strategy']
            summary_parts.append(f"🤖 Algo Strategy: {strategy['target_cagr']}% CAGR target ({strategy['risk_tolerance']} risk)")
        
        # Report status
        if 'final_report' in analysis_context:
            summary_parts.append("📋 Final report generated")
        
        return "\n".join(summary_parts) if summary_parts else "No analysis completed yet"
        
    except Exception as e:
        return f"Error getting summary: {str(e)}"

@mcp.tool()
def parse_query(query: str) -> str:
    """Parse natural language query to extract stock symbol and intent"""
    print(f"CALLED: parse_query(query='{query}') -> str:")
    
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY == 'your-gemini-api-key-here':
            return "Error: Gemini API key not configured for query parsing"
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are a financial query parser. Think step-by-step to extract structured information from the user's query.
        
        REASONING PROCESS:
        1. Identify the company/stock mentioned in the query
        2. Determine what type of analysis is being requested
        3. Infer appropriate timeframe based on analysis type
        4. Assess your confidence in the parsing
        
        Query to parse: "{query}"
        
        STEP-BY-STEP ANALYSIS:
        Step 1: Company Identification
        - Look for company names, stock symbols, or business references
        - Convert to proper stock symbol format using mappings below
        
        Step 2: Task Classification
        - Sentiment: "analyze sentiment", "news analysis", "what's happening"
        - Correlation: "correlation", "news impact", "price relationship"
        - Technical: "RSI", "MACD", "technical analysis", "indicators"
        - Strategy: "algo", "strategy", "CAGR", "trading plan"
        - Backtest: "backtest", "test strategy", "historical performance"
        - Full: "full analysis", "complete analysis", "comprehensive"
        
        Step 3: Timeframe Selection
        - Sentiment analysis: "1h" or "1d"
        - Technical analysis: "1h" or "1d"
        - Strategy development: "1d"
        - Quick queries: "1h"
        
        SYMBOL MAPPINGS:
        Indian Companies (.NS suffix):
        - Reliance Industries → RELIANCE.NS
        - HDFC Bank → HDFCBANK.NS
        - Tata Consultancy Services, TCS → TCS.NS
        - Infosys → INFY.NS
        - Wipro → WIPRO.NS
        - ICICI Bank → ICICIBANK.NS
        - State Bank of India, SBI → SBIN.NS
        - Bharti Airtel → BHARTIARTL.NS
        - ITC → ITC.NS
        - Larsen & Toubro, L&T → LT.NS
        - Hindustan Unilever, HUL → HINDUNILVR.NS
        - Maruti Suzuki → MARUTI.NS
        - Asian Paints → ASIANPAINT.NS
        - Bajaj Finance → BAJFINANCE.NS
        - Kotak Mahindra Bank → KOTAKBANK.NS
        
        US Companies (direct symbols):
        - Tesla → TSLA
        - Apple → AAPL
        - Microsoft → MSFT
        - Google, Alphabet → GOOGL
        - Amazon → AMZN
        - NVIDIA → NVDA
        - Meta, Facebook → META
        
        OUTPUT FORMAT - Return ONLY valid JSON with these exact fields:
        {{
            "symbol": "STOCK_SYMBOL_HERE",
            "timeframe": "1h_OR_1d_HERE", 
            "task": "TASK_TYPE_HERE",
            "analysis_type": "comprehensive",
            "confidence": 0.0_TO_1.0_HERE
        }}
        
        SELF-CHECK before responding:
        - Is the symbol in correct format (e.g., RELIANCE.NS, AAPL)?
        - Is the task accurately identified from the query?
        - Is the confidence score realistic (0.9+ for clear queries, 0.5-0.8 for ambiguous)?
        - Is the JSON format valid and parseable?
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        # Clean and parse response
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        parsed_data = json.loads(response_text)
        
        # Store parsed query context
        analysis_context['parsed_query'] = {
            'original_query': query,
            'symbol': parsed_data.get('symbol', 'UNKNOWN'),
            'timeframe': parsed_data.get('timeframe', '1h'),
            'task': parsed_data.get('task', 'full_analysis'),
            'analysis_type': parsed_data.get('analysis_type', 'comprehensive'),
            'confidence': float(parsed_data.get('confidence', 0.5))
        }
        
        return f"Query parsed successfully: {parsed_data.get('symbol', 'UNKNOWN')} for {parsed_data.get('task', 'analysis')} (confidence: {parsed_data.get('confidence', 0.5):.1f})"
        
    except Exception as e:
        return f"Error parsing query: {str(e)}"


@mcp.tool()
def calculate_rsi(period: int = 14) -> str:
    """Calculate Relative Strength Index (RSI) for the stock data"""
    print(f"CALLED: calculate_rsi(period={period}) -> str:")
    
    try:
        if 'stock_data' not in analysis_context:
            return "Error: No stock data available. Please fetch stock data first."
        
        candles = analysis_context['stock_data']['candles']
        if len(candles) < period + 1:
            return f"Error: Need at least {period + 1} data points for RSI calculation"
        
        # Calculate RSI
        closes = [candle['close'] for candle in candles]
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi_values = []
        
        # Calculate RSI for each point
        for i in range(period, len(deltas)):
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append({
                'timestamp': candles[i+1]['timestamp'],
                'rsi': rsi,
                'price': candles[i+1]['close']
            })
            
            # Update averages using Wilder's smoothing
            if i < len(deltas) - 1:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # Store RSI data
        analysis_context['rsi_data'] = {
            'period': period,
            'values': rsi_values,
            'current_rsi': rsi_values[-1]['rsi'] if rsi_values else 0,
            'overbought_level': 70,
            'oversold_level': 30
        }
        
        current_rsi = rsi_values[-1]['rsi'] if rsi_values else 0
        signal = "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
        
        return f"RSI({period}) calculated: Current RSI = {current_rsi:.2f} ({signal}). {len(rsi_values)} data points generated."
        
    except Exception as e:
        return f"Error calculating RSI: {str(e)}"


@mcp.tool()
def calculate_macd(fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> str:
    """Calculate MACD (Moving Average Convergence Divergence) indicator"""
    print(f"CALLED: calculate_macd(fast_period={fast_period}, slow_period={slow_period}, signal_period={signal_period}) -> str:")
    
    try:
        if 'stock_data' not in analysis_context:
            return "Error: No stock data available. Please fetch stock data first."
        
        candles = analysis_context['stock_data']['candles']
        if len(candles) < slow_period + signal_period:
            return f"Error: Need at least {slow_period + signal_period} data points for MACD calculation"
        
        closes = [candle['close'] for candle in candles]
        
        # Calculate EMAs
        def calculate_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = [sum(data[:period]) / period]  # First EMA is SMA
            
            for i in range(period, len(data)):
                ema.append((data[i] * multiplier) + (ema[-1] * (1 - multiplier)))
            
            return ema
        
        # Calculate fast and slow EMAs
        fast_ema = calculate_ema(closes, fast_period)
        slow_ema = calculate_ema(closes, slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = []
        start_idx = slow_period - fast_period
        
        for i in range(len(slow_ema)):
            macd_line.append(fast_ema[i + start_idx] - slow_ema[i])
        
        # Calculate signal line (EMA of MACD line)
        signal_line = calculate_ema(macd_line, signal_period)
        
        # Calculate histogram (MACD - Signal)
        histogram = []
        start_signal_idx = len(macd_line) - len(signal_line)
        
        for i in range(len(signal_line)):
            histogram.append(macd_line[i + start_signal_idx] - signal_line[i])
        
        # Prepare results
        macd_values = []
        result_start_idx = slow_period + signal_period - 1
        
        for i in range(len(histogram)):
            idx = result_start_idx + i
            if idx < len(candles):
                macd_values.append({
                    'timestamp': candles[idx]['timestamp'],
                    'macd': macd_line[start_signal_idx + i],
                    'signal': signal_line[i],
                    'histogram': histogram[i],
                    'price': candles[idx]['close']
                })
        
        # Store MACD data
        analysis_context['macd_data'] = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'values': macd_values,
            'current_macd': macd_values[-1]['macd'] if macd_values else 0,
            'current_signal': macd_values[-1]['signal'] if macd_values else 0,
            'current_histogram': macd_values[-1]['histogram'] if macd_values else 0
        }
        
        if macd_values:
            current = macd_values[-1]
            signal_status = "Bullish" if current['macd'] > current['signal'] else "Bearish"
            trend = "Strengthening" if current['histogram'] > 0 else "Weakening"
            
            return f"MACD({fast_period},{slow_period},{signal_period}) calculated: MACD={current['macd']:.4f}, Signal={current['signal']:.4f}, Status={signal_status} ({trend})"
        else:
            return "MACD calculated but no valid data points generated"
        
    except Exception as e:
        return f"Error calculating MACD: {str(e)}"


@mcp.tool()
def calculate_bollinger_bands(period: int = 20, std_dev: float = 2.0) -> str:
    """Calculate Bollinger Bands indicator"""
    print(f"CALLED: calculate_bollinger_bands(period={period}, std_dev={std_dev}) -> str:")
    
    try:
        if 'stock_data' not in analysis_context:
            return "Error: No stock data available. Please fetch stock data first."
        
        candles = analysis_context['stock_data']['candles']
        if len(candles) < period:
            return f"Error: Need at least {period} data points for Bollinger Bands calculation"
        
        closes = [candle['close'] for candle in candles]
        
        bollinger_values = []
        
        for i in range(period - 1, len(closes)):
            # Calculate moving average
            window = closes[i - period + 1:i + 1]
            sma = sum(window) / period
            
            # Calculate standard deviation
            variance = sum((x - sma) ** 2 for x in window) / period
            std = variance ** 0.5
            
            # Calculate bands
            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)
            
            # Calculate position within bands
            current_price = closes[i]
            band_width = upper_band - lower_band
            position = (current_price - lower_band) / band_width if band_width > 0 else 0.5
            
            bollinger_values.append({
                'timestamp': candles[i]['timestamp'],
                'price': current_price,
                'sma': sma,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'band_width': band_width,
                'position': position  # 0 = at lower band, 1 = at upper band, 0.5 = at middle
            })
        
        # Store Bollinger Bands data
        analysis_context['bollinger_data'] = {
            'period': period,
            'std_dev': std_dev,
            'values': bollinger_values,
            'current_position': bollinger_values[-1]['position'] if bollinger_values else 0.5
        }
        
        if bollinger_values:
            current = bollinger_values[-1]
            if current['position'] > 0.8:
                signal = "Near Upper Band (Overbought)"
            elif current['position'] < 0.2:
                signal = "Near Lower Band (Oversold)"
            else:
                signal = "Within Normal Range"
            
            return f"Bollinger Bands({period},{std_dev}) calculated: Price=₹{current['price']:.2f}, Position={current['position']:.2%} ({signal})"
        else:
            return "Bollinger Bands calculated but no valid data points generated"
        
    except Exception as e:
        return f"Error calculating Bollinger Bands: {str(e)}"


@mcp.tool()
def generate_algo_strategy(target_cagr: float, risk_tolerance: str = "medium") -> str:
    """Generate algorithmic trading strategy to achieve target CAGR"""
    print(f"CALLED: generate_algo_strategy(target_cagr={target_cagr}, risk_tolerance='{risk_tolerance}') -> str:")
    
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY == 'your-gemini-api-key-here':
            return "Error: Gemini API key not configured for strategy generation"
        
        # Check available data
        available_data = []
        if 'stock_data' in analysis_context:
            available_data.append("Stock Price Data")
        if 'news_data' in analysis_context:
            available_data.append("News Sentiment Data")
        if 'correlation_data' in analysis_context:
            available_data.append("News-Price Correlations")
        if 'rsi_data' in analysis_context:
            available_data.append("RSI Technical Indicator")
        if 'macd_data' in analysis_context:
            available_data.append("MACD Technical Indicator")
        if 'bollinger_data' in analysis_context:
            available_data.append("Bollinger Bands")
        
        if not available_data:
            return "Error: No analysis data available. Please run some analysis first (stock data, indicators, sentiment, etc.)"
        
        # Get current market data for context
        symbol = analysis_context.get('stock_data', {}).get('symbol', 'UNKNOWN')
        current_price = analysis_context.get('stock_data', {}).get('current_price', 0)
        
        # Prepare technical indicator summary
        technical_summary = {}
        if 'rsi_data' in analysis_context:
            rsi = analysis_context['rsi_data']
            technical_summary['RSI'] = f"Current: {rsi['current_rsi']:.2f}"
        
        if 'macd_data' in analysis_context:
            macd = analysis_context['macd_data']
            technical_summary['MACD'] = f"MACD: {macd['current_macd']:.4f}, Signal: {macd['current_signal']:.4f}"
        
        if 'bollinger_data' in analysis_context:
            bb = analysis_context['bollinger_data']
            technical_summary['Bollinger'] = f"Position: {bb['current_position']:.2%}"
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        prompt = f"""
        You are an expert algorithmic trading strategist. Think step-by-step to create a comprehensive trading strategy that can realistically achieve the target CAGR.
        
        REASONING PROCESS:
        1. Analyze the target CAGR and assess its feasibility
        2. Evaluate available data and current market conditions
        3. Design entry/exit rules based on available indicators
        4. Calculate position sizing for target returns
        5. Implement risk management for sustainability
        6. Validate strategy logic and expectations
        
        TARGET ANALYSIS:
        - Target CAGR: {target_cagr}% annually
        - Risk Tolerance: {risk_tolerance}
        - Stock: {symbol} (Current Price: ₹{current_price:.2f})
        - Available Data: {', '.join(available_data)}
        
        TECHNICAL CONTEXT:
        {json.dumps(technical_summary, indent=2)}
        
        STEP-BY-STEP STRATEGY DEVELOPMENT:
        
        Step 1: FEASIBILITY ASSESSMENT
        - Is {target_cagr}% CAGR realistic for this stock and risk level?
        - What market conditions are required to achieve this target?
        - How does this compare to historical performance?
        
        Step 2: STRATEGY TYPE SELECTION
        Based on risk tolerance:
        - Conservative ({risk_tolerance}): Focus on capital preservation, lower frequency
        - Medium ({risk_tolerance}): Balanced risk/reward, moderate frequency  
        - Aggressive ({risk_tolerance}): Higher risk for higher returns, active trading
        
        Step 3: ENTRY SIGNAL DESIGN
        Using available indicators, create specific entry conditions:
        - Technical thresholds (RSI, MACD, Bollinger Bands)
        - Sentiment triggers (if news data available)
        - Market regime filters
        
        Step 4: EXIT STRATEGY DESIGN
        Calculate specific exit rules:
        - Profit targets: What % gain per trade achieves {target_cagr}% annually?
        - Stop losses: Maximum acceptable loss per trade
        - Time-based exits: Maximum holding period
        
        Step 5: POSITION SIZING CALCULATION
        Mathematical approach to position sizing:
        - Risk per trade: What % of portfolio to risk?
        - Kelly Criterion or fixed fractional sizing
        - Maximum exposure limits
        
        Step 6: RISK MANAGEMENT FRAMEWORK
        Comprehensive risk controls:
        - Maximum drawdown limits
        - Daily/monthly loss limits
        - Correlation and concentration limits
        
        Step 7: IMPLEMENTATION PLAN
        Practical execution details:
        - Trading frequency and timing
        - Rebalancing schedule
        - Performance monitoring and adjustment triggers
        
        OUTPUT FORMAT:
        Provide a detailed, actionable strategy with specific numbers and thresholds. Include:
        
        ## STRATEGY OVERVIEW
        - Strategy Name: [Descriptive name]
        - Target vs Expected Return: {target_cagr}% target vs X% expected
        - Risk Assessment: Maximum drawdown, volatility expectations
        
        ## ENTRY CONDITIONS (Specific Thresholds)
        - Technical Indicators: Exact RSI/MACD/Bollinger levels
        - Sentiment Triggers: Specific sentiment scores (if available)
        - Market Filters: Trend, volatility, volume conditions
        
        ## EXIT CONDITIONS (Specific Rules)
        - Profit Target: X% gain per trade
        - Stop Loss: Y% maximum loss
        - Time Exit: Z days maximum hold
        
        ## POSITION SIZING (Mathematical Formula)
        - Risk Per Trade: X% of portfolio
        - Position Size Formula: [Specific calculation]
        - Maximum Exposure: Y% of total capital
        
        ## RISK MANAGEMENT (Specific Limits)
        - Daily Loss Limit: X%
        - Monthly Loss Limit: Y%
        - Maximum Drawdown: Z%
        
        ## IMPLEMENTATION DETAILS
        - Trading Frequency: X trades per month
        - Rebalancing: Every X days/weeks
        - Monitoring: Key metrics to track
        
        ## BACKTESTING EXPECTATIONS
        - Expected Win Rate: X%
        - Average Profit Per Trade: Y%
        - Maximum Consecutive Losses: Z trades
        
        SELF-CHECK before finalizing:
        - Are the numbers realistic and achievable?
        - Is the risk management comprehensive?
        - Are the entry/exit rules specific and actionable?
        - Does the strategy align with the risk tolerance?
        - Can this realistically achieve {target_cagr}% CAGR?
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        strategy = response.text.strip()
        
        # Store the generated strategy
        analysis_context['algo_strategy'] = {
            'target_cagr': target_cagr,
            'risk_tolerance': risk_tolerance,
            'symbol': symbol,
            'strategy': strategy,
            'available_data': available_data,
            'technical_summary': technical_summary,
            'generated_at': datetime.now().isoformat()
        }
        
        return f"Algorithmic trading strategy generated for {target_cagr}% CAGR target. Strategy includes entry/exit rules, position sizing, and risk management. ({len(strategy)} characters)"
        
    except Exception as e:
        return f"Error generating algo strategy: {str(e)}"


@mcp.tool()
def clear_analysis_data() -> str:
    """Clear all stored analysis data"""
    print("CALLED: clear_analysis_data() -> str:")
    
    global analysis_context
    analysis_context.clear()
    return "Analysis data cleared successfully"

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING THE SERVER AT AMAZING LOCATION")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
#!/usr/bin/env python3
"""
Week-6 Action Layer MCP Server
Executes analysis operations with proper architecture - receives data as parameters
"""

from mcp.server.fastmcp import FastMCP
import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from google import genai
import json
import os
import logging
from dotenv import load_dotenv

from models import (
    StockData, NewsArticle, SentimentResult, TechnicalAnalysisResult,
    CorrelationResult, BacktestResult, StockDataResult, NewsDataResult,
    ReportResult, FetchStockDataInput, FetchNewsDataInput, AnalyzeSentimentInput,
    CalculateRSIInput, CalculateCorrelationsInput, RunBacktestInput, GenerateReportInput,
    TechnicalIndicator, CorrelationData
)

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("StockAnalysisActionServer")

# Global configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Configure logging - suppress third-party library logs
logging.basicConfig(level=logging.INFO)
logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Initialize Gemini client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

@mcp.tool()
def fetch_stock_data(input_data: FetchStockDataInput) -> StockDataResult:
    """Fetch stock price data from Yahoo Finance"""
    try:
        logger.info(f"Fetching stock data for {input_data.symbol}")
        
        # Create ticker object
        ticker = yf.Ticker(input_data.symbol)
        
        # Fetch historical data
        hist = ticker.history(period=input_data.period, interval=input_data.interval)
        
        if hist.empty:
            raise ValueError(f"No data found for symbol {input_data.symbol}")
        
        # Convert to Pydantic models
        stock_data_points = []
        for timestamp, row in hist.iterrows():
            stock_data_points.append(StockData(
                symbol=input_data.symbol,
                timestamp=timestamp,
                open=float(row['Open']),
                high=float(row['High']),
                low=float(row['Low']),
                close=float(row['Close']),
                volume=int(row['Volume'])
            ))
        
        # Calculate basic metrics
        current_price = stock_data_points[-1].close
        previous_price = stock_data_points[0].close
        price_change_percent = ((current_price - previous_price) / previous_price) * 100
        
        return StockDataResult(
            symbol=input_data.symbol,
            data_points=len(stock_data_points),
            current_price=current_price,
            price_change_percent=price_change_percent,
            timeframe=input_data.interval,
            period=input_data.period,
            message=f"Stock data fetched: {len(stock_data_points)} data points, current price: ${current_price:.2f} ({price_change_percent:+.2f}%)",
            stock_data=stock_data_points
        )
        
    except Exception as e:
        logger.error(f"Error fetching stock data: {str(e)}")
        raise

@mcp.tool()
def fetch_news_data(input_data: FetchNewsDataInput) -> NewsDataResult:
    """Fetch news data using intelligent sampling strategy"""
    try:
        if not NEWS_API_KEY:
            raise ValueError("NewsAPI key not configured")
        
        logger.info(f"Fetching news data for {input_data.symbol} using intelligent sampling")
        
        # Get company info for better search
        ticker = yf.Ticker(input_data.symbol)
        info = ticker.info
        company_name = info.get('longName', input_data.symbol.replace('.NS', '').replace('.BO', ''))
        
        # Search symbol without exchange suffix
        search_symbol = input_data.symbol.replace('.NS', '').replace('.BO', '')
        
        # Use intelligent sampling strategy
        all_articles = fetch_with_intelligent_sampling(search_symbol, company_name, input_data.days)
        
        if not all_articles:
            raise ValueError(f"No news articles found for {company_name} ({input_data.symbol})")
        
        # Process and convert to Pydantic models
        news_articles = []
        sources = set()
        
        for article in all_articles:
            title = article.get('title', '').strip()
            description = article.get('description', '').strip()
            
            if title and title.lower() != '[removed]' and len(title) >= 10:
                source_name = article.get('source', {}).get('name', 'Unknown')
                sources.add(source_name)
                
                news_articles.append(NewsArticle(
                    title=title,
                    summary=description,
                    published=article.get('publishedAt', ''),
                    source=source_name,
                    url=article.get('url', '')
                ))
        
        return NewsDataResult(
            symbol=input_data.symbol,
            articles_count=len(news_articles),
            date_range=f"Last {input_data.days} days",
            sources=list(sources),
            message=f"News data fetched: {len(news_articles)} articles from {len(sources)} sources",
            news_articles=news_articles
        )
        
    except Exception as e:
        logger.error(f"Error fetching news data: {str(e)}")
        raise

@mcp.tool()
def analyze_sentiment(input_data: AnalyzeSentimentInput) -> SentimentResult:
    """Analyze sentiment of news articles using Gemini AI"""
    try:
        if not input_data.news_articles:
            raise ValueError("No news articles provided for sentiment analysis")
        
        if not client:
            raise ValueError("Gemini API key not configured")
        
        logger.info(f"Analyzing sentiment for {len(input_data.news_articles)} articles")
        
        # Process articles in batches to avoid token limits
        all_sentiments = []
        
        for i in range(0, len(input_data.news_articles), input_data.batch_size):
            batch = input_data.news_articles[i:i + input_data.batch_size]
            batch_sentiments = analyze_sentiment_batch(batch)
            all_sentiments.extend(batch_sentiments)
        
        # Calculate statistics
        positive_count = sum(1 for s in all_sentiments if s == "positive")
        negative_count = sum(1 for s in all_sentiments if s == "negative")
        neutral_count = sum(1 for s in all_sentiments if s == "neutral")
        
        total = len(all_sentiments)
        if total == 0:
            raise ValueError("No valid sentiment analysis results")
        
        positive_percent = (positive_count / total) * 100
        negative_percent = (negative_count / total) * 100
        neutral_percent = (neutral_count / total) * 100
        
        # Determine overall sentiment
        if positive_percent > negative_percent and positive_percent > neutral_percent:
            overall_sentiment = "positive"
            confidence = positive_percent / 100
        elif negative_percent > positive_percent and negative_percent > neutral_percent:
            overall_sentiment = "negative"
            confidence = negative_percent / 100
        else:
            overall_sentiment = "neutral"
            confidence = neutral_percent / 100
        
        # Return result directly - no global storage
        return SentimentResult(
            total_articles=total,
            positive_percent=positive_percent,
            negative_percent=negative_percent,
            neutral_percent=neutral_percent,
            overall_sentiment=overall_sentiment,
            confidence=confidence,
            message=f"Sentiment analysis completed: {overall_sentiment} ({confidence:.1%} confidence) - {positive_percent:.1f}% positive, {negative_percent:.1f}% negative"
        )
        
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        raise

@mcp.tool()
def calculate_rsi(input_data: CalculateRSIInput) -> TechnicalAnalysisResult:
    """Calculate RSI technical indicator"""
    try:
        if not input_data.stock_data:
            raise ValueError("No stock data provided for RSI calculation")
        
        if len(input_data.stock_data) < input_data.period + 1:
            raise ValueError(f"Insufficient data for RSI calculation. Need at least {input_data.period + 1} data points, got {len(input_data.stock_data)}")
        
        logger.info(f"Calculating RSI with period {input_data.period} for {len(input_data.stock_data)} data points")
        
        # Extract closing prices
        closes = [data.close for data in input_data.stock_data]
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        # Calculate initial average gain and loss
        avg_gain = sum(gains[:input_data.period]) / input_data.period
        avg_loss = sum(losses[:input_data.period]) / input_data.period
        
        # Calculate RSI for each subsequent period
        rsi_values = []
        
        for i in range(input_data.period, len(gains)):
            # Smoothed moving average (Wilder's smoothing)
            avg_gain = ((avg_gain * (input_data.period - 1)) + gains[i]) / input_data.period
            avg_loss = ((avg_loss * (input_data.period - 1)) + losses[i]) / input_data.period
            
            # Calculate RSI
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        if not rsi_values:
            raise ValueError("Could not calculate RSI values")
        
        current_rsi = rsi_values[-1]
        
        # Determine signal
        if current_rsi > 70:
            signal = "overbought"
        elif current_rsi < 30:
            signal = "oversold"
        else:
            signal = "neutral"
        
        return TechnicalAnalysisResult(
            indicator_name="RSI",
            current_value=round(current_rsi, 2),
            signal=signal,
            data_points=len(rsi_values),
            parameters={"period": input_data.period},
            message=f"RSI calculated: {current_rsi:.2f} ({signal} signal) using {len(rsi_values)} data points"
        )
        
    except Exception as e:
        logger.error(f"Error calculating RSI: {str(e)}")
        raise

@mcp.tool()
def calculate_correlations(input_data: CalculateCorrelationsInput) -> CorrelationResult:
    """Calculate news-price correlations"""
    try:
        if not input_data.stock_data:
            raise ValueError("No stock data provided for correlation analysis")
        
        if not input_data.sentiment_summary:
            raise ValueError("No sentiment analysis results provided for correlation analysis")
        
        logger.info(f"Calculating correlations between sentiment and price movements")
        
        # Extract price changes from stock data
        closes = [data.close for data in input_data.stock_data]
        price_changes = []
        
        for i in range(1, len(closes)):
            change_percent = ((closes[i] - closes[i-1]) / closes[i-1]) * 100
            price_changes.append(change_percent)
        
        if len(price_changes) < 5:
            raise ValueError("Insufficient price data for meaningful correlation analysis")
        
        # Analyze correlation patterns
        overall_sentiment = input_data.sentiment_summary.overall_sentiment
        confidence = input_data.sentiment_summary.confidence
        
        # Determine correlation strength based on sentiment-price alignment
        total_correlations = len(price_changes)
        matching_correlations = 0
        
        # Simple correlation logic: positive sentiment should correlate with positive price moves
        for change in price_changes:
            if overall_sentiment == "positive" and change > 0:
                matching_correlations += 1
            elif overall_sentiment == "negative" and change < 0:
                matching_correlations += 1
            elif overall_sentiment == "neutral" and abs(change) < 1.0:  # Small changes
                matching_correlations += 1
        
        correlation_percentage = (matching_correlations / total_correlations) * 100
        
        # Determine correlation strength
        if correlation_percentage >= 80:
            strength = "Very Strong"
        elif correlation_percentage >= 65:
            strength = "Strong"
        elif correlation_percentage >= 50:
            strength = "Moderate"
        elif correlation_percentage >= 35:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        logger.info(f"Correlation analysis: {matching_correlations}/{total_correlations} matches ({correlation_percentage:.1f}%)")
        
        return CorrelationResult(
            total_correlations=total_correlations,
            matching_correlations=matching_correlations,
            correlation_percentage=round(correlation_percentage, 1),
            strength=strength,
            message=f"Correlation analysis: {matching_correlations}/{total_correlations} matches ({correlation_percentage:.1f}%) - {strength} correlation"
        )
        
    except Exception as e:
        logger.error(f"Error calculating correlations: {str(e)}")
        raise

@mcp.tool()
def run_backtest(input_data: RunBacktestInput) -> BacktestResult:
    """Run backtesting simulation using sentiment-based trading strategy"""
    try:
        if not input_data.stock_data:
            raise ValueError("No stock data provided for backtesting")
        
        if not input_data.sentiment_summary:
            raise ValueError("No sentiment analysis results provided for backtesting")
        
        logger.info(f"Running backtest with {len(input_data.stock_data)} price points, capital: ${input_data.initial_capital}")
        
        # Convert stock data to DataFrame for easier processing
        df_data = []
        for data in input_data.stock_data:
            df_data.append({
                'timestamp': data.timestamp,
                'close': data.close,
                'volume': data.volume
            })
        
        df = pd.DataFrame(df_data)
        df = df.set_index('timestamp').sort_index()
        
        if len(df) < 2:
            return "Error: Insufficient price data for backtesting"
        
        # Generate trading signals based on sentiment and price movements
        signals = generate_trading_signals(df, input_data.sentiment_summary, input_data.confidence_threshold)
        
        # Run backtest simulation
        backtest_results = simulate_trading(df, signals, input_data.initial_capital)
        
        return BacktestResult(
            total_trades=backtest_results['total_trades'],
            winning_trades=backtest_results['winning_trades'],
            win_rate=backtest_results['win_rate'],
            total_return=backtest_results['total_return'],
            sharpe_ratio=backtest_results['sharpe_ratio'],
            max_drawdown=backtest_results['max_drawdown'],
            message=f"Backtest completed: {backtest_results['total_trades']} trades, {backtest_results['win_rate']:.1%} win rate, {backtest_results['total_return']:.2f}% return"
        )
        
    except Exception as e:
        logger.error(f"Error in backtesting: {str(e)}")
        raise

@mcp.tool()
def generate_report(input_data: GenerateReportInput) -> ReportResult:
    """Generate comprehensive analysis report"""
    try:
        if not client:
            raise ValueError("Gemini API key not configured for report generation")
        
        logger.info(f"Generating comprehensive analysis report for {input_data.symbol}")
        
        # Prepare data summary for the report
        data_summary = prepare_report_data(
            input_data.symbol, input_data.sentiment_summary, input_data.technical_indicators, 
            input_data.correlations, input_data.backtest_results, input_data.strategy_recommendation
        )
        
        # Generate report using Gemini AI
        prompt = build_report_prompt(input_data.symbol, data_summary)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        report = response.text.strip()
        
        # Add metadata header
        report_header = generate_report_header(input_data.symbol, data_summary)
        full_report = f"{report_header}\n\n{report}"
        
        # Determine sections included
        sections_included = []
        if input_data.sentiment_summary:
            sections_included.append("Sentiment Analysis")
        if input_data.technical_indicators:
            sections_included.append("Technical Analysis")
        if input_data.correlations:
            sections_included.append("Correlation Analysis")
        if input_data.backtest_results:
            sections_included.append("Backtesting")
        if input_data.strategy_recommendation:
            sections_included.append("Strategy Recommendation")
        
        logger.info(f"Generated comprehensive report ({len(full_report)} characters)")
        
        return ReportResult(
            symbol=input_data.symbol,
            report_content=full_report,
            report_length=len(full_report),
            sections_included=sections_included,
            message=f"Report generated: {len(full_report)} characters, {len(sections_included)} sections"
        )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        raise

# Helper functions

def analyze_sentiment_batch(articles: List[NewsArticle]) -> List[str]:
    """Analyze sentiment for a batch of articles"""
    try:
        # Prepare articles text for analysis
        articles_text = []
        for i, article in enumerate(articles):
            title = article.title
            summary = article.summary or ""
            text = f"Article {i+1}:\nTitle: {title}\nSummary: {summary}\n"
            articles_text.append(text)
        
        combined_text = "\n".join(articles_text)
        
        prompt = f"""
        Analyze the sentiment of these financial news articles. For each article, determine if the sentiment is:
        - positive: Good news, optimistic outlook, positive developments
        - negative: Bad news, concerns, negative developments  
        - neutral: Factual reporting, mixed signals, or unclear sentiment
        
        Articles to analyze:
        {combined_text}
        
        Respond with ONLY a comma-separated list of sentiments in order (positive, negative, or neutral).
        Example: positive, negative, neutral, positive, neutral
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        # Parse response
        sentiments_text = response.text.strip()
        sentiments = [s.strip().lower() for s in sentiments_text.split(',')]
        
        # Validate and clean sentiments
        valid_sentiments = []
        for sentiment in sentiments:
            if sentiment in ['positive', 'negative', 'neutral']:
                valid_sentiments.append(sentiment)
            else:
                # Default to neutral for invalid responses
                valid_sentiments.append('neutral')
        
        # Ensure we have the right number of sentiments
        while len(valid_sentiments) < len(articles):
            valid_sentiments.append('neutral')
        
        return valid_sentiments[:len(articles)]
        
    except Exception as e:
        logger.error(f"Error in batch sentiment analysis: {str(e)}")
        # Return neutral for all articles on error
        return ['neutral'] * len(articles)

def fetch_with_intelligent_sampling(symbol: str, company_name: str, days: int) -> List[Dict[str, Any]]:
    """Fetch news using intelligent sampling strategy to get diverse, representative articles"""
    
    # High-impact financial news sources (global + Indian market focused)
    priority_sources = [
        'Reuters', 'Bloomberg', 'Economic Times', 'Business Standard',
        'Mint', 'Financial Express', 'MoneyControl', 'CNBC TV18',
        'Business Today', 'Forbes India', 'Yahoo Finance', 'CNBC'
    ]
    
    all_articles = []
    
    # Strategy 1: Get recent high-priority articles (last 7 days)
    recent_articles = fetch_news_batch(
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
        popular_articles = fetch_news_batch(
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
    
    # Sort by date (most recent first) and limit total
    all_articles.sort(key=lambda x: x['publishedAt'], reverse=True)
    
    # Intelligent limit: more articles for longer periods
    max_articles = min(100, max(30, days * 2))  # 30-100 articles based on period
    final_articles = all_articles[:max_articles]
    
    logger.info(f"Final selection: {len(final_articles)} articles from {len(all_articles)} total")
    return final_articles

def fetch_news_batch(symbol: str, company_name: str, days: int, page_size: int = 30, 
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

def generate_trading_signals(df: pd.DataFrame, sentiment_summary: SentimentResult, 
                             confidence_threshold: float) -> List[Dict[str, Any]]:
    """Generate trading signals based on sentiment and price movements"""
    signals = []
    
    # Get sentiment metrics
    overall_sentiment = sentiment_summary.overall_sentiment
    confidence = sentiment_summary.confidence
    
    # Calculate price momentum for signal timing
    df['price_change'] = df['close'].pct_change()
    df['momentum'] = df['price_change'].rolling(window=3).mean()
    
    # Generate signals based on sentiment and momentum alignment
    for i in range(3, len(df)):  # Start after momentum calculation window
        current_date = df.index[i]
        current_price = df.iloc[i]['close']
        momentum = df.iloc[i]['momentum']
        
        # Signal generation logic
        signal_type = None
        signal_confidence = confidence
        
        # Strong positive sentiment + positive momentum = BUY
        if (overall_sentiment == "positive" and confidence > confidence_threshold and 
            momentum > 0.01):  # 1% positive momentum
            signal_type = "buy"
            signal_confidence = min(confidence + 0.1, 1.0)
        
        # Strong negative sentiment + negative momentum = SELL
        elif (overall_sentiment == "negative" and confidence > confidence_threshold and 
              momentum < -0.01):  # 1% negative momentum
            signal_type = "sell"
            signal_confidence = min(confidence + 0.1, 1.0)
        
        # Mixed signals or low confidence = HOLD
        else:
            signal_type = "hold"
            signal_confidence = confidence * 0.5
        
        # Add signal if confidence is sufficient
        if signal_confidence > confidence_threshold:
            signals.append({
                'date': current_date,
                'price': current_price,
                'signal': signal_type,
                'confidence': signal_confidence,
                'momentum': momentum,
                'sentiment': overall_sentiment
            })
    
    logger.info(f"Generated {len(signals)} trading signals")
    return signals

def simulate_trading(df: pd.DataFrame, signals: List[Dict[str, Any]], 
                     initial_capital: float) -> Dict[str, Any]:
    """Simulate trading based on generated signals"""
    position = 0  # 0 = no position, 1 = long, -1 = short
    entry_price = 0
    trades = []
    portfolio_value = initial_capital
    peak_value = initial_capital
    max_drawdown = 0.0
    
    for signal in signals:
        try:
            signal_date = signal['date']
            current_price = signal['price']
            signal_type = signal['signal']
            confidence = signal['confidence']
            
            # Execute trading logic
            if signal_type == 'buy' and position <= 0:
                # Close short position if exists
                if position == -1:
                    pnl_percent = (entry_price - current_price) / entry_price
                    portfolio_value *= (1 + pnl_percent)
                    trades.append({
                        'type': 'close_short',
                        'date': signal_date,
                        'price': current_price,
                        'pnl': pnl_percent,
                        'confidence': confidence
                    })
                
                # Open long position
                position = 1
                entry_price = current_price
                trades.append({
                    'type': 'buy',
                    'date': signal_date,
                    'price': current_price,
                    'pnl': 0,
                    'confidence': confidence
                })
            
            elif signal_type == 'sell' and position >= 0:
                # Close long position if exists
                if position == 1:
                    pnl_percent = (current_price - entry_price) / entry_price
                    portfolio_value *= (1 + pnl_percent)
                    trades.append({
                        'type': 'close_long',
                        'date': signal_date,
                        'price': current_price,
                        'pnl': pnl_percent,
                        'confidence': confidence
                    })
                
                # Open short position
                position = -1
                entry_price = current_price
                trades.append({
                    'type': 'sell',
                    'date': signal_date,
                    'price': current_price,
                    'pnl': 0,
                    'confidence': confidence
                })
            
            # Update peak value and drawdown
            if portfolio_value > peak_value:
                peak_value = portfolio_value
            
            current_drawdown = (peak_value - portfolio_value) / peak_value
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
            
        except Exception as e:
            logger.warning(f"Error processing signal: {e}")
            continue
    
    # Close final position
    if position != 0 and len(df) > 0:
        final_price = df.iloc[-1]['close']
        if position == 1:
            pnl_percent = (final_price - entry_price) / entry_price
        else:
            pnl_percent = (entry_price - final_price) / entry_price
        
        portfolio_value *= (1 + pnl_percent)
        trades.append({
            'type': 'close_final',
            'date': df.index[-1],
            'price': final_price,
            'pnl': pnl_percent,
            'confidence': 0.5
        })
    
    # Calculate performance metrics
    profitable_trades = [t for t in trades if t.get('pnl', 0) > 0]
    total_trades_with_pnl = [t for t in trades if t.get('pnl', 0) != 0]
    
    win_rate = len(profitable_trades) / len(total_trades_with_pnl) if total_trades_with_pnl else 0
    total_return = ((portfolio_value - initial_capital) / initial_capital) * 100
    
    # Calculate Sharpe ratio
    returns = [t.get('pnl', 0) for t in total_trades_with_pnl]
    if returns and len(returns) > 1:
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0
    else:
        sharpe_ratio = 0
    
    logger.info(f"Backtest completed: {len(total_trades_with_pnl)} trades, {win_rate:.1%} win rate, {total_return:.2f}% return")
    
    return {
        'total_trades': len(total_trades_with_pnl),
        'winning_trades': len(profitable_trades),
        'win_rate': win_rate,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown * 100,  # Convert to percentage
        'final_portfolio_value': portfolio_value,
        'trades': trades
    }

def prepare_report_data(symbol: str, sentiment_summary: Optional[SentimentResult], 
                       technical_indicators: Dict[str, List[TechnicalIndicator]], correlations: List[CorrelationData],
                       backtest_results: Optional[BacktestResult], strategy_recommendation: str) -> Dict[str, Any]:
    """Prepare and structure data for report generation"""
    
    # Process sentiment data
    if sentiment_summary:
        sentiment_data = {
            "overall_sentiment": sentiment_summary.overall_sentiment,
            "confidence": sentiment_summary.confidence,
            "positive_percent": sentiment_summary.positive_percent,
            "negative_percent": sentiment_summary.negative_percent,
            "neutral_percent": sentiment_summary.neutral_percent,
            "total_articles": sentiment_summary.total_articles
        }
    else:
        sentiment_data = {
            "overall_sentiment": "neutral",
            "confidence": 0.0,
            "positive_percent": 0.0,
            "negative_percent": 0.0,
            "neutral_percent": 0.0,
            "total_articles": 0
        }
    
    # Process technical indicators
    tech_data = {}
    for indicator_name, indicators in technical_indicators.items():
        if indicators:  # If we have indicator data
            tech_data[indicator_name] = {
                "available": True,
                "indicator_count": len(indicators) if isinstance(indicators, list) else 1
            }
        else:
            tech_data[indicator_name] = {"available": False}
    
    # Process correlation data
    correlation_data = {
        "total_correlations": len(correlations),
        "has_correlations": len(correlations) > 0
    }
    
    # Process backtest data
    if backtest_results:
        backtest_data = {
            "has_backtest": True,
            "total_trades": backtest_results.total_trades,
            "winning_trades": backtest_results.winning_trades,
            "win_rate": backtest_results.win_rate,
            "total_return": backtest_results.total_return,
            "sharpe_ratio": backtest_results.sharpe_ratio,
            "max_drawdown": backtest_results.max_drawdown
        }
    else:
        backtest_data = {
            "has_backtest": False,
            "total_trades": 0,
            "winning_trades": 0,
            "win_rate": 0.0,
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0
        }
    
    # Process strategy data
    strategy_data = {
        "has_strategy": bool(strategy_recommendation),
        "strategy_length": len(strategy_recommendation) if strategy_recommendation else 0
    }
    
    return {
        "symbol": symbol,
        "sentiment": sentiment_data,
        "technical": tech_data,
        "correlations": correlation_data,
        "backtest": backtest_data,
        "strategy": strategy_data
    }

def build_report_prompt(symbol: str, data_summary: Dict[str, Any]) -> str:
    """Build comprehensive prompt for report generation"""
    
    sentiment = data_summary["sentiment"]
    backtest = data_summary["backtest"]
    technical = data_summary["technical"]
    
    return f"""
    Generate a comprehensive financial analysis report for {symbol} based on the following analysis results:
    
    SENTIMENT ANALYSIS RESULTS:
    - Overall Sentiment: {sentiment['overall_sentiment']} (Confidence: {sentiment['confidence']:.1%})
    - Positive News: {sentiment['positive_percent']:.1f}%
    - Negative News: {sentiment['negative_percent']:.1f}%
    - Neutral News: {sentiment['neutral_percent']:.1f}%
    - Total Articles Analyzed: {sentiment['total_articles']}
    
    TECHNICAL ANALYSIS RESULTS:
    - Technical Indicators Available: {list(technical.keys())}
    - Analysis Depth: {"Comprehensive" if len(technical) > 2 else "Basic"}
    
    BACKTESTING RESULTS:
    {"- Backtest Completed: Yes" if backtest['has_backtest'] else "- Backtest Completed: No"}
    {f"- Total Trades: {backtest['total_trades']}" if backtest['has_backtest'] else ""}
    {f"- Win Rate: {backtest['win_rate']:.1%}" if backtest['has_backtest'] else ""}
    {f"- Total Return: {backtest['total_return']:.2f}%" if backtest['has_backtest'] else ""}
    {f"- Sharpe Ratio: {backtest['sharpe_ratio']:.2f}" if backtest['has_backtest'] else ""}
    {f"- Max Drawdown: {backtest['max_drawdown']:.2f}%" if backtest['has_backtest'] else ""}
    
    Please provide a comprehensive report with the following sections:
    
    1. EXECUTIVE SUMMARY
    2. SENTIMENT ANALYSIS INSIGHTS  
    3. TECHNICAL ANALYSIS SUMMARY
    4. TRADING STRATEGY PERFORMANCE
    5. RISK ASSESSMENT
    6. INVESTMENT RECOMMENDATIONS
    7. CONCLUSION
    
    Format the report professionally with clear headings and actionable insights.
    """

def generate_report_header(symbol: str, data_summary: Dict[str, Any]) -> str:
    """Generate report header with metadata"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate analysis completeness
    components = []
    if data_summary["sentiment"]["total_articles"] > 0:
        components.append("Sentiment Analysis")
    if data_summary["technical"]:
        components.append("Technical Analysis")
    if data_summary["correlations"]["has_correlations"]:
        components.append("Correlation Analysis")
    if data_summary["backtest"]["has_backtest"]:
        components.append("Backtesting")
    if data_summary["strategy"]["has_strategy"]:
        components.append("Strategy Generation")
    
    completeness = len(components)
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
                    COMPREHENSIVE STOCK ANALYSIS REPORT
                                {symbol}
═══════════════════════════════════════════════════════════════════════════════

Generated: {current_time}
Analysis Components: {', '.join(components)} ({completeness}/5 modules completed)
Sentiment Articles: {data_summary["sentiment"]["total_articles"]}
Overall Sentiment: {data_summary["sentiment"]["overall_sentiment"].upper()} ({data_summary["sentiment"]["confidence"]:.1%} confidence)
{"Backtest Performance: " + f"{data_summary['backtest']['total_return']:+.2f}% return" if data_summary["backtest"]["has_backtest"] else "Backtest: Not completed"}

═══════════════════════════════════════════════════════════════════════════════
    """

if __name__ == "__main__":
    mcp.run()
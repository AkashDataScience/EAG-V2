#!/usr/bin/env python3
"""
Data models and structures for the Stock Analysis Backend
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime

@dataclass
class CandleData:
    """OHLCV candle data structure"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

@dataclass
class NewsItem:
    """News item structure"""
    headline: str
    date: str
    url: str
    source: str

@dataclass
class AnalyzedNews:
    """News item with sentiment analysis"""
    headline: str
    date: str
    url: str
    source: str
    sentiment: str
    confidence: float
    topic: str
    impact: str

@dataclass
class CorrelationResult:
    """Correlation analysis result"""
    date: str
    headline: str
    sentiment: str
    confidence: float
    price_change: float
    correlation_match: bool

@dataclass
class BacktestTrade:
    """Individual trade in backtest"""
    type: str
    date: datetime
    price: float
    pnl: float

@dataclass
class BacktestResults:
    """Backtest execution results"""
    total_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: float
    sharpe_ratio: float
    final_portfolio_value: float
    trades: List[BacktestTrade]

@dataclass
class ParsedQuery:
    """Parsed natural language query"""
    symbol: str
    timeframe: str
    task: str
    analysis_type: str
    confidence: float
    error: Optional[str] = None

@dataclass
class AnalysisResponse:
    """Complete analysis response"""
    status: str
    symbol: str
    timeframe: str
    original_query: str
    parsed_intent: ParsedQuery
    iterations: int
    iteration_log: List[str]
    final_answer: str
    execution_context: Dict[str, Any]
    timestamp: str
    candles: Optional[List[CandleData]] = None
    news_analysis: Optional[List[AnalyzedNews]] = None
    correlation_insights: Optional[Dict] = None
    backtest_results: Optional[Dict] = None

    def to_dict(self):
        """Convert dataclass to dictionary for JSON serialization."""
        from dataclasses import asdict
        return asdict(self)
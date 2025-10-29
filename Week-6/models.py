#!/usr/bin/env python3
"""
Pydantic Models for 4-Layer Cognitive Architecture
Defines all data structures for Perception, Memory, Decision-Making, and Action layers
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# PERCEPTION LAYER MODELS
# ============================================================================

class UserQuery(BaseModel):
    """Raw user input to the system"""
    text: str = Field(..., description="Raw user query text")
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: Optional[str] = Field(None, description="Session identifier")


class ParsedIntent(BaseModel):
    """Structured interpretation of user query"""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE.NS, AAPL)")
    company_name: str = Field(..., description="Full company name")
    task_type: Literal["sentiment", "correlation", "technical", "strategy", "full_analysis"] = Field(
        ..., description="Type of analysis requested"
    )
    timeframe: str = Field(default="1h", description="Data timeframe (1m, 5m, 1h, 1d)")
    period: str = Field(default="1mo", description="Analysis period (1d, 1mo, 3mo, 1y)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Parsing confidence score")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


# ============================================================================
# MEMORY LAYER MODELS
# ============================================================================

class StockData(BaseModel):
    """Stock price and volume data"""
    symbol: str
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NewsArticle(BaseModel):
    """Individual news article"""
    title: str = Field(..., min_length=1)
    summary: Optional[str] = None
    published: datetime
    source: str
    url: Optional[str] = None
    sentiment: Optional[Literal["positive", "negative", "neutral"]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class TechnicalIndicator(BaseModel):
    """Technical analysis indicator data"""
    name: str = Field(..., description="Indicator name (RSI, MACD, etc.)")
    timestamp: datetime
    value: float
    signal: Optional[str] = Field(None, description="Buy/Sell/Hold signal")
    parameters: Dict[str, Any] = Field(default_factory=dict)


class CorrelationData(BaseModel):
    """News-price correlation information"""
    article_title: str
    published: datetime
    sentiment: str
    confidence: float
    price_change: float
    correlation_match: bool
    time_diff_hours: float


class MemoryState(BaseModel):
    """Complete memory state of the agent"""
    session_id: str
    symbol: str
    company_name: str
    
    # Data storage
    stock_data: List[StockData] = Field(default_factory=list)
    news_articles: List[NewsArticle] = Field(default_factory=list)
    technical_indicators: Dict[str, List[TechnicalIndicator]] = Field(default_factory=dict)
    correlations: List[CorrelationData] = Field(default_factory=list)
    
    # Analysis results
    sentiment_summary: Optional[Dict[str, Any]] = None
    correlation_summary: Optional[Dict[str, Any]] = None
    backtest_results: Optional[Dict[str, Any]] = None
    strategy_recommendation: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    analysis_status: Dict[str, bool] = Field(default_factory=dict)


# ============================================================================
# DECISION-MAKING LAYER MODELS
# ============================================================================

class ActionType(str, Enum):
    """Available action types"""
    FETCH_STOCK_DATA = "fetch_stock_data"
    FETCH_NEWS_DATA = "fetch_news_data"
    ANALYZE_SENTIMENT = "analyze_sentiment"
    CALCULATE_RSI = "calculate_rsi"
    CALCULATE_MACD = "calculate_macd"
    CALCULATE_BOLLINGER = "calculate_bollinger"
    CALCULATE_CORRELATIONS = "calculate_correlations"
    RUN_BACKTEST = "run_backtest"
    GENERATE_STRATEGY = "generate_strategy"
    GENERATE_REPORT = "generate_report"
    COMPLETE_ANALYSIS = "complete_analysis"


class ActionPlan(BaseModel):
    """Planned action with parameters"""
    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, description="Execution priority (1=highest)")
    dependencies: List[ActionType] = Field(default_factory=list, description="Required previous actions")
    reasoning: str = Field(..., description="Why this action is needed")


class DecisionContext(BaseModel):
    """Context for decision making"""
    current_intent: ParsedIntent
    memory_state: MemoryState
    available_actions: List[ActionType]
    completed_actions: List[ActionType] = Field(default_factory=list)
    failed_actions: List[ActionType] = Field(default_factory=list)


class DecisionOutput(BaseModel):
    """Decision layer output"""
    next_action: Optional[ActionPlan] = None
    is_complete: bool = Field(default=False)
    reasoning: str = Field(..., description="Decision reasoning")
    confidence: float = Field(..., ge=0.0, le=1.0)
    estimated_completion: float = Field(..., ge=0.0, le=1.0, description="Analysis completion percentage")


# ============================================================================
# ACTION LAYER MODELS
# ============================================================================

class ActionRequest(BaseModel):
    """Request to execute an action"""
    action_type: ActionType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ActionResult(BaseModel):
    """Result of action execution"""
    action_type: ActionType
    success: bool
    data: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time: float = Field(..., ge=0.0, description="Execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True


class StockDataResult(BaseModel):
    """Specific result for stock data fetching"""
    symbol: str
    data_points: int
    current_price: float
    price_change_percent: float
    timeframe: str
    period: str
    message: str
    # Include actual data for memory storage
    stock_data: List[StockData] = Field(..., description="Actual stock data points")


class NewsDataResult(BaseModel):
    """Specific result for news data fetching"""
    symbol: str
    articles_count: int
    date_range: str
    sources: List[str]
    message: str
    # Include actual data for memory storage
    news_articles: List[NewsArticle] = Field(..., description="Actual news articles")


class SentimentResult(BaseModel):
    """Specific result for sentiment analysis"""
    total_articles: int
    positive_percent: float = Field(..., ge=0.0, le=100.0)
    negative_percent: float = Field(..., ge=0.0, le=100.0)
    neutral_percent: float = Field(..., ge=0.0, le=100.0)
    overall_sentiment: Literal["positive", "negative", "neutral"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    message: str


class TechnicalAnalysisResult(BaseModel):
    """Result for technical indicator calculation"""
    indicator_name: str
    current_value: float
    signal: Optional[str] = None
    data_points: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    message: str


class CorrelationResult(BaseModel):
    """Result for correlation analysis"""
    total_correlations: int
    matching_correlations: int
    correlation_percentage: float = Field(..., ge=0.0, le=100.0)
    strength: Literal["Very Weak", "Weak", "Moderate", "Strong"]
    message: str


class BacktestResult(BaseModel):
    """Result for backtesting"""
    total_trades: int
    winning_trades: int
    win_rate: float = Field(..., ge=0.0, le=1.0)
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    message: str


# ============================================================================
# SYSTEM MODELS
# ============================================================================

class AgentConfig(BaseModel):
    """Configuration for the cognitive agent"""
    gemini_api_key: str
    news_api_key: Optional[str] = None
    max_iterations: int = Field(default=20, gt=0)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    memory_retention_hours: int = Field(default=24, gt=0)


# ============================================================================
# MCP TOOL INPUT/OUTPUT MODELS
# ============================================================================

class FetchStockDataInput(BaseModel):
    """Input for fetch_stock_data MCP tool"""
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL, RELIANCE.NS)")
    period: str = Field(default="1mo", description="Data period (1d, 1mo, 3mo, 1y)")
    interval: str = Field(default="1h", description="Data interval (1m, 5m, 1h, 1d)")


class FetchNewsDataInput(BaseModel):
    """Input for fetch_news_data MCP tool"""
    symbol: str = Field(..., description="Stock symbol")
    days: int = Field(default=7, ge=1, le=365, description="Number of days to fetch news")


class AnalyzeSentimentInput(BaseModel):
    """Input for analyze_sentiment MCP tool"""
    news_articles: List[NewsArticle] = Field(..., description="News articles to analyze")
    batch_size: int = Field(default=5, ge=1, le=20, description="Batch size for AI processing")


class CalculateRSIInput(BaseModel):
    """Input for calculate_rsi MCP tool"""
    stock_data: List[StockData] = Field(..., description="Stock price data")
    period: int = Field(default=14, ge=2, le=100, description="RSI calculation period")


class CalculateCorrelationsInput(BaseModel):
    """Input for calculate_correlations MCP tool"""
    stock_data: List[StockData] = Field(..., description="Stock price data")
    sentiment_summary: SentimentResult = Field(..., description="Sentiment analysis results")


class RunBacktestInput(BaseModel):
    """Input for run_backtest MCP tool"""
    stock_data: List[StockData] = Field(..., description="Stock price data")
    sentiment_summary: SentimentResult = Field(..., description="Sentiment analysis results")
    initial_capital: float = Field(default=10000.0, gt=0, description="Starting capital")
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Signal confidence threshold")


class GenerateReportInput(BaseModel):
    """Input for generate_report MCP tool"""
    symbol: str = Field(..., description="Stock symbol")
    sentiment_summary: Optional[SentimentResult] = None
    technical_indicators: Dict[str, List[TechnicalIndicator]] = Field(default_factory=dict)
    correlations: List[CorrelationData] = Field(default_factory=list)
    backtest_results: Optional[BacktestResult] = None
    strategy_recommendation: str = Field(default="", description="Generated strategy text")


class ReportResult(BaseModel):
    """Result for report generation"""
    symbol: str
    report_content: str = Field(..., description="Generated report content")
    report_length: int = Field(..., description="Report length in characters")
    sections_included: List[str] = Field(..., description="Report sections included")
    generation_timestamp: datetime = Field(default_factory=datetime.now)
    message: str
    
    class Config:
        env_prefix = "AGENT_"


# ============================================================================
# MEMORY LAYER MODELS
# ============================================================================

class StoreFactInput(BaseModel):
    """Input for storing a fact in memory"""
    fact: str = Field(..., description="The fact to store in memory")


class RecallFactsInput(BaseModel):
    """Input for recalling facts from memory"""
    query: str = Field(..., description="Query to find relevant facts")


class MemoryResult(BaseModel):
    """Result from memory operations"""
    success: bool
    message: str
    facts: List[str] = Field(default_factory=list)
    total_facts: int = 0


# ============================================================================
# PERCEPTION LAYER MODELS
# ============================================================================

class ExtractFactsInput(BaseModel):
    """Input for extracting facts from user input"""
    user_input: str = Field(..., description="Raw user input to extract facts from")


class FactExtractionResult(BaseModel):
    """Result from fact extraction"""
    success: bool
    message: str
    facts: Dict[str, str] = Field(default_factory=dict, description="Key-value pairs of extracted facts")
    questions: List[str] = Field(default_factory=list, description="List of clarifying questions")


# ============================================================================
# SYSTEM MODELS
# ============================================================================

class SystemStatus(BaseModel):
    """Overall system status"""
    session_id: str
    status: Literal["initializing", "processing", "completed", "error"]
    current_layer: Literal["perception", "memory", "decision", "action"]
    progress: float = Field(..., ge=0.0, le=1.0)
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
#!/usr/bin/env python3
"""
Iterative agent for step-by-step stock analysis
"""

import google.generativeai as genai
import json
from typing import Dict, Any, Callable
from datetime import datetime

from config import config
from models import ParsedQuery, AnalysisResponse
from services.stock_data import StockDataService
from services.news_data import NewsDataService
from services.sentiment_analysis import SentimentAnalysisService
from services.correlation_analysis import CorrelationAnalysisService
from services.backtest_engine import BacktestEngineService
from utils.logger import logger

class IterativeAgent:
    """Iterative agent that makes step-by-step decisions based on previous results"""
    
    def __init__(self):
        """Initialize the agent with available functions and services"""
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        # Initialize services
        self.stock_service = StockDataService()
        self.news_service = NewsDataService()
        self.sentiment_service = SentimentAnalysisService()
        self.correlation_service = CorrelationAnalysisService()
        self.backtest_service = BacktestEngineService()
        
        # Available functions for the agent
        self.available_functions = {
            'fetch_market_data': self._fetch_market_data,
            'fetch_news_data': self._fetch_news_data,
            'analyze_sentiment': self._analyze_sentiment,
            'calculate_correlations': self._calculate_correlations,
            'run_backtest': self._run_backtest,
            'generate_strategy': self._generate_strategy,
            'create_summary': self._create_summary
        }
        
        self.execution_context = {}
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the iterative agent"""
        return """You are a financial analysis agent that solves stock analysis problems iteratively.

Available functions:
1. fetch_market_data(symbol, timeframe, period) - Fetches OHLCV candle data for a stock
   - symbol: Stock symbol (e.g., TSLA, AAPL)
   - timeframe: Data interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo)
   - period: Time range (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
2. fetch_news_data(symbol, days) - Fetches recent news headlines for a stock
3. analyze_sentiment(news_data) - Analyzes sentiment of news headlines
4. calculate_correlations(market_data, sentiment_data) - Finds correlations between news and price
5. run_backtest(market_data, correlations) - Backtests trading strategies
6. generate_strategy(correlation_data, backtest_results) - Creates strategy recommendations
7. create_summary(all_data) - Creates final analysis summary

Respond with EXACTLY ONE of these formats:
1. FUNCTION_CALL: function_name|parameters
2. FINAL_ANSWER: [your comprehensive analysis summary]

Decision Rules:
- Always start by fetching market data first
- IMPORTANT API LIMIT: When using fetch_market_data with timeframe='1m', the period cannot be longer than '7d'.
- Only call functions when you have the required data available
- Make logical decisions based on previous iteration results
- Provide FINAL_ANSWER when you have gathered sufficient data for a comprehensive analysis
- DO NOT provide FINAL_ANSWER until you have meaningful analysis to share
- Give ONE response at a time, never multiple responses

You will continue iterating until YOU decide the analysis is complete and provide FINAL_ANSWER.
"""
    
    async def execute_iterative_analysis(self, query: str, parsed_intent: ParsedQuery, session_id: str = None) -> AnalysisResponse:
        """Execute iterative analysis based on query"""
        try:
            symbol = parsed_intent.symbol
            timeframe = parsed_intent.timeframe
            
            iteration = 0
            last_response = None
            iteration_responses = []
            
            logger.info(f"Starting iterative analysis for query: {query}")
            
            # Continue until agent provides FINAL_ANSWER
            while True:
                iteration += 1
                logger.info(f"--- Iteration {iteration} ---")
                
                # Build current query context
                if last_response is None:
                    current_query = f"Query: {query}\nSymbol: {symbol}\nTimeframe: {timeframe}"
                else:
                    context = "\n".join(iteration_responses)
                    current_query = f"Original Query: {query}\nSymbol: {symbol}\nTimeframe: {timeframe}\n\nPrevious iterations:\n{context}\n\nWhat should I do next?"
                
                # Get agent's decision
                agent_response = await self._get_agent_decision(current_query)
                logger.info(f"Agent Response: {agent_response}")
                
                # Check if response contains FUNCTION_CALL (more flexible parsing)
                if "FUNCTION_CALL:" in agent_response:
                    # Extract the function call part
                    function_call_start = agent_response.find("FUNCTION_CALL:")
                    function_call_line = agent_response[function_call_start:].split('\n')[0]
                    
                    # Parse and execute function call
                    _, function_info = function_call_line.split(":", 1)
                    func_name, params = [x.strip() for x in function_info.split("|", 1)]
                    
                    # Update status based on function being called
                    if session_id:
                        self._update_status_for_function(session_id, func_name, iteration)
                    
                    # Execute the function
                    try:
                        function_result = await self._execute_function(func_name, params, symbol, timeframe)
                        logger.info(f"Function {func_name} result: {type(function_result).__name__} with {len(str(function_result))} chars")
                        
                        # Store result and continue
                        last_response = function_result
                        iteration_responses.append(
                            f"Iteration {iteration}: Called {func_name} with '{params}' → Result: {self._summarize_result(function_result)}"
                        )
                        
                    except Exception as e:
                        error_msg = f"Function {func_name} failed with error: {str(e)}"
                        logger.error(error_msg)
                        # Feed the error back to the agent in the next iteration
                        last_response = {"error": error_msg}
                        iteration_responses.append(f"Iteration {iteration}: {error_msg}")
                
                elif "FINAL_ANSWER:" in agent_response:
                    # Agent has completed analysis - extract the final answer part
                    final_answer_start = agent_response.find("FINAL_ANSWER:")
                    final_answer = agent_response[final_answer_start + len("FINAL_ANSWER:"):].strip()
                    logger.info(f"Agent execution complete after {iteration} iterations")
                    
                    return self._get_final_response(query, parsed_intent, iteration, iteration_responses, final_answer)
                
                else:
                    logger.warning(f"Invalid agent response format: {agent_response}")
                    iteration_responses.append(f"Iteration {iteration}: Invalid response format")
                    
                    # If we get invalid responses repeatedly, provide a fallback
                    if iteration > 10:  # Safety net to prevent infinite loops
                        logger.error("Too many invalid responses, terminating")
                        return AnalysisResponse(
                            status='error',
                            symbol=symbol,
                            timeframe=timeframe,
                            original_query=query,
                            parsed_intent=parsed_intent,
                            iterations=iteration,
                            iteration_log=iteration_responses,
                            final_answer='Analysis failed due to repeated invalid agent responses',
                            execution_context=self._serialize_context(),
                            timestamp=datetime.now().isoformat()
                        )
            
        except Exception as e:
            logger.error(f"Error in iterative analysis: {str(e)}")
            return AnalysisResponse(
                status='error',
                symbol=parsed_intent.symbol,
                timeframe=parsed_intent.timeframe,
                original_query=query,
                parsed_intent=parsed_intent,
                iterations=0,
                iteration_log=[f"Error: {str(e)}"],
                final_answer=f'Analysis failed: {str(e)}',
                execution_context={},
                timestamp=datetime.now().isoformat()
            )
    
    async def _get_agent_decision(self, query: str) -> str:
        """Get the agent's next decision"""
        try:
            full_prompt = f"{self.get_system_prompt()}\n\nCurrent situation:\n{query}\n\nWhat should I do next?"
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=500,
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error getting agent decision: {str(e)}")
            return "FINAL_ANSWER: Error in agent decision making"
    
    async def _execute_function(self, func_name: str, params: str, symbol: str, timeframe: str) -> Any:
        """Execute a function call"""
        if func_name not in self.available_functions:
            raise ValueError(f"Unknown function: {func_name}")
        
        return await self.available_functions[func_name](params, symbol, timeframe)
    
    # Function implementations
    async def _fetch_market_data(self, params: str, symbol: str, timeframe: str) -> Any:
        """Fetch market data"""
        # Parse parameters to extract symbol, timeframe, and period from agent's params
        parsed_symbol = symbol
        parsed_timeframe = timeframe
        period = None
        
        if params:
            # Normalize delimiters to handle ',', '&', and '|'
            normalized_params = params.replace('&', ',').replace('|', ',')
            # Extract parameters from params like "symbol=TSLA, timeframe=1d, period=1mo"
            for param in normalized_params.split(','):
                param = param.strip()
                if param.startswith('symbol='):
                    parsed_symbol = param.split('=')[1].strip()
                elif param.startswith('timeframe='):
                    parsed_timeframe = param.split('=')[1].strip()
                elif param.startswith('period='):
                    period = param.split('=')[1].strip()
        
        logger.info(f"Agent requesting: symbol={parsed_symbol}, timeframe={parsed_timeframe}, period={period}")
        
        candles = self.stock_service.fetch_candles(parsed_symbol, parsed_timeframe, period=period)
        self.execution_context['market_data'] = candles
        return candles
    
    async def _fetch_news_data(self, params: str, symbol: str, timeframe: str) -> Any:
        """Fetch news data"""
        news = self.news_service.fetch_news(symbol)
        self.execution_context['news_data'] = news
        return news
    
    async def _analyze_sentiment(self, params: str, symbol: str, timeframe: str) -> Any:
        """Analyze sentiment"""
        if 'news_data' not in self.execution_context:
            raise ValueError("No news data available for sentiment analysis")
        
        sentiment_results = self.sentiment_service.analyze_news_sentiment(self.execution_context['news_data'])
        self.execution_context['sentiment_data'] = sentiment_results
        return sentiment_results
    
    async def _calculate_correlations(self, params: str, symbol: str, timeframe: str) -> Any:
        """Calculate correlations"""
        if 'market_data' not in self.execution_context or 'sentiment_data' not in self.execution_context:
            raise ValueError("Missing market data or sentiment data for correlation analysis")
        
        correlations = self.correlation_service.analyze_correlations(
            self.execution_context['market_data'],
            self.execution_context['sentiment_data']
        )
        self.execution_context['correlation_data'] = correlations
        return correlations
    
    async def _run_backtest(self, params: str, symbol: str, timeframe: str) -> Any:
        """Run backtest"""
        if 'market_data' not in self.execution_context or 'correlation_data' not in self.execution_context:
            raise ValueError("Missing market data or correlation data for backtesting")
        
        backtest_results = self.backtest_service.run_backtest(
            self.execution_context['market_data'],
            self.execution_context['correlation_data']['correlations']
        )
        self.execution_context['backtest_results'] = backtest_results
        return backtest_results
    
    async def _generate_strategy(self, params: str, symbol: str, timeframe: str) -> Any:
        """Generate strategy recommendations"""
        # This would use the LLM to generate strategy recommendations
        # based on correlation and backtest data
        strategy = {"recommendation": "Hold", "confidence": 0.5}
        self.execution_context['strategy'] = strategy
        return strategy
    
    async def _create_summary(self, params: str, symbol: str, timeframe: str) -> Any:
        """Create final summary"""
        summary = {
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis_complete": True,
            "context_keys": list(self.execution_context.keys())
        }
        return summary
    
    def _summarize_result(self, result: Any) -> str:
        """Create a brief summary of function result"""
        if isinstance(result, list):
            return f"List with {len(result)} items"
        elif isinstance(result, dict):
            return f"Dict with keys: {list(result.keys())}"
        else:
            return f"{type(result).__name__}"
    
    def _update_status_for_function(self, session_id: str, func_name: str, iteration: int):
        """Update status based on the function being called"""
        from routes.api import update_analysis_status
        
        function_messages = {
            'fetch_market_data': '📊 Fetching market data...',
            'fetch_news_data': '📰 Retrieving news headlines...',
            'analyze_sentiment': '🧠 Analyzing sentiment with AI...',
            'calculate_correlations': '🔗 Calculating correlations...',
            'run_backtest': '📈 Running backtests...',
            'generate_strategy': '💡 Generating strategy...',
            'create_summary': '📋 Creating summary...'
        }
        
        message = function_messages.get(func_name, f'🔄 Executing {func_name}...')
        # Progress is now handled by the frontend based on step count
        progress = iteration * 10
        
        update_analysis_status(session_id, 'processing', message, progress, func_name, step=iteration)

    def _get_final_response(self, query, parsed_intent, iteration, iteration_responses, final_answer):
        """Construct the final AnalysisResponse object"""
        return AnalysisResponse(
            status='completed',
            symbol=parsed_intent.symbol,
            timeframe=parsed_intent.timeframe,
            original_query=query,
            parsed_intent=parsed_intent,
            iterations=iteration,
            iteration_log=iteration_responses,
            final_answer=final_answer,
            execution_context=self._serialize_context(),
            timestamp=datetime.now().isoformat(),
            # Populate the data fields for the final result
            candles=self.execution_context.get('market_data', []),
            news_analysis=self.execution_context.get('sentiment_data', []),
            correlation_insights=self.execution_context.get('correlation_data', {}),
            backtest_results=self.execution_context.get('backtest_results', {})
        )

    def _serialize_context(self) -> Dict[str, Any]:
        """Serialize execution context for response"""
        serialized = {}
        for key, value in self.execution_context.items():
            if isinstance(value, list) and len(value) > 0:
                serialized[key] = f"List of {len(value)} {type(value[0]).__name__} objects"
            elif isinstance(value, dict):
                serialized[key] = f"Dict with {len(value)} keys"
            else:
                serialized[key] = str(type(value).__name__)
        return serialized
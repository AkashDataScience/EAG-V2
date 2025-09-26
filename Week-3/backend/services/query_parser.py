#!/usr/bin/env python3
"""
Natural language query parsing service
"""

import google.generativeai as genai
import json
from typing import Dict, Any

from config import config
from models import ParsedQuery
from utils.logger import logger

class QueryParserService:
    """Parses natural language queries to extract structured intent"""
    
    def __init__(self):
        """Initialize Gemini configuration"""
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
    
    def parse_query(self, query: str) -> ParsedQuery:
        """Parse natural language query to extract intent and parameters"""
        try:
            prompt = f"""
            You are a financial query parser. Parse this natural language query and extract structured information.
            
            Query: "{query}"
            
            Extract and return JSON with these fields:
            - "symbol": Stock symbol (e.g., "RELIANCE.NS", "HDFC.NS", "TSLA", "AAPL") - convert company names to symbols
            - "timeframe": Time period ("1m", "5m", "15m", "1h", "1d") - convert words like "daily" to "1d", "hourly" to "1h"
            - "task": Primary task ("sentiment", "correlation", "backtest", "strategy", "full_analysis")
            - "analysis_type": Type of analysis requested ("basic", "detailed", "comprehensive")
            - "confidence": How confident you are in parsing (0.0 to 1.0)
            
            Common symbol mappings:
            
            Indian Companies:
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
            
            US Companies:
            - Tesla → TSLA
            - Apple → AAPL
            - Microsoft → MSFT
            - Google, Alphabet → GOOGL
            - Amazon → AMZN
            - NVIDIA → NVDA
            - Meta, Facebook → META
            
            Task mapping:
            - "analyze", "analysis" → "sentiment"
            - "correlation", "correlate" → "correlation"
            - "backtest", "test strategy" → "backtest"
            - "strategy", "trading strategy", "algo trading" → "strategy"
            - "full analysis", "complete analysis" → "full_analysis"
            
            Return ONLY valid JSON.
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    top_k=1,
                    top_p=0.95,
                    max_output_tokens=300,
                )
            )
            
            # Clean and parse response
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            parsed_data = json.loads(response_text)
            
            # Create ParsedQuery object with defaults
            parsed_query = ParsedQuery(
                symbol=parsed_data.get('symbol', 'UNKNOWN'),
                timeframe=parsed_data.get('timeframe', config.DEFAULT_TIMEFRAME),
                task=parsed_data.get('task', 'full_analysis'),
                analysis_type=parsed_data.get('analysis_type', 'comprehensive'),
                confidence=float(parsed_data.get('confidence', 0.5))
            )
            
            logger.info(f"Parsed query: {query} → {parsed_query}")
            return parsed_query
            
        except Exception as e:
            logger.error(f"Error parsing query: {str(e)}")
            # Fallback parsing
            return ParsedQuery(
                symbol='UNKNOWN',
                timeframe=config.DEFAULT_TIMEFRAME,
                task='full_analysis',
                analysis_type='comprehensive',
                confidence=0.0,
                error=str(e)
            )
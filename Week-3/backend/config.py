#!/usr/bin/env python3
"""
Configuration settings for the Stock Analysis Backend
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    """Application configuration"""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')
    NEWS_API_KEY: str = os.getenv('NEWS_API_KEY', 'your-news-api-key-here')
    
    # Flask settings
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    
    # Analysis settings
    MAX_NEWS_ITEMS: int = 30  # Legacy setting, now using intelligent sampling
    MAX_CANDLES: int = 240
    DEFAULT_TIMEFRAME: str = '1h'
    DEFAULT_ANALYSIS_DAYS: int = 30
    
    # Intelligent news sampling settings
    MAX_ARTICLES_PER_ANALYSIS: int = 100  # Maximum articles for comprehensive analysis
    MIN_ARTICLES_PER_ANALYSIS: int = 30   # Minimum articles for basic analysis
    PRIORITY_SOURCES_WEIGHT: float = 0.6  # Weight given to priority financial sources
    
    # Agent settings
    GEMINI_MODEL: str = 'gemini-2.0-flash'
    
    # Backtesting settings
    INITIAL_CAPITAL: float = 10000.0
    MIN_CONFIDENCE_THRESHOLD: float = 0.6

# Global config instance
config = Config()
#!/usr/bin/env python3
"""
Stock data fetching service using Yahoo Finance
"""

import yfinance as yf
import pandas as pd
from typing import List
from datetime import datetime

from models import CandleData
from utils.logger import logger

class StockDataService:
    """Handles fetching stock market data from Yahoo Finance"""
    
    @staticmethod
    def fetch_candles(symbol: str, timeframe: str, count: int = 240, period: str = None) -> List[CandleData]:
        """Fetch OHLCV candle data from Yahoo Finance"""
        logger.info(f"Fetching data for {symbol} with timeframe {timeframe}")
        
        try:
            # Map timeframes to yfinance intervals
            interval_map = {
                '1m': '1m',
                '2m': '2m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '60m': '60m',
                '90m': '90m',
                '1h': '1h',
                '1d': '1d',
                '5d': '5d',
                '1wk': '1wk',
                '1mo': '1mo',
                '3mo': '3mo'
            }
            
            interval = interval_map.get(timeframe, '1d')
            
            # Use provided period or set default based on interval constraints
            if period is None:
                if interval in ['1m', '2m', '5m', '15m', '30m', '90m']:
                    # Intraday intervals - max 60 days
                    period = '60d'
                elif interval in ['60m', '1h']:
                    # Hourly - max 730 days
                    period = '730d'
                else:
                    # Daily and above - can use longer periods
                    period = '2y'
            
            logger.info(f"Fetching {symbol}: interval={interval}, period={period}")
            
            # Create ticker and fetch data
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No data returned for {symbol}, trying yf.download")
                # Try alternative method
                data = yf.download(symbol, period=period, interval=interval, progress=False)
            
            if data.empty:
                raise ValueError(f"No data available for symbol {symbol}")
            
            # Validate required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            
            if missing_cols:
                raise ValueError(f"Missing required columns {missing_cols} for {symbol}")
            
            # Clean the data
            data = data.dropna()
            
            if len(data) == 0:
                raise ValueError(f"No valid data after cleaning for {symbol}")
            
            # Take the most recent data
            recent_data = data.tail(min(count, len(data)))
            
            # Convert to our format
            candles = []
            for timestamp, row in recent_data.iterrows():
                try:
                    candle = CandleData(
                        timestamp=timestamp.isoformat(),
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume']) if pd.notna(row['Volume']) else 0
                    )
                    candles.append(candle)
                except Exception as e:
                    logger.warning(f"Skipping invalid row for {symbol}: {e}")
                    continue
            
            if len(candles) == 0:
                raise ValueError(f"No valid candles created for {symbol}")
            
            logger.info(f"Successfully fetched {len(candles)} candles for {symbol}")
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            raise



    @staticmethod
    def get_company_name(symbol: str) -> str:
        """Get company name from symbol for better news search"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info.get('longName', symbol)
        except:
            return symbol
#!/usr/bin/env python3
"""
Correlation analysis service
"""

import pandas as pd
from typing import List, Dict

from models import CandleData, CorrelationResult
from utils.logger import logger

class CorrelationAnalysisService:
    """Analyzes correlations between news sentiment and price movements"""
    
    @staticmethod
    def analyze_correlations(candles: List[CandleData], news_analysis: List[Dict]) -> Dict:
        """Find correlations between news sentiment and price movements"""
        try:
            correlations = []
            
            # Convert candles to DataFrame for easier analysis
            df = pd.DataFrame([{
                'timestamp': pd.to_datetime(candle.timestamp),
                'close': candle.close
            } for candle in candles])
            
            df = df.set_index('timestamp').sort_index()
            df['price_change'] = df['close'].pct_change() * 100
            
            # Analyze each news item
            for news in news_analysis:
                news_date = pd.to_datetime(news['date'])
                
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
                        'date': news['date'],
                        'headline': news['headline'],
                        'sentiment': sentiment,
                        'confidence': news['confidence'],
                        'price_change': float(price_change) if not pd.isna(price_change) else 0.0,
                        'correlation_match': correlation_match
                    })
            
            # Calculate overall correlation metrics
            matches = sum(1 for c in correlations if c['correlation_match'])
            total = len(correlations)
            correlation_rate = matches / total if total > 0 else 0
            
            # Determine correlation strength
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
            logger.error(f"Error in correlation analysis: {str(e)}")
            return {
                'correlations': [],
                'correlation_rate': 0.0,
                'strength': 'Unknown',
                'total_analyzed': 0
            }
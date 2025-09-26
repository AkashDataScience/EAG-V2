#!/usr/bin/env python3
"""
Backtesting engine service
"""

import pandas as pd
import numpy as np
from typing import List, Dict
from datetime import datetime

from models import CandleData
from config import config
from utils.logger import logger

class BacktestEngineService:
    """Runs backtesting strategies based on sentiment signals"""
    
    @staticmethod
    def run_backtest(candles: List[CandleData], correlations: List[Dict]) -> Dict:
        """Run simple sentiment-based trading strategy backtest"""
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': pd.to_datetime(candle.timestamp),
                'close': candle.close
            } for candle in candles])
            
            df = df.set_index('timestamp').sort_index()
            
            # Initialize backtest variables
            position = 0  # 0 = no position, 1 = long, -1 = short
            entry_price = 0
            trades = []
            portfolio_value = config.INITIAL_CAPITAL
            
            # Process each correlation/signal
            for corr in correlations:
                signal_date = pd.to_datetime(corr['date'])
                sentiment = corr['sentiment']
                confidence = corr['confidence']
                
                # Find price at signal time
                closest_idx = df.index.get_indexer([signal_date], method='nearest')[0]
                if closest_idx >= 0 and closest_idx < len(df):
                    current_price = df.iloc[closest_idx]['close']
                    
                    # Simple strategy: Buy on positive sentiment, sell on negative
                    if sentiment == 'positive' and confidence > config.MIN_CONFIDENCE_THRESHOLD and position <= 0:
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
                        
                    elif sentiment == 'negative' and confidence > config.MIN_CONFIDENCE_THRESHOLD and position >= 0:
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
            total_return = (portfolio_value - config.INITIAL_CAPITAL) / config.INITIAL_CAPITAL
            
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
            logger.error(f"Error in backtesting: {str(e)}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'sharpe_ratio': 0.0,
                'final_portfolio_value': config.INITIAL_CAPITAL,
                'trades': []
            }
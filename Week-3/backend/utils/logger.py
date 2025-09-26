#!/usr/bin/env python3
"""
Logging configuration for the Stock Analysis Backend
"""

import logging
import sys
from datetime import datetime

def setup_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Setup and configure logger"""
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Global logger instance
logger = setup_logger('stock_analysis')
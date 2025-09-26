#!/usr/bin/env python3
"""
Stock Analysis Backend Runner
Modular Flask application with AI-powered stock analysis
"""

import os
from dotenv import load_dotenv
from app import app
from config import config
from utils.logger import logger

# Load environment variables
load_dotenv()

if __name__ == '__main__':
    print("🚀 Starting Stock Analysis Backend (Modular)")
    print(f"📊 Server running on http://{config.HOST}:{config.PORT}")
    print("\n💡 Available endpoints:")
    print("   GET  /")
    print("   GET  /api/health")
    print("   POST /api/analyze")
    print("   POST /api/parse-query")
    
    # Check for required environment variables
    if not os.getenv('GEMINI_API_KEY'):
        print("\n⚠️  WARNING: GEMINI_API_KEY not set. LLM analysis will fail.")
        print("   Please set your Google Gemini API key in .env file")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")
    
    if not os.getenv('NEWS_API_KEY'):
        print("\n💡 INFO: NEWS_API_KEY not set. Using Yahoo Finance news only.")
    
    logger.info("Starting modular Flask application")
    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
        threaded=True
    )
#!/usr/bin/env python3
"""
Stock News + Price Correlator Backend
Modular Flask API for stock analysis with AI-powered insights
"""

from flask import Flask
from flask_cors import CORS

from config import config
from routes.api import api_bp
from utils.logger import logger

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Enable CORS for Chrome extension
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Root endpoint
    @app.route('/')
    def root():
        return {
            'service': 'Stock Analysis Backend',
            'version': '1.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/api/health',
                'analyze': '/api/analyze',
                'parse_query': '/api/parse-query'
            }
        }
    
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    logger.info(f"Starting Stock Analysis Backend on {config.HOST}:{config.PORT}")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
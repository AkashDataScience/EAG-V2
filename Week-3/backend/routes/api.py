#!/usr/bin/env python3
"""
API routes for the Stock Analysis Backend
"""

from flask import Blueprint, request, jsonify
import asyncio
import threading
import time
import uuid

from services.query_parser import QueryParserService
from agents.iterative_agent import IterativeAgent
from utils.logger import logger

# Create blueprint
api_bp = Blueprint('api', __name__)

# Initialize services
query_parser = QueryParserService()

# Global dictionaries to track status and results of concurrent analyses
current_analysis_status = {}
analysis_results = {}

def update_analysis_status(session_id, status, message, progress, current_function=None, step=0):
    """Update the analysis status for real-time tracking"""
    current_analysis_status[session_id] = {
        'status': status,
        'message': message,
        'progress': progress,
        'current_function': current_function,
        'step': step,
        'timestamp': time.time()
    }

def run_analysis_in_background(session_id, query, parsed_intent):
    """
    This function is executed in a background thread to avoid blocking the API.
    It runs the iterative agent and stores the final result.
    """
    logger.info(f"Background thread started for session {session_id}")
    # Each thread gets its own instance of the agent and its own event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        agent = IterativeAgent()
        result = loop.run_until_complete(
            agent.execute_iterative_analysis(query, parsed_intent, session_id)
        )
        
        # Upon completion, store the detailed result
        analysis_results[session_id] = result
        
        # Set final status to 'completed'
        update_analysis_status(session_id, 'completed', 'Analysis complete!', 100, 'finished', -1)
        logger.info(f"Analysis completed and result stored for session {session_id}")

    except Exception as e:
        logger.error(f"Error in background analysis for session {session_id}: {str(e)}")
        update_analysis_status(session_id, 'error', str(e), 0, 'error', -1)
        analysis_results[session_id] = {"error": "Analysis failed", "message": str(e)}
    finally:
        loop.close()

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Stock Analysis Backend',
        'version': '1.0.0'
    })

@api_bp.route('/analyze', methods=['POST'])
def analyze_stock():
    """
    Main analysis endpoint - accepts a query, starts analysis in the background,
    and immediately returns a session ID for polling.
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        session_id = str(uuid.uuid4())
        logger.info(f'Received analysis request: "{query}" (Session: {session_id})')
        
        # Initial status before starting background thread
        update_analysis_status(session_id, 'parsing', 'Parsing your query...', 5, 'parse_query', 0)
        
        parsed_intent = query_parser.parse_query(query)
        if parsed_intent.symbol == 'UNKNOWN':
            update_analysis_status(session_id, 'error', 'Could not parse stock symbol', 0)
            return jsonify({
                'error': 'Could not parse stock symbol',
                'message': 'Please specify a valid stock symbol or company name',
            }), 400
        
        # Start the analysis in a background thread
        thread = threading.Thread(
            target=run_analysis_in_background,
            args=(session_id, query, parsed_intent)
        )
        thread.daemon = True  # Allows main app to exit even if threads are running
        thread.start()
        
        # Immediately return the session ID
        return jsonify({'session_id': session_id}), 202  # 202 Accepted

    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@api_bp.route('/status/<session_id>', methods=['GET'])
def get_analysis_status(session_id):
    """Get current analysis status for a session"""
    status = current_analysis_status.get(session_id, {
        'status': 'not_found',
        'message': 'Analysis session not found.',
        'progress': 0
    })
    return jsonify(status)

@api_bp.route('/results/<session_id>', methods=['GET'])
def get_analysis_result(session_id):
    """Get the final result of a completed analysis"""
    status = current_analysis_status.get(session_id, {})
    
    if status.get('status') == 'completed':
        result = analysis_results.get(session_id)
        if result:
            # Assuming result is an object that can be converted to a dict
            return jsonify(result.to_dict() if hasattr(result, 'to_dict') else result)
        else:
            return jsonify({'error': 'Result not found for completed analysis'}), 404
            
    elif status.get('status') == 'error':
        return jsonify(analysis_results.get(session_id, {'error': 'An error occurred during analysis'})), 500
        
    else:
        return jsonify({
            'status': status.get('status', 'processing'), 
            'message': 'Analysis is still in progress. Poll the status endpoint.'
        }), 202 # Still processing

@api_bp.route('/parse-query', methods=['POST'])
def parse_query():
    """Parse natural language query endpoint"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        query = data['query'].strip()
        parsed_intent = query_parser.parse_query(query)
        
        return jsonify({
            'original_query': query,
            'parsed_intent': parsed_intent.__dict__
        })
        
    except Exception as e:
        logger.error(f"Error in parse-query endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

# Optional: Add a cleanup thread for old sessions if memory becomes a concern
def cleanup_old_sessions():
    while True:
        time.sleep(600) # Run every 10 minutes
        now = time.time()
        try:
            expired_sessions = [
                sid for sid, data in current_analysis_status.items()
                if now - data.get('timestamp', 0) > 3600  # 1 hour expiry
            ]
            for sid in expired_sessions:
                current_analysis_status.pop(sid, None)
                analysis_results.pop(sid, None)
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions.")
        except Exception as e:
            logger.error(f"Error in session cleanup thread: {e}")

cleanup_thread = threading.Thread(target=cleanup_old_sessions, daemon=True)
cleanup_thread.start()

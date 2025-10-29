#!/usr/bin/env python3
"""
Perception Layer - Simple Fact Extraction and User Understanding
"""

import os
from typing import List, Dict, Any
from google import genai
from models import ExtractFactsInput, FactExtractionResult
import logging

logger = logging.getLogger(__name__)


class Perception:
    def __init__(self):
        # Initialize Gemini client
        self.client = None
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
    
    def extract_facts(self, input_data: ExtractFactsInput) -> FactExtractionResult:
        """Extract key facts from user input and ask clarifying questions"""
        try:
            if not self.client:
                return FactExtractionResult(
                    success=False,
                    message="Gemini API key not configured",
                    facts={},
                    questions=[]
                )
            
            prompt = f"""Extract key facts from this user input and ask clarifying questions:

User Input: {input_data.user_input}

Please:
1. Extract key facts as key-value pairs based on what the user actually said
2. Always include "symbol" and "analysis_type" as facts (use "unknown" if not mentioned)
3. Add any other relevant facts you can extract from the user input
4. Ask at least 5 specific, relevant questions to better understand the user's needs

Return your response as valid JSON in this format:
{{
  "facts": {{
    "symbol": "extracted stock symbol or unknown",
    "analysis_type": "sentiment/technical/correlation/full_analysis/unknown",
    "key1": "value1",
    "key2": "value2"
  }},
  "questions": [
    "question 1 based on user input",
    "question 2 based on user input", 
    "question 3 based on user input",
    "question 4 based on user input",
    "question 5 based on user input"
  ]
}}

Example for "I want sentiment analysis for RELIANCE stock":
{{
  "facts": {{
    "symbol": "RELIANCE.NS",
    "analysis_type": "sentiment",
    "user_intent": "analyze market sentiment",
    "stock_mentioned": "RELIANCE"
  }},
  "questions": [
    "What time period should we analyze for RELIANCE sentiment?",
    "Are you interested in news from specific sources?",
    "Do you want to see the actual news articles affecting sentiment?",
    "Are you planning to buy, sell, or hold RELIANCE stock?",
    "What's your main concern about RELIANCE's current market position?"
  ]
}}

Extract facts and generate questions based on the actual user input, not the example."""

            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Parse the JSON response
            import json
            response_text = response.text.strip()
            
            # Extract JSON from response (in case there's extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_text = response_text[json_start:json_end]
                parsed_data = json.loads(json_text)
                
                facts = parsed_data.get("facts", {})
                questions = parsed_data.get("questions", [])
            
            logger.info(f"Extracted {len(facts)} facts and {len(questions)} questions")
            
            return FactExtractionResult(
                success=True,
                message=f"Extracted {len(facts)} facts and generated {len(questions)} clarifying questions",
                facts=facts,
                questions=questions
            )
            
        except Exception as e:
            logger.error(f"Error in fact extraction: {str(e)}")
            return FactExtractionResult(
                success=False,
                message=f"Error extracting facts: {str(e)}",
                facts={},
                questions=[]
            )
    

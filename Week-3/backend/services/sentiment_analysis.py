#!/usr/bin/env python3
"""
Sentiment analysis service using Google Gemini
"""

import google.generativeai as genai
import json
from typing import List, Dict

from models import NewsItem, AnalyzedNews
from config import config
from utils.logger import logger

class SentimentAnalysisService:
    """Handles LLM-based sentiment analysis using Google Gemini"""
    
    def __init__(self):
        """Initialize Gemini configuration"""
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
    
    def analyze_news_sentiment(self, news_items: List[NewsItem]) -> List[Dict]:
        """Analyze sentiment of news headlines using Google Gemini Flash 2.0"""
        try:
            # Prepare news for batch analysis
            headlines = [item.headline for item in news_items]
            
            prompt = f"""
            You are a financial sentiment analysis expert. Analyze the sentiment of these stock-related news headlines.
            
            For each headline, provide:
            1. Sentiment: positive, negative, or neutral
            2. Confidence: 0.0 to 1.0 (how confident you are in the sentiment)
            3. Topic: brief category (earnings, product, legal, market, merger, regulatory, etc.)
            4. Impact: potential stock impact (high, medium, low)
            
            Headlines to analyze:
            {chr(10).join([f"{i+1}. {headline}" for i, headline in enumerate(headlines)])}
            
            Respond ONLY in valid JSON format as an array of objects with keys: sentiment, confidence, topic, impact
            Example: [{{"sentiment": "positive", "confidence": 0.8, "topic": "earnings", "impact": "high"}}]
            """
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=2000,
                )
            )
            
            # Parse response
            analysis_text = response.text.strip()
            
            # Clean up response (remove markdown formatting if present)
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            elif analysis_text.startswith('```'):
                analysis_text = analysis_text.replace('```', '').strip()
            
            try:
                analysis_data = json.loads(analysis_text)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error: {str(e)}, response: {analysis_text}")
                # Fallback: simple sentiment analysis
                analysis_data = [{"sentiment": "neutral", "confidence": 0.5, "topic": "general", "impact": "medium"} 
                               for _ in headlines]
            
            # Ensure we have the right number of analyses
            if len(analysis_data) != len(headlines):
                logger.warning(f"Analysis count mismatch: {len(analysis_data)} vs {len(headlines)}")
                # Pad or truncate to match
                while len(analysis_data) < len(headlines):
                    analysis_data.append({"sentiment": "neutral", "confidence": 0.5, "topic": "general", "impact": "medium"})
                analysis_data = analysis_data[:len(headlines)]
            
            # Combine with original news data
            analyzed_news = []
            for i, (news_item, analysis) in enumerate(zip(news_items, analysis_data)):
                analyzed_news.append({
                    'headline': news_item.headline,
                    'date': news_item.date,
                    'url': news_item.url,
                    'source': news_item.source,
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'confidence': float(analysis.get('confidence', 0.5)),
                    'topic': analysis.get('topic', 'general'),
                    'impact': analysis.get('impact', 'medium')
                })
            
            logger.info(f"Successfully analyzed {len(analyzed_news)} news items with Gemini")
            return analyzed_news
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            # Fallback: return neutral sentiment for all
            return [{
                'headline': item.headline,
                'date': item.date,
                'url': item.url,
                'source': item.source,
                'sentiment': 'neutral',
                'confidence': 0.5,
                'topic': 'general',
                'impact': 'medium'
            } for item in news_items]
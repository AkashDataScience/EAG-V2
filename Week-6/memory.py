#!/usr/bin/env python3
"""
Memory Layer - Simple Facts Storage
"""

from typing import List, Any
import logging
import os
from google import genai
from models import StoreFactInput, RecallFactsInput, MemoryResult

logger = logging.getLogger(__name__)


class Memory:
    def __init__(self):
        self.facts = []
        
        # Initialize Gemini client for recall
        self.client = None
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        
    def store(self, input_data: StoreFactInput) -> MemoryResult:
        """Store a fact in memory"""
        try:
            self.facts.append(input_data.fact)
            logger.info(f"Stored fact: {input_data.fact}")
            
            return MemoryResult(
                success=True,
                message=f"Fact stored successfully",
                facts=[input_data.fact],
                total_facts=len(self.facts)
            )
        except Exception as e:
            logger.error(f"Error storing fact: {str(e)}")
            return MemoryResult(
                success=False,
                message=f"Error storing fact: {str(e)}",
                facts=[],
                total_facts=len(self.facts)
            )
        
    def recall(self, input_data: RecallFactsInput) -> MemoryResult:
        """Recall facts based on query using LLM"""
        try:
            if not self.facts:
                return MemoryResult(
                    success=True,
                    message="No facts in memory",
                    facts=[],
                    total_facts=0
                )
                
            # Use LLM to filter relevant facts
            prompt = f"""Given the memory facts: {self.facts}

Query: {input_data.query}

Return only the facts that are relevant to answering the query. If no facts are relevant, return an empty list.
Return the facts as a simple list, one fact per line."""

            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            # Parse the response to extract relevant facts
            response_text = response.text.strip()
            if not response_text or response_text.lower() in ['none', 'no facts', 'empty']:
                return MemoryResult(
                    success=True,
                    message="No relevant facts found",
                    facts=[],
                    total_facts=len(self.facts)
                )
                
            # Split response into individual facts
            relevant_facts = [fact.strip() for fact in response_text.split('\n') if fact.strip()]
            
            # Filter to only return facts that actually exist in memory
            filtered_facts = [fact for fact in relevant_facts if fact in self.facts]
            
            logger.info(f"Recalled {len(filtered_facts)} relevant facts for query: {input_data.query}")
            return MemoryResult(
                success=True,
                message=f"Found {len(filtered_facts)} relevant facts",
                facts=filtered_facts,
                total_facts=len(self.facts)
            )
            
        except Exception as e:
            logger.error(f"Error in recall: {str(e)}")
        
    def get_all_facts(self) -> MemoryResult:
        """Get all stored facts"""
        return MemoryResult(
            success=True,
            message=f"Retrieved all {len(self.facts)} facts",
            facts=self.facts,
            total_facts=len(self.facts)
        )
        
    def clear(self) -> MemoryResult:
        """Clear all facts"""
        cleared_count = len(self.facts)
        self.facts = []
        return MemoryResult(
            success=True,
            message=f"Cleared {cleared_count} facts from memory",
            facts=[],
            total_facts=0
        )
    
    # Convenience methods for backward compatibility
    def store_fact(self, fact: str) -> MemoryResult:
        """Convenience method to store a fact with string input"""
        return self.store(StoreFactInput(fact=fact))
        
    def recall_facts(self, query: str) -> List[str]:
        """Convenience method to recall facts and return just the list"""
        result = self.recall(RecallFactsInput(query=query))
        return result.facts
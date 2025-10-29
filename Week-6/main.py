#!/usr/bin/env python3
"""
4-Layer Cognitive Architecture for Stock Market Analysis
Main orchestrator that coordinates Perception, Memory, Decision-Making, and Action layers
"""

import uuid
import logging
import asyncio
from typing import Optional, List
from datetime import datetime

from models import (
    UserQuery, ParsedIntent, MemoryState, DecisionContext, ActionRequest,
    AgentConfig, SystemStatus, ActionType
)
from perception import Perception
from memory import Memory
from decision import DecisionLayer

# Configure logging - suppress third-party library logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress verbose third-party library logs
logging.getLogger('google_genai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class CognitiveAgent:
    """
    4-Layer Cognitive Architecture Agent
    Coordinates Perception, Memory, Decision-Making, and Action layers
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        
        # Initialize cognitive layers
        self.perception = Perception()
        self.memory = Memory()
        self.decision = DecisionLayer(config)
        
        logger.info("Cognitive Agent initialized with 3-layer architecture + MCP Action Layer")
    
    async def process_query(self, query_text: str) -> SystemStatus:
        """
        Process a user query through all cognitive layers
        
        Args:
            query_text: Natural language query from user
            
        Returns:
            SystemStatus: Final status of the analysis
        """
        session_id = str(uuid.uuid4())
        logger.info(f"Processing new query in session {session_id}: {query_text}")
        
        try:
            # LAYER 1: PERCEPTION - Understanding Input
            logger.info("🧠 PERCEPTION LAYER: Extracting facts and understanding preferences...")
            
            # Extract facts and ask clarifying questions using proper Pydantic method
            from models import ExtractFactsInput
            perception_result = self.perception.extract_facts(ExtractFactsInput(user_input=query_text))
            
            if not perception_result.success or not perception_result.facts:
                return SystemStatus(
                    session_id=session_id,
                    status="error",
                    current_layer="perception",
                    progress=0.0,
                    message=f"Could not extract facts from the query: {perception_result.message}"
                )
            
            logger.info(f"✅ Extracted facts: {perception_result.facts}")
            
            # Store all extracted facts in memory
            for key, value in perception_result.facts.items():
                fact = f"User fact - {key}: {value}"
                self.memory.store_fact(fact)
                logger.info(f"📝 Stored fact: {fact}")
            
            user_responses = self._ask_questions_to_user(perception_result.questions)
            
            # Store questions and responses in memory as single facts
            for i, (question, response) in enumerate(zip(perception_result.questions, user_responses), 1):
                qa_fact = f"User Q&A - Question {i}: {question} | Answer: {response}"
                self.memory.store_fact(qa_fact)
                
                logger.info(f"❓ Q{i}: {question}")
                logger.info(f"💬 A{i}: {response}")
                logger.info(f"📝 Stored Q&A fact: {qa_fact}")
            
            # Create a simple intent object for the decision layer
            from models import ParsedIntent
            parsed_intent = ParsedIntent(
                symbol=perception_result.facts.get("symbol", "RELIANCE.NS"),
                company_name=perception_result.facts.get("symbol", "Reliance Industries"),
                task_type=perception_result.facts.get("analysis_type", "sentiment"),
                timeframe="1h",
                period="1mo",
                confidence=0.8,
                parameters={"original_facts": perception_result.facts, "questions_asked": perception_result.questions}
            )
            
            # LAYER 2: MEMORY - Simple facts storage
            logger.info("💾 MEMORY LAYER: Ready for facts storage...")
            
            # LAYER 3 & 4: AI-DRIVEN DECISION & ACTION via MCP
            logger.info("🤔 Starting AI-driven analysis via MCP...")
            
            # Execute AI-driven analysis (Week-5 pattern)
            analysis_result = await self.decision.execute_analysis(parsed_intent, self.memory)
            
            if analysis_result["success"]:
                status = "completed"
                message = f"AI-driven analysis completed in {analysis_result['iterations']} steps"
                completion = 1.0
            else:
                status = "error"
                message = f"Analysis failed: {analysis_result.get('error', 'Unknown error')}"
                completion = analysis_result['iterations'] / self.config.max_iterations
            
            return SystemStatus(
                session_id=session_id,
                status=status,
                current_layer="action",
                progress=completion,
                message=message
            )
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return SystemStatus(
                session_id=session_id,
                status="error",
                current_layer="unknown",
                progress=0.0,
                message=f"Processing error: {str(e)}"
            )
    

    def get_session_summary(self, session_id: str) -> Optional[dict]:
        """Get summary of a session's analysis"""
        result = self.memory.get_all_facts()
        return {"facts": result.facts, "total_facts": result.total_facts}
    
    def cleanup_old_sessions(self) -> int:
        """Clean up old memory sessions"""
        self.memory.clear()
        return 1
    
    def _ask_questions_to_user(self, questions: List[str]) -> List[str]:
        """Ask questions to user and collect responses"""
        responses = []
        
        print("\n" + "="*60)
        print("🤔 I have some questions to better understand your needs:")
        print("="*60)
        
        for i, question in enumerate(questions, 1):
            print(f"\n❓ Question {i}: {question}")
            
            # Get user input
            try:
                response = input("💬 Your answer: ").strip()
                
                # Handle empty responses
                if not response:
                    response = "No specific preference"
                    print(f"   (Using default: {response})")
                
                responses.append(response)
                
            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C or EOF gracefully
                print("\n⚠️  Input interrupted. Using default responses for remaining questions.")
                remaining_count = len(questions) - len(responses)
                responses.extend(["No specific preference"] * remaining_count)
                break
            except Exception as e:
                # Handle any other input errors
                logger.warning(f"Input error: {str(e)}. Using default response.")
                responses.append("No specific preference")
        
        print("\n" + "="*60)
        print("✅ Thank you for your responses! Proceeding with analysis...")
        print("="*60 + "\n")
        
        return responses


async def main():
    """Main function for interactive testing"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Create agent configuration
    config = AgentConfig(
        gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
        news_api_key=os.getenv('NEWS_API_KEY', ''),
        max_iterations=15,
        confidence_threshold=0.6,
        memory_retention_hours=24
    )
    
    if not config.gemini_api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        print("Please set your Gemini API key in .env file")
        return
    
    # Create cognitive agent
    agent = CognitiveAgent(config)
    
    print("🧠 4-Layer Cognitive Architecture Stock Analysis Agent")
    print("=" * 60)
    print("🔍 Perception Layer: Understanding natural language queries")
    print("💾 Memory Layer: Storing analysis state and results")
    print("🤔 Decision Layer: Planning optimal analysis workflow (via MCP)")
    print("🔧 Action Layer: Executing analysis operations (MCP Server)")
    print("=" * 60)
    
    while True:
        try:
            # Get user input
            query = input("\n📊 Enter your analysis request (or 'quit' to exit): ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                print("Please enter a valid query.")
                continue
            
            print(f"\n🚀 Processing: {query}")
            print("-" * 40)
            
            # Process the query
            status = await agent.process_query(query)
            
            # Display results
            print(f"\n📋 Analysis Results:")
            print(f"Session ID: {status.session_id}")
            print(f"Status: {status.status}")
            print(f"Progress: {status.progress:.1%}")
            print(f"Message: {status.message}")
            
            # Get detailed session summary
            summary = agent.get_session_summary(status.session_id)
            if summary:
                print(f"\n📊 Session Summary:")
                print(f"Symbol: {summary['symbol']}")
                print(f"Company: {summary['company_name']}")
                print(f"Completion: {summary['completion_percentage']:.1%}")
                print(f"Data Points: {summary['data_counts']}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
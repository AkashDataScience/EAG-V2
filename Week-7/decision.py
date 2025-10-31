import os
from dotenv import load_dotenv
from google import genai
import logging
from datetime import datetime
from typing import List, Optional
from models import PerceptionResult, MemoryItem, DecisionResult, VideoSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.decision")

load_dotenv()

def log(stage: str, msg: str):
    """Log a message with timestamp and stage"""
    now = datetime.now().strftime("%H:%M:%S")
    logger.debug(f"[{now}] [{stage}] {msg}")

class Decision:
    def __init__(self):
        """Initialize the decision component."""
        log("decision", "Initializing Decision component")
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not found in environment variables")
                logger.info("Decision component will provide informational responses only")
                self.client = None
            else:
                log("decision", "GEMINI_API_KEY found in environment variables")
                self.client = genai.Client(api_key=api_key)
                log("decision", "Gemini API initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Gemini API: {e}")
            logger.error("Traceback:", exc_info=True)
            self.client = None
    
    def generate_response(self, perception: PerceptionResult, memory_items: List[MemoryItem]) -> str:
        """
        Generate a response based on perception and memory.
        Use this for the fallback case when no final answer is provided.
        
        Args:
            perception: The perception result containing query and intent
            memory_items: List of memory items from the memory component
            
        Returns:
            Generated response as a string
        """
        log("decision", f"Generating response for query: {perception.query}")
        
        # Extract video segments
        video_segments = []
        conversation_history = []
        
        for item in memory_items:
            if hasattr(item, 'type'):
                # Handle different types of memory items
                if item.type == "video_segments":
                    segments = item.content
                    log("decision", f"Found {len(segments)} video segments")
                    video_segments.extend(segments)
                elif item.type == "conversation_history":
                    log("decision", "Found conversation history")
                    conversation_history = item.content
        
        # Format video segments for the prompt
        memory_segments = []
        segment_count = min(len(video_segments), 10)  # Limit to top 10 for prompt length
        
        log("decision", f"Processing {segment_count} video segments for prompt")
        for i, segment in enumerate(video_segments[:segment_count]):
            try:
                # Format timestamp for readability
                minutes, seconds = divmod(int(segment.start_time), 60)
                timestamp = f"{minutes}:{seconds:02d}"
                
                # Format segment info
                segment_info = f"Segment {i+1} from '{segment.video_title}' (timestamp: {timestamp})"
                memory_segments.append(f"{segment_info}\n{segment.text}")
            except Exception as e:
                log("decision", f"Error formatting video segment {i}: {e}")
        
        # Format conversation history if available
        conversation_context = ""
        if conversation_history:
            log("decision", f"Including {len(conversation_history)} conversation history items")
            conv_items = []
            for i, conv in enumerate(conversation_history):
                if 'query' in conv and 'response' in conv:
                    conv_items.append(f"User: {conv['query']}\nAssistant: {conv['response']}")
                elif 'text' in conv:
                    conv_items.append(conv['text'])
            
            if conv_items:
                conversation_context = "## Previous Conversation\n" + "\n\n".join(conv_items)
        
        # Combine all segments
        memory_text = "\n\n".join(memory_segments)
        
        # Build the full prompt
        system_prompt = f"""🤖 ROLE AND GOAL
You are a YouTube video transcript assistant with expert reasoning abilities. Your task is to respond to queries about YouTube video content using only information from the provided transcript segments.

📝 QUERY CONTEXT
- User Query: "{perception.query}"
- Detected Intent: {perception.intent}
- Key Entities: {', '.join(perception.entities) if perception.entities else 'None detected'}

📋 TRANSCRIPT SEGMENTS
{memory_text}

{conversation_context}

📊 RESPONSE GUIDELINES
1. Analyze the transcript segments thoroughly before responding
2. Structure your response clearly using Markdown
3. ALWAYS quote directly from the transcript when referencing specific content
4. Include relevant timestamps when available
5. For specific claims, mention which video and timestamp the information comes from

⚠️ CRITICAL RULES
- NEVER fabricate or assume information not present in the transcript segments
- If the transcript segments don't contain sufficient information to answer the query, clearly state this
- Precision is more important than comprehensiveness - be accurate with what you know
"""
        
        # Generate a response using Gemini API
        log("decision", "Calling Gemini API to generate response")
        
        try:
            if not self.client:
                log("decision", "No Gemini client available, returning default response")
                return "I don't have enough information to answer that question based on the video content."
            else:
                # Make the API call with error handling
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=system_prompt
                )
                
                # Check if response has text attribute and is not empty
                if hasattr(response, 'text') and response.text.strip():
                    log("decision", "Successfully generated response")
                    return response.text
                else:
                    log("decision", "Empty response received from Gemini API")
                    return "I couldn't generate a proper response. Please try again or rephrase your query."
                
        except Exception as e:
            log("decision", f"Error calling Gemini API: {e}")
            return "I encountered an issue while processing your query. Please try again."

    def generate_plan(self, perception: PerceptionResult, memory_items: List[MemoryItem], tool_descriptions: Optional[str] = None) -> str:
        """Generate a plan based on perception and memory.
        
        Args:
            perception: The perception result containing query and intent
            memory_items: List of memory items from the memory component
            tool_descriptions: Description of available tools
            
        Returns:
            A plan string (either FUNCTION_CALL or FINAL_ANSWER)
        """
        log("decision", f"Generating plan for query: {perception.query}")
        
        # Extract memory texts
        memory_texts = []
        for item in memory_items:
            if hasattr(item, 'type'):
                if item.type == "video_segments":
                    segments = item.content
                    for segment in segments:
                        memory_texts.append(f"- Video segment from '{segment.video_title}' at {int(segment.start_time)}s: {segment.text[:100]}...")
                elif item.type == "conversation_history":
                    history = item.content
                    for h in history:
                        if 'text' in h:
                            memory_texts.append(f"- Previous memory: {h['text'][:100]}...")
                        elif 'query' in h and 'response' in h:
                            memory_texts.append(f"- Previous conversation: Q: {h['query'][:50]}... A: {h['response'][:50]}...")
                else:
                    memory_texts.append(f"- {item.type}: {str(item.content)[:100]}...")
        
        memory_context = "\n".join(memory_texts) or "None"
        tool_context = f"\nYou have access to the following tools:\n{tool_descriptions}" if tool_descriptions else ""
        
        prompt = f"""
You are a reasoning-driven AI agent with access to tools. Your job is to solve the user's request step-by-step by reasoning through the problem, selecting a tool if needed, and continuing until the FINAL_ANSWER is produced.{tool_context}

Always follow this loop:

1. Think step-by-step about the problem.
2. If a tool is needed, respond using the format:
   FUNCTION_CALL: tool_name|param1=value1|param2=value2
3. When the final answer is known, respond using:
   FINAL_ANSWER: [your final result]

Guidelines:
- Respond using EXACTLY ONE of the formats above per step.
- Do NOT include extra text, explanation, or formatting.
- Use nested keys (e.g., input.string) and square brackets for lists.
- You can reference these relevant memories:
{memory_context}

Input Summary:
- User input: "{perception.query}"
- Intent: {perception.intent or 'Unknown'}
- Entities: {', '.join(perception.entities) if perception.entities else 'None'}
- Tool hint: {perception.tool_hint or 'None'}

IMPORTANT:
- 🚫 Do NOT invent tools. Use only the tools listed below.
- 📄 If the question relates to factual knowledge about videos, use the 'search_transcripts' tool to look for the answer.
- 🧠 If the previous tool output already contains sufficient information, DO NOT search again. Instead, summarize the relevant facts and respond with: FINAL_ANSWER: [your answer]
- Only repeat `search_transcripts` if the last result was irrelevant or empty.
- ❌ Do NOT repeat function calls with the same parameters.
- 💥 If unsure or no tool fits, respond with: FINAL_ANSWER: [unknown]
- ✅ You have only 3 attempts. Final attempt must be FINAL_ANSWER
"""
        
        try:
            log("decision", "Calling Gemini API")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw = response.text.strip()
            log("decision", f"LLM output: {raw}")
            
            for line in raw.splitlines():
                if line.strip().startswith("FUNCTION_CALL:") or line.strip().startswith("FINAL_ANSWER:"):
                    return line.strip()
            
            return raw.strip()
            
        except Exception as e:
            log("decision", f"⚠️ Decision generation failed: {e}")
            return "FINAL_ANSWER: I encountered an error and couldn't process your query." 
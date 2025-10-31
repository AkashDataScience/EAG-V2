import os
import json
import re
import logging
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from google import genai
from models import PerceptionResult

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.perception")

def log(stage: str, msg: str):
    """Log a message with timestamp and stage"""
    now = datetime.now().strftime("%H:%M:%S")
    logger.debug(f"[{now}] [{stage}] {msg}")

class Perception:
    def __init__(self):
        """Initialize perception component with Gemini client."""
        log("perception", "Initializing Perception component")
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found in environment, using mock perception")
        self.client = genai.Client(api_key=api_key) if api_key else None
        log("perception", f"Gemini client initialized: {self.client is not None}")

    def extract_intent(self, query: str) -> PerceptionResult:
        """Extract intent and entities from a user query."""
        log("perception", f"Extracting intent from query: {query}")
        
        prompt = f"""
You are an AI that extracts structured facts from user input.

Input: "{query}"

Return the response as a Python dictionary with keys:
- intent: (brief phrase about what the user wants)
- entities: a list of strings representing keywords or values (e.g., ["YouTube", "transcript"])
- tool_hint: (name of the MCP tool that might be useful, if any)

Output only the dictionary on a single line. Do NOT wrap it in ```json or other formatting. Ensure `entities` is a list of strings, not a dictionary.
"""
        
        try:
            log("perception", "Calling Gemini API")
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            raw_response = response.text.strip()
            log("perception", f"Raw Gemini response: {raw_response}")

            # Strip Markdown backticks if present
            clean = re.sub(r"^```json|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()

            try:
                parsed = eval(clean)
            except Exception as e:
                log("perception", f"⚠️ Failed to parse cleaned output: {e}")
                raise

            # Fix common issues
            if isinstance(parsed.get("entities"), dict):
                parsed["entities"] = list(parsed["entities"].values())

            return PerceptionResult(query=query, **parsed)

        except Exception as e:
            log("perception", f"⚠️ Extraction failed: {e}")
            return PerceptionResult(query=query)
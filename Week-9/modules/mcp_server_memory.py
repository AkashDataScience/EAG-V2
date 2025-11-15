from mcp.server.fastmcp import FastMCP, Context
from typing import List, Optional, Dict, Any
from datetime import datetime
import yaml
from memory import MemoryManager  # Import MemoryManager to use its path structure
import json
import os
import sys
import signal
from pydantic import BaseModel  # Add this import

# Define input model here
class SearchInput(BaseModel):
    query: str

BASE_MEMORY_DIR = "memory"

# Get absolute path to config file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from modules to S9
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "profiles.yaml")

# Load config
try:
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
        MEMORY_CONFIG = config.get("memory", {}).get("storage", {})
        BASE_MEMORY_DIR = MEMORY_CONFIG.get("base_dir", "memory")
except Exception as e:
    print(f"Error loading config from {CONFIG_PATH}: {e}")
    sys.exit(1)

mcp = FastMCP("memory-service")

class MemoryStore:
    def __init__(self):
        self.memory_dir = BASE_MEMORY_DIR
        # self.memory_manager = None
        self.current_session = None  # Track current session
        os.makedirs(self.memory_dir, exist_ok=True)

    def load_session(self, session_id: str):
        """Load memory manager for a specific session."""
        # self.memory_manager = MemoryManager(session_id=session_id, memory_dir=self.memory_dir)
        self.current_session = session_id

    def _list_all_memories(self) -> List[Dict]:
        """Load all memory files using MemoryManager's date-based structure"""
        all_memories = []
        base_path = self.memory_dir  # Use the simple memory_dir path
        
        for year_dir in os.listdir(base_path):
            year_path = os.path.join(base_path, year_dir)
            if not os.path.isdir(year_path):
                continue
                
            for month_dir in os.listdir(year_path):
                month_path = os.path.join(year_path, month_dir)
                if not os.path.isdir(month_path):
                    continue
                    
                for day_dir in os.listdir(month_path):
                    day_path = os.path.join(month_path, day_dir)
                    if not os.path.isdir(day_path):
                        continue
                        
                    for file in os.listdir(day_path):
                        if file.endswith('.json'):
                            try:
                                with open(os.path.join(day_path, file), 'r') as f:
                                    session_memories = json.load(f)
                                    all_memories.extend(session_memories)  # Extend instead of append
                            except Exception as e:
                                print(f"Failed to load {file}: {e}")
        
        return all_memories

    def _get_conversation_flow(self, conversation_id: str = None) -> Dict:
        """Get sequence of interactions in a conversation"""
        if conversation_id is None:
            conversation_id = self.current_session
        
        # Use the session path we already know
        session_path = os.path.join(self.memory_dir, conversation_id)
        if not os.path.exists(session_path):
            return {"error": "Conversation not found"}
        
        interactions = []
        for file in sorted(os.listdir(session_path)):
            if file.endswith('.json'):
                with open(os.path.join(session_path, file), 'r') as f:
                    interactions.append(json.load(f))
        
        return {
            "conversation_flow": [
                {
                    "query": interaction.get("query", ""),
                    "intent": interaction.get("intent", ""),
                    "tool_calls": [
                        {
                            "tool": call["tool"],
                            "args": call["args"],
                            "result_summary": call.get("result_summary", "No summary available")
                        }
                        for call in interaction.get("tool_calls", [])
                    ],
                    "final_answer": interaction.get("final_answer", ""),
                    "tags": interaction.get("tags", [])
                }
                for interaction in interactions
            ],
            "timestamp_start": interactions[0].get("timestamp") if interactions else None,
            "timestamp_end": interactions[-1].get("timestamp") if interactions else None
        }

# Initialize global memory store
memory_store = MemoryStore()

def handle_shutdown(signum, frame):
    """Global shutdown handler"""
    sys.exit(0)

@mcp.tool()
async def get_current_conversations(input: Dict) -> Dict[str, Any]:
    """Get current session interactions. Usage: input={"input":{}} result = await mcp.call_tool('get_current_conversations', input)"""
    try:
        # Use absolute paths
        memory_root = os.path.join(ROOT_DIR, "memory")  # ROOT_DIR is already defined at top
        dt = datetime.now()
        
        # List all files in today's directory
        day_path = os.path.join(
            memory_root,
            str(dt.year),
            f"{dt.month:02d}",
            f"{dt.day:02d}"
        )
        
        if not os.path.exists(day_path):
            return {"error": "No sessions found for today"}
            
        # Get most recent session file
        session_files = [f for f in os.listdir(day_path) if f.endswith('.json')]
        if not session_files:
            return {"error": "No session files found"}
            
        latest_file = sorted(session_files)[-1]  # Get most recent
        file_path = os.path.join(day_path, latest_file)
        
        # Read and return contents
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        return {"result": {
                    "session_id": latest_file.replace(".json", ""),
                    "interactions": [
                        item for item in data 
                        if item.get("type") != "run_metadata"
                    ]
                }}
    except Exception as e:
        print(f"[memory] Error: {str(e)}")  # Debug print
        return {"error": str(e)}

@mcp.tool()
async def search_historical_conversations(input: SearchInput) -> Dict[str, Any]:
    """Search conversation memory between user and YOU. Usage: input={"input": {"query": "anmol singh"}} result = await mcp.call_tool('search_historical_conversations', input)"""
    try:
        all_memories = memory_store._list_all_memories()
        search_terms = input.query.lower().split()
        
        matches = []
        for memory in all_memories:
            # Only search in user query, final answer, and intent
            memory_content = " ".join([
                str(memory.get("user_query", "")),
                str(memory.get("final_answer", "")),
                str(memory.get("intent", ""))
            ]).lower()
            
            if all(term in memory_content for term in search_terms):
                # Only keep fields we want to return
                matches.append({
                    "user_query": memory.get("user_query", ""),
                    "final_answer": memory.get("final_answer", ""),
                    "timestamp": memory.get("timestamp", ""),
                    "intent": memory.get("intent", "")
                })

        # Sort by timestamp (most recent last)
        matches.sort(key=lambda x: x.get("timestamp", ""), reverse=False)
        
        # Count total words in matches
        total_words = 0
        filtered_matches = []
        WORD_LIMIT = 10000
        
        for match in matches:
            match_text = " ".join([
                str(match.get("user_query", "")),
                str(match.get("final_answer", ""))
            ])
            words_in_match = len(match_text.split())
            
            if total_words + words_in_match <= WORD_LIMIT:
                filtered_matches.append(match)
                total_words += words_in_match
            else:
                break
        
        return {"result": {
                    "status": "error",
                    "message": str(e)
                }}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("Memory MCP server starting...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "dev":
            mcp.run()
        else:
            mcp.run(transport="stdio")
    finally:
        print("\nShutting down memory service...")

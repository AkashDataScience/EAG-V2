from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
import sys
import logging
from pathlib import Path
import json
from typing import Dict, List, Any

# Import models
from models import SearchInput, SearchOutput

# Local imports
from utils.transcript_manager import TranscriptManager

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
logger = logging.getLogger("yt_rag.mcp")

def log(stage: str, msg: str):
    """Log a message with timestamp"""
    sys.stderr.write(f"[MCP:{stage}] {msg}\n")
    sys.stderr.flush()

# Initialize components
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

transcript_manager = TranscriptManager(
    transcripts_dir=DATA_DIR / "transcripts",
    index_dir=DATA_DIR / "faiss_index",
    chunk_size=60
)

# Initialize MCP server
mcp = FastMCP("YouTube RAG Tools")

@mcp.tool()
def search_transcripts(input: SearchInput) -> SearchOutput:
    """Search indexed YouTube transcripts for relevant content"""
    log("search", f"Searching transcripts for: {input.query}")
    
    try:
        results = transcript_manager.search(input.query, k=input.top_k)
        log("search", f"Found {len(results)} results")
        return SearchOutput(results=results)
    except Exception as e:
        log("error", f"Search error: {str(e)}")
        return SearchOutput(results=[])

if __name__ == "__main__":
    log("start", "Starting MCP server for YouTube RAG Tools")
    mcp.run() 
import asyncio
import logging
import threading
import os
import traceback
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, Optional
import time
from datetime import datetime
import json

# Import PADM components
from perception import Perception
from memory import Memory
from decision import Decision
from action import Action
from models import IndexingStatus, SearchResult
from utils.transcript_manager import TranscriptManager
from utils.status_tracker import StatusTracker
from collections_manager import CollectionsManager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),  # Only log to stdout
    ]
)

# Create logger instance for the agent module
logger = logging.getLogger("yt_rag.agent")

def log(stage: str, msg: str):
    """Log a message with timestamp and stage"""
    now = datetime.now().strftime("%H:%M:%S")
    logger.debug(f"[{now}] [{stage}] {msg}")

class Agent:
    def __init__(self):
        """Initialize the agent with all components."""
        logger.debug("Initializing Agent")
        # Set up data directories
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        logger.debug(f"Data directory: {self.data_dir}")
        
        # Initialize components
        logger.debug("Initializing TranscriptManager")
        self.transcript_manager = TranscriptManager(
            transcripts_dir=self.data_dir / "transcripts",
            index_dir=self.data_dir / "faiss_index"
        )
        logger.debug("Initializing StatusTracker")
        self.status_tracker = StatusTracker()
        
        # Initialize Collections Manager
        logger.debug("Initializing CollectionsManager")
        self.collections_manager = CollectionsManager(self.data_dir)
        
        # Initialize PADM components
        logger.debug("Initializing PADM components")
        self.perception = Perception()
        self.memory = Memory(self.transcript_manager)
        self.decision = Decision()
        self.action = Action()
        
        logger.info("Agent initialized with all components")

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query through the PADM cycle.
        
        Args:
            query: The user's natural language query
            
        Returns:
            Dictionary with answer and sources
        """
        logger.info(f"Processing query: {query}")
        start_time = time.time()
        max_steps = 3

        # Start up the MCP server
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        try:
            # Connect to MCP server
            async with stdio_client(server_params) as (read, write):
                log("agent", "Connection established, creating session...")
                
                async with ClientSession(read, write) as session:
                    log("agent", "Session created, initializing...")
                    await session.initialize()
                    log("agent", "MCP session initialized")

                    # Get available tools
                    tools_result = await session.list_tools()
                    tools = tools_result.tools
                    tool_descriptions = "\n".join(
                        f"- {tool.name}: {getattr(tool, 'description', 'No description')}" 
                        for tool in tools
                    )
                    log("agent", f"{len(tools)} tools loaded")

                    # Begin PADM loop
                    step = 0
                    session_id = f"session-{int(time.time())}"
                    original_query = query  # Store original query for reference
                    final_answer = None
                    sources = []

                    while step < max_steps:
                        log("loop", f"Step {step + 1} started")

                        # Perception: Extract intent and entities from query
                        perception_result = self.perception.extract_intent(query)
                        log("perception", f"Intent: {perception_result.intent}, Entities: {perception_result.entities}")

                        # Memory: Retrieve relevant transcript chunks
                        memory_items = self.memory.retrieve(perception_result)
                        log("memory", f"Retrieved {len(memory_items)} memory items")

                        # Decision: Generate plan based on perception and memory
                        plan = self.decision.generate_plan(perception_result, memory_items, tool_descriptions)
                        log("decision", f"Plan generated: {plan}")

                        # Check if we have a final answer
                        if plan.startswith("FINAL_ANSWER:"):
                            final_answer = plan.replace("FINAL_ANSWER:", "").strip()
                            log("agent", f"✅ FINAL RESULT: {final_answer}")
                            break

                        # Action: Execute tool if plan indicates tool use
                        try:
                            result = await self.action.execute_tool(session, tools, plan)
                            log("action", f"Tool {result.tool_name} returned: {result.result}")

                            # Add tool result to memory
                            self.memory.add_interaction({
                                "text": f"Tool call: {result.tool_name} with {result.arguments}, result: {result.result}",
                                "type": "tool_output",
                                "tool_name": result.tool_name,
                                "user_query": query,
                                "session_id": session_id
                            })

                            # Update query for next iteration
                            query = f"Original task: {original_query}\nPrevious output: {result.result}\nWhat should I do next?"

                        except Exception as e:
                            log("error", f"Tool execution failed: {e}")
                            traceback.print_exc()
                            break

                        step += 1

                    # If no final answer was generated, use the last memory items to create one
                    if not final_answer and memory_items:
                        log("agent", "No final answer generated, creating one from memory items")
                        response_text = self.decision.generate_response(perception_result, memory_items)
                        result = self.action.format_response(response_text, memory_items)
                        return {
                            "status": "success",
                            "answer": result.answer,
                            "sources": result.sources
                        }
                    elif not final_answer:
                        log("agent", "No final answer or memory items available")
                        return {
                            "status": "success",
                            "answer": "I couldn't find any relevant information to answer your question.",
                            "sources": []
                        }
                    else:
                        # Format the final answer with sources
                        sources = []
                        for item in memory_items:
                            if hasattr(item, 'type') and item.type == "video_segments":
                                for segment in item.content[:5]:  # Limit to top 5 segments
                                    sources.append({
                                        "video_title": segment.video_title,
                                        "url": segment.url,
                                        "timestamp": int(segment.start_time),
                                        "text": segment.text[:150] + "..." if len(segment.text) > 150 else segment.text
                                    })

                        log("agent", f"Found {len(sources)} sources for the answer")
                        
                        # Create formatted response with correct structure for frontend
                        formatted_response = {
                            "status": "success",
                            "answer": final_answer,
                            "sources": sources
                        }
                        
                        end_time = time.time()
                        log("agent", f"Query processing completed in {end_time - start_time:.2f} seconds")
                        return formatted_response

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            logger.error(traceback.format_exc())
            end_time = time.time()
            logger.debug(f"Query processing failed after {end_time - start_time:.2f} seconds")
            return {
                "error": str(e),
                "status": "error"
            }
    
    def index_video_task(self, operation_id: str, url: str):
        """Background task for indexing a video.
        
        Args:
            operation_id: Unique ID for tracking the operation
            url: YouTube video URL
        """
        logger.debug(f"Starting index_video_task for operation_id={operation_id}, url={url}")
        try:
            # Update status to fetching metadata
            logger.debug("Updating status to FETCHING_METADATA")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FETCHING_METADATA,
                "Fetching video metadata..."
            )
            
            # Extract video ID and get metadata
            logger.debug("Extracting video ID")
            video_id = self.transcript_manager.extract_video_id(url)
            logger.debug(f"Extracted video_id: {video_id}")
            if not video_id:
                logger.warning(f"Invalid YouTube URL: {url}")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Invalid YouTube URL",
                    "Could not extract video ID"
                )
                return
                
            logger.debug("Fetching video metadata")
            metadata = self.transcript_manager.get_video_metadata(url)
            logger.debug(f"Metadata retrieved: {metadata is not None}")
            if not metadata:
                logger.warning("Failed to fetch video metadata")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Failed to fetch video metadata",
                    "Could not retrieve video information"
                )
                return
                
            # Update status to fetching transcript
            logger.debug("Updating status to FETCHING_TRANSCRIPT")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FETCHING_TRANSCRIPT,
                "Fetching video transcript..."
            )
            
            # Get transcript
            logger.debug("Fetching transcript")
            transcript = self.transcript_manager.get_transcript(video_id)
            logger.debug(f"Transcript retrieved: {transcript is not None}")
            if not transcript:
                logger.warning("Failed to fetch transcript")
                self.status_tracker.update_status(
                    operation_id,
                    IndexingStatus.FAILED,
                    "Failed to fetch transcript",
                    "Could not retrieve video transcript"
                )
                return
                
            # Update status to indexing
            logger.debug("Updating status to INDEXING")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.INDEXING,
                "Processing and indexing transcript..."
            )
            
            # Index the video
            logger.debug("Starting transcript indexing")
            self.transcript_manager.index_video(url)
            
            # Auto-categorize the video
            logger.debug("Auto-categorizing video")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.INDEXING,
                "Auto-categorizing video content..."
            )
            
            video_metadata_with_id = {
                **metadata,
                'video_id': video_id
            }
            assigned_collections = self.collections_manager.auto_categorize_video(video_metadata_with_id)
            logger.debug(f"Video assigned to {len(assigned_collections)} collections")
            
            # Update status to completed
            logger.debug("Updating status to COMPLETED")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.COMPLETED,
                f"Video indexed and categorized into {len(assigned_collections)} collections!"
            )
            logger.debug(f"Indexing operation {operation_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Error in indexing task: {str(e)}")
            logger.error(traceback.format_exc())
            # Update status to failed if any error occurs
            logger.debug(f"Updating status to FAILED for operation {operation_id}")
            self.status_tracker.update_status(
                operation_id,
                IndexingStatus.FAILED,
                "An error occurred while indexing",
                str(e)
            )


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize agent
logger.debug("Initializing agent instance")
agent = Agent()

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler for Flask app."""
    logger.error(f"Global error handler triggered: {str(error)}")
    logger.error(traceback.format_exc())
    return jsonify({
        "error": str(error),
        "status": "error"
    }), 500

@app.route("/index_video", methods=["POST"])
def index_video():
    """Start an asynchronous video indexing operation."""
    logger.debug("index_video endpoint called")
    try:
        data = request.get_json()
        logger.debug(f"Request data: {data}")
        if not data or "url" not in data:
            logger.warning("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400
            
        url = data["url"]
        logger.debug(f"URL to index: {url}")
        
        # Create new operation
        logger.debug("Creating new operation")
        operation_id = agent.status_tracker.create_operation(url)
        logger.debug(f"Operation ID created: {operation_id}")
        
        # Start indexing in background thread
        logger.debug("Starting indexing thread")
        thread = threading.Thread(
            target=agent.index_video_task,
            args=(operation_id, url)
        )
        thread.daemon = True
        thread.start()
        logger.debug("Indexing thread started")
        
        response = {
            "operation_id": operation_id,
            "message": "Indexing started",
            "status": "pending"
        }
        logger.debug(f"Returning response: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error starting indexing: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/indexing_status/<operation_id>", methods=["GET"])
def get_indexing_status(operation_id):
    """Get the status of an indexing operation."""
    logger.debug(f"get_indexing_status endpoint called for operation_id={operation_id}")
    try:
        logger.debug("Retrieving status from status_tracker")
        status = agent.status_tracker.get_status(operation_id)
        logger.debug(f"Status retrieved: {status}")
        return jsonify(status)
    except ValueError as e:
        logger.warning(f"Operation not found: {operation_id}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 404
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route('/query', methods=['POST'])
def query():
    """Endpoint to query indexed transcripts."""
    logger.debug("query endpoint called")
    try:
        request_data = request.get_json()
        logger.debug(f"Request data: {request_data}")
        
        if not request_data or 'query' not in request_data:
            logger.warning("No query provided in request")
            return jsonify({"error": "No query provided", "status": "error"}), 400
        
        user_query = request_data['query']
        
        # Process query asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(agent.process_query(user_query))
        loop.close()
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        detailed_error = {
            "error": str(e),
            "status": "error",
            "traceback": traceback.format_exc().split("\n")
        }
        logger.debug(f"Returning error response: {detailed_error}")
        return jsonify(detailed_error), 500

@app.route('/list_indexed_videos', methods=['GET'])
def list_indexed_videos():
    """Endpoint to list all indexed videos without duplicates."""
    logger.debug("list_indexed_videos endpoint called")
    try:
        transcripts_dir = Path("data/transcripts")
        videos = []
        video_ids = set()  # To track already processed videos
        
        # Get all transcript files
        transcript_files = list(transcripts_dir.glob("transcript_*.json"))
        logger.debug(f"Found {len(transcript_files)} transcript files")
        
        for file_path in transcript_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(f.read())
                    
                    video_id = data.get("video_id")
                    if video_id and video_id not in video_ids:
                        metadata = data.get("metadata", {})
                        videos.append({
                            "video_id": video_id,
                            "title": metadata.get("title", "Unknown"),
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "author": metadata.get("author", "Unknown"),
                            "thumbnail_url": metadata.get("thumbnail_url", ""),
                            "length": metadata.get("length", 0),  # Duration in seconds
                            "views": metadata.get("views", 0)
                        })
                        video_ids.add(video_id)
            except Exception as e:
                logger.warning(f"Error processing transcript file {file_path}: {str(e)}")
                continue
        
        # Sort by title
        videos.sort(key=lambda x: x["title"])
        
        logger.debug(f"Returning {len(videos)} unique indexed videos")
        return jsonify({
            "status": "success",
            "count": len(videos),
            "videos": videos
        })
        
    except Exception as e:
        logger.error(f"Error listing indexed videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/collections", methods=["GET"])
def get_collections():
    """Get all collections"""
    logger.debug("get_collections endpoint called")
    try:
        collections = agent.collections_manager.get_collections()
        return jsonify({
            "status": "success",
            "collections": [collection.dict() for collection in collections]
        })
    except Exception as e:
        logger.error(f"Error getting collections: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/collections", methods=["POST"])
def create_collection():
    """Create a new collection"""
    logger.debug("create_collection endpoint called")
    try:
        data = request.get_json()
        if not data or "name" not in data:
            return jsonify({"error": "Collection name is required"}), 400
        
        collection_id = agent.collections_manager.create_collection(
            name=data["name"],
            description=data.get("description", ""),
            color=data.get("color", "#6366f1"),
            tags=data.get("tags", [])
        )
        
        return jsonify({
            "status": "success",
            "collection_id": collection_id,
            "message": "Collection created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating collection: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/collections/<collection_id>", methods=["GET"])
def get_collection_details(collection_id):
    """Get detailed information about a collection"""
    logger.debug(f"get_collection_details endpoint called for {collection_id}")
    try:
        summary = agent.collections_manager.get_collection_summary(collection_id, agent.transcript_manager)
        return jsonify({
            "status": "success",
            "summary": summary.dict()
        })
    except ValueError as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 404
    except Exception as e:
        logger.error(f"Error getting collection details: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/collections/<collection_id>/videos", methods=["POST"])
def add_video_to_collection(collection_id):
    """Add a video to a collection"""
    logger.debug(f"add_video_to_collection endpoint called")
    try:
        data = request.get_json()
        if not data or "video_id" not in data:
            return jsonify({"error": "Video ID is required"}), 400
        
        agent.collections_manager.add_video_to_collection(
            video_id=data["video_id"],
            collection_id=collection_id
        )
        
        return jsonify({
            "status": "success",
            "message": "Video added to collection"
        })
    except ValueError as e:
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 404
    except Exception as e:
        logger.error(f"Error adding video to collection: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/smart_playlists", methods=["POST"])
def create_smart_playlist():
    """Create a smart playlist"""
    logger.debug("create_smart_playlist endpoint called")
    try:
        data = request.get_json()
        if not data or "name" not in data or "query" not in data:
            return jsonify({"error": "Name and query are required"}), 400
        
        playlist_id = agent.collections_manager.create_smart_playlist(
            name=data["name"],
            query=data["query"],
            max_videos=data.get("max_videos", 20)
        )
        
        return jsonify({
            "status": "success",
            "playlist_id": playlist_id,
            "message": "Smart playlist created successfully"
        })
    except Exception as e:
        logger.error(f"Error creating smart playlist: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

@app.route("/collections/stats", methods=["GET"])
def get_categorization_stats():
    """Get categorization statistics"""
    logger.debug("get_categorization_stats endpoint called")
    try:
        stats = agent.collections_manager.get_categorization_stats()
        return jsonify({
            "status": "success",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting categorization stats: {str(e)}")
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == "__main__":
    logger.info("Starting Nexus Agent")
    app.run(debug=True) 
from typing import List, Dict, Any, Optional, Literal
import logging
import time
import json
import faiss
import numpy as np
import requests
from datetime import datetime
from pathlib import Path
from models import PerceptionResult, MemoryItem, VideoSegment

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("yt_rag.memory")

def log(stage: str, msg: str):
    """Log a message with timestamp and stage"""
    now = datetime.now().strftime("%H:%M:%S")
    logger.debug(f"[{now}] [{stage}] {msg}")

class Memory:
    """Store and retrieve information from indexed videos and past interactions."""
    
    def __init__(self, transcript_manager):
        """Initialize memory with transcript manager."""
        log("memory", "Initializing Memory component")
        self.transcript_manager = transcript_manager
        self.conversation_history = []
        self.embedding_url = "http://localhost:11434/api/embeddings"
        self.embedding_model = "nomic-embed-text"
        self.index = None
        self.memory_items = []
        log("memory", "Memory component initialized")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using local model."""
        response = requests.post(
            self.embedding_url,
            json={"model": self.embedding_model, "prompt": text}
        )
        response.raise_for_status()
        return np.array(response.json()["embedding"], dtype=np.float32)
        
    def retrieve(self, perception: PerceptionResult) -> List[MemoryItem]:
        """
        Retrieve memory items relevant to the perception result.
        
        Args:
            perception: PerceptionResult containing query and intent
            
        Returns:
            List of MemoryItem objects
        """
        log("memory", f"Retrieving memory items for perception: {perception.intent}")
        query = perception.query
        
        # First, search for relevant video segments
        segments = self.search_relevant_segments(query, top_k=5)
        memory_items = []
        
        # Add video segments as memory item
        if segments:
            memory_items.append(MemoryItem(
                type="video_segments",
                content=segments
            ))
            
        # Add recent conversation history
        recent_history = self.get_recent_interactions(3)
        if recent_history:
            memory_items.append(MemoryItem(
                type="conversation_history",
                content=recent_history
            ))
            
        log("memory", f"Retrieved {len(memory_items)} memory items with {len(segments)} video segments")
        return memory_items
    
    def retrieve_by_query(self, query: str, top_k: int = 3, session_filter: Optional[str] = None) -> List[MemoryItem]:
        """
        Alternative retrieve method that allows filtering by session ID.
        
        Args:
            query: Search query
            top_k: Number of results to return
            session_filter: Optional session ID to filter by
            
        Returns:
            List of MemoryItem objects
        """
        # If we have no memory items, just return an empty list
        if not self.memory_items:
            return []
            
        log("memory", f"Memory retrieval for: {query}")
        query_vec = self._get_embedding(query).reshape(1, -1)
        
        if self.index is None:
            log("memory", "No memory index available yet")
            return []
            
        # Search index
        D, I = self.index.search(query_vec, top_k * 2)  # Overfetch to allow filtering
        
        results = []
        for idx in I[0]:
            if idx >= len(self.memory_items):
                continue
                
            item = self.memory_items[idx]
            
            # Filter by session
            if session_filter and hasattr(item, 'session_id') and item.session_id != session_filter:
                continue
                
            results.append(item)
            if len(results) >= top_k:
                break
                
        log("memory", f"Retrieved {len(results)} memory items")
        return results
            
    def search_relevant_segments(self, query: str, top_k: int = 5) -> List[VideoSegment]:
        """
        Search for video segments relevant to the user query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant VideoSegment objects
        """
        if not query:
            log("memory", "Empty query provided for search")
            return []
            
        log("memory", f"Searching for segments matching query: '{query}'")
        start_time = time.time()
        
        try:
            log("memory", f"Performing search with top_k={top_k}")
            results = self.transcript_manager.search(query, k=top_k)
            
            if not results:
                log("memory", f"No results found for query: '{query}'")
                return []
                
            result_count = len(results)
            log("memory", f"Search returned {result_count} results")
            
            # Convert raw results to VideoSegment objects
            video_segments = []
            for i, result in enumerate(results):
                try:
                    segment = VideoSegment(
                        text=result.get('text', ''),
                        start_time=result.get('start_time', 0),
                        end_time=result.get('end_time', 0),
                        video_id=result.get('video_id', ''),
                        video_title=result.get('video_title', 'Unknown Video'),
                        url=result.get('url', ''),
                        score=1.0 - (i / len(results)) if len(results) > 1 else 1.0  # Simple score based on position
                    )
                    video_segments.append(segment)
                except Exception as e:
                    log("memory", f"Error creating VideoSegment from result: {e}")
            
            end_time = time.time()
            log("memory", f"Search completed in {end_time - start_time:.3f} seconds")
            return video_segments
            
        except Exception as e:
            log("memory", f"Error during search: {str(e)}")
            return []
            
    def add_interaction(self, interaction: Dict[str, Any]) -> None:
        """
        Add user interaction or tool result to memory.
        
        Args:
            interaction: Dict with interaction data
        """
        log("memory", f"Adding interaction of type: {interaction.get('type', 'unknown')}")
        
        if not interaction:
            log("memory", "Attempted to add empty interaction")
            return
            
        # Store in conversation history for MemoryItem retrieval
        if 'type' not in interaction:
            interaction['type'] = 'fact'
            
        # Add timestamp if not present
        if 'timestamp' not in interaction:
            interaction['timestamp'] = datetime.now().isoformat()
            
        # Create embedding and add to index
        try:
            text = interaction.get('text', '')
            if text:
                emb = self._get_embedding(text)
                
                # Initialize or add to index
                if self.index is None:
                    self.index = faiss.IndexFlatL2(len(emb))
                    
                self.index.add(np.stack([emb]))
                self.memory_items.append(interaction)
                log("memory", f"Added interaction to memory index, now {len(self.memory_items)} items")
        except Exception as e:
            log("memory", f"Error adding interaction to memory: {e}")
            
        # Also add to conversation history
        self.conversation_history.append(interaction)
        history_length = len(self.conversation_history)
        log("memory", f"Conversation history updated, now contains {history_length} interactions")
        
    def get_recent_interactions(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Get the most recent interactions.
        
        Args:
            count: Number of interactions to retrieve
            
        Returns:
            List of recent interactions
        """
        log("memory", f"Retrieving {count} recent interactions")
        history_length = len(self.conversation_history)
        
        if history_length == 0:
            log("memory", "Conversation history is empty")
            return []
            
        # Get the last 'count' interactions
        recent = self.conversation_history[-count:] if count < history_length else self.conversation_history
        log("memory", f"Retrieved {len(recent)} recent interactions")
        
        return recent 
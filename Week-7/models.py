from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal, Union
from enum import Enum


class PerceptionResult(BaseModel):
    """Result from the Perception component"""
    query: str
    intent: Optional[str] = None
    entities: List[str] = []
    tool_hint: Optional[str] = None


class VideoSegment(BaseModel):
    """Represents a segment of a video with transcript text"""
    text: str
    start_time: float
    end_time: float
    video_id: str
    video_title: str
    url: str
    score: Optional[float] = None


class MemoryItem(BaseModel):
    """Represents a memory item that can contain different types of content"""
    type: str  # "video_segments" or "conversation_history"
    content: Any  # Either List[VideoSegment] or conversation history


class DecisionResult(BaseModel):
    """Result from the Decision component"""
    response: str
    should_search_more: bool = False
    intent: Optional[str] = None
    plan: Optional[str] = None


class ActionResult(BaseModel):
    """Result from the Action component"""
    response: str
    video_segments: List[Any] = []


class SearchResult(BaseModel):
    """Result format for search queries"""
    answer: str
    sources: List[Dict[str, Any]] = []


class IndexingStatus(str, Enum):
    PENDING = "pending"
    FETCHING_METADATA = "fetching_metadata"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


# MCP Tool Input/Output models
class SearchInput(BaseModel):
    query: str
    top_k: int = 3


class SearchOutput(BaseModel):
    results: List[Dict[str, Any]]
    

class IndexInput(BaseModel):
    url: str


class IndexOutput(BaseModel):
    operation_id: str
    status: str
    message: str


class StatusInput(BaseModel):
    operation_id: str


class StatusOutput(BaseModel):
    status: str
    message: str
    elapsed_seconds: float
    error: Optional[str] = None


# Smart Collections Models
class Collection(BaseModel):
    id: str
    name: str
    description: str
    color: str
    created_at: str
    video_count: int
    tags: List[str] = []
    is_auto: bool = False  # Auto-generated vs manual


class VideoCollection(BaseModel):
    video_id: str
    collection_id: str
    added_at: str
    confidence: Optional[float] = None  # For auto-categorization


class CollectionSummary(BaseModel):
    collection: Collection
    videos: List[Dict[str, Any]]
    total_duration: int
    topics: List[str] 
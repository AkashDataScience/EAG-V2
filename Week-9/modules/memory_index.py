# modules/memory_index.py
"""
Smart historical conversation indexing and memory summarization.
Replaces raw memory items with compact, relevant summaries.
"""

from typing import List, Dict, Any
from difflib import SequenceMatcher
from modules.memory import MemoryItem, MemoryManager
import time


def calculate_relevance_score(
    item: MemoryItem,
    query_terms: List[str],
    current_time: float
) -> float:
    """
    Score memory item by multiple factors:
    - Semantic relevance to query
    - Recency
    - Tool success
    - Length penalty
    """
    score = 0.0
    item_text = item.text.lower()
    
    # 1. Semantic relevance (0-40 points)
    relevance = 0.0
    for term in query_terms:
        if term.lower() in item_text:
            relevance += 10.0
    score += min(relevance, 40.0)
    
    # 2. Recency bonus (0-20 points)
    # More recent items get higher scores
    age_seconds = current_time - item.timestamp
    age_hours = age_seconds / 3600
    recency_score = max(0, 20.0 - (age_hours * 2))  # Decay over time
    score += recency_score
    
    # 3. Tool success bonus (0-20 points)
    if item.type == "tool_output" and item.success:
        score += 20.0
    
    # 4. Length penalty (0 to -10 points)
    # Penalize very long items
    text_length = len(item.text)
    if text_length > 1000:
        score -= 10.0
    elif text_length > 500:
        score -= 5.0
    
    # 5. Diversity bonus (handled externally)
    
    return score


def extract_query_terms(user_input: str) -> List[str]:
    """Extract key terms from user query."""
    # Simple tokenization - split on whitespace and punctuation
    import re
    terms = re.findall(r'\b\w+\b', user_input.lower())
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    terms = [t for t in terms if t not in stop_words and len(t) > 2]
    
    return terms


def compress_to_bullets(items: List[MemoryItem], max_bullets: int = 10) -> str:
    """Compress memory items into bullet points."""
    bullets = []
    
    for i, item in enumerate(items[:max_bullets]):
        # Truncate long text
        text = item.text
        if len(text) > 150:
            text = text[:147] + "..."
        
        # Format based on type
        if item.type == "tool_output":
            status = "✓" if item.success else "✗"
            bullet = f"- {status} {item.tool_name}: {text}"
        else:
            bullet = f"- {text}"
        
        bullets.append(bullet)
    
    return "\n".join(bullets)


def get_compact_memory_summary(
    user_input: str,
    memory_manager: MemoryManager,
    max_chars: int = 1500
) -> str:
    """
    Get compact memory summary relevant to user input.
    
    Process:
    1. Try search_historical_conversations (if available)
    2. Fallback to get_current_conversations
    3. Score items by relevance, recency, success, etc.
    4. Select top items until ≤max_chars
    5. Compress to ≤10 bullet points
    """
    
    # Extract query terms
    query_terms = extract_query_terms(user_input)
    
    # Get memory items
    # Try historical search first (if method exists)
    try:
        if hasattr(memory_manager, 'search_historical_conversations'):
            items = memory_manager.search_historical_conversations(query_terms)
        else:
            items = memory_manager.get_session_items()
    except:
        items = memory_manager.get_session_items()
    
    if not items:
        return "No relevant memory."
    
    # Score all items
    current_time = time.time()
    scored_items = []
    
    for item in items:
        score = calculate_relevance_score(item, query_terms, current_time)
        scored_items.append((score, item))
    
    # Sort by score (descending)
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    # Select top items until max_chars
    selected_items = []
    total_chars = 0
    seen_tools = set()
    
    for score, item in scored_items:
        item_length = len(item.text)
        
        # Diversity bonus: prefer different tool types
        if item.type == "tool_output" and item.tool_name:
            if item.tool_name in seen_tools:
                continue  # Skip duplicate tool types
            seen_tools.add(item.tool_name)
        
        if total_chars + item_length <= max_chars:
            selected_items.append(item)
            total_chars += item_length
        
        if len(selected_items) >= 10:
            break
    
    # Compress to bullets
    if not selected_items:
        return "No relevant memory."
    
    summary = compress_to_bullets(selected_items, max_bullets=10)
    
    return summary


def get_recent_successful_tools(memory_manager: MemoryManager, limit: int = 5) -> List[str]:
    """Get list of recently successful tool names."""
    items = memory_manager.get_session_items()
    successful_tools = []
    
    for item in reversed(items):
        if item.type == "tool_output" and item.success and item.tool_name:
            if item.tool_name not in successful_tools:
                successful_tools.append(item.tool_name)
            if len(successful_tools) >= limit:
                break
    
    return successful_tools

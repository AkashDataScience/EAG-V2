# modules/historical_index.py
"""
Smart historical conversation indexing and scoring system.
Provides high-signal historical context to improve agent planning.
"""

import json
import os
import time
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import math


def extract_query_terms(user_input: str) -> List[str]:
    """Extract key nouns/verbs from user input for search."""
    # Simple tokenization - split on whitespace and punctuation
    terms = re.findall(r'\b\w+\b', user_input.lower())
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
        'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
    }
    
    terms = [t for t in terms if t not in stop_words and len(t) > 2]
    
    return terms


def simple_cosine_similarity(text1: str, text2: str) -> float:
    """
    Simple word-based cosine similarity.
    Returns value between 0.0 and 1.0.
    """
    words1 = set(extract_query_terms(text1))
    words2 = set(extract_query_terms(text2))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    
    # Jaccard similarity as approximation
    union = words1.union(words2)
    similarity = len(intersection) / len(union) if union else 0.0
    
    return similarity


def calculate_historical_score(
    item: Dict[str, Any],
    query_terms: List[str],
    current_time: float,
    seen_texts: set
) -> float:
    """
    Calculate composite score for historical memory item.
    
    Weights:
    - Recency: 0.30
    - Semantic Relevance: 0.30
    - Tool Success: 0.15
    - Provenance: 0.10
    - Length Penalty: 0.10
    - Diversity Bonus: 0.05
    """
    score = 0.0
    
    # Combine user + assistant text for scoring
    item_text = f"{item.get('user', '')} {item.get('assistant', '')}".lower()
    
    # 1. RECENCY (0.30) - exponential decay
    try:
        item_timestamp = item.get('timestamp', '')
        if isinstance(item_timestamp, str):
            item_time = datetime.fromisoformat(item_timestamp.replace('Z', '+00:00')).timestamp()
        else:
            item_time = float(item_timestamp)
        
        age_hours = (current_time - item_time) / 3600
        # Decay over 7 days (168 hours)
        recency_score = math.exp(-age_hours / 168) * 0.30
        score += recency_score
    except:
        # If timestamp parsing fails, give minimal recency score
        score += 0.05
    
    # 2. SEMANTIC RELEVANCE (0.30)
    query_text = ' '.join(query_terms)
    similarity = simple_cosine_similarity(query_text, item_text)
    score += similarity * 0.30
    
    # 3. TOOL SUCCESS SIGNAL (0.15)
    if item.get('success', False) and item.get('tool'):
        score += 0.15
    elif item.get('tool'):
        score += 0.05  # Tool was used but maybe not successful
    
    # 4. PROVENANCE (0.10)
    provenance_score = 0.0
    if item.get('timestamp'):
        provenance_score += 0.03
    if item.get('tool'):
        provenance_score += 0.04
    if item.get('result'):
        provenance_score += 0.03
    score += provenance_score
    
    # 5. LENGTH PENALTY (0.10)
    text_length = len(item_text)
    if text_length < 200:
        score += 0.10
    elif text_length < 500:
        score += 0.07
    elif text_length < 1000:
        score += 0.04
    else:
        score += 0.01
    
    # 6. DIVERSITY BONUS (0.05)
    # Penalize if very similar to already seen items
    is_diverse = True
    for seen_text in seen_texts:
        if simple_cosine_similarity(item_text, seen_text) > 0.8:
            is_diverse = False
            break
    
    if is_diverse:
        score += 0.05
    
    return score


def compress_to_bullets(
    items: List[tuple[float, Dict[str, Any]]],
    max_bullets: int = 10,
    max_chars: int = 1500
) -> str:
    """
    Compress scored items into bullet points.
    Format: "- YYYY-MM-DD — <intent> — <summary> — [tool: X] — score: 0.xx"
    """
    bullets = []
    total_chars = 0
    
    for score, item in items[:max_bullets]:
        # Extract date
        try:
            timestamp = item.get('timestamp', '')
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
            else:
                date_str = "Unknown"
        except:
            date_str = "Unknown"
        
        # Extract intent (first 50 chars of user query)
        user_query = item.get('user', 'No query')
        intent = user_query[:50] + "..." if len(user_query) > 50 else user_query
        
        # Extract summary (first 80 chars of assistant response)
        assistant_resp = item.get('assistant', 'No response')
        summary = assistant_resp[:80] + "..." if len(assistant_resp) > 80 else assistant_resp
        
        # Tool info
        tool_name = item.get('tool', 'none')
        
        # Format bullet
        bullet = f"- {date_str} — {intent} — {summary} — [tool: {tool_name}] — score: {score:.2f}"
        
        # Check if adding this bullet exceeds max_chars
        if total_chars + len(bullet) + 1 > max_chars:
            break
        
        bullets.append(bullet)
        total_chars += len(bullet) + 1  # +1 for newline
    
    return "\n".join(bullets) if bullets else ""


def get_historical_context(
    user_input: str,
    memory_path: str = "historical_conversation_store.json"
) -> str:
    """
    Get smart historical context for agent planning.
    
    Returns:
        Compressed bullet-point summary (≤1500 chars, ≤10 bullets)
    """
    
    # A) LOAD MEMORY
    if not os.path.exists(memory_path):
        return "No relevant historical context found."
    
    try:
        with open(memory_path, 'r', encoding='utf-8') as f:
            memory_items = json.load(f)
    except Exception as e:
        return "No relevant historical context found."
    
    if not memory_items or not isinstance(memory_items, list):
        return "No relevant historical context found."
    
    # B) EXTRACT QUERY TERMS
    query_terms = extract_query_terms(user_input)
    
    if not query_terms:
        return "No relevant historical context found."
    
    # C) SCORE EACH MEMORY ITEM
    current_time = time.time()
    scored_items = []
    seen_texts = set()
    
    for item in memory_items:
        if not isinstance(item, dict):
            continue
        
        score = calculate_historical_score(item, query_terms, current_time, seen_texts)
        scored_items.append((score, item))
        
        # Add to seen texts for diversity tracking
        item_text = f"{item.get('user', '')} {item.get('assistant', '')}".lower()
        seen_texts.add(item_text)
    
    # D) SELECT TOP ITEMS
    # Sort by score descending
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    # Compress to bullets
    summary = compress_to_bullets(scored_items, max_bullets=10, max_chars=1500)
    
    # E) FAILSAFE RULE
    if not summary or len(summary.strip()) == 0:
        return "No relevant historical context found."
    
    return summary


def append_to_historical_store(
    user_input: str,
    assistant_output: str,
    tool_name: Optional[str] = None,
    success: bool = False,
    result: Optional[str] = None,
    memory_path: str = "historical_conversation_store.json"
) -> None:
    """
    Append new interaction to historical conversation store.
    """
    # Load existing
    if os.path.exists(memory_path):
        try:
            with open(memory_path, 'r', encoding='utf-8') as f:
                memory_items = json.load(f)
        except:
            memory_items = []
    else:
        memory_items = []
    
    # Create new entry
    new_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_input,
        "assistant": assistant_output,
        "tool": tool_name,
        "success": success,
        "result": result
    }
    
    # Append
    memory_items.append(new_entry)
    
    # Save
    with open(memory_path, 'w', encoding='utf-8') as f:
        json.dump(memory_items, f, indent=2, ensure_ascii=False)

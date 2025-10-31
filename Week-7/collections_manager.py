"""
Smart Collections Manager for Nexus
Handles auto-categorization, manual collections, and smart playlists
"""

import json
import uuid
import os
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from dotenv import load_dotenv
from google import genai

load_dotenv()

from models import Collection, VideoCollection, CollectionSummary


class CollectionsManager:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.collections_dir = self.data_dir / "collections"
        self.collections_dir.mkdir(parents=True, exist_ok=True)
        
        self.collections_file = self.collections_dir / "collections.json"
        self.video_collections_file = self.collections_dir / "video_collections.json"
        
        # Embedding service
        self.embed_url = "http://localhost:11434/api/embeddings"
        self.embed_model = "nomic-embed-text"
        
        # Initialize Gemini AI for LLM-based categorization
        api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = genai.Client(api_key=api_key) if api_key else None
        if not self.gemini_client:
            print("❌ GEMINI_API_KEY not found - Auto-categorization will be disabled")
            print("💡 Set GEMINI_API_KEY environment variable to enable AI categorization")
        else:
            print("🤖 LLM-powered categorization enabled with Gemini AI")
        
        # Load existing data
        self.collections = self._load_collections()
        self.video_collections = self._load_video_collections()
        
        # Base categories for LLM reference (no keywords needed)
        self.base_categories = {
            "programming": {
                "color": "#3b82f6",
                "description": "Programming and software development content"
            },
            "machine_learning": {
                "color": "#8b5cf6", 
                "description": "Machine Learning and AI content"
            },
            "web_development": {
                "color": "#10b981",
                "description": "Web development and frontend/backend technologies"
            },
            "data_science": {
                "color": "#f59e0b",
                "description": "Data science and analytics content"
            },
            "tutorials": {
                "color": "#ef4444",
                "description": "Educational tutorials and guides"
            },
            "reviews": {
                "color": "#6366f1",
                "description": "Product reviews and comparisons"
            },
            "technology": {
                "color": "#14b8a6",
                "description": "General technology and innovation content"
            },
            "business": {
                "color": "#f97316",
                "description": "Business, entrepreneurship, and finance content"
            },
            "design": {
                "color": "#ec4899",
                "description": "Design, UI/UX, and creative content"
            },
            "science": {
                "color": "#84cc16",
                "description": "Science, research, and academic content"
            }
        }

    def _load_collections(self) -> Dict[str, Collection]:
        """Load collections from file"""
        if self.collections_file.exists():
            try:
                with open(self.collections_file, 'r') as f:
                    data = json.load(f)
                return {cid: Collection(**cdata) for cid, cdata in data.items()}
            except Exception as e:
                print(f"Error loading collections: {e}")
        return {}

    def _load_video_collections(self) -> List[VideoCollection]:
        """Load video-collection mappings from file"""
        if self.video_collections_file.exists():
            try:
                with open(self.video_collections_file, 'r') as f:
                    data = json.load(f)
                return [VideoCollection(**item) for item in data]
            except Exception as e:
                print(f"Error loading video collections: {e}")
        return []

    def _save_collections(self):
        """Save collections to file"""
        data = {cid: collection.dict() for cid, collection in self.collections.items()}
        with open(self.collections_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_video_collections(self):
        """Save video-collection mappings to file"""
        data = [vc.dict() for vc in self.video_collections]
        with open(self.video_collections_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using local model"""
        try:
            response = requests.post(
                self.embed_url,
                json={"model": self.embed_model, "prompt": text}
            )
            response.raise_for_status()
            return np.array(response.json()["embedding"], dtype=np.float32)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return np.zeros(384)  # Default embedding size

    def create_collection(self, name: str, description: str = "", color: str = "#6366f1", 
                         tags: List[str] = None, is_auto: bool = False) -> str:
        """Create a new collection"""
        collection_id = str(uuid.uuid4())
        collection = Collection(
            id=collection_id,
            name=name,
            description=description,
            color=color,
            created_at=datetime.now().isoformat(),
            video_count=0,
            tags=tags or [],
            is_auto=is_auto
        )
        
        self.collections[collection_id] = collection
        self._save_collections()
        
        print(f"Created collection: {name} ({collection_id})")
        return collection_id

    def add_video_to_collection(self, video_id: str, collection_id: str, confidence: float = None):
        """Add a video to a collection"""
        if collection_id not in self.collections:
            raise ValueError(f"Collection {collection_id} not found")
        
        # Check if already exists
        existing = next((vc for vc in self.video_collections 
                        if vc.video_id == video_id and vc.collection_id == collection_id), None)
        if existing:
            return
        
        video_collection = VideoCollection(
            video_id=video_id,
            collection_id=collection_id,
            added_at=datetime.now().isoformat(),
            confidence=confidence
        )
        
        self.video_collections.append(video_collection)
        
        # Update collection video count
        self.collections[collection_id].video_count += 1
        
        self._save_video_collections()
        self._save_collections()

    def auto_categorize_video(self, video_metadata: Dict[str, Any]) -> List[str]:
        """Automatically categorize a video using LLM-based analysis"""
        video_id = video_metadata.get('video_id')
        title = video_metadata.get('title', '')
        description = video_metadata.get('description', '')
        
        print(f"🤖 Auto-categorizing video: {title}")
        
        if not self.gemini_client:
            print("❌ LLM not available - skipping categorization")
            return []
        
        assigned_collections = []
        
        # Use LLM for intelligent categorization
        llm_categories = self._llm_categorize_video(title, description)
        for category_data in llm_categories:
            category_name = category_data['category']
            confidence = category_data['confidence']
            
            # Create collection if it doesn't exist
            collection_id = self._ensure_auto_collection_from_llm(category_name, category_data)
            
            # Add video to collection
            self.add_video_to_collection(video_id, collection_id, confidence)
            assigned_collections.append(collection_id)
            
            print(f"✅ LLM categorized '{title}' to '{category_name}' (confidence: {confidence:.2f})")
        
        # If LLM didn't suggest any categories, that's fine - video remains uncategorized
        if not assigned_collections:
            print(f"🤷 No suitable categories found for '{title}' - leaving uncategorized")
        
        return assigned_collections



    def _ensure_auto_collection_from_llm(self, category_name: str, category_data: Dict) -> str:
        """Ensure an auto collection exists for an LLM-suggested category"""
        # Normalize category name
        normalized_name = category_name.lower().replace(' ', '_')
        
        # Check if collection already exists
        for collection_id, collection in self.collections.items():
            if (collection.name.lower().replace(' ', '_') == normalized_name and 
                collection.is_auto):
                return collection_id
        
        # Handle new categories suggested by LLM
        if category_data.get('is_new', False):
            # Create new category with LLM-provided details
            color = self._generate_category_color(category_name)
            description = category_data.get('description', f"AI-categorized {category_name} content")
            
            return self.create_collection(
                name=category_name.title(),
                description=description,
                color=color,
                tags=[normalized_name, 'llm_generated'],
                is_auto=True
            )
        else:
            # Use existing category info if available
            if normalized_name in self.base_categories:
                category_info = self.base_categories[normalized_name]
                return self.create_collection(
                    name=category_name.replace('_', ' ').title(),
                    description=category_info['description'],
                    color=category_info['color'],
                    tags=[normalized_name],
                    is_auto=True
                )
            else:
                # Create with default settings for new categories
                return self.create_collection(
                    name=category_name.title(),
                    description=f"AI-categorized {category_name} content",
                    color=self._generate_category_color(category_name),
                    tags=[normalized_name, 'llm_generated'],
                    is_auto=True
                )

    def _generate_category_color(self, category_name: str) -> str:
        """Generate a consistent color for a category based on its name"""
        # Simple hash-based color generation
        import hashlib
        hash_object = hashlib.md5(category_name.encode())
        hex_dig = hash_object.hexdigest()
        
        # Convert to HSL for better color distribution
        hue = int(hex_dig[:2], 16) * 360 // 255
        saturation = 60 + (int(hex_dig[2:4], 16) % 40)  # 60-100%
        lightness = 45 + (int(hex_dig[4:6], 16) % 20)   # 45-65%
        
        # Convert HSL to hex (simplified)
        colors = [
            "#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", 
            "#6366f1", "#ec4899", "#14b8a6", "#f97316", "#84cc16"
        ]
        
        return colors[hash(category_name) % len(colors)]

    def _llm_categorize_video(self, title: str, description: str) -> List[Dict[str, Any]]:
        """Use LLM to intelligently categorize video content"""
        if not self.gemini_client:
            return []
        
        # Create prompt for LLM categorization
        available_categories = list(self.base_categories.keys())
        categories_desc = "\n".join([
            f"- {name.replace('_', ' ').title()}: {info['description']}" 
            for name, info in self.base_categories.items()
        ])
        
        prompt = f"""
You are an expert content curator. Analyze this YouTube video and select the 1-2 MOST appropriate categories.

Video Title: "{title}"
Video Description: "{description[:500]}..."

Existing Categories (you can use these or create new ones):
{categories_desc}

CREATIVE GUIDELINES:
1. 🎯 Understand the content's main topic and purpose
2. 🆕 Create new specific categories when existing ones don't fit perfectly
3. 📊 Use confidence scores (0.0-1.0) - suggest categories with >0.4 confidence
4. � Be creative and specific with category names
5. 💡 Think about how users would search for and organize this content
6. 🌟 Consider entertainment, educational, and cultural value

RESPONSE FORMAT (JSON only, no markdown):
[
    {{"category": "avatar_animation", "confidence": 0.90, "reason": "Focuses on Avatar series animation", "is_new": true, "description": "Avatar: The Last Airbender animation and fight scenes"}},
    {{"category": "martial_arts_choreography", "confidence": 0.85, "reason": "Showcases martial arts fight sequences", "is_new": true, "description": "Martial arts choreography and fight scene analysis"}}
]

For existing categories, omit "is_new" and "description":
{{"category": "tutorials", "confidence": 0.70, "reason": "Educational content about animation techniques"}}

CRITICAL RULES:
- Maximum 2 categories total
- Only include if confidence > 0.6
- Focus on PRIMARY topic, not secondary themes
- Return ONLY the JSON array
- Be highly selective - quality over quantity
"""

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            response_text = response.text.strip()
            
            # Clean up the response (remove markdown formatting if present)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON response
            import json
            categories = json.loads(response_text)
            
            # Validate and filter results with hard limit of 2 categories
            valid_categories = []
            for cat in categories:
                if isinstance(cat, dict) and 'category' in cat and 'confidence' in cat:
                    if cat['confidence'] > 0.6:  # Raised threshold to 0.6 for selectivity
                        valid_categories.append(cat)
            
            print(f"🧠 LLM suggested {len(valid_categories)} categories for '{title}'")
            return valid_categories
            
        except Exception as e:
            print(f"❌ LLM categorization failed: {e}")
            return []

    def get_collections(self) -> List[Collection]:
        """Get all collections"""
        return list(self.collections.values())

    def get_collection_videos(self, collection_id: str, transcript_manager=None) -> List[Dict[str, Any]]:
        """Get all videos in a collection"""
        video_ids = [vc.video_id for vc in self.video_collections 
                    if vc.collection_id == collection_id]
        
        videos = []
        for video_id in video_ids:
            # Try to get video metadata if transcript_manager is available
            video_info = {"video_id": video_id}
            
            if transcript_manager:
                # Look for transcript files to get metadata
                transcript_files = list(transcript_manager.transcripts_dir.glob(f"transcript_{video_id}_*.json"))
                if transcript_files:
                    try:
                        with open(transcript_files[0], 'r') as f:
                            data = json.load(f)
                            if 'metadata' in data:
                                video_info.update(data['metadata'])
                    except Exception as e:
                        print(f"Error loading video metadata: {e}")
            
            videos.append(video_info)
        
        return videos

    def get_video_collections(self, video_id: str) -> List[str]:
        """Get all collections containing a video"""
        return [vc.collection_id for vc in self.video_collections 
                if vc.video_id == video_id]

    def create_smart_playlist(self, name: str, query: str, max_videos: int = 20) -> str:
        """Create a smart playlist based on a query using LLM analysis"""
        playlist_id = self.create_collection(
            name=f"🎵 {name}",
            description=f"Smart playlist: {query}",
            color="#ec4899",
            tags=["smart_playlist", "dynamic", query.lower()],
            is_auto=True
        )
        
        # Use LLM to analyze the query and suggest matching criteria
        if self.gemini_client:
            self._populate_smart_playlist_with_llm(playlist_id, query, max_videos)
        
        print(f"🎵 Created smart playlist: {name}")
        return playlist_id

    def _populate_smart_playlist_with_llm(self, playlist_id: str, query: str, max_videos: int):
        """Use LLM to populate smart playlist based on query"""
        if not self.gemini_client:
            return
        
        # This would be implemented to:
        # 1. Analyze the query using LLM
        # 2. Find matching videos from existing collections
        # 3. Add them to the smart playlist
        # For now, we'll just log the intent
        
        print(f"🤖 LLM analyzing smart playlist query: '{query}'")
        print(f"📝 Would populate playlist with up to {max_videos} matching videos")

    def suggest_collections(self, video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest collections for a video based on similarity"""
        suggestions = []
        
        # Get existing collections and suggest based on content similarity
        for collection_id, collection in self.collections.items():
            if collection.is_auto:
                continue
                
            # Calculate similarity (simplified)
            similarity_score = 0.5  # Placeholder
            
            suggestions.append({
                "collection_id": collection_id,
                "collection_name": collection.name,
                "similarity_score": similarity_score,
                "reason": "Similar content detected"
            })
        
        return sorted(suggestions, key=lambda x: x['similarity_score'], reverse=True)[:5]

    def get_collection_summary(self, collection_id: str, transcript_manager=None) -> CollectionSummary:
        """Get detailed summary of a collection"""
        if collection_id not in self.collections:
            raise ValueError(f"Collection {collection_id} not found")
        
        collection = self.collections[collection_id]
        videos = self.get_collection_videos(collection_id, transcript_manager)
        
        # Calculate total duration and extract topics
        total_duration = 0
        topics = set(collection.tags)
        
        for video in videos:
            # Get duration from metadata if available
            duration = video.get('length', 300)  # Default to 5 minutes
            total_duration += duration
            
            # Extract topics from video metadata
            title = video.get('title', '').lower()
            # Simple topic extraction based on common terms
            common_topics = ['programming', 'tutorial', 'review', 'guide', 'introduction', 'advanced']
            for topic in common_topics:
                if topic in title:
                    topics.add(topic.title())
        
        return CollectionSummary(
            collection=collection,
            videos=videos,
            total_duration=total_duration,
            topics=list(topics)
        )

    def improve_categorization(self, video_id: str, correct_collection_id: str, 
                             incorrect_collection_id: str = None):
        """Learn from user corrections to improve future categorization"""
        # This method would be called when users manually move videos between collections
        # It could be used to fine-tune the LLM prompts or adjust keyword weights
        
        print(f"📚 Learning: Video {video_id} belongs to collection {correct_collection_id}")
        
        if incorrect_collection_id:
            print(f"❌ Correcting: Video was incorrectly placed in {incorrect_collection_id}")
        
        # In a full implementation, this would:
        # 1. Store the correction in a learning database
        # 2. Analyze patterns in corrections
        # 3. Adjust categorization prompts or weights
        # 4. Potentially retrain or fine-tune the categorization model

    def get_categorization_stats(self) -> Dict[str, Any]:
        """Get statistics about auto-categorization performance"""
        total_videos = len(set(vc.video_id for vc in self.video_collections))
        auto_collections = [c for c in self.collections.values() if c.is_auto]
        manual_collections = [c for c in self.collections.values() if not c.is_auto]
        
        # Calculate distribution
        collection_distribution = {}
        for collection in self.collections.values():
            video_count = sum(1 for vc in self.video_collections 
                            if vc.collection_id == collection.id)
            collection_distribution[collection.name] = video_count
        
        return {
            "total_videos": total_videos,
            "total_collections": len(self.collections),
            "auto_collections": len(auto_collections),
            "manual_collections": len(manual_collections),
            "collection_distribution": collection_distribution,
            "llm_enabled": self.gemini_client is not None
        }

    def cleanup_invalid_collections(self):
        """Clean up collections with truly invalid or generic names"""
        # Only remove collections with obviously invalid names
        invalid_names = ['category_name', 'another_category', 'New_Category_Name', 'Category Name']
        collections_to_remove = []
        
        for collection_id, collection in self.collections.items():
            # Only remove collections with generic placeholder names or empty collections
            if (collection.name in invalid_names or 
                collection.video_count == 0):
                collections_to_remove.append(collection_id)
                print(f"🗑️ Marking invalid collection for removal: {collection.name}")
        
        # Remove invalid collections
        for collection_id in collections_to_remove:
            # Remove video associations
            self.video_collections = [vc for vc in self.video_collections 
                                    if vc.collection_id != collection_id]
            # Remove collection
            del self.collections[collection_id]
            
        if collections_to_remove:
            self._save_collections()
            self._save_video_collections()
            print(f"✅ Cleaned up {len(collections_to_remove)} invalid collections")
        
        return len(collections_to_remove)
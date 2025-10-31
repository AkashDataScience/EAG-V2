import sys
import os
from pathlib import Path
import json
import faiss
import numpy as np
from datetime import datetime
import requests
from typing import List, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import JSONFormatter
import yt_dlp
import re

class TranscriptManager:
    def __init__(self, transcripts_dir: Path, index_dir: Path, chunk_size: int = 60):
        """Initialize the transcript manager.
        
        Args:
            transcripts_dir: Directory to store transcript JSONs
            index_dir: Directory to store FAISS index and metadata
            chunk_size: Number of seconds per chunk
        """
        self.transcripts_dir = Path(transcripts_dir)
        self.index_dir = Path(index_dir)
        self.chunk_size = chunk_size
        self.embed_url = "http://localhost:11434/api/embeddings"
        self.embed_model = "nomic-embed-text"
        
        # Create directories if they don't exist
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize or load FAISS index
        self.index_path = self.index_dir / "index.bin"
        self.metadata_path = self.index_dir / "metadata.json"
        self._initialize_index()

    def extract_video_id(self, url: str) -> str:
        """Extract the video ID from a YouTube URL."""
        # Regular expression pattern for YouTube video ID
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_metadata(self, url: str) -> Dict:
        """Fetch video metadata using yt-dlp."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            metadata = {
                "title": info.get('title'),
                "description": info.get('description'),
                "views": info.get('view_count'),
                "rating": info.get('average_rating'),
                "length": info.get('duration'),
                "author": info.get('uploader'),
                "publish_date": info.get('upload_date'),
                "thumbnail_url": info.get('thumbnail'),
                "tags": info.get('tags', []),
                "categories": info.get('categories', []),
                "channel_id": info.get('channel_id'),
                "channel_url": info.get('channel_url')
            }
            return metadata
        except Exception as e:
            print(f"Error fetching video metadata: {str(e)}")
            return None

    def get_transcript(self, video_id: str) -> List[Dict]:
        """Fetch video transcript using youtube_transcript_api."""
        try:
            # Correct usage: create instance and call fetch
            ytt_api = YouTubeTranscriptApi()
            transcript = ytt_api.fetch(video_id)
            
            # Debug: print the response structure
            print(f"Transcript type: {type(transcript)}")
            print(f"Transcript length: {len(transcript) if transcript else 'None'}")
            if transcript and len(transcript) > 0:
                print(f"First entry: {transcript[0]}")
                print(f"First entry type: {type(transcript[0])}")
                if isinstance(transcript[0], dict):
                    print(f"Available keys: {list(transcript[0].keys())}")
            
            return transcript
        except Exception as e:
            print(f"Error fetching transcript: {str(e)}")
            return None

    def _initialize_index(self):
        """Initialize FAISS index and metadata."""
        if self.index_path.exists() and self.metadata_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Error loading index: {str(e)}")
                self.index = None
                self.metadata = []
        else:
            self.index = None
            self.metadata = []

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using local model."""
        response = requests.post(
            self.embed_url,
            json={"model": self.embed_model, "prompt": text}
        )
        response.raise_for_status()
        return np.array(response.json()["embedding"], dtype=np.float32)

    def _chunk_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk transcript into semantic segments based on time."""
        chunks = []
        current_chunk = []
        chunk_start = 0
        
        for entry in transcript:
            current_chunk.append(entry)
            if entry.start - chunk_start >= self.chunk_size:
                # Create chunk
                chunk_text = " ".join(item.text for item in current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'start_time': chunk_start,
                    'end_time': entry.start + entry.duration
                })
                # Start new chunk
                current_chunk = [entry]
                chunk_start = entry.start
        
        # Add final chunk if any
        if current_chunk:
            chunk_text = " ".join(item.text for item in current_chunk)
            chunks.append({
                'text': chunk_text,
                'start_time': chunk_start,
                'end_time': current_chunk[-1].start + current_chunk[-1].duration
            })
        
        return chunks

    def index_video(self, url: str) -> str:
        """Index a YouTube video transcript.
        
        Args:
            url: YouTube video URL
            
        Returns:
            video_id: The YouTube video ID
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Get video data
        metadata = self.get_video_metadata(url)
        transcript = self.get_transcript(video_id)
        if not metadata or not transcript:
            raise ValueError("Failed to fetch video data")
        
        # Chunk transcript
        chunks = self._chunk_transcript(transcript)
        
        # Get embeddings for chunks
        embeddings = []
        for chunk in chunks:
            embedding = self._get_embedding(chunk['text'])
            embeddings.append(embedding)
        
        # Initialize index if needed
        if self.index is None:
            self.index = faiss.IndexFlatL2(len(embeddings[0]))
        
        # Add to index
        embeddings_array = np.stack(embeddings)
        self.index.add(embeddings_array)
        
        # Add metadata
        chunk_metadata = []
        for i, chunk in enumerate(chunks):
            chunk_metadata.append({
                'video_id': video_id,
                'video_title': metadata['title'],
                'url': url,
                'chunk_id': len(self.metadata) + i,
                'text': chunk['text'],
                'start_time': chunk['start_time'],
                'end_time': chunk['end_time']
            })
        self.metadata.extend(chunk_metadata)
        
        # Save index and metadata
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Save full transcript data
        transcript_file = self.transcripts_dir / f"transcript_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert transcript to JSON-serializable format using JSONFormatter
        formatter = JSONFormatter()
        transcript_json = formatter.format_transcript(transcript)
        
        with open(transcript_file, 'w') as f:
            json.dump({
                'video_id': video_id,
                'metadata': metadata,
                'transcript': json.loads(transcript_json)  # Parse the JSON string back to dict/list
            }, f, indent=2)
            
        return video_id

    def search(self, query: str, k: int = 6) -> List[Dict[str, Any]]:
        """Search for relevant transcript chunks.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.index:
            return []
            
        # Get query embedding
        query_embedding = self._get_embedding(query)
        
        # Search index
        D, I = self.index.search(query_embedding.reshape(1, -1), k)
        
        # Get results
        results = []
        for idx in I[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])        
        return results 
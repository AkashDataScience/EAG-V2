# 🧠 Nexus - AI-Powered Video Knowledge Hub

**Transform YouTube into your personal knowledge base with Nexus - an intelligent video transcript analysis system featuring AI-powered Smart Collections, semantic search, and a beautiful Chrome extension interface.**

## 🌟 Key Features

### 🤖 **AI-Powered Smart Collections**
- **Automatic Categorization**: Gemini AI intelligently organizes videos into collections
- **Creative Categories**: AI creates specific, meaningful categories (e.g., "AI Ethics", "React Tutorials")
- **Quality Control**: Maximum 2 categories per video with >0.6 confidence threshold
- **Dynamic Organization**: Collections grow and adapt as you add more content

### 🔍 **Advanced Search & Analysis**
- **Semantic Search**: Find content by meaning, not just keywords
- **PADM Architecture**: Perception-Action-Decision-Memory cognitive framework
- **Context-Aware Responses**: AI understands your questions and provides detailed answers
- **Source Attribution**: Every answer links back to specific video timestamps

### 🌐 **Seamless Browser Integration**
- **One-Click Indexing**: Index any YouTube video instantly
- **Real-Time Status**: Live progress updates during video processing
- **Professional UI**: Clean, modern interface inspired by productivity tools
- **Cross-Video Search**: Query across your entire video library

### ⚡ **High Performance**
- **FAISS Vector Search**: Sub-second query responses
- **Local Embeddings**: Fast processing with Ollama
- **Background Processing**: Non-blocking video indexing
- **Efficient Storage**: Optimized data structures and caching

## 🏗️ System Architecture

### 🧠 **PADM Cognitive Framework**
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ PERCEPTION  │───▶│   MEMORY    │───▶│  DECISION   │───▶│   ACTION    │
│             │    │             │    │             │    │             │
│ • Intent    │    │ • Video     │    │ • Planning  │    │ • Tool      │
│ • Entities  │    │   Segments  │    │ • Strategy  │    │   Execution │
│ • Context   │    │ • History   │    │ • Reasoning │    │ • Response  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### 🤖 **Smart Collections System**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VIDEO INPUT   │───▶│  GEMINI AI      │───▶│  COLLECTIONS    │
│                 │    │                 │    │                 │
│ • Title         │    │ • Content       │    │ • AI Ethics     │
│ • Description   │    │   Analysis      │    │ • Programming   │
│ • Metadata      │    │ • Category      │    │ • Tutorials     │
│                 │    │   Selection     │    │ • Custom...     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ⚡ **Data Flow**
1. **📹 Index Video** → Extract transcript & metadata
2. **🤖 AI Categorization** → Gemini analyzes content (max 2 categories)
3. **🔍 Semantic Search** → FAISS vector similarity matching
4. **🧠 PADM Processing** → Intelligent query understanding & response
5. **📚 Source Attribution** → Link answers to specific video moments

## 🚀 Quick Start

### 📋 **Prerequisites**

- **Python 3.8+** with pip
- **Chrome Browser** (latest version)
- **Gemini API Key** ([Get one free](https://makersuite.google.com/app/apikey))
- **Ollama** ([Download here](https://ollama.ai))

### 1️⃣ **Setup Backend**

```bash
# Clone and navigate to project
git clone https://github.com/SXD390/EAG-V1-Assignment-7.git
cd Week-7

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate


# Set up environment variables
echo "GEMINI_API_KEY=your_api_key_here" > .env

# Install and start Ollama embedding model
ollama pull nomic-embed-text
```

### 2️⃣ **Install Chrome Extension**

1. **Open Chrome** → `chrome://extensions/`
2. **Enable Developer mode** (top-right toggle)
3. **Click "Load unpacked"** → Select `chrome_extension` folder
4. **Pin Nexus** to your toolbar 📌

### 3️⃣ **Launch Nexus**

```bash
# Start the AI agent server
python agent.py

# Server runs on http://localhost:5000
# Extension connects automatically
```

### 4️⃣ **Start Using**

1. **Visit any YouTube video**
2. **Click Nexus extension** 🧠
3. **Click "Index Current Video"**
4. **Watch AI categorize your content!**

## 🔧 Technical Architecture

### 🧠 **Core AI Components**

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Collections Manager** | AI categorization & organization | Gemini 2.0 Flash |
| **PADM Agent** | Cognitive processing framework | Custom architecture |
| **Transcript Manager** | Video processing & indexing | FAISS + Ollama |
| **Memory System** | Semantic search & retrieval | Vector embeddings |

### 🌐 **Frontend (Chrome Extension)**

```
chrome_extension/
├── popup.html          # Main UI interface
├── js/popup.js         # NexusAgent class logic
├── css/styles.css      # Professional styling
├── manifest.json       # Extension configuration
└── icons/              # Extension icons
```

### ⚙️ **Backend Services**

```
Week-7/
├── agent.py                    # Flask API server
├── collections_manager.py      # AI categorization engine
├── perception.py              # Intent & entity extraction
├── memory.py                  # Semantic search system
├── decision.py                # Strategic planning
├── action.py                  # Tool execution
├── models.py                  # Data structures
└── utils/
    ├── transcript_manager.py   # Video processing
    └── status_tracker.py      # Progress monitoring
```

### 💾 **Data Storage**

- **🔍 FAISS Index**: Lightning-fast vector similarity search
- **📄 JSON Files**: Structured metadata and collections
- **🤖 Ollama**: Local embedding generation (nomic-embed-text)
- **☁️ Gemini API**: Cloud-based AI categorization

## 🧠 PADM Agent: How It Works

- **Perception**: Extracts user intent and entities using Gemini LLM.
- **Memory**: Retrieves relevant transcript chunks (semantic search via FAISS).
- **Decision**: Plans next steps (tool call or answer) using Gemini LLM.
- **Action**: Executes tool calls (via MCP) or formats the final answer.

The agent loops through these steps, using retrieved transcript data and LLM reasoning, until a final answer is produced.

## 🖥️ Chrome Extension

- **Index**: One-click to index the current YouTube video.
- **Query**: Ask questions about any indexed video.
- **Results**: Answers are shown with direct transcript quotes and timestamps, plus clickable sources.

## � APPI Reference

### 📹 **Video Operations**

```http
POST /index_video
{
  "url": "https://youtube.com/watch?v=VIDEO_ID"
}
# Returns: operation_id for tracking progress

GET /indexing_status/{operation_id}
# Returns: real-time indexing progress

GET /list_indexed_videos
# Returns: all indexed videos with metadata
```

### 🔍 **Search & Query**

```http
POST /query
{
  "query": "What does the video say about neural networks?"
}
# Returns: AI-generated answer with source timestamps
```

### 📚 **Collections Management**

```http
GET /collections
# Returns: all collections with video counts

POST /collections
{
  "name": "My Custom Collection",
  "description": "Hand-picked videos",
  "color": "#ff6b6b"
}

GET /collections/{id}
# Returns: detailed collection summary

POST /collections/cleanup
# Removes invalid collections

POST /collections/reset
# ⚠️ Deletes ALL collections (destructive)
```

### 📊 **Analytics**

```http
GET /collections/stats
# Returns: categorization statistics
```

## 🎯 How to Use Nexus

### 📹 **Index Videos**

1. **Visit YouTube video** you want to analyze
2. **Click Nexus extension** (🧠 icon)
3. **Click "Index Current Video"**
4. **Watch AI categorization**:
   ```
   🔍 Fetching transcript...
   🤖 AI analyzing content...
   📂 Creating collections...
   ✅ Video categorized into "AI Ethics"
   ```

### 🔍 **Search Your Library**

```
💭 "What does the video say about neural networks?"
🤖 AI searches across ALL your indexed videos
📚 Returns detailed answer with source timestamps
🔗 Click sources to jump to exact moments
```

### 📊 **Manage Collections**

- **🤖 Smart Collections**: AI automatically organizes content
- **📊 View Stats**: See categorization analytics
- **🗑️ Cleanup**: Remove invalid collections
- **🔄 Reset**: Start fresh (clears all data)
- **+ Create**: Add custom manual collections

### 🎯 **Example Workflow**

1. **Index educational videos** on topics you're learning
2. **AI creates collections** like "Machine Learning", "React Development"
3. **Ask questions** like "How do transformers work?"
4. **Get instant answers** with exact video references
5. **Build your knowledge** systematically over time

## 🚀 Advanced Features

### 🤖 **AI Categorization Engine**

```python
# Gemini AI analyzes video content
Prompt: "Analyze this video and select 1-2 MOST appropriate categories"

# AI Response Example:
[
  {
    "category": "ai_ethics", 
    "confidence": 0.95,
    "reason": "Primary focus on AI safety and control",
    "is_new": true,
    "description": "AI ethics and safety discussions"
  }
]
```

### 📊 **Quality Controls**

- **Confidence Threshold**: Only >0.6 confidence categories
- **Maximum Limit**: 2 categories per video maximum
- **Smart Validation**: Prevents generic/invalid category names
- **Cleanup Tools**: Remove empty or invalid collections

### 💡 **Performance Tips**

- **Index quality content**: Educational videos work best
- **Use specific queries**: "Explain backpropagation" > "tell me about AI"
- **Batch indexing**: Index related videos together
- **Regular cleanup**: Remove unused collections

### 🤝 **Contributing**

Want to help improve Nexus?

1. **🐛 Report Issues**: Found a bug? Let us know!
2. **💡 Suggest Features**: Have ideas? We'd love to hear them!
3. **🔧 Submit PRs**: Code contributions welcome!
4. **📚 Improve Docs**: Help others learn Nexus!

## 🏆 **Why Nexus?**

> **"Transform passive video watching into active knowledge building"**

- **🧠 AI-Powered**: Intelligent categorization and search
- **⚡ Lightning Fast**: Sub-second search across thousands of videos
- **🎯 Focused Learning**: Organize content by your interests
- **🔗 Connected Knowledge**: Link related concepts across videos
- **📈 Scalable**: Grows with your learning journey

<div align="center">

**🧠 Ready to transform your learning?**

**[Get Started](#-quick-start) • [View Demo](#-how-to-use-nexus) • [Join Community](#-contributing)**

*Nexus - Where AI meets knowledge* ✨

</div> 

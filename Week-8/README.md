# 🧠 Synapse

**A reasoning-driven AI agent with multi-transport MCP support**

![Version](https://img.shields.io/badge/version-1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![UV](https://img.shields.io/badge/uv-package%20manager-purple)
![MCP](https://img.shields.io/badge/MCP-multi--transport-orange)

Synapse is an intelligent agent that monitors Telegram, processes queries using advanced reasoning, and executes tasks using multiple tool servers across different transport protocols. With enhanced reasoning capabilities and structured workflow management, Synapse can handle complex multi-step tasks without getting stuck in loops.

## ✨ Features

### Core Capabilities
- **Multi-Transport MCP**: Supports both STDIO and SSE transports
- **Telegram Integration**: Monitors and responds to Telegram messages
- **Advanced Reasoning Engine**: 4-step framework (ANALYZE → IDENTIFY → DECIDE → SELF-CHECK)
- **Tool Orchestration**: Seamlessly uses 7 different MCP servers with 40+ tools
- **Memory System**: Context-aware with semantic search using embeddings
- **Google Services**: Full integration with Sheets, Drive, and Gmail

### Intelligence Features
- **Loop Prevention**: Detects and prevents infinite loops through memory checking
- **Data Sufficiency Recognition**: Knows when to stop gathering and move forward
- **Multi-Step Workflows**: Handles complex task chains with clear transitions
- **Self-Verification**: Built-in checks before each action
- **Reasoning Type Awareness**: Identifies problem type (lookup, compute, transform, multi-step)

## 🛠️ Available Tools

### Math Operations (STDIO)
- Basic arithmetic, trigonometry, factorial, fibonacci
- Python sandbox execution
- Shell command execution
- SQL query execution

### Document Search (SSE, port 8000)
- FAISS-powered semantic search
- PDF extraction with image captioning
- Webpage extraction to markdown
- Multi-format document processing

### Web Search (STDIO)
- DuckDuckGo search integration
- Content fetching and parsing
- Table extraction from HTML and text content

### Telegram (SSE, port 8001)
- Dialog listing
- Message reading and sending
- Real-time monitoring

### Google Sheets (STDIO)
- Read/write spreadsheet data
- Batch operations
- Sheet management
- Formula handling

### Google Drive (STDIO)
- File search and retrieval
- Read file contents
- Metadata access

### Gmail (STDIO)
- Read unread emails
- Send emails (with confirmation)
- Trash management
- Email drafting and editing

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** with `uv` package manager
2. **Ollama** running locally (for embeddings)
3. **Google Cloud credentials** 
4. **Telegram API credentials**
5. **Gemini API key**

### Setup

1. **Configure environment** (`.env`):
   ```properties
   GEMINI_API_KEY=your_key_here
   TELEGRAM_API_ID=your_id
   TELEGRAM_API_HASH=your_hash
   CREDENTIALS_PATH=creds_path.json
   TOKEN_PATH=token_pathjson
   ```

2. **Start SSE servers**:
   
   Terminal 1 - Document Server:
   ```bash
   cd Week-8
   uv run mcp_server_documents.py
   ```
   
   Terminal 2 - Telegram Server:
   ```bash
   cd Week-8
   uv run mcp_server_telegram.py
   ```

3. **Run Synapse**:
   ```bash
   cd Week-8
   uv run agent.py
   ```

## 📋 Configuration

Edit `config/profiles.yaml` to customize:

- **Strategy**: Conservative, retry_once, or explore_all
- **Max Steps**: Maximum tool-use iterations (default: 20)
- **Memory**: Top-K retrieval and filtering
- **Persona**: Tone and behavior settings

## 🎯 Example Tasks

Synapse can handle complex multi-step tasks:

**Task 1**: "Find the Current Point Standings of F1 Racers. Save data in Google Sheets. Send the sheet link to email@example.com"
- Uses `search` to find F1 standings
- Uses `fetch_content` to get the webpage data
- Uses `extract_table` to parse standings into structured format
- Uses `create_spreadsheet` to create a new sheet
- Uses `batch_update_cells` to populate the sheet with F1 data
- Uses `share_spreadsheet` to share with the email address
- Multi-step workflow with data extraction and transformation

**Task 2**: "Find ASCII values of INDIA, calculate exponential sum, save to Google Sheets"
- Uses `strings_to_chars_to_int` tool
- Uses `int_list_to_exponential_sum` tool
- Uses Google Sheets tools to save results

**Task 3**: "Check my unread emails and summarize them"
- Uses `get-unread-emails` from Gmail
- Uses `read-email` to get content
- Summarizes using LLM

**Task 4**: "Search for 'budget' in Drive and create a summary"
- Uses `search_files` from Google Drive
- Uses `get_file` to read content
- Generates summary

## 🏗️ Architecture

```
Synapse Agent
    ↓
MultiMCP (Session Manager)
    ↓
    ├─→ STDIO Servers (subprocess-based)
    │   ├─→ Math Server
    │   ├─→ Web Search Server
    │   ├─→ Google Sheets Server
    │   ├─→ Google Drive Server
    │   └─→ Gmail Server
    │
    └─→ SSE Servers (HTTP-based)
        ├─→ Document Server (port 8000)
        └─→ Telegram Server (port 8001)
```

## 🧠 How It Works

1. **Telegram Monitoring**: Synapse monitors a Telegram dialog for new messages
2. **Perception**: Extracts intent and identifies needed tools
3. **Memory Retrieval**: Searches past interactions for context
4. **Reasoning Process**: 4-step framework (ANALYZE → IDENTIFY → DECIDE → SELF-CHECK)
5. **Planning**: Decides next action using conservative strategy with explicit reasoning
6. **Tool Execution**: Calls appropriate MCP server tools
7. **Memory Storage**: Saves results for future reference
8. **Response**: Sends answer back to Telegram

### Reasoning Framework

Synapse uses a structured reasoning process:

- **ANALYZE**: What is the user asking? What have I done? What do I have? What's missing?
- **IDENTIFY**: What type of reasoning is needed? (Lookup, Computation, Transformation, Multi-step)
- **DECIDE**: Do I have enough info for FINAL_ANSWER or need more tools?
- **SELF-CHECK**: Have I done this before? Am I repeating? Is this the logical next step?

This framework prevents loops, reduces hallucination, and ensures thoughtful decision-making.

## 📊 Memory System

- **Storage**: In-memory with embeddings
- **Embedding Model**: nomic-embed-text (via Ollama)
- **Retrieval**: Top-K similarity search
- **Types**: tool_output, fact, query
- **Session-aware**: Tracks conversation context

## 🎓 Key Concepts

- **MCP (Model Context Protocol)**: Standard for tool integration
- **STDIO Transport**: Subprocess-based, stateless
- **SSE Transport**: HTTP-based, persistent connections
- **Conservative Strategy**: Careful, step-by-step execution
- **Memory-Enhanced**: Uses past context for better decisions
- **Reasoning-Driven**: Explicit thinking process before each action
- **Self-Verifying**: Built-in checks to prevent errors and loops

## 🔄 Multi-Step Workflow Pattern

Synapse excels at complex workflows by following a structured approach:

### Example: Web Data to Spreadsheet
```
1. GATHER: Search → Fetch content
   ↓ (Once you have data, STOP gathering)
2. PARSE: Extract table → Structure data
   ↓ (Transform into spreadsheet format)
3. STORE: Create spreadsheet → Update cells
   ↓ (Save structured data)
4. SHARE: Share spreadsheet → Send notification
   ↓ (Distribute results)
5. COMPLETE: Provide final answer
```

### Key Principles
- **One-Way Flow**: Move forward, don't repeat steps
- **Data Sufficiency**: Recognize when you have enough information
- **Memory Checking**: Always verify what's already been done
- **Clear Transitions**: Each step has a clear output for the next

## 🤝 Contributing

Synapse is designed to be extensible:
- Add new MCP servers in `mcp_server_*.py`
- Update `profiles.yaml` to register them
- Choose STDIO or SSE transport based on needs

## 🙏 Acknowledgments

Built with:
- FastMCP for server implementation
- Google APIs for service integration
- Ollama for embeddings
- Gemini for text generation
- FAISS for vector search

---

**Synapse** - Connecting intelligence across services 🧠⚡

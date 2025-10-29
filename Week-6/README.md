# 🧠 4-Layer Cognitive Architecture Stock Analysis Agent

A sophisticated **cognitive architecture** implementation for stock market analysis using **4 distinct cognitive layers**: Perception, Memory, Decision-Making, and Action. Built with **Pydantic** for robust data validation, **MCP (Model Context Protocol)** for tool execution, and **Gemini AI** for intelligent decision-making.

## 🏗️ Cognitive Architecture Overview

### **🔍 Layer 1: Perception (Understanding Input)**
- **Purpose**: Extracts facts from user input and asks clarifying questions
- **Implementation**: `perception.py` - Simple fact extraction with dynamic questioning
- **Technology**: Gemini AI for natural language understanding
- **Input**: Raw user text
- **Output**: Structured facts (key-value pairs) + clarifying questions

### **💾 Layer 2: Memory (Simple Facts Storage)**
- **Purpose**: Stores and recalls facts using LLM-powered filtering
- **Implementation**: `memory.py` - Simple facts list with intelligent recall
- **Technology**: Gemini AI for context-aware fact retrieval
- **Features**: `store(fact)`, `recall(query)` with LLM filtering

### **🤔 Layer 3: Decision-Making (AI-Driven MCP Client)**
- **Purpose**: Uses AI to decide what MCP tools to call next
- **Implementation**: `decision.py` - AI-driven workflow planning (Week-5 pattern)
- **Technology**: Gemini AI + MCP client for tool orchestration
- **Features**: Dynamic context building, tool parameter parsing, iterative execution

### **🔧 Layer 4: Action (MCP Server Tools)**
- **Purpose**: Executes financial analysis operations via MCP tools
- **Implementation**: `action.py` - MCP server with Pydantic-validated tools
- **Technology**: FastMCP server + Yahoo Finance + NewsAPI + Gemini AI
- **Tools**: 7 analysis tools with full Pydantic validation

## 🚀 Key Features

### **📊 Comprehensive Stock Analysis Tools**
1. **`fetch_stock_data`**: Real-time OHLCV data from Yahoo Finance
2. **`fetch_news_data`**: Multi-source news with intelligent sampling + fallback
3. **`analyze_sentiment`**: AI-powered sentiment analysis with Gemini
4. **`analyze_sentiment_simple`**: Stateless sentiment analysis for workflow
5. **`calculate_rsi`**: Technical indicator calculation
6. **`calculate_correlations`**: News-price correlation analysis
7. **`run_backtest`**: Trading strategy backtesting
8. **`generate_report`**: Comprehensive analysis reports

### **🧠 Advanced Cognitive Capabilities**
- **Dynamic Fact Extraction**: Adapts to any user input with relevant questions
- **LLM-Powered Memory**: Intelligent fact storage and context-aware recall
- **AI-Driven Decisions**: Gemini AI decides optimal tool execution sequence
- **Interactive Questioning**: Asks 5+ clarifying questions to understand preferences
- **Stateless Tool Design**: Clean MCP architecture with proper data flow

### **🔒 Type Safety & Validation**
- **Full Pydantic Integration**: All layers use Pydantic models
- **MCP Tool Validation**: Input/output validation for all tools
- **Dynamic Parameter Parsing**: Key-value parameter handling
- **Error Recovery**: Graceful fallbacks and mock data for demos

## 📁 Project Structure

```
Week-6/
├── models.py           # All Pydantic models (centralized)
├── perception.py       # Layer 1: Fact extraction + questioning
├── memory.py          # Layer 2: Simple facts storage with LLM recall
├── decision.py        # Layer 3: AI-driven MCP client (Week-5 pattern)
├── action.py          # Layer 4: MCP server with analysis tools
├── main.py            # Cognitive agent orchestrator
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## 🛠️ Setup & Installation

### **1. Install Dependencies**
```bash
cd Week-6
pip install -r requirements.txt
```

### **2. Configure Environment Variables**
```bash
# Create .env file with your API keys
GEMINI_API_KEY=your_gemini_api_key_here
NEWS_API_KEY=your_news_api_key_here
```

### **3. Get API Keys**
- **Gemini API**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **NewsAPI**: Get from [NewsAPI.org](https://newsapi.org/) (optional - has fallback)

## 🎯 Usage

### **Interactive Mode**
```bash
python main.py
```

### **Example Interaction Flow**
```
🧠 PERCEPTION LAYER: Extracting facts and understanding preferences...
✅ Extracted facts: {'symbol': 'RELIANCE.NS', 'analysis_type': 'sentiment', 'user_intent': 'analyze market sentiment'}

🤔 I have some questions to better understand your needs:
============================================================

❓ Question 1: What time period should we analyze for RELIANCE sentiment?
💬 Your answer: 1 month

❓ Question 2: Are you interested in news from specific sources?
💬 Your answer: All sources

...

🤔 Starting AI-driven analysis via MCP...
Analysis iteration 1
AI Decision: FUNCTION_CALL: fetch_news_data|symbol=RELIANCE.NS|days=30
Result: News data fetched: 45 articles from 23 sources

Analysis iteration 2  
AI Decision: FUNCTION_CALL: analyze_sentiment_simple|symbol=RELIANCE.NS|batch_size=5
Result: Sentiment analysis completed: positive (72% confidence) - 65.2% positive, 22.1% negative

✅ Analysis completed successfully!
```

## 🔄 Cognitive Flow Example

### **Query**: "Analyze HDFC Bank sentiment"

#### **🔍 Perception Layer**
```python
# Input: "Analyze HDFC Bank sentiment"
# Extracts facts using Gemini AI
facts = {
    "symbol": "HDFCBANK.NS",
    "analysis_type": "sentiment", 
    "user_intent": "analyze market sentiment",
    "stock_mentioned": "HDFC Bank"
}

# Generates 5+ clarifying questions
questions = [
    "What time period should we analyze?",
    "Are you interested in specific news sources?",
    "Do you want technical indicators too?",
    "What's your investment timeline?",
    "Any specific concerns about this stock?"
]
```

#### **💾 Memory Layer**
```python
# Stores all facts and Q&A responses
memory.store_fact("User fact - symbol: HDFCBANK.NS")
memory.store_fact("User fact - analysis_type: sentiment")
memory.store_fact("User Q&A - Question 1: What time period? | Answer: 1 month")
# ... stores all interactions
```

#### **🤔 Decision Layer**
```python
# AI-driven decision making with dynamic context
system_prompt = "You are an autonomous Stock Market Analysis Agent..."
dynamic_context = f"""
CURRENT ANALYSIS REQUEST:
- Symbol: HDFCBANK.NS
- Task Type: sentiment

CURRENT MEMORY STATE:
Facts: ['User fact - symbol: HDFCBANK.NS', 'fetch_news_data completed: ...']

What should the agent do next?
"""

# AI decides: FUNCTION_CALL: fetch_news_data|symbol=HDFCBANK.NS|days=30
# Then: FUNCTION_CALL: analyze_sentiment_simple|symbol=HDFCBANK.NS|batch_size=5
```

#### **🔧 Action Layer (MCP Server)**
```python
# Tool 1: fetch_news_data
@mcp.tool()
def fetch_news_data(input_data: FetchNewsDataInput) -> NewsDataResult:
    # Fetches news with intelligent sampling + fallback
    # Returns: NewsDataResult with articles, sources, message

# Tool 2: analyze_sentiment_simple  
@mcp.tool()
def analyze_sentiment_simple(symbol: str, batch_size: int = 5) -> str:
    # Analyzes sentiment for the symbol
    # Returns: "Sentiment analysis completed: positive (72% confidence)"
```

## 📊 Data Models (Centralized in models.py)

### **Perception Layer Models**
- **`ExtractFactsInput`**: User input for fact extraction
- **`FactExtractionResult`**: Facts (Dict) + questions (List)

### **Memory Layer Models**
- **`StoreFactInput`**: Fact to store
- **`RecallFactsInput`**: Query for fact retrieval
- **`MemoryResult`**: Success/failure + facts list

### **Action Layer Models**
- **`FetchStockDataInput/Result`**: Stock data fetching
- **`FetchNewsDataInput/Result`**: News data fetching
- **`AnalyzeSentimentInput/Result`**: Sentiment analysis
- **`StockData`**: Individual stock price point
- **`NewsArticle`**: Individual news article

### **Core Data Models**
- **`ParsedIntent`**: Structured user intent
- **`SystemStatus`**: Overall system status
- **`AgentConfig`**: Agent configuration

## 🎯 Key Architecture Decisions

### **1. 🧠 Simplified Cognitive Layers**
- **Perception**: Dynamic fact extraction (not rigid intent parsing)
- **Memory**: Simple facts storage (not complex session management)
- **Decision**: AI-driven MCP client (Week-5 pattern)
- **Action**: Stateless MCP tools (clean separation)

### **2. 🔗 MCP Integration Pattern**
- **Decision Layer**: MCP client that calls tools
- **Action Layer**: MCP server that provides tools
- **Clean Separation**: Decision logic separate from tool implementation
- **Week-5 Pattern**: Proven AI-driven tool orchestration

### **3. 🔒 Full Pydantic Consistency**
- **All Models Centralized**: Single `models.py` file
- **Type Safety**: Every layer uses Pydantic validation
- **Parameter Parsing**: Dynamic key=value parameter handling
- **Error Prevention**: Validation catches issues early

### **4. 🤖 AI-Powered Intelligence**
- **Dynamic Questioning**: Adapts questions to user input
- **Context-Aware Memory**: LLM filters relevant facts
- **Intelligent Planning**: AI decides tool execution sequence
- **Graceful Fallbacks**: Mock data when APIs fail

## 🔧 Available MCP Tools

### **Data Fetching Tools**
```python
# Fetch stock price data
FUNCTION_CALL: fetch_stock_data|symbol=RELIANCE.NS|period=1mo|interval=1h

# Fetch news articles with intelligent sampling
FUNCTION_CALL: fetch_news_data|symbol=RELIANCE.NS|days=30
```

### **Analysis Tools**
```python
# Analyze sentiment (stateless)
FUNCTION_CALL: analyze_sentiment_simple|symbol=RELIANCE.NS|batch_size=5

# Calculate RSI technical indicator
FUNCTION_CALL: calculate_rsi|window=14

# Calculate news-price correlations
FUNCTION_CALL: calculate_correlations
```

### **Strategy Tools**
```python
# Run backtesting simulation
FUNCTION_CALL: run_backtest|initial_capital=10000

# Generate comprehensive report
FUNCTION_CALL: generate_report|report_type=full
```

## 🧪 Testing & Debugging

### **Layer Testing**
```bash
# Test perception layer
python -c "from perception import Perception; p = Perception(); print('Perception OK')"

# Test memory layer  
python -c "from memory import Memory; m = Memory(); print('Memory OK')"

# Test decision layer
python -c "from decision import DecisionLayer; from models import AgentConfig; d = DecisionLayer(AgentConfig()); print('Decision OK')"
```

### **MCP Server Testing**
```bash
# Start MCP server directly
python action.py

# Test with MCP client
python -c "import asyncio; # test MCP tools"
```

### **Integration Testing**
```bash
# Full cognitive flow test
python main.py
# Try: "Analyze Reliance sentiment"
```

## 🔮 Architecture Benefits

### **🧠 Cognitive Advantages**
- **Clear Separation**: Each layer has distinct cognitive function
- **Modularity**: Easy to modify individual layers
- **Testability**: Each layer can be tested independently
- **Scalability**: Can add new cognitive layers easily

### **🔗 MCP Integration Benefits**
- **Tool Reusability**: MCP tools can be used by other clients
- **Clean Architecture**: Decision logic separate from tool implementation
- **Standardization**: Follows MCP protocol standards
- **Interoperability**: Tools can be called from any MCP client

### **🔒 Pydantic Benefits**
- **Type Safety**: Automatic validation and type conversion
- **Error Prevention**: Catch data issues early
- **Self-Documenting**: Clear data structures and interfaces
- **IDE Support**: Better autocomplete and error detection

### **🤖 AI-Powered Benefits**
- **Adaptive Behavior**: Responds to different user inputs
- **Context Awareness**: Remembers previous interactions
- **Intelligent Planning**: Optimal tool execution sequence
- **Natural Interaction**: Conversational question-asking

## 🚀 Future Enhancements

### **Cognitive Layer Improvements**
- **Learning Layer**: Learn from past decisions and outcomes
- **Reflection Layer**: Self-assessment and improvement
- **Emotional Layer**: Sentiment-aware decision making
- **Social Layer**: Multi-user interaction and collaboration

### **MCP Tool Expansion**
- **Real-Time Data**: WebSocket-based live market data
- **Advanced Analytics**: Machine learning models
- **Portfolio Tools**: Multi-asset analysis capabilities
- **Risk Management**: VaR, stress testing, scenario analysis

### **System Enhancements**
- **Persistent Memory**: Database-backed fact storage
- **Distributed Processing**: Scale across multiple machines
- **Web Interface**: Browser-based interaction
- **API Gateway**: RESTful API for external integration

---

## 🎉 Summary

Week-6 represents a **mature cognitive architecture** for AI agents:

### **🔄 Evolution from Week-5**
- **Week-5**: Single MCP client with mixed responsibilities
- **Week-6**: 4-layer cognitive architecture with clear separation
- **Improvement**: Better modularity, testability, and maintainability

### **🧠 Cognitive Science Principles**
- **Perception**: Fact extraction and questioning
- **Memory**: Storage and context-aware retrieval
- **Decision**: AI-driven planning and tool orchestration
- **Action**: Execution of analysis operations

### **🔒 Production-Ready Features**
- **Full Pydantic Validation**: Type safety throughout
- **Error Recovery**: Graceful fallbacks and mock data
- **Interactive Experience**: Dynamic questioning and feedback
- **Comprehensive Logging**: Detailed execution tracking

### **🎯 Real-World Application**
- **Financial Analysis**: Professional-grade stock analysis
- **User Experience**: Natural language interaction
- **Scalable Architecture**: Easy to extend and maintain
- **Industry Standards**: MCP protocol compliance

This cognitive architecture provides a **solid foundation** for building sophisticated AI agents that can understand, remember, plan, and execute complex financial analysis tasks with human-like reasoning capabilities.

---

**Built with 🧠 Cognitive Architecture + 🔗 MCP + 🔒 Pydantic + 🤖 Gemini AI**

*Advancing AI agent design through cognitive science principles and modern tooling*
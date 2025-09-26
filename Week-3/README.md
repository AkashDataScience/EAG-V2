# Stock Analysis Chrome Extension - Modular Architecture

A sophisticated Chrome extension that analyzes stock price movements and correlates them with news sentiment using AI-powered analysis. Now featuring a clean, modular backend architecture for better maintainability and scalability.

## 🚀 Features

- **Natural Language Queries**: Ask questions like "Analyze Tesla stock sentiment" or "Check AAPL correlation with news"
- **Real-time Stock Data**: Fetches live OHLCV data from Yahoo Finance
- **AI-Powered Sentiment Analysis**: Uses Google Gemini Flash 2.0 for intelligent sentiment analysis
- **Correlation Detection**: Finds relationships between news sentiment and price movements
- **Backtesting Engine**: Tests trading strategies based on sentiment signals
- **Interactive Charts**: Visualizes price data with Chart.js
- **Iterative AI Agent**: Makes step-by-step decisions based on previous results

## 🏗️ Modular Architecture

### Frontend (Chrome Extension)
```
Week-3/
├── manifest.json          # Extension configuration
├── popup.html            # Main UI interface
├── popup.js              # Frontend logic and API communication
├── background.js         # Service worker
└── styles.css           # Modern UI styling
```

### Backend (Modular Flask API)
```
Week-3/backend/
├── app.py                    # Main Flask application factory
├── run.py                    # Development server runner
├── config.py                 # Configuration management
├── models.py                 # Data models and structures
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
│
├── utils/
│   ├── __init__.py
│   └── logger.py            # Logging configuration
│
├── services/
│   ├── __init__.py
│   ├── stock_data.py        # Yahoo Finance integration
│   ├── news_data.py         # News fetching service
│   ├── sentiment_analysis.py # Gemini sentiment analysis
│   ├── correlation_analysis.py # Correlation calculations
│   ├── backtest_engine.py   # Trading strategy backtesting
│   └── query_parser.py      # Natural language parsing
│
├── agents/
│   ├── __init__.py
│   └── iterative_agent.py   # AI agent orchestration
│
└── routes/
    ├── __init__.py
    └── api.py               # API route definitions
```

## 🔧 API Endpoints

### Health Check
```http
GET /api/health
```

### Natural Language Analysis
```http
POST /api/analyze
Content-Type: application/json

{
  "query": "Analyze Tesla stock sentiment and correlation"
}
```

### Query Parsing
```http
POST /api/parse-query
Content-Type: application/json

{
  "query": "Check AAPL news sentiment"
}
```

## 📦 Setup Instructions

### 1. Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd Week-3/backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Required API Keys:**
   - **Google Gemini API**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - **NewsAPI** (optional): Get from [NewsAPI.org](https://newsapi.org/)

5. **Run the backend:**
   ```bash
   python run.py
   ```

### 2. Chrome Extension Setup

1. **Open Chrome Extensions:**
   - Go to `chrome://extensions/`
   - Enable "Developer mode"

2. **Load the extension:**
   - Click "Load unpacked"
   - Select the `Week-3` directory (containing manifest.json)

3. **Use the extension:**
   - Click the extension icon in Chrome toolbar
   - Enter natural language queries

## 🤖 AI Agent System

The modular agent system works through these components:

### 1. Query Parser Service
- Parses natural language into structured intent
- Extracts stock symbols, timeframes, and analysis types
- Uses Gemini Flash 2.0 for intelligent parsing

### 2. Iterative Agent
- Makes step-by-step decisions based on previous results
- Orchestrates multiple services in logical sequence
- Provides detailed execution logs

### 3. Service Layer
- **StockDataService**: Yahoo Finance integration
- **NewsDataService**: Multi-source news aggregation
- **SentimentAnalysisService**: AI-powered sentiment analysis
- **CorrelationAnalysisService**: Statistical correlation detection
- **BacktestEngineService**: Strategy backtesting

## 💡 Usage Examples

### Natural Language Queries
```
"Analyze Tesla stock sentiment for the last week"
"Check correlation between Apple news and price movements"
"Run backtest on Microsoft with sentiment signals"
"What's the sentiment analysis for NVDA?"
"Compare GOOGL news impact on stock price"
```

### Response Structure
```json
{
  "status": "completed",
  "symbol": "TSLA",
  "timeframe": "1h",
  "original_query": "Analyze Tesla stock sentiment",
  "iterations": 4,
  "iteration_log": [
    "Iteration 1: Called fetch_market_data → Result: List with 240 items",
    "Iteration 2: Called fetch_news_data → Result: List with 25 items",
    "Iteration 3: Called analyze_sentiment → Result: List with 25 items",
    "Iteration 4: Called calculate_correlations → Result: Dict with 4 keys"
  ],
  "final_answer": "Tesla shows moderate positive sentiment...",
  "execution_context": {...},
  "timestamp": "2025-01-21T10:30:00"
}
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional
NEWS_API_KEY=your-news-api-key-here
FLASK_DEBUG=true
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

### Configuration Options (config.py)
- `MAX_NEWS_ITEMS`: Maximum news items to analyze (default: 30)
- `MAX_CANDLES`: Maximum price candles to fetch (default: 240)
- `MIN_CONFIDENCE_THRESHOLD`: Minimum confidence for trading signals (default: 0.6)
- `GEMINI_MODEL`: AI model to use (default: 'gemini-2.0-flash-exp')

## 🧪 Development

### Adding New Services
1. Create new service in `services/` directory
2. Follow the existing service pattern
3. Import and use in the iterative agent

### Adding New Routes
1. Add routes to `routes/api.py`
2. Use blueprint pattern for organization
3. Include proper error handling

### Testing
```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test query parsing
curl -X POST http://localhost:5000/api/parse-query \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyze TSLA sentiment"}'
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors:**
   - Ensure all `__init__.py` files are present
   - Check relative imports in service modules

2. **API Key Issues:**
   - Verify `.env` file is in the backend directory
   - Check API key format and validity

3. **Extension Loading:**
   - Ensure manifest.json is in the Week-3 directory
   - Check Chrome Extensions page for errors

### Debug Mode
- Backend logs show detailed execution information
- Chrome DevTools console shows frontend errors
- Agent iteration logs provide step-by-step debugging

## 📈 Performance Features

- **Modular Design**: Easy to maintain and extend
- **Service Separation**: Clear separation of concerns
- **Error Isolation**: Failures in one service don't crash others
- **Async Processing**: Non-blocking operations throughout
- **Efficient Data Processing**: Pandas for numerical operations
- **Smart Caching**: Reduces redundant API calls

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the modular architecture patterns
4. Add appropriate tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the troubleshooting section
- Review service logs for detailed error information
- Ensure all dependencies are correctly installed
- Verify API keys are properly configured
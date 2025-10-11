# 📊 Advanced Stock Market Analysis MCP Agent

An **autonomous stock market analysis agent** built with **Model Context Protocol (MCP)** that performs comprehensive financial analysis, technical analysis, and algorithmic trading strategy generation using AI-powered decision making.

## 🚀 Key Features

### **🧠 Intelligent Natural Language Interface**
- **Company Name Recognition**: "Analyze Reliance sentiment" → Automatically converts to RELIANCE.NS
- **Adaptive Workflows**: AI decides which tools to use based on your specific request
- **Step-by-Step Reasoning**: Agent thinks through each decision before taking action
- **Multi-Market Support**: Indian stocks (.NS), US stocks, and global markets

### **📈 Comprehensive Analysis Suite**
- **📊 Stock Data Analysis**: Real-time OHLCV data from Yahoo Finance
- **📰 Intelligent News Sampling**: Multi-source news with priority financial sources
- **🧠 AI Sentiment Analysis**: Gemini-powered sentiment analysis with confidence scoring
- **🔗 News-Price Correlations**: Statistical correlation between sentiment and price movements
- **� AdvanceGd Backtesting**: Sophisticated trading strategy simulation
- **📋 AI Report Generation**: Comprehensive analysis reports with actionable insights

### **📈 Technical Analysis Tools**
- **RSI (Relative Strength Index)**: Overbought/oversold signals with customizable periods
- **MACD**: Moving Average Convergence Divergence with signal line and histogram
- **Bollinger Bands**: Volatility-based bands with position analysis
- **Multi-Indicator Analysis**: Combines multiple technical signals for robust analysis

### **🤖 Algorithmic Trading Strategy Generation**
- **Target CAGR-Based Strategies**: Generate strategies for specific annual return targets
- **Risk-Adjusted Approaches**: Conservative, medium, and aggressive risk profiles
- **Mathematical Position Sizing**: Kelly Criterion and risk-based position sizing
- **Comprehensive Risk Management**: Drawdown limits, stop-losses, and exposure controls
- **Implementation-Ready**: Specific entry/exit rules and monitoring frameworks

### **🏗️ Advanced MCP Architecture**
- **Protocol-Based Communication**: Standardized MCP for reliable tool interaction
- **Modular Design**: Clean separation between analysis tools and orchestration logic
- **Extensible Framework**: Easy to add new indicators, strategies, and analysis methods
- **Robust Error Handling**: Graceful failure recovery and adaptive workflows
- **Type-Safe Operations**: Proper parameter validation and data type handling

## 🛠️ Setup

### **Requirements**
```bash
pip install -r requirements.txt
```

### **Environment Setup**
1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure API keys in `.env`:**
   ```env
   # Required: Get from https://aistudio.google.com/app/apikey
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Required: Get from https://newsapi.org/
   NEWS_API_KEY=your_news_api_key_here
   ```

### **Dependencies**
- **google-genai**: Gemini AI integration
- **mcp**: Model Context Protocol framework
- **yfinance**: Yahoo Finance data
- **requests**: HTTP requests for news APIs
- **pandas/numpy**: Data processing
- **python-dotenv**: Environment management

## 🎯 Usage

### **🚀 Run the Analysis Agent**
```bash
python talk2mcp.py
```

### **🎯 Example Analysis Sessions**

#### **📈 Sentiment Analysis Example**
```
📊 Enter your analysis request: Analyze Reliance sentiment

🎯 Processing request: Analyze Reliance sentiment
🤖 AI agent will decide the analysis approach...

--- �c Analysis Step 1 ---
🤖 AI Decision: FUNCTION_CALL: parse_query|Analyze Reliance sentiment
🔧 Executing: parse_query with parameters: ['Analyze Reliance sentiment']
✅ Result: Query parsed successfully: RELIANCE.NS for sentiment (confidence: 0.9)

--- �c Analysis Step 2 ---
🤖 AI Decision: FUNCTION_CALL: fetch_news_data|RELIANCE.NS|7
🔧 Executing: fetch_news_data with parameters: ['RELIANCE.NS', '7']
✅ Result: Successfully fetched 25 news articles for Reliance Industries Limited

--- 📈 Analysis Step 3 ---
🤖 AI Decision: FUNCTION_CALL: analyze_sentiment|5
🔧 Executing: analyze_sentiment with parameters: ['5']
✅ Result: Analyzed sentiment for 25 articles. Overall: 65.0% positive, 20.0% negative, 15.0% neutral

--- 📈 Analysis Step 4 ---
🤖 AI Decision: FINAL_ANSWER: [Analysis Complete]

🎉 === Stock Analysis Complete ===
📈 Final Analysis Summary:
� EStock: RELIANCE.NS - Current: ₹1,380.70 (+1.2%)
📰 News: 25 articles analyzed
🧠 Sentiment: 65.0% positive, 20.0% negative
```

#### **🤖 Algorithmic Strategy Generation Example**
```
📊 Enter your analysis request: Generate algo strategy for 20% CAGR on TCS

🎯 Processing request: Generate algo strategy for 20% CAGR on TCS
🤖 AI agent will decide the analysis approach...

--- 📈 Analysis Step 1 ---
🤖 AI Decision: FUNCTION_CALL: parse_query|Generate algo strategy for 20% CAGR on TCS
✅ Result: Query parsed successfully: TCS.NS for strategy (confidence: 0.9)

--- 📈 Analysis Step 2 ---
� AIn Decision: FUNCTION_CALL: fetch_stock_data|TCS.NS|3mo|1d
✅ Result: Successfully fetched 65 price points for TCS.NS. Current price: ₹4,125.30

--- 📈 Analysis Step 3 ---
🤖 AI Decision: FUNCTION_CALL: calculate_rsi|14
✅ Result: RSI(14) calculated: Current RSI = 58.2 (Neutral). 51 data points generated.

--- 📈 Analysis Step 4 ---
🤖 AI Decision: FUNCTION_CALL: calculate_macd|12|26|9
✅ Result: MACD(12,26,9) calculated: MACD=45.23, Signal=38.67, Status=Bullish (Strengthening)

--- 📈 Analysis Step 5 ---
🤖 AI Decision: FUNCTION_CALL: calculate_bollinger_bands|20|2.0
✅ Result: Bollinger Bands(20,2.0) calculated: Price=₹4,125.30, Position=45% (Within Normal Range)

--- 📈 Analysis Step 6 ---
🤖 AI Decision: FUNCTION_CALL: fetch_news_data|TCS.NS|30
✅ Result: Successfully fetched 28 news articles for Tata Consultancy Services

--- 📈 Analysis Step 7 ---
🤖 AI Decision: FUNCTION_CALL: analyze_sentiment|10
✅ Result: Analyzed sentiment for 28 articles. Overall: 70.0% positive, 15.0% negative, 15.0% neutral

--- 📈 Analysis Step 8 ---
🤖 AI Decision: FUNCTION_CALL: calculate_correlations
✅ Result: Calculated correlations for 25 data points. 68.0% correlation match (Moderate)

--- 📈 Analysis Step 9 ---
🤖 AI Decision: FUNCTION_CALL: generate_algo_strategy|20|medium
✅ Result: Algorithmic trading strategy generated for 20.0% CAGR target. Strategy includes entry/exit rules, position sizing, and risk management.

--- 📈 Analysis Step 10 ---
🤖 AI Decision: FINAL_ANSWER: [Analysis Complete]

🎉 === Stock Analysis Complete ===
📈 Final Analysis Summary:
📊 Stock: TCS.NS - Current: ₹4,125.30 (+0.8%)
📰 News: 28 articles analyzed
🧠 Sentiment: 70.0% positive, 15.0% negative
🔗 Correlation: 68.0% match (Moderate)
📈 RSI: 58.2 (Neutral)
📊 MACD: Bullish trend
📉 Bollinger: Normal Range
🤖 Algo Strategy: 20.0% CAGR target (medium risk)
```

### **📊 Natural Language Query Examples**
The agent understands natural language and automatically converts company names to proper symbols:

```bash
# Sentiment Analysis
"Analyze Reliance sentiment"
"What's the news on TCS?"
"Check Apple sentiment today"

# Technical Analysis  
"Calculate RSI for HDFC Bank"
"MACD analysis for Tesla"
"Full technical analysis of Infosys"

# Correlation Analysis
"Check Reliance news correlation with price"
"TCS sentiment vs price movement"
"Apple news impact analysis"

# Algorithmic Trading Strategies
"Generate algo strategy for 15% CAGR on Reliance"
"Create trading algorithm for 20% returns on TCS"
"Conservative strategy for 12% CAGR on HDFC"

# Comprehensive Analysis
"Full analysis of Apple stock"
"Complete study of Tesla with all indicators"
"Comprehensive analysis of Infosys"
```

### **🤖 AI Decision-Making Process**
1. **Query Parsing**: Converts natural language to structured intent
2. **Workflow Planning**: AI decides which tools are needed based on the request
3. **Data Gathering**: Fetches required stock data, news, and market information
4. **Analysis Execution**: Performs technical analysis, sentiment analysis, correlations
5. **Strategy Generation**: Creates algorithmic trading strategies if requested
6. **Report Compilation**: Generates comprehensive analysis reports
7. **Results Summary**: Provides actionable insights and recommendations

## 🔧 Architecture

### **MCP Server (`mcp_server.py`)**
- **FastMCP Framework**: Provides standardized tool interface
- **Stock Analysis Tools**: 8 specialized financial analysis functions
- **Data Management**: Maintains analysis context across tool calls
- **Error Handling**: Robust error recovery and reporting

### **MCP Client (`talk2mcp.py`)**
- **Gemini AI Integration**: Uses Gemini 2.0 Flash for decision making
- **Autonomous Orchestration**: Decides which tools to call and when
- **Workflow Management**: Handles multi-step analysis pipeline
- **Progress Tracking**: Real-time feedback on analysis progress

### **🛠️ Analysis Tools Suite**

#### **📊 Core Analysis Tools**

**1. `parse_query(query)`**
- Intelligent natural language parsing with step-by-step reasoning
- Converts company names to proper stock symbols (Reliance → RELIANCE.NS)
- Identifies analysis type and appropriate parameters
- Confidence scoring for parsing accuracy

**2. `fetch_stock_data(symbol, period, interval)`**
- Real-time OHLCV data from Yahoo Finance with Indian stock support
- Multiple timeframes: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo
- Automatic symbol formatting and validation
- Current price and percentage change calculations

**3. `fetch_news_data(symbol, days)`**
- Intelligent news sampling from NewsAPI with priority financial sources
- Multi-strategy approach: Priority sources + Popular articles + Time-distributed sampling
- Indian financial news sources: Economic Times, Business Standard, Mint, MoneyControl
- Advanced deduplication and relevance filtering

**4. `analyze_sentiment(batch_size)`**
- AI-powered sentiment analysis using Gemini 2.0 Flash
- Batch processing with confidence scoring and reasoning
- Sentiment statistics: positive/negative/neutral percentages
- Overall sentiment classification and insights

#### **📈 Technical Analysis Tools**

**5. `calculate_rsi(period=14)`**
- Relative Strength Index with customizable period
- Overbought (>70) and oversold (<30) signal detection
- Current RSI value with trend analysis
- Historical RSI data for strategy development

**6. `calculate_macd(fast_period=12, slow_period=26, signal_period=9)`**
- MACD line, signal line, and histogram calculation
- Bullish/bearish crossover detection
- Trend strengthening/weakening analysis
- Standard and customizable MACD parameters

**7. `calculate_bollinger_bands(period=20, std_dev=2.0)`**
- Upper and lower bands with standard deviation analysis
- Price position within bands (0-100% scale)
- Volatility analysis through band width
- Overbought/oversold signals based on band position

#### **🔗 Advanced Analysis Tools**

**8. `calculate_correlations()`**
- Time-aligned news sentiment and price movement analysis
- Statistical correlation with strength classification (Strong/Moderate/Weak)
- Correlation match percentage and detailed breakdowns
- Individual article-price correlation tracking

**9. `run_backtest(initial_capital, confidence_threshold)`**
- Sophisticated trading strategy simulation
- Long/short position management with automatic position switching
- Performance metrics: win rate, total return, Sharpe ratio
- Detailed trade history and risk-adjusted returns

#### **🤖 Strategy & Reporting Tools**

**10. `generate_algo_strategy(target_cagr, risk_tolerance)`**
- Target CAGR-based algorithmic trading strategy generation
- Risk tolerance levels: conservative, medium, aggressive
- Comprehensive strategy framework:
  - Mathematical position sizing and risk management
  - Specific entry/exit conditions based on available indicators
  - Implementation details and performance monitoring
  - Backtesting expectations and validation criteria

**11. `generate_analysis_report()`**
- AI-generated comprehensive analysis reports
- Professional formatting with executive summary
- Covers all analysis dimensions with actionable insights
- Risk assessment and trading recommendations

**12. `get_analysis_summary()`**
- Real-time analysis status and key metrics
- Technical indicator summaries (RSI, MACD, Bollinger Bands)
- Sentiment and correlation insights
- Strategy and performance tracking

## 🎯 Key Innovations

### **1. 🧠 Advanced AI Reasoning**
- **Step-by-Step Decision Making**: AI thinks through each decision before acting
- **Self-Verification**: Built-in checks to ensure analysis quality and completeness
- **Adaptive Workflows**: Dynamically adjusts approach based on query type and available data
- **Error Recovery**: Intelligent handling of failures with alternative approaches

### **2. 📈 Professional-Grade Technical Analysis**
- **Multiple Technical Indicators**: RSI, MACD, Bollinger Bands with customizable parameters
- **Signal Integration**: Combines multiple indicators for robust analysis
- **Real-Time Calculations**: Live technical analysis with current market data
- **Historical Context**: Technical indicator trends and pattern recognition

### **3. 🤖 Target CAGR-Based Strategy Generation**
- **Mathematical Approach**: Calculates position sizing and risk parameters for specific return targets
- **Risk-Adjusted Strategies**: Conservative, medium, and aggressive risk profiles
- **Implementation-Ready**: Specific entry/exit rules, stop-losses, and monitoring frameworks
- **Backtesting Integration**: Strategy validation with historical performance expectations

### **4. 🌍 Multi-Market Intelligence**
- **Indian Market Expertise**: Specialized support for NSE/BSE stocks with local news sources
- **Global Stock Support**: US, European, and other international markets
- **Intelligent Symbol Resolution**: Automatic conversion of company names to proper symbols
- **Market-Specific Analysis**: Adapts analysis approach based on market characteristics

### **5. 📊 Comprehensive Data Integration**
- **Multi-Source News Sampling**: Priority financial sources with intelligent article selection
- **Real-Time Market Data**: Live OHLCV data with multiple timeframe support
- **Sentiment-Price Correlation**: Statistical analysis of news impact on price movements
- **Cross-Validation**: Multiple data sources for robust analysis conclusions

### **6. 🏗️ Advanced MCP Architecture**
- **Protocol-Based Communication**: Standardized, reliable tool interaction
- **Modular Tool Design**: Easy addition of new indicators and analysis methods
- **Type-Safe Operations**: Robust parameter validation and error handling
- **Scalable Framework**: Designed for extension and customization

## 🔍 Example Analysis Outputs

### **Sentiment Analysis**
```
Analyzed sentiment for 25 articles:
- 60.0% positive sentiment
- 24.0% negative sentiment  
- 16.0% neutral sentiment
Overall sentiment: Positive
```

### **Correlation Analysis**
```
Calculated correlations for 18 data points:
- 72.2% correlation match (Strong)
- Average price change: +1.8%
- 13 positive sentiment articles
- 5 negative sentiment articles
```

### **Backtest Results**
```
Backtest Performance:
- Initial Capital: $10,000
- Final Value: $11,250
- Total Return: +12.5%
- Total Trades: 8
- Win Rate: 75.0%
- Buy Trades: 5
- Sell Trades: 3
```

## 🚀 Testing

### **Quick Test**
```bash
# Test with default symbol (TSLA)
python talk2mcp.py
# Just press Enter to use TSLA

# Test with specific symbol
python talk2mcp.py
# Enter: AAPL
```

### **Manual Tool Testing**
```bash
# Run server in development mode
python mcp_server.py dev

# Test individual tools
# (Use MCP client or testing framework)
```

## 🔮 Future Enhancements

### **Advanced Analysis**
- **Technical Indicators**: RSI, MACD, Bollinger Bands
- **Options Analysis**: Volatility and Greeks calculation
- **Sector Comparison**: Relative performance analysis
- **Risk Metrics**: VaR, Sharpe ratio, maximum drawdown

### **Data Sources**
- **Alternative Data**: Social media sentiment, satellite data
- **Economic Indicators**: GDP, inflation, interest rates
- **Earnings Data**: Financial statements and guidance
- **Insider Trading**: SEC filings and insider activity

### **AI Improvements**
- **Multi-Model Ensemble**: Combine multiple AI models
- **Fine-Tuned Models**: Domain-specific financial models
- **Real-Time Analysis**: Streaming data processing
- **Predictive Modeling**: Price forecasting capabilities

### **User Interface**
- **Web Dashboard**: Interactive analysis interface
- **API Endpoints**: RESTful API for integration
- **Mobile App**: On-the-go analysis capabilities
- **Alerts System**: Real-time notification system

## 🎮 Interactive Demo

### **Quick Demo Start**
```bash
# Interactive demo with guided prompts
python run_demo.py

# Or view all demo examples
python demo_prompts.py
```

### **🎯 Best Demo Queries**
```bash
# Indian Stocks (Recommended)
"Analyze Reliance Industries sentiment"
"Generate algo strategy for 18% CAGR on TCS"
"Full technical analysis of HDFC Bank"
"Check Infosys news correlation with price"

# US Stocks
"Tesla sentiment and technical analysis"
"Apple algo strategy for 15% CAGR"
"Microsoft comprehensive analysis"

# Technical Analysis Focus
"Calculate all indicators for Reliance"
"RSI and MACD signals for Apple"
"Bollinger Bands analysis for Tesla"

# Strategy Generation
"Conservative 12% CAGR strategy for HDFC"
"Aggressive 25% CAGR strategy for Tesla"
"Medium risk 20% returns on TCS"
```

### **📊 Demo Features**
- **🎲 Random Prompts**: Quick demo with pre-selected queries
- **📋 Categorized Examples**: Organized by analysis type and complexity
- **🚀 Automated Execution**: Runs the agent with selected prompts
- **📖 Guided Instructions**: Step-by-step setup and usage guide

---

## 🆘 Troubleshooting

### **Common Issues**

1. **API Key Errors**
   - Verify GEMINI_API_KEY is set correctly
   - Check API key permissions and quotas
   - Ensure .env file is in the correct directory

2. **Data Fetching Issues**
   - Check internet connection
   - Verify stock symbol is valid
   - Try different time periods if data is limited

3. **MCP Connection Issues**
   - Ensure mcp_server.py is executable
   - Check Python path and dependencies
   - Verify MCP framework installation

### **Debug Mode**
- Server logs show detailed function execution
- Client provides step-by-step analysis progress
- Error messages include specific failure reasons

---

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the MCP architecture patterns
4. Add appropriate error handling
5. Submit a pull request

---

## 🎉 Summary

Week-5 represents a significant evolution in autonomous financial analysis:

### **🚀 What Makes This Special**
- **🧠 Natural Language Understanding**: Just describe what you want - no technical knowledge required
- **📈 Professional-Grade Analysis**: Technical indicators, sentiment analysis, and correlation studies
- **🤖 AI-Powered Strategy Generation**: Target specific CAGR returns with mathematical precision
- **🌍 Multi-Market Support**: Seamless analysis of Indian and global stocks
- **⚡ Autonomous Operation**: AI decides the optimal analysis workflow for each query
- **🔧 Implementation-Ready**: Strategies include specific rules, parameters, and monitoring frameworks

### **🎯 Perfect For**
- **📊 Financial Analysts**: Comprehensive analysis with professional-grade tools
- **🤖 Algo Traders**: CAGR-targeted strategy generation with risk management
- **📈 Technical Analysts**: Multiple indicators with signal integration
- **💼 Investment Researchers**: Sentiment-price correlation analysis
- **🎓 Finance Students**: Learn through hands-on analysis and strategy development

### **🔮 Future-Ready Architecture**
Built on MCP protocol for easy extension with new indicators, data sources, and analysis methods. The modular design allows for continuous enhancement while maintaining reliability and performance.

---

**Built with ❤️ using MCP Protocol, Gemini AI, and Advanced Financial Analysis**

*Empowering intelligent investment decisions through autonomous AI analysis*
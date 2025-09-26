// Stock News + Price Correlator - Frontend Logic

class StockAnalyzer {
    constructor() {
        this.backendUrl = 'http://localhost:5000';
        this.currentAnalysis = null;
        this.currentSessionId = null;
        this.statusPollingInterval = null;
        this.currentStep = 0;
        this.lastFunctionName = '';
        
        
        this.initializeEventListeners();
        this.loadSavedSettings();
    }

    initializeEventListeners() {
        // Main natural language analysis button
        document.getElementById('analyzeBtn').addEventListener('click', () => this.runNaturalLanguageAnalysis());
        
        // Legacy analysis button
        document.getElementById('legacyAnalyzeBtn').addEventListener('click', () => this.runLegacyAnalysis());
        
        // Retry button
        document.getElementById('retryBtn').addEventListener('click', () => this.runNaturalLanguageAnalysis());
        
        // Export and save buttons are not in the HTML, so these lines are removed to prevent errors.
        // document.getElementById('exportBtn').addEventListener('click', () => this.exportReport());
        // document.getElementById('saveBtn').addEventListener('click', () => this.saveAnalysis());
        
        // Toggle manual input section
        document.getElementById('toggleManualInput').addEventListener('click', () => this.toggleManualInput());
        
        // Example query buttons
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                document.getElementById('naturalQuery').value = query;
            });
        });
        
        // Input validation for legacy inputs
        const stockSymbolInput = document.getElementById('stockSymbol');
        if (stockSymbolInput) {
            stockSymbolInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        }
        
        // Enter key support for natural query
        document.getElementById('naturalQuery').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.runNaturalLanguageAnalysis();
            }
        });
    }

    async loadSavedSettings() {
        try {
            const result = await chrome.storage.local.get(['lastSymbol', 'lastTimeframe']);
            if (result.lastSymbol) {
                document.getElementById('stockSymbol').value = result.lastSymbol;
            }
            if (result.lastTimeframe) {
                document.getElementById('timeframe').value = result.lastTimeframe;
            }
        } catch (error) {
            console.error('Error loading saved settings:', error);
        }
    }

    async saveSettings(symbol, timeframe) {
        try {
            await chrome.storage.local.set({
                lastSymbol: symbol,
                lastTimeframe: timeframe
            });
        } catch (error) {
            console.error('Error saving settings:', error);
        }
    }

    async runNaturalLanguageAnalysis() {
        const query = document.getElementById('naturalQuery').value.trim();
        if (!query) {
            this.showError('Please enter a query to analyze.');
            return;
        }

        // Reset state for new analysis
        this.hideAllSections();
        this.stopProgressTracking(); // Stop any previous polling
        this.currentStep = 0;
        this.lastFunctionName = '';
        this.currentSessionId = null;
        await this.saveSettings(query, 'natural_query');

        this.showStatus('🚀 Initializing analysis...', 5);

        try {
            const response = await fetch(`${this.backendUrl}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            if (response.status !== 202) { // 202 Accepted is the expected success code
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Analysis request failed: ${response.statusText}`);
            }

            const data = await response.json();
            if (data.session_id) {
                this.currentSessionId = data.session_id;
                this.startRealTimeProgressTracking(this.currentSessionId);
            } else {
                throw new Error('Backend did not return a session ID.');
            }

        } catch (error) {
            console.error('Analysis initiation failed:', error);
            this.showError(error.message || 'Could not start the analysis.');
            this.stopProgressTracking();
        }
    }

    async getFinalResults(sessionId) {
        try {
            this.updateStatus('✅ Analysis Complete! Fetching results...', 100);
            const response = await fetch(`${this.backendUrl}/api/results/${sessionId}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || 'Failed to retrieve final results.');
            }

            const finalData = await response.json();
            await this.displayAgentResults(finalData);
            setTimeout(() => this.hideStatus(), 2000);

            return finalData; // Return data for error handling case

        } catch (error) {
            console.error('Failed to get final results:', error);
            this.showError(error.message);
            return { error: error.message }; // Return error for error handling case
        }
    }

    async runLegacyAnalysis() {
        const symbol = document.getElementById('stockSymbol').value.trim();
        const timeframe = document.getElementById('timeframe').value;

        if (!symbol) {
            this.showError('Please enter a stock symbol for manual analysis.');
            return;
        }

        // Construct a natural language query from the manual inputs
        const query = `Perform a full analysis for ${symbol} using a ${timeframe} timeframe.`;
        
        // Set the main query input and run the standard analysis flow
        document.getElementById('naturalQuery').value = query;
        this.runNaturalLanguageAnalysis();
    }

    

    

    async pollBackendStatus(sessionId) {
        if (!sessionId) return;

        try {
            const response = await fetch(`${this.backendUrl}/api/status/${sessionId}`);
            if (!response.ok) return; // Silently fail and retry on the next interval

            const status = await response.json();

            // Stop polling if analysis is complete or has failed
            if (status.status === 'completed' || status.status === 'error') {
                this.stopProgressTracking();
                if (status.status === 'completed') {
                    await this.getFinalResults(sessionId);
                } else {
                    // Attempt to get a more detailed error message from the results endpoint
                    const errorResult = await this.getFinalResults(sessionId).catch(() => ({ message: 'Analysis failed on the backend.' }));
                    this.showError(errorResult.message || status.message || 'An unknown error occurred.');
                }
                return;
            }

            // Update progress based on the user's rules
            if (status.current_function && status.current_function !== this.lastFunctionName) {
                this.lastFunctionName = status.current_function;
                this.currentStep = status.step;

                let progress = this.currentStep * 10;
                if (this.currentStep > 9) {
                    progress = 90; // Cap at 90% if more than 9 steps
                }

                const enhancedMessage = this.enhanceStatusMessage(status.message, status.current_function);
                this.updateStatus(enhancedMessage, progress);
                console.log(`Step ${this.currentStep}: ${enhancedMessage} (Progress: ${progress}%)`);
            }

        } catch (error) {
            console.warn('Status polling error:', error);
            // Don't stop polling on a single network error, allow it to retry
        }
    }

    enhanceStatusMessage(message, currentFunction) {
        // Add more context based on the current function being executed
        const functionEnhancements = {
            'fetch_market_data': {
                '📊 Fetching market data': '📊 Fetching market data from Yahoo Finance...',
                'Validating': '🔍 Validating stock symbol...',
                'Configuring': '⏰ Configuring timeframe parameters...',
                'Fetching': '📈 Downloading historical price data...',
                'Processing': '🔄 Processing candle data...'
            },
            'fetch_news_data': {
                '📰 Retrieving news': '📰 Retrieving news headlines with intelligent sampling...',
                'Getting company': '🏢 Getting company information...',
                'Fetching priority': '⭐ Fetching priority financial news sources...',
                'Fetching popular': '🔥 Fetching popular articles...',
                'Fetching distributed': '📅 Fetching time-distributed articles...',
                'Removing duplicates': '🔄 Removing duplicate articles...'
            },
            'analyze_sentiment': {
                '🧠 Analyzing sentiment': '🧠 AI analyzing sentiment with Google Gemini...',
                'Preparing headlines': '📝 Preparing headlines for AI analysis...',
                'AI batch processing': '🤖 Processing sentiment in batches...',
                'Aggregating results': '📊 Aggregating sentiment results...'
            },
            'calculate_correlations': {
                '🔗 Calculating correlations': '🔗 Calculating news-price correlations...',
                'Aligning timestamps': '⏰ Aligning news and price timestamps...',
                'Calculating price changes': '📈 Calculating price movements...',
                'Computing correlations': '🔢 Computing statistical correlations...',
                'Statistical analysis': '📊 Performing statistical analysis...'
            },
            'run_backtest': {
                '📈 Running backtest': '📈 Running backtest simulations...',
                'Setting up portfolio': '💼 Setting up trading portfolio...',
                'Generating signals': '📡 Generating trading signals...',
                'Executing trades': '💰 Simulating trade executions...',
                'Calculating metrics': '📊 Calculating performance metrics...'
            },
            'generate_strategy': {
                '💡 Generating strategy': '💡 Generating strategy recommendations...',
                'Analyzing patterns': '🔍 Analyzing market patterns...',
                'Generating recommendations': '💡 Creating actionable recommendations...'
            }
        };

        if (currentFunction && functionEnhancements[currentFunction]) {
            const enhancements = functionEnhancements[currentFunction];
            
            // Find the best match for the message
            for (const [key, enhancement] of Object.entries(enhancements)) {
                if (message.includes(key)) {
                    return enhancement;
                }
            }
        }

        // Return original message if no enhancement found
        return message;
    }

    startRealTimeProgressTracking(sessionId) {
        if (!sessionId) {
            console.warn('No session ID provided for real-time progress tracking.');
            return;
        }
        
        console.log('Starting real-time progress tracking for session:', sessionId);
        
        // Poll backend status every 2 seconds
        this.statusPollingInterval = setInterval(() => {
            this.pollBackendStatus(sessionId);
        }, 2000);
    }

    toggleManualInput() {
        const section = document.getElementById('manualInputSection');
        const icon = document.getElementById('toggleIcon');
        
        if (section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            icon.style.transform = 'rotate(180deg)';
        } else {
            section.classList.add('hidden');
            icon.style.transform = 'rotate(0deg)';
        }
    }

    stopProgressTracking() {
        // Clear status polling
        if (this.statusPollingInterval) {
            clearInterval(this.statusPollingInterval);
            this.statusPollingInterval = null;
        }
    }

    async analyzeCorrelations(symbol, candlesData, newsData) {
        const response = await fetch(`${this.backendUrl}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                symbol: symbol,
                candles: candlesData,
                news: newsData
            })
        });

        if (!response.ok) {
            throw new Error(`Analysis failed: ${response.statusText}`);
        }
        return await response.json();
    }

    async displayAgentResults(data) {
        try {
            this.currentAnalysis = data;

            // Handle the new modular backend response format
            console.log('Agent Response:', data);

            // Show analysis information
            this.displayAnalysisInfo(data);

            // Extract metrics from iteration logs if available
            this.displayMetricsFromLogs(data);

            // Show results section FIRST to ensure elements are visible
            const resultsSection = document.getElementById('resultsSection');
            if (resultsSection) {
                resultsSection.classList.remove('hidden');
            } else {
                console.error('resultsSection element not found');
                return;
            }

            // Display the AI agent's final answer
            const strategyDiv = document.getElementById('strategyRecommendation');
            if (!strategyDiv) {
                console.error('strategyRecommendation element not found');
                return;
            }
        
        if (data.final_answer) {
            // Convert basic markdown to HTML for better display
            const formattedAnswer = this.convertMarkdownToHtml(data.final_answer);
            
            strategyDiv.innerHTML = `
                <div class="analysis-result">
                    <h4 style="font-weight: bold; margin-bottom: 8px;">🤖 AI Analysis Result:</h4>
                    <div style="line-height: 1.5;">${formattedAnswer}</div>
                    
                    <div style="margin-top: 12px; padding: 12px; background: #f3f4f6; border-radius: 6px; border-left: 4px solid #2563eb;">
                        <div style="color: #374151; margin-bottom: 8px;">
                            <strong>📊 Analysis Summary:</strong>
                        </div>
                        <div style="color: #6b7280; font-size: 13px; line-height: 1.4;">
                            <div style="margin-bottom: 4px;"><strong>Symbol:</strong> ${data.symbol}</div>
                            <div style="margin-bottom: 4px;"><strong>Timeframe:</strong> ${data.timeframe}</div>
                            <div style="margin-bottom: 4px;"><strong>AI Iterations:</strong> ${data.iterations}</div>
                            <div style="margin-bottom: 4px;"><strong>Status:</strong> <span style="color: #059669; font-weight: 500;">${data.status}</span></div>
                            <div><strong>Functions Used:</strong> ${this.extractFunctionsCalled(data.iteration_log)}</div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            strategyDiv.innerHTML = `
                <div class="analysis-result">
                    <h4 style="font-weight: bold; margin-bottom: 8px;">📊 Analysis Status:</h4>
                    <p>Status: ${data.status}</p>
                    <p>Iterations: ${data.iterations}</p>
                    ${data.iteration_log ? `<p>Last step: ${data.iteration_log[data.iteration_log.length - 1]}</p>` : ''}
                </div>
            `;
        }

        // Create actual chart with real data
        this.createAnalysisChart(data);

            // Display correlation table if available
            if (data.correlation_insights && data.correlation_insights.correlations) {
                this.displayCorrelationTable(data.correlation_insights.correlations);
            }

        } catch (error) {
            console.error('Error displaying agent results:', error);
            this.showError('Failed to display analysis results: ' + error.message);
        }
    }

    displayMetricsFromLogs(data) {
        // Use actual backtest results if available
        if (data.backtest_results && Object.keys(data.backtest_results).length > 0) {
            const results = data.backtest_results;
            this.safeSetTextContent('winRate', `${(results.win_rate * 100).toFixed(1)}%`);
            this.safeSetTextContent('sharpeRatio', results.sharpe_ratio.toFixed(2));
            this.safeSetTextContent('totalPnL', `${results.total_pnl >= 0 ? '+' : ''}${results.total_pnl.toFixed(2)}%`);
        } else {
            this.safeSetTextContent('winRate', 'N/A');
            this.safeSetTextContent('sharpeRatio', 'N/A');
            this.safeSetTextContent('totalPnL', 'N/A');
        }
        
        // Use actual correlation results if available
        if (data.correlation_insights && data.correlation_insights.strength) {
            this.safeSetTextContent('correlation', data.correlation_insights.strength);
        } else {
            this.safeSetTextContent('correlation', 'N/A');
        }
    }

    safeSetTextContent(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        } else {
            console.warn(`Element with ID '${elementId}' not found`);
        }
    }

    extractFunctionsCalled(logs) {
        if (!logs) return 'None';
        
        const functions = [];
        logs.forEach(log => {
            if (log.includes('fetch_market_data')) functions.push('Market Data');
            if (log.includes('fetch_news_data')) functions.push('News Data');
            if (log.includes('analyze_sentiment')) functions.push('Sentiment Analysis');
            if (log.includes('calculate_correlations')) functions.push('Correlations');
            if (log.includes('run_backtest')) functions.push('Backtesting');
            if (log.includes('generate_strategy')) functions.push('Strategy');
        });
        
        return functions.length > 0 ? functions.join(', ') : 'Query Processing';
    }

    convertMarkdownToHtml(text) {
        if (!text) return '';
        
        // Simple markdown to HTML conversion
        let html = text
            // Convert **bold** to <strong>
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            // Convert *italic* to <em>
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Convert bullet points (- or *) to HTML lists
            .replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>')
            // Convert numbered lists
            .replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>')
            // Convert line breaks to <br>
            .replace(/\n/g, '<br>')
            // Convert ### headers to h4
            .replace(/^###\s+(.+)$/gm, '<h4 style="font-weight: bold; margin: 8px 0;">$1</h4>')
            // Convert ## headers to h3
            .replace(/^##\s+(.+)$/gm, '<h3 style="font-weight: bold; margin: 10px 0;">$1</h3>');
        
        // Wrap consecutive <li> elements in <ul>
        html = html.replace(/(<li>.*?<\/li>)(?:\s*<br>\s*<li>.*?<\/li>)*/g, function(match) {
            return '<ul style="margin: 8px 0; padding-left: 20px;">' + match.replace(/<br>/g, '') + '</ul>';
        });
        
        return html;
    }

    createAnalysisChart(data) {
        try {
            // Use the existing createPriceChart method with actual data
            if (data.candles && data.candles.length > 0) {
                this.createPriceChart(data.candles, data.news_analysis || []);
            } else {
                // Hide the chart section if no data
                const chartSection = document.querySelector('.chart-section');
                if (chartSection) {
                    chartSection.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error creating analysis chart:', error);
        }
    }

    displayAnalysisInfo(data) {
        // Display basic analysis information
        console.log('Analysis Info:', {
            symbol: data.symbol,
            timeframe: data.timeframe,
            status: data.status,
            iterations: data.iterations
        });
    }

    displayQueryInfo(data) {
        // Add query information to the results
        const resultsSection = document.getElementById('resultsSection');
        if (!resultsSection) {
            console.warn('resultsSection element not found');
            return;
        }
        
        const queryInfo = document.createElement('div');
        queryInfo.className = 'mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg';
        queryInfo.innerHTML = `
            <div class="text-sm">
                <div class="font-medium text-blue-800 mb-1">🤖 Agent Analysis</div>
                <div class="text-blue-700 mb-2"><strong>Query:</strong> "${data.original_query || 'N/A'}"</div>
                <div class="text-blue-600 text-xs">
                    <strong>Detected:</strong> ${data.parsed_intent?.symbol || 'N/A'} | ${data.parsed_intent?.timeframe || 'N/A'} | ${data.parsed_intent?.task || 'N/A'}
                </div>
            </div>
        `;
        
        // Insert at the beginning of results section
        const firstChild = resultsSection.querySelector('.p-4');
        if (firstChild) {
            firstChild.insertBefore(queryInfo, firstChild.firstChild);
        }
    }



    createPriceChart(candles, newsAnalysis) {
        const canvas = document.getElementById('priceChart');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = 380;
        canvas.height = 200;
        
        if (!candles || candles.length === 0) {
            ctx.fillStyle = '#6b7280';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('No price data available', canvas.width / 2, canvas.height / 2);
            return;
        }

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Get price data
        const prices = candles.map(candle => candle.close);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const priceRange = maxPrice - minPrice;
        
        // Chart dimensions
        const padding = 40;
        const chartWidth = canvas.width - 2 * padding;
        const chartHeight = canvas.height - 2 * padding;
        
        // Draw axes
        ctx.strokeStyle = '#e5e7eb';
        ctx.lineWidth = 1;
        
        // Y-axis
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, canvas.height - padding);
        ctx.stroke();
        
        // X-axis
        ctx.beginPath();
        ctx.moveTo(padding, canvas.height - padding);
        ctx.lineTo(canvas.width - padding, canvas.height - padding);
        ctx.stroke();
        
        // Draw price line
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = 2;
        ctx.beginPath();
        
        for (let i = 0; i < prices.length; i++) {
            const x = padding + (i / (prices.length - 1)) * chartWidth;
            const y = canvas.height - padding - ((prices[i] - minPrice) / priceRange) * chartHeight;
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }
        ctx.stroke();
        
        // Draw sentiment points if available
        if (newsAnalysis && newsAnalysis.length > 0) {
            newsAnalysis.forEach(news => {
                const newsDate = new Date(news.date);
                const priceAtDate = this.findPriceAtDate(candles, news.date);
                
                if (priceAtDate) {
                    const x = padding + this.getDatePosition(candles, newsDate) * chartWidth;
                    const y = canvas.height - padding - ((priceAtDate - minPrice) / priceRange) * chartHeight;
                    
                    // Set color based on sentiment
                    ctx.fillStyle = news.sentiment === 'positive' ? '#10b981' : 
                                   news.sentiment === 'negative' ? '#ef4444' : '#6b7280';
                    
                    ctx.beginPath();
                    ctx.arc(x, y, 4, 0, 2 * Math.PI);
                    ctx.fill();
                }
            });
        }
        
        // Draw labels
        ctx.fillStyle = '#6b7280';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        
        // Price labels
        ctx.textAlign = 'right';
        ctx.fillText(maxPrice.toFixed(2), padding - 5, padding + 5);
        ctx.fillText(minPrice.toFixed(2), padding - 5, canvas.height - padding + 5);
        
        // Title
        ctx.textAlign = 'center';
        ctx.fillStyle = '#374151';
        ctx.font = 'bold 14px Arial';
        ctx.fillText('Price Movement with Sentiment', canvas.width / 2, 20);
    }

    findPriceAtDate(candles, date) {
        const targetDate = new Date(date).getTime();
        let closestCandle = null;
        let minDiff = Infinity;
        
        candles.forEach(candle => {
            const candleTime = new Date(candle.timestamp).getTime();
            const diff = Math.abs(candleTime - targetDate);
            if (diff < minDiff) {
                minDiff = diff;
                closestCandle = candle;
            }
        });
        
        return closestCandle ? closestCandle.close : null;
    }
    
    getDatePosition(candles, targetDate) {
        if (candles.length === 0) return 0;
        
        const startTime = new Date(candles[0].timestamp).getTime();
        const endTime = new Date(candles[candles.length - 1].timestamp).getTime();
        const targetTime = targetDate.getTime();
        
        if (targetTime <= startTime) return 0;
        if (targetTime >= endTime) return 1;
        
        return (targetTime - startTime) / (endTime - startTime);
    }

    displayCorrelationTable(correlations) {
        const tableContainer = document.getElementById('correlationTable');
        if (!tableContainer) {
            console.warn('correlationTable element not found');
            return;
        }
        
        let tableHTML = `
            <table class="min-w-full bg-white border border-gray-200 rounded-lg overflow-hidden">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">News</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Sentiment</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price Move</th>
                        <th class="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Correlation</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
        `;

        correlations.forEach(corr => {
            const sentimentColor = corr.sentiment === 'positive' ? 'text-green-600' : 
                                 corr.sentiment === 'negative' ? 'text-red-600' : 'text-gray-600';
            const priceColor = corr.price_change > 0 ? 'text-green-600' : 
                              corr.price_change < 0 ? 'text-red-600' : 'text-gray-600';
            const correlationIcon = corr.correlation_match ? '✅' : '❌';

            tableHTML += `
                <tr class="hover:bg-gray-50">
                    <td class="px-3 py-2 text-sm text-gray-900">${new Date(corr.date).toLocaleDateString()}</td>
                    <td class="px-3 py-2 text-sm text-gray-900 max-w-xs truncate" title="${corr.headline}">${corr.headline}</td>
                    <td class="px-3 py-2 text-sm ${sentimentColor} font-medium">${corr.sentiment}</td>
                    <td class="px-3 py-2 text-sm ${priceColor} font-medium">${corr.price_change > 0 ? '+' : ''}${corr.price_change.toFixed(2)}%</td>
                    <td class="px-3 py-2 text-sm">${correlationIcon}</td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        tableContainer.innerHTML = tableHTML;
    }

    showStatus(message, progress) {
        const statusSection = document.getElementById('statusSection');
        const statusText = document.getElementById('statusText');
        const progressBar = document.getElementById('progressBar');
        
        if (statusSection) {
            statusSection.classList.remove('hidden');
        }
        if (statusText) {
            statusText.textContent = message;
        }
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    updateStatus(message, progress) {
        const statusText = document.getElementById('statusText');
        const progressBar = document.getElementById('progressBar');
        
        if (statusText) {
            statusText.textContent = message;
        }
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    hideStatus() {
        const statusSection = document.getElementById('statusSection');
        if (statusSection) {
            statusSection.classList.add('hidden');
        }
    }

    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        const errorSection = document.getElementById('errorSection');
        
        if (errorMessage) {
            errorMessage.textContent = message;
        }
        if (errorSection) {
            errorSection.classList.remove('hidden');
        }
        this.hideStatus();
    }

    hideAllSections() {
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('errorSection').classList.add('hidden');
        document.getElementById('statusSection').classList.add('hidden');
    }

    async exportReport() {
        if (!this.currentAnalysis) return;

        const report = this.generateReport(this.currentAnalysis);
        const blob = new Blob([report], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `stock-analysis-${this.currentAnalysis.symbol}-${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateReport(data) {
        return `# Stock Analysis Report: ${data.symbol}

**Generated:** ${new Date().toLocaleString()}
**Timeframe:** ${data.timeframe}

## Summary Metrics
- **Win Rate:** ${(data.backtest.win_rate * 100).toFixed(1)}%
- **Sharpe Ratio:** ${data.backtest.sharpe_ratio.toFixed(2)}
- **Total PnL:** ${data.backtest.total_pnl.toFixed(2)}%
- **Correlation Strength:** ${data.correlation.strength}

## Strategy Recommendation
${data.strategy_recommendation}

## Correlation Analysis
${data.correlations.map(corr => 
    `- **${new Date(corr.date).toLocaleDateString()}:** ${corr.headline} (${corr.sentiment}) → ${corr.price_change > 0 ? '+' : ''}${corr.price_change.toFixed(2)}% ${corr.correlation_match ? '✅' : '❌'}`
).join('\n')}

---
*Generated by Stock News + Price Correlator*
`;
    }

    async saveAnalysis() {
        if (!this.currentAnalysis) return;

        try {
            const savedAnalyses = await chrome.storage.local.get(['savedAnalyses']) || { savedAnalyses: [] };
            const analyses = savedAnalyses.savedAnalyses || [];
            
            analyses.push({
                ...this.currentAnalysis,
                savedAt: new Date().toISOString()
            });

            await chrome.storage.local.set({ savedAnalyses: analyses });
            
            // Show success feedback
            const saveBtn = document.getElementById('saveBtn');
            const originalText = saveBtn.textContent;
            saveBtn.textContent = '✅ Saved!';
            saveBtn.classList.add('bg-green-700');
            
            setTimeout(() => {
                saveBtn.textContent = originalText;
                saveBtn.classList.remove('bg-green-700');
            }, 2000);

        } catch (error) {
            console.error('Error saving analysis:', error);
        }
    }

    toggleManualInput() {
        const section = document.getElementById('manualInputSection');
        const icon = document.getElementById('toggleIcon');
        
        if (section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            icon.style.transform = 'rotate(180deg)';
        } else {
            section.classList.add('hidden');
            icon.style.transform = 'rotate(0deg)';
        }
    }
}

// Initialize the analyzer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new StockAnalyzer();
});
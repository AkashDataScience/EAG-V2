// Smart Paper & Doc Summarizer - Popup Script
class SmartSummarizer {
    constructor() {
        this.apiKey = null;
        this.currentContent = '';
        this.focusMode = 'technical';
        this.results = {};
        
        this.initializeEventListeners();
        this.loadStoredData();
    }

    async initializeEventListeners() {
        // API Key management
        document.getElementById('saveApiKey').addEventListener('click', () => this.saveApiKey());
        document.getElementById('toggleApiKey').addEventListener('click', () => this.toggleApiKeyVisibility());
        
        // Content input methods
        document.getElementById('useCurrentPage').addEventListener('click', () => this.useCurrentPage());
        document.getElementById('uploadPdf').addEventListener('click', () => this.triggerPdfUpload());
        document.getElementById('pdfInput').addEventListener('change', (e) => this.handlePdfUpload(e));
        document.getElementById('contentInput').addEventListener('input', (e) => this.updateContent(e.target.value));
        
        // Focus mode selection
        document.getElementById('focusMode').addEventListener('change', (e) => this.updateFocusMode(e.target.value));
        
        // Main action
        document.getElementById('summarizeBtn').addEventListener('click', () => this.summarizeContent());
        
        // Results actions
        document.getElementById('copyResults').addEventListener('click', () => this.copyResults());
        document.getElementById('exportMarkdown').addEventListener('click', () => this.exportMarkdown());
        document.getElementById('exportPdf').addEventListener('click', () => this.exportPdf());
        
        // Collapsible sections
        this.initializeCollapsibles();
    }

    async loadStoredData() {
        try {
            const result = await chrome.storage.sync.get(['apiKey']);
            if (result.apiKey) {
                this.apiKey = result.apiKey;
                document.getElementById('apiKeyInput').value = result.apiKey;
                this.showMainContent();
            }
        } catch (error) {
            console.error('Error loading stored data:', error);
        }
    }

    async saveApiKey() {
        const apiKey = document.getElementById('apiKeyInput').value.trim();
        if (!apiKey) {
            this.showError('Please enter a valid API key');
            return;
        }

        if (!apiKey.startsWith('AIza')) {
            this.showError('Google AI API key should start with "AIza"');
            return;
        }

        try {
            await chrome.storage.sync.set({ apiKey });
            this.apiKey = apiKey;
            this.showMainContent();
            this.hideError();
        } catch (error) {
            this.showError('Failed to save API key');
        }
    }

    toggleApiKeyVisibility() {
        const input = document.getElementById('apiKeyInput');
        const toggleText = document.getElementById('toggleText');
        
        if (input.type === 'password') {
            input.type = 'text';
            toggleText.textContent = 'Hide';
        } else {
            input.type = 'password';
            toggleText.textContent = 'Show';
        }
    }

    showMainContent() {
        document.getElementById('apiKeySection').style.display = 'none';
        document.getElementById('mainContent').style.display = 'block';
    }

    async useCurrentPage() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // Check if it's a PDF page
            if (tab.url.includes('.pdf') || tab.url.includes('pdf')) {
                this.showError('PDF pages cannot be extracted directly. Please use one of these methods:\n\n1. Copy the text from the PDF viewer manually\n2. Use the "Upload PDF" button for instructions\n3. Paste the content manually in the text area below');
                return;
            }
            
            // Inject content script to extract text
            const results = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                function: this.extractPageContent
            });

            if (results && results[0] && results[0].result) {
                const result = results[0].result;
                
                // Handle PDF page detection
                if (result === 'PDF_PAGE_DETECTED') {
                    this.showError('PDF pages cannot be extracted directly. Please use one of these methods:\n\n1. Copy the text from the PDF viewer manually\n2. Use the "Upload PDF" button for instructions\n3. Paste the content manually in the text area below');
                    return;
                }
                
                // Handle error cases
                if (result.error) {
                    this.showError(`Content extraction failed: ${result.error}\n\nTry copying the text manually or using a different page.`);
                    return;
                }
                
                // Handle successful extraction
                if (result.content && result.content.length > 50) {
                    this.currentContent = result.content;
                    document.getElementById('contentInput').value = result.content;
                    this.showSuccess(`Page content extracted successfully!\n\nSource: ${result.source}\nWords: ${result.wordCount}\nCharacters: ${result.content.length}`);
                } else {
                    this.showError('Page content appears to be empty or restricted. Try:\n\n1. Refreshing the page and trying again\n2. Copying the text manually\n3. Using a different page');
                }
            } else {
                this.showError('Failed to extract page content. This might be due to:\n\n1. Page restrictions (PDF, protected content)\n2. Page not fully loaded\n3. Browser security policies\n\nTry copying the text manually or using a different page.');
            }
        } catch (error) {
            console.error('Error extracting page content:', error);
            
            // Provide specific error messages based on error type
            if (error.message.includes('Cannot access')) {
                this.showError('Cannot access page content due to browser security. Try:\n\n1. Copying the text manually\n2. Using a different page\n3. Refreshing the page');
            } else if (error.message.includes('PDF')) {
                this.showError('PDF pages cannot be extracted directly. Please copy the text manually or use the upload option.');
            } else {
                this.showError('Failed to extract page content. Please try:\n\n1. Refreshing the page\n2. Copying the text manually\n3. Using a different page');
            }
        }
    }

    triggerPdfUpload() {
        document.getElementById('pdfInput').click();
    }

    async handlePdfUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            this.showError('Please select a valid PDF file');
            return;
        }

        try {
            const text = await this.extractPdfText(file);
            this.currentContent = text;
            document.getElementById('contentInput').value = text;
            this.showSuccess('PDF content extracted successfully!');
        } catch (error) {
            console.error('Error extracting PDF:', error);
            this.showError('Failed to extract PDF content');
        }
    }

    async extractPdfText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = async function(e) {
                try {
                    // Check if PDF.js is available
                    if (typeof pdfjsLib === 'undefined') {
                        throw new Error('PDF.js library not loaded');
                    }

                    const typedarray = new Uint8Array(e.target.result);
                    const pdf = await pdfjsLib.getDocument(typedarray).promise;
                    let fullText = '';

                    // Extract text from all pages
                    for (let i = 1; i <= pdf.numPages; i++) {
                        const page = await pdf.getPage(i);
                        const textContent = await page.getTextContent();
                        const pageText = textContent.items.map(item => item.str).join(' ');
                        fullText += pageText + '\n';
                    }

                    // Clean up the text
                    const cleanedText = fullText
                        .replace(/\s+/g, ' ')
                        .replace(/\n\s*\n/g, '\n')
                        .trim();

                    if (cleanedText.length < 50) {
                        throw new Error('PDF appears to be empty or contains only images');
                    }

                    resolve(cleanedText);
                } catch (error) {
                    console.error('PDF extraction error:', error);
                    
                    // Fallback message with helpful instructions
                    const fallbackMessage = `PDF extraction failed: ${error.message}

Alternative methods:
1. Copy text from PDF viewer (Ctrl+A, Ctrl+C)
2. Use online PDF-to-text converters
3. Paste content manually below

File: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;

                    resolve(fallbackMessage);
                }
            };
            reader.onerror = reject;
            reader.readAsArrayBuffer(file);
        });
    }

    updateContent(content) {
        this.currentContent = content;
    }

    updateFocusMode(mode) {
        this.focusMode = mode;
    }

    async summarizeContent() {
        if (!this.currentContent.trim()) {
            this.showError('Please provide content to summarize');
            return;
        }

        if (!this.apiKey) {
            this.showError('Please configure your API key first');
            return;
        }

        this.showLoading(true);
        this.hideError();

        try {
            const results = await this.callGemini();
            this.displayResults(results);
            this.showResults();
        } catch (error) {
            console.error('Error during summarization:', error);
            this.showError(`Summarization failed: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    async callGemini() {
        const prompt = this.buildPrompt();
        
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${this.apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `You are an expert research analyst. Provide structured, detailed responses for each research step.\n\n${prompt}`
                    }]
                }],
                generationConfig: {
                    temperature: 0.7,
                    maxOutputTokens: 4000,
                    topP: 0.8,
                    topK: 10
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error?.message || 'API request failed');
        }

        const data = await response.json();
        const content = data.candidates[0].content.parts[0].text;
        console.log('Raw Gemini Response:', content);
        return this.parseResponse(content);
    }

    buildPrompt() {
        const focusInstructions = {
            technical: 'Focus on algorithms, optimization techniques, experimental methodologies, and technical implementations.',
            legal: 'Emphasize compliance requirements, regulatory frameworks, policy implications, and legal considerations.',
            privacy: 'Highlight data protection measures, anonymization techniques, privacy-preserving methods, and safe AI practices.',
            biometrics: 'Concentrate on biometric authentication methods, liveness detection, fairness in biometric systems, and accuracy metrics.'
        };

        return `
You are an expert research analyst. Your task is to read the provided document and propose a NEW research project based on it.

Analyze the following content and generate a novel research plan by following the 5 steps below.

Focus mode: ${this.focusMode.toUpperCase()}.
${focusInstructions[this.focusMode]}

Content to analyze:
${this.currentContent}

Please provide your analysis in the following structured format:

STEP 1 - NEW RESEARCH PROBLEM IDENTIFICATION:
[Based on the paper's content, limitations, and future work sections, identify and propose a NEW, UNSOLVED research problem. Clearly state the research gaps this new problem addresses and formulate specific, novel research questions.]

STEP 2 - RESEARCH DESIGN FOR THE NEW PROBLEM:
[For the new problem identified in Step 1, suggest an appropriate research design, methodology, and approach. Justify why this design is suitable for the proposed new research.]

STEP 3 - DATA COLLECTION FOR THE NEW PROBLEM:
[For the new research problem, recommend specific instruments, tools, and methods for data collection. If new data is needed, describe how it would be generated.]

STEP 4 - SAMPLING STRATEGIES FOR THE NEW PROBLEM:
[For the new research problem, propose suitable sampling methods, target populations, and sample size considerations.]

STEP 5 - RESEARCH PROPOSAL FOR THE NEW PROBLEM:
[Write a mini research proposal for the NEW problem. It should include a clear title, objectives, a summary of the methodology from the steps above, expected contributions, and a high-level project timeline.]

Ensure each step is detailed, actionable, and builds upon the previous one, all focused on the NEW research problem you have identified.
        `;
    }

    parseResponse(response) {
        const steps = {};
        const stepPatterns = [
            { key: 'step1', pattern: /STEP 1[*\s:-]*(?:NEW RESEARCH PROBLEM IDENTIFICATION)?[*\s:-]*\n?(.*?)(?=STEP 2|$)/is },
            { key: 'step2', pattern: /STEP 2[*\s:-]*(?:RESEARCH DESIGN FOR THE NEW PROBLEM)?[*\s:-]*\n?(.*?)(?=STEP 3|$)/is },
            { key: 'step3', pattern: /STEP 3[*\s:-]*(?:DATA COLLECTION FOR THE NEW PROBLEM)?[*\s:-]*\n?(.*?)(?=STEP 4|$)/is },
            { key: 'step4', pattern: /STEP 4[*\s:-]*(?:SAMPLING STRATEGIES FOR THE NEW PROBLEM)?[*\s:-]*\n?(.*?)(?=STEP 5|$)/is },
            { key: 'step5', pattern: /STEP 5[*\s:-]*(?:RESEARCH PROPOSAL FOR THE NEW PROBLEM)?[*\s:-]*\n?(.*?)$/is }
        ];

        stepPatterns.forEach(({ key, pattern }) => {
            const match = response.match(pattern);
            steps[key] = match ? match[1].trim() : 'Content not found for this step.';
        });

        return steps;
    }

    displayResults(results) {
        this.results = results;
        
        document.getElementById('step1Content').innerHTML = this.markdownToHtml(results.step1) || 'No content available';
        document.getElementById('step2Content').innerHTML = this.markdownToHtml(results.step2) || 'No content available';
        document.getElementById('step3Content').innerHTML = this.markdownToHtml(results.step3) || 'No content available';
        document.getElementById('step4Content').innerHTML = this.markdownToHtml(results.step4) || 'No content available';
        document.getElementById('step5Content').innerHTML = this.markdownToHtml(results.step5) || 'No content available';
    }

    markdownToHtml(text) {
        if (!text) return '';
        const lines = text.trim().split('\n');
        const htmlLines = [];
        let inUl = false;
        let inOl = false;

        for (const line of lines) {
            let processedLine = line.trim();
            if (!processedLine) continue;

            // Bold and Italic
            processedLine = processedLine
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');

            // Unordered list
            if (processedLine.startsWith('- ') || processedLine.startsWith('* ')) {
                if (inOl) { htmlLines.push('</ol>'); inOl = false; }
                if (!inUl) { htmlLines.push('<ul>'); inUl = true; }
                htmlLines.push(`<li>${processedLine.substring(2)}</li>`);
            } 
            // Ordered list
            else if (processedLine.match(/^\d+\.\s/)) {
                if (inUl) { htmlLines.push('</ul>'); inUl = false; }
                if (inOl) { htmlLines.push('<ol>'); inOl = true; }
                htmlLines.push(`<li>${processedLine.replace(/^\d+\.\s/, '')}</li>`);
            } 
            // Paragraph
            else {
                if (inUl) { htmlLines.push('</ul>'); inUl = false; }
                if (inOl) { htmlLines.push('</ol>'); inOl = false; }
                htmlLines.push(`<p>${processedLine}</p>`);
            }
        }

        if (inUl) htmlLines.push('</ul>');
        if (inOl) htmlLines.push('</ol>');

        return htmlLines.join('');
    }

    showResults() {
        document.getElementById('resultsSection').style.display = 'block';
    }

    showLoading(show) {
        const button = document.getElementById('summarizeBtn');
        const text = document.getElementById('summarizeText');
        const spinner = document.getElementById('loadingSpinner');
        
        if (show) {
            text.style.display = 'none';
            spinner.style.display = 'block';
            button.disabled = true;
        } else {
            text.style.display = 'block';
            spinner.style.display = 'none';
            button.disabled = false;
        }
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorSection').style.display = 'block';
    }

    hideError() {
        document.getElementById('errorSection').style.display = 'none';
    }

    showSuccess(message) {
        // Simple success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-md text-sm z-50';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }

    initializeCollapsibles() {
        document.querySelectorAll('.collapsible-header').forEach(header => {
            header.addEventListener('click', () => {
                const content = header.nextElementSibling;
                const arrow = header.querySelector('span:last-child');
                
                if (content.classList.contains('open')) {
                    content.classList.remove('open');
                    arrow.textContent = '▼';
                } else {
                    content.classList.add('open');
                    arrow.textContent = '▲';
                }
            });
        });
    }

    async copyResults() {
        const resultsText = this.formatResultsForCopy();
        
        try {
            await navigator.clipboard.writeText(resultsText);
            this.showSuccess('Results copied to clipboard!');
        } catch (error) {
            this.showError('Failed to copy results');
        }
    }

    async exportMarkdown() {
        const markdown = this.formatResultsAsMarkdown();
        const blob = new Blob([markdown], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-analysis-${new Date().toISOString().split('T')[0]}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showSuccess('Markdown file exported!');
    }

    async exportPdf() {
        // Simple PDF export using browser's print functionality
        const printWindow = window.open('', '_blank');
        const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Research Analysis</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #2563eb; }
                    h2 { color: #1e40af; margin-top: 30px; }
                    .step { margin-bottom: 20px; }
                    @media print { body { margin: 0; } }
                </style>
            </head>
            <body>
                <h1>Research Analysis Report</h1>
                <p><strong>Focus Mode:</strong> ${this.focusMode.toUpperCase()}</p>
                <p><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
                
                <div class="step">
                    <h2>Step 1: Research Problem</h2>
                    <p>${this.markdownToHtml(this.results.step1) || 'No content available'}</p>
                </div>
                
                <div class="step">
                    <h2>Step 2: Research Design</h2>
                    <p>${this.markdownToHtml(this.results.step2) || 'No content available'}</p>
                </div>
                
                <div class="step">
                    <h2>Step 3: Data Collection</h2>
                    <p>${this.markdownToHtml(this.results.step3) || 'No content available'}</p>
                </div>
                
                <div class="step">
                    <h2>Step 4: Sampling Strategies</h2>
                    <p>${this.markdownToHtml(this.results.step4) || 'No content available'}</p>
                </div>
                
                <div class="step">
                    <h2>Step 5: Research Proposal</h2>
                    <p>${this.markdownToHtml(this.results.step5) || 'No content available'}</p>
                </div>
            </body>
            </html>
        `;
        
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        printWindow.print();
        
        this.showSuccess('PDF export initiated!');
    }

    formatResultsForCopy() {
        return `Research Analysis Report
Focus Mode: ${this.focusMode.toUpperCase()}
Generated: ${new Date().toLocaleString()}

Step 1: Research Problem
${this.results.step1 || 'No content available'}

Step 2: Research Design
${this.results.step2 || 'No content available'}

Step 3: Data Collection
${this.results.step3 || 'No content available'}

Step 4: Sampling Strategies
${this.results.step4 || 'No content available'}

Step 5: Research Proposal
${this.results.step5 || 'No content available'}`;
    }

    formatResultsAsMarkdown() {
        return `# Research Analysis Report

**Focus Mode:** ${this.focusMode.toUpperCase()}  
**Generated:** ${new Date().toLocaleString()}

## Step 1: Research Problem

${this.results.step1 || 'No content available'}

## Step 2: Research Design

${this.results.step2 || 'No content available'}

## Step 3: Data Collection

${this.results.step3 || 'No content available'}

## Step 4: Sampling Strategies

${this.results.step4 || 'No content available'}

## Step 5: Research Proposal

${this.results.step5 || 'No content available'}
`;
    }
}

// Content extraction function for injection
function extractPageContent() {
    try {
        // Check if this is a PDF page
        if (window.location.href.includes('.pdf') || 
            document.querySelector('embed[type="application/pdf"]') ||
            document.querySelector('object[type="application/pdf"]')) {
            return 'PDF_PAGE_DETECTED';
        }
        
        // Remove script and style elements
        const scripts = document.querySelectorAll('script, style, nav, header, footer, aside');
        scripts.forEach(el => el.remove());
        
        // Get main content areas with priority order
        const contentSelectors = [
            'main', 'article', '.content', '#content', '.post', '.entry',
            '.article', '.main-content', '[role="main"]', '.paper-content',
            '.abstract', '.document', '.text-content', '.body-content'
        ];
        
        let content = '';
        let bestMatch = '';
        
        for (const selector of contentSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                const text = element.innerText || element.textContent;
                if (text && text.length > content.length) {
                    content = text;
                    bestMatch = selector;
                }
            }
        }
        
        // Fallback to body if no main content found
        if (!content || content.length < 100) {
            content = document.body.innerText || document.body.textContent;
            bestMatch = 'body';
        }
        
        // Clean up the text
        const cleanedContent = content
            .replace(/\s+/g, ' ')
            .replace(/\n\s*\n/g, '\n')
            .trim();
        
        // Return metadata along with content
        return {
            content: cleanedContent,
            source: bestMatch,
            url: window.location.href,
            title: document.title,
            wordCount: cleanedContent.split(' ').length
        };
        
    } catch (error) {
        return {
            error: error.message,
            content: '',
            source: 'error',
            url: window.location.href,
            title: document.title
        };
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new SmartSummarizer();
});

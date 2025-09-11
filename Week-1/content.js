// Smart Paper & Doc Summarizer - Content Script
class ContentExtractor {
    constructor() {
        this.isInitialized = false;
        this.extractedContent = null;
        this.initialize();
    }

    initialize() {
        if (this.isInitialized) return;
        
        this.setupMessageListener();
        this.detectPageType();
        this.isInitialized = true;
    }

    setupMessageListener() {
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // Keep message channel open for async responses
        });
    }

    async handleMessage(request, sender, sendResponse) {
        try {
            switch (request.action) {
                case 'extractContent':
                    const content = await this.extractContent();
                    sendResponse({ success: true, content });
                    break;

                case 'getPageInfo':
                    const pageInfo = this.getPageInfo();
                    sendResponse({ success: true, pageInfo });
                    break;

                case 'highlightText':
                    this.highlightText(request.text);
                    sendResponse({ success: true });
                    break;

                case 'removeHighlights':
                    this.removeHighlights();
                    sendResponse({ success: true });
                    break;

                default:
                    sendResponse({ success: false, error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Error handling message:', error);
            sendResponse({ success: false, error: error.message });
        }
    }

    detectPageType() {
        const url = window.location.href;
        const hostname = window.location.hostname;
        
        this.pageType = {
            isPdf: url.includes('.pdf') || hostname.includes('pdf'),
            isAcademic: this.isAcademicSite(hostname),
            isResearch: this.isResearchSite(hostname),
            isLegal: this.isLegalSite(hostname),
            isNews: this.isNewsSite(hostname)
        };
    }

    isAcademicSite(hostname) {
        const academicDomains = [
            'arxiv.org', 'scholar.google.com', 'ieee.org', 'acm.org',
            'springer.com', 'nature.com', 'science.org', 'cell.com',
            'jstor.org', 'pubmed.ncbi.nlm.nih.gov', 'researchgate.net',
            'semanticscholar.org', 'dblp.org', 'academia.edu'
        ];
        
        return academicDomains.some(domain => hostname.includes(domain));
    }

    isResearchSite(hostname) {
        const researchKeywords = ['research', 'study', 'paper', 'journal', 'conference'];
        return researchKeywords.some(keyword => hostname.includes(keyword));
    }

    isLegalSite(hostname) {
        const legalDomains = [
            'law.cornell.edu', 'justia.com', 'findlaw.com', 'lexisnexis.com',
            'westlaw.com', 'courtlistener.com', 'scholar.google.com'
        ];
        
        return legalDomains.some(domain => hostname.includes(domain));
    }

    isNewsSite(hostname) {
        const newsDomains = [
            'bbc.com', 'cnn.com', 'reuters.com', 'ap.org', 'npr.org',
            'nytimes.com', 'washingtonpost.com', 'theguardian.com'
        ];
        
        return newsDomains.some(domain => hostname.includes(domain));
    }

    async extractContent() {
        if (this.extractedContent) {
            return this.extractedContent;
        }

        try {
            if (this.pageType.isPdf) {
                this.extractedContent = await this.extractPdfContent();
            } else {
                this.extractedContent = await this.extractWebContent();
            }

            return this.extractedContent;
        } catch (error) {
            console.error('Error extracting content:', error);
            throw error;
        }
    }

    async extractPdfContent() {
        // For PDFs, we'll extract text from the page
        // This is a simplified version - in production, you'd use PDF.js
        const textElements = document.querySelectorAll('div, p, span');
        let content = '';

        textElements.forEach(element => {
            const text = element.innerText || element.textContent;
            if (text && text.trim().length > 10) {
                content += text + '\n';
            }
        });

        return {
            type: 'pdf',
            content: this.cleanText(content),
            metadata: this.getPageMetadata()
        };
    }

    async extractWebContent() {
        // Remove unwanted elements
        this.removeUnwantedElements();

        // Extract main content
        const mainContent = this.extractMainContent();
        
        // Extract metadata
        const metadata = this.getPageMetadata();

        // Extract structured data
        const structuredData = this.extractStructuredData();

        return {
            type: 'web',
            content: mainContent,
            metadata,
            structuredData,
            pageType: this.pageType
        };
    }

    removeUnwantedElements() {
        const unwantedSelectors = [
            'script', 'style', 'nav', 'header', 'footer', 'aside',
            '.advertisement', '.ads', '.sidebar', '.menu', '.navigation',
            '.social-share', '.comments', '.related-posts', '.tags',
            '.breadcrumb', '.pagination', '.cookie-notice', '.popup'
        ];

        unwantedSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => el.remove());
        });
    }

    extractMainContent() {
        // Priority order for content extraction
        const contentSelectors = [
            'main', 'article', '.content', '#content', '.post', '.entry',
            '.article', '.main-content', '[role="main"]', '.paper-content',
            '.abstract', '.document', '.text-content', '.body-content'
        ];

        let bestContent = '';
        let bestSelector = '';

        for (const selector of contentSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                const text = this.getElementText(element);
                if (text.length > bestContent.length) {
                    bestContent = text;
                    bestSelector = selector;
                }
            }
        }

        // Fallback to body if no main content found
        if (!bestContent || bestContent.length < 100) {
            bestContent = this.getElementText(document.body);
            bestSelector = 'body';
        }

        return {
            text: this.cleanText(bestContent),
            selector: bestSelector,
            wordCount: bestContent.split(' ').length
        };
    }

    getElementText(element) {
        // Clone the element to avoid modifying the original
        const clone = element.cloneNode(true);
        
        // Remove unwanted child elements
        const unwanted = clone.querySelectorAll('script, style, nav, .ad, .advertisement');
        unwanted.forEach(el => el.remove());
        
        return clone.innerText || clone.textContent || '';
    }

    cleanText(text) {
        return text
            .replace(/\s+/g, ' ')
            .replace(/\n\s*\n/g, '\n')
            .replace(/[^\w\s.,!?;:()\-]/g, '')
            .trim();
    }

    getPageMetadata() {
        const metadata = {
            title: document.title,
            url: window.location.href,
            domain: window.location.hostname,
            timestamp: new Date().toISOString(),
            language: document.documentElement.lang || 'en'
        };

        // Extract meta tags
        const metaTags = document.querySelectorAll('meta');
        metaTags.forEach(meta => {
            const name = meta.getAttribute('name') || meta.getAttribute('property');
            const content = meta.getAttribute('content');
            
            if (name && content) {
                switch (name) {
                    case 'description':
                        metadata.description = content;
                        break;
                    case 'keywords':
                        metadata.keywords = content;
                        break;
                    case 'author':
                        metadata.author = content;
                        break;
                    case 'og:title':
                        metadata.ogTitle = content;
                        break;
                    case 'og:description':
                        metadata.ogDescription = content;
                        break;
                }
            }
        });

        return metadata;
    }

    extractStructuredData() {
        const structuredData = {
            headings: [],
            links: [],
            images: [],
            tables: []
        };

        // Extract headings
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        headings.forEach(heading => {
            structuredData.headings.push({
                level: parseInt(heading.tagName.charAt(1)),
                text: heading.innerText.trim(),
                id: heading.id
            });
        });

        // Extract important links
        const links = document.querySelectorAll('a[href]');
        links.forEach(link => {
            const href = link.getAttribute('href');
            const text = link.innerText.trim();
            
            if (text && href && !href.startsWith('#')) {
                structuredData.links.push({
                    text,
                    href: href.startsWith('http') ? href : new URL(href, window.location.href).href
                });
            }
        });

        // Extract images with alt text
        const images = document.querySelectorAll('img[alt]');
        images.forEach(img => {
            structuredData.images.push({
                alt: img.getAttribute('alt'),
                src: img.src
            });
        });

        // Extract tables
        const tables = document.querySelectorAll('table');
        tables.forEach((table, index) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            const tableData = rows.map(row => {
                const cells = Array.from(row.querySelectorAll('td, th'));
                return cells.map(cell => cell.innerText.trim());
            });
            
            structuredData.tables.push({
                index,
                data: tableData
            });
        });

        return structuredData;
    }

    getPageInfo() {
        return {
            url: window.location.href,
            title: document.title,
            domain: window.location.hostname,
            pageType: this.pageType,
            wordCount: document.body.innerText.split(' ').length,
            hasContent: document.body.innerText.length > 100
        };
    }

    highlightText(text) {
        this.removeHighlights();
        
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        const textNodes = [];
        let node;
        
        while (node = walker.nextNode()) {
            if (node.textContent.includes(text)) {
                textNodes.push(node);
            }
        }

        textNodes.forEach(textNode => {
            const parent = textNode.parentNode;
            const content = textNode.textContent;
            const highlightedContent = content.replace(
                new RegExp(text, 'gi'),
                `<mark class="smart-summarizer-highlight">$&</mark>`
            );
            
            if (highlightedContent !== content) {
                parent.innerHTML = parent.innerHTML.replace(content, highlightedContent);
            }
        });
    }

    removeHighlights() {
        const highlights = document.querySelectorAll('.smart-summarizer-highlight');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });
    }
}

// Initialize content extractor when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new ContentExtractor();
    });
} else {
    new ContentExtractor();
}

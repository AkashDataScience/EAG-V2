// Background service worker for Multi-Agent Task Orchestrator

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
    console.log('Mindflow installed');
    
    // Set default settings if not already set
    chrome.storage.local.get(['initialized'], (result) => {
        if (!result.initialized) {
            chrome.storage.local.set({
                initialized: true,
                agents: [],
                executionMode: 'sequential',
                apiKey: ''
            });
        }
    });
});

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('Mindflow started');
});

// Handle messages from popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
        case 'getStorageData':
            chrome.storage.local.get(request.keys, (result) => {
                sendResponse(result);
            });
            return true; // Keep message channel open for async response
            
        case 'setStorageData':
            chrome.storage.local.set(request.data, () => {
                sendResponse({ success: true });
            });
            return true;
            
        case 'clearStorage':
            chrome.storage.local.clear(() => {
                sendResponse({ success: true });
            });
            return true;
            
        case 'scrapeCurrentPage':
            handlePageScraping(request.tabId, sendResponse);
            return true;
            
        default:
            sendResponse({ error: 'Unknown action' });
    }
});

// Handle page scraping for agents that need current page content
async function handlePageScraping(tabId, sendResponse) {
    try {
        const results = await chrome.scripting.executeScript({
            target: { tabId: tabId },
            function: extractPageContent
        });
        
        sendResponse({ 
            success: true, 
            content: results[0].result 
        });
    } catch (error) {
        sendResponse({ 
            success: false, 
            error: error.message 
        });
    }
}

// Function to be injected into the page for content extraction
function extractPageContent() {
    // Remove script and style elements
    const scripts = document.querySelectorAll('script, style');
    scripts.forEach(el => el.remove());
    
    // Get main content
    const content = {
        title: document.title,
        url: window.location.href,
        text: document.body.innerText.trim(),
        headings: Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.textContent.trim()),
        links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
            text: a.textContent.trim(),
            href: a.href
        })).filter(link => link.text && link.href)
    };
    
    return content;
}

// Handle storage changes for debugging
chrome.storage.onChanged.addListener((changes, namespace) => {
    console.log('Storage changed:', changes, 'in', namespace);
});

// Cleanup on extension suspend
chrome.runtime.onSuspend.addListener(() => {
    console.log('Mindflow suspended');
});
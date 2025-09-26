// Background service worker for Stock News + Price Correlator

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
    console.log('Stock News + Price Correlator installed');
    
    // Set default settings if not already set
    chrome.storage.local.get(['initialized'], (result) => {
        if (!result.initialized) {
            chrome.storage.local.set({
                initialized: true,
                savedAnalyses: [],
                backendUrl: 'http://localhost:5000'
            });
        }
    });
});

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('Stock News + Price Correlator started');
});

// Handle messages from popup
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
            
        default:
            sendResponse({ error: 'Unknown action' });
    }
});

// Handle storage changes for debugging
chrome.storage.onChanged.addListener((changes, namespace) => {
    console.log('Storage changed:', changes, 'in', namespace);
});

// Cleanup on extension suspend
chrome.runtime.onSuspend.addListener(() => {
    console.log('Stock News + Price Correlator suspended');
});
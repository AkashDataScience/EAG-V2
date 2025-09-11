// Smart Paper & Doc Summarizer - Background Script (Service Worker)

// Handle extension installation
if (chrome.runtime && chrome.runtime.onInstalled) {
    chrome.runtime.onInstalled.addListener((details) => {
        handleInstallation(details);
    });
}

// Handle messages from popup and content scripts
if (chrome.runtime && chrome.runtime.onMessage) {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        handleMessage(request, sender, sendResponse);
        return true; // Keep message channel open for async responses
    });
}

// Handle tab updates for content extraction
if (chrome.tabs && chrome.tabs.onUpdated) {
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
        handleTabUpdate(tabId, changeInfo, tab);
    });
}

// Setup context menus
setupContextMenus();

function handleInstallation(details) {
    if (details.reason === 'install') {
        console.log('Smart Paper & Doc Summarizer installed');
        
        // Set default settings
        chrome.storage.sync.set({
            apiKey: '',
            focusMode: 'technical',
            autoExtract: true,
            theme: 'light'
        });

        // Show welcome notification
        showWelcomeNotification();
    } else if (details.reason === 'update') {
        console.log('Smart Paper & Doc Summarizer updated');
    }
}

async function handleMessage(request, sender, sendResponse) {
    try {
        switch (request.action) {
            case 'extractContent':
                const content = await extractPageContent(request.tabId);
                sendResponse({ success: true, content });
                break;

            case 'saveApiKey':
                await saveApiKey(request.apiKey);
                sendResponse({ success: true });
                break;

            case 'getApiKey':
                const apiKey = await getApiKey();
                sendResponse({ success: true, apiKey });
                break;

            case 'validateApiKey':
                const isValid = await validateApiKey(request.apiKey);
                sendResponse({ success: true, isValid });
                break;

            case 'getSettings':
                const settings = await getSettings();
                sendResponse({ success: true, settings });
                break;

            case 'updateSettings':
                await updateSettings(request.settings);
                sendResponse({ success: true });
                break;

            case 'logUsage':
                await logUsage(request.data);
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

async function extractPageContent(tabId) {
    try {
        // Check if scripting API is available
        if (!chrome.scripting) {
            throw new Error('Scripting API not available');
        }

        const results = await chrome.scripting.executeScript({
            target: { tabId },
            function: extractPageContentFunction
        });

        if (results && results[0] && results[0].result) {
            return results[0].result;
        }
        throw new Error('Failed to extract content');
    } catch (error) {
        console.error('Error extracting page content:', error);
        throw error;
    }
}

async function saveApiKey(apiKey) {
    try {
        // Check if storage API is available
        if (!chrome.storage) {
            throw new Error('Storage API not available');
        }

        await chrome.storage.sync.set({ apiKey });
        
        // Log usage
        await logUsage({
            action: 'api_key_saved',
            timestamp: Date.now()
        });
    } catch (error) {
        console.error('Error saving API key:', error);
        throw error;
    }
}

async function getApiKey() {
    try {
        // Check if storage API is available
        if (!chrome.storage) {
            console.error('Storage API not available');
            return '';
        }

        const result = await chrome.storage.sync.get(['apiKey']);
        return result.apiKey || '';
    } catch (error) {
        console.error('Error getting API key:', error);
        return '';
    }
}

async function validateApiKey(apiKey) {
    if (!apiKey || !apiKey.startsWith('AIza')) {
        return false;
    }

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
        return response.ok;
    } catch (error) {
        console.error('Error validating API key:', error);
        return false;
    }
}

async function getSettings() {
    try {
        const result = await chrome.storage.sync.get([
            'focusMode',
            'autoExtract',
            'theme',
            'defaultModel',
            'maxTokens'
        ]);

        return {
            focusMode: result.focusMode || 'technical',
            autoExtract: result.autoExtract !== false,
            theme: result.theme || 'light',
            defaultModel: result.defaultModel || 'gemini-1.5-flash',
            maxTokens: result.maxTokens || 4000
        };
    } catch (error) {
        console.error('Error getting settings:', error);
        return {};
    }
}

async function updateSettings(settings) {
    try {
        await chrome.storage.sync.set(settings);
        
        // Log usage
        await logUsage({
            action: 'settings_updated',
            settings: Object.keys(settings),
            timestamp: Date.now()
        });
    } catch (error) {
        console.error('Error updating settings:', error);
        throw error;
    }
}

async function logUsage(data) {
    try {
        const result = await chrome.storage.local.get(['usageLog']);
        const usageLog = result.usageLog || [];
        
        usageLog.push({
            ...data,
            timestamp: Date.now()
        });

        // Keep only last 100 entries
        if (usageLog.length > 100) {
            usageLog.splice(0, usageLog.length - 100);
        }

        await chrome.storage.local.set({ usageLog });
    } catch (error) {
        console.error('Error logging usage:', error);
    }
}

function setupContextMenus() {
    // Check if contextMenus API is available
    if (!chrome.contextMenus) {
        console.log('Context menus API not available');
        return;
    }

    try {
        // Create context menu for text selection
        chrome.contextMenus.create({
            id: 'summarizeSelectedText',
            title: 'Summarize with Smart Summarizer',
            contexts: ['selection']
        });

        // Handle context menu clicks
        chrome.contextMenus.onClicked.addListener((info, tab) => {
            if (info.menuItemId === 'summarizeSelectedText') {
                handleContextMenuClick(info, tab);
            }
        });
    } catch (error) {
        console.error('Error setting up context menus:', error);
    }
}

async function handleContextMenuClick(info, tab) {
    try {
        // Check if runtime API is available
        if (!chrome.runtime) {
            console.error('Runtime API not available');
            return;
        }

        // Send selected text to popup
        chrome.runtime.sendMessage({
            action: 'selectedText',
            text: info.selectionText,
            tabId: tab.id
        });
    } catch (error) {
        console.error('Error handling context menu click:', error);
    }
}

function handleTabUpdate(tabId, changeInfo, tab) {
    // Check if tabs API is available
    if (!chrome.tabs) {
        console.log('Tabs API not available');
        return;
    }

    // Auto-extract content when page is fully loaded
    if (changeInfo.status === 'complete' && tab.url) {
        handlePageLoad(tabId, tab);
    }
}

async function handlePageLoad(tabId, tab) {
    try {
        const settings = await getSettings();
        
        if (settings.autoExtract && isExtractablePage(tab.url)) {
            // Pre-extract content for faster processing
            setTimeout(async () => {
                try {
                    const content = await extractPageContent(tabId);
                    await chrome.storage.local.set({
                        [`extracted_${tabId}`]: {
                            content,
                            timestamp: Date.now(),
                            url: tab.url
                        }
                    });
                } catch (error) {
                    console.error('Error pre-extracting content:', error);
                }
            }, 2000); // Wait 2 seconds for page to fully load
        }
    } catch (error) {
        console.error('Error handling page load:', error);
    }
}

function isExtractablePage(url) {
    try {
        const urlObj = new URL(url);
        const extractableDomains = [
            'arxiv.org',
            'scholar.google.com',
            'ieee.org',
            'acm.org',
            'springer.com',
            'nature.com',
            'science.org'
        ];

        return extractableDomains.some(domain => 
            urlObj.hostname.includes(domain)
        ) || urlObj.pathname.includes('.pdf');
    } catch (error) {
        return false;
    }
}

function showWelcomeNotification() {
    // Welcome notification disabled to avoid API issues
    // Users will see the extension icon in the toolbar instead
    console.log('Smart Paper & Doc Summarizer installed successfully!');
}

// Content extraction function for injection
function extractPageContentFunction() {
    // Remove script and style elements
    const scripts = document.querySelectorAll('script, style, nav, header, footer, aside');
    scripts.forEach(el => el.remove());
    
    // Get main content areas with priority order
    const contentSelectors = [
        'main', 'article', '.content', '#content', '.post', '.entry',
        '.article', '.main-content', '[role="main"]', '.paper-content',
        '.abstract', '.document', '.text-content'
    ];
    
    let content = '';
    let bestMatch = null;
    
    for (const selector of contentSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            const text = element.innerText || element.textContent;
            if (text.length > content.length) {
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
    
    return {
        content: cleanedContent,
        source: bestMatch,
        url: window.location.href,
        title: document.title,
        wordCount: cleanedContent.split(' ').length
    };
}

// Nexus - AI-powered Video Knowledge Hub

class NexusAgent {
    constructor() {
        this.backendUrl = 'http://localhost:5000';
        this.currentTab = null;
        this.statusCheckInterval = null;
        this.videosLoaded = false;
        
        this.initializeEventListeners();
        this.loadSavedSettings();
        this.checkCurrentTab();
    }

    initializeEventListeners() {
        // Main search button
        document.getElementById('searchButton').addEventListener('click', () => this.runQuery());
        
        // Index button
        document.getElementById('indexButton').addEventListener('click', () => this.indexCurrentVideo());
        
        // Retry button
        document.getElementById('retryBtn').addEventListener('click', () => this.runQuery());
        
        // Toggle index section
        document.getElementById('toggleIndexSection').addEventListener('click', () => this.toggleIndexSection());
        
        // Create collection button
        document.getElementById('createCollectionBtn').addEventListener('click', () => this.showCreateCollectionDialog());
        
        // View stats button
        document.getElementById('viewStatsBtn').addEventListener('click', () => this.showCategorizationStats());
        
        // Example query buttons
        document.querySelectorAll('.example-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                document.getElementById('searchQuery').value = query;
            });
        });
        
        // Enter key support for search query
        document.getElementById('searchQuery').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.runQuery();
            }
        });
    }

    async loadSavedSettings() {
        try {
            const result = await chrome.storage.local.get(['lastQuery']);
            if (result.lastQuery) {
                document.getElementById('searchQuery').value = result.lastQuery;
            }
        } catch (error) {
            console.error('Error loading saved settings:', error);
        }
    }

    async saveSettings(query) {
        try {
            await chrome.storage.local.set({ lastQuery: query });
        } catch (error) {
            console.error('Error saving settings:', error);
        }
    }

    checkCurrentTab() {
        console.log('[Nexus] Checking current tab');
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            if (!tabs || !tabs[0]) {
                console.error('[Nexus] No active tab found');
                this.showIndexStatus('Error: Cannot access current tab', 'error');
                return;
            }

            console.log('[Nexus] Active tab:', tabs[0].url);
            
            this.currentTab = tabs[0];
            const url = this.currentTab.url;
            if (url && url.includes('youtube.com/watch')) {
                console.log('[Nexus] Valid video detected, enabling button');
                // Check for ongoing operations
                chrome.storage.local.get(['ongoingOperation'], (result) => {
                    if (!result.ongoingOperation) {
                        document.getElementById('indexButton').disabled = false;
                        this.showIndexStatus('Ready to index this video ✨', 'success');
                    } else {
                        // Resume ongoing operation
                        console.log('[Nexus] Found ongoing operation:', result.ongoingOperation);
                        document.getElementById('indexButton').disabled = true;
                        this.showIndexStatus('Indexing in progress...', 'pending');
                        this.startStatusPolling(result.ongoingOperation.id);
                    }
                });
            } else {
                console.log('[Nexus] Not a valid video page');
                this.showIndexStatus('Please navigate to a YouTube video', 'error');
            }
        });
    }

    async runQuery() {
        const query = document.getElementById('searchQuery').value.trim();
        if (!query) {
            this.showError('Please enter a query to search.');
            return;
        }

        // Reset state for new query
        this.hideAllSections();
        await this.saveSettings(query);

        this.showStatus('🔍 Searching indexed videos...', 10);

        try {
            const response = await fetch(`${this.backendUrl}/query`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Search failed: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.status === 'success') {
                await this.displayResults(data);
                this.hideStatus();
            } else {
                throw new Error(data.error || 'Search failed');
            }

        } catch (error) {
            console.error('Search failed:', error);
            this.showError(error.message || 'Could not complete the search.');
        }
    }

    async indexCurrentVideo() {
        const url = this.currentTab.url;
        if (!url) return;
        
        try {
            document.getElementById('indexButton').disabled = true;
            this.showIndexStatus('Starting indexing operation...', 'pending');
            
            const response = await fetch(`${this.backendUrl}/index_video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Save operation ID to Chrome storage
                const operation = {
                    id: data.operation_id,
                    startTime: Date.now(),
                    videoUrl: url
                };
                
                chrome.storage.local.set({ ongoingOperation: operation });
                
                // Start polling for status updates
                this.startStatusPolling(data.operation_id);
            } else {
                throw new Error(data.error || "Failed to index video");
            }
        } catch (error) {
            this.showIndexStatus(`Error: ${error.message}`, 'error');
            document.getElementById('indexButton').disabled = false;
        }
    }

    startStatusPolling(operationId) {
        this.statusCheckInterval = setInterval(async () => {
            try {
                const response = await fetch(`${this.backendUrl}/indexing_status/${operationId}`);
                if (!response.ok) return;

                const status = await response.json();
                this.updateIndexStatus(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(this.statusCheckInterval);
                    chrome.storage.local.remove('ongoingOperation');
                    
                    setTimeout(() => {
                        document.getElementById('indexButton').disabled = false;
                    }, 2000);
                    
                    if (status.status === 'completed' && this.videosLoaded) {
                        setTimeout(() => this.fetchIndexedVideos(), 1000);
                    }
                }
            } catch (error) {
                console.error('Error checking indexing status:', error);
            }
        }, 2000);
    }

    updateIndexStatus(status) {
        const statusColors = {
            pending: 'pending',
            fetching_metadata: 'pending',
            fetching_transcript: 'pending', 
            indexing: 'pending',
            completed: 'success',
            failed: 'error'
        };

        let statusText = status.message;
        if (status.status === 'indexing') {
            statusText += ` (${status.elapsed_seconds}s elapsed)`;
        }
        
        this.showIndexStatus(statusText, statusColors[status.status] || 'pending');
    }

    async displayResults(data) {
        try {
            // Show results section
            const resultsSection = document.getElementById('resultsSection');
            resultsSection.classList.remove('hidden');

            // Display AI response
            const aiResponse = document.getElementById('aiResponse');
            if (data.answer) {
                aiResponse.innerHTML = `
                    <h4>🤖 AI Analysis:</h4>
                    <div class="response-content">${this.formatMarkdown(data.answer)}</div>
                `;
            }

            // Display sources
            if (data.sources && data.sources.length > 0) {
                const sourcesSection = document.getElementById('sourcesSection');
                const sourcesList = document.getElementById('sourcesList');
                
                sourcesSection.style.display = 'block';
                sourcesList.innerHTML = '';
                
                data.sources.forEach(source => {
                    const sourceDiv = document.createElement('div');
                    sourceDiv.className = 'source-item';
                    
                    const timestamp = Math.floor(source.timestamp);
                    const videoUrl = `${source.url}&t=${timestamp}s`;
                    
                    sourceDiv.innerHTML = `
                        <div class="source-text">${source.text}</div>
                        <div class="source-link">
                            <a href="${videoUrl}" target="_blank">
                                ${source.video_title} (${this.formatTime(timestamp)})
                            </a>
                        </div>
                    `;
                    
                    sourcesList.appendChild(sourceDiv);
                });
            } else {
                document.getElementById('sourcesSection').style.display = 'none';
            }

        } catch (error) {
            console.error('Error displaying results:', error);
            this.showError('Failed to display search results: ' + error.message);
        }
    }

    formatMarkdown(text) {
        if (!text) return '';
        
        // Simple markdown to HTML conversion
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^[\s]*[-*]\s+(.+)$/gm, '<li>$1</li>')
            .replace(/^[\s]*\d+\.\s+(.+)$/gm, '<li>$1</li>')
            .replace(/\n/g, '<br>')
            .replace(/^###\s+(.+)$/gm, '<h4>$1</h4>')
            .replace(/^##\s+(.+)$/gm, '<h3>$1</h3>')
            .replace(/(<li>.*?<\/li>)(?:\s*<br>\s*<li>.*?<\/li>)*/g, function(match) {
                return '<ul>' + match.replace(/<br>/g, '') + '</ul>';
            });
    }

    toggleIndexSection() {
        const section = document.getElementById('indexSection');
        const icon = document.getElementById('indexToggleIcon');
        
        if (section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            icon.style.transform = 'rotate(180deg)';
            
            // Load videos and collections if not loaded yet
            if (!this.videosLoaded) {
                this.fetchIndexedVideos();
                this.fetchCollections();
            }
        } else {
            section.classList.add('hidden');
            icon.style.transform = 'rotate(0deg)';
        }
    }

    async fetchIndexedVideos() {
        try {
            const videoList = document.getElementById('videoList');
            videoList.innerHTML = '<div class="loading-indicator">Loading videos...</div>';
            
            const response = await fetch(`${this.backendUrl}/list_indexed_videos`);
            if (!response.ok) {
                throw new Error('Failed to fetch indexed videos');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.videos && data.videos.length > 0) {
                    this.renderVideoList(data.videos);
                } else {
                    videoList.innerHTML = '<div class="no-videos">No videos have been indexed yet.</div>';
                }
                this.videosLoaded = true;
            } else {
                throw new Error(data.error || "Failed to load videos");
            }
        } catch (error) {
            console.error('Error fetching indexed videos:', error);
            document.getElementById('videoList').innerHTML = 
                `<div class="error-message">Error: ${error.message}</div>`;
        }
    }

    renderVideoList(videos) {
        const videoList = document.getElementById('videoList');
        
        const table = document.createElement('table');
        table.className = 'video-table';
        
        // Table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['#', 'Title', 'Channel', 'Duration'].forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        videos.forEach((video, index) => {
            const row = document.createElement('tr');
            
            // Number
            const numCell = document.createElement('td');
            numCell.textContent = index + 1;
            row.appendChild(numCell);
            
            // Title (clickable)
            const titleCell = document.createElement('td');
            const titleSpan = document.createElement('span');
            titleSpan.className = 'video-title-table-link';
            titleSpan.textContent = video.title;
            titleSpan.onclick = () => window.open(video.url, '_blank');
            titleCell.appendChild(titleSpan);
            row.appendChild(titleCell);
            
            // Channel
            const channelCell = document.createElement('td');
            channelCell.textContent = video.author;
            row.appendChild(channelCell);
            
            // Duration
            const durationCell = document.createElement('td');
            durationCell.textContent = this.formatTime(video.length);
            row.appendChild(durationCell);
            
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        
        videoList.innerHTML = '';
        videoList.appendChild(table);
    }

    async fetchCollections() {
        try {
            const collectionsList = document.getElementById('collectionsList');
            collectionsList.innerHTML = '<div class="loading-indicator">Loading collections...</div>';
            
            const response = await fetch(`${this.backendUrl}/collections`);
            if (!response.ok) {
                throw new Error('Failed to fetch collections');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                if (data.collections && data.collections.length > 0) {
                    this.renderCollectionsList(data.collections);
                } else {
                    collectionsList.innerHTML = '<div class="no-videos">No collections created yet.</div>';
                }
            } else {
                throw new Error(data.error || "Failed to load collections");
            }
        } catch (error) {
            console.error('Error fetching collections:', error);
            document.getElementById('collectionsList').innerHTML = 
                `<div class="error-message">Error: ${error.message}</div>`;
        }
    }

    renderCollectionsList(collections) {
        const collectionsList = document.getElementById('collectionsList');
        collectionsList.innerHTML = '';
        
        collections.forEach(collection => {
            const collectionDiv = document.createElement('div');
            collectionDiv.className = 'collection-item';
            collectionDiv.onclick = () => this.viewCollection(collection.id);
            
            collectionDiv.innerHTML = `
                <div class="collection-color" style="background-color: ${collection.color}"></div>
                <div class="collection-info">
                    <div class="collection-name">${collection.name}</div>
                    <div class="collection-meta">${collection.video_count} videos</div>
                </div>
                ${collection.is_auto ? '<span class="collection-badge auto">Auto</span>' : '<span class="collection-badge">Manual</span>'}
            `;
            
            collectionsList.appendChild(collectionDiv);
        });
    }

    async viewCollection(collectionId) {
        try {
            const response = await fetch(`${this.backendUrl}/collections/${collectionId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch collection details');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showCollectionDetails(data.summary);
            } else {
                throw new Error(data.error || "Failed to load collection details");
            }
        } catch (error) {
            console.error('Error viewing collection:', error);
            this.showError(`Error viewing collection: ${error.message}`);
        }
    }

    showCollectionDetails(summary) {
        // For now, just show an alert with collection info
        // In a full implementation, this would open a detailed view
        const collection = summary.collection;
        const message = `Collection: ${collection.name}\n` +
                       `Description: ${collection.description}\n` +
                       `Videos: ${collection.video_count}\n` +
                       `Duration: ${Math.floor(summary.total_duration / 60)} minutes\n` +
                       `Topics: ${summary.topics.join(', ')}`;
        
        alert(message);
    }

    showCreateCollectionDialog() {
        const name = prompt('Enter collection name:');
        if (!name) return;
        
        const description = prompt('Enter collection description (optional):') || '';
        
        this.createCollection(name, description);
    }

    async createCollection(name, description = '', color = '#6366f1') {
        try {
            const response = await fetch(`${this.backendUrl}/collections`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description, color })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to create collection');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Refresh collections list
                this.fetchCollections();
                this.showIndexStatus(`Collection "${name}" created successfully!`, 'success');
            } else {
                throw new Error(data.error || 'Failed to create collection');
            }
        } catch (error) {
            console.error('Error creating collection:', error);
            this.showError(`Error creating collection: ${error.message}`);
        }
    }

    async showCategorizationStats() {
        try {
            const response = await fetch(`${this.backendUrl}/collections/stats`);
            if (!response.ok) {
                throw new Error('Failed to fetch categorization stats');
            }
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const stats = data.stats;
                const message = `📊 Categorization Statistics\n\n` +
                               `Total Videos: ${stats.total_videos}\n` +
                               `Total Collections: ${stats.total_collections}\n` +
                               `Auto Collections: ${stats.auto_collections}\n` +
                               `Manual Collections: ${stats.manual_collections}\n` +
                               `Categorization: ${stats.categorization_method}\n` +
                               `Base Categories: ${stats.base_categories_count}\n\n` +
                               `Top Collections:\n` +
                               Object.entries(stats.collection_distribution)
                                   .sort(([,a], [,b]) => b - a)
                                   .slice(0, 5)
                                   .map(([name, count]) => `• ${name}: ${count} videos`)
                                   .join('\n');
                
                alert(message);
            } else {
                throw new Error(data.error || 'Failed to load stats');
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
            this.showError(`Error fetching stats: ${error.message}`);
        }
    }

    formatTime(seconds) {
        if (!seconds) return '0:00';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            const remainingMinutes = minutes % 60;
            return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
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

    hideStatus() {
        const statusSection = document.getElementById('statusSection');
        if (statusSection) {
            statusSection.classList.add('hidden');
        }
    }

    showIndexStatus(message, type) {
        const statusElement = document.getElementById('indexStatus');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status-message ${type}`;
            statusElement.style.display = 'block';
            
            if (type === 'success') {
                setTimeout(() => {
                    statusElement.style.display = 'none';
                }, 3000);
            }
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
}

// Initialize the agent when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Nexus] Initializing Nexus Agent');
    new NexusAgent();
});
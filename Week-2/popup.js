// Main popup logic and UI management

class PopupManager {
    constructor() {
        this.orchestrator = new WorkflowOrchestrator();
        this.currentInput = '';
        this.rolesConfig = null;
        this.workflowSteps = []; // Array of agent IDs in execution order
        this.init();
    }

    async init() {
        await this.loadRolesConfig();
        await this.orchestrator.loadFromStorage();
        await this.loadWorkflowFromStorage();
        this.setupEventListeners();
        this.populateRoleSelectors();
        this.renderAgents();
        this.updateExecutionModeUI();
        await this.loadSettings();
    }

    setupEventListeners() {
        // Agent management
        document.getElementById('addAgentBtn').addEventListener('click', () => this.showAgentModal());
        document.getElementById('agentForm').addEventListener('submit', (e) => this.handleAgentSubmit(e));
        document.getElementById('cancelBtn').addEventListener('click', () => this.hideAgentModal());

        // Execution mode
        document.getElementById('sequentialBtn').addEventListener('click', () => this.setExecutionMode('sequential'));
        document.getElementById('parallelBtn').addEventListener('click', () => this.setExecutionMode('parallel'));

        // Workflow execution
        document.getElementById('runWorkflowBtn').addEventListener('click', () => this.runWorkflow());

        // Settings
        document.getElementById('settingsBtn').addEventListener('click', () => this.showSettingsModal());
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('closeSettingsBtn').addEventListener('click', () => this.hideSettingsModal());

        // Role Management
        document.getElementById('manageRolesBtn').addEventListener('click', () => this.showRoleManagementModal());
        document.getElementById('closeRoleManagementBtn').addEventListener('click', () => this.hideRoleManagementModal());
        document.getElementById('addRoleBtn').addEventListener('click', () => this.showRoleEditor());
        document.getElementById('roleEditorForm').addEventListener('submit', (e) => this.handleRoleSubmit(e));
        document.getElementById('cancelRoleEditorBtn').addEventListener('click', () => this.hideRoleEditor());

        // Tab Management
        document.getElementById('rolesTab').addEventListener('click', () => this.showRolesTab());
        document.getElementById('inputTypesTab').addEventListener('click', () => this.showInputTypesTab());

        // Input Type Management
        document.getElementById('addInputTypeBtn').addEventListener('click', () => this.showInputTypeEditor());
        document.getElementById('inputTypeEditorForm').addEventListener('submit', (e) => this.handleInputTypeSubmit(e));
        document.getElementById('cancelInputTypeEditorBtn').addEventListener('click', () => this.hideInputTypeEditor());

        // Workflow Builder
        document.getElementById('clearWorkflowBtn').addEventListener('click', () => this.clearWorkflow());

        // Output actions
        document.getElementById('exportBtn').addEventListener('click', () => this.toggleExportDropdown());
        document.getElementById('exportJsonBtn').addEventListener('click', () => this.exportResults('json'));
        document.getElementById('exportMarkdownBtn').addEventListener('click', () => this.exportResults('markdown'));
        document.getElementById('exportPdfBtn').addEventListener('click', () => this.exportResults('pdf'));
        document.getElementById('copyBtn').addEventListener('click', () => this.copyResults());

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#exportBtn') && !e.target.closest('#exportDropdown')) {
                document.getElementById('exportDropdown').classList.add('hidden');
            }
        });

        // Modal close on background click
        document.getElementById('agentModal').addEventListener('click', (e) => {
            if (e.target.id === 'agentModal') this.hideAgentModal();
        });
        document.getElementById('settingsModal').addEventListener('click', (e) => {
            if (e.target.id === 'settingsModal') this.hideSettingsModal();
        });
    }

    showAgentModal(agent = null) {
        const modal = document.getElementById('agentModal');
        const form = document.getElementById('agentForm');
        
        if (agent) {
            // Edit mode
            document.getElementById('agentName').value = agent.name;
            document.getElementById('agentRole').value = agent.role;
            document.getElementById('agentPrompt').value = agent.prompt;
            document.getElementById('agentInputType').value = agent.inputType;
            form.dataset.editId = agent.id;
        } else {
            // Add mode
            form.reset();
            delete form.dataset.editId;
        }
        
        modal.classList.remove('hidden');
    }

    hideAgentModal() {
        document.getElementById('agentModal').classList.add('hidden');
    }

    async handleAgentSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const name = document.getElementById('agentName').value;
        const role = document.getElementById('agentRole').value;
        const prompt = document.getElementById('agentPrompt').value;
        const inputType = document.getElementById('agentInputType').value;

        if (form.dataset.editId) {
            // Edit existing agent
            const agent = this.orchestrator.getAgent(form.dataset.editId);
            if (agent) {
                agent.name = name;
                agent.role = role;
                agent.prompt = prompt;
                agent.inputType = inputType;
            }
        } else {
            // Add new agent
            const agent = new Agent(
                Date.now().toString(),
                name,
                role,
                prompt,
                inputType
            );
            this.orchestrator.addAgent(agent);
        }

        await this.orchestrator.saveToStorage();
        this.renderAgents();
        this.hideAgentModal();
    }

    renderAgents() {
        const agentList = document.getElementById('agentList');
        
        if (this.orchestrator.agents.length === 0) {
            agentList.innerHTML = '<p class="text-sm text-gray-500 text-center py-4">No agents configured</p>';
            this.renderWorkflow();
            return;
        }

        agentList.innerHTML = this.orchestrator.agents.map(agent => `
            <div class="agent-card" draggable="true" data-agent-id="${agent.id}">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <div class="drag-handle cursor-move text-gray-400 hover:text-gray-600">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"></path>
                            </svg>
                        </div>
                        <div class="flex-1">
                            <div class="flex items-center space-x-2">
                                <span class="font-medium text-sm">${agent.name}</span>
                                <span class="agent-status status-${agent.status}">${agent.status}</span>
                            </div>
                            <p class="text-xs text-gray-500">${agent.role}</p>
                        </div>
                    </div>
                    <div class="flex space-x-1">
                        <button class="add-to-workflow-btn p-1 text-gray-400 hover:text-green-600" data-agent-id="${agent.id}" title="Add to Workflow">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                            </svg>
                        </button>
                        <button class="edit-agent-btn p-1 text-gray-400 hover:text-blue-600" data-agent-id="${agent.id}" title="Edit Agent">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button class="delete-agent-btn p-1 text-gray-400 hover:text-red-600" data-agent-id="${agent.id}" title="Delete Agent">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        // Add event listeners for agent buttons
        this.setupAgentButtonListeners();
        
        this.renderWorkflow();
    }

    setupAgentButtonListeners() {
        // Add to workflow buttons
        document.querySelectorAll('.add-to-workflow-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.addToWorkflow(agentId);
            });
        });

        // Edit agent buttons
        document.querySelectorAll('.edit-agent-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.editAgent(agentId);
            });
        });

        // Delete agent buttons
        document.querySelectorAll('.delete-agent-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.deleteAgent(agentId);
            });
        });
    }

    editAgent(agentId) {
        const agent = this.orchestrator.getAgent(agentId);
        if (agent) {
            this.showAgentModal(agent);
        }
    }

    async deleteAgent(agentId) {
        if (confirm('Are you sure you want to delete this agent?')) {
            this.orchestrator.removeAgent(agentId);
            await this.orchestrator.saveToStorage();
            this.renderAgents();
        }
    }

    setExecutionMode(mode) {
        this.orchestrator.setExecutionMode(mode);
        this.updateExecutionModeUI();
        this.renderWorkflow(); // Re-render workflow to update numbering/arrows
        this.orchestrator.saveToStorage();
    }

    updateExecutionModeUI() {
        const sequentialBtn = document.getElementById('sequentialBtn');
        const parallelBtn = document.getElementById('parallelBtn');
        
        sequentialBtn.classList.remove('active');
        parallelBtn.classList.remove('active');
        
        if (this.orchestrator.executionMode === 'sequential') {
            sequentialBtn.classList.add('active');
        } else {
            parallelBtn.classList.add('active');
        }
    }

    async runWorkflow() {
        const runBtn = document.getElementById('runWorkflowBtn');
        
        if (this.workflowSteps.length === 0) {
            alert('Please add agents to the workflow before running.');
            return;
        }

        // Get API key
        const settings = await chrome.storage.local.get(['apiKey']);
        if (!settings.apiKey) {
            alert('Please configure your Google Gemini API key in settings.');
            this.showSettingsModal();
            return;
        }

        try {
            runBtn.disabled = true;
            runBtn.textContent = 'Running...';
            
            // Show output panel
            document.getElementById('outputPanel').classList.remove('hidden');
            
            // Get the first agent to determine input type
            const firstAgent = this.orchestrator.getAgent(this.workflowSteps[0]);
            const inputTypeDisplay = this.getInputTypeDisplay(firstAgent.inputType);
            
            // Update button text to show what's happening
            runBtn.textContent = `Getting ${inputTypeDisplay}...`;
            
            // Get initial input based on first agent's input type
            const initialInput = await this.getInitialInput();
            if (initialInput === null) return; // User cancelled or error occurred
            
            runBtn.textContent = 'Processing...';
            
            // Run workflow with ordered steps
            await this.orchestrator.runWorkflowWithSteps(this.workflowSteps, initialInput, settings.apiKey);
            this.renderResults();
            
        } catch (error) {
            alert(`Workflow failed: ${error.message}`);
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = 'Run Workflow';
        }
    }

    renderResults() {
        const outputResults = document.getElementById('outputResults');
        const results = this.orchestrator.getResults();
        
        outputResults.innerHTML = results.map((result, index) => `
            <div class="output-card">
                <div class="output-header cursor-pointer" data-result-index="${index}">
                    <div class="flex items-center space-x-2">
                        <span class="font-medium text-sm">${result.name}</span>
                        <span class="agent-status status-${result.status}">${result.status}</span>
                    </div>
                    <svg class="w-4 h-4 text-gray-400 collapse-arrow transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                </div>
                <div class="output-content hidden" data-content-index="${index}">
                    ${result.error ? 
                        `<span class="text-red-600">Error: ${result.error}</span>` : 
                        this.renderMarkdown(result.output || 'No output')
                    }
                </div>
            </div>
        `).join('');
        
        // Add event listeners for collapse functionality
        this.setupResultsCollapseListeners();
        
        // Set initial arrow states
        this.setInitialArrowStates();
    }

    setupResultsCollapseListeners() {
        document.querySelectorAll('.output-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const index = e.currentTarget.getAttribute('data-result-index');
                const content = document.querySelector(`[data-content-index="${index}"]`);
                const arrow = e.currentTarget.querySelector('.collapse-arrow');
                
                if (content) {
                    // Toggle content visibility
                    content.classList.toggle('hidden');
                    
                    // Rotate arrow based on state
                    if (content.classList.contains('hidden')) {
                        arrow.style.transform = 'rotate(0deg)'; // Right arrow (collapsed)
                    } else {
                        arrow.style.transform = 'rotate(90deg)'; // Down arrow (expanded)
                    }
                }
            });
        });
    }

    setInitialArrowStates() {
        document.querySelectorAll('.output-header').forEach(header => {
            const index = header.getAttribute('data-result-index');
            const content = document.querySelector(`[data-content-index="${index}"]`);
            const arrow = header.querySelector('.collapse-arrow');
            
            if (content && arrow) {
                // Set arrow direction based on initial content visibility
                if (content.classList.contains('hidden')) {
                    arrow.style.transform = 'rotate(0deg)'; // Right arrow (collapsed)
                } else {
                    arrow.style.transform = 'rotate(90deg)'; // Down arrow (expanded)
                }
            }
        });
    }

    showSettingsModal() {
        document.getElementById('settingsModal').classList.remove('hidden');
    }

    hideSettingsModal() {
        document.getElementById('settingsModal').classList.add('hidden');
    }

    async loadSettings() {
        const settings = await chrome.storage.local.get(['apiKey']);
        if (settings.apiKey) {
            document.getElementById('apiKey').value = settings.apiKey;
        }
    }

    async saveSettings() {
        const apiKey = document.getElementById('apiKey').value;
        await chrome.storage.local.set({ apiKey });
        this.hideSettingsModal();
    }

    // Role Management Methods
    async loadRolesConfig() {
        try {
            const response = await fetch(chrome.runtime.getURL('roles.json'));
            this.rolesConfig = await response.json();
            
            // Load custom roles and input types from storage and merge
            const customData = await chrome.storage.local.get(['customRoles', 'customInputTypes']);
            if (customData.customRoles) {
                this.rolesConfig.roles = [...this.rolesConfig.roles, ...customData.customRoles];
            }
            if (customData.customInputTypes) {
                this.rolesConfig.inputTypes = [...this.rolesConfig.inputTypes, ...customData.customInputTypes];
            }
        } catch (error) {
            console.error('Failed to load roles config:', error);
            // Fallback to basic config
            this.rolesConfig = {
                roles: [
                    { id: 'custom', name: 'Custom', description: 'Custom role', defaultPrompt: '', defaultInputType: 'text', category: 'data' }
                ],
                inputTypes: [
                    { id: 'text', name: 'Text Input', description: 'Direct text input', handler: 'handleTextInput', requiresPermission: false },
                    { id: 'page_scrape', name: 'Page Scrape', description: 'Scraped content', handler: 'handlePageScrape', requiresPermission: true },
                    { id: 'previous_output', name: 'Previous Output', description: 'Previous agent output', handler: 'handlePreviousOutput', requiresPermission: false }
                ],
                categories: [
                    { id: 'data', name: 'Data Processing', color: 'blue' }
                ]
            };
        }
    }

    populateRoleSelectors() {
        const roleSelect = document.getElementById('agentRole');
        const inputTypeSelect = document.getElementById('agentInputType');
        const categorySelect = document.getElementById('roleCategory');
        const defaultInputTypeSelect = document.getElementById('roleDefaultInputType');

        // Populate role selector
        roleSelect.innerHTML = this.rolesConfig.roles.map(role => 
            `<option value="${role.id}">${role.name}</option>`
        ).join('');

        // Populate input type selectors
        const inputTypeOptions = this.rolesConfig.inputTypes.map(type => 
            `<option value="${type.id}">${type.name}</option>`
        ).join('');
        inputTypeSelect.innerHTML = inputTypeOptions;
        if (defaultInputTypeSelect) {
            defaultInputTypeSelect.innerHTML = inputTypeOptions;
        }

        // Populate category selector
        if (categorySelect) {
            categorySelect.innerHTML = this.rolesConfig.categories.map(category => 
                `<option value="${category.id}">${category.name}</option>`
            ).join('');
        }

        // Handle role selection change
        roleSelect.addEventListener('change', (e) => {
            const selectedRole = this.rolesConfig.roles.find(role => role.id === e.target.value);
            if (selectedRole) {
                document.getElementById('agentPrompt').value = selectedRole.defaultPrompt;
                document.getElementById('agentInputType').value = selectedRole.defaultInputType;
            }
        });
    }

    showRoleManagementModal() {
        this.showRolesTab(); // Default to roles tab
        document.getElementById('roleManagementModal').classList.remove('hidden');
    }

    hideRoleManagementModal() {
        document.getElementById('roleManagementModal').classList.add('hidden');
    }

    renderRolesList() {
        const rolesList = document.getElementById('rolesList');
        
        rolesList.innerHTML = this.rolesConfig.roles.map(role => {
            const category = this.rolesConfig.categories.find(cat => cat.id === role.category);
            const isCustom = !['scraper', 'summarizer', 'analyzer', 'compliance', 'researcher', 'translator'].includes(role.id);
            
            return `
                <div class="bg-gray-50 border border-gray-200 rounded p-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="flex items-center space-x-2">
                                <h4 class="font-medium text-gray-800">${role.name}</h4>
                                <span class="px-2 py-1 text-xs rounded-full bg-${category?.color || 'gray'}-100 text-${category?.color || 'gray'}-600">
                                    ${category?.name || 'Unknown'}
                                </span>
                                ${isCustom ? '<span class="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-600">Custom</span>' : ''}
                            </div>
                            <p class="text-sm text-gray-600 mt-1">${role.description}</p>
                            <p class="text-xs text-gray-500 mt-1">Default Input: ${this.rolesConfig.inputTypes.find(t => t.id === role.defaultInputType)?.name || role.defaultInputType}</p>
                        </div>
                        <div class="flex space-x-2">
                            <button class="edit-role-btn p-1 text-blue-600 hover:text-blue-800" data-role-id="${role.id}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                            </button>
                            ${isCustom ? `
                                <button class="delete-role-btn p-1 text-red-600 hover:text-red-800" data-role-id="${role.id}">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    showRoleEditor(role = null) {
        const modal = document.getElementById('roleEditorModal');
        const form = document.getElementById('roleEditorForm');
        const title = document.getElementById('roleEditorTitle');
        
        if (role) {
            // Edit mode
            title.textContent = 'Edit Role';
            document.getElementById('roleName').value = role.name;
            document.getElementById('roleDescription').value = role.description;
            document.getElementById('roleCategory').value = role.category;
            document.getElementById('roleDefaultPrompt').value = role.defaultPrompt;
            document.getElementById('roleDefaultInputType').value = role.defaultInputType;
            form.dataset.editId = role.id;
        } else {
            // Add mode
            title.textContent = 'Add New Role';
            form.reset();
            delete form.dataset.editId;
        }
        
        modal.classList.remove('hidden');
    }

    hideRoleEditor() {
        document.getElementById('roleEditorModal').classList.add('hidden');
    }

    async handleRoleSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const roleData = {
            id: form.dataset.editId || Date.now().toString(),
            name: document.getElementById('roleName').value,
            description: document.getElementById('roleDescription').value,
            category: document.getElementById('roleCategory').value,
            defaultPrompt: document.getElementById('roleDefaultPrompt').value,
            defaultInputType: document.getElementById('roleDefaultInputType').value
        };

        // Get existing custom roles
        const customRoles = await chrome.storage.local.get(['customRoles']);
        let roles = customRoles.customRoles || [];

        if (form.dataset.editId) {
            // Edit existing role
            const index = roles.findIndex(role => role.id === form.dataset.editId);
            if (index !== -1) {
                roles[index] = roleData;
            } else {
                // Editing a built-in role - add as custom override
                roles.push(roleData);
            }
        } else {
            // Add new role
            roles.push(roleData);
        }

        // Save to storage
        await chrome.storage.local.set({ customRoles: roles });
        
        // Reload config and update UI
        await this.loadRolesConfig();
        this.populateRoleSelectors();
        this.renderRolesList();
        this.hideRoleEditor();
    }

    editRole(roleId) {
        const role = this.rolesConfig.roles.find(r => r.id === roleId);
        if (role) {
            this.showRoleEditor(role);
        }
    }

    async deleteRole(roleId) {
        if (confirm('Are you sure you want to delete this role?')) {
            const customRoles = await chrome.storage.local.get(['customRoles']);
            let roles = customRoles.customRoles || [];
            
            roles = roles.filter(role => role.id !== roleId);
            await chrome.storage.local.set({ customRoles: roles });
            
            // Reload config and update UI
            await this.loadRolesConfig();
            this.populateRoleSelectors();
            this.renderRolesList();
        }
    }

    // Tab Management
    showRolesTab() {
        document.getElementById('rolesTab').classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        document.getElementById('rolesTab').classList.remove('text-gray-600');
        document.getElementById('inputTypesTab').classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        document.getElementById('inputTypesTab').classList.add('text-gray-600');
        
        document.getElementById('rolesSection').classList.remove('hidden');
        document.getElementById('inputTypesSection').classList.add('hidden');
        
        this.renderRolesList();
    }

    showInputTypesTab() {
        document.getElementById('inputTypesTab').classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        document.getElementById('inputTypesTab').classList.remove('text-gray-600');
        document.getElementById('rolesTab').classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        document.getElementById('rolesTab').classList.add('text-gray-600');
        
        document.getElementById('inputTypesSection').classList.remove('hidden');
        document.getElementById('rolesSection').classList.add('hidden');
        
        this.renderInputTypesList();
    }

    // Input Type Management Methods
    renderInputTypesList() {
        const inputTypesList = document.getElementById('inputTypesList');
        
        inputTypesList.innerHTML = this.rolesConfig.inputTypes.map(inputType => {
            const isCustom = !['text', 'page_scrape', 'previous_output', 'file_upload', 'clipboard', 'api_call'].includes(inputType.id);
            
            return `
                <div class="bg-gray-50 border border-gray-200 rounded p-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="flex items-center space-x-2">
                                <h4 class="font-medium text-gray-800">${inputType.name}</h4>
                                ${inputType.requiresPermission ? '<span class="px-2 py-1 text-xs rounded-full bg-orange-100 text-orange-600">Requires Permission</span>' : ''}
                                ${isCustom ? '<span class="px-2 py-1 text-xs rounded-full bg-purple-100 text-purple-600">Custom</span>' : ''}
                            </div>
                            <p class="text-sm text-gray-600 mt-1">${inputType.description}</p>
                            ${inputType.handler ? `<p class="text-xs text-gray-500 mt-1">Handler: ${inputType.handler}</p>` : ''}
                        </div>
                        <div class="flex space-x-2">
                            <button class="edit-input-type-btn p-1 text-blue-600 hover:text-blue-800" data-input-type-id="${inputType.id}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                            </button>
                            ${isCustom ? `
                                <button class="delete-input-type-btn p-1 text-red-600 hover:text-red-800" data-input-type-id="${inputType.id}">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add event listeners for input type buttons
        this.setupInputTypeButtonListeners();
    }

    setupInputTypeButtonListeners() {
        // Edit input type buttons
        document.querySelectorAll('.edit-input-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const inputTypeId = e.currentTarget.getAttribute('data-input-type-id');
                this.editInputType(inputTypeId);
            });
        });

        // Delete input type buttons
        document.querySelectorAll('.delete-input-type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const inputTypeId = e.currentTarget.getAttribute('data-input-type-id');
                this.deleteInputType(inputTypeId);
            });
        });
    }

    showInputTypeEditor(inputType = null) {
        const modal = document.getElementById('inputTypeEditorModal');
        const form = document.getElementById('inputTypeEditorForm');
        const title = document.getElementById('inputTypeEditorTitle');
        
        if (inputType) {
            // Edit mode
            title.textContent = 'Edit Input Type';
            document.getElementById('inputTypeName').value = inputType.name;
            document.getElementById('inputTypeDescription').value = inputType.description;
            document.getElementById('inputTypeHandler').value = inputType.handler || '';
            document.getElementById('inputTypeRequiresPermission').checked = inputType.requiresPermission || false;
            form.dataset.editId = inputType.id;
        } else {
            // Add mode
            title.textContent = 'Add New Input Type';
            form.reset();
            delete form.dataset.editId;
        }
        
        modal.classList.remove('hidden');
    }

    hideInputTypeEditor() {
        document.getElementById('inputTypeEditorModal').classList.add('hidden');
    }

    async handleInputTypeSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const inputTypeData = {
            id: form.dataset.editId || Date.now().toString(),
            name: document.getElementById('inputTypeName').value,
            description: document.getElementById('inputTypeDescription').value,
            handler: document.getElementById('inputTypeHandler').value || null,
            requiresPermission: document.getElementById('inputTypeRequiresPermission').checked
        };

        // Get existing custom input types
        const customInputTypes = await chrome.storage.local.get(['customInputTypes']);
        let inputTypes = customInputTypes.customInputTypes || [];

        if (form.dataset.editId) {
            // Edit existing input type
            const index = inputTypes.findIndex(inputType => inputType.id === form.dataset.editId);
            if (index !== -1) {
                inputTypes[index] = inputTypeData;
            } else {
                // Editing a built-in input type - add as custom override
                inputTypes.push(inputTypeData);
            }
        } else {
            // Add new input type
            inputTypes.push(inputTypeData);
        }

        // Save to storage
        await chrome.storage.local.set({ customInputTypes: inputTypes });
        
        // Reload config and update UI
        await this.loadRolesConfig();
        this.populateRoleSelectors();
        this.renderInputTypesList();
        this.hideInputTypeEditor();
    }

    editInputType(inputTypeId) {
        const inputType = this.rolesConfig.inputTypes.find(it => it.id === inputTypeId);
        if (inputType) {
            this.showInputTypeEditor(inputType);
        }
    }

    async deleteInputType(inputTypeId) {
        if (confirm('Are you sure you want to delete this input type?')) {
            const customInputTypes = await chrome.storage.local.get(['customInputTypes']);
            let inputTypes = customInputTypes.customInputTypes || [];
            
            inputTypes = inputTypes.filter(inputType => inputType.id !== inputTypeId);
            await chrome.storage.local.set({ customInputTypes: inputTypes });
            
            // Reload config and update UI
            await this.loadRolesConfig();
            this.populateRoleSelectors();
            this.renderInputTypesList();
        }
    }

    // Workflow Builder Methods
    renderWorkflow() {
        const workflowSteps = document.getElementById('workflowSteps');
        const emptyWorkflow = document.getElementById('emptyWorkflow');
        
        if (this.workflowSteps.length === 0) {
            workflowSteps.innerHTML = '';
            emptyWorkflow.classList.remove('hidden');
            return;
        }
        
        emptyWorkflow.classList.add('hidden');
        
        workflowSteps.innerHTML = this.workflowSteps.map((agentId, index) => {
            const agent = this.orchestrator.getAgent(agentId);
            if (!agent) return '';
            
            const isLast = index === this.workflowSteps.length - 1;
            const executionMode = this.orchestrator.executionMode;
            
            return `
                <div class="workflow-step" data-agent-id="${agentId}">
                    <div class="flex items-center space-x-2">
                        <div class="workflow-step-number">
                            ${executionMode === 'sequential' ? index + 1 : '•'}
                        </div>
                        <div class="flex-1 bg-blue-50 border border-blue-200 rounded p-2">
                            <div class="flex items-center justify-between">
                                <div class="flex-1">
                                    <div class="flex items-center space-x-2">
                                        <span class="font-medium text-sm text-blue-800">${agent.name}</span>
                                        <span class="px-2 py-1 text-xs rounded bg-blue-100 text-blue-600">${agent.role}</span>
                                        ${index === 0 ? '<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-600">First</span>' : ''}
                                    </div>
                                    <p class="text-xs text-blue-600 mt-1">Input: ${this.getInputTypeDisplay(agent.inputType)}</p>
                                </div>
                                <div class="flex space-x-1">
                                    ${index > 0 ? `<button class="move-workflow-up-btn p-1 text-blue-600 hover:text-blue-800" data-agent-id="${agentId}" title="Move Up">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path>
                                        </svg>
                                    </button>` : ''}
                                    ${!isLast ? `<button class="move-workflow-down-btn p-1 text-blue-600 hover:text-blue-800" data-agent-id="${agentId}" title="Move Down">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                        </svg>
                                    </button>` : ''}
                                    <button class="remove-from-workflow-btn p-1 text-red-600 hover:text-red-800" data-agent-id="${agentId}" title="Remove from Workflow">
                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                        </svg>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    ${!isLast && executionMode === 'sequential' ? `
                        <div class="workflow-arrow">
                            <svg class="w-4 h-4 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
        this.saveWorkflowToStorage();
        this.updateWorkflowInfo();
        
        // Add event listeners for workflow buttons
        this.setupWorkflowButtonListeners();
    }

    updateWorkflowInfo() {
        const workflowInfo = document.getElementById('workflowInfo');
        const workflowInfoText = document.getElementById('workflowInfoText');
        
        if (this.workflowSteps.length === 0) {
            workflowInfo.classList.add('hidden');
            return;
        }
        
        const firstAgent = this.orchestrator.getAgent(this.workflowSteps[0]);
        if (!firstAgent) {
            workflowInfo.classList.add('hidden');
            return;
        }
        
        const inputTypeDisplay = this.getInputTypeDisplay(firstAgent.inputType);
        const actionMap = {
            'page_scrape': 'will automatically scrape the current webpage',
            'file_upload': 'will open a file picker for you to select a file',
            'text': 'will ask you to enter text input',
            'clipboard': 'will use content from your clipboard',
            'api_call': 'will ask you for an API endpoint to call',
            'previous_output': 'ERROR: First agent cannot use previous output'
        };
        
        const action = actionMap[firstAgent.inputType] || 'will process your input';
        workflowInfoText.textContent = `When you run this workflow, it ${action}.`;
        
        // Show warning for invalid first agent
        if (firstAgent.inputType === 'previous_output') {
            workflowInfo.className = 'mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700';
        } else {
            workflowInfo.className = 'mb-3 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-700';
        }
        
        workflowInfo.classList.remove('hidden');
    }

    setupWorkflowButtonListeners() {
        // Move up buttons
        document.querySelectorAll('.move-workflow-up-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.moveWorkflowStep(agentId, 'up');
            });
        });

        // Move down buttons
        document.querySelectorAll('.move-workflow-down-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.moveWorkflowStep(agentId, 'down');
            });
        });

        // Remove from workflow buttons
        document.querySelectorAll('.remove-from-workflow-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const agentId = e.currentTarget.getAttribute('data-agent-id');
                this.removeFromWorkflow(agentId);
            });
        });
    }

    addToWorkflow(agentId) {
        if (!this.workflowSteps.includes(agentId)) {
            this.workflowSteps.push(agentId);
            this.renderWorkflow();
        }
    }

    removeFromWorkflow(agentId) {
        this.workflowSteps = this.workflowSteps.filter(id => id !== agentId);
        this.renderWorkflow();
    }

    moveWorkflowStep(agentId, direction) {
        const currentIndex = this.workflowSteps.indexOf(agentId);
        if (currentIndex === -1) return;
        
        const newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
        
        if (newIndex >= 0 && newIndex < this.workflowSteps.length) {
            // Swap elements
            [this.workflowSteps[currentIndex], this.workflowSteps[newIndex]] = 
            [this.workflowSteps[newIndex], this.workflowSteps[currentIndex]];
            
            this.renderWorkflow();
        }
    }

    clearWorkflow() {
        if (confirm('Are you sure you want to clear the workflow?')) {
            this.workflowSteps = [];
            this.renderWorkflow();
        }
    }

    async saveWorkflowToStorage() {
        await chrome.storage.local.set({ workflowSteps: this.workflowSteps });
    }

    async loadWorkflowFromStorage() {
        const data = await chrome.storage.local.get(['workflowSteps']);
        if (data.workflowSteps) {
            this.workflowSteps = data.workflowSteps;
        }
    }

    // Initial Input Handling Methods
    async getInitialInput() {
        if (this.workflowSteps.length === 0) {
            throw new Error('No workflow steps configured');
        }

        // Get the first agent in the workflow
        const firstAgentId = this.workflowSteps[0];
        const firstAgent = this.orchestrator.getAgent(firstAgentId);
        
        if (!firstAgent) {
            throw new Error(`First agent with ID ${firstAgentId} not found`);
        }

        const inputType = firstAgent.inputType;

        switch (inputType) {
            case 'page_scrape':
                // Automatically scrape the current web page
                return await this.scrapeCurrentPage();
                
            case 'file_upload':
                // Open file picker and extract content
                return await this.handleFileUpload();
                
            case 'text':
                // Ask user for manual text input
                return await this.getTextInput();
                
            case 'previous_output':
                // Invalid: first agent cannot depend on previous output
                alert('Error: The first agent cannot depend on a previous agent output.');
                return null;
                
            case 'clipboard':
                // Get content from clipboard
                return await this.getClipboardContent();
                
            case 'api_call':
                // Handle API call input
                return await this.handleApiCall();
                
            default:
                // Fallback to text input for unknown types
                console.warn(`Unknown input type: ${inputType}. Falling back to text input.`);
                return await this.getTextInput();
        }
    }

    async scrapeCurrentPage() {
        try {
            // Get the current active tab
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            // Send message to background script to scrape the page
            const response = await chrome.runtime.sendMessage({
                action: 'scrapeCurrentPage',
                tabId: tab.id
            });

            if (response.success) {
                const content = response.content;
                return `Page Title: ${content.title}\nURL: ${content.url}\n\nContent:\n${content.text}`;
            } else {
                throw new Error(response.error || 'Failed to scrape page');
            }
        } catch (error) {
            console.error('Page scraping failed:', error);
            alert(`Failed to scrape page: ${error.message}. Please enter text manually.`);
            return await this.getTextInput();
        }
    }

    async handleFileUpload() {
        return new Promise((resolve) => {
            // Create file input element
            const fileInput = document.createElement('input');
            fileInput.type = 'file';
            fileInput.accept = '.txt,.pdf,.doc,.docx,.md';
            fileInput.style.display = 'none';
            
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) {
                    resolve(null);
                    return;
                }

                try {
                    const content = await this.extractFileContent(file);
                    resolve(content);
                } catch (error) {
                    console.error('File processing failed:', error);
                    alert(`Failed to process file: ${error.message}. Please enter text manually.`);
                    const textInput = await this.getTextInput();
                    resolve(textInput);
                }
                
                // Clean up
                document.body.removeChild(fileInput);
            });

            // Add to DOM and trigger click
            document.body.appendChild(fileInput);
            fileInput.click();
        });
    }

    async extractFileContent(file) {
        const fileType = file.type;
        const fileName = file.name.toLowerCase();

        if (fileType === 'text/plain' || fileName.endsWith('.txt') || fileName.endsWith('.md')) {
            // Handle text files
            return await this.readTextFile(file);
        } else if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
            // Handle PDF files
            return await this.readPdfFile(file);
        } else {
            // Try to read as text for other file types
            return await this.readTextFile(file);
        }
    }

    async readTextFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    async readPdfFile(file) {
        // For PDF files, we'll read as text for now
        // In a full implementation, you'd use PDF.js here
        try {
            const text = await this.readTextFile(file);
            return `PDF Content (Note: PDF parsing not fully implemented):\n${text}`;
        } catch (error) {
            throw new Error('PDF processing not available. Please convert to text file.');
        }
    }

    async getTextInput() {
        return new Promise((resolve) => {
            const input = prompt('Enter the initial input for the workflow:');
            resolve(input);
        });
    }

    async getClipboardContent() {
        try {
            const text = await navigator.clipboard.readText();
            if (text && text.trim()) {
                return `Clipboard Content:\n${text}`;
            } else {
                alert('Clipboard is empty. Please enter text manually.');
                return await this.getTextInput();
            }
        } catch (error) {
            console.error('Clipboard access failed:', error);
            alert('Cannot access clipboard. Please enter text manually.');
            return await this.getTextInput();
        }
    }

    async handleApiCall() {
        // For API calls, ask user for the API endpoint and parameters
        const apiUrl = prompt('Enter API URL:');
        if (!apiUrl) return null;

        try {
            const response = await fetch(apiUrl);
            const data = await response.text();
            return `API Response from ${apiUrl}:\n${data}`;
        } catch (error) {
            console.error('API call failed:', error);
            alert(`API call failed: ${error.message}. Please enter text manually.`);
            return await this.getTextInput();
        }
    }

    getInputTypeDisplay(inputType) {
        const displayMap = {
            'page_scrape': 'Page Content',
            'file_upload': 'File Content',
            'text': 'Text Input',
            'clipboard': 'Clipboard Content',
            'api_call': 'API Data',
            'previous_output': 'Previous Output'
        };
        return displayMap[inputType] || 'Input';
    }

    // Markdown Rendering
    renderMarkdown(text) {
        if (!text) return 'No output';
        
        // Escape HTML to prevent XSS
        let html = this.escapeHtml(text);
        
        // Convert markdown to HTML
        html = this.convertMarkdownToHtml(html);
        
        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    convertMarkdownToHtml(text) {
        // Headers
        text = text.replace(/^### (.*$)/gm, '<h3 class="text-md font-semibold text-gray-800 mt-3 mb-2">$1</h3>');
        text = text.replace(/^## (.*$)/gm, '<h2 class="text-lg font-semibold text-gray-800 mt-4 mb-2">$1</h2>');
        text = text.replace(/^# (.*$)/gm, '<h1 class="text-xl font-bold text-gray-800 mt-4 mb-3">$1</h1>');
        
        // Bold and Italic
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-gray-800">$1</strong>');
        text = text.replace(/\*(.*?)\*/g, '<em class="italic text-gray-700">$1</em>');
        
        // Lists
        text = text.replace(/^\*   (.*$)/gm, '<li class="ml-6 text-gray-700">$1</li>');
        text = text.replace(/^\* (.*$)/gm, '<li class="ml-4 text-gray-700">$1</li>');
        
        // Wrap consecutive list items in ul tags
        text = text.replace(/(<li.*<\/li>\s*)+/g, (match) => {
            return '<ul class="list-disc list-outside mb-2">' + match + '</ul>';
        });
        
        // Code blocks
        text = text.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 p-2 rounded text-xs font-mono overflow-x-auto mb-2"><code>$1</code></pre>');
        
        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code class="bg-gray-100 px-1 rounded text-xs font-mono">$1</code>');
        
        // Tables
        text = this.convertMarkdownTables(text);
        
        // Line breaks
        text = text.replace(/\n\n/g, '</p><p class="mb-2 text-gray-700">');
        text = text.replace(/\n/g, '<br>');
        
        // Wrap in paragraph if not already wrapped
        if (!text.startsWith('<')) {
            text = '<p class="mb-2 text-gray-700">' + text + '</p>';
        }
        
        return text;
    }

    convertMarkdownTables(text) {
        // Split text into lines for table processing
        const lines = text.split('\n');
        const result = [];
        let i = 0;
        
        while (i < lines.length) {
            const line = lines[i].trim();
            
            // Check if this line looks like a table header (contains |)
            if (line.includes('|') && line.split('|').length > 2) {
                // Check if next line is a separator (contains | and -)
                const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
                if (nextLine.includes('|') && nextLine.includes('-')) {
                    // This is a table, process it
                    const tableResult = this.processMarkdownTable(lines, i);
                    result.push(tableResult.html);
                    i = tableResult.nextIndex;
                    continue;
                }
            }
            
            result.push(lines[i]);
            i++;
        }
        
        return result.join('\n');
    }

    processMarkdownTable(lines, startIndex) {
        const tableLines = [];
        let i = startIndex;
        
        // Collect all table lines
        while (i < lines.length) {
            const line = lines[i].trim();
            if (line.includes('|')) {
                tableLines.push(line);
                i++;
            } else {
                break;
            }
        }
        
        if (tableLines.length < 2) {
            return { html: lines[startIndex], nextIndex: startIndex + 1 };
        }
        
        // Parse header
        const headerCells = tableLines[0].split('|').map(cell => cell.trim()).filter(cell => cell);
        
        // Skip separator line (index 1)
        
        // Parse data rows
        const dataRows = [];
        for (let j = 2; j < tableLines.length; j++) {
            const cells = tableLines[j].split('|').map(cell => cell.trim()).filter(cell => cell);
            if (cells.length > 0) {
                dataRows.push(cells);
            }
        }
        
        // Generate HTML table
        let html = '<table class="table-auto w-full border-collapse border border-gray-300 mb-4 text-sm">';
        
        // Header
        html += '<thead class="bg-gray-100">';
        html += '<tr>';
        headerCells.forEach(cell => {
            html += `<th class="border border-gray-300 px-2 py-1 text-left font-semibold">${cell}</th>`;
        });
        html += '</tr>';
        html += '</thead>';
        
        // Body
        html += '<tbody>';
        dataRows.forEach(row => {
            html += '<tr>';
            row.forEach((cell, index) => {
                html += `<td class="border border-gray-300 px-2 py-1">${cell}</td>`;
            });
            // Fill empty cells if row is shorter than header
            for (let k = row.length; k < headerCells.length; k++) {
                html += '<td class="border border-gray-300 px-2 py-1"></td>';
            }
            html += '</tr>';
        });
        html += '</tbody>';
        html += '</table>';
        
        return { html, nextIndex: i };
    }

    toggleExportDropdown() {
        const dropdown = document.getElementById('exportDropdown');
        dropdown.classList.toggle('hidden');
    }

    exportResults(format = 'json') {
        const results = this.orchestrator.getResults();
        const timestamp = new Date().toISOString();
        
        // Hide dropdown
        document.getElementById('exportDropdown').classList.add('hidden');
        
        if (format === 'pdf') {
            this.generatePdfExport(results, timestamp);
            return;
        }
        
        let content, mimeType, extension;
        
        if (format === 'markdown') {
            content = this.generateMarkdownExport(results, timestamp);
            mimeType = 'text/markdown';
            extension = 'md';
        } else {
            content = this.generateJsonExport(results, timestamp);
            mimeType = 'application/json';
            extension = 'json';
        }
        
        // Direct download like Week-1
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `workflow-results-${Date.now()}.${extension}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateJsonExport(results, timestamp) {
        const exportData = {
            timestamp: timestamp,
            executionMode: this.orchestrator.executionMode,
            workflowSteps: this.workflowSteps,
            results: results.map(result => ({
                id: result.id,
                name: result.name,
                role: result.role,
                status: result.status,
                output: result.output,
                error: result.error,
                executionTime: result.executionTime || null
            }))
        };
        
        return JSON.stringify(exportData, null, 2);
    }

    generateMarkdownExport(results, timestamp) {
        const date = new Date(timestamp).toLocaleString();
        let markdown = `# Mindflow Workflow Results\n\n`;
        markdown += `**Generated:** ${date}\n`;
        markdown += `**Execution Mode:** ${this.orchestrator.executionMode}\n`;
        markdown += `**Total Agents:** ${results.length}\n\n`;
        
        // Add workflow summary
        markdown += `## Workflow Summary\n\n`;
        results.forEach((result, index) => {
            const statusEmoji = this.getStatusEmoji(result.status);
            markdown += `${index + 1}. ${statusEmoji} **${result.name}** (${result.role}) - ${result.status}\n`;
        });
        markdown += `\n`;
        
        // Add detailed results
        markdown += `## Detailed Results\n\n`;
        results.forEach((result, index) => {
            const statusEmoji = this.getStatusEmoji(result.status);
            markdown += `### ${index + 1}. ${result.name} ${statusEmoji}\n\n`;
            markdown += `**Role:** ${result.role}\n`;
            markdown += `**Status:** ${result.status}\n\n`;
            
            if (result.error) {
                markdown += `**Error:**\n\`\`\`\n${result.error}\n\`\`\`\n\n`;
            } else if (result.output) {
                markdown += `**Output:**\n\n${result.output}\n\n`;
            } else {
                markdown += `**Output:** No output generated\n\n`;
            }
            
            markdown += `---\n\n`;
        });
        
        return markdown;
    }

    getStatusEmoji(status) {
        const emojiMap = {
            'idle': '⏸️',
            'running': '🔄',
            'completed': '✅',
            'error': '❌'
        };
        return emojiMap[status] || '❓';
    }

    generatePdfExport(results, timestamp) {
        // Simple PDF export using browser's print functionality (exact Week-1 approach)
        const printWindow = window.open('', '_blank');
        const date = new Date(timestamp).toLocaleString();
        
        const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mindflow Workflow Results</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 20px; 
                        line-height: 1.6; 
                    }
                    h1 { 
                        color: #2563eb; 
                        border-bottom: 2px solid #2563eb; 
                        padding-bottom: 10px; 
                    }
                    h2 { 
                        color: #1e40af; 
                        margin-top: 30px; 
                        border-bottom: 1px solid #e5e7eb; 
                        padding-bottom: 5px; 
                    }
                    .agent-result { 
                        margin-bottom: 30px; 
                        border: 1px solid #e5e7eb; 
                        padding: 15px; 
                        border-radius: 5px; 
                    }
                    .agent-result h1, .agent-result h2, .agent-result h3 { 
                        margin: 15px 0 10px 0; 
                        color: #1f2937; 
                    }
                    .agent-result h1 { font-size: 18px; }
                    .agent-result h2 { font-size: 16px; }
                    .agent-result h3 { font-size: 14px; }
                    .agent-result ul { 
                        margin: 10px 0; 
                        padding-left: 20px; 
                    }
                    .agent-result li { 
                        margin: 5px 0; 
                    }
                    .agent-result p { 
                        margin: 8px 0; 
                    }
                    .agent-result strong { 
                        font-weight: bold; 
                        color: #1f2937; 
                    }
                    .agent-result em { 
                        font-style: italic; 
                    }
                    .agent-result code { 
                        font-family: 'Courier New', monospace; 
                        background: #f5f5f5; 
                        padding: 2px 4px; 
                        border-radius: 2px; 
                        font-size: 12px; 
                    }
                    .agent-result pre { 
                        background: #f5f5f5; 
                        padding: 10px; 
                        border-radius: 3px; 
                        margin: 10px 0; 
                        overflow-x: auto; 
                        font-family: 'Courier New', monospace; 
                    }
                    @media print { 
                        body { margin: 0; } 
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="no-print" style="text-align: center; margin-bottom: 20px;">
                    <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-right: 10px;">Print/Save as PDF</button>
                    <button onclick="window.close()" style="background: #6b7280; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">Close</button>
                </div>
                
                <h1>Mindflow Workflow Results</h1>
                <p><strong>Generated:</strong> ${date}</p>
                <p><strong>Execution Mode:</strong> ${this.orchestrator.executionMode}</p>
                <p><strong>Total Agents:</strong> ${results.length}</p>
                
                ${results.map((result, index) => `
                    <div class="agent-result">
                        <h2>${index + 1}. ${result.name}</h2>
                        <p><strong>Role:</strong> ${result.role}</p>
                        <p><strong>Status:</strong> ${this.getStatusText(result.status)}</p>
                        <p><strong>${result.error ? 'Error:' : 'Output:'}</strong></p>
                        <div>${result.error ? this.escapeHtml(result.error) : (result.output ? this.convertMarkdownToHtmlForPdf(result.output) : 'No output generated')}</div>
                    </div>
                `).join('')}
            </body>
            </html>
        `;
        
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        printWindow.print();
    }



    getStatusText(status) {
        const statusMap = {
            'idle': 'Idle',
            'running': 'Running',
            'completed': 'Completed',
            'error': 'Error'
        };
        return statusMap[status] || 'Unknown';
    }

    cleanTextForPdf(text) {
        if (!text) return '';
        
        // Remove HTML tags
        let cleaned = text.replace(/<[^>]*>/g, '');
        
        // Convert HTML entities
        cleaned = cleaned.replace(/&nbsp;/g, ' ');
        cleaned = cleaned.replace(/&amp;/g, '&');
        cleaned = cleaned.replace(/&lt;/g, '<');
        cleaned = cleaned.replace(/&gt;/g, '>');
        cleaned = cleaned.replace(/&quot;/g, '"');
        
        // Normalize whitespace
        cleaned = cleaned.replace(/\s+/g, ' ');
        cleaned = cleaned.trim();
        
        return cleaned;
    }

    convertMarkdownToHtmlForPdf(text) {
        if (!text) return '';
        
        // Escape HTML first to prevent XSS
        let html = this.escapeHtml(text);
        
        // Convert markdown to HTML for PDF
        // Headers
        html = html.replace(/^### (.*$)/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gm, '<h1>$1</h1>');
        
        // Bold and Italic
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Lists - handle nested lists
        html = html.replace(/^\*   (.*$)/gm, '<li style="margin-left: 20px;">$1</li>');
        html = html.replace(/^\* (.*$)/gm, '<li>$1</li>');
        
        // Wrap consecutive list items in ul tags
        html = html.replace(/(<li.*?<\/li>\s*)+/g, (match) => {
            return '<ul>' + match + '</ul>';
        });
        
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre style="background: #f5f5f5; padding: 10px; border-radius: 3px; font-family: monospace; white-space: pre-wrap;"><code>$1</code></pre>');
        
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code style="background: #f5f5f5; padding: 2px 4px; border-radius: 2px; font-family: monospace;">$1</code>');
        
        // Line breaks and paragraphs
        html = html.replace(/\n\n/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        
        // Wrap in paragraph if not already wrapped
        if (!html.startsWith('<')) {
            html = '<p>' + html + '</p>';
        }
        
        return html;
    }

    async copyResults() {
        const results = this.orchestrator.getResults();
        const text = results.map(result => 
            `${result.name} (${result.status}):\n${result.output || result.error || 'No output'}\n`
        ).join('\n');
        
        try {
            await navigator.clipboard.writeText(text);
            // Show temporary feedback
            const btn = document.getElementById('copyBtn');
            const originalText = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => btn.textContent = originalText, 1000);
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
        }
    }
}

// Initialize popup manager when DOM is loaded
window.popupManager = null;
document.addEventListener('DOMContentLoaded', () => {
    window.popupManager = new PopupManager();
});
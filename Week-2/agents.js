// Agent class and orchestrator management

class Agent {
    constructor(id, name, role, prompt, inputType) {
        this.id = id;
        this.name = name;
        this.role = role;
        this.prompt = prompt;
        this.inputType = inputType;
        this.status = 'idle';
        this.output = null;
        this.error = null;
    }

    async execute(input, apiKey) {
        this.status = 'running';
        this.error = null;
        
        try {
            const response = await this.callGemini(input, apiKey);
            this.output = response;
            this.status = 'completed';
            return response;
        } catch (error) {
            this.error = error.message;
            this.status = 'error';
            throw error;
        }
    }

    async callGemini(input, apiKey) {
        if (!apiKey) {
            throw new Error('Google Gemini API key not configured');
        }

        const prompt = this.buildPrompt(input);
        
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `You are a ${this.role} agent. ${this.prompt}\n\nInput: ${input}`
                    }]
                }],
                generationConfig: {
                    temperature: 0.7,
                    topK: 40,
                    topP: 0.95,
                    maxOutputTokens: 1000
                },
                safetySettings: [
                    {
                        category: "HARM_CATEGORY_HARASSMENT",
                        threshold: "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        category: "HARM_CATEGORY_HATE_SPEECH",
                        threshold: "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        category: "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold: "BLOCK_MEDIUM_AND_ABOVE"
                    },
                    {
                        category: "HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold: "BLOCK_MEDIUM_AND_ABOVE"
                    }
                ]
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error?.message || 'Google Gemini API request failed');
        }

        const data = await response.json();
        
        if (!data.candidates || !data.candidates[0] || !data.candidates[0].content) {
            throw new Error('No response generated from Gemini API');
        }
        
        return data.candidates[0].content.parts[0].text;
    }

    buildPrompt(input) {
        return `${this.prompt}\n\nInput: ${input}`;
    }

    reset() {
        this.status = 'idle';
        this.output = null;
        this.error = null;
    }
}

class WorkflowOrchestrator {
    constructor() {
        this.agents = [];
        this.executionMode = 'sequential';
        this.isRunning = false;
    }

    addAgent(agent) {
        this.agents.push(agent);
    }

    removeAgent(agentId) {
        this.agents = this.agents.filter(agent => agent.id !== agentId);
    }

    getAgent(agentId) {
        return this.agents.find(agent => agent.id === agentId);
    }

    setExecutionMode(mode) {
        this.executionMode = mode;
    }

    async runWorkflow(initialInput, apiKey) {
        if (this.isRunning) {
            throw new Error('Workflow is already running');
        }

        if (this.agents.length === 0) {
            throw new Error('No agents configured');
        }

        this.isRunning = true;
        
        // Reset all agents
        this.agents.forEach(agent => agent.reset());

        try {
            if (this.executionMode === 'sequential') {
                await this.runSequential(initialInput, apiKey);
            } else {
                await this.runParallel(initialInput, apiKey);
            }
        } finally {
            this.isRunning = false;
        }
    }

    async runWorkflowWithSteps(workflowSteps, initialInput, apiKey) {
        if (this.isRunning) {
            throw new Error('Workflow is already running');
        }

        if (workflowSteps.length === 0) {
            throw new Error('No workflow steps configured');
        }

        this.isRunning = true;
        
        // Reset all agents
        this.agents.forEach(agent => agent.reset());

        try {
            if (this.executionMode === 'sequential') {
                await this.runSequentialWithSteps(workflowSteps, initialInput, apiKey);
            } else {
                await this.runParallelWithSteps(workflowSteps, initialInput, apiKey);
            }
        } finally {
            this.isRunning = false;
        }
    }

    async runSequential(initialInput, apiKey) {
        let currentInput = initialInput;

        for (const agent of this.agents) {
            try {
                const output = await agent.execute(currentInput, apiKey);
                currentInput = output; // Pass output to next agent
            } catch (error) {
                console.error(`Agent ${agent.name} failed:`, error);
                // Continue with remaining agents even if one fails
            }
        }
    }

    async runParallel(initialInput, apiKey) {
        const promises = this.agents.map(agent => 
            agent.execute(initialInput, apiKey).catch(error => {
                console.error(`Agent ${agent.name} failed:`, error);
                return null;
            })
        );

        await Promise.all(promises);
    }

    async runSequentialWithSteps(workflowSteps, initialInput, apiKey) {
        let currentInput = initialInput;

        for (const agentId of workflowSteps) {
            const agent = this.getAgent(agentId);
            if (!agent) {
                console.error(`Agent with ID ${agentId} not found`);
                continue;
            }

            try {
                const output = await agent.execute(currentInput, apiKey);
                currentInput = output; // Pass output to next agent
            } catch (error) {
                console.error(`Agent ${agent.name} failed:`, error);
                // Continue with remaining agents even if one fails
            }
        }
    }

    async runParallelWithSteps(workflowSteps, initialInput, apiKey) {
        const promises = workflowSteps.map(agentId => {
            const agent = this.getAgent(agentId);
            if (!agent) {
                console.error(`Agent with ID ${agentId} not found`);
                return Promise.resolve(null);
            }
            
            return agent.execute(initialInput, apiKey).catch(error => {
                console.error(`Agent ${agent.name} failed:`, error);
                return null;
            });
        });

        await Promise.all(promises);
    }

    getResults() {
        return this.agents.map(agent => ({
            id: agent.id,
            name: agent.name,
            role: agent.role,
            status: agent.status,
            output: agent.output,
            error: agent.error
        }));
    }

    async saveToStorage() {
        const agentData = this.agents.map(agent => ({
            id: agent.id,
            name: agent.name,
            role: agent.role,
            prompt: agent.prompt,
            inputType: agent.inputType
        }));

        await chrome.storage.local.set({
            agents: agentData,
            executionMode: this.executionMode
        });
    }

    async loadFromStorage() {
        const data = await chrome.storage.local.get(['agents', 'executionMode']);
        
        if (data.agents) {
            this.agents = data.agents.map(agentData => 
                new Agent(
                    agentData.id,
                    agentData.name,
                    agentData.role,
                    agentData.prompt,
                    agentData.inputType
                )
            );
        }

        if (data.executionMode) {
            this.executionMode = data.executionMode;
        }
    }
}

// Export for use in popup.js
window.Agent = Agent;
window.WorkflowOrchestrator = WorkflowOrchestrator;
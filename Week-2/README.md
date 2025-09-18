# Mindflow

A Chrome extension for creating, configuring, and running multiple AI agents that work together in intelligent workflows.

## Features

- **Agent Management**: Create and configure multiple AI agents with different roles
- **Workflow Orchestration**: Run agents sequentially or in parallel
- **Google Gemini Integration**: Uses Gemini 2.0 Flash for agent reasoning
- **Result Export**: Export results as JSON or copy to clipboard
- **Persistent Storage**: Agents and settings are saved locally

## Installation

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" in the top right
3. Click "Load unpacked" and select the extension folder
4. The extension icon will appear in your toolbar

## Setup

1. Click the extension icon to open the popup
2. Click the settings gear icon
3. Enter your Google Gemini API key (get it from [Google AI Studio](https://aistudio.google.com/app/apikey))
4. Click "Save"

## Usage

### Creating Agents

1. Click "Add Agent" in the popup
2. Configure the agent:
   - **Name**: A descriptive name for the agent
   - **Role**: Choose from predefined roles or select "Custom"
   - **Prompt Template**: Instructions for what the agent should do
   - **Input Type**: How the agent receives input
3. Click "Save Agent"

### Running Workflows

1. Configure your agents
2. Choose execution mode:
   - **Sequential**: Agents run one after another, passing output to the next
   - **Parallel**: All agents run simultaneously with the same input
3. Click "Run Workflow"
4. Enter the initial input when prompted
5. View results in the Output Panel

### Agent Roles

- **Scraper**: Extract and structure information
- **Summarizer**: Create concise summaries
- **Analyzer**: Analyze and provide insights
- **Compliance Checker**: Check for compliance issues
- **Custom**: Define your own role

## Example Workflow

1. **Scraper Agent**: Extract key information from a webpage
2. **Summarizer Agent**: Create a summary of the extracted content
3. **Analyzer Agent**: Analyze the summary for insights
4. **Compliance Checker**: Check if content meets specific guidelines

## File Structure

```
├── manifest.json          # Extension manifest (MV3)
├── popup.html             # Main UI
├── popup.js               # UI logic and event handling
├── agents.js              # Agent classes and orchestrator
├── background.js          # Service worker
├── styles.css             # Custom styles
└── README.md              # This file
```

## API Key Security

Your Google Gemini API key is stored locally in Chrome's storage and never transmitted except to Google's Gemini API endpoints.

## Troubleshooting

- **"API key not configured"**: Make sure you've entered your Google Gemini API key in settings
- **"No agents configured"**: Add at least one agent before running a workflow
- **API errors**: Check that your API key is valid and has sufficient credits

## Development

The extension uses:
- Manifest V3
- Tailwind CSS for styling
- Chrome Storage API for persistence
- Google Gemini 2.0 Flash API
- Modern JavaScript (ES6+)

## License

MIT License
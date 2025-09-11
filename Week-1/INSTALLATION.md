# Installation Guide - Smart Paper & Doc Summarizer

## Quick Start

### Step 1: Download the Extension
1. Download or clone this repository
2. Navigate to the `Week-1` folder
3. Ensure all files are present:
   - `manifest.json`
   - `popup.html`
   - `popup.js`
   - `background.js`
   - `content.js`
   - `README.md`

### Step 2: Load in Chrome
1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `Week-1` folder
6. The extension should appear in your extensions list

### Step 3: Configure API Key
1. Click the extension icon in the Chrome toolbar
2. Enter your Google AI API key (starts with "AIza")
3. Click "Save API Key"
4. The main interface will appear

### Step 4: Start Using
1. Navigate to any webpage or upload a PDF
2. Click "Use Current Page" or "Upload PDF"
3. Select your focus mode (Technical, Legal, Privacy, Biometrics)
4. Click "Summarize & Generate Research Steps"
5. Review the 5-step research analysis
6. Export results as needed

## Requirements

### System Requirements
- Chrome browser version 88 or higher
- Internet connection
- Google AI API key (Gemini)

### API Key Setup
1. Visit [Google AI Studio](https://aistudio.google.com/)
2. Create an account or sign in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (starts with "AIza")
6. Paste it in the extension popup

## Troubleshooting

### Extension Not Loading
- Ensure all files are in the same folder
- Check that `manifest.json` is valid
- Try refreshing the extensions page
- Check Chrome console for errors

### API Key Issues
- Verify the key starts with "AIza"
- Check that you have Google AI credits
- Ensure the key has proper permissions
- Try creating a new API key

### Content Extraction Problems
- Make sure the page is fully loaded
- Try refreshing the page
- Check if the site blocks content extraction
- Use manual text input as fallback

### PDF Upload Issues
- Ensure the file is a valid PDF
- Check file size (should be reasonable)
- Try with a different PDF file
- Use manual text input as alternative

## Features Overview

### Content Sources
- **Current Page**: Extract text from any webpage
- **PDF Upload**: Upload and analyze PDF documents
- **Manual Input**: Paste content directly

### Focus Modes
- **Technical**: Algorithms, optimization, experiments
- **Legal**: Compliance, regulations, policy
- **Privacy**: Data protection, anonymization, safe AI
- **Biometrics**: Biometric methods, liveness detection, fairness

### Export Options
- **Copy**: Copy results to clipboard
- **Markdown**: Export as .md file
- **PDF**: Generate PDF report

## Security Notes

- API keys are stored securely in Chrome's sync storage
- No content is sent to external servers except Google AI
- All processing is done client-side when possible
- Extension follows Chrome security best practices

## Support

For technical issues:
1. Check this installation guide
2. Review the main README.md
3. Check Chrome console for error messages
4. Contact course instructors for help

## Updates

To update the extension:
1. Download the latest version
2. Remove the old extension from Chrome
3. Load the new version following Step 2 above
4. Your API key and settings will be preserved

---

**Ready to start analyzing research papers with AI! 🚀**

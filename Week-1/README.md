# Smart Paper & Doc Summarizer - Chrome Extension

A comprehensive Chrome extension that provides AI-powered research paper and document summarization with structured research proposal generation.

## Features

### Core Functionality
- **Multi-format Support**: Processes PDFs, web pages, research papers, and legal documents
- **AI-Powered Analysis**: Uses Google Gemini 1.5 Flash for intelligent content analysis
- **Structured Research Process**: Follows a 5-step research methodology
- **Focus Modes**: Specialized analysis for Technical, Legal, Privacy, and Biometrics content

### Research Process (Steps 1-5)
1. **New Research Problem Identification**: Identifies and proposes new, unsolved research problems based on the paper's content, limitations, and future work.
2. **Research Design for the New Problem**: Suggests appropriate methodology and approach for the proposed new research problem.
3. **Data Collection for the New Problem**: Recommends specific instruments, tools, and methods for data collection for the new research problem.
4. **Sampling Strategies for the New Problem**: Proposes sampling methods, target populations, and sample size considerations for the new research problem.
5. **Research Proposal for the New Problem**: Generates a mini research proposal for the new problem, including objectives, methodology, expected contributions, and timeline

### Focus Modes
- **🔬 Technical**: Emphasizes algorithms, optimization, and experimental methodologies
- **⚖️ Legal**: Focuses on compliance, regulations, and policy implications
- **🔒 Privacy**: Highlights data protection, anonymization, and safe AI practices
- **👤 Biometrics**: Concentrates on biometric methods, liveness detection, and fairness

### User Interface
- **Modern Design**: Clean, responsive UI built with Tailwind CSS
- **Collapsible Sections**: Organized display of research analysis results
- **Export Options**: Copy to clipboard, export as Markdown, or generate PDF
- **Real-time Processing**: Live status updates and error handling

## Installation

### Prerequisites
- Chrome browser (version 88+)
- Google AI API key (Gemini)
- Internet connection

### Setup Instructions
1. Download or clone this repository
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" in the top right
4. Click "Load unpacked" and select the extension folder
5. Click the extension icon in the toolbar
6. Enter your Google AI API key when prompted

## File Structure

```
Week-1/
├── manifest.json          # Extension configuration (Manifest V3)
├── popup.html             # Main UI with Tailwind CSS
├── popup.js               # User interactions and API calls
├── background.js          # Service worker for persistent state
├── content.js             # Content extraction and page analysis
├── icons/                 # Extension icons (16px, 32px, 48px, 128px)
└── README.md              # This file
```

## Usage

### Basic Workflow
1. **Configure API Key**: Enter your Google AI API key in the extension popup
2. **Select Content Source**:
   - Use current page content
   - Upload a PDF file
   - Paste content manually
3. **Choose Focus Mode**: Select the appropriate analysis focus
4. **Generate Analysis**: Click "Summarize & Generate Research Steps"
5. **Review Results**: Expand each step to view detailed analysis
6. **Export Results**: Copy, export as Markdown, or generate PDF

### Content Extraction
- **Web Pages**: Automatically extracts main content from academic sites, news articles, and research papers
- **PDFs**: Direct PDF text extraction using PDF.js library
- **Manual Input**: Supports direct text input for custom content

### API Integration
- **Google Gemini 1.5 Flash**: Primary language model for analysis
- **Structured Prompts**: Custom prompts for each focus mode and research step
- **Error Handling**: Robust error handling with user-friendly messages

## Technical Details

### Architecture
- **Manifest V3**: Latest Chrome extension standard
- **Service Worker**: Background script for persistent state management
- **Content Scripts**: Page content extraction and analysis
- **Popup Interface**: User interaction and result display

### Security Features
- **API Key Storage**: Secure storage using Chrome's sync storage
- **Input Validation**: Comprehensive validation of user inputs
- **Error Handling**: Graceful error handling and user feedback
- **Content Sanitization**: Safe content extraction and processing

### Performance Optimizations
- **Lazy Loading**: Content extraction only when needed
- **Caching**: Intelligent caching of extracted content
- **Async Processing**: Non-blocking operations for better UX
- **Memory Management**: Efficient memory usage and cleanup

## Development

### Prerequisites
- Node.js (for development tools)
- Chrome browser with developer tools
- Google AI API key for testing

### Local Development
1. Clone the repository
2. Make changes to the source files
3. Load the extension in Chrome developer mode
4. Test functionality and debug using Chrome DevTools

### Building for Production
1. Ensure all files are properly structured
2. Test all functionality thoroughly
3. Create a ZIP file of the extension folder
4. Submit to Chrome Web Store (if publishing)

## API Usage

### Google Gemini Integration
The extension uses Google's Gemini 1.5 Flash model with the following configuration:
- **Model**: gemini-1.5-flash
- **Temperature**: 0.7 (balanced creativity and consistency)
- **Max Output Tokens**: 4000 (sufficient for detailed analysis)
- **Top P**: 0.8 (nucleus sampling)
- **Top K**: 10 (top-k sampling)
- **System Prompt**: Expert research analyst persona

### Rate Limiting
- Respects Google AI's rate limits
- Implements retry logic for failed requests
- Provides user feedback for API issues

## Troubleshooting

### Common Issues
1. **API Key Not Working**: Verify the key starts with "AIza" and has sufficient credits
2. **Content Not Extracting**: Ensure the page is fully loaded and accessible
3. **PDF Upload Fails**: Check file size and format (PDF only)
4. **Export Not Working**: Ensure popup blockers are disabled

### Error Messages
- **"Please configure your API key first"**: Set up Google AI API key
- **"Failed to extract content"**: Try refreshing the page or uploading manually
- **"API request failed"**: Check internet connection and API key validity

## Contributing

### Development Guidelines
- Follow Chrome extension best practices
- Maintain clean, commented code
- Test all functionality before submitting
- Update documentation for new features

### Code Style
- Use modern JavaScript (ES6+)
- Follow consistent naming conventions
- Implement proper error handling
- Add comments for complex logic

## License

This project is provided for educational purposes as part of The School of AI's EAG V2 course.

## Support

For issues and questions:
- Check the troubleshooting section
- Review Chrome extension documentation
- Contact course instructors for technical support

---

**Built with ❤️ for The School of AI - EAG V2 Course**

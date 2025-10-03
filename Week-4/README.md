# 🎨 Paint Automation Agent

An **MCP-powered autonomous agent** that controls Microsoft Paint through natural language commands using Gemini AI for decision-making.

## 🚀 Features

### **Autonomous Paint Control**
- **Natural Language Interface**: "Open Paint and draw a rectangle, then write Hello AI inside it"
- **Multi-Step Workflows**: Agent decides when to call which functions
- **Smart Coordination**: Handles Paint opening, drawing, and text placement automatically

### **Available Paint Tools**
- `open_paint()` - Opens and maximizes Paint on secondary monitor
- `draw_rectangle(x1, y1, x2, y2)` - Draws rectangles with specified coordinates
- `draw_circle(center_x, center_y, radius)` - Draws circles
- `add_text_in_paint(text)` - Adds text at optimal locations
- `clear_canvas()` - Clears the Paint canvas
- `save_paint_file(filename)` - Saves the current artwork

### **Mathematical Tools** (Legacy)
- 20+ math functions (add, multiply, factorial, trigonometry, etc.)
- String processing (ASCII conversion, exponentials)
- List operations and Fibonacci sequences

## 🛠️ Setup

### **Requirements**
```bash
pip install mcp fastmcp python-dotenv google-generativeai pywinauto
```

### **Environment Setup**
Create `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### **System Requirements**
- **Windows**: Uses `pywinauto` and `win32gui` for Paint control
- **Multi-Monitor Setup**: Optimized for secondary monitor placement
- **Microsoft Paint**: Must be available on the system

## 🎯 Usage

### **Run the Agent**
```bash
python talk2mcp.py
```

### **Example Queries**
```
🎨 Enter your Paint automation request: Open Paint and draw a rectangle, then write Hello AI inside it.
```

### **Expected Workflow**
1. **Agent Analysis**: Gemini AI analyzes the natural language request
2. **Function Planning**: Decides which Paint functions to call in sequence
3. **Autonomous Execution**: 
   - `FUNCTION_CALL: open_paint`
   - `FUNCTION_CALL: draw_rectangle|780|380|1140|700`
   - `FUNCTION_CALL: add_text_in_paint|Hello AI`
   - `FINAL_ANSWER: [Done]`

## 🔧 Architecture

### **MCP Client (`talk2mcp.py`)**
- Connects to MCP server via stdio
- Uses **Gemini 2.0 Flash** for AI reasoning
- Iterative decision-making process
- Handles function calls and coordinates workflow

### **MCP Server (`mcp_server.py`)**
- **FastMCP** framework implementation
- Paint automation tools using `pywinauto`
- Multi-monitor coordinate handling
- Error handling and recovery

### **Agent Flow**
```
User Query → Gemini AI → Function Decisions → MCP Tools → Paint Actions → Result
```

## 📋 Example Queries

### **Basic Paint Operations**
```
"Open Paint and draw a rectangle, then write Hello AI inside it."
"Draw a box in Paint and label it Trading Bot."
"Create a rectangle and add text MCP Agent inside."
```

### **Advanced Operations**
```
"Open Paint, draw a circle, and add text Welcome to MCP."
"Draw a shape in Paint and add the text Autonomous AI."
"Clear the canvas, draw a rectangle, and write Testing 123."
```

### **Multi-Step Workflows**
```
"Open Paint, draw two rectangles, add different text in each."
"Create a circle, then a rectangle, and label them Shape 1 and Shape 2."
```

## 🎨 Coordinate System

### **Default Rectangle Coordinates**
- **x1=780, y1=380** (top-left)
- **x2=1140, y2=700** (bottom-right)
- Optimized for **1920x1080 secondary monitor**

### **Multi-Monitor Setup**
- Automatically detects primary monitor width
- Positions Paint on secondary monitor
- Adjusts coordinates for multi-screen environments

## 🔍 Debugging

### **Enable Verbose Logging**
The server prints detailed function calls:
```
CALLED: open_paint() -> str:
CALLED: draw_rectangle(x1=780, y1=380, x2=1140, y2=700) -> str:
CALLED: add_text_in_paint(text='Hello AI') -> str:
```

### **Common Issues**
1. **Paint not opening**: Check Windows permissions
2. **Coordinates off**: Adjust for your monitor setup
3. **Text placement**: Modify text coordinates in `add_text_in_paint`

## 🚀 Testing

### **Run Test Suite**
```bash
python test_paint_agent.py
```

### **Manual Testing**
1. Ensure Paint is not already running
2. Run `python talk2mcp.py`
3. Enter a natural language query
4. Watch the autonomous execution

## 🎯 Key Innovations

### **1. Autonomous Decision Making**
- **No Hardcoded Workflows**: Agent decides function sequence
- **Context-Aware**: Understands when Paint needs to be opened first
- **Error Recovery**: Handles failures gracefully

### **2. Natural Language Interface**
- **Flexible Queries**: Multiple ways to express the same intent
- **Intent Recognition**: Gemini AI parses complex requests
- **Multi-Step Planning**: Breaks down complex tasks automatically

### **3. MCP Integration**
- **Tool Discovery**: Dynamically loads available functions
- **Type Safety**: Proper parameter type conversion
- **Error Handling**: Robust error reporting and recovery

## 🔮 Future Enhancements

### **Cross-Platform Support**
- **Linux**: `xdotool` integration
- **macOS**: `pyautogui` implementation
- **Web**: Browser-based drawing tools

### **Advanced Drawing**
- **Color selection tools**
- **Line and polygon drawing**
- **Image import/export**
- **Layer management**

### **AI Improvements**
- **Visual feedback**: Screenshot analysis
- **Coordinate optimization**: Smart placement algorithms
- **Style preferences**: User-customizable drawing styles

---

## 🎉 Example Session

```bash
$ python talk2mcp.py

🎨 Enter your Paint automation request: Draw a rectangle and write MCP Agent inside

🚀 Processing query: Draw a rectangle and write MCP Agent inside

--- Iteration 1 ---
LLM Response: FUNCTION_CALL: open_paint

--- Iteration 2 ---
LLM Response: FUNCTION_CALL: draw_rectangle|780|380|1140|700

--- Iteration 3 ---
LLM Response: FUNCTION_CALL: add_text_in_paint|MCP Agent

--- Iteration 4 ---
LLM Response: FINAL_ANSWER: [Done]

=== 🎨 Paint Automation Complete ===
✅ Final Result: [Done]

📋 Execution Summary:
  1. In the 1 iteration you called open_paint with {} parameters, and the function returned Paint opened successfully and maximized.
  2. In the 2 iteration you called draw_rectangle with {'x1': 780, 'y1': 380, 'x2': 1140, 'y2': 700} parameters, and the function returned Rectangle drawn successfully from (780,380) to (1140,700).
  3. In the 3 iteration you called add_text_in_paint with {'text': 'MCP Agent'} parameters, and the function returned Text 'MCP Agent' added successfully in Paint.
```

**Result**: Paint opens, draws a rectangle, and adds "MCP Agent" text inside it - all autonomously! 🎨✨
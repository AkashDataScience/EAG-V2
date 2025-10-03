# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
from pywinauto.application import Application
import win32gui
import win32con
import time
from win32api import GetSystemMetrics

# instantiate an MCP server client
mcp = FastMCP("PaintAutomationServer")

# Global variable to track Paint application
paint_app = None

# DEFINE TOOLS

#addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print("CALLED: add(a: int, b: int) -> int:")
    return int(a + b)

@mcp.tool()
def add_list(l: list) -> int:
    """Add all numbers in a list"""
    print("CALLED: add(l: list) -> int:")
    return sum(l)

# subtraction tool
@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    print("CALLED: subtract(a: int, b: int) -> int:")
    return int(a - b)

# multiplication tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    print("CALLED: multiply(a: int, b: int) -> int:")
    return int(a * b)

#  division tool
@mcp.tool() 
def divide(a: int, b: int) -> float:
    """Divide two numbers"""
    print("CALLED: divide(a: int, b: int) -> float:")
    return float(a / b)

# power tool
@mcp.tool()
def power(a: int, b: int) -> int:
    """Power of two numbers"""
    print("CALLED: power(a: int, b: int) -> int:")
    return int(a ** b)

# square root tool
@mcp.tool()
def sqrt(a: int) -> float:
    """Square root of a number"""
    print("CALLED: sqrt(a: int) -> float:")
    return float(a ** 0.5)

# cube root tool
@mcp.tool()
def cbrt(a: int) -> float:
    """Cube root of a number"""
    print("CALLED: cbrt(a: int) -> float:")
    return float(a ** (1/3))

# factorial tool
@mcp.tool()
def factorial(a: int) -> int:
    """factorial of a number"""
    print("CALLED: factorial(a: int) -> int:")
    return int(math.factorial(a))

# log tool
@mcp.tool()
def log(a: int) -> float:
    """log of a number"""
    print("CALLED: log(a: int) -> float:")
    return float(math.log(a))

# remainder tool
@mcp.tool()
def remainder(a: int, b: int) -> int:
    """remainder of two numbers divison"""
    print("CALLED: remainder(a: int, b: int) -> int:")
    return int(a % b)

# sin tool
@mcp.tool()
def sin(a: int) -> float:
    """sin of a number"""
    print("CALLED: sin(a: int) -> float:")
    return float(math.sin(a))

# cos tool
@mcp.tool()
def cos(a: int) -> float:
    """cos of a number"""
    print("CALLED: cos(a: int) -> float:")
    return float(math.cos(a))

# tan tool
@mcp.tool()
def tan(a: int) -> float:
    """tan of a number"""
    print("CALLED: tan(a: int) -> float:")
    return float(math.tan(a))

# mine tool
@mcp.tool()
def mine(a: int, b: int) -> int:
    """special mining tool"""
    print("CALLED: mine(a: int, b: int) -> int:")
    return int(a - b - b)

@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    print("CALLED: create_thumbnail(image_path: str) -> Image:")
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")

@mcp.tool()
def strings_to_chars_to_int(string: str) -> list[int]:
    """Return the ASCII values of the characters in a word"""
    print("CALLED: strings_to_chars_to_int(string: str) -> list[int]:")
    return [int(ord(char)) for char in string]

@mcp.tool()
def int_list_to_exponential_sum(int_list: list) -> float:
    """Return sum of exponentials of numbers in a list"""
    print("CALLED: int_list_to_exponential_sum(int_list: list) -> float:")
    return sum(math.exp(i) for i in int_list)

@mcp.tool()
def fibonacci_numbers(n: int) -> list:
    """Return the first n Fibonacci Numbers"""
    print("CALLED: fibonacci_numbers(n: int) -> list:")
    if n <= 0:
        return []
    fib_sequence = [0, 1]
    for _ in range(2, n):
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence[:n]

@mcp.tool()
def draw_circle(center_x: int, center_y: int, radius: int) -> str:
    """Draw a circle in Paint with center at (center_x, center_y) and given radius"""
    global paint_app
    print(f"CALLED: draw_circle(center_x={center_x}, center_y={center_y}, radius={radius}) -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        # Method 1: Try finding ellipse/circle tool by automation ID
        circle_selected = False
        
        try:
            # Try to find Rectangle tool by title and control type
            oval_tool = paint_window.child_window(title="Oval", control_type="ListItem")
            if oval_tool.exists():
                oval_tool.click_input()
                circle_selected = True
                print("SUCCESS: Rectangle tool selected via automation ID")
            else:
                # Try alternative titles
                alt_titles = ["Circle", "Oval tool", "Oval shape"]
                for title in alt_titles:
                    try:
                        oval_tool = paint_window.child_window(title=title, control_type="ListItem")
                        if oval_tool.exists():
                            oval_tool.click_input()
                            circle_selected = True
                            print(f"SUCCESS: Rectangle tool selected via title: {title}")
                            break
                    except:
                        continue
        except Exception as e:
            print(f"Method 1 automation ID failed: {e}")
        
        if not circle_selected:
            print("WARNING: Could not select circle tool, proceeding anyway")
        
        time.sleep(0.3)
        
        # Calculate circle bounds
        x1 = center_x - radius
        y1 = center_y - radius
        x2 = center_x + radius
        y2 = center_y + radius

        # Method 1: Use drag_mouse_input (same as working rectangle)
        print(f"Drawing circle from ({x1},{y1}) to ({x2},{y2}) using drag_mouse_input")
        
        # Hold Shift for perfect circle, then drag
        paint_window.type_keys('{VK_SHIFT down}')
        paint_window.drag_mouse_input(src=(x1, y1), dst=(x1, y1))
        paint_window.drag_mouse_input(src=(x1, y1), dst=(x2, y2))
        paint_window.type_keys('{VK_SHIFT up}')
        
        return f"Circle drawn at center ({center_x},{center_y}) with radius {radius}"
        
    except Exception as e:
        return f"Error drawing circle: {str(e)}"

@mcp.tool()
def clear_canvas() -> str:
    """Clear the Paint canvas"""
    global paint_app
    print("CALLED: clear_canvas() -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        # Use Ctrl+A to select all, then Delete
        paint_window.type_keys('^a')  # Ctrl+A
        time.sleep(0.2)
        paint_window.type_keys('{DELETE}')
        time.sleep(0.2)
        
        return "Canvas cleared successfully"
        
    except Exception as e:
        return f"Error clearing canvas: {str(e)}"

@mcp.tool()
def save_paint_file(filename: str) -> str:
    """Save the Paint file with given filename"""
    global paint_app
    print(f"CALLED: save_paint_file(filename='{filename}') -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        # Use Ctrl+S to save
        paint_window.type_keys('^s')
        time.sleep(1.0)
        
        # Type filename
        paint_window.type_keys(filename, with_spaces=True)
        time.sleep(0.3)
        
        # Press Enter to save
        paint_window.type_keys('{ENTER}')
        time.sleep(0.5)
        
        return f"File saved as '{filename}'"
        
    except Exception as e:
        return f"Error saving file: {str(e)}"

@mcp.tool()
def debug_paint_controls() -> str:
    """Debug function to list all available controls in Paint for finding correct automation IDs"""
    global paint_app
    print("CALLED: debug_paint_controls() -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        debug_info = []
        debug_info.append("=== Paint Window Controls Debug ===")
        
        # List all child windows
        try:
            children = paint_window.children()
            debug_info.append(f"Found {len(children)} child windows:")
            
            for i, child in enumerate(children[:10]):  # Limit to first 10
                try:
                    class_name = child.class_name()
                    window_text = child.window_text()
                    control_type = getattr(child, 'control_type', 'Unknown')
                    debug_info.append(f"  {i+1}. Class: {class_name}, Text: '{window_text}', Type: {control_type}")
                except:
                    debug_info.append(f"  {i+1}. Error reading child info")
        except Exception as e:
            debug_info.append(f"Error listing children: {e}")
        
        # List all descendants with specific control types
        try:
            debug_info.append("\n=== Buttons ===")
            buttons = paint_window.descendants(control_type="Button")
            for i, button in enumerate(buttons[:15]):  # Limit to first 15
                try:
                    text = button.window_text()
                    debug_info.append(f"  Button {i+1}: '{text}'")
                except:
                    debug_info.append(f"  Button {i+1}: Error reading")
        except Exception as e:
            debug_info.append(f"Error listing buttons: {e}")
        
        try:
            debug_info.append("\n=== ListItems ===")
            listitems = paint_window.descendants(control_type="ListItem")
            for i, item in enumerate(listitems[:15]):  # Limit to first 15
                try:
                    text = item.window_text()
                    debug_info.append(f"  ListItem {i+1}: '{text}'")
                except:
                    debug_info.append(f"  ListItem {i+1}: Error reading")
        except Exception as e:
            debug_info.append(f"Error listing listitems: {e}")
        
        result = "\n".join(debug_info)
        print(result)  # Also print to console
        return result
        
    except Exception as e:
        return f"Error in debug function: {str(e)}"


@mcp.tool()
def draw_rectangle(x1: int, y1: int, x2: int, y2: int) -> str:
    """Draw a rectangle in Paint from (x1,y1) to (x2,y2)"""
    global paint_app
    print(f"CALLED: draw_rectangle(x1={x1}, y1={y1}, x2={x2}, y2={y2}) -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        # Get the Paint window
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        # Method 1: Try finding rectangle tool by automation ID or control name
        rectangle_selected = False
        
        try:
            # Try to find Rectangle tool by title and control type
            rect_tool = paint_window.child_window(title="Rectangle", control_type="ListItem")
            if rect_tool.exists():
                rect_tool.click_input()
                rectangle_selected = True
                print("SUCCESS: Rectangle tool selected via automation ID")
            else:
                # Try alternative titles
                alt_titles = ["Rect", "Rectangle tool", "Rectangle shape"]
                for title in alt_titles:
                    try:
                        rect_tool = paint_window.child_window(title=title, control_type="ListItem")
                        if rect_tool.exists():
                            rect_tool.click_input()
                            rectangle_selected = True
                            print(f"SUCCESS: Rectangle tool selected via title: {title}")
                            break
                    except:
                        continue
        except Exception as e:
            print(f"Method 1 automation ID failed: {e}")
        
        if not rectangle_selected:
            print("WARNING: Could not select rectangle tool, proceeding with drawing anyway")
        
        time.sleep(0.3)
        
        # Validate coordinates
        if x1 >= x2 or y1 >= y2:
            return f"Error: Invalid coordinates. x1({x1}) must be < x2({x2}) and y1({y1}) must be < y2({y2})"
        
        # Method 1: Use drag_mouse_input (working method)
        print(f"Drawing rectangle from ({x1},{y1}) to ({x2},{y2}) using drag_mouse_input")
        
        # Drag inside Paint using window coordinates
        paint_window.drag_mouse_input(src=(x1, y1), dst=(x1, y1))
        paint_window.drag_mouse_input(src=(x1, y1), dst=(x2, y2))
        
        return f"Rectangle drawn successfully from ({x1},{y1}) to ({x2},{y2})"
        
    except Exception as e:
        return f"Error drawing rectangle: {str(e)}"

@mcp.tool()
def add_text_in_paint(text: str, x: int, y: int) -> str:
    """Add text in Paint at specified coordinates (x, y)"""
    global paint_app
    print(f"CALLED: add_text_in_paint(text='{text}', x={x}, y={y}) -> str:")
    
    try:
        if not paint_app:
            return "Error: Paint is not open. Please call open_paint first."
        
        # Get the Paint window
        paint_window = paint_app.window(class_name='MSPaintApp')
        
        paint_window.set_focus()
        
        # Method 1: Try finding text tool by automation ID
        text_selected = False
        
        try:
            # Try to find Rectangle tool by title and control type
            text_tool = paint_window.child_window(title="Text", control_type="Button")
            if text_tool.exists():
                text_tool.click_input()
                text_selected = True
                print("SUCCESS: Rectangle tool selected via automation ID")
            else:
                # Try alternative titles
                alt_titles = ["Txt", "Text tool", "Text shape"]
                for title in alt_titles:
                    try:
                        text_tool = paint_window.child_window(title=title, control_type="Button")
                        if text_tool.exists():
                            text_tool.click_input()
                            text_selected = True
                            print(f"SUCCESS: Rectangle tool selected via title: {title}")
                            break
                    except:
                        continue
        except Exception as e:
            print(f"Method 1 automation ID failed: {e}")
        
        if not text_selected:
            print("WARNING: Could not select text tool, trying direct typing")
        
        time.sleep(0.3)
        
        # Method 1: Use paint_window click (same pattern as working rectangle)
        print(f"Adding text '{text}' at position ({x}, {y}) using paint_window")
        
        # Click at text position using paint_window (same as rectangle method)
        paint_window.click_input(coords=(x, y))
        paint_window.click_input(coords=(x, y))
        time.sleep(0.3)
        
        # Type the text
        paint_window.type_keys(text, with_spaces=True)
        time.sleep(0.3)
        
        # Click outside text area to finish text entry
        paint_window.click_input(coords=(x + 200, y + 100))
        time.sleep(0.2)
        
        return f"Text '{text}' added successfully at ({x}, {y}) in Paint"
        
    except Exception as e:
        return f"Error adding text: {str(e)}"

@mcp.tool()
def open_paint() -> str:
    """Open Microsoft Paint maximized on secondary monitor"""
    global paint_app
    print("CALLED: open_paint() -> str:")
    try:
        # Check if Paint is already running
        if paint_app is not None:
            try:
                paint_window = paint_app.window(class_name='MSPaintApp')
                if paint_window.exists():
                    paint_window.set_focus()
                    return "Paint is already open and focused"
            except:
                paint_app = None  # Reset if window no longer exists
        
        # Start new Paint instance
        paint_app = Application(backend="uia").start('mspaint.exe')
        time.sleep(1.0)  # Give Paint time to fully load
        
        # Get the Paint window
        paint_window = paint_app.window(class_name='MSPaintApp')
        paint_window.wait('ready', timeout=10)
        
        # Get primary monitor width for multi-monitor setup
        primary_width = GetSystemMetrics(0)
        
        # Ensure window is focused
        paint_window.set_focus()
        
        return "Paint opened successfully"
        
    except Exception as e:
        paint_app = None
        return f"Error opening Paint: {str(e)}"
# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING THE SERVER AT AMAZING LOCATION")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution

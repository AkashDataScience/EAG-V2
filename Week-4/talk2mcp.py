import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

max_safety_iterations = 20  # Safety limit to prevent infinite loops
last_response = None
iteration = 0
iteration_response = []
consecutive_errors = 0
max_consecutive_errors = 3

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, consecutive_errors
    last_response = None
    iteration = 0
    iteration_response = []
    consecutive_errors = 0

async def main():
    reset_state()  # Reset at the start of main
    print("Starting main execution...")
    try:
        # Create a single MCP server connection
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            print("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("Session created, initializing...")
                await session.initialize()
                
                # Get available tools
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")
                

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                system_prompt = f"""You are a Math and Paint Automation Agent that can perform mathematical calculations AND control Microsoft Paint. You handle both math operations and paint workflows autonomously based on natural language queries.

Available tools:
{tools_description}

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls:
   FUNCTION_CALL: function_name|param1|param2|...
   
2. For final answers:
   FINAL_ANSWER: [Done]

Combined Math and Paint Workflow:
1. For math operations: Use mathematical functions (add, multiply, strings_to_chars_to_int, int_list_to_exponential_sum, etc.)
2. For paint operations: Use paint functions (open_paint, draw_rectangle, add_text_in_paint, etc.)
3. For combined queries: Do math calculations FIRST, then use results in paint operations
4. ALWAYS call open_paint() first if Paint operations are needed
5. Use draw_rectangle(x1, y1, x2, y2) to draw rectangles with appropriate coordinates
6. Use add_text_in_paint(text, x, y) to add text at specific coordinates
7. IMPORTANT: Text should be placed INSIDE rectangles at the center coordinates
8. To center text in rectangle: text_x = (x1 + x2) / 2, text_y = (y1 + y2) / 2
9. For multi-monitor setup, use coordinates around x1=780, y1=380, x2=1140, y2=700 for rectangles
10. Continue making FUNCTION_CALL until ALL requested tasks are complete
11. Only return FINAL_ANSWER: [Done] when the ENTIRE workflow is finished

Examples:

Math Only:
- FUNCTION_CALL: strings_to_chars_to_int|INDIA
- FUNCTION_CALL: int_list_to_exponential_sum|[73, 78, 68, 73, 65]
- FINAL_ANSWER: [Done]

Paint Only:
- FUNCTION_CALL: open_paint
- FUNCTION_CALL: draw_rectangle|200|200|400|300
- FUNCTION_CALL: add_text_in_paint|Hello|300|250
- FINAL_ANSWER: [Done]

Combined Math + Paint:
- FUNCTION_CALL: strings_to_chars_to_int|HELLO
- FUNCTION_CALL: add_list|[72, 69, 76, 76, 79]
- FUNCTION_CALL: open_paint
- FUNCTION_CALL: draw_rectangle|300|200|500|350
- FUNCTION_CALL: add_text_in_paint|Sum: 372|400|275
- FINAL_ANSWER: [Done]

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

                # Get user query for Math and Paint automation
                query = input("\n🧮🎨 Enter your Math/Paint request: ").strip()
                if not query:
                    query = "Find the ASCII values of characters in INDIA and then return sum of exponentials of those values. Open paint and draw a rectangle. Write those values inside it."
                    print(f"Using default query: {query}")
                
                print(f"\n🚀 Processing query: {query}")
                print("Starting iteration loop...")
                
                # Use global iteration variables
                global iteration, last_response, consecutive_errors
                
                # Continue until agent provides FINAL_ANSWER (no iteration limit)
                while True:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    
                    # Safety checks to prevent infinite loops
                    if iteration >= max_safety_iterations:
                        print(f"\n⚠️ Safety limit reached ({max_safety_iterations} iterations)")
                        print("Stopping execution to prevent infinite loop")
                        break
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n⚠️ Too many consecutive errors ({consecutive_errors})")
                        print("Stopping execution due to repeated failures")
                        break
                    if last_response is None:
                        current_query = query
                    else:
                        current_query = current_query + "\n\n" + " ".join(iteration_response)
                        current_query = current_query + "  What should I do next?"

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")
                        
                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        consecutive_errors += 1
                        print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            print("Breaking due to too many consecutive LLM failures")
                        break


                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        
                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {params}")
                        
                        try:
                            # Find the matching tool to get its input schema
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            # Prepare arguments according to the tool's input schema
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            print(f"DEBUG: Schema properties: {schema_properties}")

                            for param_name, param_info in schema_properties.items():
                                if not params:  # Check if we have enough parameters
                                    raise ValueError(f"Not enough parameters provided for {func_name}")
                                    
                                value = params.pop(0)  # Get and remove the first parameter
                                param_type = param_info.get('type', 'string')
                                
                                print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                
                                # Convert the value to the correct type based on the schema
                                if param_type == 'integer':
                                    arguments[param_name] = int(value)
                                elif param_type == 'number':
                                    arguments[param_name] = float(value)
                                elif param_type == 'array':
                                    # Handle array input
                                    if isinstance(value, str):
                                        value = value.strip('[]').split(',')
                                    arguments[param_name] = [int(x.strip()) for x in value]
                                else:
                                    arguments[param_name] = str(value)

                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")
                            
                            result = await session.call_tool(func_name, arguments=arguments)
                            print(f"DEBUG: Raw result: {result}")
                            
                            # Get the full result content
                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                # Handle multiple content items
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)
                                
                            print(f"DEBUG: Final iteration result: {iteration_result}")
                            
                            # Format the response based on result type
                            if isinstance(iteration_result, list):
                                result_str = f"[{', '.join(iteration_result)}]"
                            else:
                                result_str = str(iteration_result)
                            
                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}."
                            )
                            last_response = iteration_result
                            
                            # Reset consecutive errors on successful function call
                            consecutive_errors = 0

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
                            
                            # Track consecutive errors
                            consecutive_errors += 1
                            print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                            
                            if consecutive_errors >= max_consecutive_errors:
                                print("Breaking due to too many consecutive errors")
                                break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== 🎨 Paint Automation Complete ===")
                        final_answer = response_text.split(":", 1)[1].strip()
                        print(f"✅ Final Result: {final_answer}")
                        
                        # Display completion summary
                        print("\n📋 Execution Summary:")
                        for i, step in enumerate(iteration_response, 1):
                            print(f"  {i}. {step}")
                        
                        break
                    
                    else:
                        # Handle invalid response format
                        print(f"⚠️ Invalid response format: {response_text}")
                        print("Expected FUNCTION_CALL: or FINAL_ANSWER:")
                        
                        consecutive_errors += 1
                        print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            print("Breaking due to too many invalid responses")
                            break
                        
                        # Add to iteration log
                        iteration_response.append(f"Iteration {iteration + 1}: Invalid response format - {response_text[:100]}...")

                    iteration += 1

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    asyncio.run(main())
    
    

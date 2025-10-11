#!/usr/bin/env python3
"""
Stock Analysis MCP Client
Autonomous stock analysis agent using MCP protocol
"""

import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
import json

# Load environment variables
load_dotenv()

# Initialize Gemini client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Global state management
max_safety_iterations = 15
last_response = None
iteration = 0
iteration_responses = []
consecutive_errors = 0
max_consecutive_errors = 3

async def generate_with_timeout(client, prompt, timeout=15):
    """Generate content with a timeout"""
    print("🤖 Generating AI response...")
    try:
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
        print("✅ AI response generated")
        return response
    except TimeoutError:
        print("⏰ AI generation timed out!")
        raise
    except Exception as e:
        print(f"❌ Error in AI generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_responses, consecutive_errors
    last_response = None
    iteration = 0
    iteration_responses = []
    consecutive_errors = 0

async def main():
    reset_state()
    print("🚀 Starting Stock Analysis MCP Client")
    
    try:
        # Create MCP server connection
        print("🔌 Establishing connection to Stock Analysis MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            print("✅ Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("📡 Session created, initializing...")
                await session.initialize()
                
                # Get available tools
                print("🔍 Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"📋 Successfully retrieved {len(tools)} analysis tools")
                
                # Create system prompt with available tools
                tools_description = []
                for i, tool in enumerate(tools):
                    try:
                        params = tool.inputSchema
                        desc = getattr(tool, 'description', 'No description available')
                        name = getattr(tool, 'name', f'tool_{i}')
                        
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
                    except Exception as e:
                        print(f"⚠️ Error processing tool {i}: {e}")
                        tools_description.append(f"{i+1}. Error processing tool")
                
                tools_description = "\n".join(tools_description)
                
                system_prompt = f"""You are an autonomous Stock Market Analysis Agent that performs financial analysis using MCP tools. You must think step-by-step and reason through each decision before taking action.

REASONING PROCESS:
1. First, analyze the user's request to understand what type of analysis they want
2. Identify what data and tools you need to fulfill their request
3. Plan your approach step-by-step before executing
4. After each tool execution, evaluate the results and decide your next step
5. Self-check: Do you have enough information to provide a meaningful answer?

Available analysis tools:
{tools_description}

OUTPUT FORMAT - Respond with EXACTLY ONE line:
1. For function calls: FUNCTION_CALL: function_name|param1|param2|...
2. For final answers: FINAL_ANSWER: [Analysis Complete]

DECISION FRAMEWORK:
Step 1: PARSE QUERY
- Always start with parse_query to convert company names to proper stock symbols
- This ensures you have the correct symbol format for subsequent analysis

Step 2: IDENTIFY ANALYSIS TYPE
- Sentiment Analysis: Requires news_data → sentiment analysis
- Technical Analysis: Requires stock_data → technical indicators (RSI, MACD, Bollinger)
- Correlation Analysis: Requires both stock_data and news_data → correlations
- Algo Strategy: Requires comprehensive data → technical indicators + sentiment + strategy generation
- Full Analysis: All of the above in logical sequence

Step 3: GATHER REQUIRED DATA
- For price analysis: fetch_stock_data (period: 1mo-3mo, interval: 1h-1d)
- For news analysis: fetch_news_data (days: 7-30 depending on analysis depth)
- CRITICAL: interval='1m' requires period ≤ '7d' due to API limits

Step 4: PERFORM ANALYSIS
- Technical indicators: calculate_rsi|14, calculate_macd|12|26|9, calculate_bollinger_bands|20|2.0
- Sentiment: analyze_sentiment|5-10 (batch size)
- Correlations: calculate_correlations (requires both price and sentiment data)
- Strategy: generate_algo_strategy|target_cagr|risk_tolerance

Step 5: SELF-VERIFICATION
- Do I have sufficient data for the requested analysis?
- Are there any errors or missing information?
- Can I provide a meaningful answer to the user's question?

ERROR HANDLING:
- If a tool fails, adapt your approach and try alternative methods
- If data is insufficient, gather more data before proceeding
- If uncertain about next steps, choose the most logical progression
- Always explain your reasoning in the context of previous results

REASONING TYPES:
- Data Gathering: When you need more information
- Technical Analysis: When calculating indicators or patterns
- Fundamental Analysis: When analyzing news and sentiment
- Strategic Planning: When generating trading strategies
- Verification: When checking results or validating approaches

EXAMPLE WORKFLOWS WITH REASONING:

Query: "Analyze Reliance sentiment"
Reasoning: User wants sentiment analysis only, need company symbol and news data
→ parse_query|Analyze Reliance sentiment
→ fetch_news_data|RELIANCE.NS|7
→ analyze_sentiment|5
→ FINAL_ANSWER: [Analysis Complete]

Query: "Generate 20% CAGR strategy for TCS"
Reasoning: User wants algorithmic strategy, need comprehensive analysis including technical indicators
→ parse_query|Generate 20% CAGR strategy for TCS
→ fetch_stock_data|TCS.NS|3mo|1d
→ calculate_rsi|14
→ calculate_macd|12|26|9
→ calculate_bollinger_bands|20|2.0
→ fetch_news_data|TCS.NS|30
→ analyze_sentiment|10
→ calculate_correlations
→ generate_algo_strategy|20|medium
→ FINAL_ANSWER: [Analysis Complete]

Query: "Full analysis of HDFC Bank"
Reasoning: User wants comprehensive analysis, need all data types and analysis methods
→ parse_query|Full analysis of HDFC Bank
→ fetch_stock_data|HDFCBANK.NS|1mo|1h
→ calculate_rsi|14
→ calculate_macd|12|26|9
→ fetch_news_data|HDFCBANK.NS|14
→ analyze_sentiment|5
→ calculate_correlations
→ run_backtest|10000|0.6
→ generate_analysis_report
→ FINAL_ANSWER: [Analysis Complete]

CONVERSATION LOOP:
- Each iteration builds on previous results
- Update your reasoning based on new information
- Adapt your approach if initial plans don't work
- Continue until you have sufficient information to answer the user's question

CRITICAL REMINDERS:
- Think before you act - explain your reasoning internally
- One function call per response
- Verify you have the right data before proceeding to analysis
- Don't provide FINAL_ANSWER until analysis is truly complete
- Adapt to errors and unexpected results gracefully"""

                # Get user query
                query = input("\n📊 Enter your analysis request (e.g., 'Analyze Reliance sentiment', 'Full analysis of TCS', 'Check Apple news correlation'): ").strip()
                if not query:
                    query = "Analyze Reliance Industries sentiment and price correlation"
                    print(f"Using default query: {query}")
                
                print(f"\n🎯 Processing request: {query}")
                print("🤖 AI agent will decide the analysis approach...")
                
                # Use global iteration variables
                global iteration, last_response, consecutive_errors
                
                # Continue until agent provides FINAL_ANSWER
                while True:
                    print(f"\n--- 📈 Analysis Step {iteration + 1} ---")
                    
                    # Safety checks
                    if iteration >= max_safety_iterations:
                        print(f"\n⚠️ Safety limit reached ({max_safety_iterations} steps)")
                        print("Stopping to prevent infinite loop")
                        break
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n❌ Too many consecutive errors ({consecutive_errors})")
                        print("Stopping execution due to repeated failures")
                        break
                    
                    # Build context for AI
                    if last_response is None:
                        current_query = f"User Request: {query}"
                    else:
                        context = "\n".join(iteration_responses)
                        current_query = f"User Request: {query}\n\nPrevious steps:\n{context}\n\nWhat should I do next to fulfill this request?"

                    # Get AI decision
                    prompt = f"{system_prompt}\n\nCurrent situation:\n{current_query}"
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"🤖 AI Decision: {response_text}")
                        
                        # Extract the decision line
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:") or line.startswith("FINAL_ANSWER:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"❌ Failed to get AI response: {e}")
                        consecutive_errors += 1
                        print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            print("Breaking due to AI failures")
                            break
                        continue

                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        
                        print(f"🔧 Executing: {func_name} with parameters: {params}")
                        
                        try:
                            # Find the matching tool
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                raise ValueError(f"Unknown tool: {func_name}")

                            # Prepare arguments according to schema
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            
                            param_index = 0
                            for param_name, param_info in schema_properties.items():
                                if param_index < len(params):
                                    value = params[param_index]
                                    param_type = param_info.get('type', 'string')
                                    
                                    # Convert to correct type
                                    if param_type == 'integer':
                                        arguments[param_name] = int(value)
                                    elif param_type == 'number':
                                        arguments[param_name] = float(value)
                                    elif param_type == 'boolean':
                                        arguments[param_name] = value.lower() in ['true', '1', 'yes']
                                    else:
                                        arguments[param_name] = str(value)
                                    
                                    param_index += 1

                            print(f"📡 Calling {func_name} with: {arguments}")
                            
                            # Execute the tool
                            result = await session.call_tool(func_name, arguments=arguments)
                            
                            # Extract result content
                            if hasattr(result, 'content'):
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                    result_str = ' '.join(iteration_result)
                                else:
                                    result_str = str(result.content)
                            else:
                                result_str = str(result)
                            
                            print(f"✅ Result: {result_str}")
                            
                            # Store the response
                            iteration_responses.append(
                                f"Step {iteration + 1}: Called {func_name}({', '.join(f'{k}={v}' for k, v in arguments.items())}) → {result_str}"
                            )
                            last_response = result_str
                            
                            # Reset consecutive errors on success
                            consecutive_errors = 0

                        except Exception as e:
                            error_msg = f"❌ Error executing {func_name}: {str(e)}"
                            print(error_msg)
                            iteration_responses.append(f"Step {iteration + 1}: {error_msg}")
                            
                            consecutive_errors += 1
                            print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                            
                            if consecutive_errors >= max_consecutive_errors:
                                print("Breaking due to tool execution failures")
                                break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n🎉 === Stock Analysis Complete ===")
                        final_answer = response_text.split(":", 1)[1].strip()
                        print(f"✅ Final Result: {final_answer}")
                        
                        # Display execution summary
                        print("\n📋 Analysis Execution Summary:")
                        for i, step in enumerate(iteration_responses, 1):
                            print(f"  {i}. {step}")
                        
                        # Try to get final summary
                        try:
                            print("\n📊 Getting final analysis summary...")
                            summary_result = await session.call_tool("get_analysis_summary", arguments={})
                            if hasattr(summary_result, 'content'):
                                if isinstance(summary_result.content, list):
                                    summary_text = ' '.join([
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in summary_result.content
                                    ])
                                else:
                                    summary_text = str(summary_result.content)
                            else:
                                summary_text = str(summary_result)
                            
                            print(f"\n📈 Final Analysis Summary:\n{summary_text}")
                        except Exception as e:
                            print(f"⚠️ Could not retrieve final summary: {e}")
                        
                        break
                    
                    else:
                        print(f"⚠️ Invalid response format: {response_text}")
                        print("Expected FUNCTION_CALL: or FINAL_ANSWER:")
                        
                        consecutive_errors += 1
                        print(f"⚠️ Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
                        
                        if consecutive_errors >= max_consecutive_errors:
                            print("Breaking due to invalid responses")
                            break
                        
                        iteration_responses.append(f"Step {iteration + 1}: Invalid response - {response_text[:100]}...")

                    iteration += 1

    except Exception as e:
        print(f"❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()

if __name__ == "__main__":
    print("📊 Stock Market Analysis MCP Client v1.0")
    print("🤖 Autonomous financial analysis using AI and MCP protocol")
    print("📈 Supports global stocks with intelligent company name recognition")
    print("💡 Just use company names: Reliance, TCS, Apple, Tesla, etc.")
    print("=" * 70)
    
    asyncio.run(main())
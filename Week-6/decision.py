#!/usr/bin/env python3
"""
Decision-Making Layer - AI-Driven MCP Client
Uses AI to decide next actions and calls MCP tools (similar to Week-5 talk2mcp)
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from typing import List, Optional, Dict, Any
import logging

from models import (
    ParsedIntent, DecisionContext, 
    DecisionOutput, AgentConfig
)
from memory import Memory

logger = logging.getLogger(__name__)


class DecisionLayer:
    """
    AI-Driven Decision Layer using MCP client pattern from Week-5
    Uses Gemini AI to decide what MCP tools to call next
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.client = genai.Client(api_key=config.gemini_api_key)
        self.max_iterations = config.max_iterations
        self.iteration_responses = []
        self.last_response = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 3
    
    async def execute_analysis(self, intent: ParsedIntent, memory: Memory) -> Dict[str, Any]:
        """
        Execute analysis using AI-driven MCP tool calls
        """
        logger.info(f"Starting AI-driven analysis for {intent.symbol}")
        
        # Reset state
        self.iteration_responses = []
        self.last_response = None
        self.consecutive_errors = 0
        
        try:
            # Create MCP connection
            server_params = StdioServerParameters(
                command="python",
                args=["action.py"]
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Get available tools
                    tools_result = await session.list_tools()
                    tools = tools_result.tools
                    logger.info(f"Connected to MCP server with {len(tools)} tools")
                    
                    # Get static system prompt
                    system_prompt = self._get_system_prompt(tools)
                    
                    # AI-driven analysis loop (like Week-5)
                    for iteration in range(self.max_iterations):
                        logger.info(f"Analysis iteration {iteration + 1}")
                        
                        # Build dynamic context
                        dynamic_context = self._build_dynamic_context(intent, memory)
                        
                        # Add previous steps if any
                        if self.iteration_responses:
                            previous_steps = "\n".join(self.iteration_responses)
                            dynamic_context += f"\n\nPrevious steps:\n{previous_steps}"
                        
                        # Get AI decision
                        prompt = f"{system_prompt}\n\n{dynamic_context}"
                        
                        try:
                            response = await self._generate_with_timeout(prompt)
                            response_text = response.text.strip()
                            logger.info(f"AI Decision: {response_text}")
                            
                            # Extract decision line
                            decision_line = self._extract_decision_line(response_text)
                            
                            if decision_line.startswith("FINAL_ANSWER:"):
                                logger.info("Analysis completed by AI")
                                break
                            
                            elif decision_line.startswith("FUNCTION_CALL:"):
                                # Execute MCP tool call
                                success = await self._execute_function_call(decision_line, tools, session, iteration, memory)
                                if not success:
                                    self.consecutive_errors += 1
                                    if self.consecutive_errors >= self.max_consecutive_errors:
                                        logger.error("Too many consecutive errors, stopping")
                                        break
                                else:
                                    self.consecutive_errors = 0
                            
                        except Exception as e:
                            logger.error(f"Error in AI decision: {str(e)}")
                            self.consecutive_errors += 1
                            if self.consecutive_errors >= self.max_consecutive_errors:
                                break
                    
                    return {
                        "success": True,
                        "iterations": len(self.iteration_responses),
                        "responses": self.iteration_responses
                    }
                    
        except Exception as e:
            logger.error(f"Error in MCP analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "iterations": len(self.iteration_responses)
            }
    
    def _create_tools_description(self, tools: List[Any]) -> str:
        """Create dynamic tools description with key-value pairs from schema"""
        tools_description = []
        
        for i, tool in enumerate(tools):
            try:
                name = getattr(tool, 'name', f'tool_{i}')
                desc = getattr(tool, 'description', 'No description available')
                schema = tool.inputSchema
                
                # Extract parameters from Pydantic schema
                param_details = self._extract_tool_parameters(schema)
                
                if param_details:
                    params_str = '|'.join(param_details)
                    tool_desc = f"{i+1}. {name}|{params_str} - {desc}"
                else:
                    tool_desc = f"{i+1}. {name} - {desc}"
                
                tools_description.append(tool_desc)
            except Exception as e:
                tools_description.append(f"{i+1}. {name} - Error processing tool schema")
        
        return "\n".join(tools_description)
    
    def _extract_tool_parameters(self, schema: Dict[str, Any]) -> List[str]:
        """Extract parameter key-value format from tool schema"""
        param_details = []
        
        # Check if this is a Pydantic tool with input_data
        if 'properties' in schema and 'input_data' in schema['properties']:
            input_data_ref = schema['properties']['input_data'].get('$ref', '')
            
            # Extract model name from $ref
            if input_data_ref.startswith('#/$defs/'):
                model_name = input_data_ref.split('/')[-1]
                
                # Get model definition from $defs
                if '$defs' in schema and model_name in schema['$defs']:
                    model_def = schema['$defs'][model_name]
                    properties = model_def.get('properties', {})
                    required = model_def.get('required', [])
                    
                    for param_name, param_info in properties.items():
                        param_type = param_info.get('type', 'string')
                        default_value = param_info.get('default', None)
                        description = param_info.get('description', '')
                        
                        # Create parameter description
                        if param_name in required:
                            if default_value is not None:
                                param_details.append(f"{param_name}={default_value}")
                            else:
                                param_details.append(f"{param_name}=<{param_type}>")
                        else:
                            if default_value is not None:
                                param_details.append(f"{param_name}={default_value}")
                            else:
                                param_details.append(f"{param_name}=<optional_{param_type}>")
        
        return param_details

    def _get_system_prompt(self, tools: List[Any]) -> str:
        """Get static system prompt for AI decision making"""
        tools_description = self._create_tools_description(tools)
        
        return f"""You are an autonomous Stock Market Analysis Agent. Analyze the user's request and decide what MCP tools to call.

AVAILABLE MCP TOOLS:
{tools_description}

DECISION FRAMEWORK:
1. UNDERSTAND THE REQUEST: What type of analysis does the user want?
2. CHECK CURRENT DATA: What data do we already have in memory?
3. IDENTIFY GAPS: What additional data or analysis is needed?
4. CHOOSE NEXT ACTION: Select the most logical next step

IMPORTANT: Tools are STATELESS - they don't share data directly. Each tool returns results that are stored in memory as facts, but tools cannot pass complex data structures to each other.

ANALYSIS TYPES:
- sentiment: Use fetch_news_data first, then analyze_sentiment_simple
- correlation: Need stock data + news data → sentiment → correlations  
- technical: Need stock data → technical indicators (RSI, MACD, etc.)
- strategy: Need comprehensive data → all analysis → strategy generation
- full_analysis: Complete analysis pipeline

TOOL USAGE NOTES:
- fetch_news_data: Fetches and stores news articles, returns summary message
- analyze_sentiment_simple: Analyzes sentiment for a symbol (use this after fetch_news_data)
- For sentiment analysis workflow: 1) fetch_news_data, 2) analyze_sentiment_simple

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls (using key=value format):
FUNCTION_CALL: function_name|param1=value1|param2=value2|...
2. For final answers:
FINAL_ANSWER: [Analysis Complete]

Important:
- Use exactly one FUNCTION_CALL or FINAL_ANSWER per step.
- Do not repeat function calls with the same parameters.
- Do not include explanatory text or formatting.

✅ Examples:
- FUNCTION_CALL: fetch_stock_data|symbol=RELIANCE.NS|period=1mo|interval=1h
- FUNCTION_CALL: fetch_news_data|symbol=RELIANCE.NS|days=30
- FUNCTION_CALL: analyze_sentiment_simple|symbol=RELIANCE.NS|batch_size=5
- FINAL_ANSWER: [Analysis Complete]

DO NOT include any explanations or extra text.
Your entire response must be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

    def _build_dynamic_context(self, intent: ParsedIntent, memory: Memory) -> str:
        """Build dynamic context with current request and memory state"""
        # Get relevant facts from memory
        query = f"What data and analysis have been completed for {intent.symbol}?"
        relevant_facts = memory.recall_facts(query)
        
        return f"""CURRENT ANALYSIS REQUEST:
- Symbol: {intent.symbol}
- Company: {intent.company_name}
- Task Type: {intent.task_type}
- Period: {intent.period}
- Timeframe: {intent.timeframe}

CURRENT MEMORY STATE:
Facts: {relevant_facts if relevant_facts else "No relevant data available"}

What should the agent do next?"""
    
    async def _generate_with_timeout(self, prompt: str, timeout: int = 15) -> Any:
        """Generate AI response with timeout"""
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                ),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error("AI generation timed out")
            raise
        except Exception as e:
            logger.error(f"Error in AI generation: {e}")
            raise
    
    def _extract_decision_line(self, response_text: str) -> str:
        """Extract the decision line from AI response"""
        for line in response_text.split('\n'):
            line = line.strip()
            if line.startswith("FUNCTION_CALL:") or line.startswith("FINAL_ANSWER:"):
                return line
        return response_text.strip()
    
    def parse_function_call_params(self, param_parts: List[str]) -> Dict[str, Any]:
        """Parses key=value parts from the FUNCTION_CALL format.
        Supports nested keys like input.string=foo and list values like input.int_list=[1,2,3]
        Returns a nested dictionary."""
        import ast
        
        result = {}
        for part in param_parts:
            if "=" not in part:
                raise ValueError(f"Invalid parameter format (expected key=value): {part}")
            
            key, value = part.split("=", 1)
            
            # Try to parse as Python literal (int, float, list, etc.)
            try:
                parsed_value = ast.literal_eval(value)
            except Exception:
                parsed_value = value.strip()
            
            # Support nested keys like input.string
            keys = key.split(".")
            current = result
            for k in keys[:-1]:
                current = current.setdefault(k, {})
            current[keys[-1]] = parsed_value
        
        return result

    async def _execute_function_call(self, decision_line: str, tools: List[Any], 
                                   session: ClientSession, iteration: int, memory: Memory) -> bool:
        """Execute MCP function call (Week-5 pattern)"""
        try:
            _, function_info = decision_line.split(":", 1)
            parts = [p.strip() for p in function_info.split("|")]
            func_name = parts[0]
            param_parts = parts[1:]
            
            # Parse parameters using the cleaner method
            parsed_params = self.parse_function_call_params(param_parts)
            
            # Find the matching tool
            tool = next((t for t in tools if t.name == func_name), None)
            if not tool:
                raise ValueError(f"Unknown tool: {func_name}")
            
            # Check if this is a Pydantic tool that expects input_data wrapper
            schema = tool.inputSchema
            if 'properties' in schema and 'input_data' in schema['properties']:
                arguments = {'input_data': parsed_params}
            else:
                arguments = parsed_params
            
            logger.info(f"Executing: {func_name} with parameters: {arguments}")
            
            logger.info(f"Calling {func_name} with: {arguments}")
            
            # Execute the MCP tool
            result = await session.call_tool(func_name, arguments=arguments)
                        
            # Extract result content (Week-5 pattern)
            if hasattr(result, 'content'):
                if isinstance(result.content, list):
                    iteration_result = [
                        item.text if hasattr(item, 'text') else str(item)
                        for item in result.content
                    ]
                    result_str = ' '.join(iteration_result)
                else:
                    result_str = str(result.content)
                
                # Try to extract message from Pydantic result
                try:
                    import json
                    if isinstance(result.content, list) and len(result.content) > 0:
                        content_item = result.content[0]
                        if hasattr(content_item, 'text'):
                            # Parse JSON to extract message field
                            parsed_result = json.loads(content_item.text)
                            if isinstance(parsed_result, dict) and 'message' in parsed_result:
                                result_str = parsed_result['message']
                except:
                    pass  # Fall back to original result_str
            else:
                result_str = str(result)
            
            logger.info(f"Result: {result_str}")
            
            # Store fact in memory
            fact = f"{func_name} completed: {result_str}"
            memory.store_fact(fact)
            
            # Store the response
            self.iteration_responses.append(
                f"Step {iteration + 1}: Called {func_name}({', '.join(f'{k}={v}' for k, v in arguments.items())}) → {result_str}"
            )
            self.last_response = result_str
            
            return True
            
        except Exception as e:
            error_msg = f"Error executing {func_name}: {str(e)}"
            logger.error(error_msg)
            self.iteration_responses.append(f"Step {iteration + 1}: {error_msg}")
            return False
    
    # Legacy method for compatibility with main.py
    def decide_next_action(self, context: DecisionContext) -> DecisionOutput:
        """Legacy method - now just returns completion signal"""
        return DecisionOutput(
            next_action=None,
            is_complete=True,
            reasoning="Using AI-driven MCP analysis instead of static decision making",
            confidence=1.0,
            estimated_completion=1.0
        )
# modules/action.py

from typing import Dict, Any, Union
from pydantic import BaseModel
import asyncio
import types
import json
from modules.heuristics_code import (
    contains_unsafe_arguments,
    validate_solve_code,
    clean_output_structure,
    SANDBOX_TIMEOUT_SECONDS
)


# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

class ToolCallResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Union[str, list, dict]
    raw_response: Any

MAX_TOOL_CALLS_PER_PLAN = 10

async def run_python_sandbox(code: str, dispatcher: Any, context: Any = None) -> str:
    print("[action] 🔍 Entered run_python_sandbox()")
    
    # H3: Check for unsafe arguments
    if contains_unsafe_arguments(code):
        log("sandbox", "⚠️ Code contains unsafe patterns - blocked")
        return "[sandbox error: unsafe code patterns detected]"
    
    # H5, H7, H10: Validate code with heuristics
    is_valid, errors = validate_solve_code(code)
    if not is_valid:
        log("sandbox", f"⚠️ Code validation failed: {errors}")
        return f"[sandbox error: validation failed - {'; '.join(errors)}]"

    # Create a fresh module scope
    sandbox = types.ModuleType("sandbox")

    try:
        # Patch MCP client with real dispatcher
        class SandboxMCP:
            def __init__(self, dispatcher, context=None):
                self.dispatcher = dispatcher
                self.call_count = 0
                self.tools_called = []  # Track actual MCP tools called
                self.context = context

            async def call_tool(self, tool_name: str, input_dict: dict):
                self.call_count += 1
                if self.call_count > MAX_TOOL_CALLS_PER_PLAN:
                    raise RuntimeError(f"Exceeded max tool calls ({MAX_TOOL_CALLS_PER_PLAN}) in solve() plan.")
                
                # Track this tool call
                self.tools_called.append(tool_name)
                
                # REAL tool call now
                result = await self.dispatcher.call_tool(tool_name, input_dict)
                return result

        sandbox_mcp = SandboxMCP(dispatcher, context)
        sandbox.mcp = sandbox_mcp

        # Preload safe built-ins into the sandbox
        import json, re
        sandbox.__dict__["json"] = json
        sandbox.__dict__["re"] = re

        # Execute solve fn dynamically
        exec(compile(code, "<solve_plan>", "exec"), sandbox.__dict__)

        solve_fn = sandbox.__dict__.get("solve")
        if solve_fn is None:
            raise ValueError("No solve() function found in plan.")

        # H4: Apply timeout to execution
        if asyncio.iscoroutinefunction(solve_fn):
            result = await asyncio.wait_for(solve_fn(), timeout=SANDBOX_TIMEOUT_SECONDS)
        else:
            result = solve_fn()

        # Clean result formatting
        if isinstance(result, dict) and "result" in result:
            result_str = f"{result['result']}"
        elif isinstance(result, dict):
            result_str = f"{json.dumps(result)}"
        elif isinstance(result, list):
            result_str = f"{' '.join(str(r) for r in result)}"
        else:
            result_str = f"{result}"
        
        # H6: Clean output structure
        result_str = clean_output_structure(result_str)
        
        # Store tools_called in context if available
        if context and hasattr(sandbox_mcp, 'tools_called'):
            if not hasattr(context, 'actual_tools_used'):
                context.actual_tools_used = []
            context.actual_tools_used.extend(sandbox_mcp.tools_called)
        
        return result_str






    except asyncio.TimeoutError:
        log("sandbox", f"⚠️ Execution timeout after {SANDBOX_TIMEOUT_SECONDS}s")
        return f"[sandbox error: execution timeout]"
    except Exception as e:
        log("sandbox", f"⚠️ Execution error: {e}")
        return f"[sandbox error: {str(e)}]"

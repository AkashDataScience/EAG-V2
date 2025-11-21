
import ast
import asyncio
import time
import builtins
import textwrap
import re
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.tool_performance import log_tool_call

# ───────────────────────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────────────────────
ALLOWED_MODULES = {
    "math", "cmath", "decimal", "fractions", "random", "statistics", "itertools", "functools", "operator", "string", "re", "datetime", "calendar", "time", "collections", "heapq", "bisect", "types", "copy", "enum", "uuid", "dataclasses", "typing", "pprint", "json", "base64", "hashlib", "hmac", "secrets", "struct", "zlib", "gzip", "bz2", "lzma", "io", "pathlib", "tempfile", "textwrap", "difflib", "unicodedata", "html", "html.parser", "xml", "xml.etree.ElementTree", "csv", "sqlite3", "contextlib", "traceback", "ast", "tokenize", "token", "builtins"
}
MAX_FUNCTIONS = 5
TIMEOUT_PER_FUNCTION = 500  # seconds

class KeywordStripper(ast.NodeTransformer):
    """Rewrite all function calls to remove keyword args and keep only values as positional."""
    def visit_Call(self, node):
        self.generic_visit(node)
        if node.keywords:
            # Convert all keyword arguments into positional args (discard names)
            for kw in node.keywords:
                node.args.append(kw.value)
            node.keywords = []
        return node


# ───────────────────────────────────────────────────────────────
# AST TRANSFORMER: auto-await known async MCP tools
# ───────────────────────────────────────────────────────────────
class AwaitTransformer(ast.NodeTransformer):
    def __init__(self, async_funcs):
        self.async_funcs = async_funcs

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.async_funcs:
            return ast.Await(value=node)
        return node

# ───────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ───────────────────────────────────────────────────────────────
def count_function_calls(code: str) -> int:
    tree = ast.parse(code)
    return sum(isinstance(node, ast.Call) for node in ast.walk(tree))

def build_safe_globals(mcp_funcs: dict, multi_mcp=None) -> dict:
    safe_globals = {
        "__builtins__": {
            k: getattr(builtins, k)
            for k in ("range", "len", "int", "float", "str", "list", "dict", "print", "sum", "__import__")
        },
        **mcp_funcs,
    }

    for module in ALLOWED_MODULES:
        safe_globals[module] = __import__(module)

    # Store LLM-style result
    safe_globals["final_answer"] = lambda x: safe_globals.setdefault("result_holder", x)

    # Optional: add parallel execution
    if multi_mcp:
        async def parallel(*tool_calls):
            coros = [
                multi_mcp.function_wrapper(tool_name, *args)
                for tool_name, *args in tool_calls
            ]
            return await asyncio.gather(*coros)

        safe_globals["parallel"] = parallel

    return safe_globals


# ───────────────────────────────────────────────────────────────
# MAIN EXECUTOR
# ───────────────────────────────────────────────────────────────
async def run_user_code(code: str, multi_mcp) -> dict:
    start_time = time.perf_counter()
    start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        func_count = count_function_calls(code)
        if func_count > MAX_FUNCTIONS:
            return {
                "status": "error",
                "error": f"Too many functions ({func_count} > {MAX_FUNCTIONS})",
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }

        tool_funcs = {
            tool.name: make_tool_proxy(tool.name, multi_mcp)
            for tool in multi_mcp.get_all_tools()
        }

        sandbox = build_safe_globals(tool_funcs, multi_mcp)
        local_vars = {}

        cleaned_code = textwrap.dedent(code.strip())
        tree = ast.parse(cleaned_code)

        has_return = any(isinstance(node, ast.Return) for node in tree.body)
        has_result = any(
            isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "result" for t in node.targets
            )
            for node in tree.body
        )
        if not has_return and has_result:
            tree.body.append(ast.Return(value=ast.Name(id="result", ctx=ast.Load())))

        tree = KeywordStripper().visit(tree) # strip "key" = "value" cases to only "value"
        tree = AwaitTransformer(set(tool_funcs)).visit(tree)
        ast.fix_missing_locations(tree)

        func_def = ast.AsyncFunctionDef(
            name="__main",
            args=ast.arguments(posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=tree.body,
            decorator_list=[]
        )
        wrapper = ast.Module(body=[func_def], type_ignores=[])
        ast.fix_missing_locations(wrapper)

        compiled = compile(wrapper, filename="<user_code>", mode="exec")
        exec(compiled, sandbox, local_vars)

        try:
            timeout = max(3, func_count * TIMEOUT_PER_FUNCTION)  # minimum 3s even for plain returns
            returned = await asyncio.wait_for(local_vars["__main"](), timeout=timeout)

            result_value = returned if returned is not None else sandbox.get("result_holder", "None")

            # If result looks like tool error text, extract
            # Handle CallToolResult errors from MCP
            if hasattr(result_value, "isError") and getattr(result_value, "isError", False):
                error_msg = None

                try:
                    error_msg = result_value.content[0].text.strip()
                except Exception:
                    error_msg = str(result_value)

                return {
                    "status": "error",
                    "error": error_msg,
                    "execution_time": start_timestamp,
                    "total_time": str(round(time.perf_counter() - start_time, 3)),
                    "requires_human_intervention": True,
                    "human_in_loop_reason": "TOOL_FAILURE"
                }

            # Else: normal success
            return {
                "status": "success",
                "result": str(result_value),
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3))
            }


        except Exception as e:
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}",
                "execution_time": start_timestamp,
                "total_time": str(round(time.perf_counter() - start_time, 3)),
                "requires_human_intervention": True,
                "human_in_loop_reason": "TOOL_FAILURE"
            }


    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Execution timed out after {func_count * TIMEOUT_PER_FUNCTION} seconds",
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3)),
            "requires_human_intervention": True,
            "human_in_loop_reason": "TOOL_FAILURE"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "execution_time": start_timestamp,
            "total_time": str(round(time.perf_counter() - start_time, 3)),
            "requires_human_intervention": True,
            "human_in_loop_reason": "TOOL_FAILURE"
        }

# ───────────────────────────────────────────────────────────────
# TOOL WRAPPER WITH PERFORMANCE LOGGING
# ───────────────────────────────────────────────────────────────
def make_tool_proxy(tool_name: str, mcp):
    async def _tool_fn(*args):
        start_time = time.perf_counter()
        success = False
        result = None
        
        try:
            result = await mcp.function_wrapper(tool_name, *args)
            success = True
            return result
        except Exception as e:
            success = False
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            log_tool_call(tool_name, success, latency_ms, retries=0)
    
    return _tool_fn
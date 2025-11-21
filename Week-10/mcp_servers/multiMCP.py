import os
import sys
import asyncio
import json
import time
from typing import Optional, Any, List, Dict
from inspect import signature
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import ast
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.tool_performance import log_tool_call

class MCP:
    def __init__(
        self,
        server_script: str = "mcp_server_2.py",
        working_dir: Optional[str] = None,
        server_command: Optional[str] = None,
    ):
        self.server_script = server_script
        self.working_dir = working_dir or os.getcwd()
        self.server_command = server_command or sys.executable

    async def list_tools(self):
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                return tools_result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        server_params = StdioServerParameters(
            command=self.server_command,
            args=[self.server_script],
            cwd=self.working_dir
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=arguments)

class MultiMCP:
    def __init__(self, server_configs: List[dict]):
        self.server_configs = server_configs
        self.tool_map: Dict[str, Dict[str, Any]] = {}
        self.server_tools: Dict[str, List[Any]] = {}

    async def initialize(self):
        print("in MultiMCP initialize")
        for config in self.server_configs:
            try:
                params = StdioServerParameters(
                    command=sys.executable,
                    args=[config["script"]],
                    cwd=config.get("cwd", os.getcwd())
                )
                print(f"→ Scanning tools from: {config['script']} in {params.cwd}")
                async with stdio_client(params) as (read, write):
                    print("Connection established, creating session...")
                    try:
                        async with ClientSession(read, write) as session:
                            print("[agent] Session created, initializing...")
                            await session.initialize()
                            print("[agent] MCP session initialized")
                            tools = await session.list_tools()
                            print(f"\n→ Tools received: {[tool.name for tool in tools.tools]}")
                            for tool in tools.tools:
                                self.tool_map[tool.name] = {
                                    "config": config,
                                    "tool": tool
                                }
                                server_key = config["id"]
                                if server_key not in self.server_tools:
                                    self.server_tools[server_key] = []
                                self.server_tools[server_key].append(tool)
                    except Exception as se:
                        print(f"❌ Session error: {se}")
            except Exception as e:
                print(f"❌ Error initializing MCP server {config['script']}: {e}")

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        entry = self.tool_map.get(tool_name)
        if not entry:
            raise ValueError(f"Tool '{tool_name}' not found on any server.")

        config = entry["config"]
        params = StdioServerParameters(
            command=sys.executable,
            args=[config["script"]],
            cwd=config.get("cwd", os.getcwd())
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)



    async def function_wrapper(self, tool_name: str, *args):
        """
        Call a tool like a function with positional args OR a single string like 'add(45, 55)'.
        Returns the most relevant parsed result.
        Logs performance metrics.
        """
        start_time = time.perf_counter()
        success = False
        
        try:
            # ── Handle LLM-style string input like: "add(45, 55) or ("send_email", ("a@b.com", "hello"))" ─────────────────
            # ── Handle string-form function call like "add(10, 20)" ──────────────
            if isinstance(tool_name, str) and len(args) == 0:
                stripped = tool_name.strip()
                if stripped.endswith(")") and "(" in stripped:
                    try:
                        expr = ast.parse(stripped, mode='eval').body
                        if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name):
                            raise ValueError("Invalid function call format")
                        tool_name = expr.func.id
                        args = [ast.literal_eval(arg) for arg in expr.args]
                    except Exception as e:
                        raise ValueError(f"Failed to parse function string '{tool_name}': {e}")


            # ── Look up tool ─────────────────────────────────────
            tool_entry = self.tool_map.get(tool_name)
            if not tool_entry:
                raise ValueError(f"Tool '{tool_name}' not found.")

            tool = tool_entry["tool"]
            schema = tool.inputSchema
            params = {}

            # ── Build input payload ──────────────────────────────
            if "input" in schema.get("properties", {}):
                inner_key = next(iter(schema.get("$defs", {})), None)
                inner_props = schema["$defs"][inner_key]["properties"]
                param_names = list(inner_props.keys())
                if len(param_names) != len(args):
                    raise ValueError(f"{tool_name} expects {len(param_names)} args, got {len(args)}")
                params["input"] = dict(zip(param_names, args))
            else:
                param_names = list(schema["properties"].keys())
                if len(param_names) != len(args):
                    raise ValueError(f"{tool_name} expects {len(param_names)} args, got {len(args)}")
                params = dict(zip(param_names, args))

            # ── Call and Normalize Output ────────────────────────
            result = await self.call_tool(tool_name, params)

            try:
                content_text = getattr(result, "content", [])[0].text.strip()
                parsed = json.loads(content_text)

                if isinstance(parsed, dict):
                    if "result" in parsed:
                        success = True
                        return parsed["result"]
                    if len(parsed) == 1:
                        success = True
                        return next(iter(parsed.values()))
                    success = True
                    return parsed

                success = True
                return parsed  # primitive type
            except Exception:
                success = True
                return result  # fallback if parse fails
        
        except Exception as e:
            success = False
            raise
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            log_tool_call(tool_name, success, latency_ms, retries=0)



    def tool_description_wrapper(self) -> List[str]:
        """Format tool usage as: tool(type, type)  # description"""
        examples = []
        for tool in self.get_all_tools():
            schema = tool.inputSchema
            if "input" in schema.get("properties", {}):
                inner_key = next(iter(schema.get("$defs", {})), None)
                props = schema["$defs"][inner_key]["properties"]
            else:
                props = schema["properties"]

            arg_types = []
            for k, v in props.items():
                t = v.get("type", "any")
                arg_types.append(t)

            signature_str = ", ".join(arg_types)
            examples.append(f"{tool.name}({signature_str})  # {tool.description}")
        return examples



    async def list_all_tools(self) -> List[str]:
        return list(self.tool_map.keys())

    def get_all_tools(self) -> List[Any]:
        return [entry["tool"] for entry in self.tool_map.values()]

    def get_tools_from_servers(self, selected_servers: List[str]) -> List[Any]:
        tools = []
        for server in selected_servers:
            if server in self.server_tools:
                tools.extend(self.server_tools[server])
        return tools

    async def shutdown(self):
        pass

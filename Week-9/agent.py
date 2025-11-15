# agent.py

import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP
from core.context import MemoryItem, AgentContext
from modules.historical_index import append_to_historical_store
import datetime
from pathlib import Path
import json
import re

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")

async def main():
    print("🧠 Cortex-R Agent Ready")
    current_session = None

    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers_list = profile.get("mcp_servers", [])
        mcp_servers = {server["id"]: server for server in mcp_servers_list}

    multi_mcp = MultiMCP(server_configs=list(mcp_servers.values()))
    await multi_mcp.initialize()

    try:
        while True:
            user_input = input("🧑 What do you want to solve today? → ")
            if user_input.lower() == 'exit':
                break
            if user_input.lower() == 'new':
                current_session = None
                continue

            while True:
                context = AgentContext(
                    user_input=user_input,
                    session_id=current_session,
                    dispatcher=multi_mcp,
                    mcp_server_descriptions=mcp_servers,
                )
                agent = AgentLoop(context)
                if not current_session:
                    current_session = context.session_id

                result = await agent.run()

                if isinstance(result, dict):
                    answer = result["result"]
                    if "FINAL_ANSWER:" in answer:
                        final_answer = answer.split('FINAL_ANSWER:')[1].strip()
                        print(f"\n💡 Final Answer: {final_answer}")
                        
                        # Extract actual MCP tools used (not solve_sandbox wrapper)
                        tools_used = []
                        if hasattr(context, 'actual_tools_used') and context.actual_tools_used:
                            tools_used = list(set(context.actual_tools_used))  # Remove duplicates
                        
                        tool_name = ", ".join(tools_used) if tools_used else None
                        
                        # Log to historical store
                        append_to_historical_store(
                            user_input=context.user_input,
                            assistant_output=final_answer,
                            tool_name=tool_name,
                            success=True,
                            result=final_answer
                        )
                        break
                    elif "FURTHER_PROCESSING_REQUIRED:" in answer:
                        user_input = answer.split("FURTHER_PROCESSING_REQUIRED:")[1].strip()
                        print(f"\n🔁 Further Processing Required: {user_input}")
                        continue  # 🧠 Re-run agent with updated input
                    else:
                        print(f"\n💡 Final Answer (raw): {answer}")
                        
                        # Extract actual MCP tools used
                        tools_used = []
                        if hasattr(context, 'actual_tools_used') and context.actual_tools_used:
                            tools_used = list(set(context.actual_tools_used))
                        tool_name = ", ".join(tools_used) if tools_used else None
                        
                        # Log to historical store
                        append_to_historical_store(
                            user_input=context.user_input,
                            assistant_output=answer,
                            tool_name=tool_name,
                            success=True,
                            result=answer
                        )
                        break
                else:
                    print(f"\n💡 Final Answer (unexpected): {result}")
                    
                    # Extract actual MCP tools used
                    tools_used = []
                    if hasattr(context, 'actual_tools_used') and context.actual_tools_used:
                        tools_used = list(set(context.actual_tools_used))
                    tool_name = ", ".join(tools_used) if tools_used else None
                    
                    # Log to historical store
                    append_to_historical_store(
                        user_input=context.user_input,
                        assistant_output=str(result),
                        tool_name=tool_name,
                        success=False,
                        result=str(result)
                    )
                    break
    except KeyboardInterrupt:
        print("\n👋 Received exit signal. Shutting down...")

if __name__ == "__main__":
    asyncio.run(main())



# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 
# Explain how you answered my previous three questions and show what information from our past conversation influenced your decision.
# Take the word "AGENT" and convert each character into its ASCII value, compute the cube of each ASCII number, and then return the total sum.
# Summarize the research themes presented on https://ai.googleblog.com/ and extract the top three recurring topics.

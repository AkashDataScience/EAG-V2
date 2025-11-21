import asyncio
import yaml
from mcp_servers.multiMCP import MultiMCP

from dotenv import load_dotenv
# from agent.agent_loop import AgentLoop
from agent.agent_loop2 import AgentLoop
from pprint import pprint
BANNER = """
──────────────────────────────────────────────────────
🔸  Agentic Query Assistant  🔸
Type your question and press Enter.
Type 'exit' or 'quit' to leave.
──────────────────────────────────────────────────────
"""


async def interactive() -> None:
    print(BANNER)
    print("Loading MCP Servers...")
    with open("config/mcp_server_config.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers_list = profile.get("mcp_servers", [])
        configs = list(mcp_servers_list)

    # Initialize MCP + Dispatcher
    multi_mcp = MultiMCP(server_configs=configs)
    await multi_mcp.initialize()
    loop = AgentLoop(
        perception_prompt_path="prompts/perception_prompt.txt",
        decision_prompt_path="prompts/decision_prompt.txt",
        multi_mcp=multi_mcp,
        strategy="exploratory"
    )
    while True:

        query = input("🟢  You: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("👋  Goodbye!")
            break


        response = await loop.run(query)
        
        # Check if human intervention is required
        if response.plan_versions:
            last_plan = response.plan_versions[-1]
            if last_plan["steps"]:
                last_step = last_plan["steps"][-1]
                if last_step.type == "HUMAN_IN_LOOP" or last_step.type == "NOP":
                    print(f"\n⚠️  HUMAN INTERVENTION REQUIRED")
                    print(f"Reason: {last_step.human_in_loop_reason}")
                    print(f"Message: {last_step.human_in_loop_message}")
                    if last_step.suggested_plan:
                        print(f"\nSuggested Plan:")
                        for i, step_text in enumerate(last_step.suggested_plan):
                            print(f"  {i}: {step_text}")
                    
                    human_input = input("\n🟡 Your guidance (or 'skip' to continue): ").strip()
                    if human_input.lower() == "skip":
                        print("Skipping human intervention...")
                    else:
                        print(f"Received: {human_input}")
                        # Feed back into the agent
                        response = await loop.resume_with_guidance(response, human_input)
                        print(f"🔵 Agent: {response.state['solution_summary']}\n")
                else:
                    print(f"🔵 Agent: {response.state['solution_summary']}\n")
        else:
            print(f"🔵 Agent: {response.state['solution_summary']}\n")

        follow = input("\n\nContinue? (press Enter) or type 'exit': ").strip()
        if follow.lower() in {"exit", "quit"}:
            print("👋  Goodbye!")
            break

if __name__ == "__main__":
    asyncio.run(interactive())

# Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
# How much Anmol singh paid for his DLF apartment via Capbridge? 
# What do you know about Don Tapscott and Anthony Williams?
# What is the relationship between Gensol and Go-Auto?
# which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"
# Summarize this page: https://theschoolof.ai/
# What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? 
# Divide 100 by 0
# Calculate the factorial of -5
# Explain the difference between Python and JavaScript
# Compare supervised and unsupervised learning
# Calculate the factorial of 5, then add 10 to it, then multiply the result by 2, and finally divide that by 5.
# Calculate the factorial of 15, then add 12345 to it, then multiply the result by 9876, and finally divide that by 543.
# Multiply 1307674380345 by 9876, and finally divide that by 543.

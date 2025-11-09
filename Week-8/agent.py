# agent.py

import asyncio
import yaml
from core.loop import AgentLoop
from core.session import MultiMCP

def log(stage: str, msg: str):
    """Simple timestamped console logger."""
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [{stage}] {msg}")


async def main():
    print("🧠 Synapse Agent Ready")

    # Load MCP server configs from profiles.yaml
    with open("config/profiles.yaml", "r") as f:
        profile = yaml.safe_load(f)
        mcp_servers = profile.get("mcp_servers", [])

    multi_mcp = MultiMCP(server_configs=mcp_servers)
    print("Agent before initialize")
    await multi_mcp.initialize()

    # List dialogs and use the first one
    log("info", "Listing available Telegram dialogs...")
    dialogs_response = await multi_mcp.call_tool("list_dialogs", {})
    dialogs = dialogs_response.structuredContent.get('result', [])

    if not dialogs:
        log("fatal", "No Telegram dialogs found. Please ensure your Telegram client is set up correctly.")
        return

    first_dialog_str = dialogs[0]
    log("info", f"Using first dialog: {first_dialog_str}")

    # Extract dialog_id from the string
    try:
        import re
        match = re.search(r"id=([\d-]+)", first_dialog_str)
        if not match:
            raise ValueError("Could not parse dialog ID from string.")
        target_dialog_id = int(match.group(1))
    except (ValueError, IndexError) as e:
        log("fatal", f"Could not extract dialog ID from '{first_dialog_str}': {e}")
        return

    log("info", f"Monitoring Telegram dialog ID: {target_dialog_id}")

    log("info", "Checking for new messages...")
    try:
        messages_response = await multi_mcp.call_tool("list_messages", {
            "dialog_id": target_dialog_id,
            "unread": True,
            "mark_read": True,
        })
        messages = messages_response.structuredContent.get('result', [])

        for message in messages:
            log("info", f"New message: {message}")
            agent = AgentLoop(
                user_input=message,
                dispatcher=multi_mcp
            )

            try:
                final_response = await agent.run()

            except Exception as e:
                log("fatal", f"Agent failed: {e}")
                raise

    except Exception as e:
        log("error", f"Failed to get messages: {e}")


if __name__ == "__main__":
    asyncio.run(main())
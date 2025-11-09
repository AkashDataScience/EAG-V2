from __future__ import annotations

import sys
import logging
from functools import cache, singledispatch
from getpass import getpass
from typing import List, Sequence, Any
import threading
import time

from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings
from telethon import TelegramClient, custom, functions, types
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from telethon.tl.types import User
from xdg_base_dirs import xdg_state_home
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

class TelegramSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="TELEGRAM_", env_file=".env", extra='ignore')
    api_id: str
    api_hash: str

@cache
def create_client(
    api_id: str | None = None,
    api_hash: str | None = None,
    session_name: str = "mcp_telegram_session",
) -> TelegramClient:
    if api_id is not None and api_hash is not None:
        config = TelegramSettings(api_id=api_id, api_hash=api_hash)
    else:
        config = TelegramSettings()
    state_home = xdg_state_home() / "mcp-telegram"
    state_home.mkdir(parents=True, exist_ok=True)
    return TelegramClient(state_home / session_name, config.api_id, config.api_hash, base_logger="telethon")

mcp = FastMCP("Telegram", port=8001)

@mcp.tool()
async def list_dialogs(unread: bool = False, archived: bool = False, ignore_pinned: bool = False) -> List[str]:
    """List available dialogs, chats and channels."""
    client: TelegramClient
    logger.info("method[list_dialogs] args: unread=%s, archived=%s, ignore_pinned=%s", unread, archived, ignore_pinned)
    response: list[str] = []
    async with create_client() as client:
        dialog: custom.dialog.Dialog
        async for dialog in client.iter_dialogs(archived=archived, ignore_pinned=ignore_pinned):
            if unread and dialog.unread_count == 0:
                continue
            msg = (
                f"name='{dialog.name}' id={dialog.id} "
                f"unread={dialog.unread_count} mentions={dialog.unread_mentions_count}"
            )
            response.append(msg)
    return response

@mcp.tool()
async def get_my_id() -> int:
    """Get the user's own user ID."""
    client: TelegramClient
    async with create_client() as client:
        me = await client.get_me()
        return me.id

@mcp.tool()
async def list_messages(dialog_id: int, unread: bool = False, limit: int = 100, mark_read: bool = False) -> List[str]:
    """
    List messages in a given dialog, chat or channel. The messages are listed in order from newest to oldest.

    If `unread` is set to `True`, only unread messages will be listed. Once a message is read, it will not be
    listed again.

    If `limit` is set, only the last `limit` messages will be listed. If `unread` is set, the limit will be
    the minimum between the unread messages and the limit.

    If `mark_read` is set to `True`, the messages will be marked as read after they are fetched.
    """
    client: TelegramClient
    logger.info("method[list_messages] args: dialog_id=%s, unread=%s, limit=%s", dialog_id, unread, limit)
    response: list[str] = []
    async with create_client() as client:
        result = await client(functions.messages.GetPeerDialogsRequest(peers=[dialog_id]))
        logger.debug("="*20)
        logger.debug("result: %s", result)
        logger.debug("="*20)
        if not result or not isinstance(result, types.messages.PeerDialogs) or not result.dialogs:
            raise ValueError(f"Channel not found or invalid response for dialog_id: {dialog_id}")

        dialog = result.dialogs[0]

        iter_messages_args: dict[str, Any] = {
            "entity": dialog_id,
            "reverse": False,
        }
        
        effective_limit = limit
        if unread:
            effective_limit = min(dialog.unread_count, limit)
        
        iter_messages_args["limit"] = effective_limit

        if effective_limit == 0:
            return []

        logger.debug("iter_messages_args: %s", iter_messages_args)
        messages = []
        async for message in client.iter_messages(**iter_messages_args):
            if isinstance(message, custom.Message) and message.text:
                logger.debug("message: %s", message.text)
                messages.append(message)
                response.append(message.text)

        if mark_read and messages:
            await client.send_read_acknowledge(dialog_id, max_id=messages[0].id)

    return response

if __name__ == "__main__":
    print("STARTING THE TELEGRAM SERVER")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()
    else:
        server_thread = threading.Thread(target=lambda: mcp.run(transport="sse"))
        server_thread.daemon = True
        server_thread.start()
        time.sleep(2)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")

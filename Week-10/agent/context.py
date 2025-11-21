from mcp_servers.multiMCP import MultiMCP
from typing import Optional
from pydantic import BaseModel
import time
import uuid
from datetime import datetime

class StrategyProfile(BaseModel):
    planning_mode: str
    exploration_mode: Optional[str] = None
    memory_fallback_enabled: bool
    max_steps: int
    max_lifelines_per_step: int

class AgentContext:
    def __init__(
        self,
        mcp_context: Optional[MultiMCP] = None,
        
    ):

        self.mcp_context = mcp_context

        

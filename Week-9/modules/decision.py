from typing import List, Optional
from modules.perception import PerceptionResult
from modules.memory import MemoryItem, MemoryManager
from modules.model_manager import ModelManager
from modules.tools import load_prompt
from modules.memory_index import get_compact_memory_summary
from modules.historical_index import get_historical_context
import re

# Optional logging fallback
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

model = ModelManager()


# prompt_path = "prompts/decision_prompt.txt"

async def generate_plan(
    user_input: str, 
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str],
    prompt_path: str,
    step_num: int = 1,
    max_steps: int = 3,
    planning_mode: str = "conservative",
    exploration_mode: str = "sequential",
    memory_manager: Optional[MemoryManager] = None,
) -> str:

    """Generates the full solve() function plan for the agent."""

    # Use compact memory summary instead of raw items
    if memory_manager:
        memory_summary = get_compact_memory_summary(user_input, memory_manager)
    else:
        memory_summary = "\n".join(f"- {m.text}" for m in memory_items) or "None"
    
    # Get historical context from past conversations
    historical_context = get_historical_context(user_input)
    log("plan", f"📚 Historical context retrieved ({len(historical_context)} chars)")

    prompt_template = load_prompt(prompt_path)

    prompt = prompt_template.format(
        tool_descriptions=tool_descriptions,
        user_input=user_input,
        historical_context=historical_context,
        planning_mode=planning_mode,
        exploration_mode=exploration_mode
    )

    try:
        raw = (await model.generate_text(prompt)).strip()
        log("plan", f"LLM output: {raw}")

        # If fenced in ```python ... ```, extract
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("python"):
                raw = raw[len("python"):].strip()

        if re.search(r"^\s*(async\s+)?def\s+solve\s*\(", raw, re.MULTILINE):
            return raw  # ✅ Correct, it's a full function
        else:
            log("plan", "⚠️ LLM did not return a valid solve(). Defaulting to FINAL_ANSWER")
            return "FINAL_ANSWER: [Could not generate valid solve()]"


    except Exception as e:
        log("plan", f"⚠️ Planning failed: {e}")
        return "FINAL_ANSWER: [unknown]"

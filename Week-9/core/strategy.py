# modules/strategy.py

from typing import List, Optional, Any
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from core.context import AgentContext
from modules.tools import filter_tools_by_hint, summarize_tools, load_prompt

# Optional fallback logger
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

def select_decision_prompt_path(planning_mode: str, exploration_mode: Optional[str] = None) -> str:
    """Selects the appropriate decision prompt file based on planning strategy."""
    if planning_mode == "conservative":
        return "prompts/decision_prompt_conservative_short.txt"
    elif planning_mode == "exploratory":
        if exploration_mode == "parallel":
            return "prompts/decision_prompt_exploratory_parallel.txt"
        elif exploration_mode == "sequential":
            return "prompts/decision_prompt_exploratory_sequential.txt"
    return "prompts/decision_prompt_conservative_short.txt"  # safe fallback

model = ModelManager()

async def decide_next_action(
    context: AgentContext,
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    all_tools: List[Any],
    last_result: str = "",
    failed_tools: List[str] = [],
    force_replan: bool = False,
) -> str:
    """
    Main decision function.
    """

    strategy = context.agent_profile.strategy
    planning_mode = strategy.planning_mode
    exploration_mode = strategy.exploration_mode
    memory_fallback_enabled = strategy.memory_fallback_enabled
    max_steps = strategy.max_steps
    max_lifelines_per_step = strategy.max_lifelines_per_step
    step_num = context.step + 1

    # === Select correct decision prompt path ===
    prompt_path = select_decision_prompt_path(planning_mode, exploration_mode)

    # Filter tools based on Perception hint
    tool_hint = perception.tool_hint
    filtered_tools = filter_tools_by_hint(all_tools, hint=tool_hint)
    filtered_summary = summarize_tools(filtered_tools)

    if planning_mode == "conservative":
        return await conservative_plan(
            perception, memory_items, filtered_summary, all_tools, step_num, max_steps,
            prompt_path, force_replan
        )

    if planning_mode == "exploratory":
        return await exploratory_plan(
            perception, memory_items, filtered_summary, all_tools, step_num, max_steps,
            exploration_mode, memory_fallback_enabled, prompt_path, force_replan, failed_tools
        )

    # Fallback
    full_summary = summarize_tools(all_tools)
    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=full_summary,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps,
    )
    return plan

# === CONSERVATIVE MODE ===
async def conservative_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    filtered_summary: str,
    all_tools: List[Any],
    step_num: int,
    max_steps: int,
    prompt_path: str,
    force_replan: bool
) -> str:
    """Conservative: Plan 1 tool call."""

    if force_replan or not filtered_summary.strip():
        log("strategy", "⚠️ Force replan or no filtered tools. Using all tools.")
        tool_context = summarize_tools(all_tools)
    else:
        tool_context = filtered_summary

    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=tool_context,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps
    )

    return plan

# === EXPLORATORY MODE ===
async def exploratory_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    filtered_summary: str,
    all_tools: List[Any],
    step_num: int,
    max_steps: int,
    exploration_mode: str,
    memory_fallback_enabled: bool,
    prompt_path: str,
    force_replan: bool,
    failed_tools: List[str]
) -> str:
    """Exploratory: Plan multiple options."""

    if force_replan:
        log("strategy", "⚠️ Force replan triggered. Attempting fallback.")

        if memory_fallback_enabled:
            fallback_tools = find_recent_successful_tools(memory_items)
            if fallback_tools:
                log("strategy", f"✅ Memory fallback tools found: {fallback_tools}")
                fallback_summary = summarize_tools(fallback_tools)
                return await generate_plan(
                    perception=perception,
                    memory_items=memory_items,
                    tool_descriptions=fallback_summary,
                    prompt_path=prompt_path,
                    step_num=step_num,
                    max_steps=max_steps
                )
            else:
                log("strategy", "⚠️ No memory fallback tools. Using all tools.")

        tool_context = summarize_tools(all_tools)
        return await generate_plan(
            perception=perception,
            memory_items=memory_items,
            tool_descriptions=tool_context,
            prompt_path=prompt_path,
            step_num=step_num,
            max_steps=max_steps
        )

    if not filtered_summary.strip():
        log("strategy", "⚠️ No filtered tools. Using all tools.")
        tool_context = summarize_tools(all_tools)
    else:
        tool_context = filtered_summary

    plan = await generate_plan(
        perception=perception,
        memory_items=memory_items,
        tool_descriptions=tool_context,
        prompt_path=prompt_path,
        step_num=step_num,
        max_steps=max_steps
    )

    return plan

# === GENERATE PLAN ===
async def generate_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: str,
    prompt_path: str,
    step_num: int,
    max_steps: int,
) -> str:
    """Ask LLM to generate solve() using the right prompt."""

    prompt_template = load_prompt(prompt_path)

    final_prompt = prompt_template.format(
        tool_descriptions=tool_descriptions,
        user_input=perception.user_input
    )

    raw = (await model.generate_text(final_prompt)).strip()
    log("plan", f"Generated solve():\n{raw}")

    return raw

# === MEMORY FALLBACK LOGIC ===
def find_recent_successful_tools(memory_items: List[MemoryItem], limit: int = 5) -> List[str]:
    """Find recent successful tool names based on memory items."""
    successful_tools = []

    for item in reversed(memory_items):
        if item.type == "tool_output" and item.success and item.tool_name:
            if item.tool_name not in successful_tools:
                successful_tools.append(item.tool_name)
        if len(successful_tools) >= limit:
            break

    return successful_tools

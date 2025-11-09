from typing import List, Optional
from modules.perception import PerceptionResult
from modules.memory import MemoryItem
from modules.model_manager import ModelManager
from dotenv import load_dotenv
from google import genai
import os
import asyncio

# Optional: import logger if available
try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

model = ModelManager()


async def generate_plan(
    perception: PerceptionResult,
    memory_items: List[MemoryItem],
    tool_descriptions: Optional[str] = None,
    step_num: int = 1,
    max_steps: int = 3
) -> str:
    """Generates the next step plan for the agent: either tool usage or final answer."""

    memory_texts = "\n".join(f"- {m.text}" for m in memory_items) or "None"
    tool_context = f"\nYou have access to the following tools:\n{tool_descriptions}" if tool_descriptions else ""

    prompt = f"""
You are a reasoning-driven AI agent. Your goal is to solve the user's request by thinking step-by-step, using tools when needed, and providing a final answer.

═══════════════════════════════════════════════════════════════════════════════
REASONING PROCESS (Think Before Acting):
═══════════════════════════════════════════════════════════════════════════════

1. ANALYZE the current situation:
   - What is the user asking for?
   - What have I already done? (Check memory)
   - What information do I have?
   - What information am I missing?

2. IDENTIFY the reasoning type needed:
   - Lookup/Search: Need external information?
   - Computation: Need to calculate something?
   - Data transformation: Need to process/format data?
   - Multi-step workflow: Need to chain multiple actions?

3. DECIDE the next action:
   - If I have all needed information → FINAL_ANSWER
   - If I need more information → FUNCTION_CALL
   - If I'm unsure → FINAL_ANSWER: [unknown]

4. SELF-CHECK before responding:
   - Have I already done this action? (Check memory!)
   - Am I repeating myself?
   - Is this the logical next step?
   - Will this move me closer to the goal?

═══════════════════════════════════════════════════════════════════════════════
OUTPUT FORMAT (Respond with EXACTLY ONE of these):
═══════════════════════════════════════════════════════════════════════════════

FUNCTION_CALL: tool_name|param1=value1|param2=value2
FINAL_ANSWER: [your complete answer to the user's question]

═══════════════════════════════════════════════════════════════════════════════
CURRENT CONTEXT:
═══════════════════════════════════════════════════════════════════════════════

Step: {step_num} of {max_steps}

User Request: "{perception.user_input}"
Intent: {perception.intent}
Entities: {', '.join(perception.entities)}
Tool Hint: {perception.tool_hint or 'None'}

Memory (What I've already done):
{memory_texts}

Available Tools:
{tool_context}

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES:
═══════════════════════════════════════════════════════════════════════════════

Example 1 - Simple Calculation:
User: "What is 5 + 3?"
Reasoning: This is arithmetic, I have an 'add' tool
Action: FUNCTION_CALL: add|a=5|b=3
Result: 8
Final: FINAL_ANSWER: [8]

Example 2 - Information Lookup:
User: "What's the relationship between Cricket and Sachin Tendulkar?"
Reasoning: Need external knowledge, use search
Action: FUNCTION_CALL: search_documents|query="Cricket Sachin Tendulkar relationship"
Result: [detailed document about Sachin]
Final: FINAL_ANSWER: [Sachin Tendulkar is widely regarded as the "God of Cricket"...]

Example 3 - Multi-Step Workflow:
User: "Get F1 standings and save to Google Sheets"
Step 1: FUNCTION_CALL: search|query="F1 current standings"
Step 2: FUNCTION_CALL: extract_webpage|input={{"url":"..."}}
Step 3: FUNCTION_CALL: create_spreadsheet|title="F1 Standings"
Step 4: FUNCTION_CALL: batch_update_cells|spreadsheet_id=<from_step3>|updates=[...]
Step 5: FINAL_ANSWER: [F1 standings saved to Google Sheets]

═══════════════════════════════════════════════════════════════════════════════
CRITICAL RULES:
═══════════════════════════════════════════════════════════════════════════════

✅ DO:
- Think step-by-step before acting
- Check memory to see what's already been done
- Use tools that are listed in "Available Tools"
- Follow the exact output format (FUNCTION_CALL or FINAL_ANSWER)
- Identify the type of reasoning needed (lookup, compute, transform, etc.)
- Self-verify: "Is this the right next step?"
- Chain tools in sequence for multi-step tasks
- Extract key information from tool results before moving forward

❌ DON'T:
- Invent tools that don't exist
- Repeat the same tool call with the same parameters
- Output explanatory text (only FUNCTION_CALL or FINAL_ANSWER)
- Skip intermediate steps in multi-step workflows
- Ignore memory (always check what's been done)
- Give up early (use all {max_steps} steps if needed)

🔧 TOOL USAGE PATTERNS:
- Nested parameters: input.string, input.url, input.value
- Lists: [item1, item2, item3]
- Dictionaries: {{"key":"value"}}
- Check tool descriptions for exact parameter names

🔄 MULTI-STEP WORKFLOWS:
- Step 1: Gather information (search, extract, etc.)
- Step 2: Process/transform data if needed
- Step 3: Take action (create, update, send, etc.)
- Step 4: Verify or share results
- Step 5: Provide FINAL_ANSWER

⚠️ ERROR HANDLING:
- If uncertain: FINAL_ANSWER: [unknown]
- If tool fails: Try alternative approach or report issue
- If approaching max steps: Provide FINAL_ANSWER with what you have

═══════════════════════════════════════════════════════════════════════════════
NOW: Think through the situation above and respond with your next action.
═══════════════════════════════════════════════════════════════════════════════
"""

    try:
        raw = (await model.generate_text(prompt)).strip()
        log("plan", f"LLM output: {raw}")

        for line in raw.splitlines():
            if line.strip().startswith("FUNCTION_CALL:") or line.strip().startswith("FINAL_ANSWER:"):
                return line.strip()

        return "FINAL_ANSWER: [unknown]"

    except Exception as e:
        log("plan", f"⚠️ Planning failed: {e}")
        return "FINAL_ANSWER: [unknown]"

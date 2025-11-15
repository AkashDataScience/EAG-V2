# modules/loop.py

import asyncio
from modules.perception import run_perception
from modules.decision import generate_plan
from modules.action import run_python_sandbox
from modules.model_manager import ModelManager
from core.session import MultiMCP
from core.strategy import select_decision_prompt_path
from core.context import AgentContext
from modules.tools import summarize_tools
import re

try:
    from agent import log
except ImportError:
    import datetime
    def log(stage: str, msg: str):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{stage}] {msg}")

class AgentLoop:
    def __init__(self, context: AgentContext):
        self.context = context
        self.mcp = self.context.dispatcher
        self.model = ModelManager()

    async def run(self):
        max_steps = self.context.agent_profile.strategy.max_steps

        for step in range(max_steps):
            print(f"🔁 Step {step+1}/{max_steps} starting...")
            self.context.step = step
            lifelines_left = self.context.agent_profile.strategy.max_lifelines_per_step

            while lifelines_left >= 0:
                # === Perception ===
                user_input_override = getattr(self.context, "user_input_override", None)
                current_user_input = user_input_override or self.context.user_input
                perception = await run_perception(context=self.context, user_input=current_user_input)

                print(f"[perception] {perception}")

                selected_servers = perception.selected_servers
                selected_tools = self.mcp.get_tools_from_servers(selected_servers)
                if not selected_tools:
                    log("loop", "⚠️ No tools selected — aborting step.")
                    break

                # === Planning ===
                tool_descriptions = summarize_tools(selected_tools)
                
                # Select prompt based on strategy
                prompt_path = select_decision_prompt_path(
                    planning_mode=self.context.agent_profile.strategy.planning_mode,
                    exploration_mode=self.context.agent_profile.strategy.exploration_mode,
                )

                plan = await generate_plan(
                    user_input=current_user_input,
                    perception=perception,
                    memory_items=self.context.memory.get_session_items(),
                    tool_descriptions=tool_descriptions,
                    prompt_path=prompt_path,
                    step_num=step + 1,
                    max_steps=max_steps,
                    planning_mode=self.context.agent_profile.strategy.planning_mode,
                    exploration_mode=self.context.agent_profile.strategy.exploration_mode,
                    memory_manager=self.context.memory,
                )
                print(f"[plan] {plan}")

                # === Execution ===
                if re.search(r"^\s*(async\s+)?def\s+solve\s*\(", plan, re.MULTILINE):
                    print("[loop] Detected solve() plan — running sandboxed...")

                    self.context.log_subtask(tool_name="solve_sandbox", status="pending")
                    result = await run_python_sandbox(plan, dispatcher=self.mcp, context=self.context)

                    success = False
                    if isinstance(result, str):
                        result = result.strip()
                        if result.startswith("FINAL_ANSWER:"):
                            success = True
                            self.context.final_answer = result
                            self.context.update_subtask_status("solve_sandbox", "success")
                            self.context.memory.add_tool_output(
                                tool_name="solve_sandbox",
                                tool_args={"plan": plan},
                                tool_result={"result": result},
                                success=True,
                                tags=["sandbox"],
                            )
                            return {"status": "done", "result": self.context.final_answer}
                        elif result.startswith("FURTHER_PROCESSING_REQUIRED:"):
                            content = result.split("FURTHER_PROCESSING_REQUIRED:")[1].strip()
                            self.context.user_input_override  = (
                                f"Original user task: {self.context.user_input}\n\n"
                                f"Your last tool produced this result:\n\n"
                                f"{content}\n\n"
                                f"If this fully answers the task, return:\n"
                                f"FINAL_ANSWER: your answer\n\n"
                                f"Otherwise, return the next FUNCTION_CALL."
                            )
                            log("loop", f"📨 Forwarding intermediate result to next step:\n{self.context.user_input_override}\n\n")
                            log("loop", f"🔁 Continuing based on FURTHER_PROCESSING_REQUIRED — Step {step+1} continues...")
                            break  # Step will continue
                        elif result.startswith("[sandbox error:"):
                            success = False
                            self.context.final_answer = "FINAL_ANSWER: [Execution failed]"
                        else:
                            success = True
                            self.context.final_answer = f"FINAL_ANSWER: {result}"
                    else:
                        self.context.final_answer = f"FINAL_ANSWER: {result}"

                    if success:
                        self.context.update_subtask_status("solve_sandbox", "success")
                    else:
                        self.context.update_subtask_status("solve_sandbox", "failure")

                    self.context.memory.add_tool_output(
                        tool_name="solve_sandbox",
                        tool_args={"plan": plan},
                        tool_result={"result": result},
                        success=success,
                        tags=["sandbox"],
                    )

                    if success and "FURTHER_PROCESSING_REQUIRED:" not in result:
                        return {"status": "done", "result": self.context.final_answer}
                    else:
                        lifelines_left -= 1
                        log("loop", f"🛠 Retrying... Lifelines left: {lifelines_left}")
                        continue
                else:
                    log("loop", f"⚠️ Invalid plan detected — retrying... Lifelines left: {lifelines_left-1}")
                    lifelines_left -= 1
                    continue

        log("loop", "⚠️ Max steps reached without finding final answer.")
        self.context.final_answer = "FINAL_ANSWER: [Max steps reached]"
        return {"status": "done", "result": self.context.final_answer}

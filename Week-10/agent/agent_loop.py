import uuid
import datetime
from pathlib import Path
from perception.perception import Perception
from decision.decision import Decision
from action.executor import run_user_code
from agent.agentSession import AgentSession, PerceptionSnapshot, Step, ToolCode
from memory.session_log import append_session_to_store, live_update_session
from memory.memory_search import MemorySearch
from mcp_servers.multiMCP import MultiMCP


class AgentLoop:
    def __init__(self, perception_prompt_path: str, decision_prompt_path: str, multi_mcp: MultiMCP, strategy: str = "exploratory"):
        self.perception = Perception(perception_prompt_path)
        self.decision = Decision(decision_prompt_path, multi_mcp)
        self.strategy = strategy
        self.multi_mcp = multi_mcp

    async def run(self, query: str):
        session = AgentSession(session_id=str(uuid.uuid4()), original_query=query)
        print(f"\n=== LIVE AGENT SESSION TRACE ===")
        print(f"Session ID: {session.session_id}")
        print(f"Query: {query}")

        # ── Step -1: Memory Search ───────────────────────────
        print(f"Searching Recent Conversation History")
        searcher = MemorySearch()
        results = searcher.search_memory(query)
        if not results:
            print("❌ No matching memory entries found.\n")
        else:
            print("\n🎯 Top Matches:\n")
            for i, res in enumerate(results, 1):
                print(f"[{i}] File: {res['file']}")
                print(f"    Query: {res['query']}")
                print(f"    Result Requirement: {res['result_requirement']}")
                print(f"    Summary: {res['solution_summary']}\n")


        print(f"Query: {query}")

        # ── Step 0: Perception ───────────────────────────────
        perception_input = self.perception.build_perception_input(
                        raw_input = query, 
                        memory = results, 
                        snapshot_type="user_query")
        perception_result = self.perception.run(perception_input)

        session.add_perception(PerceptionSnapshot(**perception_result))

        # EXIT early if perception is confident
        if perception_result.get("original_goal_achieved"):
            print("\n✅ Perception has already fully answered the query.")
            session.state.update({
                "original_goal_achieved": True,
                "final_answer": perception_result.get("solution_summary", "Answer ready."),
                "confidence": perception_result.get("confidence", 0.95),
                "reasoning_note": perception_result.get("reasoning", "Fully handled by initial perception."),
                "solution_summary": perception_result.get("solution_summary", "Answer ready.")
            })
            live_update_session(session)
            return session  # exit early


        print("\n[Perception 0] Initial ERORLL:")
        print(f"  {perception_result}")
        live_update_session(session)


        # ── Step 1: Decision ────────────────────────────────
        decision_input = {
            "plan_mode": "initial",
            "planning_strategy": self.strategy,
            "original_query": query,
            "perception": perception_result,
        }
        decision_output = self.decision.run(decision_input)

        plan_text = decision_output["plan_text"]
        step_obj = Step(
            index=decision_output["step_index"],
            description=decision_output["description"],
            type=decision_output["type"],
            code=ToolCode(
                tool_name="raw_code_block",
                tool_arguments={"code": decision_output["code"]}
            ) if decision_output["type"] == "CODE" else None,
            conclusion=decision_output["conclusion"],
        )
        session.add_plan_version(plan_text, [step_obj])
        live_update_session(session)


        # ── Step Execution (Manual) ─────────────────────────
        print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")

        for line in plan_text:
            print(f"  {line}")

        while True:
            print(f"\n[Step {step_obj.index}] {step_obj.description}")
            if step_obj.type == "CODE":
                # print("\n📥 Code to run manually:\n")
                print("-"*50)
                print("[EXECUTING CODE]")
                print(step_obj.code.tool_arguments["code"])
                code = step_obj.code.tool_arguments["code"]
                # result = input("\nPaste result of running this code: ")
                executor_response = await run_user_code(code, self.multi_mcp)
                step_obj.execution_result = executor_response
                # print("-"*50)
                # print(executor_response['status'] + "\n")
                # small_result = executor_response.get('result', 'Tool Failed')
                # print(small_result[:100] + "\n")
                # print("-"*50)

                step_obj.status = "completed"

                perception_input = self.perception.build_perception_input(
                                raw_input=executor_response.get('result', 'Tool Failed'), 
                                memory = [], 
                                current_plan = session.plan_versions[-1]["plan_text"], 
                                snapshot_type="step_result")
                perception_result = self.perception.run(perception_input)

                step_obj.perception = PerceptionSnapshot(**perception_result)
                live_update_session(session)

                print(f"\n[Perception of Step {step_obj.index} Result]:")
                print(perception_result)

                if step_obj.perception.original_goal_achieved and step_obj.type != "CONCLUDE":
                    print("\n✅ Perception says original goal is satisfied at this CODE step.")
                    session.state.update({
                        "original_goal_achieved": True,
                        "final_answer": step_obj.execution_result,
                        "confidence": step_obj.perception.confidence,
                        "reasoning_note": step_obj.perception.reasoning,
                        "solution_summary": step_obj.perception.solution_summary
                    })
                    live_update_session(session)
                    break

                elif step_obj.perception.local_goal_achieved:
                    # Proceed to next step in same plan
                    current_plan = session.plan_versions[-1]
                    plan_text_lines = current_plan["plan_text"]
                    steps = current_plan["steps"]
                    next_index = step_obj.index + 1
                    total_steps = sum(1 for line in plan_text_lines if line.strip().startswith("Step "))

                    if next_index < total_steps:
                        print(f"\n➡️ Proceeding to Step {next_index}...")

                        # Ask Decision to generate next step
                        decision_input = {
                            "plan_mode": "mid_session",
                            "planning_strategy": self.strategy,
                            "original_query": query,
                            "current_plan_version": len(session.plan_versions),
                            "current_plan": plan_text_lines,
                            "completed_steps": [s.to_dict() for s in steps if s.status == "completed"],
                            "current_step": step_obj.to_dict(),
                        }

                        decision_output = self.decision.run(decision_input)
                        plan_text = decision_output["plan_text"]
                        try:
                            step_obj = Step(
                                index=session.get_next_step_index(),
                                description=decision_output["description"],
                                type=decision_output["type"],
                                code=ToolCode(
                                    tool_name="raw_code_block",
                                    tool_arguments={"code": decision_output["code"]}
                                ) if decision_output["type"] == "CODE" else None,
                                conclusion=decision_output.get("conclusion"),
                            )
                        except KeyError as e:
                            print(f"⚠️ KeyError: {e} in decision_output: {decision_output}")
                            raise
                        session.add_plan_version(plan_text, [step_obj])
                        print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
                        for line in plan_text:
                            print(f"  {line}")
                        continue

                    else:
                        output = perception_result['reasoning'] + "\n" + perception_result['local_reasoning'] + "\n Unfortunately we're out of steps."
                        print("\n✅ Max step Limit hit!\n" + output)
                        live_update_session(session)
                        break

                else:
                    print(f"\n🔁 Step {step_obj.index} failed or unhelpful. Replanning...")

                    decision_input = {
                        "plan_mode": "mid_session",
                        "planning_strategy": self.strategy,
                        "original_query": query,
                        "current_plan_version": len(session.plan_versions),
                        "current_plan": session.plan_versions[-1]["plan_text"],
                        "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
                        "current_step": step_obj.to_dict(),
                    }

                    decision_output = self.decision.run(decision_input)
                    plan_text = decision_output["plan_text"]
                    step_obj = Step(
                        index=decision_output["step_index"],
                        description=decision_output["description"],
                        type=decision_output["type"],
                        code=ToolCode(
                            tool_name="raw_code_block",
                            tool_arguments={"code": decision_output["code"]}
                        ) if decision_output["type"] == "CODE" else None,
                        conclusion=decision_output["conclusion"],
                    )
                    session.add_plan_version(plan_text, [step_obj])
                    print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
                    for line in plan_text:
                        print(f"  {line}")
                    live_update_session(session)
                    continue

            elif step_obj.type == "CONCLUDE":
                print(f"\n💡 Conclusion: {step_obj.conclusion}")
                step_obj.status = "completed"
                step_obj.execution_result = step_obj.conclusion

                # 🧠 Run perception on conclusion text
                perception_input = self.perception.build_perception_input(
                                raw_input=step_obj.conclusion, 
                                memory = [], 
                                current_plan = session.plan_versions[-1]["plan_text"], 
                                snapshot_type="step_result")
                perception_result = self.perception.run(perception_input)
                # Not ready yet?
                if 'Not ready yet' in perception_result.get('solution_summary'):
                    perception_result['solution_summary'] = perception_result['reasoning'] + "\n" + perception_result['local_reasoning'] +"\nIf you disagree, try to be more specific in your query.\n"
                step_obj.perception = PerceptionSnapshot(**perception_result)
                session.add_perception(step_obj.perception)



                session.state.update({
                    "original_goal_achieved": perception_result["original_goal_achieved"],
                    "final_answer": step_obj.conclusion,
                    "confidence": perception_result.get("confidence", 0.95),
                    "reasoning_note": perception_result.get("reasoning", "Conclusion step evaluated by perception for completeness."),
                    "solution_summary": perception_result.get("solution_summary", "Answer ready.")
                })
                live_update_session(session)
                break

            elif step_obj.type == "NOP":
                print(f"\n❓ Clarification needed: {step_obj.description}")
                live_update_session(session)
                break


        # You can now continue the loop by checking session state, goal satisfaction, etc.
        return session

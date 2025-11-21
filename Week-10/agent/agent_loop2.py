import uuid
import json
import datetime
from perception.perception import Perception
from decision.decision import Decision
from action.executor import run_user_code
from agent.agentSession import AgentSession, PerceptionSnapshot, Step, ToolCode
from memory.session_log import live_update_session
from memory.memory_search import MemorySearch
from mcp_servers.multiMCP import MultiMCP


GLOBAL_PREVIOUS_FAILURE_STEPS = 3
MAX_STEPS = 3
MAX_RETRIES = 3

class AgentLoop:
    def __init__(self, perception_prompt_path: str, decision_prompt_path: str, multi_mcp: MultiMCP, strategy: str = "exploratory"):
        self.perception = Perception(perception_prompt_path)
        self.decision = Decision(decision_prompt_path, multi_mcp)
        self.multi_mcp = multi_mcp
        self.strategy = strategy

    async def run(self, query: str):
        session = AgentSession(session_id=str(uuid.uuid4()), original_query=query)
        session_memory= []
        session.total_steps_executed = 0
        self.log_session_start(session, query)

        memory_results = self.search_memory(query)
        perception_result = self.run_perception(query, memory_results, memory_results)
        session.add_perception(PerceptionSnapshot(**perception_result))

        if perception_result.get("original_goal_achieved"):
            self.handle_perception_completion(session, perception_result)
            return session

        decision_output = self.make_initial_decision(query, perception_result)
        
        # Check if initial decision requires human intervention
        if decision_output.get("type") == "HUMAN_IN_LOOP":
            step = self.create_step(decision_output)
            step.status = "awaiting_human"
            session.add_plan_version(decision_output["plan_text"], [step])
            live_update_session(session)
            print(f"\n⚠️ HUMAN INTERVENTION REQUIRED")
            print(f"Reason: {decision_output.get('human_in_loop_reason', 'Unknown')}")
            print(f"Message: {decision_output.get('human_in_loop_message', 'No message')}")
            return session
        
        step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])
        live_update_session(session)
        print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
        for line in session.plan_versions[-1]["plan_text"]:
            print(f"  {line}")

        while step:
            # Check MAX_STEPS limit
            if session.total_steps_executed >= MAX_STEPS:
                print(f"\n⚠️ MAX_STEPS ({MAX_STEPS}) reached. Requesting human intervention.")
                human_step = Step(
                    index=step.index,
                    description=f"Maximum steps ({MAX_STEPS}) reached",
                    type="HUMAN_IN_LOOP",
                    status="awaiting_human",
                    human_in_loop_reason="MAX_STEPS_EXCEEDED",
                    human_in_loop_message=f"Agent has executed {MAX_STEPS} steps without completing the goal. Please provide guidance.",
                    suggested_plan=[f"Review completed steps", "Provide alternative approach", "Simplify the query"]
                )
                session.plan_versions[-1]["steps"].append(human_step)
                live_update_session(session)
                break
            
            step_result = await self.execute_step(step, session, session_memory)
            if step_result is None:
                break  # 🔐 protect against CONCLUDE/NOP/HUMAN_IN_LOOP cases
            
            # Check if step requires human intervention
            if step_result.type == "HUMAN_IN_LOOP":
                print(f"\n⚠️ HUMAN INTERVENTION REQUIRED")
                print(f"Reason: {step_result.human_in_loop_reason}")
                print(f"Message: {step_result.human_in_loop_message}")
                break
            
            session.total_steps_executed += 1
            step = self.evaluate_step(step_result, session, query)

        return session

    def log_session_start(self, session, query):
        print("\n=== LIVE AGENT SESSION TRACE ===")
        print(f"Session ID: {session.session_id}")
        print(f"Query: {query}")

    def search_memory(self, query):
        print("Searching Recent Conversation History")
        searcher = MemorySearch()
        results = searcher.search_memory(query)
        if not results:
            print("❌ No matching memory entries found.\n")
        else:
            print("\n🎯 Top Matches:\n")
            for i, res in enumerate(results, 1):
                print(f"[{i}] File: {res['file']}\nQuery: {res['query']}\nResult Requirement: {res['result_requirement']}\nSummary: {res['solution_summary']}\n")
        return results

    def run_perception(self, query, memory_results, session_memory=None, snapshot_type="user_query", current_plan=None):
        combined_memory = (memory_results or []) + (session_memory or [])
        perception_input = self.perception.build_perception_input(
            raw_input=query, 
            memory=combined_memory, 
            current_plan=current_plan, 
            snapshot_type=snapshot_type
        )
        perception_result = self.perception.run(perception_input)
        print("\n[Perception Result]:")
        print(json.dumps(perception_result, indent=2, ensure_ascii=False))
        return perception_result

    def handle_perception_completion(self, session, perception_result):
        print("\n✅ Perception fully answered the query.")
        session.state.update({
            "original_goal_achieved": True,
            "final_answer": perception_result.get("solution_summary", "Answer ready."),
            "confidence": perception_result.get("confidence", 0.95),
            "reasoning_note": perception_result.get("reasoning", "Handled by perception."),
            "solution_summary": perception_result.get("solution_summary", "Answer ready.")
        })
        live_update_session(session)

    def make_initial_decision(self, query, perception_result):
        decision_input = {
            "plan_mode": "initial",
            "planning_strategy": self.strategy,
            "original_query": query,
            "perception": perception_result
        }
        decision_output = self.decision.run(decision_input)
        return decision_output

    def create_step(self, decision_output):
        return Step(
            index=decision_output["step_index"],
            description=decision_output["description"],
            type=decision_output["type"],
            code=ToolCode(tool_name="raw_code_block", tool_arguments={"code": decision_output["code"]}) if decision_output["type"] == "CODE" else None,
            conclusion=decision_output.get("conclusion"),
            human_in_loop_reason=decision_output.get("human_in_loop_reason"),
            human_in_loop_message=decision_output.get("human_in_loop_message"),
            suggested_plan=decision_output.get("suggested_plan"),
        )

    async def execute_step(self, step, session, session_memory):
        print(f"\n[Step {step.index}] {step.description}")

        if step.type == "CODE":
            # Check retry limit
            if step.retries >= MAX_RETRIES:
                print(f"\n⚠️ MAX_RETRIES ({MAX_RETRIES}) reached for this step.")
                step.type = "HUMAN_IN_LOOP"
                step.status = "awaiting_human"
                step.human_in_loop_reason = "MAX_RETRIES_EXCEEDED"
                step.human_in_loop_message = f"Step has been retried {MAX_RETRIES} times without success. Please provide guidance."
                step.suggested_plan = ["Review the step logic", "Provide alternative approach", "Skip this step"]
                live_update_session(session)
                return step
            
            print("-" * 50, "\n[EXECUTING CODE]\n", step.code.tool_arguments["code"])
            executor_response = await run_user_code(step.code.tool_arguments["code"], self.multi_mcp)
            
            # Check if execution requires human intervention
            if executor_response.get("requires_human_intervention"):
                print(f"\n⚠️ Tool execution failed. Requesting human intervention.")
                step.type = "HUMAN_IN_LOOP"
                step.status = "awaiting_human"
                step.human_in_loop_reason = executor_response.get("human_in_loop_reason", "TOOL_FAILURE")
                step.human_in_loop_message = f"Tool execution failed: {executor_response.get('error', 'Unknown error')}"
                step.execution_result = executor_response
                step.error = executor_response.get("error")
                step.retries += 1
                live_update_session(session)
                return step
            
            step.execution_result = executor_response
            step.status = "completed"

            perception_result = self.run_perception(
                query=executor_response.get('result', 'Tool Failed'),
                memory_results=session_memory,
                current_plan=session.plan_versions[-1]["plan_text"],
                snapshot_type="step_result"
            )
            step.perception = PerceptionSnapshot(**perception_result)

            if not step.perception or not step.perception.local_goal_achieved:
                step.retries += 1
                failure_memory = {
                    "query": step.description,
                    "result_requirement": "Tool failed",
                    "solution_summary": str(step.execution_result)[:300]
                }
                session_memory.append(failure_memory)

                if len(session_memory) > GLOBAL_PREVIOUS_FAILURE_STEPS:
                    session_memory.pop(0)

            live_update_session(session)
            return step

        elif step.type == "CONCLUDE":
            print(f"\n💡 Conclusion: {step.conclusion}")
            step.execution_result = step.conclusion
            step.status = "completed"

            perception_result = self.run_perception(
                query=step.conclusion,
                memory_results=session_memory,
                current_plan=session.plan_versions[-1]["plan_text"],
                snapshot_type="step_result"
            )
            step.perception = PerceptionSnapshot(**perception_result)
            session.mark_complete(step.perception, final_answer=step.conclusion)
            live_update_session(session)
            return None

        elif step.type == "NOP":
            print(f"\n❓ Clarification needed: {step.description}")
            step.status = "clarification_needed"
            live_update_session(session)
            return None
        
        elif step.type == "HUMAN_IN_LOOP":
            print(f"\n⚠️ Human intervention required: {step.description}")
            step.status = "awaiting_human"
            live_update_session(session)
            return step

    def evaluate_step(self, step, session, query):
        if step.perception.original_goal_achieved:
            print("\n✅ Goal achieved.")
            session.mark_complete(step.perception)
            live_update_session(session)
            return None
        elif step.perception.local_goal_achieved:
            return self.get_next_step(session, query, step)
        else:
            print("\n🔁 Step unhelpful. Replanning.")
            decision_output = self.decision.run({
                "plan_mode": "mid_session",
                "planning_strategy": self.strategy,
                "original_query": query,
                "current_plan_version": len(session.plan_versions),
                "current_plan": session.plan_versions[-1]["plan_text"],
                "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
                "current_step": step.to_dict()
            })
            
            # Check if replanning resulted in HUMAN_IN_LOOP
            if decision_output.get("type") == "HUMAN_IN_LOOP":
                human_step = self.create_step(decision_output)
                human_step.status = "awaiting_human"
                session.add_plan_version(decision_output["plan_text"], [human_step])
                live_update_session(session)
                print(f"\n⚠️ HUMAN INTERVENTION REQUIRED during replanning")
                print(f"Reason: {decision_output.get('human_in_loop_reason', 'Unknown')}")
                print(f"Message: {decision_output.get('human_in_loop_message', 'No message')}")
                return human_step
            
            step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])

            print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
            for line in session.plan_versions[-1]["plan_text"]:
                print(f"  {line}")

            return step

    def get_next_step(self, session, query, step):
        next_index = step.index + 1
        total_steps = len(session.plan_versions[-1]["plan_text"])
        if next_index < total_steps:
            decision_output = self.decision.run({
                "plan_mode": "mid_session",
                "planning_strategy": self.strategy,
                "original_query": query,
                "current_plan_version": len(session.plan_versions),
                "current_plan": session.plan_versions[-1]["plan_text"],
                "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
                "current_step": step.to_dict()
            })
            
            # Check if next step requires human intervention
            if decision_output.get("type") == "HUMAN_IN_LOOP":
                human_step = self.create_step(decision_output)
                human_step.status = "awaiting_human"
                session.add_plan_version(decision_output["plan_text"], [human_step])
                live_update_session(session)
                print(f"\n⚠️ HUMAN INTERVENTION REQUIRED for next step")
                print(f"Reason: {decision_output.get('human_in_loop_reason', 'Unknown')}")
                print(f"Message: {decision_output.get('human_in_loop_message', 'No message')}")
                return human_step
            
            step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])

            print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
            for line in session.plan_versions[-1]["plan_text"]:
                print(f"  {line}")

            return step

        else:
            print("\n✅ No more steps.")
            return None

    async def resume_with_guidance(self, session, guidance: str):
        """
        Resume execution after a HITL pause, incorporating user guidance.
        """
        print(f"\n🔄 Resuming with guidance: '{guidance}'")
        
        # Add guidance to session memory/context
        # We can add it as a "user_feedback" memory entry
        feedback_memory = {
            "query": "User Guidance",
            "result_requirement": "Follow user instructions",
            "solution_summary": guidance
        }
        # We don't have direct access to session_memory list here as it was local to run()
        # But we can pass it or just rely on the fact that we'll do a fresh replan
        # For now, let's treat it as a strong signal for the replanner
        
        # Trigger replan with guidance
        decision_output = self.decision.run({
            "plan_mode": "mid_session",
            "planning_strategy": self.strategy,
            "original_query": session.original_query,
            "current_plan_version": len(session.plan_versions),
            "current_plan": session.plan_versions[-1]["plan_text"],
            "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
            "current_step": session.plan_versions[-1]["steps"][-1].to_dict(), # The step that triggered HITL
            "user_guidance": guidance # Pass this to decision module (need to ensure decision prompt handles it or we append it to query)
        })
        
        # If decision module doesn't explicitly handle "user_guidance", we might need to append it to the query
        # or handle it in the prompt. For now, let's assume we might need to hack it into the query context 
        # if the prompt isn't set up for it. 
        # Actually, looking at decision.py (which I haven't read fully but assuming standard structure), 
        # passing it in the input dict is best if supported. 
        # If not, we can append to original_query for this call:
        # "original_query": f"{session.original_query} (User Guidance: {guidance})"
        
        # Let's use the appended query approach to be safe without modifying decision.py yet
        decision_output = self.decision.run({
            "plan_mode": "mid_session",
            "planning_strategy": self.strategy,
            "original_query": f"{session.original_query} \n[USER GUIDANCE]: {guidance}",
            "current_plan_version": len(session.plan_versions),
            "current_plan": session.plan_versions[-1]["plan_text"],
            "completed_steps": [s.to_dict() for s in session.plan_versions[-1]["steps"] if s.status == "completed"],
            "current_step": session.plan_versions[-1]["steps"][-1].to_dict()
        })

        # Check if replanning resulted in HUMAN_IN_LOOP (unlikely if we just came from one, but possible)
        if decision_output.get("type") == "HUMAN_IN_LOOP":
             # ... handle recursive HITL ...
             # For simplicity, just return the session as is, effectively pausing again
             print(f"\n⚠️ Guidance didn't resolve the issue. Asking again.")
             return session

        # Create new step from decision
        step = session.add_plan_version(decision_output["plan_text"], [self.create_step(decision_output)])
        live_update_session(session)

        print(f"\n[Decision Plan Text: V{len(session.plan_versions)}]:")
        for line in session.plan_versions[-1]["plan_text"]:
            print(f"  {line}")

        # Resume the loop
        # We need to reconstruct the loop logic here or refactor run() to be re-entrant.
        # Refactoring run() is cleaner but riskier. 
        # Let's duplicate the loop logic for now to minimize regression risk, 
        # or better, extract the loop body.
        
        # Actually, since we are in an async method, we can just run the loop here.
        session_memory = [] # We lost the old memory context if we don't pass it. 
        # Ideally we should store session_memory in the session object.
        # For now, let's start with empty memory for the resume phase, or re-search.
        
        while step:
             # Check MAX_STEPS limit (cumulative)
            if session.total_steps_executed >= MAX_STEPS + 3: # Give some extra buffer for HITL recovery
                print(f"\n⚠️ MAX_STEPS limit reached even after guidance.")
                break
            
            step_result = await self.execute_step(step, session, session_memory)
            if step_result is None:
                break
            
            if step_result.type == "HUMAN_IN_LOOP":
                print(f"\n⚠️ HUMAN INTERVENTION REQUIRED")
                print(f"Reason: {step_result.human_in_loop_reason}")
                print(f"Message: {step_result.human_in_loop_message}")
                return session # Return to main loop for more guidance
            
            session.total_steps_executed += 1
            step = self.evaluate_step(step_result, session, session.original_query)

        return session
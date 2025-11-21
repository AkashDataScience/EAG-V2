from dataclasses import dataclass, asdict
from typing import Any, Literal, Optional, List
import uuid
import time
import json

@dataclass
class ToolCode:
    tool_name: str
    tool_arguments: dict[str, Any]

    def to_dict(self):
        return {
            "tool_name": self.tool_name,
            "tool_arguments": self.tool_arguments
        }


@dataclass
class PerceptionSnapshot:
    entities: list[str]
    result_requirement: str
    original_goal_achieved: bool
    reasoning: str
    local_goal_achieved: bool
    local_reasoning: str
    last_tooluse_summary: str
    solution_summary: str
    confidence: str

@dataclass
class Step:
    index: int
    description: str
    type: Literal["CODE", "CONCLUDE", "NOP", "HUMAN_IN_LOOP"]
    code: Optional[ToolCode] = None
    conclusion: Optional[str] = None
    execution_result: Optional[str] = None
    error: Optional[str] = None
    perception: Optional[PerceptionSnapshot] = None
    status: Literal["pending", "completed", "failed", "skipped", "awaiting_human"] = "pending"
    attempts: int = 0
    was_replanned: bool = False
    parent_index: Optional[int] = None
    human_in_loop_reason: Optional[str] = None
    human_in_loop_message: Optional[str] = None
    suggested_plan: Optional[List[str]] = None
    retries: int = 0

    def to_dict(self):
        return {
            "index": self.index,
            "description": self.description,
            "type": self.type,
            "code": self.code.to_dict() if self.code else None,
            "conclusion": self.conclusion,
            "execution_result": self.execution_result,
            "error": self.error,
            "perception": self.perception.__dict__ if self.perception else None,
            "status": self.status,
            "attempts": self.attempts,
            "was_replanned": self.was_replanned,
            "parent_index": self.parent_index,
            "human_in_loop_reason": self.human_in_loop_reason,
            "human_in_loop_message": self.human_in_loop_message,
            "suggested_plan": self.suggested_plan,
            "retries": self.retries
        }


class AgentSession:
    def __init__(self, session_id: str, original_query: str):
        self.session_id = session_id
        self.original_query = original_query
        self.perception: Optional[PerceptionSnapshot] = None
        self.plan_versions: list[dict[str, Any]] = []
        self.total_steps_executed: int = 0
        self.state = {
            "original_goal_achieved": False,
            "final_answer": None,
            "confidence": 0.0,
            "reasoning_note": "",
            "solution_summary": ""
            
        }

    def add_perception(self, snapshot: PerceptionSnapshot):
        self.perception = snapshot

    def add_plan_version(self, plan_texts: list[str], steps: list[Step]):
        plan = {
            "plan_text": plan_texts,
            "steps": steps.copy()
        }
        self.plan_versions.append(plan)
        return steps[0] if steps else None  # ✅ fix: return first Step

    def get_next_step_index(self) -> int:
        return sum(len(v["steps"]) for v in self.plan_versions)


    def to_json(self):
        return {
            "session_id": self.session_id,
            "original_query": self.original_query,
            "total_steps_executed": self.total_steps_executed,
            "perception": asdict(self.perception) if self.perception else None,
            "plan_versions": [
                {
                    "plan_text": p["plan_text"],
                    "steps": [asdict(s) for s in p["steps"]]
                } for p in self.plan_versions
            ],
            "state_snapshot": self.get_snapshot_summary()
        }

    def get_snapshot_summary(self):
        return {
            "session_id": self.session_id,
            "query": self.original_query,
            "final_plan": self.plan_versions[-1]["plan_text"] if self.plan_versions else [],
           "final_steps": [
                    asdict(s)
                    for version in self.plan_versions
                    for s in version["steps"]
                    if s.status == "completed"
                ],
            "final_answer": self.state["final_answer"],
            "confidence": self.state["confidence"],
            "reasoning_note": self.state["reasoning_note"]
        }

    def mark_complete(self, perception: PerceptionSnapshot, final_answer: Optional[str] = None, fallback_confidence: float = 0.95):
        self.state.update({
            "original_goal_achieved": perception.original_goal_achieved,
            "final_answer": final_answer or perception.solution_summary,
            "confidence": perception.confidence or fallback_confidence,
            "reasoning_note": perception.reasoning,
            "solution_summary": perception.solution_summary
        })



    def simulate_live(self, delay: float = 1.2):
        print("\n=== LIVE AGENT SESSION TRACE ===")
        print(f"Session ID: {self.session_id}")
        print(f"Query: {self.original_query}")
        time.sleep(delay)

        if self.perception:
            print("\n[Perception 0] Initial ERORLL:")
            print(f"  {asdict(self.perception)}")
            time.sleep(delay)

        for i, version in enumerate(self.plan_versions):
            print(f"\n[Decision Plan Text: V{i+1}]:")
            for j, p in enumerate(version["plan_text"]):
                print(f"  Step {j}: {p}")
            time.sleep(delay)

            for step in version["steps"]:
                print(f"\n[Step {step.index}] {step.description}")
                time.sleep(delay / 1.5)

                print(f"  Type: {step.type}")
                if step.code:
                    print(f"  Tool → {step.code.tool_name} | Args → {step.code.tool_arguments}")
                if step.execution_result:
                    print(f"  Execution Result: {step.execution_result}")
                if step.conclusion:
                    print(f"  Conclusion: {step.conclusion}")
                if step.error:
                    print(f"  Error: {step.error}")
                if step.type == "HUMAN_IN_LOOP":
                    print(f"  ⚠️ HUMAN INTERVENTION REQUIRED")
                    print(f"  Reason: {step.human_in_loop_reason}")
                    print(f"  Message: {step.human_in_loop_message}")
                    if step.suggested_plan:
                        print(f"  Suggested Plan:")
                        for i, plan_step in enumerate(step.suggested_plan):
                            print(f"    {i}: {plan_step}")
                if step.perception:
                    print("  Perception ERORLL:")
                    for k, v in asdict(step.perception).items():
                        print(f"    {k}: {v}")
                print(f"  Status: {step.status}")
                if step.retries > 0:
                    print(f"  Retries: {step.retries}")
                if step.was_replanned:
                    print(f"  (Replanned from Step {step.parent_index})")
                if step.attempts > 1:
                    print(f"  Attempts: {step.attempts}")
                time.sleep(delay)

        print("\n[Session Snapshot]:")
        print(json.dumps(self.get_snapshot_summary(), indent=2))

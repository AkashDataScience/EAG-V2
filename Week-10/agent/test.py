import json
from pathlib import Path
from agentSession import AgentSession, Step, ToolCode, PerceptionSnapshot

# Load JSON results
perception_data = json.loads(Path("perception_results.json").read_text())
decision_data = json.loads(Path("decision_results.json").read_text())

# Create session
session = AgentSession("Find number of BHK variants available in DLF Camelia from local sources.")

# Add initial perception
init_p = perception_data["initial"]
session.add_perception(PerceptionSnapshot(**init_p))

# === Plan Version 1 ===
plan_text_v1 = decision_data["initial_plan"]
steps_v1 = []
step0_def = decision_data["steps"]["0"]
step0 = Step(
    index=step0_def["index"],
    description=step0_def["description"],
    type=step0_def["type"],
    code=ToolCode(
                tool_name=step0_def["tool_name"],
                tool_arguments=step0_def["tool_arguments"]
                ) if step0_def["type"] == "CODE" else None
)
step0.attempts = 1
step0.execution_result, step0.error = None, "Failed or timeout"
step0.perception = PerceptionSnapshot(**perception_data["steps"]["0"])
step0.status = "failed"
steps_v1.append(step0)
session.add_plan_version(plan_text_v1, steps_v1)

# === Plan Version 2 ===
plan_text_v2 = ["Retry RAG with broader query scope", "Extract types from raw text.", "Summarize answer cleanly."]
steps_v2 = []
step1_def = decision_data["steps"]["1"]
step1 = Step(
    index=step1_def["index"],
    description=step1_def["description"],
    type=step1_def["type"],
    code=ToolCode(
                    tool_name=step1_def["tool_name"],
                    tool_arguments=step1_def["tool_arguments"]
                ) if step1_def["type"] == "CODE" else None if step1_def["type"] == "CODE" else None
)
step1.attempts = 1
step1.execution_result, step1.error = None, "Failed or timeout"
step1.perception = PerceptionSnapshot(**perception_data["steps"]["1"])
step1.status = "failed"
steps_v2.append(step1)
session.add_plan_version(plan_text_v2, steps_v2)

# === Plan Version 3 ===
plan_text_v3 = ["Use web search fallback to find BHK variant info", "Extract types from raw text.", "Summarize answer cleanly."]
steps_v3 = []
step2_def = decision_data["steps"]["1_replan"]
step2 = Step(
    index=step2_def["index"],
    description=step2_def["description"],
    type=step2_def["type"],
    code=ToolCode(
            tool_name=step2_def["tool_name"],
            tool_arguments=step2_def["tool_arguments"]
        ) if step2_def["type"] == "CODE" else None if step2_def["type"] == "CODE" else None
)
step2.attempts = 1
step2.execution_result, step2.error = "Found 3BHK, 4BHK, and 5BHK as official variants", None
step2.perception = PerceptionSnapshot(**perception_data["steps"]["2"])
step2.status = "completed"
steps_v3.append(step2)
session.add_plan_version(plan_text_v3, steps_v3)

# === Plan Version 4 ===
plan_text_v4 = ["Retry RAG with broader query scope", "Summarize answer cleanly."]
steps_v4 = []
step3_def = decision_data["steps"]["3"]
step3 = Step(
    index=step3_def["index"],
    description=step3_def["description"],
    type=step3_def["type"],
    conclusion="DLF Camelia has 3BHK, 4BHK, and 5BHK variants available.",
    status="completed"
)
step3.perception = PerceptionSnapshot(
    entities=["3BHK", "4BHK", "5BHK"],
    result_requirement="Final answer with all variants",
    original_goal_achieved=True,
    reasoning="Matches query perfectly.",
    local_goal_achieved=True,
    local_reasoning="All objectives clearly met."
)
steps_v4.append(step3)
session.add_plan_version(plan_text_v4, steps_v4)

# Final session state
session.state.update({
    "goal_satisfied": True,
    "final_answer": "DLF Camelia has 3BHK, 4BHK, and 5BHK variants available.",
    "confidence": 0.95,
    "reasoning_note": "Used fallback after two RAG failures. Result successful."
})

# Simulate
session.simulate_live()

# Print final JSON
# print(json.dumps(session.to_json(), indent=2))

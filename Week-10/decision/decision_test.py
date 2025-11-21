from decision import Decision
import json

def test_decision():
    decision = Decision()
    result = decision.run(
        prompt_path="prompts/decision_prompt.txt",
        decision_input={
            "plan_mode": "initial",
            "planning_strategy": "conservative",
            "original_query": "Find number of BHK variants available in DLF Camelia from local sources.",
            "perception": {
                "entities": ["DLF Camelia", "BHK variants", "local sources"],
                "result_requirement": "Numerical count of distinct BHK configurations...",
                "original_goal_achieved": False,
                "reasoning": "The user wants...",
                "local_goal_achieved": False,
                "local_reasoning": "This is just perception, no data retrieved yet."
            }
        }
    )
    print(json.dumps(result, indent=2))
    print(result)

test_decision()

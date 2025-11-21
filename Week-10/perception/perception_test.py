from perception import Perception
import asyncio

def test_perception():
    perception = Perception()
    result = perception.run(
        prompt_path="prompts/perception_prompt.txt",
        perception_input={
            "run_id": "abc",
            "snapshot_type": "user_query",
            "raw_input": "Find number of BHK variants available in DLF Camelia from local sources.",
            "memory_excerpt": {},
            "prev_objective": "",
            "prev_confidence": None,
            "timestamp": "2025-05-06T10:00:00Z",
            "schema_version": 1
        }
    )
    print(result)

test_perception()

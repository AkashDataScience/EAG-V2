import asyncio
import yaml
import json
import time
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from mcp_servers.multiMCP import MultiMCP
from agent.agent_loop2 import AgentLoop

load_dotenv()

# Test queries covering various scenarios
TEST_QUERIES = [
    # Math operations
    "What is 45 + 55?",
    "Calculate 123 * 456",
    "What is 100 divided by 5?",
    "Calculate 2 to the power of 10",
    "What is the square root of 144?",
    "Find the factorial of 7",
    "What is 17 modulo 5?",
    "Calculate sin(90 degrees)",
    "What is cos(0)?",
    "Calculate tan(45 degrees)",
    
    # String and conversion operations
    "Convert INDIA to ASCII values and sum them",
    "Find ASCII values of characters in HELLO",
    "Convert ABC to character codes",
    "Get ASCII sum of PYTHON",
    "Convert AGENT to ASCII and multiply by 2",
    
    # Fibonacci
    "Generate first 10 fibonacci numbers",
    "What are the first 5 fibonacci numbers?",
    "Calculate fibonacci sequence up to 8 terms",
    "Show me fibonacci numbers from 1 to 7",
    
    # Exponential operations
    "Calculate exponential sum of [1, 2, 3]",
    "Find e^1 + e^2 + e^3",
    "Compute exponential sum of first 5 integers",
    
    # Combined math operations
    "Add 10 and 20, then multiply by 3",
    "Calculate (50 + 50) / 10",
    "Find 2^8 and then add 100",
    "Multiply 7 by 8 and subtract 6",
    "Calculate 100 - 25 + 15",
    
    # Web search queries
    "Search for latest AI news",
    "Find information about Python programming",
    "Search for machine learning tutorials",
    "Look up quantum computing basics",
    "Find news about space exploration",
    
    # Document queries (will fail if no docs loaded, testing error handling)
    "Search stored documents for project information",
    "Find information about DLF Camelia",
    "Search local documents for pricing",
    "Look up apartment specifications",
    
    # URL/webpage queries
    "Convert https://example.com to markdown",
    "Extract content from https://python.org",
    "Get webpage content from https://github.com",
    
    # Complex multi-step queries
    "Calculate 5! and then find its square root",
    "Add 100 and 200, multiply by 2, then divide by 3",
    "Find fibonacci(10) and calculate its factorial",
    "Convert MATH to ASCII, sum them, then find square root",
    
    # Analytical queries
    "What is the relationship between AI and ML?",
    "Explain the difference between Python and JavaScript",
    "Compare supervised and unsupervised learning",
    "What are the benefits of cloud computing?",
    
    # Queries that should trigger clarification
    "Tell me about that thing",
    "Calculate the value",
    "Find information",
    "What is it?",
    
    # Edge cases
    "What is 0 divided by 0?",
    "Calculate factorial of -5",
    "Find square root of -1",
    "Divide 100 by 0",
    
    # Valid but complex
    "Calculate (10 + 20) * (30 - 15) / 5",
    "Find the sum of squares of first 5 natural numbers",
    "Calculate average of 10, 20, 30, 40, 50",
    "What is 15% of 200?",
    
    # String operations
    "Count characters in SIMULATOR",
    "Reverse the string HELLO",
    "Convert lowercase to uppercase: hello world",
    
    # Time and date
    "What is the current date?",
    "Calculate days between two dates",
    "What day of the week is today?",
    
    # Logical queries
    "Is 17 a prime number?",
    "Check if 100 is even",
    "Is 2024 a leap year?",
    
    # Data queries
    "Generate random number between 1 and 100",
    "Create a list of even numbers from 1 to 20",
    "Find all prime numbers less than 50",
    
    # Conversion queries
    "Convert 100 Celsius to Fahrenheit",
    "Convert 5 kilometers to miles",
    "Convert 1 hour to seconds",
    
    # Statistical queries
    "Calculate mean of [5, 10, 15, 20, 25]",
    "Find median of [1, 3, 5, 7, 9]",
    "Calculate standard deviation of [2, 4, 6, 8]",
    
    # Trigonometry
    "Calculate all trig functions for 30 degrees",
    "Find sin, cos, tan of 60 degrees",
    "What is the value of pi?",
    
    # Combinatorics
    "Calculate combinations of 5 choose 3",
    "Find permutations of 4 items taken 2 at a time",
    "How many ways to arrange 5 items?",
    
    # Series and sequences
    "Sum of first 100 natural numbers",
    "Calculate geometric series with ratio 2",
    "Find arithmetic progression sum",
    
    # Boolean logic
    "Evaluate True AND False",
    "What is True OR False?",
    "Calculate NOT True",
    
    # Nested operations
    "Calculate sqrt(add(multiply(5, 5), multiply(12, 12)))",
    "Find factorial of sum of 3 and 4",
    "Calculate power of 2 to the sum of 3 and 2",
    
    # Real-world scenarios
    "Calculate compound interest for 1000 at 5% for 2 years",
    "Find area of circle with radius 7",
    "Calculate volume of sphere with radius 3",
    "What is the perimeter of rectangle 10x20?",
    
    # Data processing
    "Sort the list [5, 2, 8, 1, 9]",
    "Find maximum in [10, 25, 15, 30, 5]",
    "Get minimum value from [100, 50, 75, 25]",
    
    # Pattern matching
    "Find all numbers in text: abc123def456",
    "Extract emails from text",
    "Match phone numbers in string",
    
    # Encoding/Decoding
    "Encode HELLO in base64",
    "Decode base64 string",
    "Hash the string PASSWORD",
    
    # File operations (testing error handling)
    "Read file data.txt",
    "List files in directory",
    "Check if file exists",
    
    # Network operations (testing error handling)
    "Ping google.com",
    "Check if website is up",
    "Get IP address",
    
    # System queries
    "What is the current time?",
    "Get system information",
    "Check available memory",
]

class Simulator:
    def __init__(self):
        self.results_file = Path("simulation_results.jsonl")
        self.results_file.parent.mkdir(parents=True, exist_ok=True)
        
    async def run_simulations(self, n: int = 120):
        """Run n simulations with random queries"""
        print(f"\n{'='*60}")
        print(f"🚀 STARTING SIMULATOR - {n} TESTS")
        print(f"{'='*60}\n")
        
        # Load MCP servers
        print("Loading MCP Servers...")
        with open("config/mcp_server_config.yaml", "r") as f:
            profile = yaml.safe_load(f)
            mcp_servers_list = profile.get("mcp_servers", [])
            configs = list(mcp_servers_list)
        
        multi_mcp = MultiMCP(server_configs=configs)
        await multi_mcp.initialize()
        
        loop = AgentLoop(
            perception_prompt_path="prompts/perception_prompt.txt",
            decision_prompt_path="prompts/decision_prompt.txt",
            multi_mcp=multi_mcp,
            strategy="exploratory"
        )
        
        # Run simulations
        for i in range(n):
            # Select random query or cycle through all
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            
            print(f"\n{'─'*60}")
            print(f"TEST {i+1}/{n}: {query}")
            print(f"{'─'*60}")
            
            start_time = time.time()
            
            try:
                session = await loop.run(query)
                elapsed = time.time() - start_time
                
                # Extract result
                result = {
                    "test_number": i + 1,
                    "query": query,
                    "session_id": session.session_id,
                    "success": session.state.get("original_goal_achieved", False),
                    "final_answer": session.state.get("final_answer"),
                    "confidence": session.state.get("confidence", 0.0),
                    "total_steps": session.total_steps_executed,
                    "plan_versions": len(session.plan_versions),
                    "elapsed_time_seconds": round(elapsed, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "completed"
                }
                
                # Check for human intervention
                if session.plan_versions:
                    last_plan = session.plan_versions[-1]
                    if last_plan["steps"]:
                        last_step = last_plan["steps"][-1]
                        if last_step.type == "HUMAN_IN_LOOP":
                            result["status"] = "human_intervention_required"
                            result["human_in_loop_reason"] = last_step.human_in_loop_reason
                            result["human_in_loop_message"] = last_step.human_in_loop_message
                
                print(f"\n✅ Test {i+1} completed: {result['status']}")
                print(f"   Success: {result['success']}, Steps: {result['total_steps']}, Time: {result['elapsed_time_seconds']}s")
                
            except Exception as e:
                elapsed = time.time() - start_time
                result = {
                    "test_number": i + 1,
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "elapsed_time_seconds": round(elapsed, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "error"
                }
                print(f"\n❌ Test {i+1} failed: {str(e)}")
            
            # Save result
            with open(self.results_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(result) + "\n")
            
            # Sleep to avoid rate limiting
            sleep_time = random.uniform(1.2, 3.5)
            print(f"   Sleeping for {sleep_time:.1f}s to avoid rate limiting...")
            await asyncio.sleep(sleep_time)
        
        print(f"\n{'='*60}")
        print(f"✅ SIMULATION COMPLETE - {n} tests finished")
        print(f"Results saved to: {self.results_file}")
        print(f"{'='*60}\n")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary of simulation results"""
        if not self.results_file.exists():
            print("No results file found.")
            return
        
        results = []
        with open(self.results_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    results.append(json.loads(line.strip()))
                except:
                    continue
        
        if not results:
            print("No results to summarize.")
            return
        
        total = len(results)
        successful = sum(1 for r in results if r.get("success"))
        errors = sum(1 for r in results if r.get("status") == "error")
        human_interventions = sum(1 for r in results if r.get("status") == "human_intervention_required")
        
        avg_time = sum(r.get("elapsed_time_seconds", 0) for r in results) / total
        avg_steps = sum(r.get("total_steps", 0) for r in results) / total
        
        print("\n📊 SIMULATION SUMMARY")
        print(f"{'─'*60}")
        print(f"Total Tests: {total}")
        print(f"Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"Errors: {errors} ({errors/total*100:.1f}%)")
        print(f"Human Interventions: {human_interventions} ({human_interventions/total*100:.1f}%)")
        print(f"Average Time: {avg_time:.2f}s")
        print(f"Average Steps: {avg_steps:.1f}")
        print(f"{'─'*60}\n")

async def main():
    simulator = Simulator()
    await simulator.run_simulations(n=120)

if __name__ == "__main__":
    asyncio.run(main())

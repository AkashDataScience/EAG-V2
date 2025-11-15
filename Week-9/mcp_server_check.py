from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json


async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server_math.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected to MCP server\n")

            # === CALL 1: strings_to_chars_to_int ===
            input1 = {"input": {"string": "INDIA"}}
            print(f"🔧 Calling: strings_to_chars_to_int\nInput: {input1}")
            result1 = await session.call_tool("strings_to_chars_to_int", input1)
            print(f"🧪 Raw MCP Result: {result1}\n")

            # Parse result1 safely
            ascii_json = result1.content[0].text
            ascii_values = json.loads(ascii_json)["result"]
            print(f"✅ Parsed ASCII values: {ascii_values}\n")

            # === CALL 2: int_list_to_exponential_sum ===
            input2 = {"input": {"numbers": ascii_values}}
            print(f"🔧 Calling: int_list_to_exponential_sum\nInput: {input2}")
            result2 = await session.call_tool("int_list_to_exponential_sum", input2)
            print(f"🧪 Raw MCP Result: {result2}\n")

            # Parse result2 safely
            exp_json = result2.content[0].text
            exp_sum = json.loads(exp_json)["result"]
            print(f"✅ Parsed exponential sum: {exp_sum}\n")

            # FINAL_ANSWER
            print("🎯 FINAL_ANSWER:", exp_sum)


if __name__ == "__main__":
    asyncio.run(main())

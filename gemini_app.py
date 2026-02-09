import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types

from dotenv import load_dotenv

load_dotenv()

# 1. Configuration: Use your actual API Key
HARDCODED_GEMINI_API_KEY = os.getenv("API_KEY")

# 2. Server Parameters
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"]
)

async def run_mission_analyst():
    # Initialize the modern Gemini Client
    client = genai.Client(api_key=HARDCODED_GEMINI_API_KEY)
    
    print("--- Gemini Satellite Mission Analyst AI ---")
    print("Agent active. Type your mission request.")
    print("Type 'exit' to quit.\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Step A: Register TAT-C Tools with Gemini
            mcp_tools = await session.list_tools()
            gemini_tools = types.Tool(function_declarations=[
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                } for tool in mcp_tools.tools
            ])

            while True:
                user_input = input("User > ")
                if user_input.lower() in ["exit", "quit"]:
                    break

                # Use types.Part(text=...) to avoid the positional argument error
                messages = [types.Content(role="user", parts=[types.Part(text=user_input)])]

                try:
                    while True:
                        # Step B: Multi-turn reasoning
                        response = await client.aio.models.generate_content(
                            model='gemini-3-flash-preview',
                            contents=messages,
                            config=types.GenerateContentConfig(tools=[gemini_tools])
                        )
                        
                        messages.append(response.candidates[0].content)

                        # Step C: Detect and execute function calls
                        function_calls = [
                            p.function_call for p in response.candidates[0].content.parts 
                            if p.function_call
                        ]
                        
                        if not function_calls:
                            print(f"\nAI Analyst >> {response.text}\n")
                            break

                        tool_responses = []
                        for fc in function_calls:
                            print(f"[*] AI executing: {fc.name} with {fc.args}")
                            result = await session.call_tool(fc.name, fc.args)
                            
                            # Add the tool result back to the conversation
                            tool_responses.append(types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result.content}
                            ))
                        
                        messages.append(types.Content(role="tool", parts=tool_responses))
                        
                except Exception as e:
                    print(f"\n[System Error] {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(run_mission_analyst())
"""
Gemini MCP Client - Interactive Chat Interface
Provides conversational interface for satellite mission analysis.
Implements multi-turn reasoning with automatic tool orchestration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession
from mcp.client.sse import sse_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import ICL-enhanced system prompts
from modules.icl.prompts import ROUTER_SYSTEM

load_dotenv()

# Configuration from environment
GEMINI_API_KEY = os.getenv("API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")


async def run_mission_analyst():
    """
    Executes interactive chat loop with LLM-driven tool orchestration.
    
    Establishes SSE connection to MCP server, registers available tools,
    and manages multi-turn conversations with automatic context management.
    """
    
    if not GEMINI_API_KEY:
        print("ERROR: API_KEY not found in .env file")
        return
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("=" * 70)
    print("🛰️  TAT-C Satellite Mission Analyst")
    print("=" * 70)
    print("RAG-Enhanced | Location Database Active")
    print("\nAgent ready. Type your mission request or 'exit' to quit.\n")

    async with sse_client("http://localhost:8000/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Retrieve MCP tools from server
            mcp_tools = await session.list_tools()
            print(f"[System] Loaded {len(mcp_tools.tools)} MCP tools\n")
            
            # Convert MCP tool schemas to Gemini function declarations
            gemini_tools = types.Tool(function_declarations=[
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                } for tool in mcp_tools.tools
            ])
            
            # Configure Gemini with ICL-enhanced prompts and tools
            config = types.GenerateContentConfig(
                system_instruction=ROUTER_SYSTEM,
                tools=[gemini_tools],
                temperature=0.0  # Deterministic for reproducibility
            )

            messages = []

            while True:
                user_input = input("User > ").strip()
                
                if user_input.lower() in ["exit", "quit"]:
                    print("\nGoodbye! 👋")
                    break

                messages.append(types.Content(
                    role="user", 
                    parts=[types.Part(text=user_input)]
                ))

                try:
                    iteration = 0
                    max_iterations = 10
                    
                    # Multi-turn reasoning loop (ReAct pattern)
                    while iteration < max_iterations:
                        iteration += 1
                        
                        # Generate response (may include function calls)
                        response = await client.aio.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=messages,
                            config=config
                        )
                        
                        messages.append(response.candidates[0].content)

                        # Extract function calls from response
                        function_calls = [
                            p.function_call 
                            for p in response.candidates[0].content.parts 
                            if p.function_call
                        ]
                        
                        if not function_calls:
                            # Final natural language response received
                            print(f"\n🤖 AI Analyst >> {response.text}\n")
                            
                            # Flush context after successful completion
                            if "SUCCESS" in response.text.upper():
                                print("[System] Task complete - context flushed\n")
                                messages = []
                            
                            break

                        # Execute tool calls via MCP
                        tool_responses = []
                        for fc in function_calls:
                            print(f"\n  [Tool Call {iteration}] {fc.name}")
                            for key, value in fc.args.items():
                                print(f"    {key}: {value}")
                            
                            result = await session.call_tool(fc.name, fc.args)
                            
                            # Extract text result from MCP response
                            result_text = result.content[0].text
                            
                            tool_responses.append(types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result_text}
                            ))
                        
                        messages.append(types.Content(role="tool", parts=tool_responses))
                    
                    if iteration >= max_iterations:
                        print(f"\n⚠️  Reached max iterations. Stopping.\n")
                        messages = []  # Reset context to prevent overflow
                        
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}\n")
                    if "429" in str(e):
                        print("⚠️  Rate limit hit. Wait 60 seconds and try again.\n")


if __name__ == "__main__":
    """Entry point with connection instructions."""
    
    print("=" * 70)
    print("Connecting to MCP server at http://localhost:8000")
    print("Make sure mcp_server.py is running in another terminal!")
    print("=" * 70)
    print()
    
    asyncio.run(run_mission_analyst())
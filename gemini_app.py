"""
Gemini MCP Client - Interactive Chat Interface (PRODUCTION STABLE)
Provides conversational interface for satellite mission analysis.
Implements multi-turn reasoning with automatic tool orchestration.

STABILITY FIXES:
- Event loop policy configuration for Windows
- Conversation history trimming (prevents memory leaks)
- Timeout handling for long operations
- Graceful error recovery
"""

import asyncio
import os
import sys
from pathlib import Path

# FIX #1: Configure event loop policy BEFORE any async operations
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("[System] Configured WindowsSelectorEventLoopPolicy for stability")

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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# FIX #2: Configuration constants for memory management
MAX_CONVERSATION_HISTORY = 10  # Keep only last 10 message pairs
REQUEST_TIMEOUT = 30.0  # 30 second timeout for LLM requests


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
    print("🛰️  TAT-C Satellite Mission Analyst - PRODUCTION STABLE")
    print("=" * 70)
    print("✓ RAG-Enhanced | Location Database Active")
    print("✓ Memory Management | Conversation History Limited")
    print("✓ Timeout Protection | 30s request limit")
    print("\nAgent ready. Type your mission request or 'exit' to quit.\n")

    try:
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

                    # FIX #2: Trim conversation history if too long
                    # Keeps memory bounded and prevents context overflow
                    if len(messages) > MAX_CONVERSATION_HISTORY:
                        print(f"[System] Trimming conversation history (keeping last {MAX_CONVERSATION_HISTORY} messages)")
                        messages = messages[-MAX_CONVERSATION_HISTORY:]

                    try:
                        iteration = 0
                        max_iterations = 10
                        
                        # Multi-turn reasoning loop (ReAct pattern)
                        while iteration < max_iterations:
                            iteration += 1
                            
                            try:
                                # FIX #5: Add timeout to prevent hanging on long operations
                                response = await asyncio.wait_for(
                                    client.aio.models.generate_content(
                                        model=GEMINI_MODEL,
                                        contents=messages,
                                        config=config
                                    ),
                                    timeout=REQUEST_TIMEOUT
                                )
                            except asyncio.TimeoutError:
                                print(f"\n⚠️  Request timed out after {REQUEST_TIMEOUT}s. The server may be processing a long simulation.")
                                print("    Try again or rephrase your query.\n")
                                # Remove the failed request from history
                                if messages and messages[-1].role == "user":
                                    messages.pop()
                                break
                            
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
                                
                                try:
                                    result = await session.call_tool(fc.name, fc.args)
                                    
                                    # Extract text result from MCP response
                                    result_text = result.content[0].text
                                    
                                    tool_responses.append(types.Part.from_function_response(
                                        name=fc.name,
                                        response={"result": result_text}
                                    ))
                                except Exception as tool_error:
                                    print(f"    ⚠️  Tool execution error: {str(tool_error)}")
                                    # Include error in response so LLM can handle it
                                    tool_responses.append(types.Part.from_function_response(
                                        name=fc.name,
                                        response={"result": f"ERROR: {str(tool_error)}"}
                                    ))
                            
                            if tool_responses:
                                messages.append(types.Content(role="tool", parts=tool_responses))
                        
                        if iteration >= max_iterations:
                            print(f"\n⚠️  Reached max iterations. Stopping.\n")
                            messages = []  # Reset context to prevent overflow
                            
                    except Exception as e:
                        print(f"\n❌ Error: {str(e)}\n")
                        if "429" in str(e) or "quota" in str(e).lower():
                            print("⚠️  Rate limit hit. Wait 60 seconds and try again.\n")
                        elif "connection" in str(e).lower():
                            print("⚠️  Connection error. Check if MCP server is running.\n")
                        
                        # Clean up failed message
                        if messages and messages[-1].role == "user":
                            messages.pop()
    
    except KeyboardInterrupt:
        print("\n\n[System] Received interrupt signal. Shutting down...")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        print("    Please restart the application.")


if __name__ == "__main__":
    """Entry point with connection instructions."""
    
    print("=" * 70)
    print("TAT-C Mission Analyst - Interactive Client")
    print("=" * 70)
    print("Connecting to MCP server at http://localhost:8000")
    print("Make sure mcp_server.py is running in another terminal!")
    print("=" * 70)
    print()
    
    try:
        asyncio.run(run_mission_analyst())
    except KeyboardInterrupt:
        print("\n[System] Shutdown complete")
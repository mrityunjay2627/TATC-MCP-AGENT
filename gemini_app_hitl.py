"""
Gemini MCP Client with Human-in-the-Loop (HITL)
Implements confidence-based intervention for safety-critical operations.
Supports three operational modes: always, auto, and never.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession
from mcp.client.sse import sse_client
from google import genai
from google.genai import types
from dotenv import load_dotenv
from modules.icl.prompts import ROUTER_SYSTEM
from modules.hitl.feedback_handler import (
    calculate_confidence_score,
    validate_coordinates
)

load_dotenv()

GEMINI_API_KEY = os.getenv("API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")


def get_human_approval(tool_call: dict, confidence: dict) -> tuple:
    """
    Requests human review of proposed tool invocation.
    
    Presents tool parameters and confidence assessment to user,
    allowing approval, modification, or rejection of AI actions.
    
    Args:
        tool_call: Tool invocation with name and arguments
        confidence: Multi-factor confidence assessment
    
    Returns:
        (approved: bool, modified_args: dict or None)
    """
    print("\n" + "=" * 70)
    print("🤔 HUMAN VERIFICATION REQUIRED")
    print("=" * 70)
    
    print(f"\nTool: {tool_call['name']}")
    print(f"Confidence: {confidence['overall']:.0%}")
    
    print("\nParameters:")
    for key, value in tool_call['args'].items():
        print(f"  {key}: {value}")
    
    # Display confidence warnings
    if confidence['overall'] < 0.7:
        print("\n⚠️  WARNING: Low confidence detected!")
        
        if confidence['coordinate_reliability'] < 0.5:
            print("  • Coordinates may need verification")
        
        if confidence['parameter_accuracy'] < 0.8:
            print("  • Some parameters may be missing or incorrect")
    
    # Validate coordinates if present
    args = tool_call['args']
    if 'latitude' in args and 'longitude' in args:
        lat, lon = args['latitude'], args['longitude']
        ctx = args.get('location_name', '')
        
        if not validate_coordinates(lat, lon, ctx):
            print(f"\n❌ COORDINATE ERROR DETECTED!")
            print(f"   ({lat}, {lon}) appears invalid for {ctx}")
            print(f"   Possible issues: wrong sign, out of range, or swapped")
    
    # Present intervention options
    print("\n" + "-" * 70)
    print("Options:")
    print("  [a] Approve - Execute as-is")
    print("  [m] Modify - Change parameters")
    print("  [r] Reject - Skip this tool call")
    print("  [c] Correct coordinates - Provide correct coordinates")
    
    while True:
        choice = input("\nYour choice [a/m/r/c]: ").strip().lower()
        
        if choice == 'a':
            print("✓ Approved by human")
            return True, None
        
        elif choice == 'r':
            print("✗ Rejected by human")
            return False, None
        
        elif choice == 'c':
            # Coordinate correction workflow
            print("\nProvide correct coordinates:")
            try:
                lat = float(input("  Latitude (-90 to 90): "))
                lon = float(input("  Longitude (-180 to 180): "))
                
                if validate_coordinates(lat, lon):
                    modified_args = tool_call['args'].copy()
                    modified_args['latitude'] = lat
                    modified_args['longitude'] = lon
                    
                    # Remove location_name if present (explicit coords take precedence)
                    if 'location_name' in modified_args:
                        del modified_args['location_name']
                    
                    print(f"✓ Coordinates corrected to ({lat}, {lon})")
                    return True, modified_args
                else:
                    print("❌ Invalid coordinates. Try again.")
                    continue
            except ValueError:
                print("❌ Invalid input. Try again.")
                continue
        
        elif choice == 'm':
            # General parameter modification
            print("\nCurrent parameters:")
            for i, (key, value) in enumerate(tool_call['args'].items(), 1):
                print(f"  {i}. {key}: {value}")
            
            try:
                param_num = int(input("\nWhich parameter to modify (number): "))
                param_keys = list(tool_call['args'].keys())
                
                if 1 <= param_num <= len(param_keys):
                    param_key = param_keys[param_num - 1]
                    new_value = input(f"New value for {param_key}: ").strip()
                    
                    # Type conversion based on original value
                    old_value = tool_call['args'][param_key]
                    if isinstance(old_value, int):
                        new_value = int(new_value)
                    elif isinstance(old_value, float):
                        new_value = float(new_value)
                    
                    modified_args = tool_call['args'].copy()
                    modified_args[param_key] = new_value
                    
                    print(f"✓ Modified {param_key}: {old_value} → {new_value}")
                    return True, modified_args
                else:
                    print("❌ Invalid parameter number")
                    continue
            except (ValueError, IndexError):
                print("❌ Invalid input. Try again.")
                continue
        
        else:
            print("Invalid choice. Please enter a, m, r, or c")


async def run_query_with_hitl(query: str, hitl_mode: str = "auto"):
    """
    Executes query with human-in-the-loop intervention based on confidence.
    
    Implements adaptive oversight: always mode requires approval for every
    tool, auto mode triggers intervention only when confidence < 70%,
    never mode executes without human review.
    
    Args:
        query: User's natural language question
        hitl_mode: Intervention strategy ('always', 'auto', 'never')
    """
    
    if not GEMINI_API_KEY:
        print("ERROR: API_KEY not found in .env file")
        return
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    print("\n" + "=" * 70)
    print("🛰️  PROCESSING QUERY (HITL ENABLED)")
    print("=" * 70)
    print(f"Query: {query}")
    print(f"HITL Mode: {hitl_mode.upper()}")
    print("=" * 70)

    try:
        async with sse_client("http://localhost:8000/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                mcp_tools = await session.list_tools()
                
                gemini_tools = types.Tool(function_declarations=[
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    } for tool in mcp_tools.tools
                ])
                
                config = types.GenerateContentConfig(
                    system_instruction=ROUTER_SYSTEM,
                    tools=[gemini_tools],
                    temperature=0.0
                )

                messages = [types.Content(
                    role="user", 
                    parts=[types.Part(text=query)]
                )]
                
                iteration = 0
                max_iterations = 10
                
                while iteration < max_iterations:
                    iteration += 1
                    
                    response = await client.aio.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=messages,
                        config=config
                    )
                    
                    messages.append(response.candidates[0].content)

                    function_calls = [
                        p.function_call 
                        for p in response.candidates[0].content.parts 
                        if p.function_call
                    ]
                    
                    if not function_calls:
                        # Final answer reached
                        print("\n" + "=" * 70)
                        print("📊 FINAL RESULT")
                        print("=" * 70)
                        print(response.text)
                        print("=" * 70)
                        break

                    # HITL: Review each proposed tool call
                    tool_responses = []
                    
                    for fc in function_calls:
                        tool_call = {'name': fc.name, 'args': dict(fc.args)}
                        
                        print(f"\n🔧 AI wants to call: {fc.name}")
                        
                        # Calculate multi-factor confidence score
                        has_location = 'location_name' in fc.args
                        has_coords = 'latitude' in fc.args and 'longitude' in fc.args
                        
                        confidence = calculate_confidence_score(
                            [tool_call],
                            has_location_name=has_location,
                            has_explicit_coords=has_coords
                        )
                        
                        # Determine if human review is needed based on mode
                        needs_review = False
                        
                        if hitl_mode == "always":
                            needs_review = True
                        elif hitl_mode == "auto":
                            # Trigger intervention for low confidence
                            if confidence['overall'] < 0.7:
                                needs_review = True
                        # hitl_mode == "never" -> no intervention
                        
                        # Request human approval if needed
                        if needs_review:
                            approved, modified_args = get_human_approval(tool_call, confidence)
                            
                            if not approved:
                                print("⏭️  Skipping this tool call")
                                continue
                            
                            if modified_args:
                                # Apply human corrections
                                fc.args.clear()
                                fc.args.update(modified_args)
                                print("✓ Using human-corrected parameters")
                        else:
                            # Auto-approve high confidence calls
                            print(f"  ✓ Auto-approved (confidence: {confidence['overall']:.0%})")
                            for key, val in fc.args.items():
                                print(f"    {key}: {val}")
                        
                        # Execute tool via MCP
                        print(f"  ⚙️  Executing...")
                        result = await session.call_tool(fc.name, fc.args)
                        result_text = result.content[0].text
                        
                        preview = result_text[:80] + "..." if len(result_text) > 80 else result_text
                        print(f"  ✓ Result: {preview}")
                        
                        tool_responses.append(types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result_text}
                        ))
                    
                    if not tool_responses:
                        # All tools rejected by human
                        print("\n⚠️  No tools executed. Cannot continue.")
                        break
                    
                    messages.append(types.Content(role="tool", parts=tool_responses))
                
                if iteration >= max_iterations:
                    print("\n⚠️  Reached max iterations")
                        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


async def interactive_hitl():
    """
    Interactive mode with configurable HITL intervention.
    
    Provides command interface for mode switching and query execution
    with human oversight capabilities.
    """
    
    print("=" * 70)
    print("🛰️  TAT-C Mission Analyst - HITL MODE")
    print("=" * 70)
    print("\nHuman-in-the-Loop: You can approve, modify, or reject AI actions!")
    print("\nCommands:")
    print("  - Type your question")
    print("  - 'mode always/auto/never' - Change HITL intervention level")
    print("  - 'exit' to quit")
    print("\nHITL Modes:")
    print("  • always - Ask for approval on EVERY tool call")
    print("  • auto   - Ask only when confidence is low (default)")
    print("  • never  - Auto-execute everything (no HITL)")
    print("=" * 70)
    
    hitl_mode = "auto"
    
    while True:
        print(f"\n[HITL: {hitl_mode.upper()}]")
        user_input = input("Query > ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ["exit", "quit"]:
            print("\n👋 Goodbye!")
            break
        
        if user_input.lower().startswith("mode "):
            new_mode = user_input.split()[1].lower()
            if new_mode in ["always", "auto", "never"]:
                hitl_mode = new_mode
                print(f"✓ HITL mode set to: {hitl_mode.upper()}")
            else:
                print("❌ Invalid mode. Use: always, auto, or never")
            continue
        
        await run_query_with_hitl(user_input, hitl_mode)


if __name__ == "__main__":
    """Entry point with command-line argument parsing."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="TAT-C Mission Analyst with HITL")
    parser.add_argument(
        '--hitl',
        choices=['always', 'auto', 'never'],
        default='auto',
        help='HITL intervention mode (default: auto)'
    )
    parser.add_argument(
        '--query',
        type=str,
        help='Direct query (skips interactive mode)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Connecting to MCP server at http://localhost:8000")
    print("Make sure mcp_server.py is running!")
    print("=" * 70)
    print()
    
    if args.query:
        asyncio.run(run_query_with_hitl(args.query, args.hitl))
    else:
        asyncio.run(interactive_hitl())
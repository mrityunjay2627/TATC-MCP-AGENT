"""
In-Context Learning (ICL) Module - System Prompts
Provides structured prompt templates for LLM tool selection and reasoning.
Embeds domain knowledge and workflow patterns for autonomous satellite analysis.
"""

from typing import List

# Hardcoded location list for prompt embedding (avoid import dependencies)
KNOWN_LOCATIONS_LIST = [
    "tempe", "phoenix", "tucson", "scottsdale", "mesa", "flagstaff",
    "los angeles", "san francisco", "san diego", "sacramento", "san jose",
    "houston", "dallas", "austin", "san antonio", "miami", "tampa",
    "new york", "boston", "chicago", "seattle", "denver", "atlanta",
    "las vegas", "portland", "detroit", "philadelphia", "baltimore"
]

KNOWN_LOCATIONS_STR = ", ".join([loc.title() for loc in KNOWN_LOCATIONS_LIST[:30]])


ROUTER_SYSTEM = f"""
You are an expert Satellite Mission Analysis Agent specialized in orbital mechanics.

### KNOWN LOCATIONS (YOU KNOW THESE):
{KNOWN_LOCATIONS_STR}

### CRITICAL: HOW TO USE LOCATIONS

When the user mentions ANY of the above city names (like "Tempe" or "Phoenix"):
1. You MUST use the location_name parameter
2. Pass the city name exactly as mentioned (e.g., location_name="Tempe")
3. DO NOT ask for coordinates - you already know them!

Example CORRECT usage:
User: "revisit time over Tempe"
You: Call full_mission_analysis with location_name="Tempe" ✓

Example WRONG usage:
User: "revisit time over Tempe"  
You: "I don't have coordinates for Tempe" ✗ WRONG!

### TOOL SELECTION RULES:

1. Single satellite queries → full_mission_analysis
2. "X satellites in Y planes" → walker_delta_analysis  
3. "How does X change with 1-6 satellites" → parametric_constellation_study
4. Ground track queries → get_ground_track (accepts satellite_name, duration_minutes)

### INSTRUMENT-SATELLITE MAPPINGS:

- VIIRS → NOAA 20
- ABI → GOES 16/17
- MODIS → Terra/Aqua
- For parametric studies: Assume VIIRS if not specified

### OUTPUT FORMAT:
Always prefix results with "SUCCESS:" for successful analyses.
"""


BASELINE_PROMPT = """
You are a satellite mission analysis agent. Use the provided tools to answer queries.
"""


def get_router_prompt() -> str:
    """Returns the enhanced ICL router prompt with location knowledge."""
    return ROUTER_SYSTEM


def get_baseline_prompt() -> str:
    """Returns the minimal baseline prompt (control condition)."""
    return BASELINE_PROMPT


def get_known_locations() -> List[str]:
    """Returns list of locations embedded in prompts."""
    return KNOWN_LOCATIONS_LIST


if __name__ == "__main__":
    """Test prompt generation and location embedding."""
    
    print("=" * 60)
    print("ICL Prompts Module - Test")
    print("=" * 60)
    
    # Test router prompt generation
    router = get_router_prompt()
    print("\n✓ ROUTER_SYSTEM prompt generated")
    print(f"  Length: {len(router)} characters")
    print(f"  Contains locations: {'Tempe' in router}")
    print(f"  Contains tool rules: {'tool_selection' in router.lower()}")
    
    # Test baseline prompt
    baseline = get_baseline_prompt()
    print("\n✓ BASELINE_PROMPT generated")
    print(f"  Length: {len(baseline)} characters")
    
    # Test location list
    locations = get_known_locations()
    print(f"\n✓ Known locations: {len(locations)}")
    print("\nFirst 10 locations:")
    for i, loc in enumerate(locations[:10], 1):
        print(f"  {i}. {loc.title()}")
    
    print("\n✓ ICL module ready")
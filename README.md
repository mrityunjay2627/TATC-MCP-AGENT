# TAT-C Agentic Mission Analysis Framework

**A Model Context Protocol (MCP) framework enabling natural language interaction with satellite constellation analysis tools.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Understanding the Phases](#understanding-the-phases)
- [Example Scenarios](#example-scenarios)
- [Human-in-the-Loop (HITL)](#human-in-the-loop-hitl)
- [Running Evaluations](#running-evaluations)
- [Project Structure](#project-structure)
- [Citation](#citation)

---

## Overview

This project demonstrates how Large Language Models (LLMs) can orchestrate complex aerospace simulation workflows through three progressive enhancement techniques:

1. **Baseline**: Basic MCP integration with minimal guidance
2. **In-Context Learning (ICL)**: Enhanced prompts with tool selection rules
3. **Retrieval-Augmented Generation (RAG)**: Location database grounding to prevent hallucination
4. **Human-in-the-Loop (HITL)**: Confidence-based intervention for safety-critical operations

The framework integrates with **TAT-C** (Tradespace Analysis Toolkit for Constellations) to perform satellite mission analysis through natural language queries.

---

## Key Features

- 🛰️ **Natural Language Interface**: Ask questions about satellite missions in plain English
- 🔧 **4 MCP Tools**: Single-satellite analysis, constellation design, parametric studies, ground tracks
- 🗺️ **RAG Location Database**: 50+ cities with automatic coordinate resolution
- 🤖 **ICL Prompt Engineering**: Structured prompts with semantic mappings
- 👤 **HITL Safety Net**: Confidence-based human verification
- 📊 **Comprehensive Metrics**: Track workflow correctness, hallucination rates, runtime

---

## Architecture

```
┌─────────────────┐
│   User Query    │ "What's the revisit time over Phoenix?"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini 2.0     │ (Cognitive Layer)
│  Flash Agent    │ • Intent parsing
└────────┬────────┘ • Tool selection
         │          • Multi-turn reasoning
         ▼
┌─────────────────┐
│   MCP Server    │ (Interface Layer)
│  4 TAT-C Tools  │ • Location resolution (RAG)
└────────┬────────┘ • Semantic distillation
         │          • Schema validation
         ▼
┌─────────────────┐
│   TAT-C Core    │ (Execution Layer)
│   Simulation    │ • Orbital propagation
└─────────────────┘ • Coverage analysis
```

**Three-Tier Design:**
- **Tier 1 (Cognitive)**: Gemini 2.0 Flash for reasoning and orchestration
- **Tier 2 (Interface)**: MCP server with RAG/ICL enhancements
- **Tier 3 (Execution)**: TAT-C simulation engine with real TLE data

---

## Installation

### Prerequisites

- Python 3.12+
- Google Gemini API key
- Terminal/command line access

### Setup Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd tatc-mcp-framework

# 2. Install dependencies
pip install -r requirements.txt --break-system-packages

# 3. Create .env file with your API key
echo "API_KEY=your_gemini_api_key_here" > .env
echo "GEMINI_MODEL=gemini-2.0-flash-exp" >> .env

# 4. Verify installation
python -c "import tatc; print('TAT-C installed successfully')"
```

---

## Quick Start

### Running the System

**Terminal 1: Start MCP Server**
```bash
python mcp_server.py
```

**Terminal 2: Start Interactive Client**
```bash
python gemini_app.py
```

### Your First Query

```
User > What is the mean revisit period over Tempe for NOAA 20 with VIIRS?

  [Tool Call 1] full_mission_analysis
    satellite_name: NOAA 20
    instrument_name: VIIRS
    location_name: Tempe

🤖 AI Analyst >> The mean revisit time over Tempe, Arizona for the VIIRS 
instrument on NOAA 20 is approximately 11.50 hours based on 3 passes 
over a 24-hour period.
```

---

## Understanding the Phases

### Phase 1: Baseline (No Enhancements)

**What it is**: Basic MCP integration with minimal system prompt. The LLM has access to tools but limited guidance.

**Limitations**:
- ❌ Often selects wrong tools
- ❌ May not recognize location names
- ❌ Struggles with implicit parameter inference

**Example Query**: *"What's the revisit time over Tempe for NOAA 20?"*

**Baseline Response**:
```
❌ FAILURE: "I don't have coordinates for Tempe. Please provide 
latitude and longitude."
```
**Why it fails**: No location database, no guidance on handling city names.

---

### Phase 2: In-Context Learning (ICL)

**What it is**: Enhanced system prompts with explicit tool selection rules, semantic mappings, and workflow guidance.

**Improvements**:
- ✅ Structured tool selection logic
- ✅ Instrument-to-satellite mappings (e.g., VIIRS → NOAA 20)
- ✅ Embedded location list awareness (locations shown IN the prompt)
- ✅ Parameter defaulting strategies

**How ICL Works**:
```
System Prompt includes:
"### KNOWN LOCATIONS (YOU KNOW THESE):
Tempe, Phoenix, Tucson, Los Angeles, San Francisco, ...

When user mentions ANY of these cities:
1. Use location_name parameter
2. Pass city name exactly as mentioned"
```

**Same Query with ICL**:

**Input**: *"What's the revisit time over Tempe for NOAA 20?"*

**ICL Response**:
```
✓ SUCCESS: The LLM now knows from the PROMPT:
  - Tempe is in the hardcoded list shown in system prompt
  - Should use location_name parameter
  - VIIRS is the instrument on NOAA 20
  
  [Tool Call] full_mission_analysis
    satellite_name: NOAA 20
    instrument_name: VIIRS
    location_name: Tempe
    
Result: "Mean revisit is 11.50 hours based on 3 passes."
```

**Key Difference**: ICL provides *knowledge embedded in prompts* - the LLM "sees" the location list as text.

---

### Phase 3: Retrieval-Augmented Generation (RAG)

**What it is**: ICL + Dynamic location database with 50+ cities. The MCP server performs **runtime lookup** to resolve city names to coordinates.

**How RAG is Different from ICL**:

| Aspect | ICL | RAG |
|--------|-----|-----|
| **Location Source** | Hardcoded in prompt text | Database lookup at runtime |
| **Coverage** | ~30 cities (limited by prompt length) | 50+ cities (expandable) |
| **Flexibility** | Static list | Dynamic database queries |
| **Typo Handling** | ❌ Must match exactly | ✅ Fuzzy matching (Tmepe→Tempe) |
| **Validation** | ❌ No checking | ✅ Hemisphere validation |
| **Scalability** | ❌ Limited by context window | ✅ Can add 1000s of cities |

**How RAG Resolution Works**:
```python
# MCP Server receives: location_name="Tempe"
# Step 1: Database lookup
coords = resolve_location("Tempe")  
# Returns: (33.4255, -111.9400)

# Step 2: Validation
validate_coordinates(33.4255, -111.9400, "Tempe")
# Checks: Is longitude negative? (US = Western hemisphere)

# Step 3: Return to simulation
```

**RAG Unique Features**:
- ✅ Automatic coordinate resolution
- ✅ Fuzzy matching (handles typos: "Tmepe" → Tempe, "Pheonix" → Phoenix)
- ✅ Hemisphere validation (catches coordinate errors)
- ✅ Zero coordinate hallucination guarantee
- ✅ Expandable without changing prompts

**Comparison Example**:

| Query | Baseline | ICL | RAG |
|-------|----------|-----|-----|
| "Revisit over Phoenix" | ❌ "Need coordinates" | ✅ Works (if in prompt list) | ✅ Database lookup |
| "Revisit over Tmepe" (typo) | ❌ Fails | ❌ Fails (exact match only) | ✅ Fuzzy matches to Tempe |
| "Revisit at (33, 112)" | ✅ Works | ✅ Works | ✅ Validates: Wrong hemisphere! |
| "Revisit over Flagstaff" | ❌ Fails | ⚠️ Only if in prompt | ✅ Works (database has it) |

**Why RAG > ICL for Locations**:
1. **Scalability**: Can't fit 1000 cities in a prompt, but can in a database
2. **Robustness**: Fuzzy matching handles real-world typos
3. **Validation**: Detects coordinate swap errors and wrong signs
4. **Maintainability**: Update database without changing prompts
5. **Hallucination Prevention**: LLM can't invent coordinates—they MUST come from database

---

## Example Scenarios

### Scenario 1: Basic Single Satellite Analysis

**Baseline vs. ICL vs. RAG**

```bash
Query: "What is the mean revisit time over San Francisco for NOAA 20?"
```

**Baseline Output**:
```
❌ Agent asks: "I need the latitude and longitude for San Francisco."
   
Reason: No location knowledge, no guidance to use location_name parameter
```

**ICL Output**:
```
✅ Agent recognizes San Francisco in hardcoded list (shown in prompt)
✅ Calls: full_mission_analysis(satellite_name="NOAA 20", 
                                 instrument_name="VIIRS",
                                 location_name="San Francisco")
✅ Result: "Mean revisit is 10.25 hours based on 4 passes."

Reason: ICL prompt says "when user mentions city, use location_name"
```

**RAG Output**:
```
✅ Same as ICL, but MCP server performs runtime database lookup:
   resolve_location("San Francisco") → (37.7749, -122.4194)
   
✅ Server validates: Coordinates in Western hemisphere (correct for US)
✅ Result: Same accuracy, but with built-in hallucination prevention

Reason: Database grounding ensures coordinates are never fabricated
```

---

### Scenario 2: Constellation Design

**Understanding Tool Selection**

```bash
Query: "What's the revisit time for 9 satellites in 3 planes over Denver?"
```

**Baseline Output**:
```
❌ Calls: full_mission_analysis (WRONG TOOL!)
   
Reason: Doesn't recognize constellation keywords
```

**ICL Output**:
```
✅ ICL prompt has rule: "X satellites in Y planes → walker_delta_analysis"
✅ Calls: walker_delta_analysis(satellite_name="NOAA 20",
                                 instrument_name="VIIRS",
                                 num_satellites=9,
                                 num_planes=3,
                                 location_name="Denver")
✅ Result: "Constellation mean revisit is 3.8 hours."

Reason: Explicit tool selection rules in system prompt
```

**RAG Output**:
```
✅ Same as ICL with runtime location resolution
✅ Denver → database lookup → (39.7392, -104.9903)
✅ Prevents hallucination if user had typo: "Dnever" → fuzzy matches to Denver
```

---

### Scenario 3: Parametric Study

**Showing Scaling Relationships**

```bash
Query: "How does revisit time change with 1-6 satellites per plane over Phoenix?"
```

**Baseline Output**:
```
❌ May call wrong tool or ask for clarification
```

**ICL/RAG Output**:
```
✅ Recognizes parametric scaling query
✅ Calls: parametric_constellation_study(location_name="Phoenix")
✅ Result:
   
   | Sats/Plane | Total | Mean Revisit (hrs) |
   |------------|-------|-------------------|
   | 1          | 3     | 10.2              |
   | 2          | 6     | 5.1               |
   | 3          | 9     | 3.4               |
   | 4          | 12    | 2.5               |
   | 5          | 15    | 2.0               |
   | 6          | 18    | 1.7               |
```

---

### Scenario 4: Coordinate Validation (RAG Strength)

**Catching Errors**

```bash
Query: "Revisit time at coordinates (33.4, 111.9) for Phoenix"
                                            ↑
                                      WRONG SIGN!
```

**Baseline/ICL Output**:
```
⚠️ Accepts coordinates blindly
⚠️ Simulation runs but results are for wrong location (Eastern hemisphere)
```

**RAG Output**:
```
✅ validate_coordinates(33.4, 111.9, "Phoenix") → FALSE
✅ Returns: "ERROR: Invalid coordinates (33.4, 111.9). Phoenix is in 
            Western hemisphere (negative longitude expected)."
            
Reason: Hemisphere validation based on location context
```

---

### Scenario 5: Typo Handling (RAG vs ICL)

**Testing Fuzzy Matching**

```bash
Query: "What's the revisit over Tmepe for NOAA 20?"  
                                    ↑
                                 TYPO
```

**Baseline Output**:
```
❌ "I don't have coordinates for Tmepe."
```

**ICL Output**:
```
❌ "I don't recognize 'Tmepe' in my location list. Did you mean Tempe?"
   
Reason: ICL has hardcoded list but requires exact match
```

**RAG Output**:
```
✅ Fuzzy matching: Levenshtein distance calculation
✅ "Tmepe" matches to "Tempe" (1 character difference, 80% similarity)
✅ Automatically resolves to (33.4255, -111.9400)
✅ Result: "Mean revisit is 11.50 hours..."

Reason: Database uses get_close_matches() with 0.8 cutoff
```

---

### Scenario 6: Unlisted City (Scalability Test)

**Database vs Prompt Limitation**

```bash
Query: "Revisit time over Flagstaff, Arizona"
```

**Baseline Output**:
```
❌ "I need coordinates for Flagstaff."
```

**ICL Output**:
```
⚠️ Depends on whether Flagstaff is in the hardcoded prompt list
   - If YES: Works (but prompt is getting long)
   - If NO: Fails like baseline
   
Limitation: Can only fit ~30 cities in prompt before context overflow
```

**RAG Output**:
```
✅ Database lookup succeeds: Flagstaff → (35.1983, -111.6513)
✅ Can store 50+ cities without prompt bloat
✅ Easily expandable to 1000s of cities

Reason: Database scales independently of prompt length
```

---

### Scenario 7: Ground Track Visualization

**Tool Understanding**

```bash
Query: "Show me the ground track for NOAA 20 over 30 minutes"
```

**Baseline Output**:
```
❌ May confuse with revisit analysis
❌ Or: "I cannot visualize, but I can describe the path"
```

**ICL Output**:
```
✅ Tool rule: "ground track queries → get_ground_track"
✅ Calls: get_ground_track(satellite_name="NOAA 20",
                           duration_minutes=30)
✅ Result: "Calculated ground track polygon. 
           Bounds: Lat (33.00 to 34.00), Lon (-112.00 to -111.00).
           Area covered: 1.00 sq degrees."
           
Reason: Explicit mapping in ICL prompt
```

**RAG Output**:
```
✅ Same as ICL (ground track doesn't require location resolution)
```

---

### Scenario 8: Instrument Inference

**Semantic Understanding**

```bash
Query: "Revisit time over Miami for the VIIRS instrument"
```

**Baseline Output**:
```
⚠️ May ask: "Which satellite carries VIIRS?"
```

**ICL Output**:
```
✅ Instrument mapping in prompt: "VIIRS → NOAA 20"
✅ Automatically infers satellite_name="NOAA 20"
✅ Calls: full_mission_analysis(satellite_name="NOAA 20",
                                 instrument_name="VIIRS",
                                 location_name="Miami")
                                 
Reason: ICL includes instrument-to-satellite knowledge
```

**RAG Output**:
```
✅ Same instrument inference as ICL
✅ PLUS: Miami → (25.7617, -80.1918) via database
✅ Validates: Latitude ~26°N makes sense for Florida
```

---

### Scenario 9: Complex Constellation Query

**Multi-Parameter Reasoning**

```bash
Query: "Compare 6 satellites vs 12 satellites in 3 planes over Los Angeles"
```

**Baseline Output**:
```
❌ Confused by comparison request
❌ May attempt single analysis instead of parametric study
```

**ICL Output**:
```
✅ Recognizes comparison → parametric study needed
✅ But user specified specific counts (6 and 12)
✅ Intelligently calls walker_delta_analysis TWICE:
   
   Call 1: num_satellites=6, num_planes=3, location_name="Los Angeles"
   Result: "Mean revisit: 5.2 hours"
   
   Call 2: num_satellites=12, num_planes=3, location_name="Los Angeles"
   Result: "Mean revisit: 2.6 hours"
   
✅ Synthesizes: "Doubling satellites from 6 to 12 halves revisit time"

Reason: ICL enables multi-step reasoning with tool sequencing
```

**RAG Output**:
```
✅ Same multi-tool workflow
✅ Los Angeles → (34.0522, -118.2437) resolved once, used twice
✅ Validates coordinates for both calls
```

---

### Scenario 10: Hemisphere Error Detection (RAG Only)

**Catching User Mistakes**

```bash
Query: "Revisit over Seattle at coordinates (47.6, 122.3)"
                                                      ↑
                                              MISSING MINUS SIGN
```

**Baseline Output**:
```
⚠️ Accepts (47.6, 122.3) blindly
⚠️ Runs simulation for location in Asia (Eastern hemisphere)
⚠️ Returns incorrect results
```

**ICL Output**:
```
⚠️ Same as baseline - no coordinate validation
⚠️ ICL only helps with tool selection, not data quality
```

**RAG Output**:
```
✅ validate_coordinates(47.6, 122.3, "Seattle") → FALSE
✅ Detects: Seattle is in US → should have negative longitude
✅ Returns: "ERROR: Invalid coordinates (47.6, 122.3). 
            Seattle is in Western hemisphere (negative longitude expected).
            Did you mean (47.6, -122.3)?"
            
Reason: RAG includes semantic validation based on location context
```

---

### Scenario 11: Ambiguous Query Resolution

**Context Understanding**

```bash
Query: "What's the coverage for GOES-16?"
```

**Baseline Output**:
```
❌ "Coverage of what? I need a location."
```

**ICL Output**:
```
⚠️ May ask for clarification
OR
✅ Infers: "ground track" is most likely for a single satellite
✅ Calls: get_ground_track(satellite_name="GOES-16")
✅ Uses default 30-minute duration

Reason: ICL includes default parameter strategy
```

**RAG Output**:
```
✅ Same as ICL (no location needed for geostationary satellite path)
```

---

### Scenario 12: Synthesis Question (No Tools Needed)

**Pure Reasoning Test**

```bash
Query: "Why would I use a constellation instead of a single satellite?"
```

**All Phases Output**:
```
✅ Baseline: Can answer (doesn't need tools)
✅ ICL: Better structured answer
✅ RAG: Same as ICL

Response: "A constellation provides:
  • Reduced revisit times through distributed coverage
  • Redundancy if one satellite fails
  • Better temporal resolution
  • More frequent observations of targets
  
  Trade-offs include higher cost and complexity."
  
Reason: This tests reasoning, not tool use - all phases handle it
```

---

## Quick Reference: When Each Phase Excels

| Scenario | Baseline | ICL | RAG | Winner |
|----------|----------|-----|-----|--------|
| Known city (exact match) | ❌ | ✅ | ✅ | ICL/RAG |
| City with typo | ❌ | ❌ | ✅ | **RAG** |
| Unlisted city | ❌ | ❌ | ✅ | **RAG** |
| Tool selection | ❌ | ✅ | ✅ | **ICL** |
| Instrument inference | ⚠️ | ✅ | ✅ | **ICL** |
| Coordinate validation | ❌ | ❌ | ✅ | **RAG** |
| Hemisphere checking | ❌ | ❌ | ✅ | **RAG** |
| Explicit coordinates | ✅ | ✅ | ✅ | All |
| Pure reasoning | ✅ | ✅ | ✅ | All |
| Scalability (1000+ cities) | ❌ | ❌ | ✅ | **RAG** |

**Key Insight**: 
- **ICL** = Better decision making (tool selection, semantic understanding)
- **RAG** = Better data quality (coordinate grounding, validation, scalability)
- **Together** = Best of both worlds!

---

## Human-in-the-Loop (HITL)

### When to Use HITL

HITL provides **confidence-based intervention** for safety-critical operations. Three modes:

| Mode | When to Use | Behavior |
|------|-------------|----------|
| **always** | Safety-critical missions, high-stakes decisions | Approve EVERY tool call |
| **auto** | Normal operations (default) | Approve if confidence ≥ 70% |
| **never** | Exploratory analysis, low-risk queries | Auto-execute everything |

### Starting HITL Client

```bash
python gemini_app_hitl.py --hitl auto
```

### Example: Low Confidence Triggers Review

**Query**: *"Revisit time over coordinates (85, -50) for NOAA 20"*

**Why Low Confidence?**
- ❌ Unusual latitude (85° is near North Pole)
- ❌ No location context provided
- ❌ Coordinates without known source

**HITL Workflow**:

```
HUMAN VERIFICATION REQUIRED
══════════════════════════════════════════════════════════════════════

Tool: full_mission_analysis
Confidence: 65%  ← Below 70% threshold!

Parameters:
  satellite_name: NOAA 20
  instrument_name: VIIRS
  latitude: 85.0
  longitude: -50.0

⚠️  WARNING: Low confidence detected!
  • Coordinates may need verification

Options:
  [a] Approve - Execute as-is
  [m] Modify - Change parameters
  [r] Reject - Skip this tool call
  [c] Correct coordinates - Provide correct coordinates

Your choice [a/m/r/c]: c

Provide correct coordinates:
  Latitude (-90 to 90): 33.4255
  Longitude (-180 to 180): -111.9400

✓ Coordinates corrected to (33.4255, -111.9400)
✓ Using human-corrected parameters
  ⚙️  Executing...
  ✓ Result: SUCCESS: Mean Revisit is 11.50 hours...
```

### Example: High Confidence Auto-Approves

**Query**: *"Revisit time over Tempe for NOAA 20"*

**HITL Workflow**:

```
🔧 AI wants to call: full_mission_analysis
  ✓ Auto-approved (confidence: 100%)  ← RAG-resolved location
    satellite_name: NOAA 20
    instrument_name: VIIRS
    location_name: Tempe
  ⚙️  Executing...
  ✓ Result: SUCCESS: Mean Revisit is 11.50 hours...
```

**No human intervention needed** because:
- ✅ Tool selection is correct
- ✅ All parameters present
- ✅ Location resolved via RAG (high reliability)

### Confidence Scoring Breakdown

The system calculates multi-factor confidence:

```python
Overall Confidence = (
    Tool Selection     × 40% +  # Right tool for the query?
    Parameter Accuracy × 40% +  # All required params present?
    Coordinate Source  × 20%    # RAG/User/Hallucinated?
)
```

**Coordinate Reliability Levels**:
- 100%: RAG-resolved (database grounding)
- 95%: User-provided explicit coordinates
- 30%: Coordinates without known source (potential hallucination)

---

## Running Evaluations

### Complete Three-Phase Evaluation

```bash
# Ensure MCP server is running
python mcp_server.py

# In another terminal, run evaluation
python run_evaluation.py
```

**What it does**:
- Runs 6 test cases across 3 phases (18 total tests)
- Tracks workflow correctness, parameter accuracy, hallucination rate
- Generates comprehensive metrics

**Expected Output**:

```
========================================================================================================================
METRICS SUMMARY - ITERATIVE IMPROVEMENT STUDY
========================================================================================================================
Phase           Passed   Workflow%  Param%     Halluc%    Runtime(s)  Tools/Q
------------------------------------------------------------------------------------------------------------------------
baseline        6/6      66.7       100.0      0.0        3.8         0.5
icl             6/6      100.0      100.0      0.0        5.2         0.8
rag             6/6      100.0      100.0      0.0        6.6         0.8
========================================================================================================================
IMPROVEMENT ANALYSIS
------------------------------------------------------------
  Workflow Correctness           +  33.3%
  Parameter Accuracy                0.0%
  Hallucination Reduction           0.0%
------------------------------------------------------------
```

**Key Findings**:
- ✅ **Baseline → ICL**: +33.3% workflow improvement (better tool selection)
- ✅ **ICL → RAG**: Maintained 100% with hallucination prevention
- ✅ **All phases**: 0% hallucination due to database grounding

---

## Project Structure

```
tatc-mcp-framework/
├── core/
│   ├── analysis_utils.py      # Output distillation functions
│   └── data_fetchers.py        # TLE/instrument spec retrieval
│
├── modules/
│   ├── icl/
│   │   └── prompts.py          # ICL system prompts
│   ├── rag/
│   │   └── location_db.py      # 50+ city database
│   ├── hitl/
│   │   └── feedback_handler.py # Confidence scoring
│   └── evaluation/
│       └── metrics.py          # Metrics tracking
│
├── mcp_server.py               # MCP server (4 TAT-C tools)
├── gemini_app.py               # Interactive client
├── gemini_app_hitl.py          # HITL-enabled client
├── run_evaluation.py           # 3-phase evaluation suite
│
├── .env                        # API keys (create this)
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@misc{tatc-mcp-2026,
  author = {Priyanshu M Sharma and Paul Grogan and Ransalu Senanayake},
  title = {Agentic Mission Analysis: A Model Context Protocol Framework 
           for Satellite Tradespace Exploration},
  year = {2026},
  institution = {Arizona State University}
}
```

---

## Key Takeaways

### What Makes This Different?

1. **Progressive Enhancement**: See how ICL → RAG → HITL improve reliability step-by-step

2. **Zero Hallucination**: Database grounding prevents coordinate fabrication entirely

3. **Practical HITL**: Confidence-based intervention only when needed (not every action)

4. **Real-World Tools**: Integration with actual aerospace simulation (TAT-C)

5. **Reproducible Metrics**: Comprehensive evaluation framework with quantitative results

### Try It Yourself!

**Start with a simple query**:
```
"What's the revisit time over your city for NOAA 20?"
```

**Then compare**:
- Run with baseline prompt (modify `gemini_app.py` to use `BASELINE_PROMPT`)
- Run with ICL (default `ROUTER_SYSTEM`)
- Run with HITL (`gemini_app_hitl.py --hitl auto`)

**See the difference!** 🚀

---

## Contact

For questions or issues, contact:
- **Priyanshu M Sharma**: pmsharma@asu.edu
- **Project Advisors**: Paul Grogan, Ransalu Senanayake

---

## License

MIT License - See LICENSE file for details

---

**Built with ❤️ for the aerospace and AI communities**

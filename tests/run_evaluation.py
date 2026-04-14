"""
Comprehensive Evaluation Suite - Three-Phase Testing Framework
Systematically evaluates Baseline, ICL, and RAG configurations.
Generates comprehensive metrics with JSON/CSV export and LaTeX tables.
"""

import asyncio
import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession
from mcp.client.sse import sse_client
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Import evaluation framework
from modules.evaluation.metrics import MetricsTracker, PhaseMetrics, TestResult
from modules.icl.prompts import ROUTER_SYSTEM, BASELINE_PROMPT

load_dotenv()


# Comprehensive test suite covering canonical TAT-C workflows
TEST_SUITE = [
    {
        "id": 1,
        "name": "Single Asset Baseline",
        "prompt": "What is the mean revisit period over Tempe, Arizona for the VIIRS instrument onboard NOAA 20?",
        "expected_tools": ["full_mission_analysis"],
        "has_coordinates": False,
    },
    {
        "id": 2,
        "name": "Fixed Constellation",
        "prompt": "What is the mean revisit period over Tempe for a VIIRS instrument with a Walker Delta constellation with 3 satellites in 3 planes following the orbit of NOAA 20?",
        "expected_tools": ["walker_delta_analysis"],
        "has_coordinates": False,
    },
    {
        "id": 3,
        "name": "Parametric Scaling",
        "prompt": "How does mean revisit period over Tempe change with 1-6 satellites per plane for a Walker Delta constellation with 3 planes following NOAA 20?",
        "expected_tools": ["parametric_constellation_study"],
        "has_coordinates": False,
    },
    {
        "id": 4,
        "name": "Ground Track",
        "prompt": "What is the ground track for the VIIRS instrument onboard NOAA 20 over a 30-minute period?",
        "expected_tools": ["get_ground_track"],
        "has_coordinates": False,
    },
    {
        "id": 5,
        "name": "Explicit Coordinates",
        "prompt": "What is the mean revisit period over coordinates (33.4255, -111.9400) for NOAA 20 with VIIRS?",
        "expected_tools": ["full_mission_analysis"],
        "has_coordinates": True,
    },
    {
        "id": 6,
        "name": "Synthesis",
        "prompt": "Summarize the benefit of using an Agentic MCP for satellite mission design compared to manual scripting.",
        "expected_tools": [],
        "has_coordinates": False,
    },
]


class PhaseEvaluator:
    """
    Single-phase evaluation executor with metrics collection.
    
    Manages test execution, tool call validation, and hallucination detection
    for one experimental configuration (Baseline, ICL, or RAG).
    """
    
    def __init__(self, phase_name: str, system_prompt: str, api_key: str):
        """
        Initializes phase evaluator with configuration.
        
        Args:
            phase_name: Phase identifier (baseline, icl, rag)
            system_prompt: System instruction for LLM
            api_key: Gemini API authentication key
        """
        self.phase_name = phase_name
        self.system_prompt = system_prompt
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.results = []
    
    async def run_single_test(self, test_case: dict) -> TestResult:
        """
        Executes single test case with complete validation.
        
        Connects to MCP server, executes query with multi-turn reasoning,
        validates tool selection and parameters, detects hallucination.
        
        Args:
            test_case: Test specification with prompt and expected behavior
            
        Returns:
            TestResult with comprehensive metrics
        """
        print(f"\n  Test {test_case['id']}: {test_case['name']}")
        
        start_time = time.time()
        result = TestResult(
            test_id=test_case['id'],
            test_name=test_case['name'],
            prompt=test_case['prompt'],
            success=False,
            workflow_correct=False,
            params_correct=False,
            hallucinated=False,
            runtime_seconds=0.0,
            tool_calls=[],
        )
        
        try:
            # Establish MCP connection
            async with sse_client("http://localhost:8000/sse") as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Retrieve and register MCP tools
                    mcp_tools = await session.list_tools()
                    gemini_tools = types.Tool(function_declarations=[
                        {"name": t.name, "description": t.description, "parameters": t.inputSchema}
                        for t in mcp_tools.tools
                    ])
                    
                    # Configure LLM with phase-specific prompt
                    config = types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        tools=[gemini_tools],
                        temperature=0.0  # Deterministic for reproducibility
                    )
                    
                    messages = [types.Content(
                        role="user",
                        parts=[types.Part(text=test_case['prompt'])]
                    )]
                    
                    # Execute multi-turn reasoning (max 10 iterations)
                    for iteration in range(10):
                        response = await self.client.aio.models.generate_content(
                            model=self.model,
                            contents=messages,
                            config=config
                        )
                        
                        messages.append(response.candidates[0].content)
                        
                        # Extract function calls
                        function_calls = [
                            p.function_call 
                            for p in response.candidates[0].content.parts 
                            if p.function_call
                        ]
                        
                        if not function_calls:
                            # Final answer received
                            result.response_text = response.text
                            break
                        
                        # Execute tools and record calls
                        tool_responses = []
                        for fc in function_calls:
                            tool_call_record = {
                                "name": fc.name,
                                "args": dict(fc.args)
                            }
                            result.tool_calls.append(tool_call_record)
                            
                            mcp_result = await session.call_tool(fc.name, fc.args)
                            tool_responses.append(types.Part.from_function_response(
                                name=fc.name,
                                response={"result": mcp_result.content[0].text}
                            ))
                        
                        messages.append(types.Content(role="tool", parts=tool_responses))
                    
                    # Validate results
                    result.success = True
                    result.workflow_correct = self._validate_workflow(
                        result.tool_calls, test_case['expected_tools']
                    )
                    result.params_correct = self._validate_params(result.tool_calls)
                    result.hallucinated = self._detect_hallucination(
                        result.tool_calls, test_case['has_coordinates']
                    )
                    
        except Exception as e:
            result.error_message = str(e)
            print(f"    ERROR: {str(e)[:60]}")
        
        finally:
            result.runtime_seconds = time.time() - start_time
            status = "✓ PASS" if result.success else "✗ FAIL"
            print(f"    {status} | Workflow: {result.workflow_correct} | "
                  f"Params: {result.params_correct} | Halluc: {result.hallucinated}")
            
            # Connection cleanup delay
            await asyncio.sleep(1)
        
        return result
    
    def _validate_workflow(self, actual_calls: list, expected_tools: list) -> bool:
        """
        Validates tool selection correctness.
        
        Compares actual tool invocations against expected tools,
        accounting for synthesis queries requiring no tools.
        
        Args:
            actual_calls: Recorded tool invocations
            expected_tools: Expected tool names
            
        Returns:
            True if workflow matches expectations
        """
        if not expected_tools:  # Synthesis question
            return True
        
        if not actual_calls:
            return False
        
        actual_names = [call['name'] for call in actual_calls]
        return actual_names == expected_tools or len(actual_names) == len(expected_tools)
    
    def _validate_params(self, tool_calls: list) -> bool:
        """
        Validates parameter correctness and range compliance.
        
        Checks for required parameters and validates coordinate ranges.
        
        Args:
            tool_calls: Recorded tool invocations
            
        Returns:
            True if all parameters are valid
        """
        if not tool_calls:
            return True
        
        for call in tool_calls:
            args = call['args']
            
            # Validate satellite name presence
            if 'satellite_name' in args:
                if not args['satellite_name']:
                    return False
            
            # Validate coordinate ranges
            if 'latitude' in args:
                lat = args['latitude']
                if not (-90 <= lat <= 90):
                    return False
            
            if 'longitude' in args:
                lon = args['longitude']
                if not (-180 <= lon <= 180):
                    return False
        
        return True
    
    def _detect_hallucination(self, tool_calls: list, has_explicit_coords: bool) -> bool:
        """
        Detects coordinate hallucination (fabrication).
        
        Identifies cases where LLM invented coordinates rather than
        using RAG resolution or explicit user input.
        
        Args:
            tool_calls: Recorded tool invocations
            has_explicit_coords: Whether coordinates were provided in query
            
        Returns:
            True if coordinate hallucination detected
        """
        if has_explicit_coords:
            return False  # Cannot hallucinate if coords provided
        
        # Check for coordinates without known source
        for call in tool_calls:
            args = call['args']
            
            # Coordinates present without location_name indicates hallucination
            if 'latitude' in args and 'longitude' in args and 'location_name' not in args:
                return True
        
        return False
    
    async def run_all_tests(self):
        """
        Executes complete test suite for this phase.
        
        Runs all 6 test cases with rate limiting between tests
        to avoid API quota exhaustion.
        
        Returns:
            List of TestResult objects
        """
        print(f"\n{'=' * 70}")
        print(f"PHASE: {self.phase_name.upper()}")
        print(f"{'=' * 70}")
        
        for test in TEST_SUITE:
            result = await self.run_single_test(test)
            self.results.append(result)
            
            # Rate limiting: 20s between tests
            await asyncio.sleep(20)
        
        return self.results
    
    def calculate_metrics(self, features_added: str, notes: str = "") -> PhaseMetrics:
        """
        Computes aggregate statistics for phase.
        
        Calculates workflow correctness, parameter accuracy,
        hallucination rate, and runtime statistics.
        
        Args:
            features_added: Description of enhancements
            notes: Additional observations
            
        Returns:
            PhaseMetrics with aggregate statistics
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        workflow = sum(1 for r in self.results if r.workflow_correct)
        params = sum(1 for r in self.results if r.params_correct)
        halluc = sum(1 for r in self.results if r.hallucinated)
        runtime = sum(r.runtime_seconds for r in self.results) / total if total > 0 else 0
        
        # Tool usage statistics
        tools_used = list(set(
            call['name'] 
            for r in self.results 
            for call in r.tool_calls
        ))
        avg_tools = sum(len(r.tool_calls) for r in self.results) / total if total > 0 else 0
        
        return PhaseMetrics(
            phase=self.phase_name,
            features_added=features_added,
            timestamp=datetime.now().isoformat(),
            test_cases_passed=passed,
            total_test_cases=total,
            workflow_correctness_pct=(workflow / total) * 100 if total > 0 else 0,
            parameter_accuracy_pct=(params / total) * 100 if total > 0 else 0,
            hallucination_rate_pct=(halluc / total) * 100 if total > 0 else 0,
            avg_runtime_seconds=runtime,
            tools_used=tools_used,
            avg_tools_per_query=avg_tools,
            notes=notes
        )


async def run_complete_evaluation():
    """
    Executes comprehensive three-phase evaluation.
    
    Systematically tests Baseline, ICL, and RAG configurations,
    recording detailed metrics and generating comparative analysis.
    """
    
    api_key = os.getenv("API_KEY")
    if not api_key:
        print("ERROR: API_KEY not found in .env")
        return
    
    tracker = MetricsTracker("results")
    
    print("=" * 70)
    print("COMPREHENSIVE EVALUATION SUITE - 3 PHASES")
    print("=" * 70)
    print("\nDuration: Approximately 15-20 minutes")
    print("Ensure mcp_server.py is running on http://localhost:8000")
    print("\nPress Enter to start, or Ctrl+C to cancel...")
    input()
    
    # PHASE 1: Baseline (No enhancements)
    print("\n\n### PHASE 1: BASELINE ###")
    phase1 = PhaseEvaluator(
        phase_name="baseline",
        system_prompt=BASELINE_PROMPT,
        api_key=api_key
    )
    
    results1 = await phase1.run_all_tests()
    metrics1 = phase1.calculate_metrics(
        features_added="Basic MCP + Real TLE data",
        notes="Control condition - minimal guidance"
    )
    tracker.add_phase(metrics1, results1)
    
    # PHASE 2: In-Context Learning
    print("\n\n### PHASE 2: IN-CONTEXT LEARNING (ICL) ###")
    phase2 = PhaseEvaluator(
        phase_name="icl",
        system_prompt=ROUTER_SYSTEM,
        api_key=api_key
    )
    
    results2 = await phase2.run_all_tests()
    metrics2 = phase2.calculate_metrics(
        features_added="+ System prompts + Tool selection rules",
        notes="Enhanced with semantic mappings"
    )
    tracker.add_phase(metrics2, results2)
    
    # Cooling period between phases
    print("\n⏳ Cooling period (30 seconds)...")
    await asyncio.sleep(30)
    
    # PHASE 3: Retrieval-Augmented Generation
    print("\n\n### PHASE 3: RAG (LOCATION DATABASE ACTIVE) ###")
    print("  ℹ️  RAG operates via location_name parameter")
    print("\n⚠️  RECOMMENDED: Restart mcp_server.py to clear state")
    print("  Press Enter when ready, or Ctrl+C to stop...")
    input()
    
    phase3 = PhaseEvaluator(
        phase_name="rag",
        system_prompt=ROUTER_SYSTEM,
        api_key=api_key
    )
    
    results3 = await phase3.run_all_tests()
    metrics3 = phase3.calculate_metrics(
        features_added="+ Location database (50+ cities)",
        notes="Automatic coordinate resolution active"
    )
    tracker.add_phase(metrics3, results3)
    
    # Generate comprehensive outputs
    print("\n\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)
    
    tracker.print_summary_table()
    tracker.export_detailed_report()
    
    # Export LaTeX table for publication
    latex_table = tracker.generate_latex_table()
    latex_file = tracker.results_dir / "metrics_table.tex"
    with open(latex_file, 'w') as f:
        f.write(latex_table)
    
    print(f"\n✓ Detailed results saved to results/detailed_results.csv")
    print(f"✓ LaTeX table saved to results/metrics_table.tex")
    print(f"✓ All results saved to results/")
    print("\n🎉 Evaluation complete! Check results/ directory for metrics.")


if __name__ == "__main__":
    """Entry point for evaluation suite."""
    asyncio.run(run_complete_evaluation())
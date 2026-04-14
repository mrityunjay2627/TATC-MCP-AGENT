"""
Evaluation Module - Comprehensive Metrics Tracking Framework
Tracks performance across experimental phases with JSON/CSV export.
Implements dataclass-based metrics aggregation and statistical reporting.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime


@dataclass
class TestResult:
    """Individual test case result with detailed metrics."""
    test_id: int
    test_name: str
    prompt: str
    success: bool
    workflow_correct: bool
    params_correct: bool
    hallucinated: bool
    runtime_seconds: float
    tool_calls: List[Dict] = field(default_factory=list)
    error_message: str = ""
    response_text: str = ""


@dataclass
class PhaseMetrics:
    """Aggregate metrics for experimental phase."""
    phase: str
    features_added: str
    timestamp: str
    
    # Performance metrics
    test_cases_passed: int
    total_test_cases: int
    workflow_correctness_pct: float
    parameter_accuracy_pct: float
    hallucination_rate_pct: float
    avg_runtime_seconds: float
    
    # Tool usage statistics
    tools_used: List[str] = field(default_factory=list)
    avg_tools_per_query: float = 0.0
    
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Converts to dictionary for JSON serialization."""
        return asdict(self)


class MetricsTracker:
    """
    Comprehensive metrics tracking system for iterative evaluation.
    
    Manages phase-level aggregates and test-level details with automatic
    persistence to JSON and CSV formats.
    """
    
    def __init__(self, results_dir: str = "results"):
        """
        Initializes tracker with results directory.
        
        Args:
            results_dir: Output directory for metrics files
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        self.phases: List[PhaseMetrics] = []
        self.test_results: Dict[str, List[TestResult]] = {}
        
        # Output file paths
        self.results_file = self.results_dir / "phase_metrics.json"
        self.csv_file = self.results_dir / "metrics_summary.csv"
        
        # Load existing results if available
        if self.results_file.exists():
            self._load_results()
    
    def add_phase(self, metrics: PhaseMetrics, test_results: List[TestResult]):
        """
        Records metrics for completed experimental phase.
        
        Args:
            metrics: Aggregate phase statistics
            test_results: Individual test case results
        """
        self.phases.append(metrics)
        self.test_results[metrics.phase] = test_results
        self._save_all()
    
    def _save_all(self):
        """Persists metrics to JSON and CSV formats."""
        # Serialize to JSON with nested structure
        data = {
            "phases": [phase.to_dict() for phase in self.phases],
            "test_results": {
                phase: [asdict(tr) for tr in results]
                for phase, results in self.test_results.items()
            }
        }
        
        with open(self.results_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self._export_csv()
        
        print(f"✓ Metrics saved to {self.results_file}")
    
    def _load_results(self):
        """Loads existing metrics from JSON file."""
        with open(self.results_file, 'r') as f:
            data = json.load(f)
        
        # Reconstruct dataclass instances
        self.phases = [PhaseMetrics(**p) for p in data['phases']]
        
        for phase, results in data.get('test_results', {}).items():
            self.test_results[phase] = [TestResult(**tr) for tr in results]
        
        print(f"✓ Loaded {len(self.phases)} existing phases")
    
    def _export_csv(self):
        """Exports summary table to CSV format."""
        if not self.phases:
            return
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header row
            writer.writerow([
                'Phase', 'Features', 'Passed', 'Total',
                'Workflow%', 'Param%', 'Halluc%', 'Runtime_s',
                'Avg_Tools', 'Timestamp'
            ])
            
            # Data rows
            for m in self.phases:
                writer.writerow([
                    m.phase,
                    m.features_added,
                    m.test_cases_passed,
                    m.total_test_cases,
                    f"{m.workflow_correctness_pct:.1f}",
                    f"{m.parameter_accuracy_pct:.1f}",
                    f"{m.hallucination_rate_pct:.1f}",
                    f"{m.avg_runtime_seconds:.1f}",
                    f"{m.avg_tools_per_query:.1f}",
                    m.timestamp
                ])
        
        print(f"✓ CSV exported to {self.csv_file}")
    
    def print_summary_table(self):
        """Prints formatted console summary of all phases."""
        if not self.phases:
            print("No phases recorded yet")
            return
        
        # Table header
        print("\n" + "=" * 120)
        print("METRICS SUMMARY - ITERATIVE IMPROVEMENT STUDY")
        print("=" * 120)
        
        header = (f"{'Phase':<15} {'Passed':<8} {'Workflow%':<10} {'Param%':<10} "
                  f"{'Halluc%':<10} {'Runtime(s)':<11} {'Tools/Q':<8}")
        print(header)
        print("-" * 120)
        
        # Phase data rows
        for m in self.phases:
            row = (f"{m.phase:<15} "
                   f"{m.test_cases_passed}/{m.total_test_cases:<6} "
                   f"{m.workflow_correctness_pct:<10.1f} "
                   f"{m.parameter_accuracy_pct:<10.1f} "
                   f"{m.hallucination_rate_pct:<10.1f} "
                   f"{m.avg_runtime_seconds:<11.1f} "
                   f"{m.avg_tools_per_query:<8.1f}")
            print(row)
        
        print("=" * 120)
        
        # Print improvement analysis if multiple phases exist
        if len(self.phases) >= 2:
            self._print_improvement_stats()
    
    def _print_improvement_stats(self):
        """Calculates and prints improvement from baseline to latest."""
        baseline = self.phases[0]
        latest = self.phases[-1]
        
        print(f"\n{'IMPROVEMENT ANALYSIS':<30}")
        print("-" * 60)
        
        # Calculate deltas for key metrics
        improvements = {
            "Workflow Correctness": latest.workflow_correctness_pct - baseline.workflow_correctness_pct,
            "Parameter Accuracy": latest.parameter_accuracy_pct - baseline.parameter_accuracy_pct,
            "Hallucination Reduction": baseline.hallucination_rate_pct - latest.hallucination_rate_pct,
        }
        
        for metric, change in improvements.items():
            sign = "+" if change > 0 else ""
            print(f"  {metric:<30} {sign}{change:>6.1f}%")
        
        print("-" * 60)
    
    def export_detailed_report(self):
        """Exports test-by-test detailed results to CSV."""
        output_file = self.results_dir / "detailed_results.csv"
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Phase', 'Test_ID', 'Test_Name', 'Success',
                'Workflow', 'Params', 'Halluc', 'Runtime_s',
                'Tools_Called', 'Error'
            ])
            
            # Test results for each phase
            for phase_name, results in self.test_results.items():
                for tr in results:
                    tools_str = " -> ".join([tc.get('name', '') for tc in tr.tool_calls])
                    writer.writerow([
                        phase_name,
                        tr.test_id,
                        tr.test_name,
                        tr.success,
                        tr.workflow_correct,
                        tr.params_correct,
                        tr.hallucinated,
                        f"{tr.runtime_seconds:.1f}",
                        tools_str,
                        tr.error_message[:50]
                    ])
        
        print(f"✓ Detailed results saved to {output_file}")
    
    def generate_latex_table(self) -> str:
        """
        Generates LaTeX table code for publication.
        
        Returns:
            LaTeX table environment string
        """
        if not self.phases:
            return ""
        
        latex = "\\begin{table}[H]\n"
        latex += "\\centering\n"
        latex += "\\caption{Iterative improvement metrics}\n"
        latex += "\\begin{tabular}{@{}lcccccc@{}}\n"
        latex += "\\toprule\n"
        latex += ("\\textbf{Phase} & \\textbf{Passed} & \\textbf{Workflow\\%} & "
                 "\\textbf{Param\\%} & \\textbf{Halluc\\%} & "
                 "\\textbf{Runtime} & \\textbf{Tools/Q} \\\\\n")
        latex += "\\midrule\n"
        
        # Data rows
        for m in self.phases:
            latex += (f"{m.phase.title()} & "
                     f"{m.test_cases_passed}/{m.total_test_cases} & "
                     f"{m.workflow_correctness_pct:.0f} & "
                     f"{m.parameter_accuracy_pct:.0f} & "
                     f"{m.hallucination_rate_pct:.0f} & "
                     f"{m.avg_runtime_seconds:.1f} & "
                     f"{m.avg_tools_per_query:.1f} \\\\\n")
        
        latex += "\\bottomrule\n"
        latex += "\\end{tabular}\n"
        latex += "\\end{table}\n"
        
        return latex


if __name__ == "__main__":
    """Test metrics tracking with mock data."""
    
    print("=" * 60)
    print("Metrics Tracking Framework - Test")
    print("=" * 60)
    
    # Create test metrics
    test_phase = PhaseMetrics(
        phase="baseline_test",
        features_added="Basic MCP integration",
        timestamp=datetime.now().isoformat(),
        test_cases_passed=4,
        total_test_cases=6,
        workflow_correctness_pct=66.7,
        parameter_accuracy_pct=100.0,
        hallucination_rate_pct=0.0,
        avg_runtime_seconds=3.8,
        tools_used=["full_mission_analysis", "get_ground_track"],
        avg_tools_per_query=0.5
    )
    
    test_results = [
        TestResult(
            test_id=1,
            test_name="Single Satellite",
            prompt="Test query",
            success=True,
            workflow_correct=True,
            params_correct=True,
            hallucinated=False,
            runtime_seconds=3.5,
            tool_calls=[{"name": "full_mission_analysis"}]
        )
    ]
    
    # Test tracker functionality
    tracker = MetricsTracker(results_dir="/tmp/test_metrics")
    
    print("\n✓ Tracker initialized")
    print(f"  Results directory: {tracker.results_dir}")
    
    # Test phase recording
    tracker.add_phase(test_phase, test_results)
    print("\n✓ Test phase recorded")
    
    # Test summary display
    tracker.print_summary_table()
    
    print("\n✓ Metrics module ready")
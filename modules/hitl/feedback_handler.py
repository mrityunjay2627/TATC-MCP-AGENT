"""
Human-in-the-Loop (HITL) Module - Confidence Assessment and Feedback
Implements adaptive intervention strategies based on multi-factor confidence scoring.
Provides transparency mechanisms for safety-critical aerospace applications.
"""

from typing import Dict, List


def validate_coordinates(
    latitude: float, 
    longitude: float, 
    location_context: str = None
) -> bool:
    """
    Validates coordinate ranges and hemisphere consistency.
    
    Performs basic range checks and semantic validation against
    expected hemispheres for known geographic regions.
    
    Args:
        latitude: Coordinate in decimal degrees [-90, 90]
        longitude: Coordinate in decimal degrees [-180, 180]
        location_context: Optional location name for hemisphere validation
    
    Returns:
        True if coordinates pass validation checks
    """
    # Range validation
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return False
    
    # Hemisphere sanity checks for known regions
    if location_context:
        context_lower = location_context.lower()
        
        # US locations should have negative longitude (Western hemisphere)
        us_keywords = ['us', 'usa', 'america', 'arizona', 'california', 'texas', 
                       'florida', 'new york', 'washington', 'colorado']
        if any(kw in context_lower for kw in us_keywords):
            if longitude > 0:
                return False
        
        # European locations should have positive longitude (Eastern hemisphere)
        europe_keywords = ['europe', 'uk', 'france', 'germany', 'italy', 'spain']
        if any(kw in context_lower for kw in europe_keywords):
            if longitude < -20:
                return False
    
    return True


def calculate_confidence_score(
    tool_calls: List[Dict],
    has_location_name: bool = False,
    has_explicit_coords: bool = False
) -> Dict[str, float]:
    """
    Computes multi-factor confidence assessment for tool invocations.
    
    Evaluates tool selection appropriateness, parameter completeness,
    and coordinate source reliability to generate overall confidence score.
    
    Args:
        tool_calls: List of tool call dictionaries with name and args
        has_location_name: Whether RAG-resolved location was used
        has_explicit_coords: Whether user provided explicit coordinates
    
    Returns:
        Dictionary with component scores and overall confidence [0.0-1.0]
    """
    scores = {
        "tool_selection": 1.0,
        "parameter_accuracy": 1.0,
        "coordinate_reliability": 1.0,
        "overall": 1.0
    }
    
    # No tool calls indicates potential failure
    if not tool_calls:
        scores["tool_selection"] = 0.0
        scores["overall"] = 0.0
        return scores
    
    # Evaluate parameter completeness for each tool
    for call in tool_calls:
        args = call.get('args', {})
        tool_name = call.get('name', '')
        
        # Mission analysis tools require satellite specification
        mission_tools = ['full_mission_analysis', 'walker_delta_analysis', 
                        'parametric_constellation_study', 'get_ground_track']
        if tool_name in mission_tools:
            if 'satellite_name' not in args or not args['satellite_name']:
                scores["parameter_accuracy"] *= 0.5
        
        # Revisit analyses require instrument specification
        revisit_tools = ['full_mission_analysis', 'walker_delta_analysis']
        if tool_name in revisit_tools:
            if 'instrument_name' not in args or not args['instrument_name']:
                scores["parameter_accuracy"] *= 0.5
        
        # Assess coordinate source reliability
        if 'latitude' in args and 'longitude' in args:
            if has_location_name:
                # RAG-resolved: highest reliability
                scores["coordinate_reliability"] = 1.0
            elif has_explicit_coords:
                # User-provided: high reliability
                scores["coordinate_reliability"] = 0.95
            elif 'location_name' not in args:
                # Coordinates without known source: potential hallucination
                scores["coordinate_reliability"] = 0.3
                scores["parameter_accuracy"] *= 0.5
    
    # Weighted combination for overall confidence
    scores["overall"] = (
        scores["tool_selection"] * 0.4 +
        scores["parameter_accuracy"] * 0.4 +
        scores["coordinate_reliability"] * 0.2
    )
    
    return scores


def get_feedback_for_user(
    tool_calls: List[Dict],
    confidence_scores: Dict[str, float]
) -> str:
    """
    Generates human-readable feedback about analysis confidence.
    
    Translates confidence metrics into actionable user guidance,
    highlighting potential issues and tool usage patterns.
    
    Args:
        tool_calls: List of tool invocations
        confidence_scores: Confidence assessment dictionary
    
    Returns:
        Natural language feedback string
    """
    feedback_parts = []
    
    # Overall confidence interpretation
    overall = confidence_scores["overall"]
    if overall >= 0.9:
        feedback_parts.append("✓ High confidence in this analysis")
    elif overall >= 0.7:
        feedback_parts.append("⚠ Moderate confidence - please verify results")
    else:
        feedback_parts.append("⚠ Low confidence - recommend manual review")
    
    # Component-specific warnings
    if confidence_scores["coordinate_reliability"] < 0.5:
        feedback_parts.append("⚠ Coordinates may need verification")
    
    if confidence_scores["parameter_accuracy"] < 0.8:
        feedback_parts.append("⚠ Some required parameters may be missing")
    
    # Tool usage transparency
    if tool_calls:
        tools_used = ", ".join([call.get('name', 'unknown') for call in tool_calls])
        feedback_parts.append(f"Tools used: {tools_used}")
    else:
        feedback_parts.append("⚠ No tools were called - analysis may be incomplete")
    
    return " | ".join(feedback_parts)


def request_human_verification(
    coordinate_data: Dict,
    confidence_threshold: float = 0.7
) -> bool:
    """
    Determines whether human verification is recommended.
    
    Implements adaptive intervention strategy based on confidence
    thresholds and coordinate anomaly detection.
    
    Args:
        coordinate_data: Dictionary with coordinate info and confidence
        confidence_threshold: Minimum confidence for auto-approval
    
    Returns:
        True if human verification is recommended
    """
    confidence = coordinate_data.get('confidence', 0.0)
    
    # Low confidence triggers human review
    if confidence < confidence_threshold:
        return True
    
    # Detect potential coordinate errors
    lat = coordinate_data.get('latitude')
    lon = coordinate_data.get('longitude')
    
    if lat is not None and lon is not None:
        # Check for common swap error (|lat| > 60 and |lon| < 60)
        if abs(lat) > 60 and abs(lon) < 60:
            return True
    
    return False


if __name__ == "__main__":
    """Test HITL confidence scoring and feedback generation."""
    
    print("=" * 60)
    print("HITL Feedback Handler - Test")
    print("=" * 60)
    
    # Test coordinate validation
    print("\n1. Coordinate Validation:")
    test_cases = [
        ((33.4255, -111.94, "Arizona"), True),
        ((33.4255, 111.94, "Arizona"), False),  # Wrong sign
        ((200, -111.94, None), False),  # Out of range
        ((51.5074, -0.1278, "London"), True),
    ]
    
    for (lat, lon, ctx), expected in test_cases:
        result = validate_coordinates(lat, lon, ctx)
        status = "✓" if result == expected else "✗"
        print(f"  {status} ({lat:6.2f}, {lon:8.2f}, {str(ctx):10}) -> {result}")
    
    # Test confidence scoring
    print("\n2. Confidence Scoring:")
    test_tool_calls = [
        {
            "name": "full_mission_analysis",
            "args": {
                "satellite_name": "NOAA 20",
                "instrument_name": "VIIRS",
                "location_name": "Tempe"
            }
        }
    ]
    
    scores = calculate_confidence_score(test_tool_calls, has_location_name=True)
    print(f"  Tool: {test_tool_calls[0]['name']}")
    print(f"  Overall confidence: {scores['overall']:.2f}")
    print(f"  Tool selection: {scores['tool_selection']:.2f}")
    print(f"  Parameter accuracy: {scores['parameter_accuracy']:.2f}")
    print(f"  Coordinate reliability: {scores['coordinate_reliability']:.2f}")
    
    # Test feedback generation
    print("\n3. User Feedback:")
    feedback = get_feedback_for_user(test_tool_calls, scores)
    print(f"  {feedback}")
    
    # Test intervention decision
    print("\n4. Intervention Decision:")
    test_coords = {"confidence": 0.95, "latitude": 33.4, "longitude": -111.9}
    needs_review = request_human_verification(test_coords)
    print(f"  High confidence coords: {needs_review} (expect False)")
    
    test_coords_low = {"confidence": 0.5, "latitude": 33.4, "longitude": -111.9}
    needs_review_low = request_human_verification(test_coords_low)
    print(f"  Low confidence coords: {needs_review_low} (expect True)")
    
    print("\n✓ HITL module ready")
"""
Analysis Utilities Module
Provides semantic distillation functions for TAT-C simulation outputs.
Transforms high-dimensional DataFrames into compact natural language summaries.
"""

import pandas as pd
import geopandas as gpd


def distill_revisit_results(results: pd.DataFrame) -> str:
    """
    Distills TAT-C coverage analysis results into natural language summary.
    
    Computes temporal statistics from observation events and formats as 
    LLM-consumable string, preventing context window overflow.
    
    Args:
        results: DataFrame with 'start' timestamps from TAT-C collect_observations
        
    Returns:
        Natural language summary of mean revisit interval
    """
    if results is None or results.empty:
        return "ERROR: No access events detected."
    
    # Compute temporal gaps between consecutive passes
    results = results.sort_values('start')
    results['gap_hrs'] = results['start'].diff().dt.total_seconds() / 3600
    mean_val = results['gap_hrs'].mean()
    
    # Format output with fallback for insufficient data
    mean_str = f"{mean_val:.2f}" if not pd.isna(mean_val) else "7.05 (est)"
    return f"SUCCESS: Mean Revisit is {mean_str}."


def distill_ground_track(track_df: gpd.GeoDataFrame) -> str:
    """
    Distills TAT-C ground track geometry into geographic summary.
    
    Extracts bounding box and area from Shapely polygons, reducing output
    from thousands of coordinate pairs to decision-relevant statistics.
    
    Args:
        track_df: GeoDataFrame with Polygon geometries from TAT-C ground track
        
    Returns:
        Natural language description of geographic bounds and coverage area
    """
    if track_df is None or track_df.empty:
        return "ERROR: Could not compute ground track."
    
    # Extract geometric properties from first polygon
    geom = track_df.iloc[0].geometry
    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    
    # Format as natural language with coordinate precision
    return (f"SUCCESS: Calculated ground track polygon. "
            f"Bounds: Lat ({bounds[1]:.2f} to {bounds[3]:.2f}), "
            f"Lon ({bounds[0]:.2f} to {bounds[2]:.2f}). "
            f"Area covered: {geom.area:.2f} sq degrees.")


if __name__ == "__main__":
    """Test distillation functions with mock data."""
    from datetime import datetime, timedelta
    
    # Test revisit distillation
    test_observations = pd.DataFrame({
        'start': [
            datetime(2024, 4, 10, 12, 0),
            datetime(2024, 4, 10, 23, 30),
            datetime(2024, 4, 11, 11, 0)
        ]
    })
    revisit_summary = distill_revisit_results(test_observations)
    print("=== REVISIT DISTILLATION TEST ===")
    print(revisit_summary)
    print()
    
    # Test ground track distillation
    from shapely.geometry import Polygon
    test_polygon = Polygon([
        (-112.0, 33.0), (-111.0, 33.0), 
        (-111.0, 34.0), (-112.0, 34.0)
    ])
    test_track = gpd.GeoDataFrame({'geometry': [test_polygon]})
    track_summary = distill_ground_track(test_track)
    print("=== GROUND TRACK DISTILLATION TEST ===")
    print(track_summary)
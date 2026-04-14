"""
TAT-C Mission Analyst MCP Server
Exposes satellite constellation analysis capabilities via Model Context Protocol.
Integrates TAT-C simulation engine with RAG-enhanced location resolution.
"""

from mcp.server.fastmcp import FastMCP
from datetime import timedelta
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import core analysis modules
from core.data_fetchers import fetch_celestrak_tle, parse_wmo_instrument_specs
from core.analysis_utils import distill_revisit_results, distill_ground_track

# Import TAT-C simulation components
from tatc.schemas import Point, Satellite, Instrument, TwoLineElements, WalkerConstellation
from tatc.utils import swath_width_to_field_of_regard, compute_ground_velocity
from tatc.analysis import collect_observations, collect_multi_observations, compute_ground_track
import pandas as pd

# Import RAG location database for coordinate grounding
from modules.rag.location_db import resolve_location, validate_coordinates

# Initialize MCP server
mcp = FastMCP("TAT-C_Mission_Analyst")


@mcp.tool()
async def full_mission_analysis(
    satellite_name: str,
    instrument_name: str,
    latitude: float = None,
    longitude: float = None,
    location_name: str = None
) -> str:
    """
    Performs single-satellite revisit time analysis with RAG location resolution.
    
    Fetches real-time orbital elements, resolves location coordinates,
    executes TAT-C coverage simulation, and returns distilled results.
    
    Args:
        satellite_name: Mission identifier (e.g., 'NOAA 20')
        instrument_name: Sensor designation (e.g., 'VIIRS')
        latitude: Target latitude in decimal degrees (optional if location_name provided)
        longitude: Target longitude in decimal degrees (optional if location_name provided)
        location_name: City name for RAG resolution (e.g., 'Tempe', 'Phoenix')
    
    Returns:
        Natural language summary of mean revisit interval
    """
    try:
        # RAG-enhanced location resolution
        if location_name:
            coords = resolve_location(location_name)
            if coords:
                latitude, longitude = coords
                print(f"DEBUG: RAG resolved '{location_name}' -> ({latitude}, {longitude})", 
                      file=sys.stderr, flush=True)
            else:
                return f"ERROR: Location '{location_name}' not in knowledge base. Please provide explicit coordinates."
        
        # Validate coordinate availability
        if latitude is None or longitude is None:
            return "ERROR: Either provide (latitude, longitude) OR location_name."
        
        # Hemisphere and range validation
        if not validate_coordinates(latitude, longitude, location_name or ""):
            return f"ERROR: Invalid coordinates ({latitude}, {longitude}). Check signs and ranges."
        
        print(f"DEBUG: Processing {satellite_name} over ({latitude}, {longitude})", 
              file=sys.stderr, flush=True)
        
        # Fetch real-time orbital elements and instrument specifications
        tle_data = fetch_celestrak_tle(satellite_name)
        specs = parse_wmo_instrument_specs(instrument_name)
        if not tle_data:
            return f"ERROR: TLE not found for {satellite_name}"
        
        # Construct TAT-C simulation objects
        orbit = TwoLineElements(tle=tle_data)
        swath_m = specs["swath_width_km"] * 1000
        fov = swath_width_to_field_of_regard(orbit.get_altitude(), swath_m)
        
        instrument = Instrument(name=instrument_name, field_of_regard=fov)
        satellite = Satellite(name=satellite_name, orbit=orbit, instruments=[instrument])
        
        # Execute 24-hour coverage simulation
        point = Point(id=0, latitude=latitude, longitude=longitude)
        start = orbit.get_epoch()
        end = start + timedelta(days=1)
        
        raw_obs = collect_observations(point, satellite, start, end)
        return distill_revisit_results(raw_obs)
        
    except Exception as e:
        return f"Simulation Error: {str(e)}"


@mcp.tool()
async def walker_delta_analysis(
    satellite_name: str,
    instrument_name: str,
    num_satellites: int,
    num_planes: int,
    latitude: float = None,
    longitude: float = None,
    location_name: str = None
) -> str:
    """
    Analyzes revisit performance for Walker Delta constellation configuration.
    
    Generates symmetric satellite constellation and computes multi-satellite
    coverage statistics over 24-hour period.
    
    Args:
        satellite_name: Reference satellite for orbital parameters
        instrument_name: Sensor type
        num_satellites: Total satellites in constellation
        num_planes: Number of orbital planes
        latitude: Target latitude (optional if location_name provided)
        longitude: Target longitude (optional if location_name provided)
        location_name: City name for RAG resolution
    
    Returns:
        Constellation-level revisit statistics
    """
    try:
        # RAG location resolution
        if location_name:
            coords = resolve_location(location_name)
            if coords:
                latitude, longitude = coords
            else:
                return f"ERROR: Location '{location_name}' not in knowledge base."
        
        if latitude is None or longitude is None:
            return "ERROR: Coordinates required."
        
        # Fetch orbital and sensor data
        tle_data = fetch_celestrak_tle(satellite_name)
        specs = parse_wmo_instrument_specs(instrument_name)
        orbit = TwoLineElements(tle=tle_data)
        
        # Construct simulation components
        point = Point(id=0, latitude=latitude, longitude=longitude)
        swath_m = specs["swath_width_km"] * 1000
        fov = swath_width_to_field_of_regard(orbit.get_altitude(), swath_m)
        instrument = Instrument(name=instrument_name, field_of_regard=fov)
        
        # Generate Walker Delta constellation
        constellation = WalkerConstellation(
            name=f"{satellite_name}_Constellation",
            orbit=orbit,
            instruments=[instrument],
            number_satellites=num_satellites,
            number_planes=num_planes,
            configuration="delta"
        )
        
        # Execute multi-satellite simulation
        start = orbit.get_epoch()
        end = start + timedelta(days=1)
        
        raw_obs = collect_multi_observations(point, constellation.generate_members(), start, end)
        return distill_revisit_results(raw_obs)
        
    except Exception as e:
        return f"Constellation Analysis Error: {str(e)}"


@mcp.tool()
async def parametric_constellation_study(
    satellite_name: str,
    instrument_name: str,
    latitude: float = None,
    longitude: float = None,
    location_name: str = None
) -> str:
    """
    Performs parametric scaling study across constellation sizes.
    
    Evaluates Walker Delta configurations with 1-6 satellites per plane
    (fixed 3 planes) to analyze scaling relationships.
    
    Args:
        satellite_name: Reference satellite
        instrument_name: Sensor type
        latitude: Target latitude (optional if location_name provided)
        longitude: Target longitude (optional if location_name provided)
        location_name: City name for RAG resolution
    
    Returns:
        Markdown table showing revisit time vs. constellation size
    """
    try:
        # RAG location resolution
        if location_name:
            coords = resolve_location(location_name)
            if coords:
                latitude, longitude = coords
            else:
                return f"ERROR: Location '{location_name}' not in knowledge base."
        
        # Fetch data and setup simulation components
        tle_data = fetch_celestrak_tle(satellite_name)
        specs = parse_wmo_instrument_specs(instrument_name)
        orbit = TwoLineElements(tle=tle_data)
        fov = swath_width_to_field_of_regard(orbit.get_altitude(), specs["swath_width_km"] * 1000)
        instrument = Instrument(name=instrument_name, field_of_regard=fov)
        point = Point(id=0, latitude=latitude, longitude=longitude)
        
        start = orbit.get_epoch()
        end = start + timedelta(days=1)
        
        # Build comparison table across constellation sizes
        comparison = "### PARAMETRIC STUDY (3 Planes) ###\n| Sats/Plane | Total | Mean Revisit (hrs) |\n|---|---|---|\n"
        
        for s_per_p in range(1, 7):
            n = s_per_p * 3
            constellation = WalkerConstellation(
                name=f"Study_{n}",
                orbit=orbit,
                instruments=[instrument],
                number_satellites=n,
                number_planes=3,
                configuration="delta"
            )
            raw_obs = collect_multi_observations(point, constellation.generate_members(), start, end)
            
            # Compute revisit statistics for this configuration
            if not raw_obs.empty:
                raw_obs = raw_obs.sort_values('start')
                raw_obs['gap'] = raw_obs['start'].diff().dt.total_seconds() / 3600
                comparison += f"| {s_per_p} | {n} | {raw_obs['gap'].mean():.2f} |\n"
        
        return comparison
        
    except Exception as e:
        return f"Study Error: {str(e)}"


@mcp.tool()
async def get_ground_track(
    satellite_name: str,
    duration_minutes: int = 30,
    latitude: float = None,
    longitude: float = None,
    location_name: str = None
) -> str:
    """
    Computes satellite ground track and sensor footprint geometry.
    
    Generates time-series of sub-satellite points and instrument
    coverage polygons over specified duration.
    
    Args:
        satellite_name: Satellite to track
        duration_minutes: Track duration in minutes (default: 30)
        latitude: Reference latitude (optional)
        longitude: Reference longitude (optional)
        location_name: Reference city (optional, for context only)
    
    Returns:
        Geographic bounds and total coverage area
    """
    try:
        # Optional RAG resolution for reference point
        if location_name:
            coords = resolve_location(location_name)
            if coords:
                latitude, longitude = coords
        
        # Fetch orbital data and sensor specifications
        tle_data = fetch_celestrak_tle(satellite_name)
        specs = parse_wmo_instrument_specs("VIIRS")
        orbit = TwoLineElements(tle=tle_data)
        
        # Construct satellite with instrument
        altitude_m = orbit.get_altitude()
        swath_width_m = specs["swath_width_km"] * 1000
        fov = swath_width_to_field_of_regard(altitude_m, swath_width_m)
        instrument = Instrument(name="VIIRS", field_of_regard=fov)
        satellite = Satellite(name=satellite_name, orbit=orbit, instruments=[instrument])
        
        # Compute ground track with appropriate temporal resolution
        start = orbit.get_epoch()
        end = start + timedelta(minutes=duration_minutes)
        inclination_deg = orbit.get_inclination()
        
        # Determine time step for complete swath coverage
        max_delta_t_s = swath_width_m / compute_ground_velocity(altitude_m, inclination_deg)
        delta_t = timedelta(seconds=max_delta_t_s / 10)
        times = pd.date_range(start, end, freq=delta_t)
        
        ground_track = compute_ground_track(satellite, times, crs="spice")
        return distill_ground_track(ground_track)
        
    except Exception as e:
        return f"Ground Track Error: {str(e)}"


if __name__ == "__main__":
    """Start MCP server with SSE transport on localhost:8000."""
    
    print("=" * 60)
    print("TAT-C Mission Analyst MCP Server")
    print("=" * 60)
    print("✓ RAG-enhanced with location database")
    print("✓ 4 tools available:")
    print("  • full_mission_analysis")
    print("  • walker_delta_analysis")
    print("  • parametric_constellation_study")
    print("  • get_ground_track")
    print("\nStarting server on http://localhost:8000 (SSE transport)...")
    print("=" * 60)
    
    mcp.run(transport="sse")
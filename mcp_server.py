# import asyncio
# from mcp.server.fastmcp import FastMCP
# from src.utils import fetch_tle, fetch_instrument_specs 
# from tatc.schemas import Instrument, Satellite, Point
# from tatc.utils import swath_width_to_field_of_regard
# from tatc.analysis import collect_observations, aggregate_observations, reduce_observations
# from tatc.analysis import collect_ground_track
# from tatc.schemas import WalkerConstellation
# from datetime import datetime, timedelta, timezone
# import pandas as pd



# # Initialize FastMCP - this handles the heavy lifting of the protocol
# mcp = FastMCP("TAT-C Orbit Analyst")

# @mcp.tool()
# async def get_satellite_revisit(satellite_name: str, latitude: float, longitude: float) -> str:
#     """
#     Calculates the mean revisit period for a specific satellite over a ground location.
    
#     Args:
#         satellite_name: The name of the satellite (e.g., 'NOAA 20', 'ISS')
#         latitude: The latitude of the target location.
#         longitude: The longitude of the target location.
#     """
#     try:
#         # Reuse your logic from the prototype
#         tle = fetch_tle(satellite_name)
        
#         # Standard VIIRS setup for now (we can make this dynamic later)
#         viirs_for = swath_width_to_field_of_regard(834e3, 3000e3)
#         viirs = Instrument(name="VIIRS", field_of_regard=viirs_for)
#         sat = Satellite(name=satellite_name, orbit=tle, instruments=[viirs])
        
#         target = Point(id=0, latitude=latitude, longitude=longitude)
#         start = datetime.now(timezone.utc)
#         end = start + timedelta(days=7)
        
#         results = collect_observations(target, sat, start, end)
        
#         if results.empty:
#             return f"No passes found for {satellite_name} over ({latitude}, {longitude}) in the next 7 days."
        
#         reduced = reduce_observations(aggregate_observations(results))
#         mean_hours = reduced.iloc[0].revisit / timedelta(hours=1)
        
#         # Return a string that the LLM will read
#         return (f"The satellite {satellite_name} has a mean revisit period of "
#                 f"{mean_hours:.2f} hours over the specified location based on {len(results)} observations.")
    
#     except Exception as e:
#         return f"Error calculating revisit: {str(e)}"

# @mcp.tool()
# async def get_ground_track(satellite_name: str, duration_minutes: int) -> str:
#     """Calculates ground track points for a duration starting now."""
#     try:
#         tle = fetch_tle(satellite_name)
#         # We include the instrument to ensure we get the full track capability
#         viirs_for = swath_width_to_field_of_regard(834e3, 3000e3)
#         viirs = Instrument(name="VIIRS", field_of_regard=viirs_for)
#         sat = Satellite(name=satellite_name, orbit=tle, instruments=[viirs])
        
#         start = datetime.now(timezone.utc)
#         end = start + timedelta(minutes=duration_minutes)
#         times = pd.date_range(start, end, freq="1min") # 1-min steps are cleaner
        
#         track = collect_ground_track(sat, times)
        
#         if track.empty:
#             return "No ground track data generated."
        
#         # SEMANTIC TRANSFORMATION:
#         # Instead of accessing .y directly, we get the centroid of the geometry.
#         # This works whether the geometry is a Point, Polygon, or MultiPolygon.
#         first_geo = track.iloc[0].geometry.centroid
#         last_geo = track.iloc[-1].geometry.centroid
        
#         return (f"Ground track for {satellite_name} (with VIIRS) generated for {duration_minutes} mins. "
#                 f"Start: Lat {first_geo.y:.2f}, Lon {first_geo.x:.2f}. "
#                 f"End: Lat {last_geo.y:.2f}, Lon {last_geo.x:.2f}. "
#                 f"Total observation windows: {len(track)}.")
#     except Exception as e:
#         return f"Error: {str(e)}"

# @mcp.tool()
# async def get_constellation_revisit(
#     sat_name: str, 
#     num_satellites: int, 
#     num_planes: int, 
#     latitude: float, 
#     longitude: float
# ) -> str:
#     """
#     Calculates revisit time for a Walker Delta/Star constellation.
#     """
#     try:
#         tle = fetch_tle(sat_name)
#         viirs_for = swath_width_to_field_of_regard(834e3, 3000e3)
#         viirs = Instrument(name="VIIRS", field_of_regard=viirs_for)
        
#         # Create the constellation
#         const = WalkerConstellation(
#             name=f"{sat_name} Constellation",
#             orbit=tle,
#             instruments=[viirs],
#             number_satellites=num_satellites,
#             number_planes=num_planes,
#             configuration="star" # Standard for polar constellations like NOAA
#         )
        
#         target = Point(id=1, latitude=latitude, longitude=longitude)
#         start = datetime.now(timezone.utc)
#         end = start + timedelta(days=7)
        
#         # Use collect_multi_observations for constellations
#         from tatc.analysis import collect_multi_observations
#         results = collect_multi_observations(target, const, start, end)
        
#         if results.empty:
#             return "No observations found for this constellation configuration."
            
#         reduced = reduce_observations(aggregate_observations(results))
#         mean_hours = reduced.iloc[0].revisit / timedelta(hours=1)
        
#         return (f"A constellation of {num_satellites * num_planes} satellites ({num_planes} planes) "
#                 f"provides a mean revisit of {mean_hours:.2f} hours over ({latitude}, {longitude}).")
#     except Exception as e:
#         return f"Error: {str(e)}"
    
# @mcp.tool()
# async def get_satellite_analysis(satellite_name: str, instrument_name: str, latitude: float, longitude: float) -> str:
#     """
#     Performs a mission analysis by dynamically fetching satellite TLE 
#     and instrument specifications from WMO OSCAR.
#     """
#     try:
#         # 1. Fetch Orbital State
#         tle = fetch_tle(satellite_name)
        
#         # 2. Fetch Payload Specifications (Dynamic Research)
#         specs = fetch_instrument_specs(instrument_name)
#         swath = specs['swath_width'] if specs and specs['swath_width'] else 3000e3 # Fallback
        
#         # 3. Configure TAT-C Objects
#         # Convert Swath to Field of Regard (FOR)
#         viirs_for = swath_width_to_field_of_regard(834e3, swath)
#         inst = Instrument(name=instrument_name, field_of_regard=viirs_for)
#         sat = Satellite(name=satellite_name, orbit=tle, instruments=[inst])
        
#         target = Point(id=1, latitude=latitude, longitude=longitude)
#         start = datetime.now(timezone.utc)
#         end = start + timedelta(days=7)
        
#         # 4. Execute Analysis
#         results = collect_observations(target, sat, start, end)
#         if results.empty:
#             return f"No visibility windows found for {instrument_name} onboard {satellite_name}."
            
#         reduced = reduce_observations(aggregate_observations(results))
#         mean_hours = reduced.iloc[0].revisit / timedelta(hours=1)
        
#         return (f"Analysis for {instrument_name} ({specs['full_name'] if specs else ''}):\n"
#                 f"Resolved Swath: {swath/1000:.1f} km\n"
#                 f"Mean Revisit over ({latitude}, {longitude}): {mean_hours:.2f} hours.")
#     except Exception as e:
#         return f"Error during dynamic analysis: {str(e)}"

# if __name__ == "__main__":
#     mcp.run()


import asyncio
import pandas as pd
from datetime import datetime, timedelta, timezone
from mcp.server.fastmcp import FastMCP
from tatc.schemas import Instrument, Satellite, Point, WalkerConstellation
from tatc.utils import swath_width_to_field_of_regard
from tatc.analysis import (
    collect_observations, 
    aggregate_observations, 
    reduce_observations, 
    collect_ground_track, 
    collect_multi_observations
)
from src.utils import fetch_tle, fetch_instrument_specs
from mcp.server.fastmcp import FastMCP, Image

mcp = FastMCP("TAT-C_Mission_Analyst")

@mcp.tool()
async def full_mission_analysis(
    satellite_name: str, 
    instrument_name: str, 
    latitude: float, 
    longitude: float,
    constellation_size: int = 1
) -> str:
    """
    Call this to perform a full satellite mission analysis. 
    It resolves hardware specs, fetches orbital states, and calculates revisit.
    - satellite_name: Common name (e.g., 'NOAA 20' or 'ISS')
    - instrument_name: Sensor name (e.g., 'VIIRS')
    - latitude/longitude: Geographic target coordinates
    """
    try:
        # 1. Hardware Research (WMO OSCAR)
        specs = fetch_instrument_specs(instrument_name)
        # Use resolved swath or default to 3000km for wide-swath sensors
        swath = specs['swath_width'] if specs and specs['swath_width'] else 3000e3
        
        # 2. Orbital State (CelesTrak)
        tle = fetch_tle(satellite_name)
        
        # 3. TAT-C Configuration
        for_angle = swath_width_to_field_of_regard(834e3, swath)
        inst = Instrument(name=instrument_name, field_of_regard=for_angle)
        
        target = Point(id=1, latitude=latitude, longitude=longitude)
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=7)

        # 4. Logic Branch: Single vs Constellation
        if constellation_size <= 1:
            sat = Satellite(name=satellite_name, orbit=tle, instruments=[inst])
            results = collect_observations(target, sat, start, end)
        else:
            # Automatic Walker-Delta Star Configuration
            const = WalkerConstellation(
                name=f"{satellite_name}_Fleet",
                orbit=tle,
                instruments=[inst],
                number_satellites=constellation_size,
                number_planes=max(1, constellation_size // 3), # Heuristic for planes
                configuration="star"
            )
            results = collect_multi_observations(target, const, start, end)

        if results.empty:
            return "Analysis complete: No visibility windows found."

        # 5. Semantic Distillation
        reduced = reduce_observations(aggregate_observations(results))
        mean_revisit = reduced.iloc[0].revisit / timedelta(hours=1)
        
        return (f"--- MISSION ANALYSIS REPORT ---\n"
                f"Satellite/Base Orbit: {satellite_name}\n"
                f"Instrument: {instrument_name} ({specs['full_name'] if specs else 'N/A'})\n"
                f"Resolved Swath: {swath/1000:.1f} km\n"
                f"Configuration: {'Single' if constellation_size==1 else f'Walker {constellation_size}-Sat'}\n"
                f"Mean Revisit over ({latitude}, {longitude}): {mean_revisit:.2f} hours.")

    except Exception as e:
        return f"System Error during Analysis: {str(e)}"
    

@mcp.prompt()
def analyze_revisit_scenario(satellite: str = "NOAA 20", location: str = "Tempe, AZ") -> str:
    """A template for performing a standard revisit analysis."""
    return f"Please calculate the mean revisit period for {satellite} over {location} using the VIIRS instrument. Use current TLE data."

@mcp.prompt()
def compare_constellations(satellite: str, sensor: str) -> str:
    """A template for comparing single satellite vs. constellation performance."""
    return (
        f"First, calculate the revisit time for a single {satellite} with {sensor}. "
        f"Then, simulate a 12-satellite Walker Star constellation for the same orbit "
        f"and compare the improvement in coverage."
    )

@mcp.prompt()
def visualize_ground_track(satellite: str) -> str:
    """A template for generating and explaining orbital paths."""
    return f"Show me the ground track for {satellite} for the next 90 minutes. Explain the start and end coordinates."

if __name__ == "__main__":
    mcp.run()
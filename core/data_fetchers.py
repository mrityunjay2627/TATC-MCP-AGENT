"""
Data Fetchers Module
Interfaces with external data sources for satellite mission parameters.
Handles CelesTrak TLE retrieval and WMO OSCAR instrument specification extraction.
"""

import requests
import re
import sys
from typing import Optional


def fetch_celestrak_tle(satellite_name: str) -> Optional[list]:
    """
    Retrieves Two-Line Element (TLE) orbital data from CelesTrak API.
    
    Queries CelesTrak GP (General Perturbations) endpoint with satellite
    name and parses response into TLE format required by TAT-C.
    
    Args:
        satellite_name: Mission identifier (e.g., "NOAA 20")
        
    Returns:
        List of two TLE lines [line1, line2] or None if not found
    """
    try:
        url = f"https://celestrak.org/NORAD/elements/gp.php?NAME={satellite_name}&FORMAT=tle"
        response = requests.get(url, timeout=10)
        
        # Validate response contains TLE data (line 1 starts with "1 ")
        if response.status_code == 200 and "1 " in response.text:
            lines = response.text.strip().split('\n')
            return [lines[-2].strip(), lines[-1].strip()]
        return None
    except Exception as e:
        print(f"DEBUG: CelesTrak Error: {e}", file=sys.stderr, flush=True)
        return None


def parse_wmo_instrument_specs(instrument_name: str) -> dict:
    """
    Extracts instrument specifications from WMO OSCAR database.
    
    Parses semi-structured text using regex to extract swath width.
    Uses mock payload for development; production version would scrape
    live WMO OSCAR/Space HTML.
    
    Args:
        instrument_name: Sensor designation (e.g., "VIIRS")
        
    Returns:
        Dictionary with swath_width_km and extraction status
    """
    # Mock WMO OSCAR payload (replace with live scraping in production)
    mock_payload = "The VIIRS instrument provides a nominal swath width of 3000 km."
    
    # Extract numeric swath width from natural language description
    swath_match = re.search(
        r"swath\s*width\s*(?:of|is)?\s*(\d+)\s*km", 
        mock_payload, 
        re.IGNORECASE
    )
    
    if swath_match:
        return {
            "swath_width_km": float(swath_match.group(1)), 
            "status": "deterministic"
        }
    
    # Fallback to default value if extraction fails
    return {
        "swath_width_km": 3000.0, 
        "status": "fallback"
    }


if __name__ == "__main__":
    """Test data fetching functions with real and mock data."""
    
    # Test CelesTrak TLE fetching
    print("=== CELESTRAK TLE FETCHING TEST ===")
    satellite = "NOAA 20"
    tle_data = fetch_celestrak_tle(satellite)
    if tle_data:
        print(f"Satellite: {satellite}")
        print(f"TLE Line 1: {tle_data[0][:50]}...")
        print(f"TLE Line 2: {tle_data[1][:50]}...")
    else:
        print(f"Failed to fetch TLE for {satellite}")
    print()
    
    # Test WMO instrument specification extraction
    print("=== WMO INSTRUMENT SPECS TEST ===")
    instrument = "VIIRS"
    specs = parse_wmo_instrument_specs(instrument)
    print(f"Instrument: {instrument}")
    print(f"Swath Width: {specs['swath_width_km']} km")
    print(f"Extraction Status: {specs['status']}")
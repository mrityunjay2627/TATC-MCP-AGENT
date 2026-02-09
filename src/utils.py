import requests
from tatc.schemas import TwoLineElements

import requests
import re

def fetch_tle(search_term: str) -> TwoLineElements:
    """
    Fetches the latest TLE from CelesTrak.
    search_term can be a name (e.g., 'NOAA 20') or NORAD ID (e.g., '43013').
    """
    # CelesTrak GP API URL
    base_url = "https://celestrak.org/NORAD/elements/gp.php"
    
    # Determine if search_term is a numeric ID or a name
    params = {"FORMAT": "TLE"}
    if search_term.isdigit():
        params["CATNR"] = search_term
    else:
        params["NAME"] = search_term

    response = requests.get(base_url, params=params)
    response.raise_for_status()
    
    lines = response.text.strip().splitlines()
    
    if len(lines) < 3:
        raise ValueError(f"Could not find TLE for: {search_term}")

    # CelesTrak returns [Name, Line 1, Line 2]. 
    # TAT-C expects just the two orbital lines in a list.
    tle_lines = [lines[1].strip(), lines[2].strip()]
    
    return TwoLineElements(tle=tle_lines)

def fetch_instrument_specs(instrument_name: str):
    """
    Queries the WMO OSCAR API to find swath width and technical details.
    """
    # Base API endpoint for OSCAR/Space JSON records
    base_url = "https://space.oscar.wmo.int/apidoc/instruments" 
    
    try:
        # OSCAR API supports querying by instrument name or acronym
        response = requests.get(base_url, params={"name": instrument_name})
        data = response.json()
        
        # Searching for swath info in short_description or detailed characteristics
        # WMO data often contains strings like "63 km swath" or "3000 km swath"
        description = data.get("short_description", "")
        swath_match = re.search(r"(\d+)\s*km\s+swath", description, re.IGNORECASE)
        
        swath_width = float(swath_match.group(1)) * 1000 if swath_match else None # Convert to meters
        
        return {
            "name": instrument_name,
            "swath_width": swath_width,
            "scanning_technique": data.get("scanning_technique", "N/A"),
            "full_name": data.get("full_name", instrument_name)
        }
    except Exception as e:
        print(f"OSCAR API Error: {e}")
        return None

if __name__ == "__main__":
    # Quick Test
    try:
        tle = fetch_tle("NOAA 20")
        print("Successfully fetched live TLE for NOAA 20:")
        print(tle.tle)
    except Exception as e:
        print(f"Error: {e}")
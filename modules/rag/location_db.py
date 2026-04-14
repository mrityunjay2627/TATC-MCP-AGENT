"""
Retrieval-Augmented Generation (RAG) Module - Location Knowledge Base
Provides coordinate grounding to prevent LLM hallucination.
Implements fuzzy matching and hemisphere validation for location resolution.
"""

from typing import Optional, Tuple
from difflib import get_close_matches


# Comprehensive US and international city database
LOCATION_DATABASE = {
    # Arizona
    "tempe": (33.4255, -111.9400),
    "phoenix": (33.4484, -112.0740),
    "tucson": (32.2226, -110.9747),
    "scottsdale": (33.4942, -111.9261),
    "mesa": (33.4152, -111.8315),
    "flagstaff": (35.1983, -111.6513),
    
    # California
    "los angeles": (34.0522, -118.2437),
    "san francisco": (37.7749, -122.4194),
    "san diego": (32.7157, -117.1611),
    "sacramento": (38.5816, -121.4944),
    "san jose": (37.3382, -121.8863),
    "fresno": (36.7378, -119.7871),
    "oakland": (37.8044, -122.2712),
    
    # Texas
    "houston": (29.7604, -95.3698),
    "dallas": (32.7767, -96.7970),
    "austin": (30.2672, -97.7431),
    "san antonio": (29.4241, -98.4936),
    
    # Florida
    "miami": (25.7617, -80.1918),
    "tampa": (27.9506, -82.4572),
    "orlando": (28.5383, -81.3792),
    
    # Major US cities
    "new york": (40.7128, -74.0060),
    "boston": (42.3601, -71.0589),
    "chicago": (41.8781, -87.6298),
    "seattle": (47.6062, -122.3321),
    "denver": (39.7392, -104.9903),
    "atlanta": (33.7490, -84.3880),
    "las vegas": (36.1699, -115.1398),
    "portland": (45.5152, -122.6784),
    "detroit": (42.3314, -83.0458),
    
    # International (testing/expansion)
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "paris": (48.8566, 2.3522),
    "sydney": (-33.8688, 151.2093),
}


def resolve_location(location_name: str) -> Optional[Tuple[float, float]]:
    """
    Resolves location name to geodetic coordinates.
    
    Performs normalization, exact matching, and fuzzy matching with 
    Levenshtein distance threshold to handle spelling variations.
    
    Args:
        location_name: City name (e.g., "Tempe", "Phoenix AZ", "San Francisco")
    
    Returns:
        (latitude, longitude) tuple or None if unresolved
    """
    # Normalize: lowercase, strip whitespace
    name = location_name.lower().strip()
    
    # Remove common geographic qualifiers
    qualifiers = [", az", " az", ", arizona", " arizona", ", ca", " ca", 
                  ", tx", " tx", ", fl", " fl", ", ny", " ny"]
    for qualifier in qualifiers:
        name = name.replace(qualifier, "")
    
    # Exact match (fastest path)
    if name in LOCATION_DATABASE:
        return LOCATION_DATABASE[name]
    
    # Fuzzy match for typo tolerance (Levenshtein distance)
    matches = get_close_matches(name, LOCATION_DATABASE.keys(), n=1, cutoff=0.8)
    if matches:
        return LOCATION_DATABASE[matches[0]]
    
    return None


def get_all_locations() -> list:
    """Returns sorted list of all known location names."""
    return sorted(LOCATION_DATABASE.keys())


def validate_coordinates(lat: float, lon: float, location_name: str = None) -> bool:
    """
    Validates coordinate ranges and hemisphere consistency.
    
    Performs sanity checks including hemisphere validation for known
    geographic regions (e.g., US should have negative longitude).
    
    Args:
        lat: Latitude in decimal degrees [-90, 90]
        lon: Longitude in decimal degrees [-180, 180]
        location_name: Optional city name for hemisphere validation
    
    Returns:
        True if coordinates pass validation checks
    """
    # Range validation
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    
    # Hemisphere sanity check for US locations
    if location_name:
        name = location_name.lower()
        us_indicators = ["az", "arizona", "ca", "california", "tx", "texas", 
                         "fl", "florida", "ny", "new york", "us", "usa"]
        
        # US locations require negative longitude (Western hemisphere)
        if any(indicator in name for indicator in us_indicators):
            if lon > 0:
                return False
    
    return True


if __name__ == "__main__":
    """Test location resolution and validation functions."""
    
    print("=" * 60)
    print("RAG Location Database - Test")
    print("=" * 60)
    
    # Test location resolution
    test_cases = [
        ("Tempe", (33.4255, -111.9400)),
        ("Phoenix AZ", (33.4484, -112.0740)),
        ("San Francisco", (37.7749, -122.4194)),
        ("Tmepe", (33.4255, -111.9400)),  # Typo tolerance test
        ("atlanta", (33.7490, -84.3880)),
        ("NonExistentCity", None),
    ]
    
    print("\n1. Location Resolution:")
    passed = 0
    for name, expected in test_cases:
        result = resolve_location(name)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        print(f"  {status} {name:20} -> {result}")
    
    print(f"\n  Passed: {passed}/{len(test_cases)}")
    
    # Test coordinate validation
    print("\n2. Coordinate Validation:")
    validation_tests = [
        ((33.4255, -111.94, "Arizona"), True),
        ((33.4255, 111.94, "Arizona"), False),  # Wrong hemisphere
        ((200, -111.94, None), False),  # Out of range
        ((51.5074, -0.1278, "London"), True),
    ]
    
    for (lat, lon, ctx), expected in validation_tests:
        result = validate_coordinates(lat, lon, ctx)
        status = "✓" if result == expected else "✗"
        print(f"  {status} ({lat:7.2f}, {lon:8.2f}, {str(ctx):10}) -> {result}")
    
    # Database statistics
    print(f"\n3. Database Statistics:")
    print(f"  Total locations: {len(LOCATION_DATABASE)}")
    print(f"  US cities: {len([k for k in LOCATION_DATABASE.keys() if k not in ['london', 'tokyo', 'paris', 'sydney']])}")
    print(f"  International: 4")
    
    print("\n✓ RAG module ready")
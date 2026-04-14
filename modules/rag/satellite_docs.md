# TAT-C & Agentic Mission Analysis Reference

This document serves as the technical "Source of Truth" for the Agentic MCP Framework. It defines the mapping between natural language engineering intent and the underlying **Tradespace Analysis Toolkit for Constellations (TAT-C)** execution logic.

---

## 1. Core Analytical Methods (The Execution Layer)

### `collect_multi_observations`
Used for constellation-level analysis where multiple satellites interact with a single ground point.
- **Logic**: Aggregates individual `collect_observations` calls across all members of a `WalkerConstellation`.
- **Key Output Columns**:
    - `start`: Rise time (UTC) of the contact window.
    - `end`: Set time (UTC) of the contact window.
    - `point_id`: Unique identifier for the ground target.
    - `sat_id`: Identifier for the specific satellite in the fleet providing coverage.

### `aggregate_observations` & `reduce_observations`
Critical for calculating **Mean Revisit** in multi-satellite scenarios.
- **Aggregation**: Groups raw contact windows into "passes" based on temporal overlap or specific sensor constraints.
- **Reduction**: Collapses these passes into a single unified timeline per point to identify **Gaps**.
- **Engineering Note**: In 3x3 Walker Delta configurations, this logic prevents "Double Counting" when two satellites have simultaneous line-of-sight to the same point.

### `compute_ground_track`
Utilized by the `get_ground_track` tool to generate high-fidelity geometric data.
- **Coordinate Reference**: `spice` (Standard for high-accuracy orbital frames).
- **Swath Logic**: Maps the `Instrument` field-of-regard to generate a **Polygon** ribbon rather than a simple sub-satellite line.
- **Temporal Resolution**: Sampling is controlled by `max_delta_t_s`, derived from the instrument swath width and ground velocity.

---

## 2. Orbital & Constellation Schemas

### `TwoLineElements` (TLE)
The primary data structure for SGP4 orbital propagation.
- **Epoch**: The reference timestamp for the orbital elements. The framework uses this to synchronize the simulation `start` time.
- **Inclination**: Defines the latitudinal reach of the sensor. For NOAA 20 (~98.7°), this ensures polar/global coverage.

### `WalkerConstellation`
The primary schema for global fleet design.
- **Configuration**: `delta` (Standard for uniform global coverage).
- **Design Parameters**:
    - `number_satellites` ($N$): Total assets in the fleet.
    - `number_planes` ($P$): Number of distinct orbital planes.
    - `phase_factor` ($F$): Spacing between satellites in adjacent planes.

---

## 3. Geolocation & Grid Generation

### `generate_equally_spaced_points`
Used in `global_coverage_analysis` to ensure statistical validity across the globe.
- **Mechanism**: Solves the "Pole Crowding" issue by distributing points uniformly across a spherical Earth model based on a `mean_distance_m` (e.g., 5000km).
- **Analyst Utility**: Ensures the "Global Mean Revisit" metric isn't skewed by the naturally higher density of satellite passes at high latitudes.

---

## 4. Instrument Specifications (The WMO Oracle)

### `swath_width_to_field_of_regard`
Translates physical sensor dimensions into simulation geometry.
- **Inputs**: `altitude_m` (derived from TLE) and `swath_width_m` (queried from WMO OSCAR).
- **Output**: The angular `field_of_regard` required for the TAT-C `Instrument` object.
- **Example**: The VIIRS instrument (3000km swath) results in a ~120° field of regard, significantly reducing revisit times compared to narrow-FOV sensors.

---

## 5. Agentic State & Status Codes

To facilitate the **Context Flush** and **HITL** logic in the Interface Layer (`gemini_app.py`), the following return strings are standardized:

| Status Code | Meaning | Agent Action |
| :--- | :--- | :--- |
| **`SUCCESS`** | Task completed; metrics verified. | **Flush Context** (Clear Memory). |
| **`HITL_REQUIRED`** | Missing parameters (e.g., Lat/Lon). | Pause and prompt user; **Persist Intent**. |
| **`ERROR`** | TLE fetch failure or math crash. | Maintain context for troubleshooting. |
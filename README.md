# Rio Bus Line Tracker

A Streamlit app that visualizes real-time bus positions for any Rio de Janeiro SPPO line. Data is sourced from the official mobility API at https://dados.mobilidade.rio/gps/sppo. The app fetches a fresh snapshot automatically (cached for 30 seconds), lets users pick a line from the returned dataset, and displays the results on a color-coded map plus a synchronized table.

## Features
- Automatic fetching on every run with Streamlit caching (`@st.cache_data`) so repeated reruns within 30 seconds reuse the same API snapshot.
- Automated coordinate normalization (comma decimals → floats) and timezone-aware timestamp formatting.
- Five-minute freshness filter to keep the UI lightweight and focused on recent telemetry.
- Line picker populated from the fetched dataset plus an optional bus selector to isolate an `ordem`.
- When a single bus is selected, the last 10 locations appear with progressively lighter markers to visualize its path.
- Map centers/zooms around active buses and uses per-bus marker colors that match a styled column in the data grid.
- Streamlit data grid for quick inspection, including the color legend and last update metadata.

## Project Structure
```
app.py              # Streamlit application entry point
requirements.txt    # Python dependencies
README.md           # This document
```

## Prerequisites
- Python 3.11+ (ZoneInfo requires Python 3.9+, but Streamlit benefits from newer versions)
- Virtual environment tool of your choice (optional but recommended)

## Installation & Running
1. **Clone or copy the project.**
2. **Create and activate a virtual environment (optional but recommended).**
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1
   ```
3. **Install dependencies.**
   ```bash
   pip install -r requirements.txt
   ```
4. **Launch the app.**
   ```bash
   streamlit run app.py
   ```
5. **Interact in the browser.**
   - Streamlit automatically opens a tab; if not, follow the printed local URL (default http://localhost:8501).
   - Pick a line from the dropdown (defaults to `169` when present) and optionally filter down to a single bus.
   - Explore the map (auto-centered on active buses) and the synchronized table. To refresh the data sooner than the 30-second cache window, use Streamlit’s “Rerun” control or refresh the browser tab.

## How It Works
1. `fetch_bus_positions()` pulls data from the API whenever the app reruns and caches it for 30 seconds to reduce load.
2. `prepare_bus_dataframe()` filters the DataFrame by the requested line, clamps the data to the last five minutes, normalizes coordinates, parses speeds, and formats timestamps.
3. `assign_bus_colors()` + styling helpers ensure consistent colors between the Folium markers and the table legend.
4. `build_map()` centers/zooms on the active buses, drops historical breadcrumbs when a single bus is selected, and renders the Folium layer.
5. Streamlit renders both the styled table and the Folium map (via `st_folium`).

## Notes
- If no buses match the requested line or the selected bus has no fresh data, the UI explains why instead of failing silently.
- Failed API responses surface as an error message to the user.
- The data cleaning helpers are written to be reusable in other stacks (e.g., moving data access/business logic into a different backend).
- Cached snapshots remain stable during the 30-second TTL, so multiple filters can run against the same dataset for consistent analysis.

# Rio Bus Line Tracker: Architecture & Data Workflow

## Overview
The application is a Streamlit dashboard that visualizes real-time GPS data from Rio de Janeiro’s SPPO buses. It highlights core steps in a modern data pipeline: extraction from a public API, cleaning/normalization, filtering, and presentation through map and tabular views. Folium renders a geographic view, while pandas handles in-memory data shaping. All business logic lives in `app.py`, keeping the implementation lightweight but structured enough to be reused in a larger system (e.g., Django + React) later.

---

## Data Extraction
- **Source API**: `https://dados.mobilidade.rio/gps/sppo` returns a JSON array with bus telemetry (latitude, longitude, timestamps, line identifier, etc.).
- **Fetcher**: `fetch_bus_positions()` performs a GET with `requests`, raises on HTTP errors, and validates that payloads are list-like. Streamlit’s `@st.cache_data(ttl=30)` decorator memoizes responses for 30 seconds to avoid spamming the provider and to keep the UI responsive.
- **Schema expectations**: The function asserts the presence of `linha`, `latitude`, `longitude`, `ordem`, `velocidade`, and `datahora`. Early validation prevents downstream logic from failing silently and demonstrates best practices in data ingestion.
- **Automatic refresh cadence**: Every Streamlit rerun (triggered by user interactions or manual reruns) pulls a new snapshot through the cached fetcher. Within the 30-second TTL, Streamlit serves the cached DataFrame instantly; once it expires, the next rerun renews the dataset. This mirrors reproducible batch-extraction workflows where fresh pulls feed downstream filters.

**Data-pipeline tie-in**: This stage mirrors a typical “extract” step, enforcing schema contracts and caching raw pulls for subsequent transformations.

---

## Data Preparation & Cleaning
### Coordinate normalization (`normalize_coordinate`)
- Latitude/longitude arrive as strings that use commas for decimals (e.g., `"-22,90001"`). The helper replaces commas with periods and converts the result to `float`, returning `None` when parsing fails. This sanitization is crucial before handing coordinates to Folium’s numeric API.

### Timestamp handling (`parse_timestamp`, `format_timestamp`)
- `datahora` values represent milliseconds since epoch but are provided as strings (sometimes with commas). `parse_timestamp` coerces them to floats, builds timezone-aware `datetime` objects (`America/Sao_Paulo`), and returns `None` on invalid data.
- `format_timestamp` applies a human-readable format for use in tooltips/table rows.

### Main preparation (`prepare_bus_dataframe`)
1. Optionally receives an already-fetched DataFrame to avoid redundant API calls (useful when Streamlit reruns multiple times within the cache window).
2. Filters by the selected `linha` (line number) and strips whitespace.
3. Cleans `ordem` identifiers, applies coordinate normalization, converts `velocidade` to numeric, and parses timestamps.
4. Drops rows missing essential fields.
5. Enforces a recency window (≤5 minutes) to reduce map clutter, ensuring the dataset reflects near-real-time conditions.

Collectively, these steps illustrate the “transform” phase: type casting, missing-value handling, feature derivation (`timestamp_dt`, formatted labels), and domain-specific filtering.

---

## UI Logic & Interactivity
-### Automatic snapshot cadence
- The app fetches data automatically during each rerun. Because Streamlit reruns the script whenever widgets change (or when the user clicks “Rerun”/refreshes the page), users see near-real-time snapshots without needing any manual refresh control.
- Cached responses from `@st.cache_data` keep repeated reruns within 30 seconds instantaneous and reduce API pressure, while still ensuring the dataset refreshes promptly when the TTL expires.

### Line selection
- Once data is available, a dropdown lists every unique `linha`. Default selection favors line `169` when present. This prevents typos and keeps the experience consistent with data-driven selection in enterprise dashboards.

### Bus filtering 
- A second dropdown lets the user focus on a specific `ordem` (vehicle). When “Show all buses” is selected, only the freshest point for each bus is displayed. When a single bus is chosen, the app reveals its last ten observations, using progressively lighter colors to visualize its recent path.

### Color encoding
- `assign_bus_colors` guarantees deterministic marker colors per bus. The hex value is shown in the table, keeping the map and grid in sync. `text_color_for_hex` and `style_color_column` ensure accessibility by selecting a complementary font color.

### Map rendering (`build_map`)
- The map centers on the mean latitude/longitude of the displayed subset and then calls `fit_bounds` where possible to zoom around the actual coverage area. 
- Current positions use Folium’s bus icon with the assigned marker color. Historical points render as circle markers with lighter shades (via `lighten_hex`), giving a sparkline-like path overlay without overwhelming the UI.

**Data-prep link:** The visualization layer depends entirely on the curated DataFrame; by the time Folium runs, coordinates are floats, timestamps are formatted strings, and style metadata is attached. This separation mirrors dashboards built atop prepared datasets or feature tables.

### Tabular output
- A pandas `DataFrame` provides complementary detail (Bus ID, last update, speed, coordinates, color swatch). Styling the color column via `DataFrame.style` carries the same palette as the map, demonstrating consistent downstream consumption of prepared data.

---

## Key Design Decisions
1. **Cached auto-refresh workflow**: Streamlit reruns trigger fresh fetches, but the cache keeps repeated interactions within 30 seconds instantaneous. This balances responsiveness with considerate API usage and mirrors controlled batch-ingestion cycles.
2. **Short recency window (5 minutes)**: Improves performance, avoids outdated markers, and acts as an implicit temporal filter—a common data-preparation practice.
3. **Reusable prep functions**: `prepare_bus_dataframe`, coordinate/timestamp utilities, and color helpers can be lifted into another backend, emphasizing modular extraction/prep logic separate from the UI shell.
4. **Fallback-safe rendering**: Every user-facing step checks for empty datasets, malformed API responses, or missing filter results, preventing crashes and ensuring the pipeline either produces useful data or surfaces actionable errors.

---

## Relation to Data Extraction & Preparation Coursework
- **Extraction**: Demonstrates connecting to an external source, validating schema, and caching raw pulls.
- **Cleaning/Preparation**: Includes coordinate normalization, timestamp parsing, type coercion, filtering, and feature engineering—all core topics in data preprocessing.
- **Exploratory visualization**: Shows how cleaned data feeds map + tabular outputs, enabling real-time exploratory analysis for stakeholders.
- **Extensibility**: The logical separation makes it straightforward to swap the Streamlit UI with a React frontend or to schedule the fetch/clean steps in an ETL job, bridging classroom exercises with production-ready patterns.

---

## Possible Extensions
- Persist historical snapshots (e.g., to a database) for trend analysis beyond the five-minute window.
- Introduce anomaly detection (speed spikes, GPS jumps) using the same prep pipeline but adding validation rules.
- Expose the prepared DataFrame via an API to decouple the visualization layer entirely.

These enhancements would deepen the data-engineering narrative by layering additional extraction, transformation, and loading steps on the existing foundation.

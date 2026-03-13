from __future__ import annotations

from datetime import datetime, timedelta
from itertools import cycle
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

API_URL = "https://dados.mobilidade.rio/gps/sppo"
RIO_CENTER = (-22.9068, -43.1729)
RIO_TZ = ZoneInfo("America/Sao_Paulo")

# Folium supports a fixed set of marker colors, so pair each with an accessible hex value for table styling.
COLOR_PALETTE = [
    ("green", "#27ae60"),
    ("blue", "#3498db"),
    ("red", "#e74c3c"),
    ("purple", "#9b59b6"),
    ("orange", "#e67e22"),
    ("darkred", "#c0392b"),
    ("cadetblue", "#5f9ea0"),
    ("darkpurple", "#553285"),
    ("lightred", "#ffa07a"),
    ("lightblue", "#add8e6"),
    ("lightgreen", "#90ee90"),
    ("gray", "#7f8c8d"),
    ("black", "#2d3436"),
    ("pink", "#fd79a8"),
    ("beige", "#f5f5dc"),
]
DEFAULT_COLOR = ("blue", "#3498db")


@st.cache_data(ttl=30)
def fetch_bus_positions() -> pd.DataFrame:
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected API response format")
    df = pd.DataFrame(data)
    expected_columns = {"linha", "latitude", "longitude", "ordem", "velocidade", "datahora"}
    missing = expected_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in API response: {missing}")
    return df


def normalize_coordinate(value: object) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    clean_value = str(value).replace(",", ".")
    try:
        return float(clean_value)
    except ValueError:
        return None


def parse_timestamp(ms_value: object) -> Optional[datetime]:
    try:
        numeric_value = float(str(ms_value).replace(",", "."))
        return datetime.fromtimestamp(numeric_value / 1000, tz=RIO_TZ)
    except (ValueError, TypeError, OSError):
        return None


def format_timestamp(value: object) -> str:
    dt_value = value if isinstance(value, datetime) else parse_timestamp(value)
    if dt_value is None:
        return "Unknown"
    return dt_value.strftime("%Y-%m-%d %H:%M:%S %Z")


def assign_bus_colors(bus_ids: list[str]) -> Dict[str, Dict[str, str]]:
    palette_iter = cycle(COLOR_PALETTE)
    color_map: Dict[str, Dict[str, str]] = {}
    for bus_id in bus_ids:
        if bus_id not in color_map:
            color_name, hex_value = next(palette_iter)
            color_map[bus_id] = {"marker": color_name, "hex": hex_value}
    return color_map


def text_color_for_hex(hex_color: str) -> str:
    hex_value = hex_color.lstrip("#")
    if len(hex_value) != 6:
        return "#000000"
    try:
        r, g, b = (int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return "#000000"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "#000000" if luminance > 186 else "#ffffff"


def lighten_hex(hex_color: str, factor: float) -> str:
    factor = max(0.0, min(1.0, factor))
    hex_value = hex_color.lstrip("#")
    if len(hex_value) != 6:
        return hex_color
    try:
        r, g, b = (int(hex_value[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return hex_color
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def style_color_column(series: pd.Series) -> list[str]:
    styles = []
    for value in series:
        bg = str(value)
        fg = text_color_for_hex(bg)
        styles.append(f"background-color: {bg}; color: {fg};")
    return styles


def prepare_bus_dataframe(
    line_number: str,
    max_age_minutes: Optional[int] = None,
    source_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    df_source = source_df if source_df is not None else fetch_bus_positions()
    df = df_source.copy()
    df["linha"] = df["linha"].astype(str).str.strip()
    line = line_number.strip()
    df = df[df["linha"] == line]

    df["ordem"] = df["ordem"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
    df["latitude"] = df["latitude"].apply(normalize_coordinate)
    df["longitude"] = df["longitude"].apply(normalize_coordinate)
    df["velocidade"] = pd.to_numeric(df["velocidade"], errors="coerce")
    df["timestamp_dt"] = df["datahora"].apply(parse_timestamp)
    df = df.dropna(subset=["latitude", "longitude", "timestamp_dt"])

    if max_age_minutes is not None:
        cutoff = datetime.now(tz=RIO_TZ) - timedelta(minutes=max_age_minutes)
        df = df[df["timestamp_dt"] >= cutoff]

    df["timestamp"] = df["timestamp_dt"].apply(format_timestamp)
    return df


def build_map(bus_df: pd.DataFrame) -> folium.Map:
    if bus_df.empty:
        return folium.Map(location=RIO_CENTER, zoom_start=12)

    avg_lat = bus_df["latitude"].mean()
    avg_lon = bus_df["longitude"].mean()
    folium_map = folium.Map(location=(avg_lat, avg_lon), zoom_start=13)
    for _, row in bus_df.iterrows():
        popup_html = (
            f"<b>Ordem:</b> {row.get('ordem', 'N/A')}<br>"
            f"<b>Velocidade:</b> {row.get('velocidade', 'N/A')} km/h<br>"
            f"<b>Atualizado:</b> {row.get('timestamp', 'N/A')}"
        )
        marker_color = row.get("marker_color") or DEFAULT_COLOR[0]
        color_hex = row.get("color_hex") or DEFAULT_COLOR[1]
        is_history = bool(row.get("is_history"))
        if is_history:
            folium.CircleMarker(
                location=(row["latitude"], row["longitude"]),
                radius=7,
                color=color_hex,
                weight=3,
                fill=True,
                fill_opacity=0.8,
                fill_color=color_hex,
                popup=popup_html,
                tooltip=f"Linha {row['linha']} - {row.get('ordem', 'N/A')}",
            ).add_to(folium_map)
        else:
            folium.Marker(
                location=(row["latitude"], row["longitude"]),
                popup=popup_html,
                tooltip=f"Linha {row['linha']} - {row.get('ordem', 'N/A')}",
                icon=folium.Icon(color=marker_color, icon="bus", prefix="fa"),
            ).add_to(folium_map)

    min_lat, max_lat = bus_df["latitude"].min(), bus_df["latitude"].max()
    min_lon, max_lon = bus_df["longitude"].min(), bus_df["longitude"].max()
    if (min_lat, max_lat, min_lon, max_lon) != (None, None, None, None) and min_lat != max_lat and min_lon != max_lon:
        folium_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(30, 30))
    return folium_map


def main() -> None:
    st.set_page_config(page_title="Rio Bus Tracker", layout="wide")
    st.title("Rio Bus Line Tracker")
    st.write("Visualize the real-time position of buses for a specific line in Rio de Janeiro.")

    try:
        source_df = fetch_bus_positions()
    except Exception as exc:
        st.error(f"Unable to load bus data: {exc}")
        return

    if source_df.empty:
        st.warning("No bus data available from the API right now.")
        return

    st.caption("Live data fetched automatically (cached for 30 seconds to reduce API load).")

    available_lines = sorted(source_df["linha"].astype(str).str.strip().unique())
    if not available_lines:
        st.warning("No bus lines available to select.")
        return

    default_line = "169" if "169" in available_lines else available_lines[0]
    default_index = available_lines.index(default_line)
    line_number = st.sidebar.selectbox(
        "Select a bus line",
        options=available_lines,
        index=default_index,
    )

    try:
        bus_df = prepare_bus_dataframe(line_number, max_age_minutes=5, source_df=source_df)
    except Exception as exc:  # Streamlit will show message to user
        st.error(f"Unable to load bus data: {exc}")
        return

    if bus_df.empty:
        st.warning(f"No bus positions found for line {line_number.strip()}.")
        return

    selectable_buses = sorted(bus for bus in bus_df["ordem"].unique() if bus)
    show_all_label = "Show all buses"
    bus_selection = st.sidebar.selectbox(
        "Filter by specific bus (ordem)",
        [show_all_label, *selectable_buses],
    )

    filtered_df = bus_df.copy()
    if bus_selection != show_all_label:
        filtered_df = filtered_df[filtered_df["ordem"] == bus_selection]
        if filtered_df.empty:
            st.warning("The selected bus has no recent position data (last 5 minutes).")
            return

    filtered_df = filtered_df.sort_values("timestamp_dt", ascending=False)
    if bus_selection == show_all_label:
        display_df = filtered_df.drop_duplicates(subset="ordem", keep="first")
    else:
        display_df = filtered_df.head(1)

    color_assignments = assign_bus_colors(display_df["ordem"].tolist())
    default_color = {"marker": DEFAULT_COLOR[0], "hex": DEFAULT_COLOR[1]}
    display_df = display_df.assign(
        marker_color=display_df["ordem"].apply(lambda bus: color_assignments.get(bus, default_color)["marker"]),
        color_hex=display_df["ordem"].apply(lambda bus: color_assignments.get(bus, default_color)["hex"]),
    )

    map_df = display_df.copy()
    map_df["is_history"] = False

    if bus_selection != show_all_label:
        base_color = color_assignments.get(bus_selection, default_color)
        history_df = filtered_df.head(10).copy()
        history_df = history_df.sort_values("timestamp_dt", ascending=False).reset_index(drop=True)
        total_points = len(history_df)
        if total_points:
            history_df["marker_color"] = base_color["marker"]
            history_df["color_hex"] = history_df.index.to_series().apply(
                lambda idx: lighten_hex(
                    base_color["hex"],
                    factor=min(idx / max(total_points - 1, 1), 0.85),
                )
            )
            history_df["is_history"] = history_df.index > 0
            map_df = history_df

    st.subheader(f"Active buses for line {line_number.strip()}")
    st.caption("Showing locations updated within the last 5 minutes.")
    table_df = (
        display_df[["ordem", "latitude", "longitude", "velocidade", "timestamp", "color_hex"]]
        .rename(
            columns={
                "ordem": "Bus ID",
                "velocidade": "Speed (km/h)",
                "timestamp": "Last Update",
                "color_hex": "Color",
            }
        )
        .reset_index(drop=True)
    )
    styled_table = table_df.style.apply(style_color_column, subset=["Color"])
    st.dataframe(styled_table, use_container_width=True)

    folium_map = build_map(map_df)
    st_folium(folium_map, width=900, height=600)


if __name__ == "__main__":
    main()

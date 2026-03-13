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

NEON_YELLOW = "#f8d349"
TROPICAL_TEAL = "#00bfa6"
URBAN_ORANGE = "#ff8a4a"
ASPHALT = "#101a24"

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


def inject_global_styles() -> None:
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {{
        --asphalt: {ASPHALT};
        --card: #182635;
        --text: #e8f0fb;
        --muted: #a9bfd8;
        --neon: {NEON_YELLOW};
        --teal: {TROPICAL_TEAL};
        --orange: {URBAN_ORANGE};
        --glow: 0 0 22px rgba(0, 191, 166, 0.24);
    }}

    .stApp {{
        background: radial-gradient(circle at 18% 22%, #1f3044 0, transparent 34%),
                    radial-gradient(circle at 82% 8%, #223447 0, transparent 32%),
                    linear-gradient(135deg, #101a24 0%, #152436 48%, #101a24 100%);
        color: var(--text);
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }}

    .main .block-container {{
        max-width: 1200px;
        padding: 1rem 1.25rem 2rem;
    }}

    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Oswald', sans-serif;
        letter-spacing: 0.03em;
        color: var(--neon);
        text-transform: uppercase;
    }}

    p, label, span, .stMarkdown, .stText {{
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        color: var(--text);
    }}

    .info-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.45rem 0.9rem;
        border-radius: 999px;
        border: 1px solid rgba(249, 211, 73, 0.35);
        background: rgba(15, 24, 36, 0.7);
        box-shadow: var(--glow);
        font-size: 0.9rem;
        color: var(--text);
    }}

    .info-pill .pulse-dot {{
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--neon);
        box-shadow: 0 0 0 rgba(248, 211, 73, 0.6);
        animation: pulse 1.8s infinite;
    }}

    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 rgba(248, 211, 73, 0.6); }}
        70% {{ box-shadow: 0 0 0 12px rgba(248, 211, 73, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(248, 211, 73, 0); }}
    }}

    .stButton > button {{
        border-radius: 10px;
        border: 1px solid rgba(0, 191, 166, 0.55);
        background: linear-gradient(135deg, #162739 0%, #1d3044 100%);
        color: var(--text);
        box-shadow: var(--glow);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, filter 180ms ease;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 12px 34px rgba(0, 191, 166, 0.2);
        border-color: var(--neon);
        filter: brightness(1.08);
    }}

    .stDataFrame {{
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
        overflow: hidden;
        transition: transform 160ms ease, box-shadow 160ms ease;
    }}

    .stDataFrame:hover {{
        transform: translateY(-2px);
        box-shadow: 0 22px 60px rgba(0, 0, 0, 0.45);
    }}

    div[data-testid="stTable"] table {{
        background: #0f1824;
        color: var(--text);
    }}

    .stMetric, .stSelectbox, .stAlert {{
        border-radius: 12px;
        background: rgba(24, 38, 53, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28);
    }}

    .stSelectbox > div > div {{
        color: var(--text);
    }}

    div[data-baseweb="select"] > div {{
        background: #1b2c3e !important;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }}

    div[data-testid="stIFrame"] iframe {{
        border-radius: 16px;
        border: 1px solid rgba(0, 191, 166, 0.35);
        box-shadow: 0 18px 55px rgba(0, 0, 0, 0.38);
        background: #122133;
    }}

    .table-title {{
        margin-top: 0.5rem;
        color: var(--muted);
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def fetch_bus_positions() -> pd.DataFrame:
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Formato inesperado na resposta da API")
    df = pd.DataFrame(data)
    expected_columns = {"linha", "latitude", "longitude", "ordem", "velocidade", "datahora"}
    missing = expected_columns - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes na resposta da API: {missing}")
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
        return "Desconhecido"
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
    # Usar imagem de satélite com sobreposição de vias para melhor leitura
    tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    roads_url = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}"
    tile_attr = "Fonte: Esri, Maxar, Earthstar Geographics e colaboradores"
    roads_attr = "Fonte das vias: Esri World Transportation"
    if bus_df.empty:
        empty_map = folium.Map(location=RIO_CENTER, zoom_start=12, tiles=None)
        folium.TileLayer(tile_url, attr=tile_attr, name="Satélite", control=False).add_to(empty_map)
        folium.TileLayer(roads_url, attr=roads_attr, name="Vias", control=False, opacity=0.85).add_to(empty_map)
        return empty_map

    avg_lat = bus_df["latitude"].mean()
    avg_lon = bus_df["longitude"].mean()
    folium_map = folium.Map(location=(avg_lat, avg_lon), zoom_start=13, tiles=None, control_scale=True)
    folium.TileLayer(tile_url, attr=tile_attr, name="Satélite", control=False).add_to(folium_map)
    folium.TileLayer(roads_url, attr=roads_attr, name="Vias", control=False, opacity=0.85).add_to(folium_map)
    for _, row in bus_df.iterrows():
        popup_html = (
            f"<b>Ordem:</b> {row.get('ordem', 'Sem dado')}<br>"
            f"<b>Velocidade:</b> {row.get('velocidade', 'Sem dado')} km/h<br>"
            f"<b>Atualizado:</b> {row.get('timestamp', 'Sem dado')}"
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
                tooltip=f"Linha {row['linha']} - Ônibus {row.get('ordem', 'Sem dado')}",
            ).add_to(folium_map)
        else:
            folium.Marker(
                location=(row["latitude"], row["longitude"]),
                popup=popup_html,
                tooltip=f"Linha {row['linha']} - Ônibus {row.get('ordem', 'Sem dado')}",
                icon=folium.Icon(color=marker_color, icon="bus", prefix="fa"),
            ).add_to(folium_map)

    min_lat, max_lat = bus_df["latitude"].min(), bus_df["latitude"].max()
    min_lon, max_lon = bus_df["longitude"].min(), bus_df["longitude"].max()
    if (min_lat, max_lat, min_lon, max_lon) != (None, None, None, None) and min_lat != max_lat and min_lon != max_lon:
        folium_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(30, 30))
    return folium_map


def main() -> None:
    st.set_page_config(page_title="Painel Ônibus RJ", layout="wide")
    inject_global_styles()
    st.title("Painel de Ônibus do Rio")
    st.write("Visualize em tempo real a posição dos ônibus por linha no Rio de Janeiro.")
    st.markdown(
        "<span class='info-pill'><span class='pulse-dot'></span> Dados ao vivo com cache de 60s para preservar a API</span>",
        unsafe_allow_html=True,
    )

    # Layout principal: mapa na direita, tabela/legenda na esquerda logo abaixo do título
    col_left, col_right = st.columns([1, 1.15])

    try:
        source_df = fetch_bus_positions()
    except Exception as exc:
        st.error(f"Não foi possível carregar os dados de ônibus: {exc}")
        return

    if source_df.empty:
        st.warning("Nenhum dado de ônibus disponível na API neste momento.")
        return

    st.caption("Dados atualizados automaticamente (cache de 60s para reduzir o consumo da API).")

    available_lines = sorted(source_df["linha"].astype(str).str.strip().unique())
    if not available_lines:
        st.warning("Nenhuma linha disponível para seleção.")
        return

    default_line = "169" if "169" in available_lines else available_lines[0]
    default_index = available_lines.index(default_line)
    line_number = st.sidebar.selectbox(
        "Escolha a linha de ônibus",
        options=available_lines,
        index=default_index,
    )

    try:
        bus_df = prepare_bus_dataframe(line_number, max_age_minutes=5, source_df=source_df)
    except Exception as exc:  # Streamlit will show message to user
        st.error(f"Não foi possível carregar os dados de ônibus: {exc}")
        return

    if bus_df.empty:
        st.warning(f"Nenhum ônibus encontrado para a linha {line_number.strip()}.")
        return

    selectable_buses = sorted(bus for bus in bus_df["ordem"].unique() if bus)
    show_all_label = "Todos os ônibus"
    bus_selection = st.sidebar.selectbox(
        "Filtrar por ônibus (ordem)",
        [show_all_label, *selectable_buses],
    )

    filtered_df = bus_df.copy()
    if bus_selection != show_all_label:
        filtered_df = filtered_df[filtered_df["ordem"] == bus_selection]
        if filtered_df.empty:
            st.warning("O ônibus selecionado não tem posições recentes (últimos 5 minutos).")
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

    with col_left:
        st.subheader(f"Ônibus em circulação na linha {line_number.strip()}")
        st.caption("Localizações atualizadas nos últimos 5 minutos.")
        table_df = (
            display_df[["ordem", "latitude", "longitude", "velocidade", "timestamp", "color_hex"]]
            .rename(
                columns={
                    "ordem": "Ônibus (ordem)",
                    "velocidade": "Velocidade (km/h)",
                    "timestamp": "Última atualização",
                    "color_hex": "Cor",
                }
            )
            .reset_index(drop=True)
        )
        styled_table = table_df.style.apply(style_color_column, subset=["Cor"])
        st.dataframe(styled_table, use_container_width=True)

    with col_right:
        st.subheader("Mapa em tempo real")
        st.caption("Mapa estilizado em modo escuro, alinhado ao painel.")
        folium_map = build_map(map_df)
        st_folium(folium_map, width=900, height=600)


if __name__ == "__main__":
    main()

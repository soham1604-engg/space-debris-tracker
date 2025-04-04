import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from skyfield.api import EarthSatellite, load, wgs84
import requests

st.set_page_config(page_title="Space Debris Tracker", layout="wide")
st.title("🚀 Real-Time Space Debris Tracker using TLE Data")

# --- Load TLE Data from Celestrak ---
@st.cache_data(show_spinner=False)
def load_tle():
    url = "https://celestrak.com/NORAD/elements/active.txt"
    response = requests.get(url)
    lines = response.text.strip().splitlines()
    satellites = []
    for i in range(0, len(lines), 3):
        try:
            name = lines[i].strip()
            line1 = lines[i+1].strip()
            line2 = lines[i+2].strip()
            sat = EarthSatellite(line1, line2, name, load.timescale())
            satellites.append(sat)
        except Exception:
            continue
    return satellites

satellites = load_tle()
st.sidebar.success(f"Loaded {len(satellites)} satellites")

# --- Sidebar to select satellite ---
selected_satellite = st.sidebar.selectbox("Select Satellite", [sat.name for sat in satellites])
sat = next(s for s in satellites if s.name == selected_satellite)

# --- Compute Position Over Time ---
@st.cache_data(show_spinner=False)
def compute_positions(sat):
    ts = load.timescale()
    now = datetime.utcnow()
    times = ts.utc(now.year, now.month, now.day, range(0, 60))  # Every minute for 1 hour
    data = []
    for t in times:
        geo = sat.at(t)
        subpoint = wgs84.subpoint(geo)
        data.append({
            "Time": t.utc_datetime(),
            "Latitude": subpoint.latitude.degrees,
            "Longitude": subpoint.longitude.degrees,
            "Elevation_km": subpoint.elevation.km
        })
    return pd.DataFrame(data)

positions_df = compute_positions(sat)

# --- Display Table ---
st.subheader("🔢 Satellite Position Data (Next 1 Hour)")
st.dataframe(positions_df)

# --- Plot Path ---
st.subheader("🌏 Orbit Path Visualization")
fig = go.Figure(go.Scattergeo(
    lat=positions_df["Latitude"],
    lon=positions_df["Longitude"],
    mode='lines+markers',
    line=dict(width=2, color='red'),
    marker=dict(size=4, color='blue'),
    name=selected_satellite
))
fig.update_layout(
    geo=dict(
        projection_type="natural earth",
        showland=True,
        landcolor="rgb(243, 243, 243)",
        subunitwidth=1,
        countrywidth=1,
        showocean=True,
        oceancolor="lightblue",
    ),
    margin={"r":0,"t":0,"l":0,"b":0},
    height=500
)
st.plotly_chart(fig, use_container_width=True)

# --- Footer ---
st.markdown("---")
st.markdown("Developed by Soham | 📡 Powered by Skyfield, Streamlit & Plotly")

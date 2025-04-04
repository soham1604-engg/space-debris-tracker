import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import load
import requests

# 🚀 Step 1: Fetch TLE Data
def fetch_tle_data():
    TLE_URL = "https://www.celestrak.com/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    response = requests.get(TLE_URL)
    tle_data = response.text.strip().split('\n')
    return tle_data

def parse_tle_data(tle_data):
    satellites = []
    for i in range(0, len(tle_data), 3):
        try:
            name, line1, line2 = tle_data[i], tle_data[i+1], tle_data[i+2]
            satellites.append((name.strip(), line1.strip(), line2.strip()))
        except IndexError:
            continue
    return satellites

# Load TLE Data
st.title("🚀 Space Debris Tracker")
tle_data = fetch_tle_data()
satellites = parse_tle_data(tle_data)

if not satellites:
    st.error("❌ Failed to load TLE data. Try refreshing.")
    st.stop()

satellite_names = [sat[0] for sat in satellites]
selected_satellite = st.selectbox("Select a Satellite", satellite_names)

# 🚀 Step 2: Compute Orbital Positions
@st.cache_data
def compute_orbital_positions(name):
    ts = load.timescale()
    satellite = next((sat for sat in satellites if sat[0] == name), None)
    if not satellite:
        return None
    name, line1, line2 = satellite
    sat = load.tle(line1, line2)
    times = ts.utc(2025, 4, range(0, 24))
    geocentric = sat.at(times)
    subpoint = geocentric.subpoint()
    return pd.DataFrame({
        "Time": times.utc_datetime(),
        "Latitude": subpoint.latitude.degrees,
        "Longitude": subpoint.longitude.degrees,
        "Altitude": subpoint.elevation.km,
        "Satellite Name": [name] * len(times)
    })

positions_df = compute_orbital_positions(selected_satellite)
if positions_df is None:
    st.error("❌ Could not compute positions.")
    st.stop()

st.write("### Orbital Positions Table")
st.dataframe(positions_df)

# 🚀 Step 3: Visualize Satellite Orbit
fig = go.Figure()
fig.add_trace(go.Scattergeo(
    lon=positions_df["Longitude"],
    lat=positions_df["Latitude"],
    mode='markers',
    marker=dict(size=5, color='red'),
    name=selected_satellite
))
fig.update_layout(
    title=f"Orbit Path of {selected_satellite}",
    geo=dict(projection_type='orthographic')
)
st.plotly_chart(fig)

st.success("✅ Live Satellite Tracking Running!")

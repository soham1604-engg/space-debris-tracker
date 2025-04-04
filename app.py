import streamlit as st
import pandas as pd
import numpy as np
from skyfield.api import load, EarthSatellite
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------
# 🌍 Load TLE Data
# ------------------------
@st.cache_data
def load_tle_data():
    url = "https://www.celestrak.com/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    response = load.tle_file(url)
    return response

satellites = load_tle_data()

# ------------------------
# 🛰 Search Filter
# ------------------------
st.title("🛰️ Space Debris Tracker")
search_query = st.text_input("Search Satellite by Name:")

if search_query:
    satellites = [sat for sat in satellites if search_query.lower() in sat.name.lower()]
    if not satellites:
        st.warning("No satellites found for that search.")
        st.stop()

# ------------------------
# 📍 Select Satellite
# ------------------------
satellite_names = [sat.name for sat in satellites]
selected_satellite = st.selectbox("Select a Satellite", satellite_names)
satellite = next(sat for sat in satellites if sat.name == selected_satellite)

# ------------------------
# 🧮 Compute Orbital Positions
# ------------------------
@st.cache_data
def compute_orbital_positions(satellite):
    ts = load.timescale()
    times = ts.utc(datetime.utcnow().year, datetime.utcnow().month, datetime.utcnow().day, range(0, 24))
    geocentric = satellite.at(times)
    subpoints = geocentric.subpoint()
    
    data = {
        "Time (UTC)": [t.utc_iso() for t in times],
        "Latitude": subpoints.latitude.degrees,
        "Longitude": subpoints.longitude.degrees,
        "Elevation (km)": subpoints.elevation.km
    }
    
    df = pd.DataFrame(data)
    return df

positions_df = compute_orbital_positions(satellite)

# ------------------------
# 📊 Plot 3D Orbit
# ------------------------
fig = go.Figure(data=[go.Scatter3d(
    x=np.cos(np.radians(positions_df["Longitude"])) * (6371 + positions_df["Elevation (km)"]),
    y=np.sin(np.radians(positions_df["Longitude"])) * (6371 + positions_df["Elevation (km)"]),
    z=positions_df["Elevation (km)"],
    mode='lines+markers',
    marker=dict(size=4, color=positions_df["Elevation (km)"], colorscale='Viridis'),
    line=dict(color='blue', width=2),
    text=positions_df["Time (UTC)"]
)])

fig.update_layout(
    title=f"3D Orbit of {satellite.name}",
    scene=dict(
        xaxis_title='X (km)',
        yaxis_title='Y (km)',
        zaxis_title='Altitude (km)'
    )
)

st.plotly_chart(fig)

# ------------------------
# 📋 Display Data Table
# ------------------------
st.subheader("Orbital Position Data")
st.dataframe(positions_df)

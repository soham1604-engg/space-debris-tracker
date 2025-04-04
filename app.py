import streamlit as st
import pandas as pd
from skyfield.api import EarthSatellite, load
import plotly.graph_objects as go
import requests
from itertools import combinations
import numpy as np

st.set_page_config(page_title="🚁️ Space Debris Tracker", layout="wide")
st.title("🚁️ Space Debris Detection & Tracking using TLE Data")

# --- STEP 1: Load TLE Data from Celestrak ---
@st.cache_data
def fetch_tle_data():
    url = "https://www.celestrak.com/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
    response = requests.get(url)
    tle_lines = response.text.strip().split('\n')

    satellites = []
    for i in range(0, len(tle_lines), 3):
        if i + 2 < len(tle_lines):
            name = tle_lines[i].strip()
            line1 = tle_lines[i+1].strip()
            line2 = tle_lines[i+2].strip()
            satellites.append((name, line1, line2))
    return satellites

tle_data = fetch_tle_data()

# --- STEP 2: Satellite Selector ---
satellite_names = [s[0] for s in tle_data]
selected_satellite = st.selectbox("🔍 Select a Satellite", satellite_names)

# --- STEP 3: Compute Orbital Position ---
def compute_positions(name, line1, line2):
    ts = load.timescale()
    satellite = EarthSatellite(line1, line2, name, ts)
    times = ts.utc(2024, 4, 4, range(0, 24))  # hourly
    geocentric = satellite.at(times)
    subpoint = geocentric.subpoint()

    df = pd.DataFrame({
        "Time (UTC)": times.utc_iso(),
        "Latitude": subpoint.latitude.degrees,
        "Longitude": subpoint.longitude.degrees,
        "Elevation (km)": subpoint.elevation.km,
        "Satellite Name": name
    })
    return df

# Get TLE for selected satellite
for sat in tle_data:
    if sat[0] == selected_satellite:
        line1, line2 = sat[1], sat[2]
        break

positions_df = compute_positions(selected_satellite, line1, line2)
st.success(f"✅ Successfully loaded data for **{selected_satellite}**")

# --- STEP 4: Show Data ---
with st.expander("📄 Orbital Data (Table View)"):
    st.dataframe(positions_df)

# --- STEP 4.5: Satellite Info Panel ---
with st.expander("🛰️ Satellite Information Panel"):
    st.markdown(f"""
    **Satellite Name:** `{selected_satellite}`  
    **TLE Line 1:** `{line1}`  
    **TLE Line 2:** `{line2}`  
    **Tracking Date:** `{positions_df["Time (UTC)"].iloc[0].split("T")[0]}`  
    **Pass Duration:** `{len(positions_df)} hours`
    """)

# --- STEP 5: Visualize Orbit Path ---
fig = go.Figure(go.Scattergeo(
    lon=positions_df["Longitude"],
    lat=positions_df["Latitude"],
    mode='markers+lines',
    marker=dict(size=4, color='red'),
    name='Satellite Path'
))

fig.update_layout(
    title=f'Orbit Path of {selected_satellite}',
    geo=dict(
        showland=True,
        landcolor="rgb(243, 243, 243)",
        countrycolor="rgb(204, 204, 204)",
    ),
    height=600
)

st.plotly_chart(fig)

# --- STEP 6: Collision Prediction with Progress Bar ---
def compute_collision_risks(tle_data, threshold_km=10):
    ts = load.timescale()
    times = ts.utc(2024, 4, 4, range(0, 24))
    positions = []

    for name, line1, line2 in tle_data:
        try:
            satellite = EarthSatellite(line1, line2, name, ts)
            geocentric = satellite.at(times)
            subpoint = geocentric.position.km.T  # shape: (24, 3)
            positions.append((name, subpoint))
        except:
            continue

    potential_collisions = []
    total_pairs = len(positions) * (len(positions) - 1) // 2
    progress = st.progress(0, text="🚨 Analyzing satellite pairs...")

    for idx, ((name1, pos1), (name2, pos2)) in enumerate(combinations(positions, 2)):
        distances = np.linalg.norm(pos1 - pos2, axis=1)
        for t_idx, dist in enumerate(distances):
            if dist < threshold_km:
                potential_collisions.append({
                    "Time (UTC)": times[t_idx].utc_iso(),
                    "Satellite 1": name1,
                    "Satellite 2": name2,
                    "Distance (km)": round(dist, 2)
                })
        progress.progress((idx + 1) / total_pairs)

    return pd.DataFrame(potential_collisions)

with st.expander("🚨 Collision Prediction"):
    st.write("Calculating potential close encounters...")
    collisions_df = compute_collision_risks(tle_data, threshold_km=10)

    if not collisions_df.empty:
        st.warning("⚠️ Potential close approaches detected!")
        st.dataframe(collisions_df)
    else:
        st.success("✅ No potential collisions detected for selected day.")

# --- Footer ---
st.markdown("---")
st.caption("Built with ❤️ by Soham | Data from [Celestrak](https://celestrak.com)")

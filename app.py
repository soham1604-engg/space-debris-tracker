import streamlit as st
import pandas as pd
from skyfield.api import EarthSatellite, load
import plotly.graph_objects as go
import requests
import re
from itertools import combinations
import numpy as np

st.set_page_config(page_title="🚁️ Space Debris Tracker", layout="wide")
st.title("🚁️ Space Debris Detection & Tracking using TLE Data")

# --- STEP 1: Load TLE Data from Celestrak ---



@st.cache_data
def load_tle_from_csv():
    try:
        df = pd.read_csv("tle_data.csv")  # Ensure tle_data.csv is in the same directory
        satellites = list(zip(df["Satellite Name"], df["TLE Line 1"], df["TLE Line 2"]))  # Updated column names
        return satellites
    except Exception as e:
        st.error(f"🚨 Failed to load TLE data from CSV: {e}")
        return []

tle_data = load_tle_from_csv()




# --- STEP 2: Satellite Selector ---
tle_data_cleaned = [(s[0].strip(), s[1], s[2]) for s in tle_data]
satellite_names = [s[0].strip() for s in tle_data]
st.write("Extracted Satellite Names:", satellite_names[:5])


# Satellite selector
selected_satellite = st.selectbox("🔍 Select a Satellite", satellite_names, key="satellite_selector")
st.write("Selected Satellite:", selected_satellite)


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
# Ensure selected satellite exists in the TLE data
selected_tle = next((sat for sat in tle_data if sat[0] == selected_satellite), None)

if selected_tle:
    line1, line2 = selected_tle[1], selected_tle[2]
    positions_df = compute_positions(selected_satellite, line1, line2)
    st.success(f"✅ Successfully loaded data for **{selected_satellite}**")
else:
    st.error("🚨 Selected satellite's TLE data not found. Please check the dataset.")
    positions_df = pd.DataFrame()  # Create an empty dataframe to prevent errors


st.write(f"Selected TLE: {line1}, {line2}")  # Debugging line

if line1 is None or line2 is None:
    st.error("🚨 Satellite TLE data not found! Please select another satellite.")
    st.stop()

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

# --- STEP 6: Collision Prediction ---
def compute_collision_risks(tle_data, threshold_km=10):
    ts = load.timescale()
    times = ts.utc(2024, 4, 4, range(0, 24))
    positions = []

    progress_bar = st.progress(0, text="Loading satellite positions...")

    for idx, (name, line1, line2) in enumerate(tle_data[:50]):  # Limit to 50 for speed
        try:
            satellite = EarthSatellite(line1, line2, name, ts)
            geocentric = satellite.at(times)
            pos = geocentric.position.km.T  # (24, 3)
            positions.append((name, pos))
        except:
            continue
        progress_bar.progress((idx + 1) / min(50, len(tle_data)), text=f"Processed {idx + 1} satellites")

    progress_bar.empty()

    potential_collisions = []
    total_pairs = len(list(combinations(positions, 2)))
    pair_counter = 0
    progress = st.progress(0, text="Checking for potential collisions...")

    for (name1, pos1), (name2, pos2) in combinations(positions, 2):
        distances = np.linalg.norm(pos1 - pos2, axis=1)
        for t_idx, dist in enumerate(distances):
            if dist < threshold_km:
                potential_collisions.append({
                    "Time (UTC)": times[t_idx].utc_iso(),
                    "Satellite 1": name1,
                    "Satellite 2": name2,
                    "Distance (km)": round(dist, 2)
                })
        pair_counter += 1
        progress.progress(pair_counter / total_pairs, text=f"Checked {pair_counter}/{total_pairs} satellite pairs")

    progress.empty()
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
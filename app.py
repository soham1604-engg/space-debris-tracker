import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from skyfield.api import load, EarthSatellite
import requests
import threading
import time
import csv

# 🌍 Streamlit Page Config
st.set_page_config(page_title="🚀 Space Debris Tracker", layout="wide")

# 🚀 Title & Description
st.title("🚀 Real-Time Space Debris Tracker")
st.write("📡 Monitoring space debris and active satellites in real time.")

# 🌍 TLE Data Source
TLE_URL = "https://www.celestrak.com/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
collision_threshold_km = 10.0  # Minimum distance to flag a collision
positions_df = pd.DataFrame()
collision_warnings = []

# 🚀 Function to Fetch & Process TLE Data in Background
def fetch_tle_data():
    global positions_df, collision_warnings
    while True:
        try:
            # 📡 Fetch Latest TLE Data
            response = requests.get(TLE_URL)
            tle_data = response.text.strip().split("\n")
            satellite_names, tle_line1, tle_line2 = [], [], []

            for i in range(0, len(tle_data), 3):
                try:
                    satellite_names.append(tle_data[i].strip())
                    tle_line1.append(tle_data[i + 1].strip())
                    tle_line2.append(tle_data[i + 2].strip())
                except IndexError:
                    continue

            df = pd.DataFrame({
                "Satellite Name": satellite_names,
                "TLE Line 1": tle_line1,
                "TLE Line 2": tle_line2
            })

            # 🚀 Compute Satellite Positions
            ts = load.timescale()
            sat_positions = []

            for _, row in df.iterrows():
                try:
                    satellite = EarthSatellite(row["TLE Line 1"], row["TLE Line 2"], row["Satellite Name"], ts)
                    pos = satellite.at(ts.now()).position.km
                    altitude = np.linalg.norm(pos)  # Calculate altitude from origin
                    sat_positions.append((row["Satellite Name"], pos[0], pos[1], pos[2], altitude))
                except:
                    continue

            positions_df = pd.DataFrame(sat_positions, columns=["Satellite Name", "X", "Y", "Z", "Altitude"])

            # 🚀 Detect Possible Collisions
            collision_warnings = []
            for i in range(len(positions_df)):
                for j in range(i + 1, len(positions_df)):
                    pos1 = positions_df.iloc[i][["X", "Y", "Z"]].values
                    pos2 = positions_df.iloc[j][["X", "Y", "Z"]].values
                    distance = np.linalg.norm(pos1 - pos2)

                    if distance < collision_threshold_km:
                        collision_warnings.append((positions_df.iloc[i]["Satellite Name"], positions_df.iloc[j]["Satellite Name"], distance))

            # 📜 Save Collisions to CSV
            save_collisions()

            print(f"🔄 Updated Data: {len(positions_df)} objects tracked.")
        except Exception as e:
            print(f"❌ Error updating TLE data: {e}")

        time.sleep(300)  # Refresh every 5 minutes

# 🚀 Save Collisions to CSV File
def save_collisions():
    if collision_warnings:
        with open("collisions.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Satellite 1", "Satellite 2", "Distance (km)"])
            writer.writerows(collision_warnings)
        print("✅ Collisions saved to collisions.csv")

# 🔄 Start Background Thread
thread = threading.Thread(target=fetch_tle_data, daemon=True)
thread.start()

# 🎯 UI: Search for a Specific Satellite
st.subheader("🔎 Search for a Satellite")
search_query = st.text_input("Enter satellite name:")

if search_query:
    results = positions_df[positions_df["Satellite Name"].str.contains(search_query, case=False, na=False)]
    if not results.empty:
        st.write(results)
    else:
        st.warning("🚀 No matching satellite found.")

# 📊 UI: Altitude Range Filter
st.sidebar.subheader("📊 Filter Satellites by Altitude")
altitude_range = st.sidebar.slider("Select Altitude Range (km)", min_value=0, max_value=50000, value=(0, 2000))

# 🛠 Fix for missing 'Z' column issue
st.write("🔍 Current DataFrame Columns:", positions_df.columns)

if "Altitude" in positions_df.columns:
    filtered_data = positions_df[
        (positions_df["Altitude"] >= altitude_range[0]) & (positions_df["Altitude"] <= altitude_range[1])
    ]
else:
    filtered_data = pd.DataFrame()
    st.warning("⚠️ 'Altitude' column not found in data.")

st.write(f"Showing {len(filtered_data)} satellites in altitude range {altitude_range} km")
st.dataframe(filtered_data)

# 🚀 Display Real-Time Data
st.subheader("🛰️ Active Satellites & Debris")
if not positions_df.empty:
    st.dataframe(positions_df)
else:
    st.write("🔄 Fetching satellite positions...")

# 🚀 Collision Warnings
st.subheader("⚠️ Potential Collision Alerts")
if collision_warnings:
    for sat1, sat2, dist in collision_warnings:
        st.warning(f"🚨 {sat1} & {sat2} - Distance: {dist:.2f} km")
else:
    st.success("✅ No imminent collisions detected.")

# 🌍 3D Visualization
st.subheader("🌍 3D Visualization of Space Objects")

if not positions_df.empty:
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(
        x=positions_df["X"], y=positions_df["Y"], z=positions_df["Z"],
        mode='markers',
        marker=dict(size=4, color="blue"),
        text=positions_df["Satellite Name"]
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="X (km)",
            yaxis_title="Y (km)",
            zaxis_title="Z (km)"
        ),
        title="3D Space Object Visualization"
    )

    st.plotly_chart(fig)

time.sleep(10)  # Refresh every 10 seconds

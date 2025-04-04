import streamlit as st
import pandas as pd
from skyfield.api import EarthSatellite, load
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="🛰️ Space Debris Tracker", layout="wide")
st.title("🛰️ Space Debris Detection & Tracking using TLE Data")

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

# Get TLE lines for selected satellite
for sat in tle_data:
    if sat[0] == selected_satellite:
        line1, line2 = sat[1], sat[2]
        break

# --- STEP 2.5: Satellite Info Panel ---
ts = load.timescale()
sat_obj = EarthSatellite(line1, line2, selected_satellite, ts)

with st.expander("🛰️ Satellite Info Panel"):
    st.markdown(f"**Name:** {selected_satellite}")
    st.markdown(f"**Epoch:** {sat_obj.epoch.utc_iso()}")
    st.markdown(f"**Inclination:** {sat_obj.model.inclo:.4f}°")
    st.markdown(f"**Eccentricity:** {sat_obj.model.ecco:.7f}")
    st.markdown(f"**Mean Motion:** {sat_obj.model.no_kozai:.7f} revs/day")

# --- STEP 3: Compute Orbital Position ---
def compute_positions(name, line1, line2):
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

positions_df = compute_positions(selected_satellite, line1, line2)
st.success(f"✅ Successfully loaded data for **{selected_satellite}**")

# --- STEP 4: Show Data ---
with st.expander("📄 Orbital Data (Table View)"):
    st.dataframe(positions_df)

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

# --- Footer ---
st.markdown("---")
st.caption("Built with ❤️ by Soham | Data from [Celestrak](https://celestrak.com)")

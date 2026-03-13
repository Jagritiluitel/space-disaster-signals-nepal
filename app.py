import streamlit as st
import pandas as pd
import folium
import requests
from io import StringIO
from streamlit_folium import st_folium

st.set_page_config(page_title="Space Disaster Signals - Nepal", layout="wide")

# ---------- Helpers ----------
def get_marker_color(incident):
    if incident == "Fire":
        return "red"
    elif incident == "Flood":
        return "blue"
    elif incident == "Heavy Rainfall":
        return "darkblue"
    elif incident == "Landslide Risk Signal":
        return "orange"
    elif incident == "Windstorm":
        return "purple"
    else:
        return "green"


def load_fire_data():
    try:
        fire_data = pd.read_csv("data/sample_wildfires.csv")
        return fire_data
    except Exception:
        return None


# ---------- App ----------
st.title("Space Disaster Signals - Nepal")
st.write(
    "A public prototype exploring how satellite data and local reports can surface early disaster signals across Nepal."
)

with st.expander("Why this matters"):
    st.write(
        """
        Nepal faces recurring disasters including floods, landslides, fires, storms, and earthquakes.
        Existing information is often fragmented, reactive, or difficult to interpret quickly.

        This prototype explores whether three kinds of signals can be combined into a clearer public picture:

        1. **Ground-reported incidents** : events already logged
        2. **Satellite wildfire signals** : signals visible from space
        3. **Rainfall-based hazard interpretation** : conditions that may lead to landslides or floods

        The goal is to make emerging risk easier to see not yet to not to replace official systems.
        """
    )

# ---------- Data ----------
data = pd.read_csv("data/sample_incidents.csv")
fire_data = load_fire_data()
rainfall_data = pd.read_csv("data/sample_rainfall.csv")
hazard_profile = pd.read_csv("data/district_hazard_profile.csv")
district_coords = pd.read_csv("data/district_coordinates.csv")

# ---------- Risk Logic ----------
risk_rows = []

for _, row in rainfall_data.iterrows():
    district = row["district"]
    rainfall_risk = row["risk_level"]

    profile_match = hazard_profile[hazard_profile["district"] == district]

    if len(profile_match) == 0:
        continue

    profile = profile_match.iloc[0]

    # Landslide logic
    if rainfall_risk in ["High", "Medium"] and profile["is_landslide_prone"] == "yes":
        risk_rows.append(
            {
                "district": district,
                "hazard": "Landslide",
                "risk_level": "High" if rainfall_risk == "High" else "Medium",
                "reason": f"{rainfall_risk} rainfall in landslide-prone terrain",
            }
        )

    # Flood logic
    if rainfall_risk in ["High", "Medium"] and profile["is_flood_prone"] == "yes":
        risk_rows.append(
            {
                "district": district,
                "hazard": "Flood",
                "risk_level": "High" if rainfall_risk == "High" else "Medium",
                "reason": f"{rainfall_risk} rainfall in flood-prone district",
            }
        )

risk_df = pd.DataFrame(risk_rows)

# ---------- Situation Summary ----------
st.subheader("Situation Summary")

summary_lines = []

high_landslide = risk_df[(risk_df["hazard"] == "Landslide") & (risk_df["risk_level"] == "High")] if len(risk_df) > 0 else pd.DataFrame()
high_flood = risk_df[(risk_df["hazard"] == "Flood") & (risk_df["risk_level"] == "High")] if len(risk_df) > 0 else pd.DataFrame()

summary_lines.append(f"- **{len(high_landslide)}** districts showing **high landslide risk**")
summary_lines.append(f"- **{len(high_flood)}** districts showing **high flood risk**")
summary_lines.append(f"- **{len(fire_data) if fire_data is not None else 0}** wildfire signals loaded")
summary_lines.append(f"- **{len(data)}** reported incident signals in the current dataset")

for line in summary_lines:
    st.markdown(line)

if len(high_landslide) > 0 or len(high_flood) > 0:
    st.markdown("**Most concerning areas today**")
    for _, row in pd.concat([high_landslide, high_flood]).iterrows():
        st.markdown(f"- **{row['district']}** — {row['hazard']} risk ({row['risk_level']})")

# ---------- Metrics ----------
total_signals = len(data)
fire_signals = (data["incident"] == "Fire").sum()
landslide_signals = (risk_df["hazard"] == "Landslide").sum() if len(risk_df) > 0 else 0
flood_signals = (risk_df["hazard"] == "Flood").sum() if len(risk_df) > 0 else 0
high_rainfall_districts = (rainfall_data["risk_level"] == "High").sum()

st.subheader("Signals Today")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Signals", total_signals)
col2.metric("Reported Fire Signals", fire_signals)
col3.metric("High Rainfall Districts", high_rainfall_districts)
col4.metric("Landslide Risk Districts", landslide_signals)
col5.metric("Flood Risk Districts", flood_signals)

# ---------- Priority Attention Areas ----------
st.subheader("Priority Attention Areas")

if len(risk_df) > 0:
    for _, row in risk_df.iterrows():
        st.write(
            f"- **{row['district']}** — **{row['hazard']} risk ({row['risk_level']})**: {row['reason']}"
        )
else:
    st.write("No priority attention areas identified yet.")

# ---------- Legend ----------
st.subheader("Map Legend")
legend_col1, legend_col2, legend_col3, legend_col4, legend_col5, legend_col6 = st.columns(6)
legend_col1.markdown("🔴 **Fire**")
legend_col2.markdown("🔴 **High landslide risk**")
legend_col3.markdown("🟠 **Medium landslide risk**")
legend_col4.markdown("🔵 **Medium flood risk**")
legend_col5.markdown("🔷 **High flood risk**")
legend_col6.markdown("🟣 **Windstorm / other**")

# ---------- Map ----------
st.subheader("Map")

toggle_col1, toggle_col2, toggle_col3, toggle_col4 = st.columns(4)
show_incidents = toggle_col1.checkbox("Show incidents", value=True)
show_wildfires = toggle_col2.checkbox("Show wildfires", value=True)
show_landslides = toggle_col3.checkbox("Show landslide risk", value=True)
show_floods = toggle_col4.checkbox("Show flood risk", value=True)

m = folium.Map(location=[28.3, 84.0], zoom_start=7, tiles="CartoDB positron")

# Sample incident markers
if show_incidents:
    for _, row in data.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            color=get_marker_color(row["incident"]),
            fill=True,
            fill_color=get_marker_color(row["incident"]),
            fill_opacity=0.8,
            popup=(
                f"<b>District:</b> {row['district']}<br>"
                f"<b>Local Level:</b> {row['local_level']}<br>"
                f"<b>Incident:</b> {row['incident']}<br>"
                f"<b>Date:</b> {row['incident_date']}"
            ),
        ).add_to(m)

# Wildfire markers
if show_wildfires and fire_data is not None and len(fire_data) > 0:
    for _, row in fire_data.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=10,
            color="red",
            weight=2,
            fill=True,
            fill_color="yellow",
            fill_opacity=0.9,
            popup=(
                f"<b>Satellite Fire Signal</b><br>"
                f"<b>Source:</b> {row['source']}<br>"
                f"<b>Date:</b> {row['date']}<br>"
                f"<b>Confidence:</b> {row['confidence']}"
            ),
        ).add_to(m)

st_folium(m, width=1000, height=550)

# ---------- Derived hazard markers ----------
if len(risk_df) > 0:
    for _, row in risk_df.iterrows():

        coord_match = district_coords[district_coords["district"] == row["district"]]

        if len(coord_match) == 0:
            continue

        lat = coord_match.iloc[0]["latitude"]
        lon = coord_match.iloc[0]["longitude"]

        # Toggle filtering
        if row["hazard"] == "Landslide" and not show_landslides:
            continue
        if row["hazard"] == "Flood" and not show_floods:
            continue

        # Severity colors
        if row["hazard"] == "Landslide":
            color = "red" if row["risk_level"] == "High" else "orange"
        else:
            color = "darkblue" if row["risk_level"] == "High" else "blue"

        folium.CircleMarker(
            location=[lat, lon],
            radius=12,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=(
                f"<b>{row['hazard']} Risk</b><br>"
                f"<b>District:</b> {row['district']}<br>"
                f"<b>Level:</b> {row['risk_level']}<br>"
                f"<b>Reason:</b> {row['reason']}"
            ),
        ).add_to(m)

# ---------- Live fire debug ----------
st.subheader("Live Satellite Fire Status")
if fire_data is None:
    st.write("No live wildfire data loaded right now.")
else:
    st.write(f"Live wildfire detections loaded: {len(fire_data)}")
    st.dataframe(fire_data.head(), use_container_width=True)

# ---------- Data tables ----------
st.subheader("Incident Data")
st.dataframe(data, use_container_width=True)

st.subheader("Rainfall Risk Data")
st.caption("Current version uses a structured sample rainfall dataset. Next upgrade: live rainfall feed.")
st.dataframe(rainfall_data, use_container_width=True)

st.subheader("Derived Hazard Risk")
st.dataframe(risk_df, use_container_width=True)
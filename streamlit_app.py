import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMapWithTime

# Load and cache the data
@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk_geocoded.feather')

data = load_data()

# Selection for weight column to visualize
weight = st.selectbox(
    'Select Weighting for Heatmap',
    [
        'pd_baseline',
        'pd_shock',
        'crispy_perc_value_change', 
        'pd_difference'
    ]
)

# Select baseline scenario
baseline_scenario = st.selectbox('Baseline Scenario', data['baseline_scenario'].unique())

# Filter data based on the selected baseline scenario to get valid shock scenarios
valid_shock_scenarios = data.loc[data['baseline_scenario'] == baseline_scenario, 'shock_scenario'].unique()

# Select shock scenario based on valid options from filtered data
shock_scenario = st.selectbox('Shock Scenario', valid_shock_scenarios)

# Filter data to include only rows with valid latitude, longitude, and selected weight
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario)
].dropna(subset=['latitude', 'longitude', 'term']).copy()

# Preview the filtered data
st.write(data_withaddress.shape)
st.write(data_withaddress.head())

# Group data by 'term' and create a list of heatmap data for each time point
heat_data = [
    data_withaddress[data_withaddress['term'] == t][['latitude', 'longitude', weight]].values.tolist()
    for t in sorted(data_withaddress['term'].unique())
]

# Check if heat_data is populated and show its shape or a sample
if heat_data:
    st.write(f"Heat Data Length: {len(heat_data)}")
    st.write(f"Sample Heat Data for First Time Period: {heat_data[0][:5]}")  # Displaying first 5 entries for the first time period
else:
    st.warning("No heat data available for the selected scenarios.")

# Create the base map
if not data_withaddress.empty:
    # Center the map based on the first data point
    initial_location = [heat_data[0][0][0], heat_data[0][0][1]] if heat_data[0] else [data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()]

    m = folium.Map(
        location=initial_location, 
        zoom_start=12
    )

    # Add a heatmap layer with time support
    HeatMapWithTime(
        heat_data,
        index=sorted(data_withaddress['term'].unique()),
        radius=10,
        auto_play=True,
        max_opacity=0.8
    ).add_to(m)

    # Display map in Streamlit
    st.title("Heatmap Over Time by Address (Using Term)")
    st_folium(m, width=700, height=500)
else:
    st.warning("No data available for the selected scenarios.")

# Show the dataframe if needed
st.write("Data Preview:")
st.dataframe(data_withaddress[['address', 'latitude', 'longitude', weight, 'term']])

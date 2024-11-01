import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMapWithTime
from collections import OrderedDict

# Display map in Streamlit
st.title("Heatmap Over Time by Address")

# Load the data (consider caching if loading is expensive)
data = pd.read_feather('tiltrisk_geocoded.feather')

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

# Filter data to include only rows with valid data
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario)
].dropna(subset=['latitude', 'longitude', 'term', weight]).copy()

# Group data by 'term' and create an OrderedDict for heatmap data
# Ensure 'term' is a datetime column or convert it to a suitable format
heat_data = OrderedDict()
for t in sorted(data_withaddress['term'].unique()):
    term_data = data_withaddress[data_withaddress['term'] == t][['latitude', 'longitude', weight]].values.tolist()
    # Assuming 't' is a datetime object, use its timestamp as the key
    heat_data[t.timestamp()] = term_data

# Create the base map (consider using folium.Figure for more control)
m = folium.Map(
    location=[data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()],
    zoom_start=12
)

# Add a heatmap layer with time support
HeatMapWithTime(
    heat_data,
    index=sorted(data_withaddress['term'].unique()),  # Sorted terms as time indices
    radius=10,
    auto_play=True,
    max_opacity=0.8
).add_to(m)

# Allow raw HTML for potential interactive elements (use cautiously)
st.experimental_allow_raw_html(st_folium(m, width=700, height=500))

# Show the dataframe if needed
st.write("Data Preview:")
st.dataframe(data_withaddress[['address', 'latitude', 'longitude', weight, 'term']])
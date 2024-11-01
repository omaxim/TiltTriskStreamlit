import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMapWithTime, HeatMap

# Display map in Streamlit
st.title("Heatmap Over Time by Address")

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

sector = st.selectbox('Select the sector',data['ald_sector'].unique())
# Filter data to include only rows with valid latitude, longitude, and selected weight
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario)
].dropna(subset=['latitude', 'longitude', 'term',weight]).copy()

# Group data by 'term' and create a list of heatmap data for each time point
# Each entry in the list corresponds to the data for a particular 'term' time period
heat_data = [
    data_withaddress[data_withaddress['term'] == t][['latitude', 'longitude', weight]].values.tolist()
    for t in sorted(data_withaddress['term'].unique())
]


# Create the base map
m = folium.Map(
    location=[data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()], 
    zoom_start=8
)
## Add a heatmap layer with time support
HeatMapWithTime(
    heat_data
).add_to(m)
# Add a heatmap layer with time support
st_folium(m)
#
## Show the dataframe if needed
#st.write("Data Preview:")
#st.dataframe(data_withaddress[['address', 'latitude', 'longitude', weight, 'term']])

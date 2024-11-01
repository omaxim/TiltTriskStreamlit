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
        'net_present_value_baseline', 
        'net_present_value_shock', 
        'pd_baseline',
        'pd_shock', 
        'net_present_value_difference',
        'crispy_perc_value_change', 
        'pd_difference'
    ]
)

# Filter data to include only rows with valid latitude, longitude, and selected weight
data_withaddress = data.dropna(subset=['latitude', 'longitude', weight, 'term']).copy()

# Group data by 'term' and create a list of heatmap data for each time point
# Each entry in the list corresponds to the data for a particular 'term' time period
heat_data = [
    data_withaddress[data_withaddress['term'] == t][['latitude', 'longitude', weight]].values.tolist()
    for t in sorted(data_withaddress['term'].unique())
]

# Create the base map
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

# Display map in Streamlit
st.title("Heatmap Over Time by Address (Using Term)")
st_folium(m, width=700, height=500)

# Show the dataframe if needed
st.write("Data Preview:")
st.dataframe(data_withaddress[['address', 'latitude', 'longitude', weight, 'term']])

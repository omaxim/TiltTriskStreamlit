import streamlit as st
import pandas as pd
import plotly.express as px

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

# Filter data to only include rows with valid latitude, longitude, and selected weight
data_withaddress = data.dropna(subset=['latitude', 'longitude', weight, 'term'])

# Convert the 'term' column to a datetime object if not already
data_withaddress['term'] = pd.to_datetime(data_withaddress['term'], errors='coerce')
data_withaddress = data_withaddress.dropna(subset=['term'])

# Create a Plotly scatter map with a time slider
fig = px.density_mapbox(
    data_withaddress,
    lat='latitude',
    lon='longitude',
    z=weight,
    radius=10,
    hover_name='address',
    animation_frame='term',
    animation_group='address',
    center={"lat": data_withaddress['latitude'].mean(), "lon": data_withaddress['longitude'].mean()},
    mapbox_style="carto-positron",
    zoom=12,
    title="Heatmap Over Time of " + weight
)

# Set color scale for better visualization
fig.update_layout(coloraxis_colorbar=dict(title=weight))

# Display the interactive map with time slider in Streamlit
st.title("Heatmap Over Time by Address")
st.plotly_chart(fig, use_container_width=True)

# Show the dataframe if needed
st.write("Data Preview:")
st.dataframe(data_withaddress[['address', 'latitude', 'longitude', weight, 'term']])

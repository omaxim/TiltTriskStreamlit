import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from folium.plugins import HeatMap

# Load and cache the data
@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk.feather')

data = load_data()

# Initialize geolocator
geolocator = Nominatim(user_agent="streamlit_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

# Extract latitude and longitude for each address
@st.cache_data
def geocode_addresses(df):
    df['location'] = df['address'].apply(geocode)
    df['latitude'] = df['location'].apply(lambda loc: loc.latitude if loc else None)
    df['longitude'] = df['location'].apply(lambda loc: loc.longitude if loc else None)
    return df.dropna(subset=['latitude', 'longitude'])

data = geocode_addresses(data)

# Create the base map
m = folium.Map(location=[data['latitude'].mean(), data['longitude'].mean()], zoom_start=12)

# Add a heatmap layer based on pd_shock values and locations
heat_data = [[row['latitude'], row['longitude'], row['pd_shock']] for index, row in data.iterrows()]
HeatMap(heat_data).add_to(m)

# Display map in Streamlit
st.title("Heatmap of PD Shock by Address")
st_folium(m, width=700, height=500)

# Show the dataframe if needed
st.write("Data Preview:")
st.dataframe(data[['address', 'latitude', 'longitude', 'pd_shock']])

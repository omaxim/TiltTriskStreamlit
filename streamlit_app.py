import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import geopandas as gpd
from shapely.geometry import Point
from visualsetup import load_visual_identity

st.set_page_config(
    page_title="SME T-risk",
    page_icon="logo.png",
    layout="wide"
)
load_visual_identity('header.png')

st.logo(icon_image='TheiaLogo.svg',image='logo.png',size='large')

nuts_gdf = gpd.read_file("NUTS_RG_60M_2024_4326.shp")
# Display map in Streamlit
st.title("")
st.title("")

# Load and cache the data
@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk_geocoded.feather')

data = load_data()
colx,col1,sepcol,col2,coly = st.columns([1,4,1,4,1])
col1.title("SME T-risk")
col2.title("")

# Selection for weight column to visualize
weight = col1.selectbox(
    'Select Weighting for Heatmap',
    [
        'pd_baseline',
        'pd_shock',
        'crispy_perc_value_change', 
        'pd_difference'
    ]
)

# Select baseline scenario
baseline_scenario = col1.selectbox('Baseline Scenario', data['baseline_scenario'].unique())
term = col1.selectbox('term',data['term'].unique())
# Filter data based on the selected baseline scenario to get valid shock scenarios
valid_shock_scenarios = data.loc[data['baseline_scenario'] == baseline_scenario, 'shock_scenario'].unique()


# Select shock scenario based on valid options from filtered data
shock_scenario = col1.selectbox('Shock Scenario', valid_shock_scenarios)

sector = col1.selectbox('Select the sector',data['ald_sector'].unique())
# Filter data to include only rows with valid latitude, longitude, and selected weight
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario) &
    (data['term'] == int(term))
].dropna(subset=['latitude', 'longitude', 'term',weight]).copy()

NUTS_level = col1.slider('Regional Aggregation Level',1,3,3,1)

# Load the NUTS shapefile
nuts_gdf_levelled = nuts_gdf[nuts_gdf['LEVL_CODE'] == NUTS_level]



# Convert your data into a GeoDataFrame
data_withaddress['geometry'] = data_withaddress.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
data_gdf = gpd.GeoDataFrame(data_withaddress, geometry='geometry', crs="EPSG:4326")

# Spatially join the data with the NUTS boundaries
# This will add the NUTS region information to each data point
data_with_nuts = gpd.sjoin(data_gdf, nuts_gdf_levelled, how="left", predicate="within")

# Aggregate the `pd_shock` by NUTS region (using the NUTS region identifier, e.g., 'NUTS_ID')
aggregated_data = data_with_nuts.groupby('NUTS_ID')[weight].mean().reset_index()

# Merge the aggregated data back with the NUTS shapefile for mapping
nuts_gdf_levelled = nuts_gdf_levelled.merge(aggregated_data, on='NUTS_ID', how='left')

# Initialize the base map centered on the data points
m = folium.Map(
    location=[data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()],
    zoom_start=5
)

# Add a choropleth layer based on the NUTS boundaries
folium.Choropleth(
    geo_data=nuts_gdf_levelled,
    name='choropleth',
    data=nuts_gdf_levelled,
    columns=['NUTS_ID', weight],
    key_on='feature.properties.NUTS_ID',
    fill_color='YlOrRd',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='PD Shock Intensity by Region'
).add_to(m)

# Add layer control and display the map
folium.LayerControl().add_to(m)
with col2:
    folium_static(m)

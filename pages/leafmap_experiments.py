import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import leafmap.foliumap as leafmap

# Load the NUTS shapefile
@st.cache_data
def load_nuts_data():
    return gpd.read_file("NUTS_RG_60M_2024_4326.shp")

nuts_gdf = load_nuts_data()

# Display title
st.title("Heatmap Over Time by Address")

# Load and cache the data
@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk_geocoded.feather')

data = load_data()

# Selection for weight column to visualize
weight = st.selectbox(
    'Select Weighting for Heatmap',
    ['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference']
)

# Select baseline scenario and filter data
baseline_scenario = st.selectbox('Baseline Scenario', data['baseline_scenario'].unique())
term = st.selectbox('Term', data['term'].unique())

# Filter valid shock scenarios based on baseline scenario selection
valid_shock_scenarios = data[data['baseline_scenario'] == baseline_scenario]['shock_scenario'].unique()
shock_scenario = st.selectbox('Shock Scenario', valid_shock_scenarios)

# Select sector
sector = st.selectbox('Select the Sector', data['ald_sector'].unique())

# Filter data based on selections
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario) &
    (data['term'] == int(term))
].dropna(subset=['latitude', 'longitude', 'term', weight]).copy()

# Check if filtered data is empty
if data_withaddress.empty:
    st.warning("No data available for the selected criteria.")
else:
    NUTS_level = st.slider('Regional Aggregation Level', 1, 3, 3, 1)

    # Filter NUTS boundaries based on level
    nuts_gdf_levelled = nuts_gdf[nuts_gdf['LEVL_CODE'] == NUTS_level]

    # Convert to GeoDataFrame
    data_withaddress['geometry'] = data_withaddress.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    data_gdf = gpd.GeoDataFrame(data_withaddress, geometry='geometry', crs="EPSG:4326")

    # Spatially join the data with NUTS boundaries
    data_with_nuts = gpd.sjoin(data_gdf, nuts_gdf_levelled, how="left", predicate="within")

    # Check for empty join results
    if data_with_nuts.empty:
        st.warning("No spatial join results. Check your NUTS boundaries and input data.")
    else:
        # Aggregate data by NUTS region
        aggregated_data = data_with_nuts.groupby('NUTS_ID')[weight].mean().reset_index()

        # Merge aggregated data back with NUTS shapefile
        nuts_gdf_levelled = nuts_gdf_levelled.merge(aggregated_data, on='NUTS_ID', how='left')

        # Handle missing values if necessary
        if nuts_gdf_levelled[weight].isna().any():
            nuts_gdf_levelled[weight] = nuts_gdf_levelled[weight].fillna(0)  # Fill NaNs with 0 or a default value

        # Initialize a Leafmap object centered on the data points with a closer zoom level
        m2 = leafmap.Map(center=[data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()])

        # Add a choropleth layer based on NUTS boundaries without outlines
        m2.add_data(
            nuts_gdf_levelled,
            column=weight,
            cmap="YlOrRd",
            layer_name="PD Shock Intensity by Region",
            legend_title="PD Shock Intensity by Region",
            edge_color=None,  # Remove boundary outlines
            edge_width=0,     # Ensure edge width is set to zero
            fill_opacity=0.7  # Adjust fill opacity for better visibility
        )

        # Display the map in Streamlit
        m2.to_streamlit(width=700, height=500, zoom=12)

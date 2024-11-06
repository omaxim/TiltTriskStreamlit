import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import leafmap.foliumap as leafmap
from visualsetup import load_visual_identity
import branca
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
# Parameters for the colormap
cmap_name = 'YlOrRd'  # Example colormap name
vmin = 0              # Minimum value for the colormap
vmax = 1              # Maximum value for the colormap
num_colors = 10        # Number of colors to sample
# Generate colors from the selected cmap name
cmap = plt.get_cmap(cmap_name)
colors = [mcolors.rgb2hex(cmap(i / (num_colors - 1))) for i in range(num_colors)]
# Create a linear colormap in branca
colormap = branca.colormap.LinearColormap(
    colors=colors,
    vmin=vmin,
    vmax=vmax
)


st.set_page_config(
    page_title="SME T-risk",
    page_icon="logo.png",
    layout="wide"
)
load_visual_identity('header.png')
st.logo(icon_image='TheiaLogo.svg',image='logo.png',size='large')

# Load the NUTS shapefile
@st.cache_data
def load_nuts_data():
    gdf = gpd.read_file("NUTS_RG_60M_2024_4326.shp")
    gdf_country = gdf[gdf['CNTR_CODE'].isin(['FR','DE'])].drop(['NUTS_NAME','COAST_TYPE','URBN_TYPE','MOUNT_TYPE'],axis=1)
    french_colonies = ['FRY','FRY1','FRY2','FRY3','FRY4','FRY5','FRY10','FRY20','FRY30','FRY40','FRY50']
    return gdf_country.loc[~gdf_country['NUTS_ID'].isin(french_colonies)] #Remove french colonies from the map

nuts_gdf = load_nuts_data()
st.title("")
st.title("")
colx,col1,sepcol,col2,coly = st.columns([1,5,1,5,2])
col1.title("SME T-risk")
col2.title("")

# Load and cache the data
@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk_geocoded.feather')

data = load_data()

# Selection for weight column to visualize
weight = col1.selectbox(
    'Select Weighting for Heatmap',
    ['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference']
)

# Select baseline scenario and filter data
baseline_scenario = col1.selectbox('Baseline Scenario', data['baseline_scenario'].unique())
term = col1.selectbox('Term', data['term'].unique())

# Filter valid shock scenarios based on baseline scenario selection
valid_shock_scenarios = data[data['baseline_scenario'] == baseline_scenario]['shock_scenario'].unique()
shock_scenario = col1.selectbox('Shock Scenario', valid_shock_scenarios)

# Select sector
sector = col1.selectbox('Select the Sector', data['ald_sector'].unique())

# Filter data based on selections
data_withaddress = data.loc[
    (data['baseline_scenario'] == baseline_scenario) &
    (data['shock_scenario'] == shock_scenario) &
    (data['term'] == int(term))
].dropna(subset=['latitude', 'longitude', 'term', weight]).copy()

# Check if filtered data is empty
if data_withaddress.empty:
    col1.warning("No data available for the selected criteria.")
else:
    NUTS_level = col1.slider('Regional Aggregation Level', 1, 3, 3, 1)

    # Filter NUTS boundaries based on level
    nuts_gdf_levelled = nuts_gdf[nuts_gdf['LEVL_CODE'] == NUTS_level]

    # Convert to GeoDataFrame
    data_withaddress['geometry'] = data_withaddress.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    data_gdf = gpd.GeoDataFrame(data_withaddress, geometry='geometry', crs="EPSG:4326")

    # Spatially join the data with NUTS boundaries
    data_with_nuts = gpd.sjoin(data_gdf, nuts_gdf_levelled, how="left", predicate="within")

    # Check for empty join results
    if data_with_nuts.empty:
        col1.warning("No spatial join results. Check your NUTS boundaries and input data.")
    else:
        # Aggregate data by NUTS region
        aggregated_data = data_with_nuts.groupby('NUTS_ID')[weight].mean().reset_index()

        # Merge aggregated data back with NUTS shapefile
        nuts_gdf_levelled = nuts_gdf_levelled.merge(aggregated_data, on='NUTS_ID', how='left')

        # Handle missing values if necessary
        if nuts_gdf_levelled[weight].isna().any():
            nuts_gdf_levelled[weight] = nuts_gdf_levelled[weight].fillna(0)  # Fill NaNs with 0 or a default value
        nuts_gdf_levelled[weight] = nuts_gdf_levelled[weight]#.map('{:.2%}'.format)
        # Initialize a Leafmap object centered on the data points with a closer zoom level
        m2 = leafmap.Map(center=[data_withaddress['latitude'].mean(), data_withaddress['longitude'].mean()])
        # Define the style_function to dynamically apply color based on the `weight` column
        # Define the colormap manually (from light to dark)


        def style_function(feature):
            # Get the value from the `weight` column for the feature
            value = feature["properties"].get(weight)  # Adjust "weight" as per your actual column name

            color = colormap(value) if value is not None else "#8c8c8c"  # Default color if None

            # Return the style for the feature
            return {
                "fillColor": color,       # Color based on the value
                "fillOpacity": 0.9,       # Adjust fill opacity
                "weight": 0,              # No outline weight
                "stroke": True,         
                "color": "#000000",       # White border color (if needed)
            }

        # Define the highlight_function to change the style when a feature is highlighted (hovered)
        def highlight_function(feature):
            return {
                "fillOpacity": 0.9,       # Slightly increase opacity on hover
                "weight": 2,              # Thicker border on hover
                "stroke": True,           # Add stroke on hover
                "color": "#ff0000",       # Red border on hover
            }

        # Add a choropleth layer based on NUTS boundaries without outlines
        m2.add_data(
            nuts_gdf_levelled,
            column=weight,
            layer_name=weight,
            add_legend=False,
            fill_opacity=0.7,  # Adjust fill opacity for better visibility
            style_function=style_function,       # Apply the style function
            highlight_function=highlight_function,  # Apply the highlight function on hover
            fields=[weight,'NAME_LATN'],
            aliases=["Weight (%)", "Region"],
            style=("background-color: white; color: black; font-weight: bold;"),
            #formatters={
            #    weight: lambda x: f"{x:.2%}" if x is not None else "N/A",  # Format as a percentage
            #},
            sticky=True

        )

        # Display the map in Streamlit
        with col2:
            m2.to_streamlit(width=700, height=500,add_layer_control=False)

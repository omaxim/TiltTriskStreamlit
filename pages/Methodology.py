import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import leafmap.foliumap as leafmap
from visualsetup import load_visual_identity
import branca
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# Utility function for colormap
def get_colormap(cmap_name='YlOrBr', vmin=0, vmax=0.2, num_colors=10, invert=False):
    cmap = plt.get_cmap(cmap_name)
    colors = [mcolors.rgb2hex(cmap(i / (num_colors - 1))) for i in range(num_colors)]
    if invert:
        colors = colors[::-1]
    return branca.colormap.LinearColormap(colors=colors, vmin=vmin, vmax=vmax)

st.set_page_config(page_title="SME T-risk", page_icon="logo.png", layout="wide")
load_visual_identity('header.png')

# Unified data loading and aggregation function
@st.cache_data
def load_data():
    # Load TRisk data
    data = pd.read_feather('tiltrisk_geocoded.feather').dropna(subset=['latitude', 'longitude']).replace('_', '', regex=True)
    pivot_data = data.pivot_table(
        index=['latitude', 'longitude'],
        columns=['baseline_scenario', 'shock_scenario', 'term', 'ald_sector'],
        values=['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference']
    )
    pivot_data.columns = ['_'.join(map(str, col)) for col in pivot_data.columns]
    pivot_data.reset_index(inplace=True)
    pivot_data['geometry'] = pivot_data.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    trisk_gdf = gpd.GeoDataFrame(pivot_data, geometry='geometry', crs="EPSG:4326")

    # Load NUTS shapefile and filter for France and Germany
    gdf = gpd.read_file("NUTS_RG_60M_2024_4326.shp")
    gdf_country = gdf[gdf['CNTR_CODE'].isin(['FR', 'DE'])].drop(
        ['NUTS_NAME', 'COAST_TYPE', 'URBN_TYPE', 'MOUNT_TYPE'], axis=1, errors='ignore'
    )
    french_colonies = ['FRY', 'FRY1', 'FRY2', 'FRY3', 'FRY4', 'FRY5', 'FRY10', 'FRY20', 'FRY30', 'FRY40', 'FRY50']
    nuts_gdf = gdf_country.loc[~gdf_country['NUTS_ID'].isin(french_colonies)]

    # Aggregate data by NUTS level
    nuts_levels_aggregated = []
    for level in [1, 2, 3]:
        nuts_level_gdf = nuts_gdf[nuts_gdf['LEVL_CODE'] == level]
        data_with_nuts = gpd.sjoin(trisk_gdf, nuts_level_gdf, how="left", predicate="within")

        # Check for NaN values in NUTS_ID and filter them out
        if data_with_nuts['NUTS_ID'].isna().any():
            st.warning(f"Some data points could not be assigned a NUTS region at level {level}. These will be ignored in the aggregation.")
        data_with_nuts = data_with_nuts.dropna(subset=['NUTS_ID'])

        # Select only numeric columns for aggregation
        numeric_columns = data_with_nuts.select_dtypes(include=['number']).columns
        aggregated_data = data_with_nuts.groupby('NUTS_ID')[numeric_columns].mean().reset_index()

        # Merge aggregated data with the NUTS level GeoDataFrame
        nuts_level_aggregated = nuts_level_gdf.merge(aggregated_data, on='NUTS_ID', how='left')
        nuts_level_aggregated = nuts_level_aggregated.fillna(0)
        nuts_levels_aggregated.append(nuts_level_aggregated)

    return nuts_levels_aggregated

# Load data
nuts_gdf_levels = load_data()

# Set up UI elements for data selection
colx, col1, sepcol, col2, coly = st.columns([1, 5, 1, 5, 2])

# Sidebar Controls for user selections
weight = col1.selectbox('Select Weighting for Heatmap', ['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference'])
baseline_scenario = col1.selectbox('Baseline Scenario', set([col.split('_')[-4] for col in nuts_gdf_levels[0].columns if col.startswith(f"{weight}_")]))
term = col1.selectbox('Term', set([col.split('_')[-2] for col in nuts_gdf_levels[0].columns if col.startswith(f"{weight}_{baseline_scenario}_")]))
shock_scenario = col1.selectbox('Shock Scenario', set([col.split('_')[-3] for col in nuts_gdf_levels[0].columns if col.startswith(f"{weight}_{baseline_scenario}_")]))
sector = col1.selectbox('Select the Sector', set([col.split('_')[-1] for col in nuts_gdf_levels[0].columns if col.startswith(f"{weight}_{baseline_scenario}_{shock_scenario}_{term}_")]))

selected_column = f"{weight}_{baseline_scenario}_{shock_scenario}_{term}_{sector}"
if selected_column not in nuts_gdf_levels[0].columns:
    col1.warning("No data available for the selected criteria.")
else:
    NUTS_level = col1.slider('Regional Aggregation Level', 1, 3, 3, 1)
    nuts_gdf_level = nuts_gdf_levels[NUTS_level - 1]

    # Filter for selected data column and set up color map
    vmin = nuts_gdf_level[selected_column].min()
    vmax = 0.5 * nuts_gdf_level[selected_column].max()
    colormap = get_colormap(vmin=vmin, vmax=vmax, num_colors=20, invert=(vmin <= -0.001))

    def style_function(feature):
        value = feature["properties"].get(selected_column)
        color = colormap(value) if value is not None else "#8c8c8c"
        return {"fillColor": color, "fillOpacity": 0.9, "weight": 0.1, "stroke": True, "color": "#000000"}

    def highlight_function(feature):
        return {"fillOpacity": 0.9, "weight": 2, "stroke": True, "color": "#ff0000"}

    # Map display with Leafmap
    m2 = leafmap.Map(center=[nuts_gdf_level.geometry.centroid.y.mean(), nuts_gdf_level.geometry.centroid.x.mean()])
    m2.add_data(
        nuts_gdf_level,
        column=selected_column,
        layer_name=selected_column,
        add_legend=False,
        fill_opacity=0.7,
        style_function=style_function,
        highlight_function=highlight_function,
        fields=['NUTS_ID', selected_column],
        style=("background-color: white; color: black; font-weight: bold;"),
        sticky=True
    )

    with col2:
        m2.to_streamlit(width=700, height=500, add_layer_control=False)

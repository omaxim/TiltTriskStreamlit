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
st.logo(icon_image='TheiaLogo.svg', image='logo.png', size='large')

# Load the NUTS shapefile
@st.cache_data
def load_nuts_data():
    gdf = gpd.read_file("NUTS_RG_60M_2024_4326.shp")
    gdf_country = gdf[gdf['CNTR_CODE'].isin(['FR','DE'])].drop(['NUTS_NAME', 'COAST_TYPE', 'URBN_TYPE', 'MOUNT_TYPE'], axis=1)
    french_colonies = ['FRY', 'FRY1', 'FRY2', 'FRY3', 'FRY4', 'FRY5', 'FRY10', 'FRY20', 'FRY30', 'FRY40', 'FRY50']
    return gdf_country.loc[~gdf_country['NUTS_ID'].isin(french_colonies)]
colx,col1,sepcol,col2,coly = st.columns([1,5,1,5,2])

nuts_gdf = load_nuts_data()

# Pivoted Data Loading Function
@st.cache_data
def load_data():
    data = pd.read_feather('tiltrisk_geocoded.feather').dropna(subset=['latitude', 'longitude'])
    # Pivot the data
    pivot_data = data.pivot_table(
        index=['latitude', 'longitude'],
        columns=['baseline_scenario', 'shock_scenario', 'term', 'ald_sector'],
        values=['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference']
    )
    # Flatten multi-index columns
    pivot_data.columns = ['_'.join(map(str, col)) for col in pivot_data.columns]
    # Reset index to make latitude and longitude columns accessible
    pivot_data.reset_index(inplace=True)
    # Convert to GeoDataFrame
    pivot_data['geometry'] = pivot_data.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    return gpd.GeoDataFrame(pivot_data, geometry='geometry', crs="EPSG:4326")

data = load_data()

# Sidebar Controls for user selections
weight = col1.selectbox('Select Weighting for Heatmap', ['pd_baseline', 'pd_shock', 'crispy_perc_value_change', 'pd_difference'])
baseline_scenario = col1.selectbox('Baseline Scenario', [col.split('_')[1] for col in data.columns if col.startswith(f"{weight}_")])
term = col1.selectbox('Term', [col.split('_')[3] for col in data.columns if col.startswith(f"{weight}_{baseline_scenario}_")])
shock_scenario = col1.selectbox('Shock Scenario', [col.split('_')[2] for col in data.columns if col.startswith(f"{weight}_{baseline_scenario}_")])
sector = col1.selectbox('Select the Sector', [col.split('_')[4] for col in data.columns if col.startswith(f"{weight}_{baseline_scenario}_{shock_scenario}_{term}_")])

# Filter for selected column
selected_column = f"{weight}_{baseline_scenario}_{shock_scenario}_{term}_{sector}"
if selected_column not in data.columns:
    col1.warning("No data available for the selected criteria.")
else:
    NUTS_level = col1.slider('Regional Aggregation Level', 1, 3, 3, 1)
    nuts_gdf_levelled = nuts_gdf[nuts_gdf['LEVL_CODE'] == NUTS_level]

    # Filter for selected data column and drop NaNs
    data_selected = data[['geometry', selected_column]].dropna(subset=[selected_column])

    # Spatial Join with NUTS
    data_with_nuts = gpd.sjoin(data_selected, nuts_gdf_levelled, how="left", predicate="within")
    if data_with_nuts.empty:
        col1.warning("No spatial join results. Check your NUTS boundaries and input data.")
    else:
        aggregated_data = data_with_nuts.groupby('NUTS_ID')[selected_column].mean().reset_index()
        nuts_gdf_levelled = nuts_gdf_levelled.merge(aggregated_data, on='NUTS_ID', how='left')
        nuts_gdf_levelled[selected_column] = nuts_gdf_levelled[selected_column].fillna(0)

        vmin = data[selected_column].min()
        vmax = 0.5 * data[selected_column].max()
        colormap = get_colormap(vmin=vmin, vmax=vmax, num_colors=20, invert=(vmin <= -0.001))

        def style_function(feature):
            value = feature["properties"].get(selected_column)
            color = colormap(value) if value is not None else "#8c8c8c"
            return {"fillColor": color, "fillOpacity": 0.9, "weight": 0.1, "stroke": True, "color": "#000000"}

        def highlight_function(feature):
            return {"fillOpacity": 0.9, "weight": 2, "stroke": True, "color": "#ff0000"}

        m2 = leafmap.Map(center=[data['latitude'].mean(), data['longitude'].mean()])
        m2.add_data(
            nuts_gdf_levelled,
            column=selected_column,
            layer_name=selected_column,
            add_legend=False,
            fill_opacity=0.7,
            style_function=style_function,
            highlight_function=highlight_function,
            fields=['NAME_LATN', selected_column],
            style=("background-color: white; color: black; font-weight: bold;"),
            sticky=True
        )

        with col2:
            m2.to_streamlit(width=700, height=500, add_layer_control=False)

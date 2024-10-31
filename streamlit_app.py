import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    return pd.read_feather('tiltrisk.feather')

data = load_data()

st.dataframe(data)
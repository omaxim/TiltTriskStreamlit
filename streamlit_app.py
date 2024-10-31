import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    return pd.read_csv('tiltrisk_alpha.csv')

data = load_data()

st.dataframe(data)
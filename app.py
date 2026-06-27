import streamlit as st
from modules.coconut import coconut_page
from modules.milk import milk_page
from modules.dashboard import dashboard

st.set_page_config(
    page_title="Farm Yield Tracker",
    layout="wide"
)

st.title("🌾 Farm Yield & Revenue Tracker")

menu = st.sidebar.radio(
    "Select",
    [
        "Dashboard",
        "Coconut Harvest",
        "Milk Yield"
    ]
)

if menu == "Dashboard":
    dashboard()

elif menu == "Coconut Harvest":
    coconut_page()

elif menu == "Milk Yield":
    milk_page()
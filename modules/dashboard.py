import streamlit as st
import pandas as pd

MILK="data/milk.csv"
COCONUT="data/coconut.csv"


def dashboard():

    st.header(
        "📊 Farm Dashboard"
    )

    c1,c2=st.columns(2)

    coconut_rev=0
    milk_rev=0

    try:

        coco=pd.read_csv(
            COCONUT
        )

        if len(coco):

            coconut_rev=(
                coco
                .iloc[-1]
                ["revenue"]
            )

    except:
        pass

    try:

        milk=pd.read_csv(
            MILK
        )

        if len(milk):

            milk["date"]=pd.to_datetime(
                milk["date"]
            )

            last=(
                pd.Timestamp.today()
                -
                pd.Timedelta(
                    days=30
                )
            )

            milk_rev=(
                milk[
                    milk["date"]
                    >=
                    last
                ]
                [
                    "total_revenue"
                ]
                .sum()
            )

    except:
        pass

    c1.metric(
        "🌴 Last Coconut Revenue",
        f"₹{coconut_rev:,.0f}"
    )

    c2.metric(
        "🥛 Last 30 Day Milk Revenue",
        f"₹{milk_rev:,.0f}"
    )
import streamlit as st
import pandas as pd
import plotly.express as px

from modules.storage import load_data

FILE = "data/coconut.csv"

COLUMNS = [
    "harvest_date",
    "yield_kg",
    "yield_count",
    "rate_per_ton",
    "revenue"
]


def save(df):

    if len(df):

        df["harvest_date"] = pd.to_datetime(
            df["harvest_date"]
        )

        df = (
            df
            .sort_values(
                "harvest_date"
            )
            .reset_index(
                drop=True
            )
        )

    df.to_csv(
        FILE,
        index=False
    )


def calculate_revenue(
    yield_kg,
    rate_per_ton
):

    tons = (
        yield_kg
        / 1000
    )

    return (
        tons
        * rate_per_ton
    )


def coconut_page():

    tabs = st.tabs([
        "Entry",
        "Analytics"
    ])

    with tabs[0]:
        entry()

    with tabs[1]:
        analytics()


def entry():

    df = load_data(
        FILE,
        COLUMNS
    )

    st.subheader(
        "🌴 Harvest Entry"
    )

    with st.form(
        "harvest_form"
    ):

        harvest_date = st.date_input(
            "Harvest Date"
        )

        yield_kg = st.number_input(
            "Yield (KG)",
            min_value=0.0,
            step=10.0
        )

        yield_count = st.number_input(
            "Yield Count",
            min_value=0
        )

        rate = st.number_input(
            "Rate (₹ / Ton)",
            min_value=0.0
        )

        revenue = calculate_revenue(
            yield_kg,
            rate
        )

        c1, c2 = st.columns(
            2
        )

        c1.metric(
            "Equivalent Tons",
            f"{yield_kg/1000:.2f}"
        )

        c2.metric(
            "Revenue",
            f"₹{revenue:,.0f}"
        )

        save_btn = st.form_submit_button(
            "Save Harvest"
        )

    if save_btn:

        row = pd.DataFrame([[
            harvest_date,
            yield_kg,
            yield_count,
            rate,
            revenue
        ]],
        columns=COLUMNS)

        df = pd.concat(
            [
                df,
                row
            ],
            ignore_index=True
        )

        save(
            df
        )

        st.success(
            "Harvest Saved"
        )

        st.rerun()

    st.subheader(
        "Harvest Records"
    )

    st.dataframe(
        df,
        use_container_width=True
    )


def analytics():

    df = load_data(
        FILE,
        COLUMNS
    )

    if df.empty:

        st.info(
            "No harvest data"
        )

        return

    df[
        "harvest_date"
    ] = pd.to_datetime(
        df[
            "harvest_date"
        ]
    )

    latest = (
        df
        .iloc[-1]
    )

    c1, c2, c3 = st.columns(
        3
    )

    c1.metric(
        "Latest Revenue",
        f"₹{latest['revenue']:,.0f}"
    )

    c2.metric(
        "Latest Yield",
        f"{latest['yield_kg']:,.0f} KG"
    )

    c3.metric(
        "Count",
        int(
            latest[
                "yield_count"
            ]
        )
    )

    st.subheader(
        "Revenue Trend"
    )

    fig1 = px.line(
        df,
        x="harvest_date",
        y="revenue",
        markers=True
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    st.subheader(
        "Yield Trend"
    )

    fig2 = px.bar(
        df,
        x="harvest_date",
        y="yield_kg"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    st.subheader(
        "Records"
    )

    st.dataframe(
        df,
        use_container_width=True
    )
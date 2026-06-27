import streamlit as st
import pandas as pd
import plotly.express as px

from modules.storage import load_data

MILK="data/milk.csv"


COLUMNS=[
"date",
"morning_yield",
"morning_rate",
"morning_revenue",
"evening_yield",
"evening_rate",
"evening_revenue",
"total_revenue"
]


def save(df):

    df["date"]=pd.to_datetime(
        df["date"]
    )

    df=(
        df
        .sort_values(
            "date"
        )
        .reset_index(
            drop=True
        )
    )

    df.to_csv(
        MILK,
        index=False
    )


def calc(df):

    df[
        "morning_revenue"
    ]=(
        df[
            "morning_yield"
        ]
        *
        df[
            "morning_rate"
        ]
    )

    df[
        "evening_revenue"
    ]=(
        df[
            "evening_yield"
        ]
        *
        df[
            "evening_rate"
        ]
    )

    df[
        "total_revenue"
    ]=(
        df[
            "morning_revenue"
        ]
        +
        df[
            "evening_revenue"
        ]
    )

    return df


def milk_page():

    tab1,tab2=st.tabs([
        "Entry",
        "Analytics"
    ])

    with tab1:
        entry()

    with tab2:
        analytics()


def entry():

    st.subheader(
        "Generate Table"
    )

    start=st.date_input(
        "From"
    )

    end=st.date_input(
        "To"
    )

    if st.button(
        "Generate"
    ):

        dates=pd.date_range(
            start,
            end
        )

        st.session_state[
            "editor"
        ]=pd.DataFrame({

            "date":
            dates.date,

            "morning_yield":
            0,

            "morning_rate":
            0,

            "evening_yield":
            0,

            "evening_rate":
            0
        })

    if "editor" in st.session_state:

        edited=st.data_editor(

            st.session_state[
                "editor"
            ],

            use_container_width=True
        )

        if st.button(
            "Save"
        ):

            edited=calc(
                edited
            )

            old=load_data(
                MILK,
                COLUMNS
            )

            final=pd.concat(
                [
                    old,
                    edited
                ]
            )

            save(
                final
            )

            st.success(
                "Saved"
            )

            st.rerun()


def analytics():

    df=load_data(
        MILK,
        COLUMNS
    )

    if df.empty:

        st.info(
            "No data"
        )

        return

    df["date"]=pd.to_datetime(
        df["date"]
    )

    trend=st.selectbox(

        "Trend",

        [
            "All",
            "Last 7 Days",
            "Last 30 Days"
        ]
    )

    if trend=="Last 7 Days":

        df=df[
            df[
                "date"
            ]
            >=
            (
                pd.Timestamp.today()
                -
                pd.Timedelta(
                    days=7
                )
            )
        ]

    elif trend=="Last 30 Days":

        df=df[
            df[
                "date"
            ]
            >=
            (
                pd.Timestamp.today()
                -
                pd.Timedelta(
                    days=30
                )
            )
        ]

    st.subheader(
        "Records"
    )

    selected=st.dataframe(
        df,
        use_container_width=True
    )

    st.subheader(
        "Revenue Trend"
    )

    fig=px.line(

        df,

        x="date",

        y="total_revenue",

        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader(
        "Milk Trend"
    )

    fig2=px.line(

        df,

        x="date",

        y=[
            "morning_yield",
            "evening_yield"
        ]
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )
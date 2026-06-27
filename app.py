import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import json
import os
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from datetime import datetime, timedelta
import urllib3

urllib3.disable_warnings()
load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# --- File paths ---
COCONUT_CSV = "data/coconut.csv"
MILK_CSV = "data/milk.csv"

COCONUT_COLUMNS = ["harvest_date", "yield_kg", "yield_count", "rate_per_ton", "revenue"]
MILK_COLUMNS = ["date", "morning_yield", "morning_rate", "morning_revenue",
                "evening_yield", "evening_rate", "evening_revenue", "total_revenue"]

os.makedirs("data", exist_ok=True)

# --- Storage ---
def load_data(file_path, columns):
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(file_path, index=False)
        return df
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return pd.DataFrame(columns=columns)
        return df
    except Exception:
        return pd.DataFrame(columns=columns)

def save_data(file_path, df):
    df.to_csv(file_path, index=False)

# --- VLM Extraction ---
def encode_image(img):
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    return base64.b64encode(buffer.getvalue()).decode()

def extract_bill_data(img):
    image_b64 = encode_image(img)
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    prompt = """This is a dairy milk bill with two tables — morning (left) and evening (right) sessions.
Extract all data rows and return as a JSON array with this exact structure:
[
  {
    "date": 1,
    "morning_yield": 15.2,
    "morning_price": 33.19,
    "evening_yield": 17.5,
    "evening_price": 30.67
  }
]
Rules:
- date is an integer (day of month, 1-31)
- morning_yield and morning_price are floats from the left table
- evening_yield and evening_price are floats from the right table
- Return only the JSON array, no explanation, no markdown backticks

the prices are called 1 லி.விலை in Tamil in both the sections
"""
    payload = {
        "model": "moonshotai/kimi-k2.6",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                    },
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
        "top_p": 1.00,
        "stream": False
    }
    response = requests.post(INVOKE_URL, headers=headers, json=payload, verify=False)
    return response.json()

def parse_vlm_response(response):

    try:
        content = response['choices'][0]['message']['content'].strip()
        if content.startswith("```"):
            lines = content.split('\n')
            content = '\n'.join(lines[1:-1])
        return json.loads(content), None
    except Exception as e:
        return None, str(e)

# --- Calculations ---
def calculate_coconut_revenue(yield_kg, rate_per_ton):
    return (yield_kg / 1000) * rate_per_ton

def calculate_milk_revenues(morning_yield, morning_rate, evening_yield, evening_rate):
    morning_revenue = morning_yield * morning_rate
    evening_revenue = evening_yield * evening_rate
    total_revenue = morning_revenue + evening_revenue
    return morning_revenue, evening_revenue, total_revenue

# --- App ---
st.set_page_config(page_title="Farm Tracker", layout="wide", page_icon="🌾")

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #2e7d32;
    }
    .section-header {
        color: #2e7d32;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌾 Farm Yield & Revenue Tracker")

tab_dashboard, tab_milk, tab_coconut = st.tabs(["Dashboard", "Milk", "Coconut"])

# ============================================================
# DASHBOARD
# ============================================================
with tab_dashboard:
    st.subheader("Overview")

    coconut_df = load_data(COCONUT_CSV, COCONUT_COLUMNS)
    milk_df = load_data(MILK_CSV, MILK_COLUMNS)

    col1, col2, col3 = st.columns(3)

    # Latest coconut revenue
    if not coconut_df.empty:
        coconut_df['harvest_date'] = pd.to_datetime(coconut_df['harvest_date'])
        latest_coconut = coconut_df.sort_values('harvest_date').iloc[-1]
        with col1:
            st.metric("Latest Coconut Revenue", f"₹{float(latest_coconut['revenue']):,.2f}")
            st.caption(f"Harvest on {latest_coconut['harvest_date'].strftime('%d %b %Y')}")
    else:
        with col1:
            st.metric("Latest Coconut Revenue", "No data")

    # Last 30 days milk revenue
    if not milk_df.empty:
        milk_df['date'] = pd.to_datetime(milk_df['date'])
        last_30 = milk_df[milk_df['date'] >= datetime.now() - timedelta(days=30)]
        milk_30_revenue = last_30['total_revenue'].sum() if not last_30.empty else 0
        with col2:
            st.metric("Milk Revenue (Last 30 Days)", f"₹{milk_30_revenue:,.2f}")
    else:
        with col2:
            st.metric("Milk Revenue (Last 30 Days)", "No data")

    # Total revenue
    total = 0
    if not coconut_df.empty:
        total += coconut_df['revenue'].sum()
    if not milk_df.empty:
        total += milk_df['total_revenue'].sum()
    with col3:
        st.metric("Total Farm Revenue", f"₹{total:,.2f}")

    # Recent milk trend
    if not milk_df.empty and len(milk_df) > 1:
        st.markdown("---")
        st.subheader("Recent Milk Revenue Trend")
        recent = milk_df.sort_values('date').tail(30)
        fig = px.line(recent, x='date', y='total_revenue',
                      title="Daily Milk Revenue (Last 30 Records)",
                      labels={'total_revenue': 'Revenue (₹)', 'date': 'Date'})
        fig.update_traces(line_color='#2e7d32')
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# MILK MODULE
# ============================================================
with tab_milk:
    milk_tab1, milk_tab2, milk_tab3, milk_tab4 = st.tabs([
        "Upload Bill", "View Records", "Analytics", "Delete Records"
    ])

    # --- Upload Bill ---
    with milk_tab1:
        st.subheader("Upload Milk Bill")
        st.caption("Upload the dairy bill image. The system extracts all daily records automatically.")

        uploaded_file = st.file_uploader("Choose bill image", type=["jpg", "jpeg", "png"], key="milk_upload")

        if uploaded_file:
            img = Image.open(uploaded_file).rotate(90, expand=True)
            st.image(img, caption="Uploaded bill", width=600)

            # Month/Year selector for date context
            col1, col2 = st.columns(2)
            with col1:
                bill_month = st.selectbox("Bill Month", range(1, 13),
                                          index=datetime.now().month - 1,
                                          format_func=lambda x: datetime(2000, x, 1).strftime('%B'))
            with col2:
                bill_year = st.number_input("Bill Year", min_value=2020,
                                            max_value=2030, value=datetime.now().year)

            if st.button("Extract & Save", type="primary"):
                with st.spinner("Extracting data from bill..."):
                    response = extract_bill_data(img)

                data, error = parse_vlm_response(response)

                if error:
                    st.error(f"Extraction failed: {error}")
                    with st.expander("Raw response"):
                        st.json(response)
                else:
                    # Build full dates
                    records = []
                    for row in data:
                        try:
                            full_date = datetime(bill_year, bill_month, int(row['date']))
                            morning_yield = float(row['morning_yield'])
                            morning_rate  = float(row['morning_price'])
                            evening_yield = float(row['evening_yield'])
                            evening_rate  = float(row['evening_price'])

                            morning_rev, evening_rev, total_rev = calculate_milk_revenues(
                                morning_yield, morning_rate, evening_yield, evening_rate
                            )

                            records.append({
                                "date": full_date.strftime('%Y-%m-%d'),
                                "morning_yield": morning_yield,
                                "morning_rate": morning_rate,
                                "morning_revenue": round(morning_rev, 2),
                                "evening_yield": evening_yield,
                                "evening_rate": evening_rate,
                                "evening_revenue": round(evening_rev, 2),
                                "total_revenue": round(total_rev, 2)
                            })
                        except Exception as e:
                            st.warning(f"Skipping row {row}: {e}")

                    if records:
                        new_df = pd.DataFrame(records)

                        # Show extracted data for review
                        st.subheader("Extracted Data — Review before saving")
                        st.dataframe(new_df)

                        # Load existing and merge — duplicates overwrite
                        existing_df = load_data(MILK_CSV, MILK_COLUMNS)
                        if not existing_df.empty:
                            existing_df['date'] = pd.to_datetime(existing_df['date']).dt.strftime('%Y-%m-%d')
                            combined = pd.concat([existing_df, new_df])
                            combined = combined.drop_duplicates(subset='date', keep='last')
                        else:
                            combined = new_df

                        combined = combined.sort_values('date').reset_index(drop=True)
                        save_data(MILK_CSV, combined)
                        st.success(f"Saved {len(records)} records successfully.")

    # --- View Records ---
    with milk_tab2:
        st.subheader("All Milk Records")
        milk_df = load_data(MILK_CSV, MILK_COLUMNS)

        if milk_df.empty:
            st.info("No records yet. Upload a bill to get started.")
        else:
            milk_df['date'] = pd.to_datetime(milk_df['date'])
            milk_df = milk_df.sort_values('date', ascending=False).reset_index(drop=True)
            st.dataframe(milk_df, use_container_width=True)

            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(milk_df))
            with col2:
                st.metric("Total Yield (Morning)", f"{milk_df['morning_yield'].sum():.1f} L")
            with col3:
                st.metric("Total Revenue", f"₹{milk_df['total_revenue'].sum():,.2f}")

    # --- Analytics ---
    with milk_tab3:
        st.subheader("Milk Analytics")
        milk_df = load_data(MILK_CSV, MILK_COLUMNS)

        if milk_df.empty:
            st.info("No records yet.")
        else:
            milk_df['date'] = pd.to_datetime(milk_df['date'])
            milk_df = milk_df.sort_values('date')

            filter_opt = st.selectbox("Filter", ["All", "Last 7 Days", "Last 30 Days"])
            if filter_opt == "Last 7 Days":
                milk_df = milk_df[milk_df['date'] >= datetime.now() - timedelta(days=7)]
            elif filter_opt == "Last 30 Days":
                milk_df = milk_df[milk_df['date'] >= datetime.now() - timedelta(days=30)]

            # Revenue line chart
            fig1 = px.line(milk_df, x='date', y='total_revenue',
                           title="Daily Revenue",
                           labels={'total_revenue': 'Revenue (₹)', 'date': 'Date'})
            fig1.update_traces(line_color='#2e7d32')
            st.plotly_chart(fig1, use_container_width=True)

            # Morning vs Evening yield
            fig2 = px.line(milk_df, x='date', y=['morning_yield', 'evening_yield'],
                           title="Morning vs Evening Yield",
                           labels={'value': 'Yield (L)', 'date': 'Date', 'variable': 'Session'})
            fig2.update_traces(selector=dict(name='morning_yield'), line_color='#1565c0')
            fig2.update_traces(selector=dict(name='evening_yield'), line_color='#e65100')
            st.plotly_chart(fig2, use_container_width=True)

    # --- Delete Records ---
    with milk_tab4:
        st.subheader("Delete Milk Records")
        milk_df = load_data(MILK_CSV, MILK_COLUMNS)

        if milk_df.empty:
            st.info("No records to delete.")
        else:
            milk_df['date'] = pd.to_datetime(milk_df['date'])
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("From Date", key="milk_del_from")
            with col2:
                to_date = st.date_input("To Date", key="milk_del_to")

            to_delete = milk_df[
                (milk_df['date'] >= pd.Timestamp(from_date)) &
                (milk_df['date'] <= pd.Timestamp(to_date))
            ]

            if not to_delete.empty:
                st.warning(f"{len(to_delete)} records will be deleted.")
                st.dataframe(to_delete)

                if st.button("Confirm Delete", type="primary", key="milk_delete_btn"):
                    remaining = milk_df[
                        ~((milk_df['date'] >= pd.Timestamp(from_date)) &
                          (milk_df['date'] <= pd.Timestamp(to_date)))
                    ]
                    save_data(MILK_CSV, remaining)
                    st.success("Records deleted.")
                    st.rerun()
            else:
                st.info("No records found in selected range.")

# ============================================================
# COCONUT MODULE
# ============================================================
with tab_coconut:
    coconut_tab1, coconut_tab2, coconut_tab3 = st.tabs([
        "Add Harvest", "View Records", "Analytics"
    ])

    # --- Add Harvest ---
    with coconut_tab1:
        st.subheader("Add Coconut Harvest")

        with st.form("coconut_form"):
            col1, col2 = st.columns(2)
            with col1:
                harvest_date = st.date_input("Harvest Date")
                yield_kg = st.number_input("Yield (KG)", min_value=0.0, step=0.5)
            with col2:
                yield_count = st.number_input("Yield Count (nuts)", min_value=0, step=1)
                rate_per_ton = st.number_input("Rate per Ton (₹)", min_value=0.0, step=100.0)

            submitted = st.form_submit_button("Save Harvest", type="primary")

            if submitted:
                if yield_kg <= 0 or rate_per_ton <= 0:
                    st.error("Yield and rate must be greater than 0.")
                else:
                    revenue = calculate_coconut_revenue(yield_kg, rate_per_ton)

                    coconut_df = load_data(COCONUT_CSV, COCONUT_COLUMNS)
                    new_row = pd.DataFrame([{
                        "harvest_date": harvest_date.strftime('%Y-%m-%d'),
                        "yield_kg": yield_kg,
                        "yield_count": yield_count,
                        "rate_per_ton": rate_per_ton,
                        "revenue": round(revenue, 2)
                    }])

                    combined = pd.concat([coconut_df, new_row])
                    combined['harvest_date'] = pd.to_datetime(combined['harvest_date'])
                    combined = combined.drop_duplicates(subset='harvest_date', keep='last')
                    combined = combined.sort_values('harvest_date').reset_index(drop=True)
                    save_data(COCONUT_CSV, combined)

                    st.success(f"Harvest saved. Revenue: ₹{revenue:,.2f}")

    # --- View Records ---
    with coconut_tab2:
        st.subheader("All Coconut Harvests")
        coconut_df = load_data(COCONUT_CSV, COCONUT_COLUMNS)

        if coconut_df.empty:
            st.info("No harvests recorded yet.")
        else:
            coconut_df['harvest_date'] = pd.to_datetime(coconut_df['harvest_date'])
            coconut_df = coconut_df.sort_values('harvest_date', ascending=False).reset_index(drop=True)
            st.dataframe(coconut_df, use_container_width=True)

            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Harvests", len(coconut_df))
            with col2:
                st.metric("Total Yield", f"{coconut_df['yield_kg'].sum():,.1f} KG")
            with col3:
                st.metric("Total Revenue", f"₹{coconut_df['revenue'].sum():,.2f}")

    # --- Analytics ---
    with coconut_tab3:
        st.subheader("Coconut Analytics")
        coconut_df = load_data(COCONUT_CSV, COCONUT_COLUMNS)

        if coconut_df.empty:
            st.info("No data yet.")
        else:
            coconut_df['harvest_date'] = pd.to_datetime(coconut_df['harvest_date'])
            coconut_df = coconut_df.sort_values('harvest_date')

            # Revenue trend
            fig1 = px.bar(coconut_df, x='harvest_date', y='revenue',
                          title="Revenue per Harvest",
                          labels={'revenue': 'Revenue (₹)', 'harvest_date': 'Date'})
            fig1.update_traces(marker_color='#2e7d32')
            st.plotly_chart(fig1, use_container_width=True)

            # Yield trend
            fig2 = px.line(coconut_df, x='harvest_date', y='yield_kg',
                           title="Yield per Harvest (KG)",
                           labels={'yield_kg': 'Yield (KG)', 'harvest_date': 'Date'})
            fig2.update_traces(line_color='#558b2f')
            st.plotly_chart(fig2, use_container_width=True)

            # Latest KPI cards
            st.markdown("---")
            st.subheader("Latest Harvest")
            latest = coconut_df.iloc[-1]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Date", latest['harvest_date'].strftime('%d %b %Y'))
            with col2:
                st.metric("Yield", f"{latest['yield_kg']:,.1f} KG")
            with col3:
                st.metric("Rate", f"₹{latest['rate_per_ton']:,.0f}/ton")
            with col4:
                st.metric("Revenue", f"₹{latest['revenue']:,.2f}")
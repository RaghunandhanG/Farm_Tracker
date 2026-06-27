import streamlit as st
import requests
import base64
import json
import os
import pandas as pd
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings()
load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

st.set_page_config(page_title="Milk Bill Income Tracker", layout="wide")
st.title("Milk Bill Income Tracker")


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
"""

    payload = {
        "model": "meta/llama-3.2-90b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "max_tokens": 1024,
        "temperature": 0.1,
        "top_p": 1.00,
        "frequency_penalty": 0.00,
        "presence_penalty": 0.00,
        "stream": False
    }

    response = requests.post(INVOKE_URL, headers=headers, json=payload, verify=False)
    return response.json()


def parse_response(response):
    try:
        content = response['choices'][0]['message']['content']

        # Clean markdown if present
        content_clean = content.strip()
        if content_clean.startswith("```"):
            lines = content_clean.split('\n')
            content_clean = '\n'.join(lines[1:-1])

        data = json.loads(content_clean)
        return data, None

    except Exception as e:
        return None, str(e)


# --- UI ---
uploaded_file = st.file_uploader("Upload milk bill image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file).rotate(90, expand=True)

    st.subheader("Uploaded Bill")
    st.image(img, caption="Rotated bill image")

    st.markdown("---")

    if st.button("Extract Data"):
        with st.spinner("Sending to Llama 3.2 Vision..."):
            response = extract_bill_data(img)

        data, error = parse_response(response)

        if error:
            st.error(f"Failed to parse response: {error}")
            with st.expander("Raw response"):
                st.json(response)
        else:
            df = pd.DataFrame(data)

            # Sort by date
            df = df.sort_values('date').reset_index(drop=True)

            st.subheader("Extracted Data")
            st.dataframe(df)

            # Summary stats
            st.markdown("---")
            st.subheader("Summary")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Morning Yield", f"{df['morning_yield'].sum():.1f} L")
                st.metric("Total Evening Yield", f"{df['evening_yield'].sum():.1f} L")

            with col2:
                st.metric("Avg Morning Price", f"₹{df['morning_price'].mean():.2f}")
                st.metric("Avg Evening Price", f"₹{df['evening_price'].mean():.2f}")

            with col3:
                morning_income = (df['morning_yield'] * df['morning_price']).sum()
                evening_income = (df['evening_yield'] * df['evening_price']).sum()
                st.metric("Morning Income", f"₹{morning_income:.2f}")
                st.metric("Evening Income", f"₹{evening_income:.2f}")
                st.metric("Total Income", f"₹{morning_income + evening_income:.2f}")

            st.markdown("---")

            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="milk_bill_extracted.csv",
                mime="text/csv"
            )
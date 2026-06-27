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
IMAGE_PATH = r"C:\Users\raghu\Downloads\milk_bill.jpeg"
INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

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
    print("Status code:", response.status_code)
    print("Raw response text:", response.text[:300])
    return response.json()

# Load and rotate image
print("Loading image...")
img = Image.open(IMAGE_PATH).rotate(90, expand=True)

print("Sending request to Llama 3.2 Vision...")
response = extract_bill_data(img)

try:
    content = response['choices'][0]['message']['content']
    print("\nModel output:")
    print(content)

    # Clean markdown if present
    content_clean = content.strip()
    if content_clean.startswith("```"):
        lines = content_clean.split('\n')
        content_clean = '\n'.join(lines[1:-1])

    data = json.loads(content_clean)
    print("\nParsed data:")
    for row in data:
        print(row)

    df = pd.DataFrame(data)
    print("\nDataFrame:")
    print(df)
    df.to_csv("vlm_extracted.csv", index=False)
    print("\nSaved to vlm_extracted.csv")

except Exception as e:
    print(f"\nError: {e}")
    print("Full response:", json.dumps(response, indent=2))
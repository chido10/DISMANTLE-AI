import streamlit as st
import requests
from streamlit.components.v1 import html
import boto3
import random
import string
import json
from typing import Dict, Any
from urllib.parse import urlparse
import pandas as pd
import base64
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --------------------------------------------------------------------------------
# Configuration and Settings
# --------------------------------------------------------------------------------
def get_aws_config():
    """Fetch AWS configuration from secrets or environment variables."""
    try:
        aws_region = st.secrets["aws_credentials"]["AWS_REGION"]
        aws_access_key_id = st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID"]
        aws_secret_access_key = st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY"]
        agent_alias_id = st.secrets["aws"]["AWS_AGENT_ALIAS_ID"]
        agent_id = st.secrets["aws"]["AWS_AGENT_ID"]
        s3_bucket = st.secrets["aws"]["AWS_S3_BUCKET"]
    except Exception:
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        agent_alias_id = os.getenv("AWS_AGENT_ALIAS_ID", "")
        agent_id = os.getenv("AWS_AGENT_ID", "")
        s3_bucket = os.getenv("AWS_S3_BUCKET", "brandbyme1")

    return {
        "region": aws_region,
        "access_key": aws_access_key_id,
        "secret_key": aws_secret_access_key,
        "agent_alias_id": agent_alias_id,
        "agent_id": agent_id,
        "s3_bucket": s3_bucket,
    }

AWS_CONFIG = get_aws_config()

# Get the absolute path to the assets directory
ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH = str(ASSETS_DIR / "logo.png")

def preprocess_url(url: str) -> str:
    """Preprocess URL to ensure proper format"""
    url = url.strip()
    if not url:
        return url

    # Remove any trailing slashes
    while url.endswith("/"):
        url = url[:-1]

    # Check if the URL starts with a protocol
    if not url.startswith(("http://", "https://")):
        # If it starts with 'www', add https://
        if url.startswith("www."):
            url = "https://" + url
        else:
            # Add both https:// and www. if neither is present
            if not any(c in url for c in ["/", " ", "\n", "\t"]):  # Basic URL validation
                url = "https://www." + url

    return url

def load_local_image(image_path):
    """Load and encode a local image file"""
    try:
        # Convert string path to Path object
        image_path = Path(image_path)

        # Check if file exists
        if not image_path.exists():
            st.warning(f"Logo file not found at: {image_path}")
            return None

        # Read and encode the image
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
        return None

# App configuration
st.set_page_config(
    page_title="DISMANTLE AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://www.dismantleai.com/help",
        "Report a bug": "https://www.dismantleai.com/bug",
        "About": "# DISMANTLE AI\nAn anti-racism content audit tool.",
    },
)

# Custom CSS
st.markdown(
    """
    <style>
    .stApp {
        max-width: 100%;
        padding: 1rem;
    }
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

def call_bedrock_agent(prompt: str) -> dict:
    """Enhanced Bedrock Agent caller with JSON response parsing"""
    try:
        # Use AWS credentials
        bedrock_agent_runtime = boto3.client(
            service_name="bedrock-agent-runtime",
            region_name=AWS_CONFIG["region"],
            aws_access_key_id=AWS_CONFIG["access_key"],
            aws_secret_access_key=AWS_CONFIG["secret_key"],
        )

        response = bedrock_agent_runtime.invoke_agent(
            agentAliasId=AWS_CONFIG["agent_alias_id"],
            agentId=AWS_CONFIG["agent_id"],
            sessionId=str(random.randint(1, 1000000)),
            inputText=prompt,
            enableTrace=True,
        )

        # Parse the response
        full_response = ""
        for event in response["completion"]:
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    full_response += chunk["bytes"].decode("utf-8")

        return {"success": True, "message": full_response, "data": None}
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}

def get_s3_analysis_history():
    """Fetch analysis history from S3"""
    try:
        s3 = boto3.client(
            "s3",
            region_name=AWS_CONFIG["region"],
            aws_access_key_id=AWS_CONFIG["access_key"],
            aws_secret_access_key=AWS_CONFIG["secret_key"],
        )
        response = s3.list_objects_v2(Bucket=AWS_CONFIG["s3_bucket"], Prefix="scraped-data/")
        if "Contents" in response:
            return sorted(response["Contents"], key=lambda x: x["LastModified"], reverse=True)
    except Exception as e:
        st.error(f"Failed to fetch analysis history: {str(e)}")
    return []

def main():
    st.sidebar.image(load_local_image(LOGO_PATH), use_column_width=True)
    st.sidebar.title("DISMANTLE AI")

    st.header("Welcome to DISMANTLE AI")
    st.write("Analyze websites and detect anti-racism indicators.")
    st.write("---")

if __name__ == "__main__":
    main()

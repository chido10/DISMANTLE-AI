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
REGION = os.getenv('AWS_REGION', 'us-east-1')
AGENT_ALIAS_ID = os.getenv('AWS_AGENT_ALIAS_ID', '')
AGENT_ID = os.getenv('AWS_AGENT_ID', '')
S3_BUCKET = os.getenv('AWS_S3_BUCKET', 'brandbyme1')

# Get the absolute path to the assets directory
ASSETS_DIR = Path(__file__).parent / 'assets'
LOGO_PATH = str(ASSETS_DIR / 'logo.png')

def preprocess_url(url: str) -> str:
    """Preprocess URL to ensure proper format"""
    url = url.strip()
    if not url:
        return url
        
    # Remove any trailing slashes
    while url.endswith('/'):
        url = url[:-1]
        
    # Check if the URL starts with a protocol
    if not url.startswith(('http://', 'https://')):
        # If it starts with 'www', add https://
        if url.startswith('www.'):
            url = 'https://' + url
        else:
            # Add both https:// and www. if neither is present
            if not any(c in url for c in ['/', ' ', '\n', '\t']):  # Basic URL validation
                url = 'https://www.' + url
    
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
        'Get Help': 'https://www.dismantleai.com/help',
        'Report a bug': "https://www.dismantleai.com/bug",
        'About': "# DISMANTLE AI\nAn anti-racism content audit tool."
    }
)

# Custom CSS
st.markdown("""
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
    .chat-message {
        padding: 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e6f3ff;
    }
    .assistant-message {
        background-color: #f0f0f0;
    }
    .predefined-question {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
    }
    .predefined-question:hover {
        background-color: #f8f9fa;
        border-color: #FF4B4B;
        cursor: pointer;
        transform: translateY(-2px);
    }
    .question-section {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

def call_bedrock_agent(prompt: str) -> dict:
    """Enhanced Bedrock Agent caller with JSON response parsing"""
    try:
        # Get AWS credentials from environment variables or Streamlit secrets
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID"]
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY"]
        
        bedrock_agent_runtime = boto3.client(
            service_name="bedrock-agent-runtime",
            region_name=REGION,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        response = bedrock_agent_runtime.invoke_agent(
            agentAliasId=AGENT_ALIAS_ID,
            agentId=AGENT_ID,
            sessionId=str(random.randint(1, 1000000)),
            inputText=prompt,
            enableTrace=True
        )
        
        # Parse the response
        full_response = ""
        for event in response["completion"]:
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    full_response += chunk["bytes"].decode("utf-8")
        
        # Try to parse JSON from the response
        try:
            response_data = json.loads(full_response)
            if isinstance(response_data, dict) and "response" in response_data:
                function_response = response_data["response"]["functionResponse"]
                if "responseBody" in function_response:
                    if "TEXT" in function_response["responseBody"]:
                        text_response = function_response["responseBody"]["TEXT"]["body"]
                        return {
                            "success": True,
                            "message": text_response,
                            "data": None
                        }
        except json.JSONDecodeError:
            pass
        
        return {
            "success": True,
            "message": full_response,
            "data": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "data": None
        }

def clear_chat_history():
    """Clear the chat history from session state"""
    if "messages" in st.session_state:
        st.session_state.messages = []
    return True

def initialize_chat_history():
    if "messages" not in st.session_state:
        st.session_state.messages = []

def display_media_section(media_items):
    """Display media items in a grid"""
    if not media_items:
        st.write("No media found")
        return
        
    st.subheader(f"📸 Media ({len(media_items)} items)")
    
    for i in range(0, len(media_items), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(media_items):
                with cols[j]:
                    try:
                        st.image(
                            media_items[i + j]['url'],
                            caption=media_items[i + j]['alt'] if media_items[i + j]['alt'] else f"Image {i + j + 1}",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.warning(f"Unable to load image: {media_items[i + j]['url']}")

def display_structured_content(content):
    """Display structured content with proper formatting"""
    for item in content:
        if item['type'] == 'header':
            level = int(item['level'][1])
            header_text = '#' * level + ' ' + item['text']
            st.markdown(header_text)
        elif item['type'] == 'paragraph':
            st.write(item['text'])
        elif item['type'] == 'list':
            for list_item in item['items']:
                st.markdown(f"- {list_item}")

def get_s3_analysis_history():
    """Fetch analysis history from S3"""
    try:
        # Get AWS credentials from environment variables or Streamlit secrets
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID"]
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY"]
        
        s3 = boto3.client('s3', 
                         region_name=REGION,
                         aws_access_key_id=aws_access_key,
                         aws_secret_access_key=aws_secret_key)
                         
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix="scraped-data/")
        if 'Contents' in response:
            return sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    except Exception as e:
        st.error(f"Failed to fetch analysis history: {str(e)}")
    return []

def display_analysis_results(data: Dict[str, Any]):
    """Enhanced display of analysis results"""
    st.header("📊 Analysis Results")
    
    # Basic Information with enhanced metrics
    with st.expander("📌 Basic Information", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Images", data['metadata']['image_count'], 
                     delta="found" if data['metadata']['image_count'] > 0 else "none")
        with col2:
            st.metric("Paragraphs", data['metadata']['paragraph_count'])
        with col3:
            st.metric("Headers", len(data['metadata']['headers']))
        with col4:
            st.metric("Analysis Date", data.get('timestamp', 'N/A')[:10])
            
        st.markdown(f"""
        **URL:** [{data['url']}]({data['url']})  
        **Title:** {data['title']}
        """)

    # Media Section with download option
    with st.expander("📸 Media Gallery", expanded=True):
        if data.get('media'):
            col1, col2 = st.columns([3, 1])
            with col1:
                display_media_section(data['media'])
            with col2:
                st.download_button(
                    label="Download Media List",
                    data=json.dumps([m['url'] for m in data['media']], indent=2),
                    file_name="media_urls.json",
                    mime="application/json"
                )

    # Content Structure
    with st.expander("📝 Content Structure", expanded=True):
        display_structured_content(data.get('structured_content', []))

def handle_predefined_question(question: str):
    """Handle predefined question clicks"""
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    
    with st.chat_message("assistant"):
        response = call_bedrock_agent(question)
        if response["success"]:
            st.markdown(response["message"])
            st.session_state.messages.append({"role": "assistant", "content": response["message"]})
        else:
            st.error("Failed to get response")

def main():
    initialize_chat_history()
    
    # Add a sidebar with logo
    with st.sidebar:
        logo_image = load_local_image(LOGO_PATH)
        if logo_image:
            st.markdown(
                f'<img src="{logo_image}" style="width: 100%; margin-bottom: 20px;">',
                unsafe_allow_html=True
            )
        else:
            # Fallback if logo cannot be loaded
            st.title("DISMANTLE AI")
            
        st.markdown("---")
        st.caption("Version 1.0.0")

    # Main content
    tabs = st.tabs(["🔍 Analysis", "📚 History", "💬 Chat", "ℹ️ About"])

    with tabs[0]:
        st.header("Website Analysis")
        raw_url = st.text_input(
            "Enter website URL:",
            placeholder="example.com or www.example.com"
        )
        
        # Preprocess URL when input is provided
        url = preprocess_url(raw_url) if raw_url else ""
        
        # Show the processed URL if it's different from input
        if url and url != raw_url:
            st.markdown(
                f'<p style="color: #666; font-size: 0.9em; font-style: italic;">'
                f'Analyzing: {url}</p>',
                unsafe_allow_html=True
            )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            analyze_button = st.button("🔍 Analyze Website", disabled=not url, use_container_width=True)
        with col2:
            if st.button("📋 Clear", use_container_width=True):
                st.rerun()

        if analyze_button and url:
            with st.spinner("🔍 Analyzing website..."):
                response = call_bedrock_agent(f"Analyze this website: {url}")
                
                if response["success"]:
                    st.success("Analysis completed!")
                    
                    # Extract the presigned URL from the response
                    message_lines = response["message"].split('\n')
                    presigned_url = None
                    for line in message_lines:
                        if line.startswith("Access full analysis at:"):
                            presigned_url = line.split(": ")[1].strip()
                    
                    if presigned_url:
                        try:
                            analysis_data = requests.get(presigned_url).json()
                            display_analysis_results(analysis_data)
                        except Exception as e:
                            st.error(f"Error loading analysis data: {str(e)}")
                    
                    st.write(response["message"])
                else:
                    st.error(f"Analysis failed: {response['message']}")

    with tabs[1]:
        st.header("Analysis History")
        col1, col2 = st.columns([3, 1])
        with col1:
            history = get_s3_analysis_history()
        with col2:
            if st.button("🔄 Refresh History", use_container_width=True):
                st.rerun()
        
        if history:
            selected_analysis = st.selectbox(
                "Select previous analysis:",
                options=[item['Key'] for item in history],
                format_func=lambda x: x.split('/')[-1]
            )
            
            if selected_analysis:
                try:
                    # Get AWS credentials
                    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID') or st.secrets["aws_credentials"]["AWS_ACCESS_KEY_ID"]
                    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') or st.secrets["aws_credentials"]["AWS_SECRET_ACCESS_KEY"]
                    
                    s3 = boto3.client('s3', 
                                    region_name=REGION,
                                    aws_access_key_id=aws_access_key,
                                    aws_secret_access_key=aws_secret_key)
                    
                    obj = s3.get_object(Bucket=S3_BUCKET, Key=selected_analysis)
                    analysis_data = json.loads(obj['Body'].read().decode('utf-8'))
                    display_analysis_results(analysis_data)
                except Exception as e:
                    st.error(f"Error loading analysis: {str(e)}")
        else:
            st.info("No previous analyses found")

    with tabs[2]:
        st.header("Chat with DISMANTLE AI")
        
        # Add Clear Chat button
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                clear_chat_history()
                st.rerun()
        
        # Predefined Questions Section
        st.markdown("### ❓ Common Questions")
        st.markdown('<div class="question-section">', unsafe_allow_html=True)
        
        # Create three columns for better layout
        q_col1, q_col2, q_col3 = st.columns(3)
        
        with q_col1:
            if st.button("👋 What are you?", use_container_width=True):
                handle_predefined_question("Can you explain what DISMANTLE AI is and how it helps with anti-racism auditing?")
                
            if st.button("🔍 Key Anti-Racism Indicators", use_container_width=True):
                handle_predefined_question("What are the key anti-racism indicators and keywords that you look for when analyzing content?")
                
            if st.button("📊 Bias Measurement Method", use_container_width=True):
                handle_predefined_question("How do you measure and quantify racial bias in content?")
        
        with q_col2:
            if st.button("🔴 High Risk Factors", use_container_width=True):
                handle_predefined_question("What factors or patterns would classify content as High Risk (Red) in terms of racial bias?")
                
            if st.button("✅ Low Risk Characteristics", use_container_width=True):
                handle_predefined_question("What characteristics indicate content is Low Risk (Green) in terms of racial inclusivity?")
                
            if st.button("🎯 Audit Methodology", use_container_width=True):
                handle_predefined_question("Can you explain your methodology for conducting anti-racism audits?")

        with q_col3:
            if st.button("❓ Understanding Results", use_container_width=True):
                handle_predefined_question("How should I interpret the analysis results and risk ratings?")
                
            if st.button("📈 Inclusive Best Practices", use_container_width=True):
                handle_predefined_question("What are the best practices for creating inclusive, anti-racist content?")
                
            if st.button("🔄 Improvement Steps", use_container_width=True):
                handle_predefined_question("What steps can be taken to improve content that has been flagged as potentially problematic?")

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        
        # Display chat history
        for message in st.session_state.get("messages", []):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Enhanced chat input
        if prompt := st.chat_input("Ask anything about anti-racism auditing..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                response = call_bedrock_agent(prompt)
                if response["success"]:
                    st.markdown(response["message"])
                    st.session_state.messages.append({"role": "assistant", "content": response["message"]})
                else:
                    st.error("Failed to get response")

    with tabs[3]:
        st.header("About DISMANTLE AI")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### What is DISMANTLE AI?
            DISMANTLE AI is an advanced tool for analyzing web content for potential bias 
            and racist elements. It combines web scraping, AI analysis, and interactive 
            chat capabilities to provide comprehensive insights.
            
            ### Key Features:
            - 🔍 Website Content Analysis
            - 📊 Comprehensive Reports
            - 💬 Interactive Chat Assistant
            - 📚 Analysis History
            """)
        
        with col2:
            st.markdown("""
            ### How to Use:
            1. Enter a website URL
            2. Click Analyze
            3. Review the results
            4. Chat with AI for insights
            
            ### Need Help?
            Contact us at support@dismantleai.com
            """)

if __name__ == "__main__":
    main()

import os

# AWS Configuration
REGION = os.getenv('AWS_REGION', 'us-east-1')
AGENT_ALIAS_ID = os.getenv('AWS_AGENT_ALIAS_ID', '')
AGENT_ID = os.getenv('AWS_AGENT_ID', '')
S3_BUCKET = os.getenv('AWS_S3_BUCKET', '')

# Other configurations
LOGO_PATH = "assets/logo.png"
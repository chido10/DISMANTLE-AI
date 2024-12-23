# How to Test Your Bedrock Agent

Your agent (ID: B4EAA9HCZJ) is already configured in the debugging interface. To test your agent:

1. Make sure you have the required Python packages installed (`streamlit`, `boto3`, `matplotlib`, `Pillow`)
2. Run the debug interface by executing:
   ```
   streamlit run debug_bedrock.py
   ```
3. Once the interface opens in your browser:
   - Enter your test query in the text input field
   - Click the "Send Query" button to test the agent
   - The response will appear below, including any text, images, or files
   - Each interaction will maintain the same session ID for consistent conversation

The interface supports:
- Text responses
- Image display (PNG format)
- File downloads
- Conversation history tracking

Test different types of queries to ensure your agent responds as expected.
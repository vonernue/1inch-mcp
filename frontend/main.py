import gradio as gr
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

# Claude API settings
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-3-7-sonnet-20250219"
HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Define system prompt in code
SYSTEM_PROMPT = "You are a helpful, harmless, and honest AI assistant. Answer questions accurately and be concise in your responses."

# Function to call Claude API
def call_claude_api(messages):
    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": messages,
        "system": SYSTEM_PROMPT
    }
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except Exception as e:
        return f"Error: {str(e)}"

# Chat function for Gradio
def chat_bot(message, history):
    # Construct messages from history
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        if assistant:  # Skip if the assistant hasn't responded yet
            messages.append({"role": "assistant", "content": assistant})
    
    # Add the current message
    messages.append({"role": "user", "content": message})
    
    # Call Claude API
    response = call_claude_api(messages)
    return response

# Create the Gradio interface
with gr.Blocks(title="Claude Chat Interface") as app:
    with gr.Row():
        gr.Markdown("## Chat with Claude")
    
    chatbot = gr.ChatInterface(
        fn=chat_bot,
        title="Claude Assistant"
    )

app.launch()

import gradio as gr
import os
import requests
import json
import anthropic
import asyncio
from eth_account import Account
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Load environment variables from .env file
load_dotenv()

client = anthropic.Anthropic()

# Claude API settings
MODEL = "claude-3-7-sonnet-20250219"

# Define system prompt in code
SYSTEM_PROMPT = "You are a crypto wallet assistant that can help user to check their portfolios, swap tokens."

server_params = StdioServerParameters(
    command="node",  # Executable
    args=["../mcp/build/index.js"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

# Chat function for Gradio
async def chat_bot(message, history):
    # Construct messages from history
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        if assistant:  # Skip if the assistant hasn't responded yet
            messages.append({"role": "assistant", "content": assistant})
    
    # Add the current message
    messages.append({"role": "user", "content": message})
    
    response = ""
    async with stdio_client(server_params) as (read, write):
        # Call Claude API
        async with ClientSession(
            read, write
        ) as session:
            await session.initialize()
            tools = await session.list_tools()
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema
            } for tool in tools.tools]

            response = client.messages.create(
                system=SYSTEM_PROMPT,
                model=MODEL,
                max_tokens=1024,
                messages=messages,
                tools=available_tools
            )

            # Process response and handle tool calls
            final_text = []

            assistant_message_content = []
            for content in response.content:
                if content.type == 'text':
                    final_text.append(content.text)
                    assistant_message_content.append(content)
                    yield "\n".join(final_text)
                elif content.type == 'tool_use':
                    tool_name = content.name
                    tool_args = content.input

                    # Execute tool call
                    result = await session.call_tool(tool_name, tool_args)
                    final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                    assistant_message_content.append(content)
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message_content
                    })
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content
                            }
                        ]
                    })

                    # Get next response from Claude
                    response = client.messages.create(
                        model=MODEL,
                        max_tokens=1024,
                        messages=messages,
                        tools=available_tools
                    )

                    final_text.append(response.content[0].text)
                    yield "\n".join(final_text)

            yield "\n".join(final_text)

def save_settings(private_key):
    try:
        acct = Account.from_key(private_key)
        public_key = acct.address
        return private_key, public_key
    except Exception as e:
        return private_key, f"Error: {str(e)}"
    
# Create the Gradio interface
with gr.Blocks(title="WalletPilot") as app:
    privateKeyState = gr.State("")

    with gr.Tabs():
        with gr.Tab("🔧 Settings"):
            gr.Markdown("## App Settings")

            private_key = gr.Textbox(
                label="Wallet Private Key",
                type="password",
                placeholder="Enter your wallet private key"
            )
            public_key = gr.Textbox(
                label="Wallet Public Key",
                type="text",
                interactive=False,
            )

            save_btn = gr.Button("Save Settings")
            settings_output = gr.Textbox(label="Status", interactive=False)

            save_btn.click(
                fn=save_settings,
                inputs=[private_key],
                outputs=[privateKeyState, public_key]
            )
            
            
        with gr.Tab("💬 Chat"):
            with gr.Row():
                gr.Markdown("## Chat")
            
            chatbot = gr.ChatInterface(
                fn=chat_bot,
            )

app.launch()

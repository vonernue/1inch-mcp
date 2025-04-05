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

# Private key confirmation function
def use_pvkey(private_key, operation_name, confirm=None):
    """
    Function to request and handle private key confirmation.
    When called without confirm parameter, it initiates a confirmation request.
    When called with confirm=True/False, it completes the confirmation process.
    
    Returns:
    - message: Status message for display
    - private_key: The private key string if confirmed, None otherwise
    - needs_confirmation: Boolean indicating if confirmation is needed
    - confirmation_ui: UI update for the confirmation row
    """
    if confirm is None:
        # Initiate confirmation request
        return f"Waiting for confirmation to perform: {operation_name}", None, True, gr.update(visible=True)
    elif confirm:
        # Confirmation approved
        return f"Operation '{operation_name}' confirmed", private_key, False, gr.update(visible=False)
    else:
        # Confirmation rejected
        return f"Operation cancelled", None, False, gr.update(visible=False)

# Function to fetch transaction history from 1inch API
def fetch_transaction_history(wallet_address):
    if not wallet_address:
        return "Please enter a wallet address in settings"
    
    try:
        # Using the 1inch explorer API (you may need to adjust the endpoint)
        # The Ethereum mainnet chain ID is 1
        chain_id = 1
        base_url = f"https://api.1inch.dev/tx-history/v1/transactions?chain={chain_id}&address={wallet_address}&limit=5"
        
        # In a production environment, you would need to add an API key
        headers = {
            "Accept": "application/json",
            # "Authorization": "Bearer YOUR_API_KEY" # Uncomment and add your API key
        }
        
        response = requests.get(base_url, headers=headers)
        
        if response.status_code == 200:
            transactions = response.json()
            # Format transactions for display
            transaction_text = "## Recent Transactions\n\n"
            
            if not transactions or len(transactions.get("items", [])) == 0:
                return f"## Recent Transactions\n\nNo transactions found for {wallet_address}"
                
            for tx in transactions.get("items", [])[:5]:
                tx_hash = tx.get("hash", "Unknown")
                tx_time = tx.get("timeStamp", "Unknown")
                tx_status = "Success" if tx.get("success") else "Failed"
                
                # Get the transaction description
                tx_desc = "Unknown transaction"
                if "swapDescription" in tx:
                    swap = tx["swapDescription"]
                    from_token = swap.get("fromToken", {}).get("symbol", "Unknown")
                    to_token = swap.get("toToken", {}).get("symbol", "Unknown")
                    tx_desc = f"Swap {from_token} to {to_token}"
                
                transaction_text += f"- **{tx_desc}** ({tx_status})\n"
                transaction_text += f"  Hash: {tx_hash[:10]}...{tx_hash[-6:]}\n"
                transaction_text += f"  Time: {tx_time}\n\n"
                
            return transaction_text
        else:
            return f"## Transaction History\n\nError fetching transactions: {response.status_code}"
    except Exception as e:
        return f"## Transaction History\n\nError: {str(e)}"

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

def save_settings(private_key, wallet_address=None):
    """
    Save user settings and derive wallet address from private key if not provided
    """
    try:
        # Try to derive the wallet address from private key
        if private_key:
            acct = Account.from_key(private_key)
            derived_address = acct.address
            
            # Use derived address if wallet_address not provided
            if not wallet_address:
                wallet_address = derived_address
                
            # Validate if provided address matches derived address
            elif wallet_address.lower() != derived_address.lower():
                status_msg = "⚠️ Warning: Provided wallet address doesn't match the address derived from private key"
            else:
                status_msg = "✅ Settings saved successfully!"
        else:
            status_msg = "⚠️ No private key provided."
            
        if not wallet_address:
            status_msg = "⚠️ No wallet address available."
    except Exception as e:
        status_msg = f"⚠️ Error processing private key: {str(e)}"
    
    # Fetch transaction history if wallet address is provided
    transaction_history = fetch_transaction_history(wallet_address) if wallet_address else "No wallet address provided"
    return private_key, wallet_address, status_msg, transaction_history

# Example function that requires private key
def sign_transaction(wallet_address, private_key=None, tx_data=None):
    """Example function that would require a private key"""
    if private_key is None:
        # If private key not provided, initiate confirmation
        operation_name = f"Sign transaction from {wallet_address}"
        result = use_pvkey(None, operation_name)
        return result[0], result[1], result[2], result[3], None
    
    # If we have the private key, perform the actual operation
    # In a real implementation, you would use web3 or another library to sign the transaction
    signed_tx = f"Transaction signed with private key for address {wallet_address}"
    return "Transaction signed successfully", None, False, gr.update(visible=False), signed_tx

# Create the Gradio interface
with gr.Blocks(title="WalletPilot", css="""
    .sidebar-box {
        border-radius: 8px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
    }
    .sidebar-box h2 {
        font-size: 1.2em;
        padding: 10px;
        margin: 0;
        background-color: #f0f0f0;
        border-bottom: 1px solid #e0e0e0;
        border-radius: 8px 8px 0 0;
    }
    .confirmation-row {
        display: flex;
        gap: 10px;
        padding: 10px;
    }
    .confirm-btn {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .cancel-btn {
        background-color: #f44336 !important;
        color: white !important;
    }
""") as app:
    privateKeyState = gr.State("")
    walletAddressState = gr.State("")
    pvkey_needs_confirmation = gr.State(False)
    current_operation = gr.State("")
    
    # Function to initiate a private key operation from anywhere in the app
    def request_pvkey_confirmation(operation):
        result = use_pvkey(None, operation)
        return result[0], operation, result[2], result[3]
    
    # Create shared components that will be referenced in multiple places
    tx_history = gr.Markdown("## Transaction History\n\nNo wallet address provided")
    pvkey_operation = gr.Markdown("No operations requiring private key")
    confirmation_row = gr.Row(visible=False, elem_classes=["confirmation-row"])
    
    with gr.Row():
        # Main content
        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.Tab("🔧 Settings"):
                    gr.Markdown("## App Settings")

                    private_key = gr.Textbox(
                        label="Wallet Private Key",
                        type="password",
                        placeholder="Enter your wallet private key"
                    )
                    
                    wallet_address = gr.Textbox(
                        label="Wallet Address",
                        placeholder="Enter your wallet address (0x...)"
                    )
                    
                    save_btn = gr.Button("Save Settings")
                    settings_output = gr.Textbox(label="Status", interactive=False)

                    save_btn.click(
                        fn=save_settings,
                        inputs=[private_key, wallet_address],
                        outputs=[privateKeyState, walletAddressState, settings_output, tx_history]
                    )
                    
                with gr.Tab("💬 Chat"):
                    with gr.Row():
                        gr.Markdown("## Chat")
                    
                    chatbot = gr.ChatInterface(
                        fn=chat_bot,
                        title="Claude Assistant"
                    )
                    
                with gr.Tab("🔄 Transactions"):
                    gr.Markdown("## Create Transaction")
                    
                    tx_data = gr.Textbox(
                        label="Transaction Data",
                        placeholder="Enter transaction data (JSON)"
                    )
                    
                    sign_tx_btn = gr.Button("Sign Transaction")
                    tx_status = gr.Textbox(label="Transaction Status", interactive=False)
                    
                    sign_tx_btn.click(
                        fn=sign_transaction,
                        inputs=[walletAddressState, privateKeyState, tx_data],
                        outputs=[pvkey_operation, current_operation, pvkey_needs_confirmation, confirmation_row, tx_status]
                    )
                    
        # Right sidebar
        with gr.Column(scale=1):
            # Top-right: Private key confirmation
            with gr.Group(elem_classes=["sidebar-box"]):
                pvkey_prompt = gr.Markdown("## Private Key Operations")
                
                with confirmation_row:
                    confirm_btn = gr.Button("Confirm", variant="primary", elem_classes=["confirm-btn"])
                    cancel_btn = gr.Button("Cancel", variant="secondary", elem_classes=["cancel-btn"])
                
                # Connect buttons to the confirmation function
                confirm_btn.click(
                    fn=use_pvkey,
                    inputs=[privateKeyState, current_operation, gr.Checkbox(value=True, visible=False)],
                    outputs=[pvkey_operation, current_operation, pvkey_needs_confirmation, confirmation_row]
                )
                
                cancel_btn.click(
                    fn=use_pvkey,
                    inputs=[privateKeyState, current_operation, gr.Checkbox(value=False, visible=False)],
                    outputs=[pvkey_operation, current_operation, pvkey_needs_confirmation, confirmation_row]
                )
            
            # Bottom-right: Transaction history
            with gr.Group(elem_classes=["sidebar-box"]):
                refresh_tx_btn = gr.Button("Refresh Transactions")
                
                # Connect refresh button
                refresh_tx_btn.click(
                    fn=fetch_transaction_history,
                    inputs=[walletAddressState],
                    outputs=[tx_history]
                )

app.launch()

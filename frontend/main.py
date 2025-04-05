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
from get_data import get_all_wallet_data, is_valid_address  # Import new functions

# Load environment variables from .env file
load_dotenv()

# Check if Anthropic API key is configured
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY environment variable is not set!")
    print("Please add it to your .env file or set it in your environment.")
    print("Chat functionality will not work without an API key.")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Claude API settings
MODEL = "claude-3-7-sonnet-20250219"

# Define system prompt in code
SYSTEM_PROMPT = """You are a helpful crypto wallet assistant. You can help users with:
1. Checking their wallet balances and transaction history
2. Explaining cryptocurrency concepts and token information
3. Providing guidance on secure wallet practices
4. Answering questions about DeFi, NFTs, and blockchain technology

If users ask about performing actions like swapping tokens or signing transactions, explain that you can provide guidance but actual transactions require their private key and should be done through the app interface.

Always be security-conscious and remind users to keep their private keys secure and never share them with anyone.
"""

server_params = StdioServerParameters(
    command="node",  # Executable
    args=["../mcp/build/index.js"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

# Function to fetch wallet token balances
def fetch_wallet_balances(wallet_address):
    """
    Fetches token balances for a wallet address using Etherscan API
    Returns formatted markdown with token balances
    """
    if not wallet_address:
        return "No wallet address provided"
    
    try:
        # You should register for an Etherscan API key for production use
        etherscan_api_key = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")  # Replace with your API key
        
        # First, get ETH balance
        eth_balance_url = f"https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={etherscan_api_key}"
        eth_response = requests.get(eth_balance_url)
        eth_data = eth_response.json()
        
        # Format ETH balance (convert from wei to ETH)
        if eth_data.get("status") == "1":
            eth_balance = float(eth_data.get("result", "0")) / 10**18  # Convert wei to ETH
        else:
            eth_balance = 0
        
        # Get ERC-20 token balances
        token_url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={wallet_address}&startblock=0&endblock=999999999&sort=desc&apikey={etherscan_api_key}"
        token_response = requests.get(token_url)
        token_data = token_response.json()
        
        # Create a dictionary to store unique tokens and their latest balance
        tokens = {}
        
        if token_data.get("status") == "1":
            for tx in token_data.get("result", []):
                token_symbol = tx.get("tokenSymbol")
                token_name = tx.get("tokenName")
                token_decimals = int(tx.get("tokenDecimal", "18"))
                
                # Only process each token once (we just want a list of tokens)
                if token_symbol not in tokens:
                    # Now get the actual balance for this token
                    token_balance_url = f"https://api.etherscan.io/api?module=account&action=tokenbalance&contractaddress={tx.get('contractAddress')}&address={wallet_address}&tag=latest&apikey={etherscan_api_key}"
                    balance_response = requests.get(token_balance_url)
                    balance_data = balance_response.json()
                    
                    if balance_data.get("status") == "1":
                        raw_balance = int(balance_data.get("result", "0"))
                        # Convert based on token decimals
                        balance = raw_balance / (10 ** token_decimals)
                        
                        # Only add tokens with non-zero balance
                        if balance > 0:
                            tokens[token_symbol] = {
                                "name": token_name,
                                "symbol": token_symbol,
                                "balance": balance
                            }
        
        # Format the balances as nice Markdown
        if eth_balance > 0 or tokens:
            balances_text = "## Wallet Balances\n\n"
            balances_text += f"**Address**: {wallet_address[:6]}...{wallet_address[-4:]}\n\n"
            
            # Add ETH balance
            if eth_balance > 0:
                balances_text += f"**ETH**: {eth_balance:.4f}\n\n"
            
            # Add token balances
            for symbol, data in tokens.items():
                balances_text += f"**{symbol}**: {data['balance']:.4f}\n\n"
            
            return balances_text
        else:
            return f"## Wallet Balances\n\n**Address**: {wallet_address[:6]}...{wallet_address[-4:]}\n\nNo tokens found for this address"
            
    except Exception as e:
        return f"Error fetching wallet balances: {str(e)}"

# Function to fetch transaction history from 1inch API (updated)
def fetch_transaction_history(wallet_address):
    if not wallet_address:
        return "Please enter a wallet address in settings"
    
    try:
        # Since 1inch API endpoints might change, we'll use Etherscan for transaction history 
        # which is more reliable for this demo purpose
        etherscan_api_key = os.getenv("ETHERSCAN_API_KEY", "YourApiKeyToken")  # Replace with your API key
        
        # Get normal transactions
        tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&page=1&offset=5&sort=desc&apikey={etherscan_api_key}"
        response = requests.get(tx_url)
        tx_data = response.json()
        
        if tx_data.get("status") == "1":
            transactions = tx_data.get("result", [])
            
            # Format transactions for display
            transaction_text = "## Recent Transactions\n\n"
            
            if not transactions:
                return f"## Recent Transactions\n\nNo transactions found for {wallet_address}"
                
            for tx in transactions[:5]:  # Show last 5 transactions
                tx_hash = tx.get("hash", "Unknown")
                tx_time = tx.get("timeStamp", "Unknown")
                # Convert Unix timestamp to readable format
                if tx_time != "Unknown":
                    from datetime import datetime
                    tx_time = datetime.fromtimestamp(int(tx_time)).strftime('%Y-%m-%d %H:%M:%S')
                
                tx_status = "Success" if tx.get("txreceipt_status") == "1" else "Failed"
                tx_from = tx.get("from", "Unknown")
                tx_to = tx.get("to", "Unknown")
                tx_value = float(tx.get("value", "0")) / 10**18  # Convert wei to ETH
                
                # Determine transaction type
                if tx_from.lower() == wallet_address.lower():
                    tx_type = "Sent"
                    tx_partner = tx_to
                else:
                    tx_type = "Received"
                    tx_partner = tx_from
                
                transaction_text += f"- **{tx_type} {tx_value:.4f} ETH** ({tx_status})\n"
                transaction_text += f"  To/From: {tx_partner[:10]}...{tx_partner[-6:]}\n"
                transaction_text += f"  Hash: {tx_hash[:10]}...{tx_hash[-6:]}\n"
                transaction_text += f"  Time: {tx_time}\n\n"
                
            return transaction_text
        else:
            return f"## Transaction History\n\nError fetching transactions: {tx_data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"## Transaction History\n\nError: {str(e)}"

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
        return f"Waiting for confirmation to perform: {operation_name}", None, True, gr.update(visible=True, elem_classes=["confirmation-row", "visible"])
    elif confirm:
        # Confirmation approved
        return f"Operation '{operation_name}' confirmed", private_key, False, gr.update(visible=False, elem_classes=["confirmation-row"])
    else:
        # Confirmation rejected
        return f"Operation cancelled", None, False, gr.update(visible=False, elem_classes=["confirmation-row"])

# Chat function for Gradio
async def chat_bot(message, history, wallet_address, system_prompt_base):
    # Check if API key is configured
    if not ANTHROPIC_API_KEY:
        yield "", history + [[message, "⚠️ API key not configured! Please add ANTHROPIC_API_KEY to your .env file or environment variables."]]
        return
    
    # Customize system prompt with wallet address if available
    current_system_prompt = system_prompt_base
    if wallet_address:
        current_system_prompt += f"\n\nThe user's connected wallet address is: {wallet_address}"
        
    # Construct messages from history
    messages = []
    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        if assistant:  # Skip if the assistant hasn't responded yet
            messages.append({"role": "assistant", "content": assistant})
    
    # Add the current message
    messages.append({"role": "user", "content": message})
    
    try:
        # Try to use MCP if the server is available
        if os.path.exists("../mcp/build/index.js"):
            async with stdio_client(server_params) as (read, write):
                # Call Claude API with MCP
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
                        system=current_system_prompt,
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
                            bot_message = "\n".join(final_text)
                            yield "", history + [[message, bot_message]]
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
                            bot_message = "\n".join(final_text)
                            yield "", history + [[message, bot_message]]

                    bot_message = "\n".join(final_text)
                    yield "", history + [[message, bot_message]]
                    return
        else:
            # Fallback to direct Claude API without tools
            response = client.messages.create(
                system=current_system_prompt,
                model=MODEL,
                max_tokens=1024,
                messages=messages
            )
            
            # Simple response without tools
            text_response = ""
            for content in response.content:
                if content.type == 'text':
                    text_response += content.text
            
            yield "", history + [[message, text_response]]
            return
    except Exception as e:
        # Handle any errors gracefully
        error_message = f"Sorry, I encountered an error: {str(e)}\n\nPlease try again later."
        yield "", history + [[message, error_message]]
        return

# Create the Gradio interface
with gr.Blocks(title="WalletPilot", css="""
    /* Dark mode theme */
    body {
        background-color: #121212;
        color: #f0f0f0;
    }
    
    /* Sidebar boxes */
    .sidebar-box {
        border-radius: 8px;
        margin-bottom: 20px;
        background-color: #2a2a2a;
        border: 1px solid #444;
        color: #f0f0f0;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
    }
    .sidebar-box h2 {
        font-size: 1.2em;
        padding: 10px;
        margin: 0;
        background-color: #1a1a1a;
        border-bottom: 1px solid #444;
        border-radius: 8px 8px 0 0;
        color: #ffffff;
    }
    
    /* Confirmation row and buttons */
    .confirmation-row {
        display: flex;
        gap: 10px;
        padding: 10px;
        visibility: hidden; /* Hide by default */
    }
    .confirmation-row.visible {
        visibility: visible;
    }
    .confirm-btn {
        background-color: #4CAF50 !important;
        color: white !important;
        font-weight: bold;
        padding: 8px 16px;
        border-radius: 4px;
    }
    .cancel-btn {
        background-color: #f44336 !important;
        color: white !important;
        font-weight: bold;
        padding: 8px 16px;
        border-radius: 4px;
    }
    .refresh-btn {
        background-color: #2196F3 !important;
        color: white !important;
        font-weight: bold;
        padding: 6px 12px;
        border-radius: 4px;
        margin: 10px;
    }
    
    /* Wallet balance display */
    .confirmation-box {
        aspect-ratio: 1/1;
        min-height: 200px;
        max-height: 300px;
        display: flex;
        flex-direction: column;
        padding: 0;
        overflow: hidden;
    }
    .confirmation-box > .prose {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: flex-start;
        color: #f0f0f0;
        padding: 15px;
        overflow-y: auto;
    }
    /* Token balance styling */
    .confirmation-box > .prose p {
        margin: 5px 0;
        display: flex;
        justify-content: space-between;
        width: 100%;
    }
    .confirmation-box > .prose strong {
        color: #64b5f6;
    }
    
    /* Transaction history layout */
    .history-box {
        min-height: 400px;
        display: flex;
        flex-direction: column;
    }
    .history-box > .prose {
        flex-grow: 1;
        overflow-y: auto;
        color: #f0f0f0;
        padding: 15px;
    }
    .history-box > .prose strong {
        color: #81c784;
    }
    
    /* Fix for duplicate components and ensuring visibility */
    .container:first-child > .prose {
        display: none;
    }
    .sidebar-box .prose {
        display: block !important;
    }
    
    /* Make inputs and buttons look better in dark mode */
    input, textarea {
        background-color: #333 !important;
        color: #f0f0f0 !important;
        border: 1px solid #555 !important;
    }
    button {
        background-color: #444 !important;
        color: #f0f0f0 !important;
    }
    
    /* API key warning */
    .api-warning {
        background-color: #ff9800;
        color: #000000;
        padding: 10px;
        border-radius: 4px;
        margin: 10px 0;
        font-weight: bold;
        text-align: center;
    }
""") as app:
    # State variables
    privateKeyState = gr.State("")
    walletAddressState = gr.State("")
    pvkey_needs_confirmation = gr.State(False)
    current_operation = gr.State("")
    
    with gr.Row():
        # Left panel for main content
        with gr.Column(scale=3):
            # Add API key warning
            oneinch_api_key = os.getenv("ONEINCH_API_KEY")
            if not oneinch_api_key or oneinch_api_key == "KTcYqWTXV5b9XLypC1Ky4XAX5B5NidHS":
                gr.HTML("""
                <div class="api-warning">
                    ⚠️ 1inch API Key not configured! 
                    <p>Please add a valid ONEINCH_API_KEY to your .env file or environment variables.</p>
                    <p>You can get a free API key at <a href="https://portal.1inch.dev/" target="_blank">https://portal.1inch.dev/</a></p>
                </div>
                """)
            
            with gr.Tabs():
                with gr.Tab("💬 Chat"):
                    # Create a more customizable chat interface
                    with gr.Group():
                        chatbot = gr.Chatbot(
                            label="Claude Assistant",
                            height=400,
                            show_copy_button=True,
                            show_share_button=False,
                            elem_id="chatbot"
                        )
                        msg = gr.Textbox(
                            placeholder="Ask a question...",
                            show_label=False,
                            container=False
                        )
                        clear = gr.Button("Clear")
                        
                        def respond(message, chat_history):
                            return chat_bot(message, chat_history, walletAddressState.value, SYSTEM_PROMPT)
                        
                        msg.submit(
                            respond,
                            [msg, chatbot],
                            [msg, chatbot],
                            queue=True
                        ).then(
                            lambda: "",
                            None,
                            [msg],
                            queue=False
                        )
                        
                        clear.click(lambda: [], None, [chatbot], queue=False)
                
                with gr.Tab("🔧 Settings"):
                    gr.Markdown("## App Settings")

                    private_key = gr.Textbox(
                        label="Wallet Private Key",
                        type="password",
                        placeholder="Enter your wallet private key"
                    )
                    
                    save_btn = gr.Button("Save Settings")
                    debug_btn = gr.Button("Debug (Test Account)", visible=True)
                    derived_wallet = gr.Markdown("Your wallet address will appear here after entering private key")

        # Right panel for confirmation and history
        with gr.Column(scale=1):
            # Top-right: Balance display or confirmation dialog
            with gr.Group(elem_classes=["sidebar-box", "confirmation-box"]):
                gr.Markdown("## Wallet Information")
                wallet_info = gr.Markdown("No wallet address provided")
                
                # Add confirmation row for private key operations
                confirmation_row = gr.Row(visible=False, elem_classes=["confirmation-row"])
                with confirmation_row:
                    confirm_btn = gr.Button("Confirm", variant="primary", elem_classes=["confirm-btn"])
                    cancel_btn = gr.Button("Cancel", variant="secondary", elem_classes=["cancel-btn"])
                
                refresh_bal_btn = gr.Button("Refresh Balances", elem_classes=["refresh-btn"])
            
            # Middle/bottom-right: Transaction history
            with gr.Group(elem_classes=["sidebar-box", "history-box"]):
                gr.Markdown("## Transaction History")
                transactions = gr.Markdown("No wallet address provided")
                refresh_tx_btn = gr.Button("Refresh Transactions", elem_classes=["refresh-btn"])
    
    # Modified save_settings function to use the new component names
    def modified_save_settings(private_key):
        if not private_key:
            return private_key, None, "⚠️ No private key provided.", "No wallet address provided", "No wallet address provided"
        
        try:
            # Derive the wallet address from private key
            acct = Account.from_key(private_key)
            wallet_address = acct.address
            
            # Format wallet address display
            wallet_display = f"## Your Wallet\n\n**Address**: {wallet_address}"
            
            try:
                print(f"Fetching wallet data for address: {wallet_address}")
                # Get balances and transaction history from multiple chains using the new functions
                wallet_data = asyncio.run(get_all_wallet_data(wallet_address))
                
                # Debug: Print what chains returned data
                balances = wallet_data.get("balances", "")
                history = wallet_data.get("history", "")
                
                print(f"Successfully fetched wallet data")
                return private_key, wallet_address, wallet_display, balances, history
            except Exception as data_e:
                print(f"Error fetching wallet data: {str(data_e)}")
                import traceback
                traceback.print_exc()
                return private_key, wallet_address, wallet_display, f"Error fetching wallet data: {str(data_e)}", f"Error fetching transaction history: {str(data_e)}"
        except Exception as e:
            print(f"Error processing private key: {str(e)}")
            import traceback
            traceback.print_exc()
            return private_key, None, f"⚠️ Error processing private key: {str(e)}", "No wallet address provided", "No wallet address provided"
    
    # Modified use_pvkey for confirmation handling
    def modified_use_pvkey(private_key, operation_name, confirm):
        result = use_pvkey(private_key, operation_name, confirm)
        return result[0], result[1], result[2], result[3]  # message, key, needs_confirm, confirm_row
    
    # Connect all the event handlers
    
    # Connect save button
    save_btn.click(
        fn=modified_save_settings,
        inputs=[private_key],
        outputs=[privateKeyState, walletAddressState, derived_wallet, wallet_info, transactions]
    )
    
    # Add debug button functionality
    debug_btn.click(
        fn=lambda: "513df09ad9ce80f0cee857fcaf2b58318bd683fdbb3e2523a4ce825ec88a1d58",
        inputs=[],
        outputs=[private_key]
    )
    
    # Connect confirmation buttons
    confirm_btn.click(
        fn=modified_use_pvkey,
        inputs=[privateKeyState, current_operation, gr.Checkbox(value=True, visible=False)],
        outputs=[wallet_info, current_operation, pvkey_needs_confirmation, confirmation_row]
    )
    
    cancel_btn.click(
        fn=modified_use_pvkey,
        inputs=[privateKeyState, current_operation, gr.Checkbox(value=False, visible=False)],
        outputs=[wallet_info, current_operation, pvkey_needs_confirmation, confirmation_row]
    )
    
    # Connect refresh buttons
    refresh_tx_btn.click(
        fn=lambda address: asyncio.run(get_all_wallet_data(address))["history"] if is_valid_address(address) else "Invalid wallet address",
        inputs=[walletAddressState],
        outputs=[transactions]
    )
    
    refresh_bal_btn.click(
        fn=lambda address: asyncio.run(get_all_wallet_data(address))["balances"] if is_valid_address(address) else "Invalid wallet address",
        inputs=[walletAddressState],
        outputs=[wallet_info]
    )

app.launch()

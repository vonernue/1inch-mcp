import os
import requests
import json
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Union, Any
from web3 import Web3
from web3.exceptions import InvalidAddress
from eth_utils import is_address
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Web3 provider
# You can use Infura, Alchemy, or any other provider
INFURA_API_KEY = os.getenv("INFURA_API_KEY")
ETH_PROVIDER_URL = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
w3 = Web3(Web3.HTTPProvider(ETH_PROVIDER_URL))

# API keys
ONEINCH_API_KEY = os.getenv("ONEINCH_API_KEY", "QatRzkYNrVbp9WvpuacgKL8GK7O9d3CI")  # Use the provided API key

# Check if API key is updated
print(f"Using 1inch API key: {ONEINCH_API_KEY[:4]}...{ONEINCH_API_KEY[-4:]}")

# List of chains to query
CHAINS = [
    {"id": 1, "name": "Ethereum", "symbol": "ETH"},
    {"id": 137, "name": "Polygon", "symbol": "MATIC"},
    {"id": 56, "name": "BNB Smart Chain", "symbol": "BNB"},
    {"id": 42161, "name": "Arbitrum", "symbol": "ETH"},
    {"id": 10, "name": "Optimism", "symbol": "ETH"},
    {"id": 8453, "name": "Base", "symbol": "ETH"},
    {"id": 43114, "name": "Avalanche", "symbol": "AVAX"}
]

# Helper functions for address validation
def is_valid_address(address: str) -> bool:
    """
    Check if an Ethereum address is valid

    Args:
        address (str): Ethereum address to check

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        return is_address(address)
    except:
        return False

def get_ens_name(address: str) -> Optional[str]:
    """
    Get ENS name for an Ethereum address using web3.py

    Args:
        address (str): Ethereum address to resolve

    Returns:
        Optional[str]: ENS name if available, None otherwise
    """
    if not is_valid_address(address):
        return None

    try:
        # Check if connected to Ethereum
        if not w3.is_connected():
            return None

        # Get ENS name
        ens_name = w3.ens.name(address)
        return ens_name
    except Exception as e:
        print(f"Error resolving ENS name: {str(e)}")
        return None

def get_address_from_ens(ens_name: str) -> Optional[str]:
    """
    Resolve ENS name to Ethereum address

    Args:
        ens_name (str): ENS name to resolve (e.g., "vitalik.eth")

    Returns:
        Optional[str]: Ethereum address if resolvable, None otherwise
    """
    try:
        # Check if connected to Ethereum
        if not w3.is_connected():
            return None

        # Get address from ENS name
        address = w3.ens.address(ens_name)
        return address
    except Exception as e:
        print(f"Error resolving ENS address: {str(e)}")
        return None

# 1inch API functions
async def get_1inch_token_balances(session, wallet_address: str, chain_id: int) -> Dict[str, Any]:
    """
    Get token balances for a wallet address using 1inch Balance API

    Args:
        session: aiohttp ClientSession
        wallet_address (str): Wallet address to check balances for
        chain_id (int): Chain ID to query (e.g., 1 for Ethereum, 137 for Polygon)

    Returns:
        Dict: Token balances data
    """
    # Check if API key is valid
    if not ONEINCH_API_KEY or ONEINCH_API_KEY == "KTcYqWTXV5b9XLypC1Ky4XAX5B5NidHS":
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": "Invalid or missing 1inch API key. Get your API key at https://portal.1inch.dev/",
            "tokens": []
        }

    url = f"https://api.1inch.dev/balance/v1.2/{chain_id}/balances/{wallet_address}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ONEINCH_API_KEY}"
    }

    try:
        # Get token balances from 1inch
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                raw_balances = await response.json()

                # Convert raw balances to a structured format
                chain_name = next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}")

                # Get token details for non-zero balances
                token_details = []
                for token_address, balance in raw_balances.items():
                    if balance == "0":
                        continue

                    # Get token info for tokens with balance
                    try:
                        # Needed for token metadata
                        token_info_url = f"https://api.1inch.dev/token/v1.2/{chain_id}/token?address={token_address}"
                        async with session.get(token_info_url, headers=headers) as token_response:
                            if token_response.status == 200:
                                token_data = await token_response.json()

                                # Format the token balance
                                decimals = int(token_data.get("decimals", 18))
                                symbol = token_data.get("symbol", "UNKNOWN")
                                name = token_data.get("name", "Unknown Token")

                                # Calculate formatted balance
                                balance_formatted = float(balance) / (10 ** decimals)

                                # Native token check
                                is_native = token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

                                token_details.append({
                                    "token_address": token_address,
                                    "symbol": symbol,
                                    "name": name,
                                    "decimals": decimals,
                                    "balance": balance,
                                    "balance_formatted": balance_formatted,
                                    "native_token": is_native
                                })

                                # Add a small delay to avoid rate limiting
                                await asyncio.sleep(0.05)
                    except Exception as token_error:
                        # If we can't get token info, still add the balance with minimal info
                        token_details.append({
                            "token_address": token_address,
                            "symbol": "UNKNOWN",
                            "name": "Unknown Token",
                            "decimals": 18,
                            "balance": balance,
                            "balance_formatted": float(balance) / (10 ** 18),
                            "native_token": token_address.lower() == "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
                        })

                return {
                    "chain": chain_id,
                    "chain_name": chain_name,
                    "tokens": token_details
                }
            else:
                error_text = await response.text()
                return {
                    "chain": chain_id,
                    "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
                    "error": f"HTTP Error {response.status}: {error_text}",
                    "tokens": []
                }
    except Exception as e:
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": str(e),
            "tokens": []
        }

async def get_1inch_portfolio(session, wallet_address: str, chain_id: int) -> Dict[str, Any]:
    """
    Get portfolio data for a wallet address using 1inch Portfolio API

    Args:
        session: aiohttp ClientSession
        wallet_address (str): Wallet address to check portfolio for
        chain_id (int): Chain ID to query (e.g., 1 for Ethereum, 137 for Polygon)

    Returns:
        Dict: Portfolio data
    """
    # Check if API key is valid
    if not ONEINCH_API_KEY or ONEINCH_API_KEY == "KTcYqWTXV5b9XLypC1Ky4XAX5B5NidHS":
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": "Invalid or missing 1inch API key. Get your API key at https://portal.1inch.dev/",
            "current_value": None,
            "token_details": None
        }

    endpoints = [
        f"https://api.1inch.dev/portfolio/v4/overview?addresses={wallet_address}&chain_id={chain_id}",
        f"https://api.1inch.dev/portfolio/v4/overview/erc20/details?addresses={wallet_address}&chain_id={chain_id}"
    ]

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ONEINCH_API_KEY}"
    }

    try:
        results = []
        for endpoint in endpoints:
            async with session.get(endpoint, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results.append(data)
                else:
                    error_text = await response.text()
                    results.append({"error": f"HTTP Error {response.status}: {error_text}"})

                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)

        chain_name = next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}")

        if len(results) >= 2 and "error" not in results[0] and "error" not in results[1]:
            return {
                "chain": chain_id,
                "chain_name": chain_name,
                "current_value": results[0],
                "token_details": results[1]
            }
        else:
            # If one of the API calls failed, return what we have
            return {
                "chain": chain_id,
                "chain_name": chain_name,
                "error": results[0].get("error", "Unknown error"),
                "current_value": results[0] if "error" not in results[0] else None,
                "token_details": results[1] if len(results) > 1 and "error" not in results[1] else None
            }
    except Exception as e:
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": str(e),
            "current_value": None,
            "token_details": None
        }

# 1inch History API
async def get_1inch_transaction_history(session, wallet_address: str, chain_id: int, limit: int = 5) -> Dict[str, Any]:
    """
    Get transaction history for a wallet address using 1inch History API

    Args:
        session: aiohttp ClientSession
        wallet_address (str): Wallet address to get history for
        chain_id (int): Chain ID to query (e.g., 1 for Ethereum, 137 for Polygon)
        limit (int): Number of transactions to return

    Returns:
        Dict: Transaction history data
    """
    # Check if API key is valid
    if not ONEINCH_API_KEY or ONEINCH_API_KEY == "KTcYqWTXV5b9XLypC1Ky4XAX5B5NidHS":
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": "Invalid or missing 1inch API key. Get your API key at https://portal.1inch.dev/",
            "result": []
        }

    # Use the working endpoint format
    url = "https://api.1inch.dev/history/v1.0/history/transactions"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {ONEINCH_API_KEY}"
    }

    params = {
        "addresses": wallet_address,
        "limit": str(limit),
        "direction": "both",
        "chain_id": str(chain_id)
    }

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                chain_name = next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}")

                # Handle different response formats
                transactions = []
                if isinstance(data, list):
                    # API returns a list of transactions
                    transactions = data
                elif isinstance(data, dict) and "transactions" in data:
                    # API returns a dict with a 'transactions' key
                    transactions = data.get("transactions", [])

                # Add chain information to match our expected structure
                return {
                    "chain": chain_id,
                    "chain_name": chain_name,
                    "result": transactions
                }
            elif response.status == 429:
                # Rate limit exceeded
                return {
                    "chain": chain_id,
                    "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
                    "error": "Rate limit exceeded. Please try again later.",
                    "result": []
                }
            else:
                error_text = await response.text()
                return {
                    "chain": chain_id,
                    "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
                    "error": f"HTTP Error {response.status}: {error_text}",
                    "result": []
                }
    except Exception as e:
        return {
            "chain": chain_id,
            "chain_name": next((c["name"] for c in CHAINS if c["id"] == chain_id), f"Chain {chain_id}"),
            "error": str(e),
            "result": []
        }

#get 1Inch transactions history
def fetch_transaction_history_another(wallet_address, chainId="1") -> Dict[str] :
    url = f"https://api.1inch.io/v4.0/1/history?address={wallet_address}"
    headers = {
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    url = f"https://api.1inch.dev/history/v2.0/history/{wallet_address}/events"
    headers = {
        "Authorization": f"Bearer {ONEINCH_API_KEY}",
        "accept": "application/json"
    }
    params={
        "chainId":chainId
    }

    markdown = f"## Transactions History\n\n"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if "items" in data:
            transactions = data["items"]
            if not transactions:
                print(f"No transactions found for address {wallet_address} on chain 1.")
                return

            print(f"Transaction history for address {wallet_address} on chain 1:")
            for trans in transactions:
                tx = trans['details']

                tx_hash = tx['txHash']
                tx_type = tx['type']
                tx_time = datetime.fromtimestamp(trans['timeMs'] / 1000.0)
                to_addr = tx['fromAddress']
                from_addr = tx['toAddress']
                tx_val = tx['tokenActions'][0]['amount']
                token_id = tx['tokenActions'][0].get('tokenId', 'NA')

                markdown += f"- **{tx_type} {tx_val} {token_id}**\n"
                markdown += f"  To/From: {to_addr} {from_addr}\n"
                markdown += f"  Hash: {tx_hash}\n"
                markdown += f"  Time: {tx_time}\n\n"
            return{
                "history": markdown
            }

        else:
            print(f"Error: {data.get('message', 'Unknown error')}")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching transaction history: {e}")
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
    except KeyError as e:
        print(f"Key error: {e}. Check the API response format.")


# Main function to get wallet data from all sources and chains
async def get_wallet_data_all_chains(wallet_address: str, chains: List[Dict] = None) -> Dict[str, Any]:
    """
    Get wallet balances and transaction history for all specified chains in parallel

    Args:
        wallet_address (str): Wallet address to get data for
        chains (List[Dict]): List of chain objects to query (defaults to CHAINS)

    Returns:
        Dict: Wallet data for all chains
    """
    if not is_valid_address(wallet_address):
        return {"error": "Invalid wallet address"}

    if chains is None:
        chains = CHAINS

    # Get ENS name if available (only works on Ethereum mainnet)
    ens_name = get_ens_name(wallet_address)

    async with aiohttp.ClientSession() as session:
        # Create tasks for parallel execution - 1inch Balance API
        balance_tasks = [
            get_1inch_token_balances(session, wallet_address, chain["id"])
            for chain in chains
        ]

        # Execute balance tasks in parallel
        balances_results = await asyncio.gather(*balance_tasks)

        # Execute history tasks sequentially with delay to avoid rate limits
        history_results = []
        for chain in chains:
            # Add delay between requests to avoid rate limiting
            if len(history_results) > 0:
                await asyncio.sleep(1)  # Wait 1 second between requests

            result = await get_1inch_transaction_history(session, wallet_address, chain["id"])
            history_results.append(result)

        # Optional: Get portfolio data from 1inch for Ethereum only
        try:
            eth_portfolio = await get_1inch_portfolio(session, wallet_address, 1)  # Ethereum mainnet
        except Exception as e:
            eth_portfolio = {"error": str(e)}

    return {
        "wallet_address": wallet_address,
        "ens_name": ens_name,
        "balances": balances_results,
        "history": history_results,
        "portfolio": eth_portfolio
    }

def format_wallet_balances_markdown_multi_chain(wallet_data: Dict[str, Any]) -> str:
    """
    Format wallet balances for multiple chains as Markdown

    Args:
        wallet_data (Dict): Wallet data from get_wallet_data_all_chains

    Returns:
        str: Formatted markdown
    """
    wallet_address = wallet_data.get("wallet_address", "Unknown")
    ens_name = wallet_data.get("ens_name")
    balances_data = wallet_data.get("balances", [])
    portfolio = wallet_data.get("portfolio", {})

    ens_display = f" ({ens_name})" if ens_name else ""

    # Start with wallet header
    markdown = f"## Wallet Balances\n\n"
    markdown += f"**Address**: {wallet_address[:6]}...{wallet_address[-4:]}{ens_display}\n\n"

    # Add portfolio info if available
    if portfolio and "current_value" in portfolio and portfolio["current_value"] and "totalUsd" in portfolio["current_value"]:
        total_usd = portfolio["current_value"]["totalUsd"]
        markdown += f"**Total Value**: ${total_usd:.2f} USD\n\n"

    # Check if we have any balance data
    if not balances_data:
        return markdown + "No balance data available."

    # Flag to track if we found any tokens
    found_tokens = False

    # Process each chain
    for chain_data in balances_data:
        chain_id = chain_data.get("chain", "unknown")
        chain_name = chain_data.get("chain_name", f"Chain {chain_id}")
        tokens = chain_data.get("tokens", [])

        if "error" in chain_data and not tokens:
            markdown += f"### {chain_name}\n"
            markdown += f"Error: {chain_data.get('error')}\n\n"
            continue

        if not tokens:
            continue  # Skip chains with no tokens

        # Flag that we found tokens
        found_tokens = True

        # Add chain header
        markdown += f"### {chain_name}\n\n"

        # Sort tokens by value (native token first, then by descending value)
        sorted_tokens = sorted(
            tokens,
            key=lambda x: (
                not x.get("native_token", False),  # Native tokens first
                -float(x.get("balance_formatted", "0"))  # Then by descending value
            )
        )

        # List tokens
        for token in sorted_tokens:
            symbol = token.get("symbol", "Unknown")
            balance = float(token.get("balance_formatted", "0"))
            token_name = token.get("name", "Unknown Token")

            # Format with 6 decimal places for small values, 4 for larger ones
            if balance < 0.0001 and balance > 0:
                formatted_balance = f"{balance:.6f}"
            else:
                formatted_balance = f"{balance:.4f}"

            markdown += f"- **{symbol}**: {formatted_balance} ({token_name})\n"

        markdown += "\n"

    # If we didn't find any tokens on any chain
    if not found_tokens:
        markdown += "No tokens found across any blockchain. The wallet may be empty or the API may not have data for these chains yet.\n\n"
        # List the chains we checked
        markdown += "Chains checked: " + ", ".join([chain_data.get("chain_name", f"Chain {chain_data.get('chain', 'unknown')}") for chain_data in balances_data]) + "\n\n"

    return markdown

def format_transaction_history_markdown_multi_chain(wallet_data: Dict[str, Any]) -> str:
    """
    Format transaction history for multiple chains as Markdown

    Args:
        wallet_data (Dict): Wallet data from get_wallet_data_all_chains

    Returns:
        str: Formatted markdown
    """
    wallet_address = wallet_data.get("wallet_address", "Unknown")
    ens_name = wallet_data.get("ens_name")
    history_data = wallet_data.get("history", [])

    ens_display = f" ({ens_name})" if ens_name else ""

    # Start with wallet header
    markdown = f"## Recent Transactions\n\n"
    markdown += f"**Address**: {wallet_address[:6]}...{wallet_address[-4:]}{ens_display}\n\n"

    # Check if we have any history data
    if not history_data:
        return markdown + "No transaction history available."

    # Flag to track if we found any transactions
    found_transactions = False

    # Process each chain
    for chain_data in history_data:
        chain_id = chain_data.get("chain", "unknown")
        chain_name = chain_data.get("chain_name", f"Chain {chain_id}")
        transactions = chain_data.get("result", [])

        if "error" in chain_data and not transactions:
            markdown += f"### {chain_name}\n"
            markdown += f"Error: {chain_data.get('error')}\n\n"
            continue

        if not transactions:
            continue  # Skip chains with no transactions

        # Flag that we found transactions
        found_transactions = True

        # Add chain header
        markdown += f"### {chain_name}\n\n"

        # Get chain symbol
        chain_symbol = next((c["symbol"] for c in CHAINS if c["id"] == chain_id), "")

        # List transactions
        for tx in transactions:
            tx_hash = tx.get("hash", tx.get("txHash", "Unknown"))
            block_timestamp = tx.get("timestamp", tx.get("timeStamp", "Unknown"))

            # Format time if it's a string or number
            if isinstance(block_timestamp, str):
                # Convert from ISO string or Unix timestamp
                try:
                    if block_timestamp.isdigit():
                        timestamp = int(block_timestamp)
                        dt = datetime.fromtimestamp(timestamp)
                    else:
                        dt = datetime.fromisoformat(block_timestamp.replace('Z', '+00:00'))
                    block_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            elif isinstance(block_timestamp, (int, float)):
                try:
                    dt = datetime.fromtimestamp(block_timestamp)
                    block_timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # Process from/to addresses
            from_address = tx.get("from", tx.get("fromAddress", "Unknown"))
            to_address = tx.get("to", tx.get("toAddress", "Unknown"))

            # Determine transaction type and partner
            if from_address.lower() == wallet_address.lower():
                tx_type = "Sent"
                tx_partner = to_address
            else:
                tx_type = "Received"
                tx_partner = from_address

            # Format partner address
            partner_display = f"{tx_partner[:10]}...{tx_partner[-6:]}"

            # Get value if available
            tx_value = 0
            tx_symbol = chain_symbol

            # Try to get value from different formats
            if "value" in tx:
                if isinstance(tx["value"], str) and tx["value"].isdigit():
                    tx_value = float(tx["value"]) / 10**18  # Assuming 18 decimals for native token
                elif isinstance(tx["value"], (int, float)):
                    tx_value = float(tx["value"]) / 10**18

            # Check for tokenSymbol in 1inch format
            if "tokenSymbol" in tx:
                tx_symbol = tx.get("tokenSymbol", chain_symbol)

            # If there is a tokenValue, use that instead
            if "tokenValue" in tx:
                tx_value = float(tx.get("tokenValue", "0"))

            # Format the transaction
            markdown += f"- **{tx_type} {tx_value:.4f} {tx_symbol}**\n"
            markdown += f"  To/From: {partner_display}\n"
            markdown += f"  Hash: {tx_hash[:10]}...{tx_hash[-6:]}\n"
            markdown += f"  Time: {block_timestamp}\n\n"

    # If we didn't find any transactions on any chain
    if not found_transactions:
        markdown += "No transactions found across any blockchain. The wallet may be new or the API may not have data for these chains yet.\n\n"
        # List the chains we checked
        markdown += "Chains checked: " + ", ".join([chain_data.get("chain_name", f"Chain {chain_data.get('chain', 'unknown')}") for chain_data in history_data]) + "\n\n"

    return markdown

# Main function to fetch all wallet data
async def get_all_wallet_data(wallet_address: str) -> Dict[str, str]:
    """
    Get all wallet data and format as Markdown

    Args:
        wallet_address (str): Wallet address to get data for

    Returns:
        Dict[str, str]: Formatted markdown for balances and history
    """
    if not is_valid_address(wallet_address):
        return {
            "balances": "Invalid wallet address provided",
            "history": "Invalid wallet address provided"
        }

    try:
        # Get data for all chains
        wallet_data = await get_wallet_data_all_chains(wallet_address)

        # Format results
        balances_markdown = format_wallet_balances_markdown_multi_chain(wallet_data)
        history_markdown = format_transaction_history_markdown_multi_chain(wallet_data)

        return {
            "balances": balances_markdown,
            "history": history_markdown
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "balances": f"Error fetching wallet data: {str(e)}",
            "history": f"Error fetching wallet data: {str(e)}"
        }

# Example usage
if __name__ == "__main__":
    # Test with Vitalik's address
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    # Run async function
    import asyncio
    results = asyncio.run(get_all_wallet_data(test_address))

    # Print results
    print(results["balances"])
    print("\n\n")
    print(results["history"])
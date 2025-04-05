import requests
import json
import time
import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OneinchSwapClient:
    def __init__(self, private_key, network_id=8453, api_key=None):
        """
        Initialize the 1inch Swap API client
        
        Args:
            private_key (str): Your wallet's private key
            network_id (int): Network ID (8453 for Base)
            api_key (str): Your 1inch API key from the developer portal
        """
        self.base_url = "https://api.1inch.dev/swap"
        self.network_id = network_id
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
            
        # Initialize web3 and account
        self.rpc_urls = {
            1: "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161", # Ethereum
            56: "https://bsc-dataseed.binance.org/",                            # BSC
            137: "https://polygon-rpc.com/",                                    # Polygon
            8453: "https://mainnet.base.org",                                   # Base
            10: "https://mainnet.optimism.io",                                  # Optimism
        }
        
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_urls.get(network_id, self.rpc_urls[1])))
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        print(f"Initialized with wallet address: {self.address}")
        
        # Common token info
        self.known_tokens = {
            # Base tokens
            "8453": {
                "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": {
                    "symbol": "ETH",
                    "name": "Native Ethereum on Base",
                    "decimals": 18
                },
                "0x4200000000000000000000000000000000000006": {
                    "symbol": "WETH",
                    "name": "Wrapped Ethereum on Base",
                    "decimals": 18
                },
                "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {
                    "symbol": "USDC",
                    "name": "USD Coin on Base",
                    "decimals": 6
                }
            },
            # Optimism tokens
            "10": {
                "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee": {
                    "symbol": "ETH",
                    "name": "Native Ethereum on Optimism",
                    "decimals": 18
                },
                "0x4200000000000000000000000000000000000006": {
                    "symbol": "WETH",
                    "name": "Wrapped Ethereum on Optimism",
                    "decimals": 18
                },
                "0x94b008aa00579c1307b0ef2c499ad98a8ce58e58": {
                    "symbol": "USDT",
                    "name": "Tether USD on Optimism",
                    "decimals": 6
                },
                "0x7f5c764cbc14f9669b88837ca1490cca17c31607": {
                    "symbol": "USDC",
                    "name": "USD Coin on Optimism",
                    "decimals": 6
                }
            }
        }
    
    def get_tokens(self):
        """Get the list of available tokens on the current network"""
        endpoint = f"{self.base_url}/v5.2/{self.network_id}/tokens"
        try:
            response = requests.get(endpoint, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error getting tokens: {response.status_code} - {response.text}")
                return {"tokens": {}}
        except Exception as e:
            print(f"Exception getting tokens: {str(e)}")
            return {"tokens": {}}
        
    def get_token_info(self, token_address):
        """
        Get token information for the current network
        
        Args:
            token_address (str): Token address
            
        Returns:
            dict: Token information
        """
        # Convert network_id to string for dictionary lookup
        network_id_str = str(self.network_id)
        
        # Convert token address to lowercase for comparison
        token_address_lower = token_address.lower()
        
        # First check our known tokens
        if network_id_str in self.known_tokens and token_address_lower in self.known_tokens[network_id_str]:
            token_info = self.known_tokens[network_id_str][token_address_lower].copy()
            token_info["address"] = token_address
            return token_info
        
        # Try to get from API
        tokens = self.get_tokens()
        if 'tokens' in tokens:
            # Check by exact address match
            if token_address in tokens['tokens']:
                token_info = tokens['tokens'][token_address]
                token_info["address"] = token_address
                return token_info
            
            # Try lowercase comparison
            for addr, info in tokens['tokens'].items():
                if addr.lower() == token_address_lower:
                    info["address"] = addr
                    return info
        
        print(f"Warning: Token {token_address} not found in API response or known tokens")
        
        # Default fallback for unknown tokens
        return {
            "symbol": f"UNKNOWN ({network_id_str})",
            "name": f"Unknown Token on network {network_id_str}",
            "address": token_address,
            "decimals": 18
        }
    
    def get_quote(self, from_token_address, to_token_address, amount):
        """
        Get a quote for swapping tokens
        
        Args:
            from_token_address (str): Address of the source token
            to_token_address (str): Address of the destination token
            amount (str): Amount to swap in wei (as string)
            
        Returns:
            dict: Quote information
        """
        endpoint = f"{self.base_url}/v5.2/{self.network_id}/quote"
        
        params = {
            "src": from_token_address,
            "dst": to_token_address, 
            "amount": amount,
            "from": self.address
        }
        
        print(f"Getting swap quote from: {endpoint}")
        print(f"With params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Quote successful. Expected output: {result.get('toAmount', 'Unknown')} tokens")
                return result
            else:
                print(f"Response content: {response.text[:500]}...")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }
        except Exception as e:
            print(f"Error during API request: {str(e)}")
            return {"error": True, "message": str(e)}
    
    def get_swap_transaction(self, from_token_address, to_token_address, amount, slippage=1):
        """
        Get transaction data for a swap
        
        Args:
            from_token_address (str): Address of the source token
            to_token_address (str): Address of the destination token
            amount (str): Amount to swap in wei (as string)
            slippage (float): Maximum acceptable slippage percentage (default: 1%)
            
        Returns:
            dict: Transaction data
        """
        endpoint = f"{self.base_url}/v5.2/{self.network_id}/swap"
        
        params = {
            "src": from_token_address,
            "dst": to_token_address, 
            "amount": amount,
            "from": self.address,
            "slippage": slippage
        }
        
        print(f"Getting swap transaction from: {endpoint}")
        print(f"With params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Transaction data obtained successfully")
                
                # Debug the response
                print(f"Swap response: {json.dumps(result, indent=2)}")
                
                # Extract transaction data
                tx_data = result.get("tx", {})
                if not tx_data or not tx_data.get("to"):
                    print("Error: Transaction data missing or invalid in response")
                    return {"error": True, "message": "Transaction data invalid"}
                
                return tx_data
            else:
                print(f"Response content: {response.text[:500]}...")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }
        except Exception as e:
            print(f"Error getting swap transaction: {str(e)}")
            return {"error": True, "message": str(e)}
    
    def check_allowance(self, token_address):
        """
        Check if token is approved for swaps
        
        Args:
            token_address (str): Address of the token to check
            
        Returns:
            dict: Allowance information
        """
        endpoint = f"{self.base_url}/v5.2/{self.network_id}/approve/allowance"
        
        params = {
            "tokenAddress": token_address,
            "walletAddress": self.address
        }
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Allowance for {token_address}: {result.get('allowance', '0')}")
                return result
            else:
                print(f"Error checking allowance: {response.status_code} - {response.text}")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }
        except Exception as e:
            print(f"Error checking allowance: {str(e)}")
            return {"error": True, "message": str(e)}
    
    def get_approval_tx(self, token_address, amount=None):
        """
        Get transaction data for token approval
        
        Args:
            token_address (str): Address of the token to approve
            amount (str, optional): Amount to approve as a decimal string (default: max uint256)
            
        Returns:
            dict: Transaction data for approval
        """
        endpoint = f"{self.base_url}/v5.2/{self.network_id}/approve/transaction"
        
        # For unlimited approval, use max uint256 as a decimal string
        if amount is None:
            amount = str(2**256 - 1)
        
        params = {
            "tokenAddress": token_address,
            "amount": amount
        }
        
        print(f"Getting approval transaction data from: {endpoint}")
        print(f"With params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.get(endpoint, params=params, headers=self.headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Approval transaction data obtained successfully")
                return result
            else:
                print(f"Error getting approval transaction: {response.status_code} - {response.text}")
                return {
                    "error": True,
                    "status_code": response.status_code,
                    "message": response.text
                }
        except Exception as e:
            print(f"Error getting approval transaction: {str(e)}")
            return {"error": True, "message": str(e)}

    def sign_and_send_transaction(self, tx_data):
        """
        Sign and send a transaction
        
        Args:
            tx_data (dict): Transaction data
            
        Returns:
            str: Transaction hash
        """
        try:
            # Check if transaction data is valid
            if not tx_data or not tx_data.get('to'):
                print(f"Invalid transaction data: {json.dumps(tx_data, indent=2)}")
                return None
            
            # Convert value to int if it's a string (hex format)
            value = tx_data.get('value', '0')
            if isinstance(value, str) and value.startswith('0x'):
                value_int = int(value, 16)
            else:
                value_int = int(value)
                
            # Convert gas to int, handling different formats or set a default
            gas = tx_data.get('gas', '0')
            if isinstance(gas, str) and gas.startswith('0x'):
                gas_int = int(gas, 16)
            elif gas and isinstance(gas, str) and not gas.startswith('0x'):
                gas_int = int(gas)
            elif gas and isinstance(gas, int):
                gas_int = gas
            else:
                # If gas is 0 or not provided, set a reasonable default
                gas_int = 200000  # Default gas limit
            
            # Ensure gas is not too low
            if gas_int < 60000:
                print(f"Warning: Gas limit {gas_int} is too low. Setting to minimum 60000.")
                gas_int = 60000
            
            # Get destination address in checksum format
            to_address = Web3.to_checksum_address(tx_data.get('to'))
            
            # Prepare transaction
            tx = {
                'chainId': self.network_id,
                'nonce': self.web3.eth.get_transaction_count(self.address),
                'from': self.address,
                'to': to_address,
                'data': tx_data.get('data'),
                'value': value_int,
                'gas': gas_int,
                'gasPrice': self.web3.eth.gas_price,
            }
            
            print(f"Prepared transaction: {json.dumps(tx, indent=2, default=str)}")
            
            # Estimate gas if possible
            try:
                estimated_gas = self.web3.eth.estimate_gas({
                    'from': self.address,
                    'to': to_address,
                    'data': tx_data.get('data'),
                    'value': value_int
                })
                
                print(f"Estimated gas: {estimated_gas}")
                # Add a 20% buffer for safety
                tx['gas'] = int(estimated_gas * 1.2)
                print(f"Setting gas to: {tx['gas']}")
            except Exception as e:
                print(f"Error estimating gas: {str(e)}. Using default value of {gas_int}")
                # Keep using the already set gas_int
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.account.key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Transaction sent! Hash: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            print(f"Error sending transaction: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

# Format amount with proper decimals
def format_token_amount(amount, decimals):
    """Format token amount with proper decimals"""
    amount_float = float(amount) / (10 ** decimals)
    if decimals == 0:
        return f"{int(amount_float):,}"
    elif decimals <= 6:
        return f"{amount_float:.{decimals}f}"
    else:
        return f"{amount_float:.8f}"

# Test swap using standard 1inch Swap API
def test_swap():
    # Load private key and API key from environment variables
    private_key = os.getenv('PRIVATE_KEY')
    api_key = os.getenv('1inch_API_KEY')
    
    if not private_key or not api_key:
        print("Please set PRIVATE_KEY and 1inch_API_KEY in your .env file")
        return
    
    # Test the API key
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Initialize the client for Base network
    client = OneinchSwapClient(
        private_key=private_key,
        network_id=8453,  # Base mainnet
        api_key=api_key
    )
    
    # Define tokens for the swap
    # WETH on Base
    from_token = "0x4200000000000000000000000000000000000006"
    # USDC on Base
    to_token = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    
    # 0.0001 ETH in wei (100000000000000 wei = 0.0001 ETH)
    amount = "100000000000000"
    
    try:
        # Get token information
        print("\n1. Getting token information...")
        from_token_info = client.get_token_info(from_token)
        to_token_info = client.get_token_info(to_token)
        
        from_symbol = from_token_info.get('symbol', 'UNKNOWN')
        to_symbol = to_token_info.get('symbol', 'UNKNOWN')
        from_decimals = int(from_token_info.get('decimals', 18))
        to_decimals = int(to_token_info.get('decimals', 6))
        
        print(f"From token: {from_symbol} ({from_token_info.get('name', 'Unknown')})")
        print(f"To token: {to_symbol} ({to_token_info.get('name', 'Unknown')})")
        
        # Check if token is approved for swaps
        print("\n2. Checking token allowance...")
        allowance = client.check_allowance(from_token)
        
        if not allowance.get("error", False):
            allowance_amount = allowance.get('allowance', '0')
            print(f"Current allowance: {allowance_amount}")
            
            if int(allowance_amount) < int(amount):
                print("Insufficient allowance. Getting approval transaction...")
                approval_tx = client.get_approval_tx(from_token, amount="115792089237316195423570985008687907853269984665640564039457584007913129639935")
                
                if not approval_tx.get("error", False):
                    print("Approval transaction data obtained. Sending approval transaction...")
                    
                    # Sign and send approval transaction
                    approval_tx_hash = client.sign_and_send_transaction(approval_tx)
                    if not approval_tx_hash:
                        print("Failed to send approval transaction")
                        return
                    
                    print(f"Approval transaction sent! Hash: {approval_tx_hash}")
                    print("Waiting for approval to be confirmed...")
                    time.sleep(30)  # Wait for approval to be confirmed
                else:
                    print(f"Error getting approval transaction: {approval_tx.get('message', 'Unknown error')}")
                    return
            else:
                print(f"Token already has sufficient allowance")
        else:
            print(f"Error checking allowance: {allowance.get('message', 'Unknown error')}")
            return
        
        # Get a quote
        print("\n3. Getting swap quote...")
        quote = client.get_quote(from_token, to_token, amount)
        
        if not quote.get("error", False):
            to_amount = quote.get('toAmount')
            if to_amount:
                # Format the amounts for better readability
                from_amount_formatted = format_token_amount(amount, from_decimals)
                to_amount_formatted = format_token_amount(to_amount, to_decimals)
                
                print(f"Swapping {from_amount_formatted} {from_symbol} for approximately {to_amount_formatted} {to_symbol}")
                
                # Calculate exchange rate
                try:
                    exchange_rate = float(to_amount) / float(amount) * (10**from_decimals) / (10**to_decimals)
                    print(f"Exchange rate: 1 {from_symbol} = {exchange_rate:.6f} {to_symbol}")
                except Exception as e:
                    print(f"Error calculating exchange rate: {str(e)}")
            
            # Get the swap transaction
            print("\n4. Getting swap transaction...")
            swap_tx = client.get_swap_transaction(from_token, to_token, amount, slippage=1)
            
            if not swap_tx.get("error", False):
                # Convert value to readable format
                value = swap_tx.get('value', '0')
                if isinstance(value, str) and value.startswith('0x'):
                    value_eth = int(value, 16) / 10**18
                else:
                    value_eth = int(value) / 10**18
                
                # Convert gas to int
                gas = swap_tx.get('gas', '0')
                if isinstance(gas, str) and gas.startswith('0x'):
                    gas_int = int(gas, 16)
                else:
                    gas_int = int(gas)
                
                # Print a more readable version of the transaction
                tx_summary = {
                    "to": swap_tx.get("to"),
                    "value": f"{value_eth:.8f} ETH",
                    "gas": gas_int,
                }
                print(f"Swap transaction summary: {json.dumps(tx_summary, indent=2)}")
                
                # Send swap transaction
                print("Sending swap transaction...")
                tx_hash = client.sign_and_send_transaction(swap_tx)
                
                if tx_hash:
                    print(f"Swap transaction sent! Hash: {tx_hash}")
                    print(f"You can monitor the transaction on BaseScan: https://basescan.org/tx/{tx_hash}")
                    
                    print(f"\nSwap completed:")
                    print(f"  Sent: {from_amount_formatted} {from_symbol}")
                    print(f"  Received: ~{to_amount_formatted} {to_symbol}")
                    print(f"  Rate: 1 {from_symbol} = {exchange_rate:.6f} {to_symbol}")
                else:
                    print("Failed to send swap transaction")
            else:
                print(f"Error getting swap transaction: {swap_tx.get('message', 'Unknown error')}")
        else:
            print(f"Error getting quote: {quote.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_swap()

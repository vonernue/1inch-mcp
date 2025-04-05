import asyncio
from eth_account import Account
from frontend.get_data import get_all_wallet_data, get_1inch_token_balances, get_1inch_transaction_history
import aiohttp
import os

async def test_wallet():
    # The private key to test
    private_key = '513df09ad9ce80f0cee857fcaf2b58318bd683fdbb3e2523a4ce825ec88a1d58'
    
    # Derive the wallet address
    wallet_address = Account.from_key(private_key).address
    print(f"Testing wallet address: {wallet_address}")
    
    # Also test Vitalik's address for comparison
    vitalik_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    print(f"Also testing Vitalik's address: {vitalik_address}")
    
    # Fetch wallet data
    try:
        print(f"Fetching data from 1inch APIs...")
        wallet_data = await get_all_wallet_data(wallet_address)
        vitalik_data = await get_all_wallet_data(vitalik_address)
        
        # Print results for test wallet
        print(f"\n===== TEST WALLET BALANCES =====\n")
        print(wallet_data["balances"])
        
        print(f"\n===== TEST WALLET TRANSACTION HISTORY =====\n")
        print(wallet_data["history"])
        
        # Print results for Vitalik's wallet
        print(f"\n===== VITALIK'S WALLET BALANCES =====\n")
        print(vitalik_data["balances"])
        
        print(f"\n===== VITALIK'S WALLET TRANSACTION HISTORY =====\n")
        print(vitalik_data["history"])
        
        # Test direct API calls for a single chain
        print(f"\n===== TESTING DIRECT API CALLS FOR ETHEREUM MAINNET =====\n")
        
        async with aiohttp.ClientSession() as session:
            # Test 1inch Balance API for Ethereum for test wallet
            print("Testing 1inch Balance API for Ethereum (test wallet)...")
            eth_balance = await get_1inch_token_balances(session, wallet_address, 1)  # Ethereum
            print(f"1inch Balance API response for test wallet: {len(eth_balance.get('tokens', []))} tokens found")
            
            if eth_balance.get('error'):
                print(f"Balance API Error for test wallet: {eth_balance.get('error')}")
            else:
                print(f"Tokens: {eth_balance.get('tokens', [])}")
            
            # Test 1inch Balance API for Ethereum for Vitalik
            print("\nTesting 1inch Balance API for Ethereum (Vitalik)...")
            vitalik_balance = await get_1inch_token_balances(session, vitalik_address, 1)  # Ethereum
            print(f"1inch Balance API response for Vitalik: {len(vitalik_balance.get('tokens', []))} tokens found")
            
            if vitalik_balance.get('error'):
                print(f"Balance API Error for Vitalik: {vitalik_balance.get('error')}")
            else:
                # Show first 3 tokens with balances
                tokens = vitalik_balance.get('tokens', [])
                if tokens:
                    print("First 3 tokens:")
                    for i, token in enumerate(tokens[:3]):
                        print(f"  {token.get('symbol', 'Unknown')}: {token.get('balance_formatted', 0)}")
            
            # Test 1inch History API
            print("\nTesting 1inch History API...")
            history = await get_1inch_transaction_history(session, wallet_address, 1)  # Ethereum
            vitalik_history = await get_1inch_transaction_history(session, vitalik_address, 1)  # Ethereum
            
            print(f"1inch History API response for test wallet: {len(history.get('result', []))} transactions found")
            print(f"1inch History API response for Vitalik: {len(vitalik_history.get('result', []))} transactions found")
            
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting wallet test...")
    success = asyncio.run(test_wallet())
    print(f"Test completed with {'success' if success else 'failure'}") 
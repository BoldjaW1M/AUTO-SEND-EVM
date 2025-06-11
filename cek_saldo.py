import json
import os
from web3 import Web3

def get_balances(addresses, rpc_url):
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("Failed to connect to RPC endpoint")
        return None
    
    balances = {}
    for address in addresses:
        try:
            balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address.strip()))
            balance_eth = w3.from_wei(balance_wei, 'ether')
            balances[address.strip()] = {
                'wei': str(balance_wei),
                'ether': str(balance_eth),
                'formatted': f"{balance_eth:.6f} ETH"
            }
        except Exception as e:
            print(f"Error checking balance for {address}: {str(e)}")
            balances[address.strip()] = None
    
    return balances

def save_results(balances, rpc_url, output_file):
    results = {
        'rpc_used': rpc_url,
        'address_count': len(balances),
        'addresses': balances
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"Results saved to {output_file}")

def main():
    input_file = "address.txt"
    output_file = "balances.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found in the current directory.")
        return
    
    with open(input_file, 'r') as f:
        addresses = f.readlines()
    
    if not addresses:
        print("No addresses found in address.txt")
        return
    
    print(f"Found {len(addresses)} addresses to check")
    
    rpc_url = input("Enter EVM RPC endpoint URL: ").strip()
    
    print("Checking balances...")
    balances = get_balances(addresses, rpc_url)
    
    if balances:
        save_results(balances, rpc_url, output_file)
        
        # Print summary
        print("\nSummary:")
        print(f"RPC Used: {rpc_url}")
        print(f"Addresses with balance > 0: {sum(1 for addr in balances.values() if addr and float(addr['ether']) > 0)}")
        print(f"Total ETH across all addresses: {sum(float(addr['ether']) for addr in balances.values() if addr):.6f} ETH")

if __name__ == "__main__":
    main()
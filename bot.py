import random
import secrets
from web3 import Web3
from colorama import Fore, Style, init
import time
import pyfiglet

# Initialize colorama
init(autoreset=True)

# Create ASCII banner
banner = pyfiglet.figlet_format("sigundul")

# Display banner with color
print(Fore.MAGENTA + Style.BRIGHT + banner)

# Display additional text
additional_text = "Auto Send EVM\nSupports EVM Chains"
print(Fore.CYAN + Style.BRIGHT + additional_text)

def print_header():
    pass

# Transfer native tokens function
def TransferNative(sender, senderkey, recipient, amount, web3, retries=3):
    for attempt in range(retries):
        try:
            gas_price = web3.eth.gas_price
            base_fee = web3.eth.fee_history(1, 'latest')["baseFeePerGas"][0]
            max_priority_fee = web3.to_wei(2, 'gwei')
            max_fee_per_gas = max(base_fee + max_priority_fee * 2, gas_price + max_priority_fee * 2)

            gas_tx = {
                'chainId': web3.eth.chain_id,
                'from': sender,
                'to': recipient,
                'value': web3.to_wei(amount, 'ether'),
                'gasPrice': gas_price,
                'nonce': web3.eth.get_transaction_count(sender)
            }
            gasAmount = web3.eth.estimate_gas(gas_tx)

            auto_tx = {
                'chainId': web3.eth.chain_id,
                'from': sender,
                'gas': gasAmount,
                'to': recipient,
                'value': web3.to_wei(amount, 'ether'),
                'maxFeePerGas': max_fee_per_gas,
                'maxPriorityFeePerGas': max_priority_fee,
                'nonce': web3.eth.get_transaction_count(sender),
                'type': 2  # EIP-1559 transaction
            }

            fixamount = '%.18f' % float(amount)
            sign_txn = web3.eth.account.sign_transaction(auto_tx, senderkey)
            print(Fore.BLUE + f'Processing Send {fixamount} Native To: {recipient} ...')
            tx_hash = web3.eth.send_raw_transaction(sign_txn.raw_transaction)

            txid = str(web3.to_hex(tx_hash))
            transaction_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(Fore.GREEN + f'Send {fixamount} Native To: {recipient} Success!')
            print(Fore.GREEN + f'TX-ID: {txid}')

            balance = web3.eth.get_balance(sender)
            balance_in_ether = web3.from_wei(balance, 'ether')
            print(Fore.BLUE + f"Remaining Balance for {sender}: {balance_in_ether} ETH")
            break
        except Exception as e:
            print(Fore.RED + f"Error on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                print(Fore.YELLOW + f"Retrying in 5 seconds... ({attempt + 1}/{retries})")
                time.sleep(5)
            else:
                print(Fore.RED + f"Transaction failed after {retries} attempts.")

# Load recipient addresses from file
def load_recipients(filename="address.txt", web3=None):
    try:
        with open(filename, "r") as file:
            addresses = [line.strip() for line in file if line.strip()]
            if not addresses:
                raise ValueError("Recipient list is empty!")
            return [web3.to_checksum_address(addr) for addr in addresses]
    except Exception as e:
        print(Fore.RED + f"Error loading recipient addresses: {e}")
        exit(1)

# Load private keys from file
def load_private_keys(filename="pvkeys.txt"):
    try:
        with open(filename, "r") as file:
            keys = [line.strip() for line in file if line.strip()]
            if not keys:
                raise ValueError("Private key list is empty!")
            return keys
    except Exception as e:
        print(Fore.RED + f"Error loading private keys: {e}")
        exit(1)

# Check if the RPC URL is valid
def check_rpc_url(rpc_url, retries=3):
    for attempt in range(retries):
        try:
            web3 = Web3(Web3.HTTPProvider(rpc_url))
            if web3.is_connected():
                print(Fore.GREEN + "Connected to RPC successfully!")
                chain_id = web3.eth.chain_id
                print(Fore.BLUE + f"Chain ID: {chain_id}")
                return web3
            else:
                print(Fore.RED + "Failed to connect to RPC. Please check the URL and try again.")
        except Exception as e:
            print(Fore.RED + f"Error connecting to RPC: {e}")
        if attempt < retries - 1:
            print(Fore.YELLOW + f"Retrying in 5 seconds... ({attempt + 1}/{retries})")
            time.sleep(5)
    print(Fore.RED + f"Failed to connect to RPC after {retries} attempts.")
    return None

# Main execution
print_header()

web3 = None
while not web3:
    rpc_url = input("Please enter the RPC URL: ")
    web3 = check_rpc_url(rpc_url)

private_keys = load_private_keys("pvkeys.txt")
recipients = load_recipients("address.txt", web3)
loop = int(input("How many transactions do you want to process? : "))
amount = float(input("How much Ether to send per transaction (e.g., 0.001)?: "))

for sender_key in private_keys:
    sender = web3.eth.account.from_key(sender_key)
    for i in range(loop):
        recipient = random.choice(recipients)  # Random recipient selection for better distribution
        print(Fore.BLUE + f"\nProcessing Transaction {i + 1}/{loop} for Wallet {sender.address}")
        TransferNative(sender.address, sender_key, recipient, amount, web3)

print(Fore.GREEN + "\nAll transactions completed.")

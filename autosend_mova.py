# autosend2.py — web3.py 7.12.0
# - Kirim LEGACY dulu (tanpa "type"), fallback ke EIP-1559 (type 2) jika ditolak
# - Estimasi fee tanpa fee_history
# - PK dari pvkeys.txt
# - Anti-salah paste RPC di prompt address
# - snake_case raw_transaction

import os
from pathlib import Path
from typing import Optional, Tuple

from web3 import Web3
from eth_account import Account
from web3.middleware import ExtraDataToPOAMiddleware

RPC_URL = os.getenv("RPC_URL") or "https://mars.rpc.movachain.com"
PVKEY_FILE = Path("pvkeys.txt")

GAS_LIMIT = 21_000
EXTRA_BUFFER_WEI = 20_000_000_000_000  # ~0.00002 ETH

def connect() -> Web3:
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 60}))
    assert w3.is_connected(), f"RPC gak connect: {RPC_URL}"
    try:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        pass
    return w3

def load_keys(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File {path} tidak ditemukan.")
    keys = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not s.startswith("0x"):
            s = "0x" + s
        keys.append(s)
    if not keys:
        raise RuntimeError("pvkeys.txt kosong.")
    return keys

def guess_priority(w3: Web3) -> int:
    try:
        return int(w3.eth.max_priority_fee)  # bisa warning di beberapa node
    except Exception:
        return int(w3.to_wei("1", "gwei"))

def guess_eip1559_fees(w3: Web3) -> Tuple[int, int]:
    """
    Kembalikan (maxFeePerGas, maxPriorityFeePerGas) dalam wei.
    Tidak bergantung pada fee_history (tapi pakai kalau ada).
    """
    prio = guess_priority(w3)
    # Coba baseFee dari latest block
    base_fee = None
    try:
        blk = w3.eth.get_block("latest")
        base_fee = blk.get("baseFeePerGas", None)
    except Exception:
        pass

    # Coba gas_price untuk batas konservatif
    try:
        gp = int(w3.eth.gas_price)
    except Exception:
        gp = int(w3.to_wei("3", "gwei"))

    if isinstance(base_fee, int):
        max_fee = max(int(base_fee * 2 + prio), gp)
    else:
        max_fee = max(int(gp * 2 + prio), int(w3.to_wei("3", "gwei")))

    if max_fee <= prio:
        max_fee = prio + int(w3.to_wei("1", "gwei"))
    return int(max_fee), int(prio)

def ask_recipient_and_maybe_set_rpc() -> str:
    global RPC_URL
    first = input("input RPC URL : ").strip()
    if first.lower().startswith(("http://", "https://")):
        RPC_URL = first
        print(f"[i] RPC_URL di-set ke: {RPC_URL}")
        addr = input("Sekarang masukkan recipient address (0x...): ").strip()
    else:
        addr = first
    if not addr.lower().startswith("0x") or not Web3.is_address(addr):
        raise ValueError(f"Recipient must be a valid 0x address. Got: {addr}")
    return Web3.to_checksum_address(addr)

def pretty_eth(w3: Web3, wei: int) -> str:
    try:
        return f"{w3.from_wei(wei, 'ether')} ETH"
    except Exception:
        return f"{wei} wei"

def build_legacy_tx(acct_addr: str, to: str, value: int, nonce: int, chain_id: int, gas_price: int) -> dict:
    # Penting: TIDAK menyertakan field "type" untuk legacy
    return {
        "from": acct_addr,
        "to": to,
        "value": int(value),
        "nonce": nonce,
        "chainId": chain_id,
        "gas": GAS_LIMIT,
        "gasPrice": int(gas_price),
    }

def build_eip1559_tx(acct_addr: str, to: str, value: int, nonce: int, chain_id: int,
                     max_fee: int, max_prio: int) -> dict:
    return {
        "from": acct_addr,
        "to": to,
        "value": int(value),
        "nonce": nonce,
        "chainId": chain_id,
        "gas": GAS_LIMIT,
        "type": 2,
        "maxFeePerGas": int(max_fee),
        "maxPriorityFeePerGas": int(max_prio),
    }

def send_with_strategy(w3: Web3, acct: Account, to: str, send_value: int, chain_id: int):
    """
    1) Coba legacy (tanpa 'type').
    2) Jika ditolak (unknown type / butuh 1559 / rlp decode), fallback ke type-2.
    """
    nonce = w3.eth.get_transaction_count(acct.address, "pending")

    # LEGACY attempt
    try:
        try:
            gp = int(w3.eth.gas_price)
        except Exception:
            gp = int(w3.to_wei("3", "gwei"))
        tx_legacy = build_legacy_tx(acct.address, to, send_value, nonce, chain_id, gp)
        signed_legacy = acct.sign_transaction(tx_legacy)
        return w3.eth.send_raw_transaction(signed_legacy.raw_transaction)
    except Exception as e1:
        msg = str(e1)
        # indikasi node menolak legacy / decoding legacy gagal / butuh typed
        need_1559 = any(s in msg.lower() for s in [
            "eip-1559", "1559", "maxfeepergas", "maxpriorityfeepergas",
            "unknown transaction type", "rlp decode failed"
        ])
        if not need_1559:
            # kalau error lain, lepasin
            raise

    # Fallback: TYPE-2
    mf, pr = guess_eip1559_fees(w3)
    tx_1559 = build_eip1559_tx(acct.address, to, send_value, nonce, chain_id, mf, pr)
    signed_1559 = acct.sign_transaction(tx_1559)
    return w3.eth.send_raw_transaction(signed_1559.raw_transaction)

def main():
    to = ask_recipient_and_maybe_set_rpc()
    w3 = connect()
    chain_id = w3.eth.chain_id
    print(f"[i] Connected. chainId={chain_id}")

    keys = load_keys(PVKEY_FILE)

    for idx, pk in enumerate(keys, 1):
        print(f"\n=== Account #{idx} ===")
        try:
            acct = Account.from_key(pk)
            bal = w3.eth.get_balance(acct.address)
            print(f"Sender: {acct.address}")
            print(f"Sender balance: {pretty_eth(w3, bal)}")

            # Estimasi biaya maksimum konservatif (pakai cap agar ga habis total)
            mf, pr = guess_eip1559_fees(w3)
            fee_cap = GAS_LIMIT * int(max(mf, int(w3.eth.gas_price) if hasattr(w3.eth, "gas_price") else mf))

            send_value = bal - fee_cap - EXTRA_BUFFER_WEI
            if send_value <= 0:
                print("Balance tidak cukup setelah fee cap, skip.")
                continue

            print(f"Processing send {pretty_eth(w3, int(send_value))} → {to}")

            tx_hash = send_with_strategy(w3, acct, to, int(send_value), chain_id)
            print("TX sent:", tx_hash.hex())

            try:
                rcpt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                print(f"Mined in block {rcpt.blockNumber}")
            except Exception as e:
                print(f"Broadcasted, menunggu konfirmasi: {e}")

        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Error:", repr(e))

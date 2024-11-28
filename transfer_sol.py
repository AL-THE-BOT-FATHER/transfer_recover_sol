import json
import time
from typing import Optional
from solders.keypair import Keypair  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.system_program import TransferParams, transfer
from solders.transaction import VersionedTransaction  # type: ignore
from solders.message import MessageV0  # type: ignore
from solders.compute_budget import set_compute_unit_price  # type: ignore


def transfer_sol(
    rpc_url: str,
    sender_priv_base58_str: str,
    receiver_pubkey_str: str,
    sol_amount: float,
    max_retries: int = 20,
    retry_interval: int = 3,
) -> Optional[bool]:

    client = Client(rpc_url)
    sender_keypair = Keypair.from_base58_string(sender_priv_base58_str)
    to_pubkey = Pubkey.from_string(receiver_pubkey_str)
    lamports_amount = int(sol_amount * 1e9)

    print(f"Sending {sol_amount} SOL from {sender_keypair.pubkey()} to {to_pubkey}")

    sender_balance = client.get_balance(sender_keypair.pubkey()).value
    print(f"Sender's balance: {sender_balance / 1e9} SOL")

    if sender_balance < lamports_amount:
        print("Insufficient balance for the transaction.")
        return False

    instructions = [
        transfer(
            TransferParams(
                from_pubkey=sender_keypair.pubkey(),
                to_pubkey=to_pubkey,
                lamports=lamports_amount,
            )
        ),
        set_compute_unit_price(100_000),
    ]

    try:
        recent_blockhash = client.get_latest_blockhash().value.blockhash
    except Exception as e:
        print(f"Failed to fetch recent blockhash: {e}")
        return None

    try:
        compiled_message = MessageV0.try_compile(
            sender_keypair.pubkey(),
            instructions,
            [],
            recent_blockhash,
        )
    except Exception as e:
        print(f"Failed to compile message: {e}")
        return None

    try:
        print("Sending transaction...")
        txn_sig = client.send_transaction(
            txn=VersionedTransaction(compiled_message, [sender_keypair]),
            opts=TxOpts(skip_preflight=True),
        ).value

        print("Transaction Signature:", txn_sig)
    except Exception as e:
        print(f"Failed to send transaction: {e}")
        return None

    for attempt in range(1, max_retries + 1):
        try:
            txn_res = client.get_transaction(
                txn_sig,
                encoding="json",
                commitment="confirmed",
                max_supported_transaction_version=0,
            )
            txn_json = json.loads(txn_res.value.transaction.meta.to_json())

            if txn_json["err"] is None:
                print("Transaction confirmed.")
                return True
            else:
                print("Transaction failed.")
                return False
        except Exception:
            print(f"Awaiting confirmation... try {attempt} of {max_retries}...")

        if attempt < max_retries:
            time.sleep(retry_interval)

    print("Max retries reached; transaction not confirmed.")
    return False


def main():
    rpc_url = "https://mainnet.helius-rpc.com/?api-key="
    sender_priv_base58_str = "<SENDER_PRIVATE_KEY_BASE58>"
    receiver_pubkey_str = "<RECEIVER_PUBLIC_KEY>"
    sol_amount = 1.0

    try:
        result = transfer_sol(
            rpc_url=rpc_url,
            sender_priv_base58_str=sender_priv_base58_str,
            receiver_pubkey_str=receiver_pubkey_str,
            sol_amount=sol_amount,
        )
        if result is True:
            print("SOL transfer successful!")
        elif result is False:
            print("SOL transfer failed.")
        else:
            print("An error occurred during the SOL transfer process.")
    except Exception as e:
        print(f"Error in transfer: {e}")


if __name__ == "__main__":
    main()

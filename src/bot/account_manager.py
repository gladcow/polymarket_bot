import json
from pathlib import Path

import web3.middleware
from web3 import Web3
from web3.constants import HASH_ZERO
from web3.gas_strategies.time_based import fast_gas_price_strategy
from web3.middleware import ExtraDataToPOAMiddleware


class AccountManager:
    def __init__(self, chain_id: int, pk: str, funder: str,  web3_url:str, usdc_address: str, ctf_address: str):
        self.pk =pk
        self.chainId = chain_id
        self.funder = "" if not funder or len(funder) == 0 else Web3.to_checksum_address(funder)
        self.web3 = Web3(Web3.HTTPProvider(web3_url))
        self.addr = self.web3.eth.account.from_key(self.pk).address
        self.usdc_address = Web3.to_checksum_address(usdc_address)
        self.web3.eth.default_account = self.addr
        self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self.web3.eth.set_gas_price_strategy(fast_gas_price_strategy)

        # Load ABI from file
        usdc_abi_path = Path(__file__).parent.parent / "abi" / "usdc.abi"
        with open(usdc_abi_path, "r") as f:
            usdc_abi = json.load(f)
        ctf_abi_path = Path(__file__).parent.parent / "abi" / "ctf.abi"
        with open(ctf_abi_path, "r") as f:
            ctf_abi = json.load(f)

        self.usdc = self.web3.eth.contract(address=self.usdc_address, abi=usdc_abi)
        self.ctf = self.web3.eth.contract(address=Web3.to_checksum_address(ctf_address), abi=ctf_abi)

    def usdc_balance(self) -> float:
        if len(self.funder) > 0:
            addr = self.funder
        else:
            addr = self.addr
        return self.usdc.functions.balanceOf(self.addr).call() / 10**6

    def balance(self) -> float:
        return self.web3.eth.get_balance(self.addr) / 10**18

    def redeem_market(self, condition_id: str) -> None:
        try:
            nonce = self.web3.eth.get_transaction_count(self.addr)
            tx = self.ctf.functions.redeemPositions(
                self.usdc_address,  # The collateral token address
                HASH_ZERO,  # The parent collectionId, always bytes32(0) for Polymarket markets
                condition_id,
                [1, 2],
            ).build_transaction({
                "from": self.addr,
                "chainId": self.chainId,
                "gas": 500000,
                "gasPrice": 3 * self.web3.eth.gas_price,
                "nonce": nonce,
            })
            signed = self.web3.eth.account.sign_transaction(tx, self.pk)
            txid = self.web3.to_hex(self.web3.eth.send_raw_transaction(signed.raw_transaction))
            print(f"Redeem transaction hash: {txid}")
            self.web3.eth.wait_for_transaction_receipt(txid, 20, 1.0)
            print("Redeem complete!")
        except Exception as e:
            print(f"Error redeeming Outcome Tokens : {e}")

    def ensure_usdc_allowance(self, required_amount: float, addr: str) -> bool:
        required = int(required_amount * 10**6)
        current_allowance = self.usdc.functions.allowance(self.addr,
                                                         addr).call()
        print(f"current_allowance: {current_allowance}")

        if current_allowance >= required:
            return True

        tx = self.usdc.functions.approve(addr, required).build_transaction({
            "from": self.addr,
            "gas": 500000,
            "gasPrice": 3 * self.web3.eth.gas_price,
            "nonce": self.web3.eth.get_transaction_count(self.addr),
            "chainId": self.chainId
        })

        signed = self.web3.eth.account.sign_transaction(tx, self.pk)
        txid = self.web3.to_hex(self.web3.eth.send_raw_transaction(signed.raw_transaction))
        receipt = self.web3.eth.wait_for_transaction_receipt(txid, 20,  1)

        if receipt.status == 1:
            print(f"USDC allowance updated: {txid}")
            return True
        else:
            print(f"USDC allowance update failed: {txid}")
        return False









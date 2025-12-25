import json
from pathlib import Path
from web3 import Web3

class AccountManager:
    def __init__(self, pk: str, funder: str,  web3_url:str, usdc_address: str, ctf_address: str):
        self.pk =pk
        #self.addr =
        self.funder = Web3.to_checksum_address(funder)
        self.web3 = Web3(Web3.HTTPProvider(web3_url))
        
        # Load ABI from file
        usdc_abi_path = Path(__file__).parent.parent / "abi" / "usdc.abi"
        with open(usdc_abi_path, "r") as f:
            usdc_abi = json.load(f)
        ctf_abi_path = Path(__file__).parent.parent / "abi" / "ctf.abi"
        with open(ctf_abi_path, "r") as f:
            ctf_abi = json.load(f)

        self.usdc = self.web3.eth.contract(address=Web3.to_checksum_address(usdc_address), abi=usdc_abi)
        self.ctf = self.web3.eth.contract(address=Web3.to_checksum_address(ctf_address), abi=ctf_abi)

    def balance(self) -> float:
        return self.usdc.functions.balanceOf(self.funder).call() / 10**6




from py_clob_client.client import ClobClient

class Market:
    def __init__(self, host: str, pk: str, chain_id: int, condition_id: str) -> None:
        self.condition_id = condition_id
        self.client = ClobClient(host, key=pk, chain_id=chain_id)
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def market_info(self) -> str:
        return self.client.get_market(self.condition_id)
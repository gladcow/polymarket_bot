from py_clob_client.client import ClobClient

class Market:
    def __init__(self, host: str, pk: str, chain_id: int, condition_id: str) -> None:
        self.condition_id = condition_id
        self.client = ClobClient(host, key=pk, chain_id=chain_id)
        self.client.set_api_creds(self.client.create_or_derive_api_creds())
        self.info = self.client.get_market(self.condition_id)
        self.upTokenId = self.info['tokens'][0]['token_id']
        self.downTokenId = self.info['tokens'][1]['token_id']

    def market_info(self) -> str:
        return self.client.get_market(self.condition_id)

    def best_up_ask(self) -> tuple[float, float]:
        order_book = self.client.get_order_book(self.upTokenId)
        if not order_book.asks:
            return 0, 0
        return float(order_book.asks[-1].price), float(order_book.asks[-1].size)

    def best_down_ask(self) -> tuple[float, float]:
        order_book = self.client.get_order_book(self.downTokenId)
        if not order_book.asks:
            return 0, 0
        return float(order_book.asks[-1].price), float(order_book.asks[-1].size)

    def buy_up(self, price: float, size: float) -> bool:
        cur_price,  cur_size = self.best_up_ask()
        if cur_price > price or size > cur_size:
            return False
        print(f"Buying {size} UP at {price}")
        return True

    def buy_down(self, price: float, size: float) -> bool:
        cur_price,  cur_size = self.best_down_ask()
        if cur_price > price or size > cur_size:
            return False
        print(f"Buying {size} DOWN at {price}")
        return True

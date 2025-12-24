from py_clob_client.client import ClobClient
from py_clob_client.clob_types import MarketOrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY

class Market:
    def __init__(self, host: str, pk: str, funder: str, chain_id: int, condition_id: str, dry: bool) -> None:
        self.dry = dry
        self.condition_id = condition_id
        self.client = ClobClient(host, key=pk, chain_id=chain_id,  signature_type=2, funder=funder)
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
        if self.dry:
            cur_price,  cur_size = self.best_up_ask()
            if cur_price > price or size > cur_size:
                return False
            print(f"Buying {size} UP at {price}")
            return True
        else:
            # Real order posting
            try:
                amount_in_dollars = size * price
                
                order_args = MarketOrderArgs(
                    token_id=str(self.upTokenId),
                    amount=float(amount_in_dollars),
                    side=BUY,
                )
                signed_order = self.client.create_market_order(order_args)
                response = self.client.post_order(signed_order, OrderType.FOK)
                
                if response.get("success"):
                    filled = response.get("data", {}).get("filledAmount", amount_in_dollars)
                    print(f"Order placed: BUY {filled:.4f} shares of UP token at ${price:.4f}")
                    return True
                else:
                    error_msg = response.get("error", "Unknown error")
                    print(f"Failed to place BUY order: {error_msg}")
                    return False
            except Exception as e:
                print(f"Error placing BUY order: {str(e)}")
                return False

    def buy_down(self, price: float, size: float) -> bool:
        if self.dry:
            cur_price,  cur_size = self.best_down_ask()
            if cur_price > price or size > cur_size:
                return False
            print(f"Buying {size} DOWN at {price}")
            return True
        else:
            # Real order posting
            try:
                amount_in_dollars = size * price
                
                order_args = MarketOrderArgs(
                    token_id=str(self.downTokenId),
                    amount=float(amount_in_dollars),
                    side=BUY,
                )
                signed_order = self.client.create_market_order(order_args)
                response = self.client.post_order(signed_order, OrderType.FOK)
                
                if response.get("success"):
                    filled = response.get("data", {}).get("filledAmount", amount_in_dollars)
                    print(f"Order placed: BUY {filled:.4f} shares of DOWN token at ${price:.4f}")
                    return True
                else:
                    error_msg = response.get("error", "Unknown error")
                    print(f"Failed to place BUY order: {error_msg}")
                    return False
            except Exception as e:
                print(f"Error placing BUY order: {str(e)}")
                return False

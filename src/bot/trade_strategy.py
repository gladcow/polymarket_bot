from bot import Market


class TradeStrategy:
    def __init__(self, market: Market, order_size: float, max_combined_price: float, pair_difference_threshold:float):
        self.market = market
        self.order_size = order_size
        self.max_combined_price = max_combined_price
        self.pair_difference_threshold = pair_difference_threshold
        self.up_spent = 0.0
        self.down_spent = 0.0
        self.up_amount = 0.0
        self.down_amount = 0.0
        self.up_inited = False
        self.down_inited = False
        self.init_up_price = 0
        self.init_down_price = 0

    def init(self)-> bool:
        if self.up_inited and self.down_inited:
            return True

        up_price,  up_size =  self.market.best_up_ask()
        down_price,  down_size =  self.market.best_down_ask()
        if not self.up_inited:
            self.init_up_price = up_price
        if not self.down_inited:
            self.init_down_price = down_price
        if self.init_up_price + self.init_down_price < self.max_combined_price:
            if up_size > self.order_size and not self.up_inited:
                if self.market.buy_up(up_price,  self.order_size):
                    self.up_spent += up_price * self.order_size
                    self.up_amount += self.order_size
                    self.up_inited = True
            if down_size > self.order_size and not self.down_inited:
                if self.market.buy_down(down_price,  self.order_size):
                    self.down_spent += down_price * self.order_size
                    self.down_amount += self.order_size
                    self.down_inited = True

        return self.up_inited and self.down_inited

    def trade(self)-> None:
        if not self.up_inited or not self.down_inited:
            return
        pair_cost = self.up_spent / self.up_amount + self.down_spent / self.down_amount
        up_price,  up_size =  self.market.best_up_ask()
        if up_size > self.order_size:
            new_pair_cost = (self.up_spent + up_price * self.order_size) / (self.up_amount + self.order_size) + self.down_spent / self.down_amount
            if new_pair_cost < pair_cost and self.up_amount < self.pair_difference_threshold * self.down_amount:
                if self.market.buy_up(up_price, self.order_size):
                    self.up_spent += up_price * self.order_size
                    self.up_amount += self.order_size
        down_price,  down_size =  self.market.best_down_ask()
        if down_size > self.order_size:
            new_pair_cost = self.up_spent / self.up_amount + (self.down_spent + self.order_size * down_price) / (self.down_amount + self.order_size)
            if new_pair_cost < pair_cost and self.down_amount < self.pair_difference_threshold * self.up_amount:
                if self.market.buy_down(down_price, self.order_size):
                    self.down_spent += down_price * self.order_size
                    self.down_amount += self.order_size

    def current_profit(self)-> float:
        return min(self.up_amount,  self.down_amount) - (self.up_spent + self.down_spent)

    def spent(self)-> float:
        return self.up_spent + self.down_spent

    def up_profit(self)-> float:
        return self.up_amount - (self.up_spent + self.down_spent)

    def down_profit(self)-> float:
        return self.down_amount - (self.up_spent + self.down_spent)

    def average_pair_cost(self)-> float:
        return self.up_spent / self.up_amount + self.down_spent / self.down_amount
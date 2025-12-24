import os
import time

from dotenv import load_dotenv

from bot.market import Market
from bot.market_finder import MarketFinder

load_dotenv()

def main():
    PK = os.getenv("PK")
    GAMMA_URL = os.getenv("GAMMA_URL")
    CLOB_URL = os.getenv("CLOB_URL")

    CHAIN_ID = int(os.getenv("CHAIN_ID"))
    ORDER_SIZE = float(os.getenv("ORDER_SIZE"))
    INIT_INTERVAL = int(os.getenv("INIT_INTERVAL"))
    TRADE_INTERVAL = int(os.getenv("TRADE_INTERVAL"))
    TAKE_PROFIT_THRESHOLD = float(os.getenv("TAKE_PROFIT_THRESHOLD"))
    PAIR_DIFFERENCE_THRESHOLD = float(os.getenv("PAIR_DIFFERENCE_THRESHOLD"))
    MAX_INIT_COMBINED_PRICE = float(os.getenv("MAX_INIT_COMBINED_PRICE"))

    print("Current 15 min BTC market:")
    finder = MarketFinder(GAMMA_URL)
    market_id = finder.get_current_market_id()
    start = finder.get_current_slot_start()
    market = Market(CLOB_URL, PK, CHAIN_ID, market_id)
    info = market.market_info() # TODO: check market is active

    up_spent = 0.0
    down_spent = 0.0
    up_amount = 0.0
    down_amount = 0.0
    # init buys
    up_inited = False
    down_inited = False
    init_up_price = 0
    init_down_price = 0
    while finder.slot_is_active(start):
        up_price,  up_size =  market.best_up_ask()
        down_price,  down_size =  market.best_down_ask()
        if not up_inited:
            init_up_price = up_price
        if not down_inited:
            init_down_price = down_price
        if init_up_price + init_down_price < MAX_INIT_COMBINED_PRICE:
            if up_size > ORDER_SIZE and not up_inited:
                if market.buy_up(up_price,  ORDER_SIZE):
                    up_spent += up_price * ORDER_SIZE
                    up_amount += ORDER_SIZE
                    up_inited = True
            if down_size > ORDER_SIZE and not down_inited:
                if market.buy_down(down_price,  ORDER_SIZE):
                    down_spent += down_price * ORDER_SIZE
                    down_amount += ORDER_SIZE
                    down_inited = True
        if up_inited and down_inited:
            break
        time.sleep(INIT_INTERVAL)
    # main loop
    pair_cost = up_spent / up_amount + down_spent / down_amount
    while finder.slot_is_active(start):
        up_price,  up_size =  market.best_up_ask()
        if up_size > ORDER_SIZE:
            new_pair_cost = (up_spent + up_price * ORDER_SIZE) / (up_amount + ORDER_SIZE) + down_spent / down_amount
            if new_pair_cost < pair_cost and up_amount < PAIR_DIFFERENCE_THRESHOLD * down_amount:
                if market.buy_up(up_price, ORDER_SIZE):
                    up_spent += up_price * ORDER_SIZE
                    up_amount += ORDER_SIZE
                    pair_cost = up_spent / up_amount + down_spent / down_amount
        down_price,  down_size =  market.best_down_ask()
        if down_size > ORDER_SIZE:
            new_pair_cost = up_spent / up_amount + (down_spent + ORDER_SIZE * down_price) / (down_amount + ORDER_SIZE)
            if new_pair_cost < pair_cost and down_amount < PAIR_DIFFERENCE_THRESHOLD * up_amount:
                if market.buy_down(down_price, ORDER_SIZE):
                    down_spent += down_price * ORDER_SIZE
                    down_amount += ORDER_SIZE
                    pair_cost = up_spent / up_amount + down_spent / down_amount
        if min(up_amount,  down_amount) > up_spent + down_spent + TAKE_PROFIT_THRESHOLD:
            print("Take profit")
            break
        time.sleep(TRADE_INTERVAL)
        print(f"Current Pair Cost: {pair_cost}")

    print(f"Spent: {up_spent + down_spent}")
    print(f"Profit for Up: {up_amount - (up_spent + down_spent)}")
    print(f"Profit for Down: {down_amount - (up_spent + down_spent)}")
    info = market.market_info()
    print(info)


if __name__ == "__main__":
    main()

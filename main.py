import os
import time

from dotenv import load_dotenv

from bot import MarketQL
from bot.account_manager import AccountManager
from bot.market import Market
from bot.market_finder import MarketFinder
from bot.trade_strategy import TradeStrategy

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
    MIN_USDC_BALANCE = float(os.getenv("MIN_USDC_BALANCE"))
    DRY_MODE = True if int(os.getenv("DRY_MODE")) else False
    USDC_ADDRESS = os.getenv("USDC_ADDRESS")
    CTF_ADDRESS = os.getenv("CTF_ADDRESS")
    FEE_MODULE_ADDRESS = os.getenv("FEE_MODULE_ADDRESS")
    CTF_EXCHANGE_ADDRESS = os.getenv("CTF_EXCHANGE_ADDRESS")
    WEB3_PROVIDER = os.getenv("WEB3_PROVIDER")
    GRAPHQL_URL = os.getenv("GRAPHQL_URL")

    account = AccountManager(CHAIN_ID, PK, WEB3_PROVIDER, USDC_ADDRESS, CTF_ADDRESS,  DRY_MODE)
    print(f"Account: {account.addr}")
    resolver = MarketQL(GRAPHQL_URL)
    initial_balance = account.balance()
    print(f"Initial balance: {initial_balance} POL")
    initial_usdc_balance = account.usdc_balance()
    print(f"Initial USDC balance: {initial_usdc_balance} USDC")
    finder = MarketFinder(GAMMA_URL)
    account.ensure_ctf_allowance(FEE_MODULE_ADDRESS)
    account.ensure_ctf_allowance(CTF_EXCHANGE_ADDRESS)
    print("Wait for the next slot")
    start = finder.get_current_slot_start()
    if not DRY_MODE:
        finder.wait_until_next_slot_start(start)

    profit = 0.0
    prev_up_profit = 0.0
    prev_down_profit = 0.0
    max_spent = 0.0
    min_profit = 0.0
    max_profit = 0.0

    while True:
        start = finder.get_current_slot_start()
        balance = account.balance()
        print(f"Current balance: {balance} POL")
        if balance < 0.01:
            print("Not enough funds")
            finder.wait_until_next_slot_start(start)
            continue
        balance_usdc = account.usdc_balance()
        print(f"Current USDC balance: {balance_usdc} USDC")
        if balance_usdc < MIN_USDC_BALANCE:
            print("Not enough funds")
            finder.wait_until_next_slot_start(start)
            continue

        account.ensure_usdc_allowance(2 * MIN_USDC_BALANCE, FEE_MODULE_ADDRESS)
        account.ensure_usdc_allowance(2 * MIN_USDC_BALANCE, CTF_EXCHANGE_ADDRESS)

        prev_market_id = finder.get_prev_market_id()
        print(f"Prev 15 min BTC market: {prev_market_id}")
        market_id = finder.get_current_market_id()
        print(f"Current 15 min BTC market: {market_id}")
        market = Market(CLOB_URL, PK, CHAIN_ID, market_id, DRY_MODE)

        strategy = TradeStrategy(market, ORDER_SIZE, MAX_INIT_COMBINED_PRICE, PAIR_DIFFERENCE_THRESHOLD)
        while finder.slot_is_active(start):
            if strategy.init():
                break
            time.sleep(INIT_INTERVAL)
        # main loop
        while finder.slot_is_active(start):
            res = strategy.trade()
            if strategy.current_profit() > TAKE_PROFIT_THRESHOLD:
                print("Take profit")
                break
            time.sleep(TRADE_INTERVAL)
            if res:
                print(f"Current Pair Cost: {strategy.average_pair_cost()}")

        resolved = False
        winnig_idx = 0
        while not resolved:
            resolved, winnig_idx = resolver.resolved(prev_market_id)
            time.sleep(1)
        account.redeem_market(prev_market_id)
        if winnig_idx == 0:
            print(f"UP wins {prev_market_id}")
            profit += prev_up_profit
        else:
            print(f"DOWN wins {prev_market_id}")
            profit += prev_down_profit
        if profit > max_profit:
            max_profit = profit
        if profit < min_profit:
            min_profit = profit
        print(f"Profit: {profit} USDC (Max Profit: {max_profit}, Min Profit: {min_profit})")

        spent = strategy.spent()
        if spent > max_spent:
            max_spent = spent
        profit -= spent
        print(f"Spent: {spent} USDC (Max Spent: {max_spent})")
        prev_up_profit = strategy.up_amount
        prev_down_profit = strategy.down_amount
        print(f"Profit for Up: {prev_up_profit}")
        print(f"Profit for Down: {prev_down_profit}")
        if finder.slot_is_active(start):
            print("Wait for the next slot")
            finder.wait_until_next_slot_start(start)


if __name__ == "__main__":
    main()

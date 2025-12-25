import os
import time

from dotenv import load_dotenv
from pygments.lexers.templates import CheetahHtmlLexer

from bot.account_manager import AccountManager
from bot.market import Market
from bot.market_finder import MarketFinder
from bot.trade_strategy import TradeStrategy

load_dotenv()

def main():
    PK = os.getenv("PK")
    FUNDER = os.getenv("FUNDER")
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
    WEB3_PROVIDER = os.getenv("WEB3_PROVIDER")

    account = AccountManager(CHAIN_ID, PK, FUNDER, WEB3_PROVIDER, USDC_ADDRESS, CTF_ADDRESS)
    print(f"Account: {account.addr}")
    initial_balance = account.balance()
    print(f"Initial balance: {initial_balance} POL")
    initial_usdc_balance = account.usdc_balance()
    print(f"Initial USDC balance: {initial_usdc_balance} USDC")
    finder = MarketFinder(GAMMA_URL)
    print("Wait for the next slot")
    start = finder.get_current_slot_start()
    finder.wait_until_next_slot_start(start)

    while True:
        start = finder.get_current_slot_start()
        balance = account.balance()
        print(f"Current balance: {balance} POL")
        if balance < 0.01:
            print("Not enough funds")
            finder.wait_until_next_slot_start(start)
            continue
        account.ensure_usdc_allowance(2 * MIN_USDC_BALANCE, FEE_MODULE_ADDRESS)
        time.sleep(120)
        prev_market_id = finder.get_prev_market_id()
        account.redeem_market(prev_market_id)
        balance_usdc = account.usdc_balance()
        print(f"Current USDC balance: {balance_usdc} USDC")
        if balance_usdc < MIN_USDC_BALANCE:
            print("Not enough funds")
            finder.wait_until_next_slot_start(start)
            continue

        print("Current 15 min BTC market:")
        market_id = finder.get_current_market_id()
        market = Market(CLOB_URL, PK, FUNDER, CHAIN_ID, market_id, DRY_MODE)

        strategy = TradeStrategy(market, ORDER_SIZE, MAX_INIT_COMBINED_PRICE, PAIR_DIFFERENCE_THRESHOLD)
        while finder.slot_is_active(start):
            if strategy.init():
                break
            time.sleep(INIT_INTERVAL)
        # main loop
        while finder.slot_is_active(start):
            strategy.trade()
            if strategy.current_profit() > TAKE_PROFIT_THRESHOLD:
                print("Take profit")
                break
            time.sleep(TRADE_INTERVAL)
            print(f"Current Pair Cost: {strategy.average_pair_cost()}")

        print(f"Spent: {strategy.spent()}")
        print(f"Profit for Up: {strategy.up_profit()}")
        print(f"Profit for Down: {strategy.down_profit()}")
        if finder.slot_is_active(start):
            print("Wait for the next slot")
            finder.wait_until_next_slot_start(start)


if __name__ == "__main__":
    main()

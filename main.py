import os

from dotenv import load_dotenv

from bot.market import Market
from bot.market_finder import MarketFinder

load_dotenv()

def main():
    print("Current 15 min BTC market:")
    finder = MarketFinder("https://gamma-api.polymarket.com/markets")
    id = finder.get_current_market_id()
    pk = os.getenv("PK")
    market = Market("https://clob.polymarket.com", pk, 137, id)
    print(market.market_info())


if __name__ == "__main__":
    main()

import time
from datetime import datetime, timezone, timedelta
import json
import requests


class MarketFinder:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    @staticmethod
    def get_current_slot_start() -> datetime:
        """
        Returns the start timestamp of the current time slot.
        For 15-minute slots, this returns the start of the current 15-minute interval.
        """
        now = datetime.now(timezone.utc)
        # Round down to the nearest 15-minute mark (0, 15, 30, or 45)
        slot_minute = (now.minute // 15) * 15
        slot_start = now.replace(minute=slot_minute, second=0, microsecond=0)
        return slot_start

    @staticmethod
    def slot_is_active(start: datetime) -> bool:
        dt = datetime.now(timezone.utc) - start
        return int(dt.total_seconds()) < 60 * 15

    @staticmethod
    def wait_until_next_slot_start(start: datetime) -> None:
        now = datetime.now(timezone.utc)
        if now >= start + timedelta(minutes=15):
            return
        dt = now - start
        time.sleep(60 * 15 - dt.total_seconds())

    def get_current_market_slug(self) -> str:
        """
        Returns the slug of the current market.
        """
        return f"btc-updown-15m-{int(self.get_current_slot_start().timestamp())}"

    def get_current_market_id(self) -> str:
        url = f"{self.base_url}/markets?slug={self.get_current_market_slug()}"
        response = requests.get(url)
        data = json.loads(response.text)
        # Response is an array with one object, extract conditionId from it
        if data and len(data) > 0:
            return data[0]["conditionId"]
        raise ValueError("No market found in response")

    def get_prev_market_slug(self) -> str:
        """
        Returns the slug of the previous market (15 minutes before current slot).
        """
        prev_slot_start = self.get_current_slot_start() - timedelta(minutes=15)
        return f"btc-updown-15m-{int(prev_slot_start.timestamp())}"

    def get_next_market_slug(self) -> str:
        """
        Returns the slug of the next market (15 minutes after current slot).
        """
        next_slot_start = self.get_current_slot_start() + timedelta(minutes=15)
        return f"btc-updown-15m-{int(next_slot_start.timestamp())}"

    def get_prev_market_id(self) -> str:
        """
        Returns the conditionId of the previous market.
        """
        url = f"{self.base_url}/markets?slug={self.get_prev_market_slug()}"
        response = requests.get(url)
        data = json.loads(response.text)
        # Response is an array with one object, extract conditionId from it
        if data and len(data) > 0:
            return data[0]["conditionId"]
        raise ValueError("No market found in response")

    def get_next_market_id(self) -> str:
        """
        Returns the conditionId of the next market.
        """
        url = f"{self.base_url}/markets?slug={self.get_next_market_slug()}"
        response = requests.get(url)
        data = json.loads(response.text)
        # Response is an array with one object, extract conditionId from it
        if data and len(data) > 0:
            return data[0]["conditionId"]
        raise ValueError("No market found in response")
from datetime import datetime, timezone
import json
import requests


class MarketFinder:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def get_current_slot_start(self) -> datetime:
        """
        Returns the start timestamp of the current time slot.
        For 15-minute slots, this returns the start of the current 15-minute interval.
        """
        now = datetime.now(timezone.utc)
        # Round down to the nearest 15-minute mark (0, 15, 30, or 45)
        slot_minute = (now.minute // 15) * 15
        slot_start = now.replace(minute=slot_minute, second=0, microsecond=0)
        return slot_start

    def slot_is_active(self, start: datetime) -> bool:
        dt = datetime.now(timezone.utc) - start
        return int(dt.total_seconds()) < 60 * 15

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
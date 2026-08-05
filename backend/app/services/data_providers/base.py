from typing import Protocol


class MarketDataProvider(Protocol):
    name: str
    supported_asset_types: frozenset[str]

    def fetch_basic_info(self, ts_code: str, asset_type: str) -> dict:
        ...

    def fetch_bars(
        self,
        ts_code: str,
        asset_type: str,
        freq: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        ...

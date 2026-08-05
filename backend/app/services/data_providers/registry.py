from .tushare_provider import TushareMarketDataProvider

_PROVIDERS = {
    "tushare": TushareMarketDataProvider(),
}


def get_market_data_provider(name="tushare"):
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise ValueError(f"Unsupported market data provider: {name}") from exc


def list_market_data_providers():
    return [
        {
            "name": provider.name,
            "supported_asset_types": sorted(provider.supported_asset_types),
        }
        for provider in _PROVIDERS.values()
    ]

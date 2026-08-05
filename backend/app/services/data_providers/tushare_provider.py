from .. import tushare_service


class TushareMarketDataProvider:
    name = "tushare"
    supported_asset_types = tushare_service.SUPPORTED_ASSET_TYPES

    def fetch_basic_info(self, ts_code, asset_type):
        return tushare_service.fetch_basic_info(ts_code, asset_type)

    def fetch_bars(self, ts_code, asset_type, freq, start_date=None, end_date=None):
        return tushare_service.fetch_bars(ts_code, asset_type, freq, start_date, end_date)

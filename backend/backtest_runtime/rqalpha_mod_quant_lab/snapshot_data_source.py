import json
from datetime import datetime

import numpy as np
import six
from rqalpha.data.base_data_source import BaseDataSource
from rqalpha.utils.datetime_func import convert_date_to_int
from rqalpha.utils.exception import RQInvalidArgument


BAR_DTYPE = np.dtype(
    [
        ("datetime", "u8"),
        ("open", "f8"),
        ("high", "f8"),
        ("low", "f8"),
        ("close", "f8"),
        ("volume", "f8"),
        ("total_turnover", "f8"),
        ("prev_close", "f8"),
        ("limit_up", "f8"),
        ("limit_down", "f8"),
    ]
)


class SnapshotDataSource(BaseDataSource):
    def __init__(self, base_config, snapshot_path):
        super().__init__(base_config)
        snapshot = json.loads(open(snapshot_path, "r", encoding="utf-8").read())
        self._snapshot_order_book_id = snapshot["instrument"]["order_book_id"]
        self._snapshot_bars = self._build_bars(snapshot["bars"])
        self._snapshot_start = datetime.strptime(snapshot["start_date"], "%Y-%m-%d").date()
        self._snapshot_end = datetime.strptime(snapshot["end_date"], "%Y-%m-%d").date()

    @staticmethod
    def _build_bars(rows):
        output = np.empty(len(rows), dtype=BAR_DTYPE)
        previous_close = np.nan
        for index, row in enumerate(rows):
            close = float(row["close"])
            reference = close if np.isnan(previous_close) else previous_close
            trade_date = datetime.strptime(row["trade_date"], "%Y-%m-%d")
            output[index] = (
                np.uint64(convert_date_to_int(trade_date)),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                close,
                float(row.get("volume") or 0),
                float(row.get("amount") or 0),
                reference,
                reference * 1.1,
                reference * 0.9,
            )
            previous_close = close
        return output

    def _is_snapshot_instrument(self, instrument):
        return instrument.order_book_id == self._snapshot_order_book_id

    def _all_day_bars_of(self, instrument):
        if self._is_snapshot_instrument(instrument):
            return self._snapshot_bars
        return super()._all_day_bars_of(instrument)

    def history_bars(
        self,
        instrument,
        bar_count,
        frequency,
        fields,
        dt,
        skip_suspended=True,
        include_now=False,
        adjust_type="pre",
        adjust_orig=None,
    ):
        if not self._is_snapshot_instrument(instrument):
            return super().history_bars(
                instrument, bar_count, frequency, fields, dt, skip_suspended, include_now, adjust_type, adjust_orig
            )
        if frequency != "1d":
            raise NotImplementedError
        bars = self._snapshot_bars
        if fields is not None:
            valid_fields = bars.dtype.names
            requested = [fields] if isinstance(fields, six.string_types) else fields
            if any(field not in valid_fields for field in requested):
                raise RQInvalidArgument(f"invalid fields: {fields}")
        index = bars["datetime"].searchsorted(np.uint64(convert_date_to_int(dt)), side="right")
        left = 0 if bar_count is None else max(0, index - bar_count)
        selected = bars[left:index]
        return selected if fields is None else selected[fields]

    def available_data_range(self, frequency):
        if frequency == "1d":
            return self._snapshot_start, self._snapshot_end
        return super().available_data_range(frequency)

    def get_dividend(self, instrument):
        if self._is_snapshot_instrument(instrument):
            return None
        return super().get_dividend(instrument)

    def get_split(self, instrument):
        if self._is_snapshot_instrument(instrument):
            return None
        return super().get_split(instrument)

    def get_ex_cum_factor(self, instrument):
        if self._is_snapshot_instrument(instrument):
            return None
        return super().get_ex_cum_factor(instrument)

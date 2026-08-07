from rqalpha.interface import AbstractMod

from .snapshot_data_source import SnapshotDataSource


class QuantLabDataMod(AbstractMod):
    def start_up(self, env, mod_config):
        env.set_data_source(SnapshotDataSource(env.config.base, mod_config.snapshot_path))

    def tear_down(self, code, exception=None):
        return None

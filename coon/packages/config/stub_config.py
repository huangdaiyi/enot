from coon.packages.config.config import ConfigFile


class StubConfig(ConfigFile):
    def __init__(self, name: str, vsn: str or None):
        super().__init__("")
        self._name = name
        self._app_vsn = vsn

    def get_compiler(self):
        raise RuntimeError('StubConfig can not be compiled')

    def read_config(self) -> dict:
        return {}
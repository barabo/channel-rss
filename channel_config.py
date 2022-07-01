import json
import logging


log = logging.getLogger(__name__)

"""
Example channels.json
{
    "channels": {
        "anaconda": {
            "cadence": 1200,
            "days_old": 30
        },
        "bioconda": {
            "cadence": 300,
            "days_old": 18
        },
        "conda-forge": {
            "cadence": 600,
            "days_old": 14
        }
    }
}
"""


class Config:
    _filename = None
    _local_folder = None
    _upstream_url = "https://conda-static.anaconda.org"

    @classmethod
    def get_file(cls):
        return cls._filename

    @classmethod
    def use_file(cls, filename):
        log.info(f"Using {filename=} for channel config.")
        try:
            with open(filename) as fd:
                _ = json.load(fd)
        except Exception as e:
            log.error(f"Failed to parse config: {filename=} - ignoring: %s", e)
            return
        cls._filename = filename

    @classmethod
    def get_cadence(cls, channel):
        config = cls.get_channels().get(channel)
        if config:
            return config.get("cadence", -1)

    @classmethod
    def get_days_old(cls, channel):
        config = cls.get_channels().get(channel)
        if config:
            return config.get("days_old", -1)

    @classmethod
    def get_channels(cls):
        with open(cls._filename) as fd:
            try:
                return json.load(fd).get("channels")
            except Exception as e:
                log.error(f"Failed to read config filename={cls._filename}: %s", e)

    @classmethod
    def get_local_folder(cls):
        return cls._local_folder

    @classmethod
    def set_local_folder(cls, folder):
        log.info(f"setting local folder to {folder}")
        cls._local_folder = folder

    @classmethod
    def get_upstream_url(cls):
        return cls._upstream_url

    @classmethod
    def set_upstream_url(cls, url):
        log.info(f"setting upstream url to {url}")
        cls._upstream_url = url

#!/usr/bin/env python3 -u
import click
import json
import logging
import sys
import threading
import time

from channel_config import Config
from downloader import Downloader
import rss
from scheduler import Scheduler

log = logging.getLogger("cli.py")

REPO_URL = "https://github.com/barabo/channel-rss"


def init_logging(level="INFO", colorize=True):
    # TODO: support logging to a named file.
    FORMAT = "%(asctime)s:%(levelname)s:%(filename)s:%(lineno)d:%(threadName)s:%(msg)s"
    if colorize:
        _COLORIZE = lambda code, message: f"\033[1;{code}m{message}\033[1;0m"
        logging.addLevelName(logging.DEBUG, f"{_COLORIZE(34, 'DEBUG')}")
        logging.addLevelName(logging.INFO, f"{_COLORIZE(37, 'INFO')}")
        logging.addLevelName(logging.WARNING, f"{_COLORIZE(31, 'WARNING')}")
        logging.addLevelName(logging.ERROR, f"{_COLORIZE(41, 'ERROR')}")
    logging.basicConfig(level=level, format=FORMAT)


@click.command(
    epilog=f"""\b
 0/ - Source: {REPO_URL}
<Y
/ \\
"""
)
@click.option(
    "--config",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Channel configuration json.",
)
@click.option(
    "--local-path",
    required=True,
    type=click.Path(file_okay=False),
    help="Local directory for downloaded repodata.",
)
@click.option(
    "--colorize", default=True, show_default=True, help="Colorize logging output."
)
@click.option(
    "--level",
    default="INFO",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    help="Lowest logging level shown.",
)
@click.option(
    "--concurrent-downloads",
    default=32,
    show_default=True,
    type=click.IntRange(1, 1000),
    help="The maximum allowed number of concurrent downloads.",
)
def main(config, local_path, colorize, level, concurrent_downloads):
    init_logging(level, colorize)
    Config.use_file(config)
    Config.set_local_folder(local_path)

    def update_callback(result):
        channel = result["channel"]
        threshold = Config.get_days_old(channel)
        channeldata_path = result["filename"]
        rss_path = channeldata_path.rsplit("/", 1)[0] + "/rss.xml"
        with open(channeldata_path, "r") as fin, open(rss_path, "w") as out:
            out.write(rss.get_rss(channel, json.load(fin), threshold))

    downloader = threading.Thread(
        target=Downloader.run,
        args=(concurrent_downloads,),
        daemon=True,
        name="Downloader()",
    )
    downloader.start()
    schedulers = {}
    while not time.sleep(5):
        if not downloader.is_alive():
            log.error("Downloader thread has died - exiting")
            return 1
        for channel in Config.get_channels():
            if channel not in schedulers:
                schedulers[channel] = Scheduler(channel, update_callback)
            schedulers[channel].observed()


if __name__ == "__main__":
    sys.exit(main())

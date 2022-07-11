import filecmp
import gzip
import io
import json
import logging
import os
import pickle
import queue
import shutil
import requests
import threading
import time

from channel_config import Config

log = logging.getLogger(__name__)


class Downloader:
    """Maintains concurrent downloads as requested by Schedulers."""

    _beautify = True
    _download_limit = None
    _schedule = queue.PriorityQueue(0)

    @classmethod
    def run(cls, download_limit, beautify=True):
        assert threading.current_thread().name.startswith("Downloader")

        if download_limit < 1:
            raise RuntimeError(f"{download_limit=} must be > 0")
        cls._download_limit = download_limit
        cls._beautify = beautify

        schedule = cls._schedule
        inflight = threading.BoundedSemaphore(download_limit)

        log.info(f"started (allowing {download_limit} concurrent downloads)")
        while True:
            if schedule.qsize() == 0:
                with schedule.not_empty:
                    log.info("waiting for work")
                    schedule.not_empty.wait()
            log.debug(f"jobs detected")

            # Drain the queue while we are behind.
            while schedule.queue and schedule.queue[0][0] < time.time():
                behind = int(time.time() - schedule.queue[0][0])
                if behind > 5:
                    log.warning(f"scheduled download starting {behind} seconds late")
                next_download = schedule.get_nowait()
                channel, notifier = next_download[1]["args"]
                log.info(f"Starting download: {channel}")
                threading.Thread(
                    target=cls.download,
                    name=f"DownloadWorker({channel})",
                    args=(channel, notifier, inflight,),
                ).start()

            # Defer downloads while the next scheduled is in the future.
            while schedule.queue and schedule.queue[0][0] > time.time():
                to_wait = int(schedule.queue[0][0] - time.time())
                if to_wait > 30 and to_wait % 30 == 0:
                    log.info(f"next job starts in {to_wait} seconds")
                time.sleep(1)

    @classmethod
    def _download(cls, channel, result):
        """Updates repodata.json for a channel."""
        url = f"{Config.get_upstream_url()}/{channel}/channeldata.json"
        channel_folder = f"{Config.get_local_folder()}/{channel}"
        new_download = f"{channel_folder}/channeldata.json.gz.new"
        compressed = f"{channel_folder}/channeldata.json.gz"
        channeldata = f"{channel_folder}/channeldata.json"
        inflated = "f{channeldata}.inflated"

        exists = os.path.exists

        if not exists(channel_folder):
            log.info(f"making channel folder: {channel_folder}")
            os.makedirs(channel_folder)

        with requests.get(url, stream=True, timeout=300) as upstream:
            result["download"] = Downloader._get_response_details(upstream)
            upstream.raise_for_status()

            # Download the file.
            with open(new_download, "wb") as local:
                shutil.copyfileobj(upstream.raw, local, length=2 ** 24)  # 16MB

            # Quit early if the downloaded file is not new or is not needed.
            if (
                exists(channeldata)
                and exists(compressed)
                and filecmp.cmp(compressed, new_download, shallow=False)
            ):
                os.unlink(new_download)
                return

            # Update channeldata!
            result["inflate_start"] = time.time()
            with gzip.open(new_download, "rt") as src, open(inflated, "w") as dest:
                shutil.copyfileobj(src, dest, length=2 ** 24)  # 16MB
            result["inflate_complete"] = time.time()

            # Replace the old channeldata with the new.
            shutil.move(inflated, channeldata)
            result["updated"] = time.time()
            result["filename"] = channeldata

    @classmethod
    def download(cls, channel, scheduler_inbox, download_gate):
        assert threading.current_thread().name.startswith("DownloadWorker")

        result = {"scheduled_start": time.time()}
        try:
            # TODO: export the number of concurrent downloads via download_gate.count
            with download_gate:
                result["download_lock_acquired"] = time.time()
                blocked_duration = time.time() - result["scheduled_start"]
                if not download_gate._value:
                    log.warning(
                        f"limit reached: {cls._download_limit} concurrent downloads"
                    )
                if blocked_duration > 1:
                    log.warning(
                        f"waited {int(blocked_duration)}s to acquire download lock"
                    )
                cls._download(channel, result)
            result["completed"] = time.time()
            inflight = cls._download_limit - download_gate._value
            log.debug(f"{inflight} inflight downloads")
        except Exception as e:  # TODO: handle specific expected types
            result["exception"] = e
            log.warning(f"exception seen: {repr(e)}")
            log.exception(e)
        finally:
            # Notify the scheduler thread that the work is done.
            scheduler_inbox.put(result)

    @classmethod
    def schedule(cls, channel, timestamp, notifier):
        assert threading.current_thread().name.startswith("Scheduler")

        upcoming = int(timestamp - time.time())
        if upcoming < 1:
            log.info("will refresh ASAP")
        else:
            log.debug(f"will refresh in {upcoming} seconds")

        cls._schedule.put((timestamp, {"args": (channel, notifier)},))

    @classmethod
    def _get_response_details(cls, response):
        """Returns the interesting parts of the download response."""
        selected = {
            key: response.__dict__[key]
            for key in response.__dict__.keys()
            & {
                "status_code",
                "headers",
                "url",
                "reason",
                "elapsed",
                "encoding",
                "request",
            }
        }
        if "request" in selected:
            selected["request"] = {
                key: selected["request"].__dict__[key]
                for key in selected["request"].__dict__.keys()
                & {"method", "url", "headers",}
            }
        return selected

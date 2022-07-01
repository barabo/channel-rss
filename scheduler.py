import collections
import logging
import queue
import random
import threading
import time

import downloader as upstream
from channel_config import Config

log = logging.getLogger(__name__)


class Scheduler(threading.Thread):
    allowed_schedule_drift = 5  # seconds / interval (for schedule fuzzing)

    def __init__(self, channel, update_callback=None):
        super().__init__(
            target=self.run,
            name=f"Scheduler({channel})",
            daemon=True,
        )
        log.info(f"Scheduler created for {channel}")
        self.attempt = 0
        self.channel = channel
        self.previous_downloads = collections.deque([])
        self.last_observed = time.time()
        self._update_callback = update_callback
        log.debug(f"Starting scheduler for {channel}")
        self.start()

    def _get_history(self, status_code):
        for previous_download in self.previous_downloads:
            download = previous_download.get("download")
            if not download:
                continue
            if status_code == download.get("status_code"):
                yield previous_download

    def get_median_duration(self):
        median = 0
        history = [
            x["completed"] - x["scheduled_start"] for x in self._get_history(200)
        ]
        if history:
            history.sort()
            median = history[len(history) // 2]
        return median

    def get_last_success(self):
        for download in self._get_history(200):
            return download

    def get_last_update(self):
        for success in self._get_history(200):
            if success.get("inflate_complete"):
                return success

    def _get_observation_time_now(self):
        now = time.time()
        if now < self.last_observed:
            log.error("detected clock jump - pretending it didn't happen")
        return now

    def observed(self):
        assert threading.current_thread().getName() == "MainThread"
        self.last_observed = self._get_observation_time_now()
        if not self.is_alive:
            log.error(f"OBSERVED A DEAD SCHEDULER: {self.name}")

    def is_observed(self):
        now = self._get_observation_time_now()
        unobserved = min(now - self.last_observed, 0)
        return unobserved < 60

    def run(self):
        def fuzz(seconds):
            time.sleep(random.random() * seconds)

        while self.is_alive() and self.is_observed():
            # Detect a disabled channel.
            cadence = Config.get_cadence(self.channel)
            if cadence <= 0:
                log.debug(f"{self.name} disabled with {cadence=}")
                fuzz(20)
                continue

            # Determine when the last download completed.
            last_success = self.get_last_success()
            if not last_success:
                # Sleep randomly until the first success to fuzz the threads.
                fuzz(10)
                # Suggest that this thread is due to be scheduled right away.
                since_last = cadence
            else:
                since_last = time.time() - last_success["completed"]
                if since_last < 0:
                    log.warning(f"possible clock jump - ignoring {since_last=}sec")
                    since_last = cadence

            # Determine when the next download should start.
            typical_duration = self.get_median_duration()
            if typical_duration > cadence:
                log.error(f"{typical_duration=} greater than {cadence=}")
            drift = random.random() * self.allowed_schedule_drift
            should_start_in = cadence - since_last - typical_duration - drift

            # This happens when we have been failing for a long time.
            if should_start_in < -cadence:
                log.error(
                    f"{self.name}: {should_start_in=}sec is far behind {cadence=}sec"
                )
                # TODO: what to do to not make things worse when this happens??

            # Only schedule the download when we're finally close to the starting time.
            if should_start_in < 10:
                if typical_duration > 20:
                    log.warning(f"JUMBO: median={int(typical_duration)}s to clone")

                download_status = queue.Queue(1)
                self.attempt += 1
                upstream.Downloader.schedule(
                    self.channel,
                    time.time() + should_start_in,
                    download_status,
                )
                try:
                    download_id = f"download({self.attempt})"
                    log.info(f"{download_id} scheduled - waiting for result")

                    result = download_status.get(timeout=cadence * 5)

                    result["channel"] = self.channel
                    result["download_id"] = download_id
                    log.info(f"{download_id} result available")
                    if result.get("updated"):
                        log.info(f"{download_id} updated")
                        if self._update_callback:
                            threading.Thread(
                                name=f"Updater({self.channel})",
                                target=self._update_callback,
                                args=(result,),
                                daemon=True,
                            ).start()

                    # Update history.
                    self.previous_downloads.appendleft(result)
                    if len(self.previous_downloads) > 100:
                        log.debug("popping history")
                        self.previous_downloads.pop()

                except queue.Empty as e:
                    log.error(f"Download did not complete")
            else:
                fuzz(2)  # sleep a random amount to fuzz the scheduler threads

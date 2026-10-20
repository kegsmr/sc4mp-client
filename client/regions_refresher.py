"""RegionsRefresher thread: downloads updated regions while the game
runs."""

from __future__ import annotations

import math
import random
import shutil
import threading as th
from pathlib import Path

from core.util import (
    sanitize_directory_name,
    sanitize_relpath,
    set_thread_name,
)
from client import state
from client.constants import SC4MP_ARROW
from client.errors import show_error
from client.sc4 import prep_region_config
from client.utils import directory_size, purge_directory


class RegionsRefresher(th.Thread):

    def __init__(self, ui, server):

        th.Thread.__init__(self)

        self.ui = ui
        self.server = server

        self.setDaemon(True)

    def run(self):

        while state.sc4mp_game_launcher.game_running:

            try:

                set_thread_name("RrThread", enumerate=False)

                # Report
                self.report("", "Refreshing regions...")

                # Set destination
                destination = Path(state.SC4MP_LAUNCHPATH) / "Regions"

                # Purge the region directories
                for region in self.server.regions:
                    purge_directory(destination / region)

                # Receive file table
                with self.server.socket() as s:
                    file_table = s.regions_table()

                # Get total download size
                size = sum([entry[1] for entry in file_table])

                # Total size downloaded
                size_downloaded = 0

                # Download percent
                percent = 0

                # Set loading bar at 0%
                self.report_progress("Refreshing regions... (0%)", 0, 100)

                # Prune file table as necessary
                ft = []
                for entry in file_table:

                    # Get necessary values from entry
                    checksum = sanitize_directory_name(entry[0])
                    filesize = entry[1]
                    relpath = Path(entry[2])

                    # Get path of cached file
                    t = Path(state.SC4MP_LAUNCHPATH) / "_Cache" / checksum

                    # Use the cached file if it exists and has the same size, otherwise append the entry to the new file table
                    if t.exists() and t.stat().st_size == filesize:

                        # Report
                        print(f'- using cached "{checksum}"')

                        # Set the destination
                        d = sanitize_relpath(Path(destination), relpath)

                        # Display current file in UI
                        try:
                            self.ui.progress_label["text"] = d.name  # .relative_to(destination)
                            self.ui.duration_label["text"] = f"Cache {SC4MP_ARROW} SC4"  # "(cached)"
                        except Exception:
                            pass

                        # Create the destination directory if necessary
                        d.parent.mkdir(parents=True, exist_ok=True)

                        # Delete the destination file if it exists
                        d.unlink(missing_ok=True)

                        # Copy the cached file to the destination
                        shutil.copy(t, d)

                        # Update progress bar
                        size_downloaded += filesize
                        old_percent = percent
                        percent = math.floor(100 * (size_downloaded / (size + 1)))
                        if percent > old_percent:
                            self.report_progress(f"Refreshing regions... ({percent}%)", percent, 100)

                    else:

                        # Append to new file table
                        ft.append(entry)

                file_table = ft

                # Receive files
                with self.server.socket() as s:

                    for entry in s.regions_data(file_table):

                        # Get necessary values from entry
                        checksum = sanitize_directory_name(entry[0])
                        filesize = entry[1]
                        relpath = Path(entry[2])
                        chunks = entry[3]

                        # Report
                        print(f'- caching "{checksum}"...')

                        # Set the destination
                        d = sanitize_relpath(Path(destination), relpath)

                        # Display current file in UI
                        try:
                            self.ui.progress_label["text"] = d.name  # .relative_to(destination)
                            self.ui.duration_label["text"] = f"Server {SC4MP_ARROW} SC4"  # "(downloading)"
                        except Exception:
                            pass

                        # Set path of cached file
                        t = Path(state.SC4MP_LAUNCHPATH) / "_Cache" / checksum

                        # Create the destination directory if necessary
                        d.parent.mkdir(parents=True, exist_ok=True)

                        # Delete the destination file if it exists
                        d.unlink(missing_ok=True)

                        # Delete the cache file if it exists
                        t.unlink(missing_ok=True)

                        # Delete cache files if cache too large to accomadate the new cache file
                        cache_directory = Path(state.SC4MP_LAUNCHPATH) / "_Cache"
                        while any(cache_directory.iterdir()) and directory_size(cache_directory) > (1000000 * int(state.sc4mp_config["STORAGE"]["cache_size"])) - filesize:
                            random_cache = random.choice(list(cache_directory.iterdir()))
                            random_cache.unlink()

                        # Receive the file. Write to both the destination and cache
                        filesize_read = 0
                        with d.open("wb") as dest, t.with_name(t.name + ".tmp").open("wb") as cache:
                            for chunk in chunks:
                                for file in [dest, cache]:
                                    file.write(chunk)
                                filesize_read += len(chunk)
                                size_downloaded += len(chunk)
                                old_percent = percent
                                percent = math.floor(100 * (size_downloaded / (size + 1)))
                                if percent > old_percent:
                                    self.report_progress(f"Refreshing regions... ({percent}%)", percent, 100)
                        t.with_name(t.name + ".tmp").replace(t)  # only cache the file once its checksum has been verified

                self.report_progress("Refreshing regions... (100%)", 100, 100)

                # Report
                self.report("", "Refreshing regions...")

                # Prep region configs
                for region in self.server.regions:
                    prep_region_config(destination / region / "region.ini")

                # Report
                self.report("", "Done.")

                break

            except Exception as e:

                # if self.ui != None:
                #    self.ui.withdraw()

                show_error("An error occurred while refreshing regions.\n\n" + str(e), no_ui=True)

    def report(self, prefix, text):

        if self.ui is not None:
            self.ui.label['text'] = text
            self.ui.progress_bar.start(2)
            self.ui.progress_bar['mode'] = "indeterminate"
            self.ui.progress_bar['maximum'] = 100
        print(prefix + text)
        # time.sleep(1) # for testing

    def report_progress(self, text, value, maximum):

        if self.ui is not None:
            self.ui.label['text'] = text
            self.ui.progress_bar.stop()
            self.ui.progress_bar['mode'] = "determinate"
            self.ui.progress_bar['value'] = value
            self.ui.progress_bar['maximum'] = maximum
        print(text)

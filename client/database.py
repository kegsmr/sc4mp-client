"""Background thread that keeps the server database saved to disk."""

from __future__ import annotations

import threading as th
import time
from pathlib import Path

from core.database import Database
from core.util import set_thread_name
from client.constants import SC4MP_DELAY
from client.errors import fatal_error, show_error


class DatabaseManager(th.Thread, Database):

    def __init__(self, filename: Path):

        th.Thread.__init__(self)
        Database.__init__(self, filename)

        self.end = False

    def run(self):

        try:

            set_thread_name("DbThread")

            while not self.end:
                try:
                    time.sleep(SC4MP_DELAY)
                    self.update_json()
                except Exception as e:
                    show_error(f"An unexpected error occurred in the database thread.\n\n{e}")

        except Exception:

            fatal_error()

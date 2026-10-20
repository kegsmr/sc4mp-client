"""Logger that timestamps console output and copies it to the log file."""

from __future__ import annotations

import inspect
import sys
import threading as th
from datetime import datetime
from pathlib import Path

from client.constants import SC4MP_LOG_PATH


class Logger:

    def __init__(self):

        self.terminal = sys.stdout
        if self.terminal is not None:
            # characters the console can't show (eg. emoji on a cp1252 console)
            # are printed as "?"
            self.terminal.reconfigure(errors="replace")
        self.log = Path(SC4MP_LOG_PATH)
        self.log.unlink(missing_ok=True)

    def write(self, message):

        output = message

        if message != "\n":

            # Timestamp
            timestamp = datetime.now().strftime("[%H:%M:%S] ")

            # Label
            label = "[SC4MP/" + th.current_thread().getName() + "] "
            for item in inspect.stack()[1:]:
                try:
                    label += "(" + item[0].f_locals["self"].__class__.__name__ + ") "
                    break
                except Exception:
                    pass

            # Type and color
            type = "[INFO] "
            color = '\033[90m '
            TYPES_COLORS = [
                ("[INFO] ", '\033[90m '),  # '\033[94m '
                ("[PROMPT]", '\033[01m '),
                ("[WARNING] ", '\033[93m '),
                ("[ERROR] ", '\033[91m '),
                ("[FATAL] ", '\033[91m ')
            ]
            for index in range(len(TYPES_COLORS)):
                current_type = TYPES_COLORS[index][0]
                current_color = TYPES_COLORS[index][1]
                if message[:len(current_type)] == current_type:
                    message = message[len(current_type):]
                    type = current_type
                    color = current_color
                    break
            if th.current_thread().getName() == "Main" and type == "[INFO] ":
                color = '\033[00m '

            # Assemble
            output = color + timestamp + label + type + message

        # Print
        if self.terminal is not None:
            self.terminal.write(output)
        with open(self.log, "a", encoding="utf-8") as log:
            log.write(output)
            log.close()

    def flush(self):

        self.terminal.flush()

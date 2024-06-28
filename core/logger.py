from __future__ import annotations
import logging
import os
import time
from bisect import bisect
from logging import (
    Filter,
    Formatter,
    LogRecord,
    Logger,
    StreamHandler,
    FileHandler,
)


class Colors:
    """
    ANSI color codes
    https://gist.github.com/rene-d/9e584a7dd2935d0f461904b9f2950007
    """

    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[0;33m"
    BLUE = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[0;37m"
    DARK_GRAY = "\033[0;90m"

    RESET = "\033[0m"


COLORS = Colors()
EXCEPTION_COLOR = COLORS.RED

LOG_PATH = f"sc4mpserver-{time.strftime('%Y%m%d-%H%M%S')}.log"

# Default date format for logged messages
DATE_FORMAT = "%H:%M:%S"

# Default format for logged messages
# see https://docs.python.org/3/library/logging.html#logrecord-attributes
# {className} is a custom token and requires passing kw extra={'className': ... } to logging calls
# this is handled by instantiating class-specific LoggingAdapters in class __init__()s
# A custom filter sets a default value for logging calls without extra={} arg
DEFAULT_MSG = "[{asctime}] [SC4MP/{threadName}] ({className}) [{levelname}]"

# Set log-level specific message format here.
BASE_FORMATS = {
    logging.DEBUG: f"{DEFAULT_MSG} {{msg}}",
    logging.INFO: f"{DEFAULT_MSG} {{msg}}",
    logging.WARNING: f"{DEFAULT_MSG} {{msg}}",
    logging.ERROR: f"{DEFAULT_MSG} {{msg}}",
    logging.CRITICAL: f"{DEFAULT_MSG} {{msg}}",
}
# Set log-level colors here
LEVEL_COLORS = {
    logging.DEBUG: COLORS.DARK_GRAY,
    logging.INFO: COLORS.WHITE,
    logging.WARNING: COLORS.YELLOW,
    logging.ERROR: COLORS.MAGENTA,
    logging.CRITICAL: COLORS.RED,
}
COLOR_FORMATS = {
    level: f"{LEVEL_COLORS[level]}{BASE_FORMATS[level]}{COLORS.RESET}"
    for level in BASE_FORMATS
}


class ColorExceptionFormatter(Formatter):
    """
    Subclass of logging.Formatter which overides the formatException() and
    formatStack(), and format() methods to optionally add formatting (color) to the output.
    """

    def __init__(self, *args, exc_color=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exc_color = exc_color

    def formatException(self, exc_info) -> str:
        if not self.exc_color:
            return super().formatException(exc_info)
        return self.exc_color + super().formatException(exc_info) + COLORS.RESET

    def formatStack(self, stack_info: str) -> str:
        if not self.exc_color:
            return stack_info
        return self.exc_color + stack_info + COLORS.RESET

    def format(self, record: LogRecord) -> str:
        """
        Overridden here because the default implementation caches
        the exception formatting which is not what we want.
        """
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s


class LevelFormatter(Formatter):
    """
    Multi-level formatter from
    https://stackoverflow.com/a/68154386/8098007
    """

    def __init__(self, formats: dict[int, str], exc_color: str = None, **kwargs):
        super().__init__()

        if "fmt" in kwargs:
            raise ValueError(
                "Format string must be passed to level-surrogate formatters, "
                "not this one"
            )

        self.formats = sorted(
            (level, ColorExceptionFormatter(fmt, exc_color=exc_color, **kwargs))
            for level, fmt in formats.items()
        )
        self.exc_color = exc_color

    def format(self, record: LogRecord) -> str:
        """Delegates the format call to a level-specific formatter"""
        idx = bisect(self.formats, (record.levelno,), hi=len(self.formats) - 1)
        level, formatter = self.formats[idx]
        return formatter.format(record)


class ClassnameFilter(Filter):
    """
    This (non)filter provides a default value for 'className' if the inspected
    LogRecord does not have the attribute.

    Note: Python 3.10 adds a 'defaults' parameter to the Formatter class which
    would make this unnecessary.
    """

    def filter(self, record: LogRecord) -> bool:
        if not hasattr(record, "className"):
            record.className = ""
        return True


def build_logger(verbose: bool = False) -> Logger:
    """Returns the custom sc4mp logger"""
    # workaround to enable ANSI color in windows terminals
    # https://stackoverflow.com/a/64222858/8098007
    os.system("")

    # build formatters
    color_formatter = LevelFormatter(
        formats=COLOR_FORMATS, exc_color=EXCEPTION_COLOR, datefmt=DATE_FORMAT, style="{"
    )
    plain_formatter = LevelFormatter(
        formats=BASE_FORMATS, datefmt=DATE_FORMAT, style="{"
    )

    # build handlers
    terminal_handler = StreamHandler()
    terminal_handler.setFormatter(color_formatter)
    file_handler = FileHandler(LOG_PATH)
    file_handler.setFormatter(plain_formatter)

    # build logger
    logger = logging.getLogger(__name__)
    logger.addHandler(file_handler)
    logger.addHandler(terminal_handler)
    logger.addFilter(ClassnameFilter())

    # set log level
    if verbose:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")

    return logger

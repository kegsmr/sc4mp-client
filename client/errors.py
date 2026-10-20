"""Error handling: the client exception, error/warning messages and
fatal-error shutdown."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tkinter as tk
import traceback
from tkinter import messagebox

from core.util import has_powershell
from client import state
from client.constants import SC4MP_LOG_PATH, SC4MP_TITLE


def cleanup():

    state.sc4mp_servers_database.end = True


def show_error(e, no_ui=False):
    """Shows an error message in the console and optionally in the UI."""
    message = None
    if isinstance(e, str):
        message = e
    else:
        message = str(e)

    print(f"[ERROR] {message}\n\n{traceback.format_exc()}")

    if not no_ui:
        if state.sc4mp_ui is not None:
            if state.sc4mp_ui is True:
                tk.Tk().withdraw()
                close_splash()
            messagebox.showerror(SC4MP_TITLE, message)


def startfile(filename):
    syst = platform.system()
    if syst == "Windows":
        os.startfile(filename)
    else:
        if syst == "Darwin":
            opener = "open"
        else:
            opener = "xdg-open"  # Linux
        subprocess.call([opener, filename])


def open_logs():
    if has_powershell():
        subprocess.Popen([
            "cmd.exe", "/c", "start", "cmd.exe", "/k",
            "@echo off && powershell -NoProfile -ExecutionPolicy Bypass "
            f"-Command $Host.UI.RawUI.WindowTitle = \"{SC4MP_TITLE}\"; "
            "gc sc4mpclient.log -Encoding UTF8 -Wait -Tail 1000"
        ])
    else:
        startfile(SC4MP_LOG_PATH)


def fatal_error():
    """Shows a fatal error message in the console and the UI. Exits the program."""

    message = f"A fatal error occurred.\n\n{traceback.format_exc()}"

    print(f"[FATAL] {message}")

    if state.sc4mp_ui is not None:
        if state.sc4mp_ui is True:
            tk.Tk().withdraw()
            close_splash()
        messagebox.showerror(SC4MP_TITLE, message)
        open_logs()

    try:
        cleanup()
    except Exception as e:
        show_error(e, no_ui=True)

    sys.exit()


def show_warning(e):
    """Shows a warning in the console and the UI."""
    message = None
    if isinstance(e, str):
        message = e
    else:
        message = str(e)

    print(f"[WARNING] {message}")

    if state.sc4mp_ui is not None:
        if state.sc4mp_ui is True:
            tk.Tk().withdraw()
            close_splash()
        messagebox.showwarning(SC4MP_TITLE, message)


def close_splash():

    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass


class ClientException(Exception):

    def __init__(self, message, *args):

        super().__init__(args)
        self.message = message

    def __str__(self):

        return self.message

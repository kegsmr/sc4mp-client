"""SC4MP Launcher: entry point.

Run with `python sc4mpclient.py`. The launcher itself is in the `client`
package.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from core.util import process_count, set_thread_name
from client import state
from client.config import create_subdirectories, load_config, load_database
# SC4MP_VERSION and SC4MP_GITHUB_REPO are not used here, but setup.py,
# publish.py and versioning.py import them from this file
from client.constants import (  # noqa: F401
    SC4MP_GITHUB_REPO,
    SC4MP_TITLE,
    SC4MP_URL_PREFIX,
    SC4MP_VERSION,
)
from client.errors import (
    cleanup,
    ClientException,
    close_splash,
    fatal_error,
    show_error,
)
from client.logger import Logger
from client.server import Server
from client.server_loader import ServerLoader
from client.ui.main_window import UI
from client.ui.server_loader import ServerLoaderUI
from client.updater import check_updates
from client.utils import get_arg_value, get_image_pids, process_exists

sc4mp_args = sys.argv


def main():
    """The main function.

    Arguments:
        None

    Returns:
        None
    """

    try:

        # URL launch behavior
        url_launch = len(sc4mp_args) > 1 and sc4mp_args[1] \
            .startswith(SC4MP_URL_PREFIX)
        url_launch_exit_after = True

        # Exit if already runnning (unless launching using URL)
        if "-allow-multiple" not in sc4mp_args:
            try:
                count = process_count("sc4mpclient.exe")
                if count is not None and count > 1:
                    if url_launch:
                        url_launch_exit_after = False
                        if process_exists("simcity 4.exe"):
                            return
                        else:
                            try:
                                our_pid: int = os.getpid()
                                pids: list[int] = get_image_pids("sc4mpclient.exe")
                                if pids is not None:
                                    if our_pid in pids:
                                        pids.remove(our_pid)
                                    for pid in pids:
                                        command = f"TASKKILL /F /PID {pid}"
                                        if subprocess.call(command, shell=True) != 0:
                                            return
                            except Exception:
                                return
                    else:
                        tk.Tk().withdraw()
                        close_splash()
                        messagebox.showerror(
                            title=SC4MP_TITLE,
                            message="SC4MP Launcher is already running!"
                        )
                        return
            except Exception:
                pass

        # Set working directory
        exec_path = Path(sys.executable)
        exec_file = exec_path.name
        exec_dir = exec_path.parent
        if exec_file == "sc4mpclient.exe":
            os.chdir(exec_dir)

        # Output
        sys.stdout = Logger()
        set_thread_name("Main", enumerate=False)

        # Title
        print(SC4MP_TITLE)

        # "-force-update"/"-skip-update" flags
        state.sc4mp_force_update = "-force-update" in sc4mp_args
        state.sc4mp_skip_update = "-skip-update" in sc4mp_args \
            or (len(sc4mp_args) > 1 and not state.sc4mp_force_update)

        # "-no-ui" flag
        state.sc4mp_ui = "-no-ui" not in sc4mp_args

        # "-exit-after" flag
        state.sc4mp_exit_after = "-exit-after" in sc4mp_args

        # "--host" argument
        state.sc4mp_host = None
        if "--host" in sc4mp_args:
            try:
                state.sc4mp_host = get_arg_value("--host", sc4mp_args)
            except Exception as e:
                raise ClientException("Invalid arguments.") from e

        # "--port" argument
        state.sc4mp_port = None
        if "--port" in sc4mp_args:
            try:
                state.sc4mp_port = int(get_arg_value("--port", sc4mp_args))
            except Exception as e:
                raise ClientException("Invalid arguments.") from e

        # "--password" argument
        state.sc4mp_password = None
        if "--password" in sc4mp_args:
            try:
                state.sc4mp_password = get_arg_value("--password", sc4mp_args)
            except Exception as e:
                raise ClientException("Invalid arguments.") from e

        # Launch using URL
        if url_launch:
            try:
                url = sc4mp_args[1]
                url = url.replace(SC4MP_URL_PREFIX, "", 1)
                if url.endswith("/"):
                    url = url[:-1]
                url = url.split(":")
                if len(url) > 1:
                    state.sc4mp_host = ":".join(url[:-1])
                    state.sc4mp_port = int(url[-1])
                else:
                    state.sc4mp_host = url[0]
                    state.sc4mp_port = 7240
                state.sc4mp_exit_after = url_launch_exit_after
            except Exception:
                show_error(
                    "Invalid URL.\n\n"
                    "URLs must adhere to:\nsc4mp://<host>:<port>\n\n"
                    f"URL given:\n{sc4mp_args[1]}"
                )
                return

        # Prep
        prep()

        # Client
        if state.sc4mp_ui:
            if state.sc4mp_host is not None and state.sc4mp_port is not None:
                if state.sc4mp_exit_after:
                    state.sc4mp_ui = tk.Tk()
                    state.sc4mp_ui.withdraw()
                else:
                    state.sc4mp_ui = UI()
                server = Server(state.sc4mp_host, state.sc4mp_port)
                server.password = state.sc4mp_password
                ServerLoaderUI(server)
            else:
                state.sc4mp_ui = UI()
            close_splash()
            state.sc4mp_ui.mainloop()
        else:
            state.sc4mp_ui = None
            if state.sc4mp_host is None or state.sc4mp_port is None:
                print("[PROMPT] Connect to server:")
            if state.sc4mp_host is None:
                state.sc4mp_host = input("[PROMPT] - Enter server address... ")
            if state.sc4mp_port is None:
                state.sc4mp_port = int(
                    input("[PROMPT] - Enter server port... ")
                )
            server = Server(state.sc4mp_host, state.sc4mp_port)
            server.fetch()
            if state.sc4mp_password is None and server.password_enabled:
                state.sc4mp_password = input(
                    "[PROMPT] - Enter server password... "
                )
            server.password = state.sc4mp_password
            ServerLoader(None, server).run()

    except KeyboardInterrupt:

        pass

    except Exception:

        # Fatal error
        fatal_error()

    # Cleanup
    print("Shutting down...")
    cleanup()


def prep():
    """Prepares the client to launch."""

    load_config()
    check_updates()
    create_subdirectories()
    load_database()


if __name__ == '__main__':
    main()

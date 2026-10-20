"""Launcher self-updates and GitHub release info."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading as th
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path

from core.util import set_thread_name, unformat_version
from client import state
from client.constants import (
    SC4MP_BUFFER_SIZE,
    SC4MP_GITHUB_REPO,
    SC4MP_ICON,
    SC4MP_VERSION,
)
from client.errors import (
    ClientException,
    close_splash,
    fatal_error,
    show_error,
)
from client.ui.updater import UpdaterUI
from client.utils import purge_directory


def check_updates():

    if state.sc4mp_config["GENERAL"]["auto_update"] and (not state.sc4mp_skip_update):

        print("Checking for updates...")

        try:

            # Get the path of the executable file which is currently running
            exec_path = Path(sys.executable)
            exec_file = exec_path.name
            exec_dir = exec_path.parent

            # Only update if running a Windows distribution
            if state.sc4mp_force_update or exec_file == "sc4mpclient.exe":

                # Get latest release info
                latest_release_info = get_release_info()

                # Download the update if the version is newer
                latest_version = unformat_version(latest_release_info["tag_name"])
                if state.sc4mp_force_update or latest_version > unformat_version(SC4MP_VERSION):

                    # Local function for update thread
                    def update(ui=None):

                        try:

                            set_thread_name("UpdtThread", enumerate=False)

                            # Function to pause updates when user presses <ESC>
                            def pause():
                                while ui.pause:
                                    time.sleep(.1)

                            # Function to write to console and update ui
                            def report(message):
                                print(message)
                                ui.label["text"] = message

                            # Change working directory to the one where the
                            # executable can be found
                            if exec_file == "sc4mpclient.exe":
                                os.chdir(exec_dir)

                            # Purge update directory
                            try:
                                if os.path.exists("update"):
                                    purge_directory(Path("update"))
                            except Exception:
                                pass

                            # Delete uninstaller if exists
                            try:
                                for filename in ["unins000.dat", "unins000.exe"]:
                                    if os.path.exists(filename):
                                        os.unlink(filename)
                            except Exception:
                                pass

                            # Give the user a chance to cancel the update
                            if ui is not None:
                                report("Preparing update...")
                                time.sleep(3)

                            # Pause if necessary
                            pause()

                            # Loop until download is successful
                            while True:

                                try:

                                    # Update UI
                                    report("Downloading update...")

                                    # Pause if necessary
                                    pause()

                                    # Get download URL
                                    download_url = None
                                    for asset in latest_release_info["assets"]:
                                        installer_prefix = "sc4mp-client-installer-windows"
                                        if asset["name"].startswith(installer_prefix):
                                            download_url = asset["browser_download_url"]
                                            destination = os.path.join("update", asset["name"])
                                            break

                                    # Raise an exception if the download URL was not found
                                    if download_url is None:
                                        raise ClientException(
                                            "The correct release asset was not found."
                                        )

                                    # Pause if necessary
                                    pause()

                                    # Prepare destination
                                    os.makedirs("update", exist_ok=True)
                                    if os.path.exists(destination):
                                        os.unlink(destination)

                                    # Pause if necessary
                                    pause()

                                    # Download file
                                    response = urllib.request.urlopen(download_url)
                                    download_size = int(response.headers["Content-Length"])
                                    if ui is not None:
                                        ui.label["text"] = "Downloading update... (0%)"
                                        ui.progress_bar["mode"] = "determinate"
                                        ui.progress_bar["maximum"] = download_size
                                        ui.progress_bar["value"] = 0
                                    with urllib.request.urlopen(download_url) as rfile:
                                        with open(destination, "wb") as wfile:
                                            download_size_downloaded = 0
                                            while download_size_downloaded < download_size:
                                                while ui.pause:
                                                    time.sleep(.1)
                                                if ui is not None:
                                                    done = download_size_downloaded
                                                    percent = int(100 * (done / download_size))
                                                    ui.label["text"] = (
                                                        f"Downloading update... ({percent}%)"
                                                    )
                                                    ui.progress_bar["value"] = (
                                                        download_size_downloaded
                                                    )
                                                bytes_read = rfile.read(SC4MP_BUFFER_SIZE)
                                                download_size_downloaded += len(bytes_read)
                                                wfile.write(bytes_read)

                                    # Pause if necessary
                                    pause()

                                    # Report installing update
                                    report("Installing update...")
                                    if ui is not None:
                                        ui.progress_bar['mode'] = "indeterminate"
                                        ui.progress_bar['maximum'] = 100
                                        ui.progress_bar.start(2)

                                    # Pause if necessary
                                    pause()

                                    # Start installer in very silent mode and exit
                                    subprocess.Popen([
                                        os.path.abspath(destination),
                                        f"/dir={os.getcwd()}",
                                        "/verysilent",
                                    ])
                                    ui.destroy()

                                except Exception as e:

                                    show_error(
                                        f"An error occurred in the update thread.\n\n{e}",
                                        no_ui=True
                                    )

                                    # Retry
                                    if ui is not None:
                                        ui.progress_bar['mode'] = "indeterminate"
                                        ui.progress_bar.start(2)
                                        for count in range(5):
                                            report(f"Update failed. Retrying in {5 - count}...")
                                            time.sleep(1)

                        except Exception:

                            # All uncaught errors in thread trigger a fatal error
                            fatal_error()

                    # Prepare the UI if not running in command-line mode
                    if state.sc4mp_ui:

                        # Create hidden top-level window
                        state.sc4mp_ui = tk.Tk()
                        state.sc4mp_ui.iconphoto(True, tk.PhotoImage(file=SC4MP_ICON))
                        state.sc4mp_ui.withdraw()

                        # Create updater UI
                        updater_ui = UpdaterUI(state.sc4mp_ui)

                        # Start update thread
                        th.Thread(target=update, kwargs={"ui": updater_ui}, daemon=True).start()

                        # Run the UI main loop
                        close_splash()
                        state.sc4mp_ui.mainloop()

                        # Exit when complete
                        sys.exit()

                    else:

                        # Run update thread directly
                        update()

        except Exception as e:

            # Show error silently and continue as usual
            show_error(f"An error occurred while updating.\n\n{e}", no_ui=True)


def get_release_info(version="latest", timeout=10) -> dict:

    if version == "latest":
        github_api_call = f"https://api.github.com/repos/{SC4MP_GITHUB_REPO}/releases/latest"
    else:
        github_api_call = (
            f"https://api.github.com/repos/{SC4MP_GITHUB_REPO}/releases/tags/v{version}"
        )

    try:
        with urllib.request.urlopen(url=github_api_call, timeout=timeout) as url:
            return json.load(url)
    except urllib.error.URLError as e:
        raise ClientException("GitHub API call timed out.") from e

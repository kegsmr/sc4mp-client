"""ServerLoader thread: connects to a server and downloads its plugins and
regions before the game starts."""

from __future__ import annotations

import ctypes
import math
import os
import random
import shutil
import socket
import threading as th
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from core.networking import NetworkException
from core.util import (
    is_windows,
    md5,
    sanitize_directory_name,
    sanitize_relpath,
    set_thread_name,
    unformat_version,
)
from client import state
from client.constants import (
    SC4MP_ARROW,
    SC4MP_DELAY,
    SC4MP_RISKY_FILE_EXTENSIONS,
    SC4MP_TITLE,
    SC4MP_VERSION,
)
from client.errors import ClientException, show_error
from client.game_monitor import GameMonitor
from client.sc4 import (
    get_sc4_path,
    is_steam_sc4,
    prep_region_config,
    sync_simcity_4_cfg,
)
from client.server import Server
from client.ui.password_dialog import PasswordDialogUI
from client.ui.settings import SC4SettingsUI
from client.utils import (
    directory_size,
    get_fullpaths_recursively,
    get_relpaths_recursively,
    get_sc4mp_path,
    process_exists,
    purge_directory,
    window_open,
)


class ServerLoader(th.Thread):

    def __init__(self, ui, server):

        th.Thread.__init__(self)

        self.ui = ui
        self.server: Server = server

        self.setDaemon(True)

        if state.sc4mp_ui is not None:
            state.sc4mp_ui.withdraw()

    def run(self):

        try:

            set_thread_name("SldThread", enumerate=False)

            if self.ui is not None:

                # Prompt the SC4 intallation directory while not found
                while get_sc4_path() is None:
                    if not messagebox.askokcancel(SC4MP_TITLE, 'No SimCity 4 installation found. \n\nPlease provide the correct installation path.'):
                        self.ui.destroy()
                        if state.sc4mp_exit_after:
                            state.sc4mp_ui.destroy()
                        else:
                            state.sc4mp_ui.deiconify()
                        return
                    path = filedialog.askdirectory(parent=self.ui)
                    if len(path) > 0:
                        state.sc4mp_config["SC4"]["game_path"] = path
                        if state.sc4mp_config["SC4"]["use_steam_browser_protocol"] in [0, 1]:
                            state.sc4mp_config["SC4"]["use_steam_browser_protocol"] = (1 if is_steam_sc4(Path(path)) else 0)
                        state.sc4mp_config.update()
                    else:
                        self.ui.destroy()
                        if state.sc4mp_exit_after:
                            state.sc4mp_ui.destroy()
                        else:
                            state.sc4mp_ui.deiconify()
                        return

                # Prompt to apply the 4gb patch if not yet applied
                if is_windows():
                    try:
                        sc4_exe_path = get_sc4_path()
                        if not os.path.exists(sc4_exe_path.parent / (sc4_exe_path.name + ".Backup")):
                            choice = messagebox.askyesnocancel(SC4MP_TITLE, "It appears the 4GB patch has not been applied to SimCity 4.\n\nLoading certain plugins may cause SimCity 4 to crash if the patch has not been applied.\n\nWould you like to apply the patch now?", icon="warning")
                            if choice is None:
                                self.ui.destroy()
                                if state.sc4mp_exit_after:
                                    state.sc4mp_ui.destroy()
                                else:
                                    state.sc4mp_ui.deiconify()
                                return
                            elif choice is True:
                                exit_code = ctypes.windll.shell32.ShellExecuteW(None, "runas", f"{get_sc4mp_path('4gb-patch.exe').absolute()}", f"\"{sc4_exe_path}\"", None, 1)
                                if exit_code not in [0, 42]:
                                    raise ClientException(f"Patcher exited with code {exit_code}.")
                    except Exception as e:
                        show_error(f"An error occurred while applying the 4GB patch.\n\n{e}")

            host = self.server.host
            port = self.server.port

            try:

                loading_start = time.time()

                self.report("", f'Connecting to server at {host}:{port}...')
                self.fetch_server()

                self.report("", 'Authenticating...')
                self.authenticate()

                self.report("", "Synchronizing plugins...")
                self.load("plugins")

                self.report("", "Synchronizing regions...")
                self.load("regions")

                self.report("", "Preparing plugins...")
                self.prep_plugins()

                self.report("", "Preparing regions...")
                self.prep_regions()

                if state.sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
                    self.report("", "Preparing config...")
                    self.prep_config()

                self.report("", "Launching SC4...")

                loading_end = time.time()

                print(f"- {round(loading_end - loading_start)} seconds")

                state.sc4mp_current_server = self.server

            except tk.TclError:

                pass

            except Exception as e:

                # pylint: disable-next=no-member
                if (self.ui is not None) and (self.ui.winfo_exists() == 1) and not (type(e) is ClientException and e.message == "Connection cancelled."):
                    show_error(f"An error occurred while connecting to the server.\n\n{e}")
                else:
                    show_error(e, no_ui=True)

            if state.sc4mp_current_server:

                state.sc4mp_config["GENERAL"]["default_host"] = self.server.host
                state.sc4mp_config["GENERAL"]["default_port"] = self.server.port
                state.sc4mp_config.update()

                self.server.categories.append("History")

                game_monitor = GameMonitor(self.server)
                game_monitor.start()

                if self.ui:

                    if self.ui.background and self.ui.background.winfo_exists():
                        self.ui.background.lift()
                    self.ui.lift()

                    try:
                        if is_windows():
                            while self.ui.winfo_exists() and not state.sc4mp_ui.winfo_viewable() and not window_open("simcity 4.exe"):
                                time.sleep(SC4MP_DELAY)
                    except Exception as e:
                        show_error(e, no_ui=True)

                    if state.sc4mp_config["SC4"]["fullscreen"] and not state.sc4mp_ui.winfo_viewable():
                        time.sleep(10)

                    self.ui.destroy()

                    if state.sc4mp_ui.winfo_viewable():
                        if messagebox.askokcancel(title=SC4MP_TITLE, icon="error", message="SimCity 4 may not have launched correctly due to invalid settings.\n\nAdjust your settings in the SC4 settings menu before connecting to the server again.\n\nTIP: You can click the \"Preview\" button in the SC4 settings menu to test your settings without connecting to a server."):
                            SC4SettingsUI()

                if game_monitor.ui and game_monitor.ui.winfo_exists() and game_monitor.ui.winfo_viewable():
                    game_monitor.ui.grab_set()

                return

            if state.sc4mp_ui:
                if state.sc4mp_exit_after:
                    state.sc4mp_ui.destroy()
                else:
                    state.sc4mp_ui.deiconify()
            if self.ui:
                self.ui.destroy()

        except Exception as e:

            show_error(f"An unexpected error occurred in the server loader thread.\n\n{e}")

    def report(self, prefix, text):

        if self.ui is not None:
            self.ui.label['text'] = text
            self.ui.progress_bar.start(2)
            self.ui.progress_bar['mode'] = "indeterminate"
            self.ui.progress_bar['maximum'] = 100
            self.ui.progress_label["text"] = ""
            self.ui.duration_label["text"] = ""
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

    def fetch_server(self):

        if not self.server.fetched:
            self.server.fetch()
            if not self.server.fetched:
                raise ClientException("Unable to find server. Check the IP address and port, then try again.")
        if not state.sc4mp_config["DEBUG"]["ignore_incompatable_versions"]:
            if unformat_version(self.server.server_version)[:2] < unformat_version(SC4MP_VERSION)[:2]:
                if state.sc4mp_beta is False:
                    raise ClientException(f"The server requires an outdated version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please contact the server administrators.")
            if unformat_version(self.server.server_version)[:2] > unformat_version(SC4MP_VERSION)[:2]:
                raise ClientException(f"The server requires a newer version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please update the launcher to connect to this server.")
        if self.ui is not None:
            self.ui.title(self.server.server_name)

    def authenticate(self):

        while True:
            try:
                tries = 0
                while not self.check_password():
                    if state.sc4mp_ui:
                        if tries >= 5:
                            raise ClientException("Too many password attempts.")
                        if tries > 0:
                            print("[WARNING] Incorrect password.")
                        PasswordDialogUI(self, tries)
                        tries += 1
                    else:
                        raise ClientException("Incorrect password.")
                if self.server.password != "":
                    self.server.authenticate()
                break
            except (socket.error, socket.timeout) as e:
                self.connection_failed_retrying(e)

    def check_password(self):

        if self.server.password_enabled:
            if self.server.password is None:
                if state.sc4mp_config["GENERAL"]["save_server_passwords"]:
                    try:
                        self.server.password = state.sc4mp_servers_database[self.server.server_id]["password"]
                    except Exception:
                        return False
            if self.server.password == "":
                return True
            if self.ui is not None:
                self.ui.label['text'] = "Authenticating..."
            with self.server.socket() as s:
                if s.check_password(password=self.server.password):
                    if state.sc4mp_config["GENERAL"]["save_server_passwords"]:
                        try:
                            state.sc4mp_servers_database[self.server.server_id]["password"] = self.server.password
                        except Exception as e:
                            show_error(e, no_ui=True)
                    return True
                else:
                    return False
        else:
            return True

    def load(self, target: str) -> None:

        # Select the destination directory according to the parameter
        destination = None
        if target == "plugins":
            destination = Path(state.SC4MP_LAUNCHPATH) / "Plugins" / "server"
        elif target == "regions":
            destination = Path(state.SC4MP_LAUNCHPATH) / "Regions"

        # Create destination if necessary
        if not destination.exists():
            destination.mkdir(parents=True, exist_ok=True)

        # Load or clear custom plugins (the code is organized like hell here, but it works)
        if target == "plugins":

            # For keeping track of DLL plugins
            self.dll_plugin_paths = []

            # Set source and destination for custom plugins
            client_plugins_source = Path(state.sc4mp_config["GENERAL"]["custom_plugins_path"])
            client_plugins_destination = Path(state.SC4MP_LAUNCHPATH) / "Plugins" / "client"

            # Synchronize custom plugins if the server permits custom plugins and the user wants to load them
            if self.server.user_plugins_enabled and state.sc4mp_config["GENERAL"]["custom_plugins"]:

                # Report for the loading sequence
                self.report("", "Synchronizing custom plugins...")
                # self.ui.duration_label["text"] = "(verifying)" # doesn't work :(

                # Get the paths to all files in the destination directory
                destination_relpaths = get_fullpaths_recursively(client_plugins_destination)

                # Delete all files in the destination directory that are not present in the source directory
                for relpath in destination_relpaths:
                    if not Path(client_plugins_source, relpath).exists():
                        filename = Path(client_plugins_destination) / relpath
                        print(f'- removing "{filename}"')
                        filename.unlink()

                # Get the paths to all files in the source directory
                source_relpaths = get_relpaths_recursively(client_plugins_source)

                # Get the size of the source directory
                source_size = directory_size(client_plugins_source)

                # These variables will be used to calculate the percentage for the progress bar
                destination_size = 0
                percent = -1

                # True if symlinks are allowed
                linking = False

                # Loop through the file paths in the source directory, and copy them to the destination if necessary
                for relpath in source_relpaths:

                    # Progress bar stuff
                    old_percent = percent
                    percent = math.floor(100 * (destination_size / source_size))
                    if percent > old_percent:
                        self.report_progress(f'Synchronizing custom plugins... ({percent}%)', percent, 100)
                    try:
                        self.ui.progress_label["text"] = relpath.name
                        if linking:
                            self.ui.duration_label["text"] = f"Link {SC4MP_ARROW} SC4"  # "(linking)"
                        else:
                            self.ui.duration_label["text"] = f"Disk {SC4MP_ARROW} SC4"  # "(copying)"
                    except Exception:
                        pass

                    # Set the source and destination paths for the file
                    src = client_plugins_source / relpath
                    dest = client_plugins_destination / relpath

                    # For DLL plugins
                    if relpath.suffix == ".dll":
                        self.dll_plugin_paths.append((dest, "client"))

                    # More progress bar stuff
                    destination_size += src.stat().st_size

                    # If the destination file exists, check the md5's to see if they match
                    if dest.exists():

                        # If the destination file is a link, or the md5's match, continue to the next iteration of the loop
                        if os.path.islink(dest) or md5(src) == md5(dest):
                            # print(f'- verified "{dest}"')
                            continue

                        # If the md5's don't match, delete the destination file
                        else:
                            print(f'- removing "{dest}"')
                            dest.unlink()

                    # Make the destination directory if necessary, then try to make a symbolic link (fast), and if the required priveleges are not held, copy the file (slower)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        os.symlink(src, dest)
                        print(f'- linked "{src}"')
                        linking = True
                    except OSError:
                        print(f'- copying "{src}"')
                        shutil.copy(src, dest)
                        linking = False

            # Clear custom plugins
            else:
                try:
                    self.report("", "Clearing custom plugins...")
                    purge_directory(client_plugins_destination)
                except Exception as e:
                    show_error(f"Unable to delete \"{e}\"!", no_ui=True)

        # Loop broken when the loading is successful, an unexpected error occurs, or the amount of tries is exceeded
        while True:

            try:

                # Purge the destination directory
                self.report("", f"Synchronizing {target}...")  # "", "Purging " + type + " directory...")
                try:
                    purge_directory(destination)
                except ClientException as e:
                    if process_exists("simcity 4.exe"):
                        raise ClientException("SimCity 4 is already running!") from e
                    raise

                # Report
                self.report("", f"Synchronizing {target}...")

                # Request the type of data
                with self.server.socket() as s:
                    file_table = s.file_table(target)

                # Get total download size
                size = sum([entry[1] for entry in file_table])

                # Total size downloaded
                size_downloaded = 0

                # Download percent
                percent = 0

                # Set loading bar at 0%
                self.report_progress(f"Synchronizing {target}... (0%)", 0, 100)

                # Prune file table as necessary
                ft = []
                for entry in file_table:

                    # Get necessary values from entry
                    checksum = sanitize_directory_name(entry[0])
                    filesize = entry[1]
                    relpath = Path(entry[2])

                    # Handle risky file types
                    if not state.sc4mp_config["GENERAL"]["ignore_risky_file_warnings"]:
                        if state.sc4mp_ui:
                            if (relpath.suffix.lower() in SC4MP_RISKY_FILE_EXTENSIONS) and (state.sc4mp_servers_database[self.server.server_id].get("allowed_files", {}).get(checksum, "") != relpath.name.lower()):
                                choice = messagebox.askyesnocancel(title=SC4MP_TITLE, message=f"You are about to download \"{relpath.name}\". This file could potentially harm your computer.\n\nWould you like to download it anyway?", icon="warning")
                                if choice is True:
                                    state.sc4mp_servers_database[self.server.server_id].setdefault("allowed_files", {})
                                    state.sc4mp_servers_database[self.server.server_id]["allowed_files"][checksum] = relpath.name.lower()
                                elif choice is False:
                                    size_downloaded += filesize
                                    continue
                                else:
                                    raise ClientException("Connection cancelled.")
                        else:
                            print(f"[WARNING] Downloading risky file: \"{relpath.name}\"")

                    # For DLL plugins
                    if relpath.suffix == ".dll":
                        self.dll_plugin_paths.append((Path(destination) / relpath, "server"))

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
                            self.report_progress(f"Synchronizing {target}... ({percent}%)", percent, 100)

                    else:

                        # Append to new file table
                        ft.append(entry)

                file_table = ft

                if state.sc4mp_ui:
                    self.ui.duration_label["text"] = f"Server {SC4MP_ARROW} SC4"  # "(downloading)"

                download_start_time = time.time() + 2

                total_size_to_download = sum([entry[1] for entry in file_table])
                total_size_already_downloaded = 0.0

                old_eta = None
                old_eta_display_time = download_start_time + 2

                # Receive files
                with self.server.socket() as s:

                    for entry in s.file_table_data(target, file_table):

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
                                total_size_already_downloaded += len(chunk)
                                size_downloaded += len(chunk)
                                old_percent = percent
                                percent = math.floor(100 * (size_downloaded / (size + 1)))
                                if percent > old_percent:
                                    self.report_progress(f"Synchronizing {target}... ({percent}%)", percent, 100)
                                if state.sc4mp_ui is not None:
                                    try:
                                        now = time.time()
                                        eta = int((total_size_to_download - total_size_already_downloaded) / (total_size_already_downloaded / float(now - download_start_time)))
                                        if (eta < 86400) and (old_eta is None or (old_eta > eta or int(now - old_eta_display_time) > 5)) and float(now - old_eta_display_time) >= .8:
                                            old_eta = eta
                                            old_eta_display_time = now
                                            hours = math.floor(eta / 3600)
                                            eta -= hours * 3600
                                            minutes = math.floor(eta / 60)
                                            eta -= minutes * 60
                                            seconds = eta
                                            if hours > 0:
                                                self.ui.duration_label["text"] = f"{hours}:{minutes:0>{2}}:{seconds:0>{2}}"
                                            else:
                                                self.ui.duration_label["text"] = f"{minutes}:{seconds:0>{2}}"
                                    except ZeroDivisionError as e:
                                        show_error(e, no_ui=True)  # Lazy solution
                        t.with_name(t.name + ".tmp").replace(t)  # only cache the file once its checksum has been verified

                self.report_progress(f"Synchronizing {target}... (100%)", 100, 100)

                break

            except (NetworkException, socket.error, socket.timeout) as e:

                # tries += 1

                # if tries < 5:

                self.connection_failed_retrying(e)

                # else:

                # raise ClientException("Maximum connection attemps exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

    def prep_plugins(self):

        # Get checksums of plugins installed to the top-level of the program files plugins folder (to avoid dobule-loading DLLs)
        toplevel_plugins_checksums = []
        try:
            installation_plugins_path = get_sc4_path().parent.parent / "Plugins"
            for file_name in os.listdir(installation_plugins_path):
                file_path = installation_plugins_path / file_name
                if file_path.is_file():
                    toplevel_plugins_checksums.append(md5(file_path))
        except Exception as e:
            show_error(e, no_ui=True)

        # Set source and destination for default plugins
        default_plugins_source = Path("resources")
        default_plugins_destination = Path(state.SC4MP_LAUNCHPATH) / "Plugins"  # / "default"

        # Clear default plugins directory
        try:
            purge_directory(default_plugins_destination, recursive=False)
        except Exception as e:
            if process_exists("simcity 4.exe"):
                raise ClientException("SimCity 4 is already running!") from e
            raise

        resw = state.sc4mp_config['SC4']['resw']
        resh = state.sc4mp_config['SC4']['resh']
        if 0 in (resw, resh) and state.sc4mp_ui:
            resw = state.sc4mp_ui.winfo_screenwidth()
            resh = state.sc4mp_ui.winfo_screenheight()

        # Load default plugins
        for default_plugin_file_name in [
            "sc4-fix.dll",
            "sc4-fix-license.txt",
            "sc4-thumbnail-fix.dll",
            "sc4-thumbnail-fix-license.txt",
            "sc4-thumbnail-fix-third-party-notices.txt",
            f"sc4mp-intro-{resw}-{resh}.dat",
            "sc4mp-local.dat",
            "sc4mp-ui.dat",
        ]:
            try:
                default_plugin_file_path = default_plugins_source / default_plugin_file_name
                default_plugin_checksum = md5(default_plugin_file_path)
                if default_plugin_checksum not in toplevel_plugins_checksums:
                    shutil.copy(default_plugin_file_path, default_plugins_destination / f"default-{default_plugin_file_name}")
                    toplevel_plugins_checksums.append(default_plugin_checksum)
            except Exception as e:
                show_error(f"Failed to load default plugin \"{default_plugin_file_name}\".\n\n{e}", no_ui=True)

        # Copy DLLs from subfolders (DLL plugins do not load in subfolders)
        for path, basename in self.dll_plugin_paths:
            checksum = md5(path)
            if checksum not in toplevel_plugins_checksums:
                shutil.copy(path, default_plugins_destination / f"{basename}-{checksum}.dll")
                toplevel_plugins_checksums.append(checksum)

        # Write server URL local plugin file
        # with open(get_sc4mp_path("sc4mp-local-server-url.dat"), "rb") as rfile:
        #     data = rfile.read().replace(b"{\x00{\x00U\x00R\x00L\x00}\x00}", bytes(self.server.server_url, encoding="utf-8"))
        #     with open(default_plugins_destination / "server-url.dat", "wb") as wfile:
        #         wfile.write(data)

    def prep_regions(self):

        # Declare instance variable to store the paths of the server region subdirectories
        self.server.regions: list[Path] = []

        # Path to regions directory
        regions_directory = Path(state.SC4MP_LAUNCHPATH) / "Regions"

        # Loop through the server regions, add them to the server regions instance variable and add prefixes to the region names in the region config files
        for child in regions_directory.iterdir():
            if child.is_dir():
                self.server.regions.append(child)
                config_path = regions_directory / child / "region.ini"
                prep_region_config(config_path)

        # Create `Downloads` directory in the `Regions` folder
        downloads_path = regions_directory / "Downloads"
        downloads_path.mkdir(exist_ok=True, parents=True)

        # Copy the latest failed save push into the `Downloads` directory
        try:

            # Pick the salvage subdirectory corresponding to the current server
            salvage_directory = Path(state.SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id

            # Pick the directory corresponding to the latest failed save push
            save_directory = os.path.join(salvage_directory, os.listdir(salvage_directory)[-1])

            # Pick the directory corresponding to the first region in the failed save push (there should only be one anyway)
            region_directory = os.path.join(save_directory, os.listdir(save_directory)[0])

            # Copy each file from the region directory to the `Downloads` directory
            for filename in os.listdir(region_directory):
                shutil.copy(os.path.join(region_directory, filename), os.path.join(downloads_path, filename))

        except Exception:

            pass  # show_error(e, no_ui=True)

        # Create the auxiliary regions for launcher functions (eg. refreshing)
        AUXILIARY_REGIONS = ["Refresh"]  # ["Backups", "Export", "Refresh"]
        for auxiliary_region in AUXILIARY_REGIONS:

            # Create the auxiliary region directory
            auxiliary_region_path = regions_directory / f"_{auxiliary_region}"  # TODO possible directory name conflicts?
            auxiliary_region_path.mkdir(parents=True)

            # Copy the blank `config.bmp` file to the auxiliary region directory
            shutil.copy(get_sc4mp_path("config.bmp"), auxiliary_region_path / "config.bmp")

            # Create a `region.ini` file for the auxiliary region
            with open(get_sc4mp_path("region.ini"), "r") as template_config_file:

                # Read the contents of the template `region.ini`
                config_file_contents: str = template_config_file.read()

                # Replace the region name
                config_file_contents = config_file_contents.replace("New Region", f"{auxiliary_region}...")

                # Write the file
                with open(auxiliary_region_path / "region.ini", "w") as config_file:
                    config_file.write(config_file_contents)

    def prep_config(self):

        try:

            # Get the path to the SimCity 4 config last used on this server
            server_config_path = state.SC4MP_LAUNCHPATH / "_Configs" / f"{self.server.server_id}.cfg"

            # Get the path to the multiplayer config
            mp_config_path = state.SC4MP_LAUNCHPATH / "SimCity 4.cfg"

            # If the server's config exists
            if server_config_path.exists():

                # Delete the old multiplayer config if it exists
                if mp_config_path.exists():
                    os.unlink(mp_config_path)

                # Copy the last used config to be the multiplayer config
                shutil.copy(server_config_path, mp_config_path)

                # Copy the multiplayer config to singleplayer
                sync_simcity_4_cfg()

            else:

                # Copy the singleplayer config to multiplayer if it does not exist
                if not mp_config_path.exists():
                    sync_simcity_4_cfg(to_mp=True)

        except Exception as e:

            show_error(f"An error occurred while preparing the config.\n\n{e}", no_ui=True)

    def connection_failed_retrying(self, e, duration=5):

        show_error(e, no_ui=True)

        for count in range(duration):
            self.report("[WARNING] ", f"Connection failed. Retrying in {duration - count}...")
            time.sleep(1)

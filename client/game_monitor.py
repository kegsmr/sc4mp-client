"""Threads that run SimCity 4 and push saved cities to the server while
it runs."""

from __future__ import annotations

import os
import shutil
import socket
import threading as th
import time
from datetime import datetime
from pathlib import Path

from core.dbpf import SC4Savegame
from core.networking import NetworkException
from core.util import md5, set_thread_name, xor
from client import state
from client.constants import SC4MP_BUFFER_SIZE, SC4MP_LAUNCHERMAP_ENABLED
from client.errors import show_error
from client.regions_refresher import RegionsRefresher
from client.sc4 import (
    get_sc4_cfg_path,
    refresh_region_open,
    start_sc4,
    sync_simcity_4_cfg,
)
from client.server import Server
from client.ui.game_monitor import (
    GameMonitorMapUI,
    GameMonitorUI,
    GameOverlayUI,
    RegionsRefresherUI,
)


class GameMonitor(th.Thread):

    def __init__(self, server):

        th.Thread.__init__(self)

        self.server: Server = server

        # Cached md5's of savegames, by path, with the size and modification time they were computed for
        self.city_hashcode_cache = {}

        # Get list of city paths and their md5's
        self.city_paths, self.city_hashcodes = self.get_cities()

        # For backwards compatability
        self.PREFIX = ""

        # For status window and overlay window
        self.ui = None
        self.overlay_ui = None

        # If UI enabled (not commandline mode)
        if state.sc4mp_ui is not None:

            # If launcher map enabled, use the map UI for the status window
            if SC4MP_LAUNCHERMAP_ENABLED:
                self.ui = GameMonitorMapUI()

            # Otherwise, use the legacy status window
            else:
                self.ui = GameMonitorUI(self)

            # Create game overlay window if the game overlay is enabled (`1` is fullscreen-mode only; `2` is always enabled)
            if (state.sc4mp_config["GENERAL"]["use_game_overlay"] == 1 and state.sc4mp_config["SC4"]["fullscreen"]) or state.sc4mp_config["GENERAL"]["use_game_overlay"] == 2:
                self.overlay_ui = GameOverlayUI(self.ui, guest=(server.password == ""))
                if state.sc4mp_game_monitor_x > 0:
                    self.ui.withdraw()
            else:
                self.ui.deiconify()

            # Set window title to server name
            self.ui.title(server.server_name)

        # Start the game launcher thread (starts the game)
        self.game_launcher = GameLauncher()
        self.game_launcher.start()

        # Thread shutsdown when this is set to `True`
        self.end = False

    def run(self):

        # Catch all errors and show an error message
        try:

            # Thead name for logging
            set_thread_name("GmThread", enumerate=False)

            # if self.ui:
            # self.ui.deiconify()
            # self.ui.grab_set()

            # Declare variable to break loop after the game closes
            end = False

            # Used for refresh stuff (`cfg_hashcode` is the md5 of `SimCity 4.cfg`)
            cfg_hashcode = None
            old_refresh_region_open = False

            # Set initial status in UI
            if self.server.password == "":
                self.report_quietly("Welcome, you've joined as a guest.")
            else:
                self.report_quietly("Welcome, start a city and save to claim a tile.")  # Ready. #"Monitoring for changes...")

            # Show server description in UI (only for the legacy status window)
            if state.sc4mp_ui and not SC4MP_LAUNCHERMAP_ENABLED:
                self.ui.ping_frame.left["text"] = f"{self.server.host}:{self.server.port}"
                self.ui.description_label["text"] = self.server.server_description
                self.ui.url_label["text"] = self.server.server_url

            # Time the server was last pinged (`None` for now)
            last_ping_time = None

            # Infinite loop that can be broken by the "end" variable (runs an extra time once it's set to `True`)
            while True:

                # Catch all errors and show an error message in the console
                try:

                    # Update server ping in UI every 5 seconds
                    if last_ping_time is None or time.time() - last_ping_time >= 5:

                        # Ping the server
                        ping = self.ping()

                        # If the server is responsive, print the ping in the console and display the ping in the ui
                        if ping is not None:
                            print(f"Ping: {ping}")
                            if self.ui is not None:
                                self.ui.ping_frame.right['text'] = f"{ping}ms"
                                self.ui.ping_frame.right['fg'] = "gray"

                        # If the server is unresponsive, print a warning in the console and update the ui accordingly
                        else:
                            print("[WARNING] Disconnected.")
                            if self.ui is not None:
                                self.ui.ping_frame.right['text'] = "Disconnected"
                                self.ui.ping_frame.right['fg'] = "red"

                        # Set the last ping time
                        last_ping_time = time.time()

                    # If not in guest mode
                    if self.server.password != "":

                        # new_city_paths, new_city_hashcodes = self.get_cities()

                        # Array of savegames to push to the server
                        save_city_paths = []

                        # Print statements for debugging
                        # print("Old cities: " + str(self.city_paths))
                        # print("New cities: " + str(new_city_paths))

                        # Will be used to store the amount of savegames detected in the previous iteration of the following while loop (-1 means the while loop will always run at least one time!)
                        save_city_paths_length = -1

                        # Loop until no new/modified savegames were found in the last iteration of the loop (meant to prevent fragmented save pushes, not the best solution because it relies somewhat on the loop delay)
                        while len(save_city_paths) != save_city_paths_length:

                            # Update the new/modified savegame counter
                            save_city_paths_length = len(save_city_paths)

                            # Store the paths and hashcodes of savegames in the "Regions" directory to two local arrays
                            new_city_paths, new_city_hashcodes = self.get_cities()  # TODO I think this should be here...?

                            # Loop through the paths of the savegames currently found in the "Regions" directory
                            for new_city_path in new_city_paths:

                                # If it's a new savegame, add it to the list of savegames to be pushed to the server
                                if new_city_path not in self.city_paths:
                                    save_city_paths.append(new_city_path)

                                # If it's not a new savegame, check if it's a modified savegame. If so, add it to the same list
                                else:
                                    city_hashcode = self.city_hashcodes[self.city_paths.index(new_city_path)]
                                    new_city_hashcode = new_city_hashcodes[new_city_paths.index(new_city_path)]
                                    if city_hashcode != new_city_hashcode:
                                        save_city_paths.append(new_city_path)

                            # For future comparisons
                            self.city_paths = new_city_paths
                            self.city_hashcodes = new_city_hashcodes

                            # If modified savegames are found
                            if len(save_city_paths) > 0:

                                # Report waiting to sync if new/modified savegames found
                                self.report("", "Saving...")
                                self.set_overlay_state("saving")

                                # Wait
                                time.sleep(1)  # 5 #6 #5 #6 #10 #3 #TODO make configurable?

                                # Filter the savegames if more than two are found
                                if len(save_city_paths) > 2:
                                    try:
                                        savegames = []
                                        for save_city_path in save_city_paths:
                                            savegame = SC4Savegame(save_city_path, error_callback=None)
                                            savegame.get_SC4ReadRegionalCity()
                                            savegames.append(savegame)
                                        filtered_savegames = self.filter_bordering_tiles(savegames)
                                        if len(filtered_savegames) == 1:
                                            save_city_paths = [savegame.filename for savegame in filtered_savegames]
                                            [savegame.close() for savegame in savegames]
                                            break
                                    except Exception as e:
                                        show_error(e, no_ui=True)

                        # If there are any new/modified savegame files, push them to the server. If errors occur, log them in the console and display a warning
                        if len(save_city_paths) > 0:
                            tries = 0
                            while True:
                                try:
                                    self.report("", "Saving...")
                                    self.set_overlay_state('saving')
                                    self.save(save_city_paths)
                                    break
                                except (NetworkException, socket.timeout, socket.error) as e:  # Is `ConnectionResetError` a `socket.error`?
                                    show_error(e, no_ui=True)
                                except Exception as e:
                                    show_error(e, no_ui=True)
                                    self.report("[WARNING] ", "Save push failed! Unexpected client-side error.", color="red")
                                    self.set_overlay_state("not-saved")
                                    break
                                tries += 1
                                for count in range(5):
                                    self.report("[WARNING] ", f"Connection failed. Retrying {5 - count}...")
                                    time.sleep(1)
                                if tries >= 3:
                                    self.report("[WARNING] ", "Save push failed! Server unreachable.", color="red")
                                    self.set_overlay_state("not-saved")
                                    break
                            time.sleep(5)

                    # Break the loop when signaled
                    if end:
                        break

                    # Signal to break the loop when the game is no longer running
                    if not self.game_launcher.game_running:
                        end = True
                        # if self.ui:
                        #     self.ui.deiconify()
                        #     self.ui.deiconify()
                        #     self.ui.lift()
                        #     self.ui.grab_set()
                        #     self.ui.focus_set()
                        #     # I tried everything...

                    # Wait
                    time.sleep(1)  # 3 #1 #3

                    # Refresh
                    cfg_path = get_sc4_cfg_path()
                    try:
                        new_cfg_hashcode = md5(cfg_path)
                        if cfg_hashcode is not None and new_cfg_hashcode != cfg_hashcode:
                            # print("Region switched!")
                            sync_simcity_4_cfg()
                            new_refresh_region_open = refresh_region_open()
                            if new_refresh_region_open and (not old_refresh_region_open):
                                # print("Refresh regions!")
                                if ping is None:
                                    self.report("[WARNING] ", "Unable to refresh regions at this time.", color="red")
                                else:
                                    old_text = self.ui.label["text"]  # noqa: F841 (unused, kept as is)
                                    self.report("", "Refreshing...")
                                    self.set_overlay_state("refreshing")
                                    if state.sc4mp_ui:
                                        regions_refresher_ui = RegionsRefresherUI(self.server)
                                        regions_refresher_ui.worker.run()
                                        try:
                                            regions_refresher_ui.destroy()
                                        except Exception:
                                            pass
                                    else:
                                        regions_refresher = RegionsRefresher(None, self.server)
                                        regions_refresher.run()
                                    self.city_paths, self.city_hashcodes = self.get_cities()
                                    if state.sc4mp_game_launcher.game_running:
                                        self.report("", "Regions refreshed at " + datetime.now().strftime("%H:%M") + ".", color="green")
                                        self.set_overlay_state("refreshed")
                                    # self.ui.label["text"] = old_text
                            old_refresh_region_open = new_refresh_region_open
                        cfg_hashcode = new_cfg_hashcode
                    except Exception as e:
                        show_error(f"An unexpected error occurred while refreshing regions.\n\n{e}", no_ui=True)

                except Exception:
                    if self.end:
                        break
                    else:
                        show_error("An unexpected error occurred in the game monitor loop.", no_ui=True)
                        time.sleep(5)  # 3

            # Save the config used on the server to the `_Configs` directory and restore the singleplayer config
            if state.sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
                try:
                    source = state.SC4MP_LAUNCHPATH / "SimCity 4.cfg"
                    destination = state.SC4MP_LAUNCHPATH / "_Configs" / f"{self.server.server_id}.cfg"
                    if destination.exists():
                        destination.unlink()
                    shutil.copy(source, destination)
                except Exception as e:
                    show_error(f"An error occurred while saving the SimCity 4 config.\n\n{e}", no_ui=True)

            # Restore the singleplayer config backup
            if state.sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
                try:
                    sp_config_path = Path("~/Documents/SimCity 4/SimCity 4.cfg").expanduser()
                    sp_config_backup_path = Path("~/Documents/SimCity 4/SimCity 4.cfg.bak").expanduser()
                    if sp_config_backup_path.exists():
                        if sp_config_path.exists():
                            os.unlink(sp_config_path)
                        shutil.copy(sp_config_backup_path, sp_config_path)
                        os.unlink(sp_config_backup_path)
                except Exception as e:
                    show_error(f"An error occurred while restoring the SimCity 4 config backup.\n\n{e}", no_ui=True)

            # Destroy the game monitor ui if running
            if self.ui:
                self.ui.destroy()

            # Destroy the game overlay ui if running
            if self.overlay_ui:
                self.overlay_ui.destroy()

            # Show the main ui once again
            if state.sc4mp_exit_after:
                if state.sc4mp_ui is not None:
                    state.sc4mp_ui.destroy()
            else:
                if state.sc4mp_ui is not None:
                    if state.sc4mp_exit_after:
                        state.sc4mp_ui.destroy()
                    else:
                        state.sc4mp_ui.deiconify()
                        state.sc4mp_ui.lift()
                        state.sc4mp_ui.focus_set()
                        state.sc4mp_ui.grab_set()

        except Exception as e:

            show_error(f"An unexpected error occurred in the game monitor thread.\n\n{e}")

    def get_cities(self) -> tuple[list[Path], list[str]]:

        city_paths = []
        city_hashcodes = []
        regions_path = Path(state.SC4MP_LAUNCHPATH) / "Regions"
        for region in self.server.regions:
            region_path: Path = regions_path / region
            region_path.mkdir(parents=True, exist_ok=True)
            if region_path.is_file():  # is this necessary?
                continue
            for city in region_path.glob('*.sc4'):
                city_path = region_path / city
                try:
                    city_hashcode = self.get_city_hashcode(city_path)
                except FileNotFoundError:
                    continue  # the game may rename or delete a savegame while we're looping
                city_paths.append(city_path)
                city_hashcodes.append(city_hashcode)
        return city_paths, city_hashcodes

    def get_city_hashcode(self, city_path: Path) -> str:

        # Only rehash savegames that changed, since reading a savegame while SC4 overwrites it causes "Error saving city"
        stat = city_path.stat()
        key = (stat.st_size, stat.st_mtime_ns)
        cached = self.city_hashcode_cache.get(city_path)
        if cached is None or cached[0] != key:
            cached = (key, md5(city_path))
            self.city_hashcode_cache[city_path] = cached
        return cached[1]

    def filter_bordering_tiles(self, savegames):

        # report("Savegame filter 1", self)

        filtered_savegames = []

        for savegame in savegames:

            add = True

            savegameX = savegame.SC4ReadRegionalCity["tileXLocation"]
            savegameY = savegame.SC4ReadRegionalCity["tileYLocation"]

            savegameSizeX = savegame.SC4ReadRegionalCity["citySizeX"]
            savegameSizeY = savegame.SC4ReadRegionalCity["citySizeY"]

            for neighbor in savegames:

                if neighbor == savegame:
                    continue

                neighborX = neighbor.SC4ReadRegionalCity["tileXLocation"]
                neighborY = neighbor.SC4ReadRegionalCity["tileYLocation"]

                neighborSizeX = neighbor.SC4ReadRegionalCity["citySizeX"]
                neighborSizeY = neighbor.SC4ReadRegionalCity["citySizeY"]

                conditionX1 = (neighborX == savegameX - neighborSizeX)
                conditionX2 = (neighborX == savegameX + savegameSizeX)
                conditionY1 = (neighborY == savegameY - neighborSizeY)
                conditionY2 = (neighborY == savegameY + savegameSizeY)

                conditionX = xor(conditionX1, conditionX2) and ((neighborY + neighborSizeY > savegameY) or (neighborY < savegameY + savegameSizeY))
                conditionY = xor(conditionY1, conditionY2) and ((neighborX + neighborSizeX > savegameX) or (neighborX < savegameX + savegameSizeX))

                condition = xor(conditionX, conditionY)

                if not condition:
                    add = False

            if add:

                filtered_savegames.append(savegame)

                # report("YES (" + str(savegameX) + ", " + str(savegameY) + ")", self)

            # else:

                # report("NO (" + str(savegameX) + ", " + str(savegameY) + ")", self)

        return filtered_savegames

    def save(self, save_city_paths: list[Path]) -> None:

        # Update overlay
        self.set_overlay_state("saving")

        # Salvage
        salvage_directory = Path(state.SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id / datetime.now().strftime("%Y%m%d%H%M%S")
        for path in save_city_paths:
            relpath = path.relative_to(Path(state.SC4MP_LAUNCHPATH) / "Regions")
            filename = salvage_directory / relpath
            directory = filename.parent
            directory.mkdir(exist_ok=True, parents=True)
            shutil.copy(path, filename)

        # Verify that all saves come from the same region
        regions = set([save_city_path.parent.name for save_city_path in save_city_paths])
        if len(regions) > 1:
            self.report(self.PREFIX, 'Save push failed! Too many regions.', color="red")
            self.set_overlay_state("not-saved")
            return
        else:
            region = list(regions)[0]

        with self.server.socket() as s:

            # Send save request
            s.save()

            # Send region name and file sizes
            s.send_json([
                region,
                [os.path.getsize(save_city_path) for save_city_path in save_city_paths]
            ])

            # Send file contents
            total_filesize = sum([save_city_path.stat().st_size for save_city_path in save_city_paths])
            filesize_sent = 0
            filesize_reported = None
            for save_city_path in save_city_paths:
                with open(save_city_path, "rb") as file:
                    while True:
                        data = file.read(SC4MP_BUFFER_SIZE)
                        if not data:
                            break
                        s.sendall(data)
                        filesize_sent += len(data)
                        if filesize_sent == total_filesize or filesize_reported is None or filesize_sent > filesize_reported + 100000:
                            filesize_reported = filesize_sent
                            self.report_quietly(f'Saving... ({round(filesize_sent / 1000):,}/{round(total_filesize / 1000):,}KB)')

            # Handle response from server
            response = s.save_result()
            if response == "ok":
                self.report(self.PREFIX, f'Saved successfully at {datetime.now().strftime("%H:%M")}.', color="green")  # TODO keep track locally of the client's claims
                self.set_overlay_state("saved")
                shutil.rmtree(salvage_directory)  # TODO make configurable
            else:
                self.report(self.PREFIX + "[WARNING] ", f"Save push failed! {response}", color="red")
                self.set_overlay_state("not-saved")

    def backup_city(self, city_path: Path) -> None:

        region = city_path.parent.name
        city = city_path.name
        backup_directory: Path = Path(state.SC4MP_LAUNCHPATH) / "SC4MPBackups" / self.server.server_id / region / city
        backup_directory.mkdir(exist_ok=True, parents=True)
        destination = backup_directory / datetime.now().strftime("%Y%m%d%H%M%S")
        shutil.copy(city_path, destination.with_suffix(".sc4"))

    def ping(self):

        return self.server.ping()

    def report(self, prefix, text, color="black"):

        if self.ui is not None:
            self.ui.label['text'] = text
            self.ui.label.config(fg=color)
        print(prefix + text)

    def report_quietly(self, text):

        if self.ui is not None:
            self.ui.label['text'] = text

    def set_overlay_state(self, state):
        if self.overlay_ui is not None:
            self.overlay_ui.set_state(state)


class GameLauncher(th.Thread):

    def __init__(self):

        super().__init__()

        state.sc4mp_game_launcher = self

        self.game_running = True
        self.setDaemon(True)

    def run(self):

        try:

            set_thread_name("GlThread", enumerate=False)

            start_sc4()

        except Exception as e:

            show_error(f"An unexpected error occurred while launching SimCity 4.\n\n{e}")

        finally:

            self.game_running = False

            state.sc4mp_current_server = None

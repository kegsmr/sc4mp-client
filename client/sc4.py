"""Finding, configuring and launching SimCity 4."""

from __future__ import annotations

import configparser
import os
import shutil
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional

from core.dbpf import SC4Config
from core.util import is_windows
from client import state
from client.errors import ClientException, show_error
from client.utils import process_exists


def get_sc4_path() -> Optional[Path]:
    """Returns the path to the SimCity 4 executable if found."""

    # The path specified by the user
    config_path = Path(state.sc4mp_config['SC4']['game_path'])

    # On Windows, create a list of possible SC4 installation paths, otherwise
    # just use the config path
    if is_windows():

        # Common SC4 dirs (alternate path used by GOG and Origin)
        sc4_dirs = Path("SimCity 4 Deluxe") / "Apps" / "SimCity 4.exe"
        sc4_dirs_alt = Path("SimCity 4 Deluxe Edition") / "Apps" / "SimCity 4.exe"

        # Common Steam dirs
        steam_dirs = Path("Steam") / "steamapps" / "common"

        # Drive letters
        drives: list[Path] = []
        for letter_code in range(65, 91):
            try:
                letter: str = chr(letter_code)
                drive = Path(f"{letter}:\\")
                if drive.exists():
                    drives += [drive]
            except Exception as e:
                show_error(e, no_ui=True)

        # List of common SC4 install dirs, highest priority at the top
        possible_paths: list[Path] = [

            # Custom (specified by the user)
            config_path,
            config_path / "SimCity 4.exe",
            config_path / "Apps" / "SimCity 4.exe",

        ]

        # Expand list for common SC4 install dirs using different drive letters
        for drive in drives:

            possible_paths += [

                # GOG (patched, no DRM, launches without issue)
                drive / "Program Files" / "GOG Galaxy" / "Games" / sc4_dirs,
                drive / "Program Files" / "GOG Galaxy" / "Games" / sc4_dirs_alt,
                drive / "Program Files (x86)" / "GOG Galaxy" / "Games" / sc4_dirs,
                drive / "Program Files (x86)" / "GOG Galaxy" / "Games" / sc4_dirs_alt,
                drive / "Games" / "GOG Galaxy" / "Games" / sc4_dirs,
                drive / "Games" / "GOG Galaxy" / "Games" / sc4_dirs_alt,
                drive / "GOG Galaxy" / "Games" / sc4_dirs,
                drive / "GOG Galaxy" / "Games" / sc4_dirs_alt,
                drive / "Games" / "GOG Games" / sc4_dirs,
                drive / "Games" / "GOG Games" / sc4_dirs_alt,
                drive / "GOG Games" / sc4_dirs,
                drive / "GOG Games" / sc4_dirs_alt,

                # Origin (holy crap Lois, they finally patched it!)
                drive / "Program Files" / "Origin Games" / sc4_dirs,
                drive / "Program Files" / "Origin Games" / sc4_dirs_alt,
                drive / "Program Files (x86)" / "Origin Games" / sc4_dirs,
                drive / "Program Files (x86)" / "Origin Games" / sc4_dirs_alt,
                drive / "Games" / "Origin Games" / sc4_dirs,
                drive / "Games" / "Origin Games" / sc4_dirs_alt,
                drive / "Origin Games" / sc4_dirs,
                drive / "Origin Games" / sc4_dirs_alt,

                # EA (apparently this is a thing now?)
                drive / "Program Files" / "EA Games" / sc4_dirs,
                drive / "Program Files" / "EA Games" / sc4_dirs_alt,
                drive / "Program Files (x86)" / "EA Games" / sc4_dirs,
                drive / "Program Files (x86)" / "EA Games" / sc4_dirs_alt,
                drive / "Games" / "EA Games" / sc4_dirs,
                drive / "Games" / "EA Games" / sc4_dirs_alt,
                drive / "EA Games" / sc4_dirs,
                drive / "EA Games" / sc4_dirs_alt,

                # Steam (patched, but has annoying DRM)
                drive / "Program Files" / steam_dirs / sc4_dirs,
                drive / "Program Files" / steam_dirs / sc4_dirs_alt,
                drive / "Program Files (x86)" / steam_dirs / sc4_dirs,
                drive / "Program Files (x86)" / steam_dirs / sc4_dirs_alt,
                drive / "Games" / "SteamLibrary" / steam_dirs / sc4_dirs,
                drive / "Games" / "SteamLibrary" / steam_dirs / sc4_dirs_alt,
                drive / "SteamLibrary" / steam_dirs / sc4_dirs,
                drive / "SteamLibrary" / steam_dirs / sc4_dirs_alt,

                # Maxis (probably not patched)
                drive / "Program Files" / "Maxis" / sc4_dirs,
                drive / "Program Files (x86)" / "Maxis" / sc4_dirs,
                drive / "Games" / "Maxis" / sc4_dirs,

                # Generic (probably pirated copies lol)
                drive / sc4_dirs,
                drive / sc4_dirs_alt,
                drive / "Games" / sc4_dirs,
                drive / "Games" / sc4_dirs_alt,
                drive / "My Games" / sc4_dirs,
                drive / "My Games" / sc4_dirs_alt,
                drive / "Game Library" / sc4_dirs,
                drive / "Game Library" / sc4_dirs_alt,
                drive / "Program Files" / sc4_dirs,
                drive / "Program Files" / sc4_dirs_alt,
                drive / "Program Files (x86)" / sc4_dirs,
                drive / "Program Files (x86)" / sc4_dirs_alt,

            ]

    else:

        # This list could be expanded if Linux/MacOS users want to put what
        # paths they use
        possible_paths: list[Path] = [

            # Custom (specified by the user)
            config_path,

            # Steam on Linux (runs through Proton)
            Path(
                "~/.local/share/Steam/steamapps/common/SimCity 4 Deluxe/Apps/"
                "SimCity 4.exe"
            ).expanduser(),

        ]

    # for possible_path in possible_paths:
    #     if possible_path.is_file():
    #         print(possible_path)

    # Return the FIRST path that exists in the list
    for possible_path in possible_paths:
        if possible_path.is_file():
            return possible_path

    # Return `None` if none of the paths exist
    return None


def start_sc4():
    """Attempts to find the install path of SimCity 4 and launches the game
    with custom launch parameters if found."""

    print("Starting SimCity 4...")

    # Variables related to game monitor exit, etc. etc.
    state.sc4mp_allow_game_monitor_exit_if_error = False
    state.sc4mp_game_exit_ovveride = False

    # Check if SC4 is already running
    try:
        if process_exists("simcity 4.exe"):
            show_error("SimCity 4 is already running!")
            return
    except Exception as e:
        show_error(e, no_ui=True)

    # Get path to SC4 using a list of possible paths
    path = get_sc4_path()

    # Cancel launch if path to SC4 not found
    if not path:
        show_error(
            "Path to SimCity 4 not found. Specify the correct path in "
            "settings."
        )
        return

    resw = state.sc4mp_config["SC4"]["resw"]
    resh = state.sc4mp_config["SC4"]["resh"]

    if 0 in (resw, resh):
        if state.sc4mp_ui:
            resw = state.sc4mp_ui.winfo_screenwidth()
            resh = state.sc4mp_ui.winfo_screenheight()
        else:
            resw = 1280
            resh = 800

    # Arguments set based on config settings
    arguments = [str(path),
                 # add trailing slash here because SC4 expects it
                 f'-UserDir:"{state.SC4MP_LAUNCHPATH}{os.sep}"',
                 '-intro:off',
                 '-CustomResolution:enabled',
                 f'-r{resw}x{resh}x32',
                 f'-CPUCount:{state.sc4mp_config["SC4"]["cpu_count"]}',
                 f'-CPUPriority:{state.sc4mp_config["SC4"]["cpu_priority"]}'
                 ]
    if state.sc4mp_config["SC4"]["fullscreen"]:
        arguments.append('-f')
    else:
        arguments.append('-w')
    # assumes that properties do not have spaces
    arguments.extend(
        state.sc4mp_config["SC4"]["additional_properties"].split()
    )

    # `True` if the game is installed using Steam
    steam_sc4 = is_steam_sc4(path)

    # Set to `True` once the game is launched successfully with the Steam
    # browser protocol
    steam_launch = False

    # If SC4 is installed through Steam, try to launch it using the Steam
    # browser protocol
    use_steam_browser_protocol = state.sc4mp_config["SC4"]["use_steam_browser_protocol"]
    if use_steam_browser_protocol == 2 or (use_steam_browser_protocol == 1 and steam_sc4):

        # Steam browser protocol command
        escaped_arguments = ' '.join(arguments[1:]).replace("\\", "\\\\").replace('"', '\\"')
        command = "steam://run/24780//" + escaped_arguments + "/"

        # Notify the user about the Steam dialog box that will popup
        # messagebox.showinfo(title=SC4MP_TITLE, message="Steam will now ask
        # your permission to launch SC4 with custom arguments.\n\nClick
        # \"Continue\" on the Steam dialog box to launch SC4.\n\nConnection
        # will be cancelled in 30 seconds if the game does not launch.")

        # Launch the game
        print(f"- using Steam browser protocol ('{command}').")
        try:
            steam_launch = webbrowser.open(command)
            if not steam_launch:
                print(
                    "[WARNING] Unable to launch SimCity 4 using the Steam browser "
                    "protocol (`webbrowser.open` returned `False`)."
                )
        except Exception as e:
            show_error(
                f"Unable to launch SimCity 4 using the Steam browser protocol.\n\n{e}",
                no_ui=True
            )

    # If SC4 isn't installed through Steam, or if launching it through the
    # Steam browser protocol didn't work, launch the SC4 exe directly
    if not steam_launch:

        # Regular command
        command = ' '.join(arguments)

        # Launch the game
        print(f"- launching directly ('{command}').")
        try:
            if is_windows():
                # `subprocess.run(arguments)` won't work on Windows for some
                # unknowable reason; `executable` stops Windows guessing where
                # the exe path ends
                subprocess.run(command, executable=arguments[0])
            else:
                # on Linux, the first String passed as argument must be a file
                # that exists
                subprocess.run(arguments)
        except PermissionError:
            show_error(
                "The launcher does not have the necessary privileges to launch "
                "SimCity 4. Try running the SC4MP Launcher as administrator."
            )

    else:

        # Using Steam SC4 otherwise
        steam_sc4 = True

    # Wait an extra 30 seconds if running the Steam version of SC4 (needed for
    # Steam browser protocol, also sometimes Steam isn't started yet)
    if steam_sc4:
        try:
            time.sleep(1)
            count = 0
            while (process_exists("Steam.exe")
                   and not process_exists("simcity 4.exe")
                   and count < 30):
                time.sleep(1)
                count += 1
        except Exception as e:
            show_error(e, no_ui=True)
            time.sleep(30)

    # Wait for SC4 to close if running the Steam version of SC4 (the Steam
    # version of SC4 spawns a separate process)
    if steam_sc4:
        state.sc4mp_allow_game_monitor_exit_if_error = True
        time.sleep(5)
        while True:
            if state.sc4mp_game_exit_ovveride:
                print(
                    "Exiting without checking whether SC4 is still running..."
                )
                return
            try:
                while process_exists("simcity 4.exe"):
                    time.sleep(1)
                break
            except Exception:
                show_error(
                    "An error occurred while checking if SC4 had exited yet.",
                    no_ui=True
                )
                time.sleep(10)

    # SimCity 4 has closed
    print("SimCity 4 closed.")


def is_steam_sc4(path: Path):

    # COMMON_STEAM_FILES = ["Steam.dll", "steam_api.dll", "steam_api64.dll",
    # "steam_appid.txt", "steamclient.dll", "steamclient64.dll"]

    # exec_dir = path.parent.parent
    # exec_dir_filenames = os.listdir(exec_dir)

    # for steam_filename in COMMON_STEAM_FILES:
    #    if steam_filename in exec_dir_filenames:
    #        return True

    return "steamapps" in [
        directory.name.lower() for directory in path.parents
    ]


def get_sc4_cfg_path() -> Path:  # TODO can this find the cfg for the origin version?
    """Returns the path to the `SimCity 4.cfg` file"""
    return Path(state.SC4MP_LAUNCHPATH) / "SimCity 4.cfg"


def get_sc4_cfg() -> dict:
    """Returns data parsed from the SimCity 4.cfg file"""
    return SC4Config(
        get_sc4_cfg_path(), error_callback=show_error
    ).get_simcity_4_cfg()


def get_last_region_name() -> str:
    """Returns the last open region stored in the `SimCity 4.cfg` file."""
    return get_sc4_cfg()["LastRegionName"]


def region_open(region) -> bool:
    """Checks if a given region is open in SC4."""
    return region == get_last_region_name()


def refresh_region_open() -> bool:
    """Checks if the refresh region is open in SC4"""
    return region_open("Refresh...")


def prep_region_config(path):

    try:

        REGION_NAME_PREFIX = "[SC4MP] "

        config = configparser.RawConfigParser()
        config.read(path)

        region_name = config.get("Regional Settings", "Name")

        if not region_name.startswith(REGION_NAME_PREFIX):

            config.set(
                "Regional Settings", "Name", REGION_NAME_PREFIX + region_name
            )

            with open(path, 'wt') as config_file:
                config.write(config_file)

    except Exception as e:

        raise ClientException(f"Failed to prepare region config at {path}.") from e


def sync_simcity_4_cfg(to_mp=False):

    try:

        # Get paths to singleplayer and multiplayer `SimCity 4.cfg` files
        sp_config_path = Path(
            "~/Documents/SimCity 4/SimCity 4.cfg"
        ).expanduser()
        mp_config_path = state.SC4MP_LAUNCHPATH / "SimCity 4.cfg"

        # Pick the source and destination based on whether the transfer is to
        # or from multiplayer
        if to_mp:
            source = sp_config_path
            destination = mp_config_path
        else:
            source = mp_config_path
            destination = sp_config_path

        # Copy the files
        print(f"\"{source}\" -> \"{destination}\"")
        if source.exists():
            if destination.exists():
                backup = destination.with_suffix(destination.suffix + ".bak")
                if not backup.exists():
                    shutil.copy(destination, backup)
                os.unlink(destination)
            shutil.copy(source, destination)

    except Exception as e:

        show_error(
            "An error occurred while transfering the SimCity 4 "
            f"config.\n\n{e}",
            no_ui=True
        )

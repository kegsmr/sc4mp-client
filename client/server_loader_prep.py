"""Steps that prepare plugins, regions and the game config after a
server's files are downloaded."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from core.util import md5
from client import state
from client.errors import ClientException, show_error
from client.sc4 import get_sc4_path, prep_region_config, sync_simcity_4_cfg
from client.utils import get_sc4mp_path, process_exists, purge_directory


class ServerLoaderPrep:
    """Plugin, region and config preparation steps of ServerLoader.

    Only used as a base class of ServerLoader; it is in its own module so
    that neither file gets too long.
    """

    def prep_plugins(self):

        # Get checksums of plugins installed to the top-level of the program
        # files plugins folder (to avoid dobule-loading DLLs)
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
                    shutil.copy(
                        default_plugin_file_path,
                        default_plugins_destination / f"default-{default_plugin_file_name}"
                    )
                    toplevel_plugins_checksums.append(default_plugin_checksum)
            except Exception as e:
                show_error(
                    f"Failed to load default plugin \"{default_plugin_file_name}\".\n\n{e}",
                    no_ui=True
                )

        # Copy DLLs from subfolders (DLL plugins do not load in subfolders)
        for path, basename in self.dll_plugin_paths:
            checksum = md5(path)
            if checksum not in toplevel_plugins_checksums:
                shutil.copy(
                    path,
                    default_plugins_destination / f"{basename}-{checksum}.dll"
                )
                toplevel_plugins_checksums.append(checksum)

        # Write server URL local plugin file
        # with open(get_sc4mp_path("sc4mp-local-server-url.dat"), "rb") as rfile:
        # data = rfile.read().replace(b"{\x00{\x00U\x00R\x00L\x00}\x00}",
        # bytes(self.server.server_url, encoding="utf-8"))
        #     with open(default_plugins_destination / "server-url.dat", "wb") as wfile:
        #         wfile.write(data)

    def prep_regions(self):

        # Declare instance variable to store the paths of the server region
        # subdirectories
        self.server.regions: list[Path] = []

        # Path to regions directory
        regions_directory = Path(state.SC4MP_LAUNCHPATH) / "Regions"

        # Loop through the server regions, add them to the server regions
        # instance variable and add prefixes to the region names in the region
        # config files
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
            save_directory = os.path.join(
                salvage_directory, os.listdir(salvage_directory)[-1]
            )

            # Pick the directory corresponding to the first region in the
            # failed save push (there should only be one anyway)
            region_directory = os.path.join(
                save_directory, os.listdir(save_directory)[0]
            )

            # Copy each file from the region directory to the `Downloads`
            # directory
            for filename in os.listdir(region_directory):
                shutil.copy(
                    os.path.join(region_directory, filename),
                    os.path.join(downloads_path, filename)
                )

        except Exception:

            pass  # show_error(e, no_ui=True)

        # Create the auxiliary regions for launcher functions (eg. refreshing)
        AUXILIARY_REGIONS = ["Refresh"]  # ["Backups", "Export", "Refresh"]
        for auxiliary_region in AUXILIARY_REGIONS:

            # Create the auxiliary region directory
            # TODO possible directory name conflicts?
            auxiliary_region_path = regions_directory / f"_{auxiliary_region}"
            auxiliary_region_path.mkdir(parents=True)

            # Copy the blank `config.bmp` file to the auxiliary region
            # directory
            shutil.copy(
                get_sc4mp_path("config.bmp"),
                auxiliary_region_path / "config.bmp"
            )

            # Create a `region.ini` file for the auxiliary region
            with open(get_sc4mp_path("region.ini"), "r") as template_config_file:

                # Read the contents of the template `region.ini`
                config_file_contents: str = template_config_file.read()

                # Replace the region name
                config_file_contents = config_file_contents.replace(
                    "New Region", f"{auxiliary_region}..."
                )

                # Write the file
                with open(auxiliary_region_path / "region.ini", "w") as config_file:
                    config_file.write(config_file_contents)

    def prep_config(self):

        try:

            # Get the path to the SimCity 4 config last used on this server
            config_name = f"{self.server.server_id}.cfg"
            server_config_path = state.SC4MP_LAUNCHPATH / "_Configs" / config_name

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

                # Copy the singleplayer config to multiplayer if it does not
                # exist
                if not mp_config_path.exists():
                    sync_simcity_4_cfg(to_mp=True)

        except Exception as e:

            show_error(
                f"An error occurred while preparing the config.\n\n{e}",
                no_ui=True
            )

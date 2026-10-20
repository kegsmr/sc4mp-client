"""Loading the user's config and preparing the launcher's directories and
database."""

from __future__ import annotations

from pathlib import Path

from core.config import Config
from client import state
from client.constants import SC4MP_CONFIG_DEFAULTS, SC4MP_CONFIG_PATH
from client.database import DatabaseManager
from client.errors import ClientException, show_error


def load_config():
    """Loads settings from the configuration file."""


    print("Loading config...")

    state.sc4mp_config = Config(
        SC4MP_CONFIG_PATH,
        SC4MP_CONFIG_DEFAULTS,
        error_callback=show_error,
        update_constants_callback=update_config_constants
    )


def update_config_constants(config):
    """For backwards compatibility. Updates the global config constants that are sometimes used internally."""


    state.SC4MP_LAUNCHPATH = config['STORAGE']['storage_path']
    state.SC4MP_LAUNCHRESW = config['SC4']['resw']
    state.SC4MP_LAUNCHRESH = config['SC4']['resh']
    state.SC4MP_CUSTOMPATH = config['SC4']['game_path']


def create_subdirectories() -> None:
    """Creates the required subdirectories in the launch directory if they do not yet exist."""

    print("Creating subdirectories...")

    directories = [
        Path("_Cache"),
        Path("_Configs"),
        Path("_Database"),
        Path("_Salvage"),
        Path("_Temp"),
        Path("_Temp") / "ServerList",
        Path("Plugins"),
        Path("Plugins") / "client",
        # Path("Plugins") / "default",
        Path("Plugins") / "server",
        Path("Regions")
    ]  # "SC4MPBackups", os.path.join("_Cache","Plugins"), os.path.join("_Cache","Regions")]

    # Update old directory names
    # if (os.path.exists(os.path.join(SC4MP_LAUNCHPATH, "_Profiles"))):
    #    os.rename(os.path.join(SC4MP_LAUNCHPATH, "_Database"), os.path.join(SC4MP_LAUNCHPATH, "_Database"))

    # Create new directories
    launchdir = Path(state.SC4MP_LAUNCHPATH)
    launchdir.mkdir(exist_ok=True, parents=True)
    for directory in directories:
        new_directory = launchdir / directory
        try:
            new_directory.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            raise ClientException("Failed to create SC4MP subdirectories.\n\n" + str(e)) from e

    # Create notice files
    with open(launchdir / "_Cache" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
        file.write("These files are OK to delete if you want to save disk space. You can also delete them in the launcher in the storage settings.")
    with open(launchdir / "_Configs" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
        file.write("These files are OK to delete, but some of your in-game settings may change if you do.")
    with open(launchdir / "_Temp" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
        file.write("These files are OK to delete if you want to save disk space. Don't do it while the launcher is running though.")
    with open(launchdir / "_Database" / "___DO NOT DELETE OR SHARE THESE FILES___", "w") as file:
        file.write("Deleting these files can cause you to lose access to your claims in servers you've joined. Only delete them if you know what you're doing.\n\nSharing these files with someone else will let that person access all your claims and mess with your cities. Don't do it!")
    with open(launchdir / "_Salvage" / "___DO NOT DELETE THESE FILES___", "w") as file:
        file.write("Deleting these files will make you unable to restore the salvaged savegames stored here. If you don't care about that, then go ahead and delete them.")


def load_database():

    print("Loading database...")

    state.sc4mp_servers_database = DatabaseManager(Path(state.SC4MP_LAUNCHPATH) / "_Database" / "servers.json")
    state.sc4mp_servers_database.start()


def update_config_value(section, item, value):
    """Updates a value in the config, attempting to convert it to the proper data type."""
    try:
        t = type(state.sc4mp_config[section][item])
        state.sc4mp_config[section][item] = t(value)
    except Exception:
        show_error(f'Invalid config value for "{item}" in section "{section}"', no_ui=True)

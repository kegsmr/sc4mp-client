"""The Server class: talks to one SC4MP server."""

from __future__ import annotations

import hashlib
import os
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import messagebox

from core.networking import ClientSocket, NetworkException
from core.util import sanitize_directory_name, sanitize_relpath
from client import state
from client.constants import SC4MP_SERVERS_DOMAIN, SC4MP_TITLE, SC4MP_VERSION
from client.errors import ClientException, show_error
from client.utils import get_bitmap_dimensions, load_json, random_string


def set_server_data(entry, server):
    """Updates the json entry for a given server with the appropriate values."""
    entry["host"] = server.host
    entry["port"] = server.port
    entry["server_name"] = server.server_name
    entry["server_description"] = server.server_description
    entry["server_url"] = server.server_url
    entry["server_version"] = server.server_version
    entry["password_enabled"] = server.password_enabled
    entry["user_plugins"] = server.user_plugins_enabled
    entry.setdefault("first_contact", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    entry["last_contact"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Server:
    """An interface for interaction with a server."""

    def __init__(self, host, port):

        self.host = host
        self.port = port

        self.fetched = False
        # self.stats = False
        self.password = None
        self.user_id = None

        self.categories = ["All"]
        if self.host == SC4MP_SERVERS_DOMAIN:
            self.categories.append("Official")

    def fetch(self):
        """Retreives basic information from a server and saves them as instance variables. Updates the json entry for the server if possible."""

        # Mark server as fetched
        self.fetched = True

        # Request server info
        try:
            with self.socket() as s:
                server_info = s.info()
        except Exception as e:
            raise ClientException("Unable to find server. Check the IP address and port, then try again.") from e

        # server_info = self.request("info")
        # if server_info is not None:
        #    try:
        #        server_info = json.loads("{"+ "{".join(server_info.split("{")[1:]))
        #        #print(server_info)
        #    except Exception:
        #        raise ClientException("Unable to fetch server info.")
        # else:
        #    raise ClientException("Unable to find server. Check the IP address and port, then try again.")

        self.server_id = sanitize_directory_name(server_info["server_id"])  # self.request("server_id")
        self.server_name = server_info["server_name"]  # self.request("server_name")
        self.server_description = server_info["server_description"]  # self.request("server_description")
        self.server_url = server_info["server_url"]  # self.request("server_url")
        self.server_version = server_info["server_version"]  # self.request("server_version")
        self.password_enabled = server_info["password_enabled"]  # self.request("password_enabled") == "y"
        self.private = server_info["private"]  # self.request("private") == "y"
        self.user_plugins_enabled = server_info["user_plugins_enabled"]  # self.request("user_plugins_enabled") == "y"
        try:
            self.claim_duration = server_info["claim_duration"]
            self.max_region_claims = server_info["max_region_claims"]
            self.godmode_filter = server_info["godmode_filter"]
        except KeyError:
            pass

        if self.server_id in state.sc4mp_servers_database.keys():
            self.password = state.sc4mp_servers_database[self.server_id].get("password", None)  # Needed for stat fetching private servers

        if self.password_enabled:
            self.categories.append("Private")
        else:
            self.categories.append("Public")

        # if (self.server_version != None):
        #    self.server_version = unformat_version(self.server_version)

        if self.fetched == True:
            try:
                self.update_database()
            except Exception as e:
                show_error("An error occurred while updating the server database.", no_ui=True)

    def fetch_stats(self):

        if not state.sc4mp_config["DEBUG"]["random_server_stats"]:

            download = self.fetch_temp()

            regions_path: Path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server_id / "Regions"

            server_time = self.time()

            mayors = []
            mayors_online = []
            claimed_area = 0
            total_area = 0
            for region in os.listdir(regions_path):
                try:
                    region_path = regions_path / region
                    region_config_path = region_path / "config.bmp"
                    region_dimensions = get_bitmap_dimensions(region_config_path)
                    region_database_path = region_path / "_Database" / "region.json"
                    region_database = load_json(region_database_path)
                    for coords in region_database.keys():
                        city_entry = region_database[coords]
                        if city_entry != None:
                            owner = city_entry["owner"]
                            locked = city_entry.get("locked", False)
                            area = city_entry["size"] ** 2
                            if locked:
                                total_area -= area
                            if owner != None:
                                if not locked:
                                    claimed_area += area
                                if owner not in mayors:
                                    mayors.append(owner)
                                modified = city_entry["modified"]
                                if modified != None:
                                    modified = datetime.strptime(modified, "%Y-%m-%d %H:%M:%S")
                                    if modified > server_time - timedelta(minutes=state.sc4mp_config["GENERAL"]["stat_mayors_online_cutoff"]) and owner not in mayors_online:
                                        mayors_online.append(owner)
                    total_area += region_dimensions[0] * region_dimensions[1]
                except Exception as e:
                    show_error(f"An error occurred while calculating region statistics for \"{region}\".", no_ui=True)

            self.stat_mayors = len(mayors)  # (random.randint(0,1000))

            self.stat_mayors_online = len(mayors_online)  # int(self.stat_mayors * (float(random.randint(0, 100)) / 100))

            try:
                self.stat_claimed = (float(claimed_area) / float(total_area))  # (float(random.randint(0, 100)) / 100)
            except ZeroDivisionError:
                self.stat_claimed = 1

            self.stat_download, self.stat_actual_download = download  # (random.randint(0, 10 ** 11))

        ping = self.ping()
        if ping != None:
            self.stat_ping = ping

        state.sc4mp_servers_database[self.server_id]["stat_mayors"] = self.stat_mayors
        state.sc4mp_servers_database[self.server_id]["stat_mayors_online"] = self.stat_mayors_online
        state.sc4mp_servers_database[self.server_id]["stat_claimed"] = self.stat_claimed
        state.sc4mp_servers_database[self.server_id]["stat_download"] = self.stat_download
        state.sc4mp_servers_database[self.server_id]["stat_actual_download"] = self.stat_actual_download
        state.sc4mp_servers_database[self.server_id]["stat_ping"] = self.stat_ping

    def fetch_temp(self):

        REQUESTS = ["plugins", "regions"]
        DIRECTORIES = ["Plugins", "Regions"]

        total_size = 0
        download_size = 0

        cache_files = os.listdir(os.path.join(state.SC4MP_LAUNCHPATH, "_Cache"))

        for type_, directory in zip(REQUESTS, DIRECTORIES):

            # Set destination
            destination = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server_id / directory

            # Receive file table
            with self.socket() as s:
                file_table = s.file_table(type_)

            # Get total and download size
            for entry in file_table:
                total_size += entry[1]
                if not entry[0] in cache_files:
                    download_size += entry[1]

            # Prune file table as necessary
            ft = []
            for entry in file_table:
                filename = Path(entry[2]).name
                if filename in ["region.json", "config.bmp"]:
                    ft.append(entry)
            file_table = ft

            # Receive files
            with self.socket() as s:

                for entry in s.file_table_data(type_, file_table):

                    # Get necessary values from entry
                    filesize = entry[1]
                    relpath = Path(entry[2])
                    chunks = entry[3]

                    # Set the destination
                    d = sanitize_relpath(Path(destination), relpath)

                    # Create the destination directory if necessary
                    d.parent.mkdir(parents=True, exist_ok=True)

                    # Delete the destination file if it exists
                    d.unlink(missing_ok=True)

                    # Receive the file
                    with d.open("wb") as dest:
                        for chunk in chunks:
                            dest.write(chunk)

        return (total_size, download_size)

    def update_database(self):
        """Updates the json entry for the server."""

        # Get database entry for server
        key = self.server_id
        entry = state.sc4mp_servers_database.get(key, dict())
        state.sc4mp_servers_database[key] = entry

        # Set server categories
        if "user_id" in entry.keys():
            self.categories.append("History")
        if entry.get("bookmarked", False):
            self.categories.append("Bookmarked")

        # Set values in database entry
        set_server_data(entry, self)

    def authenticate(self):

        # Get database entry for server
        key = self.server_id
        entry = state.sc4mp_servers_database.get(key, dict())
        state.sc4mp_servers_database[key] = entry

        # Get user_id
        user_id = None
        try:
            user_id = entry["user_id"]
        except Exception:
            user_id = random_string(32)

        # Get token
        token = None
        try:
            token = entry["token"]
        except Exception:
            pass

        # Verify server can produce the user_id from the hash of the user_id and token combined
        if token != None:
            hash = hashlib.sha256(((hashlib.sha256(user_id.encode()).hexdigest()[:32]) + token).encode()).hexdigest()
            with self.socket() as s:
                if s.user_id(hash) == hashlib.sha256(user_id.encode()).hexdigest()[:32]:
                    self.user_id = user_id
                else:
                    if not state.sc4mp_config["GENERAL"]["ignore_token_errors"]:
                        if state.sc4mp_ui:
                            if messagebox.askokcancel(title=SC4MP_TITLE, message="The server failed to authenticate.\n\nThe user ID corresponding to your last login could not be produced by the server. A recent rollback of the server, or a recent failed authentication attempt may be to blame.\n\nIf you proceed, your user ID may become compromised.", icon="warning"):
                                self.user_id = user_id
                            else:
                                raise ClientException("Connection cancelled.")
                        else:
                            raise ClientException("Invalid token.")  # "Authentication error."
        else:
            self.user_id = user_id

        # Get the new token
        with self.socket() as s:
            token = s.token(
                user_id=self.user_id, version=SC4MP_VERSION,
                password=self.password
            )

        # Raise exception if no token is received
        # if len(token) < 1:
        #     raise ClientException("Authentication failed.\n\nThe reason could be any of the following:\n(1)   You are banned from this server.\n(2)   You have too many different user accounts on this server.\n(3)   There is a problem with your internet connection.")

        # Set user_id and token in the database entry
        entry["user_id"] = user_id
        entry["token"] = token
        entry.setdefault("first_logon", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        entry["last_logon"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def ping(self):

        try:
            with self.socket() as s:
                start = time.time()
                s.ping()
                end = time.time()
                self.server_ping = round(1000 * (end - start))
                return self.server_ping
        except (NetworkException, socket.error):
            return None

    def time(self):

        try:

            with self.socket() as s:
                return s.time()

        except Exception as e:

            show_error("Unable to get server time, using local time instead.", no_ui=True)

            return datetime.now()

    def socket(self) -> ClientSocket:

        s = ClientSocket((self.host, self.port))

        s.set_headers(
            version=SC4MP_VERSION,
            user_id=self.user_id,
            password=self.password
        )

        return s

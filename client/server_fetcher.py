"""Threads that fetch and ping one server for the server browser."""

from __future__ import annotations

import random
import threading as th
import time
from typing import TYPE_CHECKING

from core.util import set_thread_name
from client import state
from client.errors import ClientException, show_error
from client.server import Server

if TYPE_CHECKING:
    # Only needed for type hints. Importing it for real would be a
    # circular import.
    from client.server_list import ServerList


class ServerFetcher(th.Thread):

    def __init__(self, parent: ServerList, server: Server):

        th.Thread.__init__(self)

        self.parent = parent
        self.server = server

        self.setDaemon(True)

    def run(self):

        try:

            try:

                set_thread_name("SfThread")

                print(f"Fetching {self.server.host}:{self.server.port}...")

                # print("- fetching server info...")

                try:

                    self.server.fetch()

                    if not self.server.fetched:
                        raise ClientException("Server is not fetched.")

                except Exception as e:

                    if (self.server.host, self.server.port) in self.parent.saved_servers.keys():

                        self.server.server_id = self.parent.saved_servers.pop(
                            (self.server.host, self.server.port)
                        )

                        server_entry: dict = state.sc4mp_servers_database[self.server.server_id]

                        if "user_id" in server_entry.keys():

                            self.server.categories = ["Offline", "History"]  # "All"

                            self.server.server_name = server_entry.get(
                                "server_name", f"{self.server.host}:{self.server.port}"
                            )
                            self.server.server_description = server_entry.get(
                                "server_description", ""
                            )
                            self.server.server_url = server_entry.get("server_url", "")

                            self.parent.fetched_servers.append(self.server)

                            self.parent.offline_server_count += 1

                    raise ClientException("Server not found.") from e

                if self.parent.end:
                    raise ClientException(
                        "The parent thread was signaled to end."
                    )

                self.server.categories.append("Online")

                # print("- populating server statistics")

                if state.sc4mp_config["DEBUG"]["random_server_stats"]:

                    self.server.stat_mayors = random.randint(0, 1000)
                    self.server.stat_mayors_online = int(
                        self.server.stat_mayors * (float(random.randint(0, 100)) / 100)
                    )
                    self.server.stat_claimed = float(random.randint(0, 100)) / 100
                    self.server.stat_download = random.randint(0, 10 ** 11)
                    self.server.stat_actual_download = int(
                        self.server.stat_download * (float(random.randint(0, 100)) / 100)
                    )
                    self.server.stat_ping = random.randint(0, 300)

                else:

                    # if not self.server.private:
                    try:
                        server_entry = state.sc4mp_servers_database[self.server.server_id]
                        self.server.stat_ping = server_entry["stat_ping"]
                        self.server.stat_mayors = server_entry["stat_mayors"]
                        self.server.stat_mayors_online = server_entry["stat_mayors_online"]
                        self.server.stat_claimed = server_entry["stat_claimed"]
                        self.server.stat_download = server_entry["stat_download"]
                        self.server.stat_actual_download = server_entry["stat_actual_download"]
                    except Exception:
                        pass
                    # else:
                    #    try:
                    # self.server.stat_ping =
                    # sc4mp_servers_database[self.server.server_id]["stat_ping"]
                    #    except Exception:
                    #        pass

                # print("- adding server to server list...")

                try:
                    self.parent.fetched_servers.append(self.server)
                except Exception as e:
                    raise ClientException("Unable to add server to server list.") from e

                # print("- starting server pinger...")

                try:
                    ServerPinger(self.parent, self.server).start()
                except Exception as e:
                    raise ClientException("Unable to start server pinger.") from e

                # print("- fetching server list...")

                try:
                    self.server_list()
                except Exception as e:
                    raise ClientException("Unable to fetch server list.") from e

                # if not self.server.private:

                    # print("- fetching server stats...")

                try:
                    self.fetch_stats()
                except Exception as e:
                    print(
                        "[WARNING] Unable to fetch server stats for "
                        f"{self.server.host}:{self.server.port}! " + str(e)
                    )

                # print("- done.")

            except Exception as e:

                print(
                    f"[WARNING] Failed to fetch {self.server.host}:{self.server.port}! " + str(e)
                )

            self.parent.server_fetchers -= 1

        except Exception as e:

            show_error(
                "A server fetcher thread encountered an unexpected "
                f"error.\n\n{e}"
            )

    def fetch_stats(self):

        self.server.fetch_stats()

    def server_list(self):

        with self.server.socket() as s:
            for host, port in s.server_list():
                self.parent.unfetched_servers.append((host, port))


class ServerPinger(th.Thread):

    def __init__(self, parent, server):

        th.Thread.__init__(self)

        self.parent = parent
        self.server = server

        self.setDaemon(True)

    def run(self):

        try:

            set_thread_name("SpThread")

            while not self.parent.end:
                time.sleep(len(self.parent.servers) + 1)
                if not self.parent.pause:
                    # print(f"Pinging {self.server.host}:{self.server.port}")
                    ping = self.server.ping()
                    if ping is not None:
                        self.server.stat_ping = ping  # int((self.server.stat_ping + ping) / 2)
                        state.sc4mp_servers_database[self.server.server_id]["stat_ping"] = ping

        except Exception as e:

            show_error(
                "A server pinger thread encountered an unexpected "
                f"error\n\n{e}",
                no_ui=True
            )

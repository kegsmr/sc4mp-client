"""Threads that fill the server browser: fetching, pinging and ranking
servers."""

from __future__ import annotations

import random
import threading as th
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from core.util import format_filesize, format_time_ago, set_thread_name
from client import state
from client.constants import SC4MP_DELAY, SC4MP_SERVERS
from client.errors import ClientException, show_error
from client.server import Server
from client.utils import arp, format_download_size, get_sc4mp_path

if TYPE_CHECKING:
    # Only needed for type hints. Importing it for real would be a
    # circular import.
    from client.ui.server_list import ServerListUI


class ServerList(th.Thread):

    def __init__(self, ui, kill=None):

        th.Thread.__init__(self)

        self.ui: ServerListUI = ui

        if self.ui is not None and kill is None:
            self.ui.label["text"] = 'Getting server list...'

        self.setDaemon(True)

        self.end = False
        self.ended = False
        self.pause = False

        self.servers: dict[str:Server] = {}

        self.unfetched_servers: list[tuple] = SC4MP_SERVERS.copy()

        self.saved_servers: dict[tuple:str] = {}

        self.fetched_servers: list[tuple] = []
        self.tried_servers: list[tuple] = []
        self.hidden_servers: list[tuple] = []

        self.offline_server_count = 0

        self.server_fetchers = 0

        self.stat_mayors = dict()
        self.stat_mayors_online = dict()
        self.stat_claimed = dict()
        self.stat_actual_download = dict()
        self.stat_ping = dict()

        if self.ui:

            self.blank_icon = tk.PhotoImage(file=get_sc4mp_path("blank-icon.png"))
            self.lock_icon = tk.PhotoImage(file=get_sc4mp_path("lock-icon.png"))
            self.official_icon = tk.PhotoImage(file=get_sc4mp_path("official-icon.png"))
            self.error_icon = tk.PhotoImage(file=get_sc4mp_path("error-icon.png"))

            self.rank_bars = {}
            self.rank_bar_images = [
                tk.PhotoImage(file=get_sc4mp_path(f"rank-{i}.png")) for i in range(6)
            ]
            self.ui.tree.bind("<<TreeviewSelect>>", self.update_rank_bars)
            self.ui.tree.bind("<MouseWheel>", self.update_rank_bars)

        self.temp_path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList"

        self.kill = kill

        self.sort_mode_changed = False

    def run(self):

        try:

            set_thread_name("SLThread", enumerate=False)

            self.lan_servers = []
            if state.sc4mp_config["GENERAL"]["scan_lan"]:
                try:
                    # localhost and every LAN address, on each default port
                    lan_servers = []
                    for port in range(7240, 7250):
                        for row in [("localhost", None, None)] + arp():
                            lan_servers.append((row[0], port))
                    self.lan_servers = lan_servers
                except Exception:
                    show_error(
                        "An error occurred while scanning for LAN servers, only internet "
                        "servers will be shown.",
                        no_ui=True
                    )

            delete_server_ids = []
            for server_id in reversed(state.sc4mp_servers_database.keys()):
                server_entry = state.sc4mp_servers_database[server_id]
                if ((server_entry.get("user_id", None) is not None)
                        or ("last_contact" not in server_entry.keys())
                        or (datetime.strptime(server_entry["last_contact"], "%Y-%m-%d %H:%M:%S")
                            + timedelta(days=30) > datetime.now())):
                    host = server_entry["host"]
                    port = server_entry["port"]
                    self.unfetched_servers.append((host, port))
                    if state.sc4mp_config["GENERAL"]["show_offline_servers"]:
                        self.saved_servers.setdefault((host, port), server_id)
                else:
                    delete_server_ids.append(server_id)
            for delete_server_id in delete_server_ids:
                state.sc4mp_servers_database.pop(delete_server_id)

            if self.kill is not None:
                self.kill.end = True
                while not self.kill.ended:
                    time.sleep(SC4MP_DELAY)
                self.clear_tree()

            # try: #TODO is this needed?
            #    purge_directory(self.temp_path)
            # except Exception as e:
            #    show_error("Error deleting temporary server list files.", no_ui=True)

            print("Fetching servers...")

            while not self.end:

                if not self.pause:

                    # Enable or disable buttons and update labels
                    server_id = self.ui.tree.focus()
                    if server_id == "" or server_id not in self.servers.keys():
                        self.ui.connect_button['state'] = tk.DISABLED
                        self.ui.details_button['state'] = tk.DISABLED
                        self.ui.address_label["text"] = ""
                        self.ui.description_label["text"] = ""
                        self.ui.url_label["text"] = ""
                    else:
                        self.ui.connect_button['state'] = tk.NORMAL
                        if "Offline" in self.servers[server_id].categories:
                            self.ui.address_label["text"] = "Offline"
                            self.ui.address_label["fg"] = "red"
                            self.ui.details_button['state'] = tk.DISABLED
                        else:
                            selected_server = self.servers[server_id]
                            self.ui.address_label["text"] = (
                                selected_server.host + ":" + str(selected_server.port)
                            )
                            self.ui.address_label["fg"] = "gray"
                            self.ui.details_button['state'] = tk.NORMAL
                        self.ui.description_label["text"] = (
                            self.servers[server_id].server_description
                        )
                        self.ui.url_label["text"] = self.servers[server_id].server_url

                    # Add all fetched servers to the server dictionary if not already present
                    while len(self.fetched_servers) > 0:
                        fetched_server = self.fetched_servers.pop(0)
                        fetched_id = fetched_server.server_id
                        if (fetched_id not in self.servers.keys()
                                or not self.servers[fetched_id].fetched):
                            self.servers[fetched_id] = fetched_server

                    # Fetch the next unfetched server
                    for unfetched_servers in [self.unfetched_servers, self.lan_servers]:
                        if self.server_fetchers < 25:  # 100 #TODO make configurable?
                            if len(unfetched_servers) > 0:
                                unfetched_server = unfetched_servers.pop(0)
                                if unfetched_server not in self.tried_servers:
                                    self.tried_servers.append(unfetched_server)
                                    self.server_fetchers += 1
                                    ServerFetcher(
                                        self, Server(unfetched_server[0], unfetched_server[1])
                                    ).start()

                    # Clear the tree if sort mode changed
                    if self.sort_mode_changed:
                        self.sort_mode_changed = False
                        self.clear_tree()

                    # Update stats
                    server_ids = self.servers.keys()
                    for server_id in server_ids:
                        try:
                            update_server = self.servers[server_id]
                            self.stat_mayors[server_id] = update_server.stat_mayors
                            self.stat_mayors_online[server_id] = update_server.stat_mayors_online
                            self.stat_actual_download[server_id] = (
                                update_server.stat_actual_download
                            )
                            self.stat_claimed[server_id] = update_server.stat_claimed
                            self.stat_ping[server_id] = update_server.stat_ping
                            self.calculate_rating(update_server)
                        except Exception:  # Exception as e:
                            # show_error(e)
                            try:
                                self.stat_ping[server_id] = update_server.stat_ping
                                self.calculate_rating(update_server)
                            except Exception:
                                pass

                    # Add missing rows to the tree
                    server_ids = self.servers.keys()
                    filter = self.ui.combo_box.get()
                    if filter == self.ui.combo_box.PLACEHOLDER_TEXT:
                        filter = ""
                    for server_id in server_ids:
                        # (len(filter) < 1 or (not self.filter(self.servers[server_id],
                        # self.filters(filter)))):
                        if ((not self.ui.tree.exists(server_id))
                                and (not self.filter(self.servers[server_id],
                                                     self.filters(filter)))):
                            # while len(self.ui.tree.get_children()) >= 50:
                            #    self.ui.tree.delete(self.ui.tree.get_children()[-1])
                            server = self.servers[server_id]
                            tags = []
                            if "Offline" in server.categories:
                                image = self.error_icon
                                tags.append("red")
                            elif server.password_enabled:
                                image = self.lock_icon
                            elif "Official" in server.categories:
                                image = self.official_icon
                            else:
                                image = self.blank_icon
                            values = self.format_server(server)
                            self.ui.tree.insert(
                                "",
                                self.in_order_index(server),
                                server_id,
                                text=server.server_name,
                                values=values,
                                image=image,
                                tags=tuple(tags)
                            )

                    # Filter the tree
                    filter = self.ui.combo_box.get()
                    if filter == self.ui.combo_box.PLACEHOLDER_TEXT:
                        filter = ""
                    # if len(filter) > 0:
                    try:
                        category, search_terms = self.filters(filter)
                        # print("Filtering by \"" + category + "\" and " +
                        # str(search_terms) + "...")
                        if category == "History":
                            self.ui.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#6")
                            # self.ui.tree.column("#5", width=0)
                            # self.ui.tree.column("#6", width=93)
                            if self.ui.tree.sort == "Rank":
                                self.ui.tree.sort = "Joined"
                                self.clear_tree()
                        else:
                            self.ui.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#5")
                            # self.ui.tree.column("#5", width=93)
                            # self.ui.tree.column("#6", width=0)
                            if self.ui.tree.sort == "Joined":
                                self.ui.tree.sort = "Rank"
                                self.clear_tree()
                        server_ids = self.ui.tree.get_children()
                        for server_id in server_ids:
                            hide = self.filter(self.servers[server_id], (category, search_terms))
                            if (hide
                                    and (server_id in self.ui.tree.get_children())
                                    and (server_id not in self.hidden_servers)):
                                self.hidden_servers.append(server_id)
                                self.ui.tree.delete(server_id)
                            elif (not hide) and (server_id in self.hidden_servers):
                                self.hidden_servers.remove(server_id)
                                # self.ui.tree.reattach(server_id,
                                # self.ui.tree.parent(server_id),
                                # self.in_order_index(self.servers[server_id]))
                    except Exception:
                        show_error(
                            "An error occurred while filtering the server list.", no_ui=True
                        )
                    # elif len(self.hidden_servers) > 0:
                    #    server_ids = self.hidden_servers
                    #    for server_id in server_ids:
                    #        self.hidden_servers.remove(server_id)
                    # #self.ui.tree.reattach(server_id,
                    # self.ui.tree.parent(server_id),
                    # self.in_order_index(self.servers[server_id]))

                    # Sort the tree
                    if not self.sorted():
                        # print("Sorting...")
                        server_ids = self.ui.tree.get_children()
                        for index in range(len(server_ids) - 1):
                            server_a_id = server_ids[index]
                            server_b_id = server_ids[index + 1]
                            server_a = self.servers[server_a_id]
                            server_b = self.servers[server_b_id]
                            if not self.in_order(server_a, server_b):
                                self.ui.tree.move(
                                    server_b_id, self.ui.tree.parent(server_b_id), index
                                )
                        """server_indices = dict()
                        for server_id in server_ids:
                            server_indices[server_id] = server_ids.index(server_id)
                        self.sort(server_indices)
                        for server_id in server_ids:
                            if (not server_id in self.hidden_servers):
                                self.ui.tree.move(server_id, self.ui.tree.parent(server_id),
                                    server_indices[server_id])"""

                    # Update the tree
                    server_ids = self.ui.tree.get_children()
                    for server_id in server_ids:
                        server = self.servers[server_id]
                        self.ui.tree.item(server_id, values=self.format_server(server))

                    # Update primary label
                    if len(self.servers) > self.offline_server_count:
                        # if len(self.hidden_servers) < len(self.servers):
                        self.ui.label["text"] = (
                            'To get started, select a server below and click "Connect"'
                        )
                        # else:
                        #    self.ui.label["text"] = 'No servers found'
                    else:
                        self.ui.address_label["text"] = ""
                        self.ui.description_label["text"] = ""
                        self.ui.url_label["text"] = ""
                        if self.server_fetchers > 0:
                            self.ui.label["text"] = 'Getting server list...'
                        else:
                            # Select "Servers" then "Connect..." in the menu
                            # bar to connect to a server.'
                            self.ui.label["text"] = 'No servers found'

                    # Update rank bars
                    self.update_rank_bars()

                # Delay
                time.sleep(SC4MP_DELAY)

            for canvas in self.rank_bars.values():
                canvas.destroy()

            self.ended = True

        except Exception as e:

            try:
                self.ended = True
            except Exception:
                pass

            show_error(f"An error occurred while fetching servers.\n\n{e}")  # , no_ui=True)

    def clear_tree(self):

        self.ui.tree.delete(*self.ui.tree.get_children())

    def filters(self, filter):

        if len(filter) > 0:
            search_terms = filter.split(" ")
            category = "All"
            if len(search_terms) > 0:
                if search_terms[0] == "category:":
                    if len(search_terms) > 1:
                        category = search_terms[1].lower().capitalize()
                        for count in range(2):
                            search_terms.pop(0)
                    else:
                        search_terms.pop(0)
            for index in range(len(search_terms)):
                if search_terms[index] == "":
                    search_terms.pop(index)
            return category, search_terms
        else:
            return "All", []

    def filter(self, server: Server, filters: list[str]):

        category = filters[0]
        search_terms = filters[1]
        search_fields = [
            server.server_name, server.server_description, server.server_url,
            server.server_id, server.host
        ]
        if len(search_terms) > 0:
            for search_field in search_fields:
                search_field = search_field.lower()
                for search_term in search_terms:
                    search_term = search_term.lower()
                    if search_term in search_field and category in server.categories:
                        return False
        elif category in server.categories:
            return False
        return True

    def sorted(self):

        server_ids = self.ui.tree.get_children()
        if len(server_ids) < 2:
            return True
        else:
            for index in range(len(server_ids) - 1):
                server_a_id = server_ids[index]
                server_b_id = server_ids[index + 1]
                server_a = self.servers[server_a_id]
                server_b = self.servers[server_b_id]
                if not self.in_order(server_a, server_b):
                    return False
            return True

    def sort(self, server_indices):  # TODO doesnt work in one pass!
        """deprecated"""
        server_ids = list(server_indices.keys())
        index_a = 0
        while index_a < len(server_ids):
            server_a_id = server_ids[index_a]
            server_a = self.servers[server_a_id]
            index_b = 0
            while index_b < index_a:
                server_b_id = server_ids[index_b]
                server_b = self.servers[server_b_id]
                if not self.in_order(server_b, server_a):
                    break
                index_b += 1
            server_ids[index_a], server_ids[index_b] = server_ids[index_b], server_ids[index_a]
            index_a += 1
        for index in range(len(server_ids)):
            server_id = server_ids[index]
            server_indices[server_id] = index

    def in_order(self, server_a, server_b):

        server_a_sort_value = self.get_sort_value(server_a)
        server_b_sort_value = self.get_sort_value(server_b)
        if server_a_sort_value is None and server_b_sort_value is None:
            return True
        elif server_a_sort_value is None:
            return False
        elif server_b_sort_value is None:
            return True
        else:
            if not self.ui.tree.reverse_sort:
                return server_a_sort_value >= server_b_sort_value
            else:
                return server_a_sort_value <= server_b_sort_value

    def in_order_index(self, server):

        if self.get_sort_value(server) is not None:
            existing_server_ids = self.ui.tree.get_children()
            for index in range(len(existing_server_ids)):
                existing_server_id = existing_server_ids[index]
                existing_server = self.servers[existing_server_id]
                if self.in_order(server, existing_server):
                    return index
        return "end"

    def get_sort_value(self, server):

        sort_mode = self.ui.tree.sort
        try:
            if sort_mode == "Name":
                return server.server_name
            elif sort_mode == "Mayors":
                return server.stat_mayors
            elif sort_mode == "Claimed":
                return server.stat_claimed
            elif sort_mode == "Download":
                if state.sc4mp_config["GENERAL"]["show_actual_download"]:
                    return server.stat_actual_download
                else:
                    return server.stat_download
            elif sort_mode == "Ping":
                return server.stat_ping
            elif sort_mode == "Joined":
                return server.last_logon
            else:
                return server.rating
        except Exception:
            return None

    def format_server(self, server):

        def mayors_cell():
            if server.stat_mayors_online > 0:
                return str(server.stat_mayors) + " (" + str(server.stat_mayors_online) + ")"
            else:
                return str(server.stat_mayors)

        def download_cell():
            if state.sc4mp_config["GENERAL"]["show_actual_download"]:
                return format_download_size(server.stat_actual_download)
            else:
                return format_filesize(server.stat_download)

        functions = [
            mayors_cell,
            lambda: str(int(server.stat_claimed * 100)) + "%",
            download_cell,
            lambda: str(server.stat_ping) + "ms",
            # (lambda: "" if sc4mp_config["GENERAL"]["show_rank_bars"] else
            # lambda: str(round(server.rating, 1))), # + " ⭐️",
            lambda: str(round(server.rating, 1)),
            lambda: self.format_server_join_time(server)
        ]
        if state.sc4mp_config["GENERAL"]["show_rank_bars"]:
            functions[4] = lambda: ""
        cells = []
        for function in functions:
            try:
                cells.append(function())
            except Exception:  # Exception as e:
                # show_error(e)
                cells.append("...")  # cells.append("")
        return cells

    def format_server_join_time(self, server: Server):

        try:
            last_logon = server.last_logon
        except AttributeError:
            server_entry = state.sc4mp_servers_database.get(server.server_id, {})
            last_logon = server_entry.get("last_logon", None)

        server.last_logon = last_logon

        if last_logon:
            last_logon = datetime.strptime(last_logon, "%Y-%m-%d %H:%M:%S")

        return format_time_ago(last_logon)

    def calculate_rating(self, server):

        try:

            try:
                mayors = self.max_category(server.stat_mayors, self.stat_mayors.values())
                mayors_online = self.max_category(
                    server.stat_mayors_online, self.stat_mayors_online.values()
                )
                categories = [
                    .5 * (mayors) * (mayors_online + 1),
                    self.min_category(server.stat_claimed, self.stat_claimed.values()),
                    self.min_category(
                        server.stat_actual_download, self.stat_actual_download.values()
                    ),
                    self.min_category(server.stat_ping, self.stat_ping.values()),
                ]
                rating = 1 + sum(categories)
            except Exception:
                rating = 1 + self.min_category(server.stat_ping, self.stat_ping.values())

            try:
                server.rating = ((99 * server.rating) + rating) / 100
            except Exception:
                server.rating = rating

        except Exception:
            pass

    def max_category(self, item, array):

        item = float(item)
        try:
            return (item - min(array)) / (max(array) - min(array))
        except Exception:
            return 1.0

    def min_category(self, item, array):

        item = float(item)
        try:
            return 1.0 - ((item - min(array)) / (max(array) - min(array)))
        except Exception:
            return 1.0

    def update_rank_bars(self, event=None):

        RANK_COLUMN_ID = "#5"

        CUTOFF_Y = 260

        OFFSET_X = 18
        OFFSET_Y = 154

        IMAGE_W = 29
        IMAGE_H = 12

        CELL_W = 93
        CELL_H = 20

        # For passing clicks from the canvas to the underlying row in the tree
        def handle_click(event):

            # Get the `server_id` associated with the canvas
            canvas = event.widget
            server_id = canvas.server_id

            # Select the row which the canvas is placed on
            self.ui.tree.selection_set([server_id])
            self.ui.tree.focus(server_id)

            # Call the event handler for a single click in `ServerListUI`
            self.ui.handle_single_click(event)

        def scheduled_update():

            # Allow the function to be scheduled again
            self.ui.rank_bar_update_scheduled = False

            # Keep the old rank bars so they can be deleted after the new ones are created
            r = self.rank_bars

            # Reset the list for new rank bars
            self.rank_bars = {}

            # If "Rank" column is being displayed
            if RANK_COLUMN_ID in self.ui.tree["displaycolumns"]:

                # Loop through rows in the tree by their `server_id`
                for server_id in self.ui.tree.get_children():

                    try:

                        # Try to get the server rank, if it blows up (no stats, probably), use `0`
                        try:
                            rank = round(self.servers[server_id].rating)
                        except Exception:
                            rank = 0

                        # Needed to choose canvas bgcolor
                        selected = server_id in self.ui.tree.selection()

                        # Get the bounding box of the cell in the "Rank" column
                        x, y, w, h = self.ui.tree.bbox(server_id, column=RANK_COLUMN_ID)

                        # If row is visible
                        if y < CUTOFF_Y:

                            # Unique identifier for the canvas
                            key = (x, y, w, h, rank, selected)

                            # If the canvas doesn't need to be updated, use the old one
                            if key in r.keys():

                                self.rank_bars[key] = r.pop(key)

                            # Otherwise, create a new one
                            else:

                                canvas = tk.Canvas(
                                    width=IMAGE_W,
                                    height=IMAGE_H,
                                    bd=0,
                                    bg=("#0078D7" if selected else "white"),
                                    highlightthickness=0,
                                    relief='flat'
                                )

                                # For click passthrough to the underlying row
                                canvas.server_id = server_id
                                canvas.bind("<Button-1>", handle_click)

                                # Create the rank bar image associated with the rank value
                                canvas.image = self.rank_bar_images[rank]
                                canvas.create_image(0, 0, anchor="nw", image=canvas.image)
                                canvas.place(
                                    x=x + OFFSET_X + ((CELL_W - IMAGE_W) / 2),
                                    y=y + OFFSET_Y + ((CELL_H - IMAGE_H) / 2),
                                )

                                # Store the canvas so it can be deleted later, when needed
                                self.rank_bars[key] = canvas

                    # Can't remember why I put this here. I guess we don't care about `ValueErrors`
                    except ValueError:
                        pass

                    # Quietly report all errors
                    except Exception as e:
                        show_error(e, no_ui=True)

            # Delete all old rank bars
            for canvas in r.values():
                canvas.destroy()

        # Running the function from this thread seems to cause CTDs with
        # 0x0000005 access violations, so we use the `after` method instead
        if self.ui and state.sc4mp_config["GENERAL"]["show_rank_bars"]:
            if (not hasattr(self.ui, "rank_bar_update_scheduled")
                    or not self.ui.rank_bar_update_scheduled):
                self.ui.rank_bar_update_scheduled = True
                self.ui.after(0, scheduled_update)


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
                    raise ClientException("The parent thread was signaled to end.")

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

            show_error(f"A server fetcher thread encountered an unexpected error.\n\n{e}")

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
                f"A server pinger thread encountered an unexpected error\n\n{e}", no_ui=True
            )

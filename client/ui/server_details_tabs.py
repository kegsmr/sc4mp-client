"""Mayors, cities and files tabs of the server details window."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Union

from core.util import format_time_ago
from client import state
from client.constants import SC4MP_VERSION
from client.errors import ClientException, show_error
from client.ui.statistics_tree import StatisticsTreeUI
from client.utils import format_download_size


class ServerDetailsTabs:
    """Builds the Mayors, Cities and Files tabs of ServerDetailsUI.

    Only used as a base class of ServerDetailsUI; it is in its own module so
    that neither file gets too long. It uses the window's attributes (server,
    notebook, time, ...).
    """

    def create_notebook_frames(self):

        try:

            self.time = self.server.time()

            self.create_mayors_frame()
            self.create_cities_frame()
            # self.create_files_frame()

        except Exception as e:

            show_error(
                f"An error occurred while creating notebook frames.\n\n{e}",
                no_ui=True
            )

    def create_mayors_frame(self):

        server_list_path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList"
        regions_directory: Path = server_list_path / self.server.server_id / "Regions"

        if not regions_directory.exists():
            return

        mayors = {}
        for region in os.listdir(regions_directory):

            region_database: Union[dict, None] = self.load_json(
                regions_directory / region / "_Database" / "region.json"
            )

            if not region_database:
                continue

            for entry in region_database.values():
                if entry is not None:
                    user_id = entry.get("owner", None)
                    if user_id is not None:

                        mayors.setdefault(user_id, {})
                        mayor = mayors[user_id]

                        mayor.setdefault("name", "Defacto")

                        mayor.setdefault("last_online", None)
                        time_format = "%Y-%m-%d %H:%M:%S"
                        last_online = mayor["last_online"]
                        if (last_online is None
                                or datetime.strptime(entry["modified"], time_format)
                                > datetime.strptime(last_online, time_format)):
                            if entry["mayor_name"] != entry.get("last_mayor_name", None):
                                mayor["name"] = entry["mayor_name"]
                            mayor["last_online"] = entry["modified"]

                        mayor.setdefault("residential_population", 0)
                        mayor["residential_population"] += entry["residential_population"]

                        mayor.setdefault("commercial_population", 0)
                        mayor["commercial_population"] += entry["commercial_population"]

                        mayor.setdefault("industrial_population", 0)
                        mayor["industrial_population"] += entry["industrial_population"]

                        mayor.setdefault("total_population", 0)
                        mayor["total_population"] += entry["population"]

                        mayor.setdefault("mayor_rating", 0)
                        mayor["mayor_rating"] += (
                            entry["residential_population"] * entry["mayor_rating"]
                        )

                        mayor.setdefault("tiles_claimed", 0)
                        mayor["tiles_claimed"] += 1

                        mayor.setdefault("area_claimed", 0)
                        mayor["area_claimed"] += entry["size"] ** 2

                        mayor.setdefault("funds", 0)
                        mayor["funds"] += entry.get("total_funds", 0)

        for entry in mayors.values():
            if entry["residential_population"] > 0:
                entry["mayor_rating"] = round(
                    entry["mayor_rating"] / entry["residential_population"]
                )
            else:
                entry["mayor_rating"] = 0

        m = {}
        for user_id, entry in mayors.items():
            m[user_id] = [
                entry["name"],
                entry["area_claimed"],
                entry["mayor_rating"],
                entry['funds'],
                entry['residential_population'],
                entry['commercial_population'],
                entry['industrial_population'],
                entry['last_online'],
            ]
        mayors = m

        if len(mayors.values()) < self.server.stat_mayors:
            raise ClientException("Wrong number of mayors.")

        columns = [
            (
                "#0",
                "Name",
                250,
                "w"
            ),
            (
                "#1",
                "Claimed",
                100,
                "center"
            ),
            (
                "#2",
                "Rating",
                100,
                "center"
            ),
            (
                "#3",
                "Funds",
                100,
                "center"
            ),
            (
                "#4",
                "Residential",
                100,
                "center"
            ),
            (
                "#5",
                "Commercial",
                100,
                "center"
            ),
            (
                "#6",
                "Industrial",
                100,
                "center"
            ),
            (
                "#7",
                "Online",
                100,
                "center"
            ),
            (
                "#8",
                "⠀",
                1000,
                "center"
            )
        ]

        formats = [
            lambda data: data,
            lambda data: f"{data}km²",
            lambda data: data,
            lambda data: f"§{data:,}",
            lambda data: f"{data:,}",
            lambda data: f"{data:,}",
            lambda data: f"{data:,}",
            lambda data: format_time_ago(
                datetime.strptime(data, "%Y-%m-%d %H:%M:%S"), now=self.time
            ),
        ]

        self.mayors_frame = StatisticsTreeUI(
            self.notebook, data=mayors, columns=columns, formats=formats
        )

        self.mayors_frame.tree["displaycolumns"] = ["#7", "#8"]
        self.mayors_frame.button.configure(
            command=self.expand_mayors_treeview, text="Expand"
        )

        self.notebook.add(self.mayors_frame, text="Mayors")

    def expand_mayors_treeview(self):

        self.mayors_frame.tree["displaycolumns"] = "#all"
        self.mayors_frame.button.configure(
            command=self.collapse_mayors_treeview, text="Collapse"
        )

        # self.notebook.bind("<<NotebookTabChanged>>", lambda event:
        # self.on_notebook_tab_changed(self.collapse_mayors_treeview))

        # self.after(200, lambda: center_window(self))

    def collapse_mayors_treeview(self):

        self.mayors_frame.tree["displaycolumns"] = ["#7", "#8"]
        self.mayors_frame.button.configure(
            command=self.expand_mayors_treeview, text="Expand"
        )

        # self.after(200, lambda: center_window(self))

    def create_cities_frame(self):

        server_list_path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList"
        regions_directory: Path = server_list_path / self.server.server_id / "Regions"

        if not regions_directory.exists():
            return

        cities = {}
        for region in os.listdir(regions_directory):

            region_database: Union[dict, None] = self.load_json(
                regions_directory / region / "_Database" / "region.json"
            )

            if not region_database:
                continue

            for coords, entry in region_database.items():

                if entry is not None:

                    city_id = f"{region.replace(' ', '_')}_{coords}"

                    city_name = entry.get("city_name", "New City")
                    mayor_name = entry.get("mayor_name", "Defacto")

                    if entry.get("gamemode", 1) < 1:
                        continue

                    s = entry.get("size")
                    if s == 1:
                        size = "Small"
                    elif s == 2:
                        size = "Medium"
                    elif s == 4:
                        size = "Large"
                    else:
                        size = "None"

                    modified = entry.get('modified', None)
                    if modified:
                        modified = datetime.strptime(modified, "%Y-%m-%d %H:%M:%S")
                    else:
                        modified = datetime.now() - timedelta(days=400000)

                    cities[city_id] = [
                        city_name,
                        mayor_name,
                        size,
                        entry.get('mayor_rating', 0),
                        entry.get('total_funds', 0),
                        entry.get('residential_population', 0),
                        entry.get('commercial_population', 0),
                        entry.get('industrial_population', 0),
                        modified,
                    ]

        columns = [
            (
                "#0",
                "Name",
                250,
                "w"
            ),
            (
                "#1",
                "Mayor",
                150,
                "w"
            ),
            (
                "#2",
                "Size",
                100,
                "center"
            ),
            (
                "#3",
                "Rating",
                100,
                "center"
            ),
            (
                "#4",
                "Funds",
                100,
                "center"
            ),
            (
                "#5",
                "Residential",
                100,
                "center"
            ),
            (
                "#6",
                "Commercial",
                100,
                "center"
            ),
            (
                "#7",
                "Industrial",
                100,
                "center"
            ),
            (
                "#8",
                "Modified",
                100,
                "center"
            ),
            (
                "#9",
                "⠀",
                1000,
                "center"
            )
        ]

        formats = [
            lambda data: data,
            lambda data: data,
            lambda data: data,
            lambda data: f"{data}",
            lambda data: f"§{data:,}",
            lambda data: f"{data:,}",
            lambda data: f"{data:,}",
            lambda data: f"{data:,}",
            lambda data: format_time_ago(data, now=self.time),
        ]

        self.cities_frame = StatisticsTreeUI(
            self.notebook, columns=columns, formats=formats, data=cities
        )

        self.cities_frame.tree["displaycolumns"] = ["#8", "#9"]

        self.cities_frame.button.configure(
            command=self.expand_cities_treeview, text="Expand"
        )

        self.notebook.add(self.cities_frame, text="Cities")

    def expand_cities_treeview(self):

        self.cities_frame.tree["displaycolumns"] = "#all"
        self.cities_frame.button.configure(
            command=self.collapse_cities_treeview, text="Collapse"
        )

    def collapse_cities_treeview(self):

        self.cities_frame.tree["displaycolumns"] = ["#8", "#9"]
        self.cities_frame.button.configure(
            command=self.expand_cities_treeview, text="Expand"
        )

    def create_files_frame(self):

        try:

            self.files_frame = StatisticsTreeUI(self.notebook, columns=[
                (
                    "#0",
                    "Name",
                    250,
                    "w"
                ),
                (
                    "#1",
                    "Download",
                    100,
                    "center"
                ),
                (
                    "#2",
                    "⠀",
                    1000,
                    "center"
                )
            ])

            self.files_frame.tree.tag_configure('cached', foreground='green')
            # self.files_frame.tree.tag_configure('red', foreground='red')

            files = {}

            for request in ["Plugins", "Regions"]:

                s = self.server.socket()

                if not self.server.private:
                    s.send(request.lower().encode())
                else:
                    s.send((
                        f"{request.lower()} {SC4MP_VERSION} "
                        f"{self.server.user_id} {self.server.password}"
                    ).encode())

                file_table = s.recv_json()

                s.close()

                for entry in file_table:

                    md5 = entry[0]
                    size = entry[1]
                    path = entry[2]

                    path = list(Path(path).parts)
                    path.insert(0, request)

                    entry = files
                    while len(path) > 1:
                        d = path.pop(0)
                        entry.setdefault(d, {})
                        entry = entry[d]

                    d = path.pop(0)

                    download_size = size
                    cached_file = state.SC4MP_LAUNCHPATH / "_Cache" / md5

                    if cached_file.exists():
                        download_size -= cached_file.stat().st_size

                    entry[d] = [
                        download_size
                    ]

            # update_json("test.json", files)

            self.populate_files_treeview(self.files_frame.tree, data=files)

            self.files_frame.button.configure(
                command=self.expand_files_treeview, text="Expand"
            )

            self.notebook.add(self.files_frame, text="Files")

        except Exception as e:

            show_error(e, no_ui=True)

    def populate_files_treeview(self, tree=None, parent="", data={}):

        total_download_size = 0

        for key in sorted(data.keys()):

            value = data[key]

            download_size = 0

            if isinstance(value, dict):

                # Insert parent node
                node = tree.insert(
                    parent,
                    'end',
                    text=key,
                    values=[""],
                    image=self.folder_icon
                )

                # Recursively add children
                download_size = self.populate_files_treeview(tree, node, value)

                # tree.item(parent, values=[format_download_size(download_size)])

            elif isinstance(value, list):

                download_size = value[0]

                # Insert leaf node
                tree.insert(
                    parent,
                    'end',
                    text=key,
                    values=[format_download_size(download_size)],
                    image=self.file_icon
                )

            total_download_size += download_size

        if parent:
            tree.item(
                parent, values=[format_download_size(total_download_size)]
            )

        return total_download_size

    def expand_files_treeview(self):

        self.expand_files_treeview_helper(self.files_frame.tree)

        self.files_frame.adjust_tree_column_widths()

        self.files_frame.button.configure(
            text="Collapse", command=self.collapse_files_treeview
        )

    def expand_files_treeview_helper(self, tree, parent=""):

        tree.item(parent, open=True)

        children = tree.get_children(parent)
        for child in children:
            self.expand_files_treeview_helper(tree, child)

    def collapse_files_treeview(self):

        self.collapse_files_treeview_helper(self.files_frame.tree)

        self.files_frame.tree.column("#0", width=250)

        self.files_frame.button.configure(
            text="Expand", command=self.expand_files_treeview
        )

    def collapse_files_treeview_helper(self, tree, parent=""):

        tree.item(parent, open=False)

        children = tree.get_children(parent)
        for child in children:
            self.collapse_files_treeview_helper(tree, child)

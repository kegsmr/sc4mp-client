"""Server details window (info, mayors, cities and files tabs)."""

from __future__ import annotations

import json
import os
import threading as th
import time
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import ttk
from typing import Callable, Union

from core.util import format_time_ago, unformat_version
from client import state
from client.constants import SC4MP_ICON, SC4MP_INVITES_DOMAIN, SC4MP_VERSION
from client.errors import ClientException, show_error
from client.server import Server
from client.ui.statistics_tree import StatisticsTreeUI
from client.utils import (
    center_window,
    copy_to_clipboard,
    format_download_size,
    get_sc4mp_path,
    load_json,
)


class ServerDetailsUI(tk.Toplevel):

    def __init__(self, server: Server):
        """TODO"""

        # print("Initializing...")

        # Init

        super().__init__()

        # Properties

        self.server = server
        self.destroyed = False
        self.folder_icon = tk.PhotoImage(file=get_sc4mp_path("folder-icon.png"))
        self.file_icon = tk.PhotoImage(file=get_sc4mp_path("file-icon.png"))

        # Title

        self.title(self.server.server_name)

        # Icon

        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry

        self.geometry('390x441')
        self.grid()
        center_window(self)

        # Priority

        self.grab_set()

        # Key bindings

        self.bind("<Return>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Up>", self.up)
        self.bind("<Down>", self.down)
        self.bind("<Left>", lambda event: self.switch_tab(left=True))
        self.bind("<Right>", lambda event: self.switch_tab())

        # Notebook

        self.notebook = ttk.Notebook(self, width=370, height=361)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_notebook_tab_changed)
        self.notebook.grid(row=0, column=0, padx=10, pady=5)

        # Info frame

        self.info_frame = tk.Frame(self.notebook)

        canvas = tk.Canvas(self.info_frame, width=350, height=341, highlightthickness=0)
        canvas.grid(row=0, column=0, padx=10, pady=10, sticky="n")
        inner_frame = tk.Frame(canvas)
        canvas.create_window(0, 0, window=inner_frame, anchor="nw")

        invite_link = f"https://{SC4MP_INVITES_DOMAIN}/{self.server.server_id}"

        invite_link_label = ttk.Label(inner_frame, text="Invite link", font=("Segoe UI", 9, "bold"))
        invite_link_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))

        invite_link_entry = ttk.Entry(inner_frame, width=40)
        invite_link_entry.insert(0, invite_link)
        invite_link_entry.after(100, lambda: self.reset_entrybox(invite_link_entry, invite_link))
        # invite_link_entry.configure(state="disabled")
        invite_link_entry.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=0)

        invite_link_copy_button = ttk.Button(inner_frame, text="Copy", command=lambda: copy_to_clipboard(invite_link))
        invite_link_copy_button.grid(row=1, column=2)

        # server_id_label = ttk.Label(inner_frame, text="ID", font=("Segoe UI", 9, "bold"))
        # server_id_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(10,0))

        # server_id_entry = ttk.Entry(inner_frame, width=40)
        # server_id_entry.insert(0, self.server.server_id)
        # server_id_entry.after(100, lambda: self.reset_entrybox(server_id_entry, self.server.server_id))
        # server_id_entry.configure(state="disabled")
        # server_id_entry.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=0)

        # server_id_copy_button = ttk.Button(inner_frame, text="Copy", command=lambda: copy_to_clipboard(self.server.server_id))
        # server_id_copy_button.grid(row=3, column=2)

        left_frame = ttk.Frame(inner_frame)
        left_frame.grid(row=10, column=0, pady=20, sticky="nw")

        version_label_1 = ttk.Label(left_frame, text="Version", font=("Segoe UI", 9, "bold"))
        version_label_1.grid(row=1, column=0, sticky="w", padx=10, pady=(10, 0))

        version_label_2 = ttk.Label(left_frame, text=self.server.server_version, foreground=("red" if unformat_version(self.server.server_version)[:2] != unformat_version(SC4MP_VERSION)[:2] else "black"))
        version_label_2.grid(row=2, column=0, sticky="w", padx=10, pady=0)

        password_enabled_label_1 = ttk.Label(left_frame, text="Public", font=("Segoe UI", 9, "bold"))
        password_enabled_label_1.grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))

        password_enabled_label_2 = ttk.Label(left_frame, text=("No" if self.server.password_enabled else "Yes"), foreground=("red" if self.server.password_enabled else "green"))
        password_enabled_label_2.grid(row=4, column=0, sticky="w", padx=10, pady=0)

        if self.server.password_enabled:

            private_label_1 = ttk.Label(left_frame, text="Guests", font=("Segoe UI", 9, "bold"))
            private_label_1.grid(row=5, column=0, sticky="w", padx=10, pady=(10, 0))

            private_label_2 = ttk.Label(left_frame, text=("No" if self.server.private else "Yes"), foreground=("red" if self.server.private else "green"))
            private_label_2.grid(row=6, column=0, sticky="w", padx=10, pady=0)

        right_frame = ttk.Frame(inner_frame)
        right_frame.grid(row=10, column=1, columnspan=2, pady=20, sticky="nw")

        custom_plugins_label_1 = ttk.Label(right_frame, text="Custom plugins", font=("Segoe UI", 9, "bold"))
        custom_plugins_label_1.grid(row=1, column=0, sticky="w", padx=10, pady=(10, 0))

        custom_plugins_label_2 = ttk.Label(right_frame, text=("Yes" if self.server.user_plugins_enabled else "No"), foreground=("green" if self.server.user_plugins_enabled else "red"))
        custom_plugins_label_2.grid(row=2, column=0, sticky="w", padx=10, pady=0)

        try:

            claim_duration = self.server.claim_duration
            max_region_claims = self.server.max_region_claims
            godmode_filter = self.server.godmode_filter

            if claim_duration is None:
                claim_duration = "Forever"
            else:
                claim_duration = f"{claim_duration} days"

            if max_region_claims is None:
                max_region_claims = "None"
            else:
                max_region_claims = f"{max_region_claims} per region"

            claim_duration_label_1 = ttk.Label(right_frame, text="Claim duration", font=("Segoe UI", 9, "bold"))
            claim_duration_label_1.grid(row=3, column=0, sticky="w", padx=10, pady=(10, 0))

            claim_duration_label_2 = ttk.Label(right_frame, text=claim_duration, foreground=("green" if claim_duration == "Forever" else "black"))
            claim_duration_label_2.grid(row=4, column=0, sticky="w", padx=10, pady=0)

            claim_limit_label_1 = ttk.Label(right_frame, text="Claim limit", font=("Segoe UI", 9, "bold"))
            claim_limit_label_1.grid(row=5, column=0, sticky="w", padx=10, pady=(10, 0))

            claim_limit_label_2 = ttk.Label(right_frame, text=max_region_claims, foreground=("green" if max_region_claims == "None" else "black"))
            claim_limit_label_2.grid(row=6, column=0, sticky="w", padx=10, pady=0)

            if not godmode_filter:

                godmode_claims_label_1 = ttk.Label(right_frame, text="Godmode claims", font=("Segoe UI", 9, "bold"))
                godmode_claims_label_1.grid(row=7, column=0, sticky="w", padx=10, pady=(10, 0))

                godmode_claims_label_2 = ttk.Label(right_frame, text=("No" if godmode_filter else "Yes"), foreground=("red" if godmode_filter else "green"))
                godmode_claims_label_2.grid(row=8, column=0, sticky="w", padx=10, pady=0)

        except AttributeError:

            pass

        # options_frame = tk.Frame(self.info_frame)
        # options_frame.grid(row=1, column=0, sticky="sw")

        # copy_link_button = ttk.Button(options_frame, text="Copy link", command=lambda: copy_to_clipboard(f"sc4mp://{self.server.host}:{self.server.port}"))
        # copy_link_button.grid(row=0, column=0, padx=20, pady=10)

        # invite_link_label = ttk.Label(self.info_frame, text="Link: ")
        # invite_link_label.grid(row=1, column=0)

        # invite_link_entry = ttk.Entry(self.info_frame)
        # invite_link_entry.insert(0, f"sc4mp://{self.server.host}:{self.server.port}")
        # invite_link_entry.grid(row=1, column=1)

        # self.info_frame.rules_frame: ttk.LabelFrame = ttk.Labelframe(self.info_frame, text="Rules")
        # self.info_frame.rules_frame.grid(row=0, column=0)

        # self.info_frame.rules_frame.label = ttk.Label(self.info_frame.rules_frame, text="TEST")
        # self.info_frame.rules_frame.label.grid(row=0, column=0)

        self.notebook.add(self.info_frame, text="Info")

        # Ok button

        self.ok_button = ttk.Button(self, text="Ok", command=self.destroy, default="active")
        self.ok_button.grid(row=1, column=0, padx=10, pady=5, sticky="se")

        # Create notebook frames asynchronously

        th.Thread(target=self.create_notebook_frames).start()

        # self.chain_functions([
        #    self.create_mayors_frame,
        #    self.create_cities_frame,
        #    lambda: th.Thread(target=self.create_files_frame).start()
        # ])

        # Update window size periodically

        self.after(100, self.update_window_size)

        # Select tab from last server detail view
        self.after(200, self.select_last_tab)

    def select_last_tab(self):

        try:
            self.notebook.select(state.sc4mp_server_details_ui_last_tab_index)
        except Exception as e:
            pass

    def on_notebook_tab_changed(self, function: Callable):

        try:

            functions = [
                self.collapse_mayors_treeview,
                self.collapse_cities_treeview,
                self.collapse_files_treeview,
            ]

            for index in range(len(self.notebook.tabs()) - 1):
                functions[index]()

        except Exception as e:

            show_error(e, no_ui=True)

        # function()

        # self.notebook.unbind("<<NotebookTabChanged>>")

    def up(self, event):
        self.focus_tree(move_up=True)

    def down(self, event):
        self.focus_tree(move_down=True)

    def focus_tree(self, move_up=False, move_down=False):

        try:

            tree: ttk.Treeview = self.notebook.nametowidget(self.notebook.select()).tree
            children = tree.get_children()
            if tree.focus() == "" or len(tree.selection()) < 1:
                tree.focus(children[0])
                tree.selection_add([children[0]])
            elif self.focus_get() is not tree:
                current_selection = tree.selection()[0]
                if current_selection in children:
                    current_selection_index = children.index(current_selection)
                    tree.selection_remove([current_selection])
                    next_selection = None
                    if move_up:
                        next_selection = [children[current_selection_index - 1]]
                    elif move_down:
                        next_selection = [children[current_selection_index + 1]]
                    if next_selection:
                        tree.selection_add(next_selection)
                        tree.focus(next_selection)
            tree.focus_set()

        except (AttributeError, ValueError, IndexError) as e:

            show_error(e, no_ui=True)

    def switch_tab(self, left=False):

        try:

            right = not left

            current_focus = self.focus_get()

            if type(current_focus) is ttk.Treeview and self.notebook.tab(self.notebook.select(), "text") == "Files":
                tree: ttk.Treeview = current_focus
                selection = tree.selection()
                if len(selection) > 0:
                    selection = selection[0]
                    if left and not (selection in tree.get_children("") and not tree.item(selection, "open")):
                        return
                    elif right and len(tree.get_children(selection)) > 0:
                        return
            elif type(current_focus) is ttk.Entry:
                return
                # current_selection = current_focus.selection()
                # if len(current_selection) > 0:
                #    current_selection = current_selection[0]
                #    if current_selection not in current_focus.get_children("") or right:
                #        return
                # if len(current_focus.get_children(current_selection)) > 0:
                # right = not left
                # expanded = current_focus.item(current_selection, "open")
                # collapsed = not expanded
                # if collapsed and right or expanded and left:
                #    return

            self.notebook.focus_set()

            all_tabs = list(self.notebook.tabs())
            all_tabs.extend(all_tabs)
            current_tab = self.notebook.select()
            current_tab_index = all_tabs.index(current_tab)
            next_tab = all_tabs[current_tab_index + (-1 if left else 1)]

            self.notebook.select(next_tab)

        except IndexError as e:

            show_error(e, no_ui=True)

    def update_window_size(self):

        try:

            # Check if UI is destoyed and stop updating window size if so
            if not self.winfo_exists():  # self.destroyed:
                return

            # Update the UI to make sure `winfo` calls are correct
            state.sc4mp_ui.update()

            # Resize notebook
            inner_frame = self.notebook.nametowidget(self.notebook.select())
            if type(inner_frame) is tk.Frame:
                notebook_width = 370
                notebook_height = 361
            else:
                notebook_width = inner_frame.winfo_width()
                notebook_height = inner_frame.winfo_height()
            self.notebook.configure(width=notebook_width, height=notebook_height)

            # Get old window width, height, x, y
            old_window_width = self.winfo_width()
            old_window_height = self.winfo_height()
            old_window_x = self.winfo_x()
            old_window_y = self.winfo_y()

            # Set new window width, height, x, y
            new_window_width = notebook_width + 20
            new_window_height = notebook_height + 80
            new_window_x = old_window_x + int((old_window_width - new_window_width) / 2)
            new_window_y = old_window_y + int((old_window_height - new_window_height) / 2)

            # Resize the window
            self.maxsize(new_window_width, new_window_height)
            self.minsize(new_window_width, new_window_height)
            self.geometry(f"{new_window_width}x{new_window_height}+{new_window_x}+{new_window_y}")

            # print(f"Resized to {new_window_width}x{new_window_height}.")

            self.after(100, self.update_window_size)

        except Exception as e:

            show_error(e, no_ui=True)

    def reset_entrybox(self, entrybox: ttk.Entry, text: str):

        try:

            if entrybox.get() != text:
                entrybox.delete(0, "end")
                entrybox.insert(0, text)

            self.after(100, lambda: self.reset_entrybox(entrybox, text))

        except Exception as e:

            show_error(e, no_ui=True)

    def destroy(self):


        try:
            state.sc4mp_server_details_ui_last_tab_index = self.notebook.index(self.notebook.select())
        except Exception:
            pass

        self.destroyed = True

        return super().destroy()

    def chain_functions(self, functions, delay=100):

        if self.destroyed:
            return
        else:
            try:
                functions[0]()
            except Exception:
                self.after(delay, lambda: self.chain_functions(functions, delay=delay))
            else:
                functions.pop(0)
                if len(functions) > 0:
                    self.after(delay, lambda: self.chain_functions(functions, delay=delay))

    def load_json(self, *args, **kwargs):

        while not self.destroyed:
            try:
                return load_json(*args, *kwargs)
            except json.decoder.JSONDecodeError:
                time.sleep(1)

    def create_notebook_frames(self):

        try:

            self.time = self.server.time()

            self.create_mayors_frame()
            self.create_cities_frame()
            # self.create_files_frame()

        except Exception as e:

            show_error(f"An error occurred while creating notebook frames.\n\n{e}", no_ui=True)

    def create_mayors_frame(self):

        regions_directory: Path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server.server_id / "Regions"

        if not regions_directory.exists():
            return

        mayors = {}
        for region in os.listdir(regions_directory):

            region_database: Union[dict, None] = self.load_json(regions_directory / region / "_Database" / "region.json")

            if not region_database:
                continue

            for entry in region_database.values():
                if entry is not None:
                    user_id = entry.get("owner", None)
                    if user_id is not None:

                        mayors.setdefault(user_id, {})

                        mayors[user_id].setdefault("name", "Defacto")

                        mayors[user_id].setdefault("last_online", None)
                        if mayors[user_id]["last_online"] is None or datetime.strptime(entry["modified"], "%Y-%m-%d %H:%M:%S") > datetime.strptime(mayors[user_id]["last_online"], "%Y-%m-%d %H:%M:%S"):
                            if entry["mayor_name"] != entry.get("last_mayor_name", None):
                                mayors[user_id]["name"] = entry["mayor_name"]
                            mayors[user_id]["last_online"] = entry["modified"]

                        mayors[user_id].setdefault("residential_population", 0)
                        mayors[user_id]["residential_population"] += entry["residential_population"]

                        mayors[user_id].setdefault("commercial_population", 0)
                        mayors[user_id]["commercial_population"] += entry["commercial_population"]

                        mayors[user_id].setdefault("industrial_population", 0)
                        mayors[user_id]["industrial_population"] += entry["industrial_population"]

                        mayors[user_id].setdefault("total_population", 0)
                        mayors[user_id]["total_population"] += entry["population"]

                        mayors[user_id].setdefault("mayor_rating", 0)
                        mayors[user_id]["mayor_rating"] += entry["residential_population"] * entry["mayor_rating"]

                        mayors[user_id].setdefault("tiles_claimed", 0)
                        mayors[user_id]["tiles_claimed"] += 1

                        mayors[user_id].setdefault("area_claimed", 0)
                        mayors[user_id]["area_claimed"] += entry["size"] ** 2

                        mayors[user_id].setdefault("funds", 0)
                        mayors[user_id]["funds"] += entry.get("total_funds", 0)

        for entry in mayors.values():
            if entry["residential_population"] > 0:
                entry["mayor_rating"] = round(entry["mayor_rating"] / entry["residential_population"])
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
            lambda data: format_time_ago(datetime.strptime(data, "%Y-%m-%d %H:%M:%S"), now=self.time),
        ]

        self.mayors_frame = StatisticsTreeUI(self.notebook, data=mayors, columns=columns, formats=formats)

        self.mayors_frame.tree["displaycolumns"] = ["#7", "#8"]
        self.mayors_frame.button.configure(command=self.expand_mayors_treeview, text="Expand")

        self.notebook.add(self.mayors_frame, text="Mayors")

    def expand_mayors_treeview(self):

        self.mayors_frame.tree["displaycolumns"] = "#all"
        self.mayors_frame.button.configure(command=self.collapse_mayors_treeview, text="Collapse")

        # self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.on_notebook_tab_changed(self.collapse_mayors_treeview))

        # self.after(200, lambda: center_window(self))

    def collapse_mayors_treeview(self):

        self.mayors_frame.tree["displaycolumns"] = ["#7", "#8"]
        self.mayors_frame.button.configure(command=self.expand_mayors_treeview, text="Expand")

        # self.after(200, lambda: center_window(self))

    def create_cities_frame(self):

        regions_directory: Path = Path(state.SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server.server_id / "Regions"

        if not regions_directory.exists():
            return

        cities = {}
        for region in os.listdir(regions_directory):

            region_database: Union[dict, None] = self.load_json(regions_directory / region / "_Database" / "region.json")

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

        self.cities_frame = StatisticsTreeUI(self.notebook, columns=columns, formats=formats, data=cities)

        self.cities_frame.tree["displaycolumns"] = ["#8", "#9"]

        self.cities_frame.button.configure(command=self.expand_cities_treeview, text="Expand")

        self.notebook.add(self.cities_frame, text="Cities")

    def expand_cities_treeview(self):

        self.cities_frame.tree["displaycolumns"] = "#all"
        self.cities_frame.button.configure(command=self.collapse_cities_treeview, text="Collapse")

    def collapse_cities_treeview(self):

        self.cities_frame.tree["displaycolumns"] = ["#8", "#9"]
        self.cities_frame.button.configure(command=self.expand_cities_treeview, text="Expand")

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
                    s.send(f"{request.lower()} {SC4MP_VERSION} {self.server.user_id} {self.server.password}".encode())

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

            self.files_frame.button.configure(command=self.expand_files_treeview, text="Expand")

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
                node = tree.insert(parent, 'end', text=key, values=[""], image=self.folder_icon)

                # Recursively add children
                download_size = self.populate_files_treeview(tree, node, value)

                # tree.item(parent, values=[format_download_size(download_size)])

            elif isinstance(value, list):

                download_size = value[0]

                # Insert leaf node
                tree.insert(parent, 'end', text=key, values=[format_download_size(download_size)], image=self.file_icon)

            total_download_size += download_size

        if parent:
            tree.item(parent, values=[format_download_size(total_download_size)])

        return total_download_size

    def expand_files_treeview(self):

        self.expand_files_treeview_helper(self.files_frame.tree)

        self.files_frame.adjust_tree_column_widths()

        self.files_frame.button.configure(text="Collapse", command=self.collapse_files_treeview)

    def expand_files_treeview_helper(self, tree, parent=""):

        tree.item(parent, open=True)

        children = tree.get_children(parent)
        for child in children:
            self.expand_files_treeview_helper(tree, child)

    def collapse_files_treeview(self):

        self.collapse_files_treeview_helper(self.files_frame.tree)

        self.files_frame.tree.column("#0", width=250)

        self.files_frame.button.configure(text="Expand", command=self.expand_files_treeview)

    def collapse_files_treeview_helper(self, tree, parent=""):

        tree.item(parent, open=False)

        children = tree.get_children(parent)
        for child in children:
            self.collapse_files_treeview_helper(tree, child)

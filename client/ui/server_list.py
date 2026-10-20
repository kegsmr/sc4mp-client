"""The server browser shown in the main window."""

from __future__ import annotations

import math
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import messagebox, ttk

from client import state
from client.constants import SC4MP_HOST, SC4MP_PORT, SC4MP_TITLE
from client.errors import show_error
from client.server import Server
from client.server_list import ServerList
from client.ui.server_details import ServerDetailsUI
from client.ui.server_loader import ServerLoaderUI
from client.utils import format_url, get_sc4mp_path


class ServerListUI(tk.Frame):
    """ServerList UI wrapper.

    Arguments:
        TODO

    Returns:
        TODO
    """

    def __init__(self, root):

        # print("Initializing...")

        # Parameters

        self.root = root

        # Init

        super().__init__(self.root)

        # Geometry

        self.grid()

        # Key bindings

        self.root.bind("<Return>", lambda event: self.connect())
        self.root.bind("<Up>", lambda event: self.focus_tree())
        self.root.bind("<Down>", lambda event: self.focus_tree())

        # Banner

        self.canvas = tk.Canvas(self, width=800, height=100)
        self.canvas.image = tk.PhotoImage(file=get_sc4mp_path("banner.png"))
        self.canvas.create_image(400, 50, image=self.canvas.image)
        self.canvas["borderwidth"] = 0
        self.canvas["highlightthickness"] = 0
        self.canvas.grid(row=0, column=0, rowspan=1, columnspan=3, padx=0, pady=0)

        # Label

        self.label = ttk.Label(self)
        self.label.grid(row=1, column=0, rowspan=1, columnspan=3, padx=10, pady=(15, 10))
        # self.label['text'] = 'Loading...' #'To get started, select a server
        # below and click "Connect."' #"Loading server list..."

        # Frame

        self.frame = tk.Frame(self)
        self.frame.grid(row=2, column=0, rowspan=1, columnspan=3, padx=15, pady=10, sticky="n")

        # Tree

        NORMAL_COLUMN_WIDTH = 93
        COLUMNS = [
            (
                "#0",
                "Name",
                3 * NORMAL_COLUMN_WIDTH,
                "w"
            ),
            (
                "#1",
                "Mayors",
                NORMAL_COLUMN_WIDTH,
                "center"
            ),
            (
                "#2",
                "Claimed",
                NORMAL_COLUMN_WIDTH,
                "center"
            ),
            (
                "#3",
                "Download",
                NORMAL_COLUMN_WIDTH,
                "center"
            ),
            (
                "#4",
                "Ping",
                NORMAL_COLUMN_WIDTH,
                "center"
            ),
            (
                "#5",
                "Rank",
                NORMAL_COLUMN_WIDTH,
                "center"
            ),
            (
                "#6",
                "Joined",
                NORMAL_COLUMN_WIDTH,
                "center"
            )
        ]

        column_ids = []
        for column in COLUMNS:
            column_ids.append(column[0])
        column_ids = tuple(column_ids[1:])

        self.tree = ttk.Treeview(self.frame, columns=column_ids, selectmode="browse", height=12)

        for column in COLUMNS:
            column_id = column[0]
            column_name = column[1]
            column_width = column[2]
            column_anchor = column[3]
            self.tree.column(column_id, width=column_width, anchor=column_anchor, stretch=False)
            self.tree.heading(
                column_id,
                text=column_name,
                command=lambda column_name=column_name: self.handle_header_click(column_name)
            )

        # self.tree['show'] = 'headings'
        self.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#5")

        # self.tree.bind("<Double-1>", self.handle_double_click) #lambda event: self.connect())
        self.tree.bind("<Button-1>", self.handle_single_click)
        self.tree.bind("<Button-2>", self.handle_right_click)
        self.tree.bind("<Button-3>", self.handle_right_click)

        self.tree.sort = "Rank"
        self.tree.reverse_sort = False

        self.tree.tag_configure(
            "strike", font=tkfont.Font(family="Segoe UI", size=9, weight="normal", overstrike=1)
        )
        self.tree.tag_configure("red", foreground="red")

        self.tree.focus_set()

        self.tree.pack(side="left")

        self.tree.last_click = 0
        self.tree.last_click_coords = (0, 0)

        # Scrollbar

        def yview(*args, **kwargs):
            self.worker.update_rank_bars()
            self.tree.yview(*args, **kwargs)

        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=yview)
        self.scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # Server info frame

        self.server_info = tk.Frame(self, width=540, height=120)
        self.server_info.grid(row=3, column=0, columnspan=2, padx=20, pady=0, sticky="nw")
        self.server_info.grid_propagate(0)

        # TODO add right click context menu

        # Description label

        self.description_label = ttk.Label(self.server_info, wraplength=self.server_info["width"])
        self.description_label.grid(
            row=0, column=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="nw"
        )
        self.description_label['text'] = ""

        # URL label

        self.url_label = tk.Label(self.server_info, fg="blue", cursor="hand2")
        self.url_label.grid(row=1, column=0, columnspan=1, padx=0, pady=5, sticky="nw")
        self.url_label['text'] = ""
        self.url_label.bind("<Button-1>", lambda e: self.open_server_url())

        # Combo box

        self.combo_box = ttk.Combobox(self, width=23)
        # "category: Bookmarked" "category: Online"
        self.combo_box["values"] = (
            "category: All", "category: Official", "category: Public",
            "category: Private", "category: History"
        )

        self.combo_box.PLACEHOLDER_TEXT = "Search/Filter servers"

        def on_focus_in(event):
            if self.combo_box.get() == self.combo_box.PLACEHOLDER_TEXT:
                self.combo_box.delete(0, tk.END)  # Clear placeholder when clicked
                self.combo_box.configure(foreground="black")

        def on_focus_out(event):
            if self.combo_box.get() == "":
                # Restore placeholder if nothing is typed
                self.combo_box.set(self.combo_box.PLACEHOLDER_TEXT)
                self.combo_box.configure(foreground="gray")

        def on_key_release(event):
            if self.combo_box.get() == self.combo_box.PLACEHOLDER_TEXT:
                self.combo_box.delete(0, tk.END)
                self.combo_box.configure(foreground="black")

        self.combo_box.bind("<FocusIn>", on_focus_in)
        self.combo_box.bind("<FocusOut>", on_focus_out)
        self.combo_box.bind("<KeyRelease>", on_key_release)

        if state.sc4mp_config["GENERAL"]["server_browser_filter"]:
            self.combo_box.insert(0, state.sc4mp_config["GENERAL"]["server_browser_filter"])
            self.combo_box.configure(foreground="black")
        else:
            self.combo_box.insert(0, self.combo_box.PLACEHOLDER_TEXT)
            self.combo_box.configure(foreground="gray")

        self.combo_box.grid(
            row=3, column=2, rowspan=1, columnspan=1, padx=(0, 16), pady=(5, 10), sticky="ne"
        )

        # Address label

        self.address_label = tk.Label(self, fg="gray")
        self.address_label.grid(row=4, column=0, columnspan=1, padx=20, pady=10, sticky="sw")
        self.address_label['text'] = ""

        # Server options frame

        self.server_options = tk.Frame(self)
        self.server_options.grid(
            row=4, column=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="se"
        )

        # Details button

        self.details_button = ttk.Button(self.server_options, text="Details", command=self.details)
        self.details_button['state'] = tk.DISABLED
        self.details_button.grid(
            row=0, column=99, columnspan=1, padx=(15, 20), pady=10, sticky="se"
        )

        # Refresh / connect frame

        self.refresh_connect = tk.Frame(self)
        self.refresh_connect.grid(
            row=4, column=2, rowspan=1, columnspan=1, padx=0, pady=0, sticky="se"
        )

        # Refresh button

        self.refresh_button = ttk.Button(
            self.refresh_connect, text="Refresh", command=self.root.refresh
        )
        self.refresh_button.grid(row=0, column=0, columnspan=1, padx=11, pady=10, sticky="se")

        # Connect button

        self.connect_button = ttk.Button(
            self.refresh_connect, text="Connect", command=self.connect, default="active"
        )
        self.connect_button['state'] = tk.DISABLED
        self.connect_button.grid(row=0, column=1, columnspan=1, padx=(0, 15), pady=10, sticky="se")

        # Worker
        self.worker = ServerList(self)
        self.worker.start()

    def handle_double_click(self, event):

        region = self.tree.identify_region(event.x, event.y)
        if region == "separator":
            return "break"
        elif region == "tree" or region == "cell":
            self.connect()
        self.tree.last_click = 0
        self.tree.last_click_coords = (0, 0)

    def handle_single_click(self, event):

        if (time.time() - self.tree.last_click < 500
                and math.dist((event.x, event.y), self.tree.last_click_coords) < 1):
            self.handle_double_click(event)
        else:
            region = self.tree.identify_region(event.x, event.y)
            if region == "separator":
                return "break"
            else:
                self.tree.last_click = time.time()
                self.tree.last_click_coords = (event.x, event.y)

    def handle_right_click(self, event):

        server_id = self.tree.identify('item', event.x, event.y)

        menu = tk.Menu(self, tearoff=0)

        if not server_id:
            return

        self.tree.selection_set(server_id)
        self.tree.focus(server_id)

        # Create the context menu
        menu.add_command(label="Connect", command=self.connect, font=("Segoe UI", 9, "bold"))
        menu.add_command(label="Refresh", command=self.root.refresh)
        if "Offline" not in self.worker.servers[server_id].categories:
            menu.add_separator()
            menu.add_command(label="Details...", command=self.details)
        # TODO add "View..." submenu
        # TODO add "Sort by..." submenu

        # Show the context menu at the cursor's location
        menu.post(event.x_root, event.y_root)

    def handle_header_click(self, name):

        print("Sort by \"" + name + "\"")
        DEFAULT_REVERSED = ("Name", "Claimed", "Download", "Ping")
        if self.tree.sort == name:
            self.tree.reverse_sort = not self.tree.reverse_sort
        else:
            self.tree.sort = name
            self.tree.reverse_sort = name in DEFAULT_REVERSED
        if self.tree.reverse_sort:
            print("- (reversed)")
        self.worker.sort_mode_changed = True
        # self.worker.sort = True

    def focus_tree(self):

        try:
            self.tree.focus_set()
            children = self.tree.get_children()
            if self.tree.focus() == "" and len(children) > 0:
                self.tree.focus(children[0])
                self.tree.selection_add([children[0]])
        except Exception:
            # Method not all that important so we'll just toss an error in the
            # console and call it a day
            show_error("Error setting focus on server list UI.", no_ui=True)

    def details(self):

        ServerDetailsUI(self.worker.servers[self.tree.focus()])

    def connect(self):

        print('"Connect"')
        server_id = self.tree.focus()
        if server_id == "":
            return
        server = self.worker.servers[server_id]
        if not ("Official" in server.categories
                or "History" in server.categories
                or state.sc4mp_config["GENERAL"]["ignore_third_party_server_warnings"]):
            message = (
                "You are about to join a third-party server.\n\n"
                "The SimCity 4 Multiplayer Project is not responsible for content "
                "downloaded from third-party servers. Only join third-party servers "
                "you trust."
            )
            if not messagebox.askokcancel(title=SC4MP_TITLE, message=message, icon="warning"):
                return
        host = server.host
        port = server.port
        try:
            if len(host) < 1:
                host = SC4MP_HOST
            try:
                port = int(port)
            except Exception:
                port = SC4MP_PORT
            ServerLoaderUI(Server(host, port))
            self.tree.focus_set()
        except Exception as e:
            show_error(f"An error occurred before the server loader thread could start.\n\n{e}")

    def open_server_url(self):

        webbrowser.open_new_tab(format_url(self.url_label["text"]))

    def destroy(self):

        server_browser_filter = self.combo_box.get()

        if server_browser_filter == self.combo_box.PLACEHOLDER_TEXT:
            server_browser_filter = ""

        if state.sc4mp_config["GENERAL"]["server_browser_filter"] != server_browser_filter:
            state.sc4mp_config["GENERAL"]["server_browser_filter"] = server_browser_filter
            state.sc4mp_config.update()

        return super().destroy()

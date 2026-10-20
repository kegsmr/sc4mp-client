"""Windows shown while playing: game monitor, launcher map, game overlay
and regions refresher."""

from __future__ import annotations

import os
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from client import state
from client.constants import SC4MP_ICON, SC4MP_TITLE
from client.errors import show_error
from client.regions_refresher import RegionsRefresher
from client.utils import (
    center_window,
    format_url,
    get_sc4mp_path,
    process_exists,
)


class GameMonitorUI(tk.Toplevel):

    def __init__(self, parent):

        # print("Initializing...")

        # Parameters
        self.parent = parent

        # Init
        super().__init__()
        self.withdraw()

        # Title
        self.title(SC4MP_TITLE)

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry(f"400x400+{state.sc4mp_game_monitor_x}+{state.sc4mp_game_monitor_y}")
        self.minsize(420, 280)
        self.maxsize(420, 280)
        self.grid()

        # Iconify
        # if sc4mp_config["SC4"]["fullscreen"]:
        #     self.iconify()

        # Priority
        # self.grab_set()

        # Protocol
        self.protocol("WM_DELETE_WINDOW", self.delete_window)

        # Status frame
        self.status_frame = tk.Frame(self)
        self.status_frame.grid(column=0, row=0, rowspan=1, columnspan=2, padx=0, pady=20, sticky="n")

        # Status label left
        # self.status_frame.left = tk.Label(self.status_frame, text="Status:")
        # self.status_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="w")

        # Status label right
        self.status_frame.right = tk.Label(self.status_frame, text="")
        self.status_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="n")
        self.label = self.status_frame.right

        # Server info frame
        self.server_info = tk.Frame(self, width=400, height=180, background="white", highlightbackground="gray", highlightthickness=1)
        self.server_info.grid(row=1, column=0, columnspan=2, padx=10, pady=0, sticky="nw")
        self.server_info.grid_propagate(0)

        # Description label
        self.description_label = ttk.Label(self.server_info, background="white", wraplength=(self.server_info["width"] - 20))
        self.description_label.grid(row=0, column=0, rowspan=1, columnspan=1, padx=10, pady=(10, 0), sticky="nw")
        self.description_label['text'] = ""

        # URL label
        self.url_label = tk.Label(self.server_info, fg="blue", cursor="hand2", background="white")
        self.url_label.grid(row=1, column=0, columnspan=1, padx=10, pady=5, sticky="nw")
        self.url_label['text'] = ""
        self.url_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab(format_url(self.url_label["text"])))

        # Ping frame
        self.ping_frame = tk.Frame(self, width=420, height=0)
        self.ping_frame.grid(column=0, row=2, rowspan=1, columnspan=2, padx=0, pady=4, sticky="ew")
        self.ping_frame.grid_propagate(0)

        # Ping label left
        self.ping_frame.left = tk.Label(self, text="", fg="gray")
        self.ping_frame.left.grid(column=0, row=3, rowspan=1, columnspan=1, padx=10, pady=0, sticky="w")

        # Ping label right
        self.ping_frame.right = tk.Label(self, text="", fg="gray")
        self.ping_frame.right.grid(column=1, row=3, rowspan=1, columnspan=1, padx=10, pady=0, sticky="e")

    def delete_window(self):

        if not state.sc4mp_config["GENERAL"]["allow_game_monitor_exit"]:
            if state.sc4mp_allow_game_monitor_exit_if_error:
                try:
                    process_exists("simcity 4.exe")
                    return
                except Exception:
                    pass
        if messagebox.askokcancel(title=SC4MP_TITLE, message="Disconnect from the server?\n\nAll unsaved changes will be lost.", icon="warning"):
            state.sc4mp_game_exit_ovveride = True
            self.parent.end = True
            self.destroy()

    def destroy(self):


        try:
            state.sc4mp_game_monitor_x = self.winfo_x()
            state.sc4mp_game_monitor_y = self.winfo_y()
        except Exception:
            pass

        return super().destroy()


class GameMonitorMapUI(tk.Toplevel):

    def __init__(self):

        print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title(SC4MP_TITLE)

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry("400x400")
        self.minsize(443, 600)
        self.maxsize(443, 600)
        self.grid()

        # Protocol
        self.protocol("WM_DELETE_WINDOW", self.disable)

        # Status label
        self.label = tk.Label(self)
        self.label.grid(row=0, column=0, padx=10, pady=20, sticky="n")
        # self.label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # Canvas
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.grid(row=1, column=0, padx=15, pady=0, sticky="nw")  # , sticky="ewns")
        self.canvas = tk.Canvas(self.canvas_frame, width=408, height=408, bg="white", highlightthickness=0)
        self.canvas_horizontal_scrollbar = tk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.canvas_horizontal_scrollbar.pack(side="bottom", fill="x")
        self.canvas_horizontal_scrollbar.config(command=self.canvas.xview)
        self.canvas_vertical_scrollbar = tk.Scrollbar(self.canvas_frame)
        self.canvas_vertical_scrollbar.pack(side="right", fill="y")
        self.canvas_vertical_scrollbar.config(command=self.canvas.yview)
        self.canvas.config(xscrollcommand=self.canvas_horizontal_scrollbar.set, yscrollcommand=self.canvas_vertical_scrollbar.set)
        self.canvas.pack(side="left", expand=True, fill="both")

        # Status frame
        # self.status_frame = tk.Frame(self)
        # self.status_frame.grid(column=0, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

        # Status label left
        # self.status_frame.left = ttk.Label(self.status_frame, text="Status:")
        # self.status_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="w")

        # Status label right
        # self.status_frame.right = ttk.Label(self.status_frame, text="")
        # self.status_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=10, sticky="w")
        # self.label = self.status_frame.right

        # Ping frame
        # self.ping_frame = tk.Frame(self)
        # self.ping_frame.grid(column=0, row=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

        # Ping label left
        # self.ping_frame.left = ttk.Label(self.ping_frame, text="Ping:")
        # self.ping_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=0, sticky="w")

        # Ping label right
        # self.ping_frame.right = ttk.Label(self.ping_frame, text="")
        # self.ping_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

        self.draw_reigon()

    def disable(self):

        pass

    def draw_reigon(self):

        self.canvas.LAUNCHER_MAP_TILE_UNCLAIMED_LARGE = tk.PhotoImage(file=os.path.join("resources", "launcher-map-tile-unclaimed-large.png"))

        TILE_SIZE = 17

        self.canvas.images = {}

        REGION_WIDTH = 6 * 4
        REGION_HEIGHT = 6 * 4

        WIDTH = TILE_SIZE * REGION_WIDTH
        HEIGHT = TILE_SIZE * REGION_HEIGHT

        self.canvas.configure(scrollregion=(-.5 * WIDTH, -.5 * HEIGHT, .5 * WIDTH, .5 * HEIGHT))

        # VIEWPORT_WIDTH = 408 / WIDTH
        # VIEWPORT_HEIGHT = 408 / HEIGHT

        # if VIEWPORT_WIDTH < 1:
        #    self.canvas_horizontal_scrollbar.set((1 + VIEWPORT_WIDTH) / 2, (1 - VIEWPORT_WIDTH) / 2)

        # if VIEWPORT_HEIGHT < 1:
        #    self.canvas_vertical_scrollbar.set((1 + VIEWPORT_HEIGHT) / 2, (1 - VIEWPORT_HEIGHT) / 2)

        LARGE_TILE_COUNT_X = REGION_WIDTH / 4
        LARGE_TILE_COUNT_Y = REGION_HEIGHT / 4

        for y in range(int(-.5 * LARGE_TILE_COUNT_Y), int(.5 * LARGE_TILE_COUNT_Y)):
            for x in range(int(-.5 * LARGE_TILE_COUNT_X), int(.5 * LARGE_TILE_COUNT_X)):
                self.canvas.images[f"{x}_{y}"] = self.canvas.create_image(x * 68, y * 68, image=self.canvas.LAUNCHER_MAP_TILE_UNCLAIMED_LARGE, anchor="nw")


class GameOverlayUI(tk.Toplevel):

    def __init__(self, game_monitor_ui, guest=False):

        # print("Initializing...")

        # Parameters
        self.game_monitor_ui = game_monitor_ui

        # Init
        super().__init__()

        # Geometry
        self.overlay()
        self.grid()

        # Priority
        self.wm_attributes("-topmost", True)

        # Images
        self.images = {}
        for overlay_state in ["connected", "guest", "not-saved", "refreshed", "refreshing", "saved", "saving"]:
            self.images[overlay_state] = tk.PhotoImage(file=get_sc4mp_path(f"overlay-{overlay_state}.png"))

        # Canvas
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="hand2")
        self.canvas.bind("<Button-1>", self.click)
        if guest:
            self.set_state("guest")
        else:
            self.set_state("connected")

    def overlay(self):

        try:

            if state.sc4mp_ui.focus_get() is self.game_monitor_ui:

                self.withdraw()

            else:

                WIDTH = 115
                HEIGHT = 20

                screen_height = self.winfo_screenheight()
                screen_width = self.winfo_screenwidth()

                self.geometry('{}x{}+{}+{}'.format(WIDTH, HEIGHT, screen_width - WIDTH, screen_height - HEIGHT))

                self.overrideredirect(True)

                self.lift()

                self.deiconify()

            self.after(100, self.overlay)

        except Exception as e:

            if type(e) is not tk.TclError or "bad window path name" not in str(e):

                show_error(f"Cannot overlay the game overlay.\n\n{e}", no_ui=True)

    def set_state(self, state):

        self.canvas.image = self.canvas.create_image(0, 0, anchor="nw", image=self.images[state])
        self.canvas.pack()

    def click(self, event):
        try:
            self.game_monitor_ui.deiconify()
            self.game_monitor_ui.focus_set()
            self.game_monitor_ui.grab_set()
        except Exception as e:
            show_error(e, no_ui=True)


class RegionsRefresherUI(tk.Toplevel):

    def __init__(self, server):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title(server.server_name)

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.minsize(800, 100)
        self.maxsize(800, 100)
        self.grid()
        center_window(self)

        # Priority
        self.attributes("-topmost", True)
        self.overlay()

        # Label
        self.label = ttk.Label(self)
        self.label['text'] = "Loading..."
        self.label.grid(column=0, row=0, columnspan=2, padx=10, pady=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self,
            orient='horizontal',
            mode='indeterminate',
            length=780,
            maximum=100
        )
        self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=10)
        self.progress_bar.start(2)

        # Worker
        self.worker = RegionsRefresher(self, server)

    def overlay(self):

        # print("Overlaying...")
        try:
            self.overrideredirect(True)
            self.lift()
            self.after(100, self.overlay)
        except Exception as e:
            show_error("Unable to overlay region refresher UI.", no_ui=True)

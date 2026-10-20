"""Windows shown while connecting to a server: the progress window and
the fullscreen background."""

from __future__ import annotations

import os
import threading as th
import tkinter as tk
from pathlib import Path
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    sc4mp_has_pil = True
except ImportError:
    sc4mp_has_pil = False

from client import state
from client.constants import SC4MP_ICON, SC4MP_TITLE
from client.errors import show_error
from client.server_loader import ServerLoader
from client.utils import center_window, get_sc4mp_path


class ServerLoaderUI(tk.Toplevel):

    def __init__(self, server):

        # print("Initializing...")

        # Init
        super().__init__()

        # Loading Background
        if sc4mp_has_pil and state.sc4mp_config["GENERAL"]["use_fullscreen_background"]:
            self.background = ServerBackgroundUI(server)
        else:
            self.background = None

        # Title
        self.title(server.host + ":" + str(server.port))

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.minsize(800, 100)
        self.maxsize(800, 100)
        self.grid()
        center_window(self)

        # Priority
        self.lift()
        self.grab_set()

        # Key bindings
        self.bind("<Escape>", lambda event: self.destroy())

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
        self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=(10, 5))
        self.progress_bar.start(2)

        # Progress label
        self.progress_label = tk.Label(self, fg="gray", font=("Segoe UI", 8))
        self.progress_label['text'] = ""
        self.progress_label.grid(column=0, row=2, columnspan=1, padx=10, pady=0, sticky="w")

        # Duration label
        self.duration_label = tk.Label(self, fg="gray", font=("Segoe UI", 8))
        self.duration_label['text'] = ""
        self.duration_label.grid(column=1, row=2, columnspan=1, padx=10, pady=0, sticky="e")

        # Worker
        self.worker = ServerLoader(self, server)
        self.worker.start()

    def destroy(self):

        super().destroy()

        if self.background is not None:
            self.background.destroy()


class ServerBackgroundUI(tk.Toplevel):

    def __init__(self, server):

        # Init
        super().__init__()
        self.server = server
        self.destroyed = False

        # Title
        self.title(SC4MP_TITLE)

        # Geometry
        self.state('zoomed')
        self.wm_attributes("-toolwindow", True)
        self.attributes("-fullscreen", state.sc4mp_config["SC4"]["fullscreen"])

        # Load the image
        self.default_image = Image.open(get_sc4mp_path("background.png"))
        self.server_image = None

        # Canvas
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind resizing event
        self.bind("<Configure>", self.reload_image)

        # Fetch loading screen image
        th.Thread(target=self.fetch_background, daemon=True).start()

        # Loop
        # self.after(100, self.loop)

    def reload_image(self, event=None):

        # Get the new size of the window
        if event is None:
            new_width = self.winfo_width()
            new_height = self.winfo_height()
        else:
            new_width = event.width
            new_height = event.height

        if self.server_image is None:
            image = self.default_image
        else:
            image = self.server_image

        try:

            # Resize the image
            self.image_resized = image.resize((new_width, new_height))

            # Convert to PhotoImage and update the canvas
            self.image_resized_tk = ImageTk.PhotoImage(self.image_resized)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_resized_tk)
            self.canvas.image = self.image_resized_tk

        except Exception as e:

            show_error(f"An error occurred while displaying the server background.\n\n{e}", no_ui=True)

    def fetch_background(self):

        if self.destroyed:

            return

        try:

            destination: Path = state.SC4MP_LAUNCHPATH / "_Temp" / "background.png"

            if destination.exists():
                os.unlink(destination)

            with self.server.socket() as s:
                with open(destination, "wb") as file:
                    file.write(s.loading_background())

            if destination.stat().st_size > 0:

                self.server_image = Image.open(destination)

                self.reload_image()

            return

        except Exception as e:

            show_error(f"An error occurred while fetching server background.\n\n{e}", no_ui=True)

            self.retry_fetch_background()

    def retry_fetch_background(self):

        if self.destroyed:
            return

        self.server_image = None
        self.after(3000, lambda: th.Thread(target=self.fetch_background, daemon=True).start())

    # def loop(self):

    #     if sc4mp_ui.winfo_viewable():
    #         self.destroy()
    #     #elif process_exists("simcity 4.exe"):
    #     #    self.destroy()
    #         #self.after(10000, self.destroy)
    #     elif not self.destroyed:
    #         self.after(100, self.loop)

    def destroy(self):

        self.destroyed = True

        return super().destroy()

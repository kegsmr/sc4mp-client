"""Small dialogs: host a server, direct connect and about."""

from __future__ import annotations

import os
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk

from client import state
from client.constants import (
    SC4MP_AUTHOR_NAME,
    SC4MP_CONTRIBUTORS_URL,
    SC4MP_HOST,
    SC4MP_ICON,
    SC4MP_LICENSE_NAME,
    SC4MP_PORT,
    SC4MP_TITLE,
    SC4MP_URL,
    SC4MP_WEBSITE_NAME,
)
from client.errors import show_error, startfile
from client.server import Server
from client.ui.server_loader import ServerLoaderUI
from client.utils import (
    center_window,
    get_sc4mp_path,
    prep_server,
    start_server,
)


class HostUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Create default server configuration
        path = Path("_Servers" / "default")
        if not path.exists():
            path.mkdir(parents=True)
            prep_server(path)

        # Init
        super().__init__()

        # Title
        self.title("Host")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        self.maxsize(305, 375)
        self.minsize(305, 375)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())

        # Label
        self.label = ttk.Label(self, text="Select a server configuration to launch with.", justify="center")
        self.label.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # Rename/Config/Files frame
        self.rename_config_files = tk.Frame(self)
        self.rename_config_files.grid(row=1, column=0, columnspan=3, sticky="w")

        # Rename button
        self.rename_config_files.rename_button = ttk.Button(self.rename_config_files, text="Rename...", command=self.rename, default="disabled")
        self.rename_config_files.rename_button.grid(row=0, column=0, columnspan=1, padx=(10, 5), pady=10, sticky="w")

        # Config button
        self.rename_config_files.config_button = ttk.Button(self.rename_config_files, text="Edit...", command=self.config, default="disabled")
        self.rename_config_files.config_button.grid(row=0, column=1, columnspan=1, padx=5, pady=10)

        # Files button
        self.rename_config_files.files_button = ttk.Button(self.rename_config_files, text="Locate...", command=self.files, default="disabled")
        self.rename_config_files.files_button.grid(row=0, column=2, columnspan=1, padx=5, pady=10, sticky="e")

        # List box
        self.list_box_variable = tk.Variable(value=os.listdir("_Servers"))
        self.list_box = tk.Listbox(self, width=47, height=15, listvariable=self.list_box_variable)
        self.list_box.select_set(0)
        self.list_box.grid(row=2, column=0, columnspan=3, padx=10, pady=0)

        # New button
        self.new_button = ttk.Button(self, text="New...", command=self.new)
        self.new_button.grid(row=3, column=0, columnspan=1, padx=10, pady=10, sticky="w")

        # Ok/Cancel frame
        self.ok_cancel = tk.Frame(self)
        self.ok_cancel.grid(row=3, column=1, columnspan=2, sticky="se")

        # Ok button
        self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Host", command=self.ok, default="active")
        self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w")

        # Cancel button
        self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.destroy)
        self.ok_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e")

    def rename(self):

        # TODO

        return

    def config(self):

        # TODO

        return

    def files(self):

        # TODO

        return

    def new(self):

        # TODO

        return

    def ok(self):

        path = Path("_Servers") / self.list_box_variable.get()[self.list_box.curselection()[0]]

        start_server(path)

        self.destroy()


class DirectConnectUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title('Direct connect')

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('350x110')
        self.maxsize(350, 110)
        self.minsize(350, 110)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.connect())
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Up>", lambda event: self.host_entry.focus())
        self.bind("<Down>", lambda event: self.port_entry.focus())

        # Host Label
        self.host_label = ttk.Label(self, text="Host")
        self.host_label.grid(row=0, column=0, columnspan=1, padx=10, pady=20)

        # Host Entry
        self.host_entry = ttk.Entry(self, width=43)
        self.host_entry.insert(0, state.sc4mp_config["GENERAL"]["default_host"])
        self.host_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=20, sticky="w")
        self.host_entry.focus()

        # Port Label
        self.port_label = ttk.Label(self, text="Port")
        self.port_label.grid(row=1, column=0, columnspan=1, padx=10, pady=0)

        # Port Entry
        self.port_entry = ttk.Entry(self, width=5)
        self.port_entry.insert(0, state.sc4mp_config["GENERAL"]["default_port"])
        self.port_entry.grid(row=1, column=1, columnspan=1, padx=10, pady=0, sticky="w")

        # Connect/Cancel frame
        self.connect_cancel = tk.Frame(self)
        self.connect_cancel.grid(row=1, column=3, sticky="e")

        # Connect button
        self.connect_cancel.connect_button = ttk.Button(self.connect_cancel, text="Connect", command=self.connect, default="active")
        self.connect_cancel.connect_button.grid(row=0, column=0, columnspan=1, padx=3, pady=5, sticky="w")

        # Cancel button
        self.connect_cancel.cancel_button = ttk.Button(self.connect_cancel, text="Cancel", command=self.destroy)
        self.connect_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=7, pady=5, sticky="e")

    def connect(self):

        print('"Connect"')
        host = self.host_entry.get()
        port = self.port_entry.get()
        try:
            if len(host) < 1:
                host = SC4MP_HOST
                # raise ClientException("Invalid host")
            try:
                port = int(port)
            except Exception:
                port = SC4MP_PORT
                # raise ClientException("Invalid port")
            ServerLoaderUI(Server(host, port))
            self.destroy()
        except Exception as e:
            show_error(f"An unexpected error occurred while starting the server loader thread.\n\n{e}")


class AboutUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title("About")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        self.maxsize(550, 286)
        self.minsize(550, 286)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())

        # Image
        self.canvas = tk.Canvas(self, width=256, height=256)
        self.canvas.image = tk.PhotoImage(file=get_sc4mp_path("icon.png"))
        self.canvas.create_image(128, 128, anchor="center", image=self.canvas.image)
        self.canvas.grid(row=0, column=0, rowspan=5, columnspan=1, padx=10, pady=(20, 0), sticky="n")

        # Title label 1
        self.title_label_1 = ttk.Label(self, text="Title:")
        self.title_label_1.grid(row=0, column=1, columnspan=1, padx=10, pady=(20, 5), sticky="e")

        # Title label 2
        self.title_label_2 = ttk.Label(self, text=SC4MP_TITLE)
        self.title_label_2.grid(row=0, column=2, columnspan=1, padx=10, pady=(20, 5), sticky="w")

        # Author label 1
        self.author_label_1 = ttk.Label(self, text="Author:")
        self.author_label_1.grid(row=1, column=1, columnspan=1, padx=10, pady=5, sticky="e")

        # Author label 2
        self.author_label_2 = tk.Label(self, text=SC4MP_AUTHOR_NAME, fg="blue", cursor="hand2")  # , font=font.Font(underline=True))
        self.author_label_2.grid(row=1, column=2, columnspan=1, padx=10, pady=5, sticky="w")
        self.author_label_2.bind("<Button-1>", lambda e: webbrowser.open_new_tab(SC4MP_CONTRIBUTORS_URL))

        # Website label 1
        self.website_label_1 = ttk.Label(self, text="Website:")
        self.website_label_1.grid(row=2, column=1, columnspan=1, padx=10, pady=5, sticky="e")

        # Website label 2
        self.website_label_2 = tk.Label(self, text=SC4MP_WEBSITE_NAME, fg="blue", cursor="hand2")
        self.website_label_2.grid(row=2, column=2, columnspan=1, padx=10, pady=5, sticky="w")
        self.website_label_2.bind("<Button-1>", lambda e: webbrowser.open_new_tab(SC4MP_URL))

        # License label 1
        self.license_label_1 = ttk.Label(self, text="License:")
        self.license_label_1.grid(row=3, column=1, columnspan=1, padx=10, pady=(5, 80), sticky="e")

        # License label 2
        self.license_label_2 = tk.Label(self, text=SC4MP_LICENSE_NAME, fg="blue", cursor="hand2")
        self.license_label_2.grid(row=3, column=2, columnspan=1, padx=10, pady=(5, 80), sticky="w")
        self.license_label_2.bind("<Button-1>", lambda e: startfile("License.txt"))

        # Ok button
        self.ok_button = ttk.Button(self, text="Ok", command=self.ok, default="active")
        self.ok_button.grid(row=4, column=2, columnspan=1, padx=0, pady=5, sticky="se")

    def ok(self):

        self.destroy()

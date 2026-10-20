"""Password prompt shown when joining a server."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from client.constants import SC4MP_DELAY, SC4MP_ICON
from client.utils import center_window

if TYPE_CHECKING:
    # Only needed for type hints. Importing it for real would be a
    # circular import.
    from client.server_loader import ServerLoader


class PasswordDialogUI(tk.Toplevel):

    def __init__(self, server_loader, tries):

        print("Initializing...")

        # Parameters
        self.server_loader: ServerLoader = server_loader
        self.tries = tries

        # Hide server loader
        self.server_loader.ui.withdraw()

        # Init
        super().__init__()

        # Title
        self.title("" + self.server_loader.server.server_name + "")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('350x110')
        self.maxsize(350, 110)
        self.minsize(350, 110)
        self.grid()
        center_window(self)

        # Priority
        self.lift()
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.cancel())

        # Password label
        self.password_label = ttk.Label(self, text="Password")
        self.password_label.grid(row=0, column=0, columnspan=1, padx=10, pady=20)

        # Password entry
        self.password_entry = ttk.Entry(self, width=38)
        # self.password_entry.insert(0, sc4mp_config["GENERAL"]["default_host"])
        self.password_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=20, sticky="w")
        self.password_entry.config(show="*")
        self.password_entry.focus()
        # try:
        # self.password_entry.insert(0,
        # sc4mp_servers_database[self.server_loader.server.server_id]["password"])
        # except Exception:
        #    pass

        # OK/Cancel frame
        self.ok_cancel = tk.Frame(self)
        self.ok_cancel.grid(row=1, column=3, sticky="e")

        # OK button
        self.ok_cancel.ok_button = ttk.Button(
            self.ok_cancel, text="Ok", command=self.ok, default="active"
        )
        self.ok_cancel.ok_button.grid(
            row=0, column=0, columnspan=1, padx=(3, 0), pady=5, sticky="w"
        )

        # Guest button
        # if True:
        # self.ok_cancel.guest_button = ttk.Button(self.ok_cancel,
        # text="Guest", command=self.ok)
        # self.ok_cancel.guest_button.grid(row=0, column=0, columnspan=1,
        # padx=(10,0), pady=5, sticky="w")

        # Cancel button
        self.ok_cancel.cancel_button = ttk.Button(
            self.ok_cancel, text="Cancel", command=self.cancel
        )
        self.ok_cancel.cancel_button.grid(
            row=0, column=2, columnspan=1, padx=(10, 7), pady=5, sticky="e"
        )

        # Update loop
        self.wait = True
        while self.wait:
            if len(self.password_entry.get()) < 1:
                if self.server_loader.server.private:
                    self.ok_cancel.ok_button['state'] = tk.DISABLED
                else:
                    self.ok_cancel.ok_button['state'] = tk.NORMAL
                    self.ok_cancel.ok_button["text"] = "Guest"
            else:
                self.ok_cancel.ok_button['state'] = tk.NORMAL
                self.ok_cancel.ok_button["text"] = "Ok"
            time.sleep(SC4MP_DELAY)

    def ok(self):

        password = self.password_entry.get()

        if len(password) < 1:
            if self.server_loader.server.private:
                return
            else:
                self.withdraw()
                if self.server_loader.ui.background:
                    self.server_loader.ui.background.lift()
                message = (
                    "You are about to join the server as a guest.\n\n"
                    "Any cities you build will NOT be saved."
                )
                if not messagebox.askokcancel(self.server_loader.server.server_name, message,
                                              icon="info"):
                    self.deiconify()
                    return

        self.server_loader.server.password = password
        self.wait = False

        self.destroy()

        self.server_loader.ui.deiconify()
        if self.server_loader.ui.background:
            self.server_loader.ui.background.lift()
        self.server_loader.ui.lift()
        self.server_loader.ui.grab_set()

    def cancel(self):

        self.server_loader.ui.destroy()
        self.wait = False
        self.destroy()

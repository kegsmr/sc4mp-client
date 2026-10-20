"""Updater progress window and release notes window."""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from client import state
from client.constants import SC4MP_ICON, SC4MP_RELEASES_URL, SC4MP_TITLE
from client.utils import center_window


class UpdaterUI(tk.Toplevel):

    def __init__(self, parent):

        # Init
        super().__init__()

        # Parameters
        self.parent = parent

        # Title
        self.title(SC4MP_TITLE)

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.minsize(400, 95)
        self.maxsize(400, 95)
        self.grid()
        center_window(self)

        # Priority
        self.lift()
        self.grab_set()

        # Protocol
        self.protocol("WM_DELETE_WINDOW", self.delete_window)

        # Key bindings
        self.bind("<Escape>", lambda event: self.delete_window())

        # Label
        self.label = ttk.Label(self)
        self.label['text'] = "Loading..."
        self.label.grid(column=0, row=0, columnspan=2, padx=10, pady=(10, 5))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self,
            orient='horizontal',
            mode='indeterminate',
            length=380,
            maximum=100
        )
        self.progress_bar.grid(
            column=0, row=1, columnspan=2, padx=10, pady=(10, 5)
        )
        self.progress_bar.start(2)

        # Small label
        self.label_small = tk.Label(
            self, fg="gray", font=("Segoe UI", 8), text="Press <ESC> to cancel"
        )
        self.label_small.grid(
            column=0, row=2, columnspan=2, padx=10, pady=(0, 5)
        )

        # Pause underlying thread
        self.pause = False

    def delete_window(self):

        self.pause = True

        choice = messagebox.askyesnocancel(
            title=SC4MP_TITLE,
            icon="warning",
            message="Are you sure you want to continue without updating?"
        )

        if choice is None:
            sys.exit()
        elif choice is True:
            subprocess.Popen(
                [sys.executable, "-skip-update", "-allow-multiple"]
            )
            sys.exit()
        elif choice is False:
            self.pause = False

    def destroy(self):

        super().destroy()

        self.parent.destroy()


class ReleaseNotesUI(tk.Toplevel):

    def __init__(self, version: str, title: str, body: str):

        # print("Initializing...")

        # Init
        super().__init__()
        self.version = version

        # Title
        self.title(f"Version {version}")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        # self.maxsize(420, 375)
        # self.minsize(420, 375)
        self.grid()

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.destroy())
        self.bind("<Escape>", lambda event: self.destroy())

        try:

            # Title
            # self.title = ttk.Label(self, text=SC4MP_TITLE, font=("Arial", 16))
            # self.title.grid(row=10, column=0, padx=10, pady=10)

            # Description
            # self.description = ttk.Label(self, text="Thank you for using the SC4MP launcher.")
            # self.description.grid(row=11, column=0, sticky="n", padx=10, pady=10)

            # Release notes label
            self.subtitle = ttk.Label(self, text="Release notes")
            self.subtitle.grid(
                row=19, column=0, columnspan=99, sticky="w", padx=10, pady=5
            )

            # Body
            self.body = tk.Frame(
                self,
                width=400,
                height=100,
                background="white",
                highlightbackground="gray",
                highlightthickness=1
            )
            self.body.grid(row=20, column=0, padx=(10, 0), pady=0, sticky="nw")
            self.body.grid_propagate(0)

            # Body title
            self.body.title = ttk.Label(
                self.body,
                text=title,
                wraplength=(int(self.body["width"]) - 20),
                background="white",
                font=("Segoe UI", 8, "bold")
            )
            self.body.title.grid(
                row=0, column=0, columnspan=99, padx=10, pady=10, sticky="nw"
            )

            # Body text
            lines = body.splitlines()
            if len(lines) > 0 and lines[-1].startswith("**Full Changelog**"):
                lines.pop(-1)
                if len(lines) > 0 and len(lines[-1]) == 0:
                    lines.pop(-1)
            if len(lines) < 1:
                ttk.Label(
                    self.body,
                    text="No description provided.",
                    background="white",
                    font=("Segoe UI", 8, "italic")
                ).grid(row=1, column=0, columnspan=99, padx=10, pady=2, sticky="nw")
            else:
                for line_number in range(len(lines)):
                    line = lines[line_number]
                    bulleted = line.startswith("- ")
                    for sequence in ["**", "- "]:
                        line = line.replace(sequence, "")
                    if bulleted:
                        ttk.Label(self.body, text="\u2022", background="white").grid(
                            row=line_number + 1,
                            column=0,
                            columnspan=1,
                            padx=(10, 0),
                            pady=2,
                            sticky="nw"
                        )
                        line_label = ttk.Label(
                            self.body,
                            text=line,
                            wraplength=(int(self.body["width"]) - 40),
                            background="white"
                        )
                        line_label.grid(
                            row=line_number + 1, column=1, columnspan=1, padx=10, pady=2,
                            sticky="nw"
                        )
                    else:
                        line_label = ttk.Label(
                            self.body,
                            text=line,
                            wraplength=(int(self.body["width"]) - 20),
                            background="white"
                        )
                        line_label.grid(
                            row=line_number + 1, column=0, columnspan=99, padx=10, pady=2,
                            sticky="nw"
                        )

            # Body link
            self.body.link = ttk.Label(
                self.body,
                text="View all releases...",
                foreground="blue",
                background="white",
                cursor="hand2"
            )
            self.body.link.grid(
                row=99, column=0, columnspan=99, padx=10, pady=10, sticky="nw"
            )
            self.body.link.bind(
                "<Button-1>",
                lambda e: webbrowser.open_new_tab(SC4MP_RELEASES_URL)
            )

            # Resize body and window to fit content
            state.sc4mp_ui.update()
            body_height = self.body.link.winfo_y() + 30
            window_height = body_height + 75
            self.body.configure(height=body_height)
            self.maxsize(420, window_height)
            self.minsize(420, window_height)

            # Scrollbar
            # scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.body.yview)
            # self.body.configure(yscrollcommand=self.scrollbar.set)
            # self.scrollbar.grid(row=20, column=1, padx=0, pady=10)

            # Ok button
            self.ok_button = ttk.Button(
                self, text="Ok", command=self.destroy, default="active"
            )
            self.ok_button.grid(
                row=99, column=0, columnspan=99, padx=0, pady=10, sticky="s"
            )

            # Center window
            center_window(self)

        except Exception as e:

            self.destroy()

            raise e

    def destroy(self):

        state.sc4mp_config["GENERAL"]["release_notes_version"] = self.version

        state.sc4mp_config.update()

        return super().destroy()

"""The launcher's main window."""

from __future__ import annotations

import threading as th
import tkinter as tk
import webbrowser
from tkinter import Menu, messagebox

from core.util import is_windows
from client import state
from client.constants import (
    SC4MP_ICON,
    SC4MP_ISSUES_URL,
    SC4MP_README_PATH,
    SC4MP_RELEASES_URL,
    SC4MP_TITLE,
    SC4MP_VERSION,
)
from client.errors import fatal_error, open_logs, show_error
from client.server_list import ServerList
from client.ui.dialogs import AboutUI, DirectConnectUI
from client.ui.sc4_settings import SC4SettingsUI
from client.ui.server_list import ServerListUI
from client.ui.settings import GeneralSettingsUI, StorageSettingsUI
from client.ui.updater import ReleaseNotesUI
from client.updater import get_release_info
from client.utils import center_window


class UI(tk.Tk):

    def __init__(self):

        # print("Initializing...")

        # Init

        super().__init__()

        # Exceptions

        self.report_callback_exception = self.show_error

        # Title

        self.title(SC4MP_TITLE)

        # Icon

        self.iconphoto(True, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry

        self.geometry("800x600")
        self.minsize(800, 600)
        self.maxsize(800, 600)
        self.grid()
        self.lift()
        center_window(self)

        # Key bindings

        self.bind("<F1>", lambda event: self.direct_connect())
        self.bind("<F2>", lambda event: self.refresh())
        # self.bind("<F3>", lambda event:self.host())
        self.bind("<F5>", lambda event: self.general_settings())
        self.bind("<F6>", lambda event: self.storage_settings())
        self.bind("<F7>", lambda event: self.SC4_settings())

        # Menu

        menu = Menu(self)

        launcher = Menu(menu, tearoff=0)
        settings_submenu = Menu(menu, tearoff=0)
        settings_submenu.add_command(
            label="General...", accelerator="F5", command=self.general_settings
        )
        settings_submenu.add_command(
            label="Storage...", accelerator="F6", command=self.storage_settings
        )
        settings_submenu.add_command(
            label="SC4...", accelerator="F7", command=self.SC4_settings
        )
        launcher.add_cascade(label="Settings", menu=settings_submenu)
        launcher.add_separator()
        launcher.add_command(
            label="Updates...",
            command=lambda: webbrowser.open_new_tab(SC4MP_RELEASES_URL)
        )
        launcher.add_separator()
        launcher.add_command(label="Exit", command=self.quit)
        # TODO rename to "Launcher" and put settings in cascade?
        menu.add_cascade(label="Launcher", menu=launcher)

        servers = Menu(menu, tearoff=0)

        servers.add_command(
            label="Connect...", accelerator="F1", command=self.direct_connect
        )
        servers.add_command(
            label="Refresh", accelerator="F2", command=self.refresh
        )
        # servers.add_separator()
        # servers.add_command(label="Host...", accelerator="F3", command=self.host)
        menu.add_cascade(label="Servers", menu=servers)

        help = Menu(menu, tearoff=0)
        help.add_command(label="About...", command=self.about)
        help.add_command(label="Readme...", command=self.readme)
        help.add_separator()
        help.add_command(label="Logs...", command=open_logs)
        help.add_separator()
        help.add_command(
            label="Feedback...",
            command=lambda: webbrowser.open_new_tab(SC4MP_ISSUES_URL)
        )
        # feedback_submenu = Menu(help, tearoff=0)
        # feedback_submenu.add_command(label=SC4MP_FEEDBACK_LINKS[0][0],
        # command=lambda:webbrowser.open_new_tab(SC4MP_FEEDBACK_LINKS[0][1]))
        # feedback_submenu.add_command(label=SC4MP_FEEDBACK_LINKS[1][0],
        # command=lambda:webbrowser.open_new_tab(SC4MP_FEEDBACK_LINKS[1][1]))
        # for link in SC4MP_FEEDBACK_LINKS:
        # feedback_submenu.add_command(label=link[0],
        # command=lambda:webbrowser.open_new_tab(link[1])) #TODO why does the
        # github button open discord?
        # help.add_cascade(label="Feedback", menu=feedback_submenu)
        menu.add_cascade(label="Help", menu=help)

        self.config(menu=menu)

        # Release notes

        th.Thread(target=self.release_notes, daemon=True).start()

        # Server browser

        if state.sc4mp_config["GENERAL"]["use_server_browser"]:
            self.server_list = ServerListUI(self)
            self.server_list.grid(row=0, column=0, padx=0, pady=0, sticky="w")
        else:
            # \n\nTo get started, press <F1> and enter the IP address and port
            # of the server you wish to connect to.")
            self.label = tk.Label(self, text="SERVER BROWSER DISABLED")
            self.label.pack(anchor="center", pady=250)
            # self.label = tk.Label(self, justify="center", text='To get
            # started, select "Servers" then "Connect..." in the menu bar and
            # enter the hostname and port of the server you wish to connect
            # to.')
            # self.label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    def release_notes(self):

        try:

            # Set version for release info
            version = SC4MP_VERSION

            # Get current release info
            release_info = get_release_info(version=version)

            # Set beta flag to `True` if pre-release
            if "prerelease" in release_info.keys():
                state.sc4mp_beta = release_info["prerelease"]

            # Create release notes UI
            general_config = state.sc4mp_config["GENERAL"]
            if (general_config["show_release_notes"]
                    and general_config["release_notes_version"] != SC4MP_VERSION):
                ReleaseNotesUI(
                    version, release_info["name"], release_info["body"]
                )

        except Exception as e:

            show_error(f"Unable to show release notes.\n\n{e}", no_ui=True)

    def show_error(self, *args):

        fatal_error()

    def to_implement(self):

        tk.messagebox.showerror(
            title=SC4MP_TITLE,
            message=(
                "This feature is incomplete and will be available in future "
                "versions of the client."
            )
        )

    def general_settings(self):
        print('"General settings..."')
        GeneralSettingsUI()

    def storage_settings(self):
        print('"Storage settings..."')
        StorageSettingsUI()

    def SC4_settings(self):

        print('"SC4 settings..."')
        SC4SettingsUI()

    def host(self):

        print('"Host..."')

        if is_windows():
            message = (
                "One of the next releases of the SC4MP Launcher will be capable "
                "of hosting servers from within the launcher, but for now, you can "
                "run the SC4MP Server manually. See the Github repository for more "
                "information.\n\n"
            )
        else:
            message = ""

        question = (
            "Hosting a server requires the SC4MP Server application.\n\n"
            f"{message}Would you like to view the GitHub repository?"
        )
        if messagebox.askyesno(SC4MP_TITLE, question):
            webbrowser.open_new_tab("https://github.com/kegsmr/sc4mp-server/")

    def direct_connect(self):

        print('"Direct connect..."')
        DirectConnectUI()

    def refresh(self):

        if state.sc4mp_config["GENERAL"]["use_server_browser"]:
            self.server_list.worker = ServerList(
                self.server_list, kill=self.server_list.worker
            )
            self.server_list.worker.start()

    def about(self):

        AboutUI()

    def readme(self):

        webbrowser.open_new_tab(SC4MP_README_PATH)

    def withdraw(self):
        super().withdraw()
        try:
            self.server_list.worker.pause = True
        except Exception:
            show_error("Unable to pause server list thread.", no_ui=True)

    def deiconify(self):
        super().deiconify()
        try:
            self.server_list.worker.pause = False
        except Exception:
            pass

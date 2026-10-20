"""Settings windows: general, storage and SimCity 4."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from core.config import Config
from core.util import format_filesize, parse_filesize
from client import state
from client.config import update_config_constants, update_config_value
from client.constants import SC4MP_ICON, SC4MP_TITLE
from client.errors import ClientException, show_error, show_warning
from client.game_monitor import GameLauncher
from client.sc4 import get_sc4_path, is_steam_sc4
from client.utils import center_window, purge_directory


class GeneralSettingsUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title("General settings")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        self.maxsize(450, 425)
        self.minsize(450, 425)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())

        # Config update
        self.config_update = []

        # Updates frame
        self.updates_frame = tk.LabelFrame(self, text="Updates", width=50)
        self.updates_frame.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10, sticky="nw"
        )

        # Updates checkbutton
        self.updates_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["auto_update"]
        )
        self.updates_frame.checkbutton = ttk.Checkbutton(
            self.updates_frame,
            text="Check for updates at startup",
            onvalue=True,
            offvalue=False,
            variable=self.updates_frame.checkbutton_variable
        )
        self.updates_frame.checkbutton.grid(
            row=0, column=0, columnspan=1, padx=10, pady=(10, 10), sticky="w"
        )
        self.config_update.append(
            (self.updates_frame.checkbutton_variable, "auto_update")
        )

        # UI frame
        self.ui_frame = tk.LabelFrame(self, text="UI")
        self.ui_frame.grid(
            row=1, column=0, columnspan=1, padx=10, pady=0, sticky="nw"
        )

        # Use game overlay
        self.ui_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["use_game_overlay"]
        )
        self.ui_frame.checkbutton = ttk.Checkbutton(
            self.ui_frame,
            text="Use game overlay",
            onvalue=True,
            offvalue=False,
            variable=self.ui_frame.checkbutton_variable
        )
        self.ui_frame.checkbutton.grid(
            row=0,
            column=0,
            columnspan=1,
            padx=(10, 65),
            pady=(10, 5),
            sticky="w"
        )
        self.config_update.append(
            (self.ui_frame.checkbutton_variable, "use_game_overlay")
        )

        # Use launcher map
        # self.ui_frame.checkbutton_variable =
        # tk.BooleanVar(value=sc4mp_config["GENERAL"]["use_launcher_map"])
        # self.ui_frame.checkbutton = ttk.Checkbutton(self.ui_frame, text="Use
        # launcher map", onvalue=True, offvalue=False,
        # variable=self.ui_frame.checkbutton_variable)
        # self.ui_frame.checkbutton.grid(row=1, column=0, columnspan=1,
        # padx=10, pady=(5,5), sticky="w")
        # self.config_update.append((self.ui_frame.checkbutton_variable, "use_launcher_map"))

        # Use fullscreen background
        self.ui_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["use_fullscreen_background"]
        )
        self.ui_frame.checkbutton = ttk.Checkbutton(
            self.ui_frame,
            text="Use loading background",
            onvalue=True,
            offvalue=False,
            variable=self.ui_frame.checkbutton_variable
        )
        self.ui_frame.checkbutton.grid(
            row=2, column=0, columnspan=1, padx=10, pady=(5, 10), sticky="w"
        )
        self.config_update.append(
            (self.ui_frame.checkbutton_variable, "use_fullscreen_background")
        )

        # Mayors online cutoff label
        # self.ui_frame.mayors_online_cutoff_label = tk.Label(self.ui_frame,
        # text="Show mayors online in the past")
        # self.ui_frame.mayors_online_cutoff_label.grid(row=0, column=0, padx=10, pady=(10,5))

        # Mayors online cutoff combobox
        # self.ui_frame.mayors_online_cutoff_combobox = ttk.Combobox(self.ui_frame)
        # self.ui_frame.mayors_online_cutoff_combobox.grid(row=0, column=1)

        # Security frame
        self.security_frame = tk.LabelFrame(self, text="Security")
        self.security_frame.grid(
            row=0,
            column=1,
            columnspan=1,
            rowspan=2,
            padx=10,
            pady=10,
            sticky="nw"
        )

        # Save server passwords checkbutton
        self.security_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["save_server_passwords"]
        )
        self.security_frame.checkbutton = ttk.Checkbutton(
            self.security_frame,
            text="Save server passwords",
            onvalue=True,
            offvalue=False,
            variable=self.security_frame.checkbutton_variable
        )
        self.security_frame.checkbutton.grid(
            row=0, column=0, columnspan=1, padx=10, pady=(10, 5), sticky="w"
        )
        self.config_update.append(
            (self.security_frame.checkbutton_variable, "save_server_passwords")
        )

        # Ignore 3rd-party server warnings checkbutton
        self.security_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["ignore_third_party_server_warnings"]
        )
        self.security_frame.checkbutton = ttk.Checkbutton(
            self.security_frame,
            text="Hide 3rd-party server warnings",
            onvalue=True,
            offvalue=False,
            variable=self.security_frame.checkbutton_variable
        )
        self.security_frame.checkbutton.grid(
            row=1, column=0, columnspan=1, padx=10, pady=(5, 5), sticky="w"
        )
        self.config_update.append(
            (self.security_frame.checkbutton_variable, "ignore_third_party_server_warnings")
        )

        # Ignore authentication errors checkbutton
        self.security_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["ignore_token_errors"]
        )
        self.security_frame.checkbutton = ttk.Checkbutton(
            self.security_frame,
            text="Hide authentication warnings",
            onvalue=True,
            offvalue=False,
            variable=self.security_frame.checkbutton_variable
        )
        self.security_frame.checkbutton.grid(
            row=2, column=0, columnspan=1, padx=10, pady=(5, 5), sticky="w"
        )
        self.config_update.append(
            (self.security_frame.checkbutton_variable, "ignore_token_errors")
        )

        # Ignore file warnings checkbutton
        self.security_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["ignore_risky_file_warnings"]
        )
        self.security_frame.checkbutton = ttk.Checkbutton(
            self.security_frame,
            text="Hide dangerous file warnings",
            onvalue=True,
            offvalue=False,
            variable=self.security_frame.checkbutton_variable
        )
        self.security_frame.checkbutton.grid(
            row=3, column=0, columnspan=1, padx=10, pady=(5, 32), sticky="w"
        )
        self.config_update.append(
            (self.security_frame.checkbutton_variable, "ignore_risky_file_warnings")
        )

        # Path frame
        self.path_frame = tk.LabelFrame(self, text="Custom plugins")
        self.path_frame.grid(
            row=10, column=0, columnspan=3, padx=10, pady=10, sticky="w"
        )

        # Path checkbutton
        self.path_frame.checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["GENERAL"]["custom_plugins"]
        )
        self.path_frame.checkbutton = ttk.Checkbutton(
            self.path_frame,
            text="Enable",
            onvalue=True,
            offvalue=False,
            variable=self.path_frame.checkbutton_variable
        )
        self.path_frame.checkbutton.grid(
            row=0, column=0, columnspan=1, padx=10, pady=(10, 5), sticky="w"
        )
        self.config_update.append(
            (self.path_frame.checkbutton_variable, "custom_plugins")
        )

        # Path entry
        self.path_frame.entry = ttk.Entry(self.path_frame, width=50)
        self.path_frame.entry.grid(
            row=1, column=0, columnspan=1, padx=10, pady=10
        )
        self.path_frame.entry.insert(
            0, state.sc4mp_config["GENERAL"]["custom_plugins_path"]
        )
        self.config_update.append(
            (self.path_frame.entry, "custom_plugins_path")
        )

        # Path browse button
        self.path_frame.button = ttk.Button(
            self.path_frame, text="Browse...", command=self.browse_path
        )
        self.path_frame.button.grid(
            row=1, column=1, columnspan=1, padx=10, pady=10
        )

        # Path label
        self.path_frame.label = ttk.Label(
            self.path_frame,
            text=(
                'Some servers allow users to load their own plugins alongside the server \n'
                'plugins. Specify your plugins directory here so that they can be loaded \n'
                'when joining a server.'
            )
        )
        self.path_frame.label.grid(
            row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w"
        )

        # Reset button
        self.reset_button = ttk.Button(self, text="Reset", command=self.reset)
        self.reset_button.grid(
            row=99, column=0, columnspan=1, padx=10, pady=10, sticky="sw"
        )

        # Ok/Cancel frame
        self.ok_cancel = tk.Frame(self)
        self.ok_cancel.grid(row=99, column=1, columnspan=2, sticky="se")

        # Ok button
        self.ok_cancel.ok_button = ttk.Button(
            self.ok_cancel, text="Ok", command=self.ok, default="active"
        )
        self.ok_cancel.ok_button.grid(
            row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w"
        )

        # Cancel button
        self.ok_cancel.cancel_button = ttk.Button(
            self.ok_cancel, text="Cancel", command=self.destroy
        )
        self.ok_cancel.cancel_button.grid(
            row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e"
        )

    def browse_path(self):

        path = filedialog.askdirectory(parent=self)
        if len(path) > 0:
            self.path_frame.entry.delete(0, 'end')
            self.path_frame.entry.insert(0, path)

    def update(self):
        for item in self.config_update:
            data = item[0].get()
            key = item[1]
            update_config_value("GENERAL", key, data)

    def ok(self):

        self.update()
        state.sc4mp_config.update()
        self.destroy()

    def reset(self):

        if messagebox.askokcancel(
                title=SC4MP_TITLE,
                message="Revert settings to the default configuration?",
                icon="warning"
        ):
            self.destroy()
            state.sc4mp_config.data.pop("GENERAL")
            state.sc4mp_config.update()
            state.sc4mp_config.data = Config(
                state.sc4mp_config.PATH,
                state.sc4mp_config.DEFAULTS,
                error_callback=show_error,
                update_constants_callback=update_config_constants
            ).data
            self.__init__()


class StorageSettingsUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title("Storage settings")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        self.maxsize(450, 250)
        self.minsize(450, 250)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())

        # Config update
        self.config_update = []

        # Path frame
        self.path_frame = tk.LabelFrame(self, text="Launch path")
        self.path_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w"
        )

        # Path entry
        self.path_frame.entry = ttk.Entry(self.path_frame, width=50)
        self.path_frame.entry.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10
        )
        self.path_frame.entry.insert(
            0, state.sc4mp_config["STORAGE"]["storage_path"]
        )
        self.config_update.append((self.path_frame.entry, "storage_path"))

        # Path browse button
        self.path_frame.button = ttk.Button(
            self.path_frame, text="Browse...", command=self.browse_path
        )
        self.path_frame.button.grid(
            row=0, column=1, columnspan=1, padx=10, pady=10
        )

        # Path label
        self.path_frame.label = ttk.Label(
            self.path_frame,
            text=(
                'Do NOT change this to your normal launch directory, or else your plugins \n'
                'and regions will be deleted!'
            )
        )
        self.path_frame.label.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w"
        )

        # Cache size frame
        self.cache_size_frame = tk.LabelFrame(self, text="Cache size")
        self.cache_size_frame.grid(
            row=99, column=0, columnspan=1, padx=10, pady=10, sticky="w"
        )

        # Cache size entry
        self.cache_size_frame.entry = ttk.Entry(
            self.cache_size_frame, width=10
        )
        self.cache_size_frame.entry.insert(
            0, format_filesize(state.sc4mp_config["STORAGE"]["cache_size"] * 1000000)
        )
        self.cache_size_frame.entry.grid(
            row=0, column=0, columnspan=1, padx=(10, 0), pady=10, sticky="w"
        )
        self.config_update.append((self.cache_size_frame.entry, "cache_size"))

        # Cache size label
        # self.cache_size_frame.label = ttk.Label(self.cache_size_frame, text="mb")
        # self.cache_size_frame.label.grid(row=0, column=1, columnspan=1,
        # padx=(2,10), pady=10, sticky="w")

        # Clear cache button
        self.cache_size_frame.button = ttk.Button(
            self.cache_size_frame, text="Clear cache", command=self.clear_cache
        )
        self.cache_size_frame.button.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w"
        )

        # Reset button
        self.reset_button = ttk.Button(self, text="Reset", command=self.reset)
        self.reset_button.grid(
            row=99, column=1, columnspan=1, padx=10, pady=10, sticky="sw"
        )

        # Ok/Cancel frame
        self.ok_cancel = tk.Frame(self)
        self.ok_cancel.grid(row=99, column=2, columnspan=2, sticky="se")

        # Ok button
        self.ok_cancel.ok_button = ttk.Button(
            self.ok_cancel, text="Ok", command=self.ok, default="active"
        )
        self.ok_cancel.ok_button.grid(
            row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w"
        )

        # Cancel button
        self.ok_cancel.cancel_button = ttk.Button(
            self.ok_cancel, text="Cancel", command=self.destroy
        )
        self.ok_cancel.cancel_button.grid(
            row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e"
        )

    def clear_cache(self):

        # if (messagebox.askokcancel(title=SC4MP_TITLE, message="Clear the
        # download cache?", icon="warning")): #TODO make yes/no
        purge_directory(Path(state.SC4MP_LAUNCHPATH) / "_Cache")

    def browse_path(self):

        path = filedialog.askdirectory(parent=self)
        if len(path) > 0:
            self.path_frame.entry.delete(0, 'end')
            self.path_frame.entry.insert(0, path)

    def update(self):
        restart = False
        for item in self.config_update:
            data = item[0].get()
            key = item[1]
            if (key == "storage_path"
                    and type(data) is str
                    and Path(data) != Path(state.sc4mp_config["STORAGE"]["storage_path"])):
                if (Path(data) / 'Plugins').exists() or (Path(data) / 'Regions').exists():
                    message = (
                        f'The directory "{data}" already contains SimCity 4 plugins and '
                        'regions. \n\n'
                        'Proceeding will result in the IRREVERSIBLE DELETION of these files! \n\n'
                        'This is your final warning, do you wish to proceed?'
                    )
                    # TODO make message box show yes/no and not ok/cancel
                    if not messagebox.askokcancel(title=SC4MP_TITLE, message=message,
                                                  icon="warning"):
                        raise ClientException("Operation cancelled by user.")
                else:
                    message = (
                        "Changing the launch path will cause you to lose access to your "
                        "claimed tiles on servers you play on.\n\n"
                        "You will only be able to access these claims in the future by "
                        "setting the launch path back to what it's currently set to now.\n\n"
                        "Do you wish to proceed?"
                    )
                    if not messagebox.askokcancel(title=SC4MP_TITLE, message=message,
                                                  icon="warning"):
                        raise ClientException("Operation cancelled by user.")
                restart = True
            if key == "cache_size":
                try:
                    data = parse_filesize(data) / 1000000
                except ValueError:
                    try:
                        data = int(data)
                    except Exception as e:
                        show_error(e, no_ui=True)
                        continue
            update_config_value("STORAGE", key, data)
        if restart:
            if Path(sys.executable).name == "sc4mpclient.exe":
                subprocess.Popen(
                    [sys.executable, "-skip-update", "-allow-multiple"]
                )
            else:
                # Restart from the entry script (sc4mpclient.py), which is
                # two folders up from this file
                ui_dir = os.path.dirname(os.path.abspath(__file__))
                client_dir = os.path.dirname(ui_dir)
                entry_path = os.path.join(
                    os.path.dirname(client_dir), "sc4mpclient.py"
                )
                subprocess.Popen([sys.executable, entry_path])
            state.sc4mp_ui.quit()
        # create_subdirectories()
        # load_database()

    def ok(self):

        try:
            self.update()
            state.sc4mp_config.update()
            self.destroy()
        except ClientException:
            pass

    def reset(self):

        # TODO make yes/no
        if messagebox.askokcancel(title=SC4MP_TITLE,
                                  message="Revert settings to the default configuration?",
                                  icon="warning"):
            self.destroy()
            state.sc4mp_config.data.pop("STORAGE")
            state.sc4mp_config.update()
            state.sc4mp_config.data = Config(
                state.sc4mp_config.PATH,
                state.sc4mp_config.DEFAULTS,
                error_callback=show_error,
                update_constants_callback=update_config_constants
            ).data
            self.__init__()


class SC4SettingsUI(tk.Toplevel):

    def __init__(self):

        # print("Initializing...")

        # Init
        super().__init__()

        # Title
        self.title("SC4 settings")

        # Icon
        self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

        # Geometry
        self.geometry('400x400')
        self.maxsize(385, 305)
        self.minsize(385, 305)
        self.grid()
        center_window(self)

        # Priority
        self.grab_set()

        # Key bindings
        self.bind("<Return>", lambda event: self.ok())
        self.bind("<Escape>", lambda event: self.destroy())

        # Config update
        self.config_update = []

        # Path frame
        self.path_frame = tk.LabelFrame(self, text="Custom installation path")
        self.path_frame.grid(
            row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w"
        )

        # Path entry
        self.path_frame.entry = ttk.Entry(self.path_frame, width=40)
        self.path_frame.entry.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10
        )
        self.path_frame.entry.insert(0, state.sc4mp_config["SC4"]["game_path"])
        self.config_update.append((self.path_frame.entry, "game_path"))

        # Path browse button
        self.path_frame.button = ttk.Button(
            self.path_frame, text="Browse...", command=self.browse_path
        )
        self.path_frame.button.grid(
            row=0, column=1, columnspan=1, padx=10, pady=10
        )

        # Path label
        self.path_frame.label = ttk.Label(
            self.path_frame,
            text=(
                'If the launcher fails to find SimCity 4 installed on your computer, \n'
                'specify the path to the game installation here.'
            )
        )
        self.path_frame.label.grid(
            row=1, column=0, columnspan=2, padx=10, pady=(0, 10)
        )

        # Resolution frame
        self.resolution_frame = tk.LabelFrame(self, text="Resolution")
        self.resolution_frame.grid(
            row=1,
            column=0,
            columnspan=1,
            rowspan=2,
            padx=10,
            pady=5,
            sticky="w"
        )

        # Resolution combo box
        self.resolution_frame.combo_box = ttk.Combobox(
            self.resolution_frame, width=15
        )
        if 0 in (state.sc4mp_config["SC4"]["resw"], state.sc4mp_config["SC4"]["resh"]):
            self.resolution_frame.combo_box.insert(0, "Automatic")
        else:
            resolution = (
                str(state.sc4mp_config["SC4"]["resw"]) + "x"
                + str(state.sc4mp_config["SC4"]["resh"])
            )
            self.resolution_frame.combo_box.insert(0, resolution)
        self.resolution_frame.combo_box["values"] = (
            "Automatic",
            "800x600 (4:3)",
            "1024x768 (4:3)",
            "1280x800 (16:10)",
            "1280x1024 (5:4)",
            "1440x900 (16:10)",
            "1600x1200 (4:3)",
            "1680x1050 (16:10)",
            "1920x1080 (16:9)",
            "2048x1152 (16:9)"
        )
        self.resolution_frame.combo_box.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w"
        )
        self.config_update.append((self.resolution_frame.combo_box, "res"))

        # Fullscreen checkbutton
        self.resolution_frame.fullscreen_checkbutton_variable = tk.BooleanVar(
            value=state.sc4mp_config["SC4"]["fullscreen"]
        )
        self.resolution_frame.fullscreen_checkbutton = ttk.Checkbutton(
            self.resolution_frame,
            text="Fullscreen",
            onvalue=True,
            offvalue=False,
            variable=self.resolution_frame.fullscreen_checkbutton_variable
        )
        self.resolution_frame.fullscreen_checkbutton.grid(
            row=1, column=0, columnspan=1, padx=10, pady=(14, 25), sticky="w"
        )
        self.config_update.append(
            (self.resolution_frame.fullscreen_checkbutton_variable, "fullscreen")
        )

        # CPU count frame
        self.cpu_count_frame = tk.LabelFrame(self, text="CPU count")
        self.cpu_count_frame.grid(
            row=1,
            column=1,
            columnspan=1,
            rowspan=1,
            padx=10,
            pady=5,
            sticky="w"
        )

        # CPU count entry
        self.cpu_count_frame.entry = ttk.Entry(self.cpu_count_frame, width=10)
        self.cpu_count_frame.entry.insert(
            0, str(state.sc4mp_config["SC4"]["cpu_count"])
        )
        self.cpu_count_frame.entry.grid(
            row=0, column=0, columnspan=1, padx=10, pady=5, sticky="w"
        )
        self.config_update.append((self.cpu_count_frame.entry, "cpu_count"))

        # CPU priority frame
        self.cpu_priority_frame = tk.LabelFrame(self, text="CPU priority")
        self.cpu_priority_frame.grid(
            row=1,
            column=2,
            columnspan=1,
            rowspan=1,
            padx=10,
            pady=5,
            sticky="e"
        )

        # CPU priority entry
        self.cpu_priority_frame.combo_box = ttk.Combobox(
            self.cpu_priority_frame, width=8
        )
        self.cpu_priority_frame.combo_box.insert(
            0, state.sc4mp_config["SC4"]["cpu_priority"]
        )
        self.cpu_priority_frame.combo_box["values"] = ("low", "normal", "high")
        self.cpu_priority_frame.combo_box.grid(
            row=0, column=0, columnspan=1, padx=10, pady=5, sticky="w"
        )
        self.config_update.append(
            (self.cpu_priority_frame.combo_box, "cpu_priority")
        )

        # Additional properties frame
        self.additional_properties_frame = tk.LabelFrame(
            self, text="Additional launch properties"
        )
        self.additional_properties_frame.grid(
            row=2, column=1, columnspan=2, padx=10, pady=5, sticky="w"
        )

        # Additional properties entry
        self.additional_properties_frame.entry = ttk.Entry(
            self.additional_properties_frame, width=30
        )
        self.additional_properties_frame.entry.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w"
        )
        self.additional_properties_frame.entry.insert(
            0, state.sc4mp_config["SC4"]["additional_properties"]
        )
        self.config_update.append(
            (self.additional_properties_frame.entry, "additional_properties")
        )

        # Reset/Preview frame
        self.reset_preview = tk.Frame(self)
        self.reset_preview.grid(row=99, column=0, columnspan=2, sticky="w")

        # Reset button
        self.reset_preview.reset_button = ttk.Button(
            self.reset_preview, text="Reset", command=self.reset
        )
        self.reset_preview.reset_button.grid(
            row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w"
        )

        # Preview button
        self.reset_preview.preview_button = ttk.Button(
            self.reset_preview, text="Preview", command=self.preview
        )
        self.reset_preview.preview_button.grid(
            row=0, column=1, columnspan=1, padx=0, pady=10, sticky="e"
        )

        # Ok/Cancel frame
        self.ok_cancel = tk.Frame(self)
        self.ok_cancel.grid(row=99, column=1, columnspan=2, sticky="e")

        # Ok button
        self.ok_cancel.ok_button = ttk.Button(
            self.ok_cancel, text="Ok", command=self.ok, default="active"
        )
        self.ok_cancel.ok_button.grid(
            row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w"
        )

        # Cancel button
        self.ok_cancel.cancel_button = ttk.Button(
            self.ok_cancel, text="Cancel", command=self.destroy
        )
        self.ok_cancel.cancel_button.grid(
            row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e"
        )

    def browse_path(self):

        path = filedialog.askdirectory(parent=self)
        if len(path) > 0:
            self.path_frame.entry.delete(0, 'end')
            self.path_frame.entry.insert(0, path)

    def update(self):
        for item in self.config_update:
            data = item[0].get()
            key = item[1]
            if key == "game_path":
                if state.sc4mp_config["SC4"]["use_steam_browser_protocol"] in [0, 1]:
                    if is_steam_sc4(Path(data)):
                        update_config_value("SC4", "use_steam_browser_protocol", 1)
                    else:
                        update_config_value("SC4", "use_steam_browser_protocol", 0)
            if key == "res":
                try:
                    if len(data) < 1 or data.lower().startswith("auto"):
                        resw = 0
                        resh = 0
                    else:
                        res = data.split(' ')[0]
                        resw, resh = res.split('x')
                    update_config_value("SC4", "resw", resw)
                    update_config_value("SC4", "resh", resh)
                except Exception as e:
                    show_error(e, no_ui=True)
            else:
                update_config_value("SC4", key, data)

    def ok(self):

        self.update()
        state.sc4mp_config.update()
        self.destroy()

    def reset(self):

        if messagebox.askokcancel(
                title=SC4MP_TITLE,
                message="Revert settings to the default configuration?",
                icon="warning"
        ):
            self.destroy()
            state.sc4mp_config.data.pop("SC4")
            state.sc4mp_config.update()
            state.sc4mp_config.data = Config(
                state.sc4mp_config.PATH,
                state.sc4mp_config.DEFAULTS,
                error_callback=show_error,
                update_constants_callback=update_config_constants
            ).data
            self.__init__()

    def preview(self):

        # Hide the settings window and main ui
        self.withdraw()
        state.sc4mp_ui.withdraw()

        # Backup the current config data
        config_data_backup = state.sc4mp_config["SC4"].copy()

        # Update the config
        self.update()

        # Load the game
        try:

            # Check if a path to SimCity 4 can be found, prompt for a custom
            # path if needed
            while get_sc4_path() is None:
                show_warning(
                    'No SimCity 4 installation found. \n\n'
                    'Please provide the correct installation path.'
                )
                path = filedialog.askdirectory(parent=state.sc4mp_ui)
                if len(path) > 0:
                    state.sc4mp_config["SC4"]["game_path"] = path
                    self.path_frame.entry.delete(0, 'end')
                    self.path_frame.entry.insert(0, path)
                else:
                    break

            # Load the game if a path to SimCity 4 can be found
            if get_sc4_path() is not None:

                # Informational dialog
                message = (
                    'You are about to launch SimCity 4 in preview mode.\n\n'
                    'The purpose of preview mode is to test your SC4 launch configuration '
                    'before joining a server. Any cities you build in preview mode will '
                    'NOT be saved.\n\n'
                    'Once the game exits, the SC4 settings window will reappear. If the '
                    'game does not launch, your SC4 settings are invalid.'
                )
                if not messagebox.askokcancel(title=SC4MP_TITLE, message=message,
                                              icon="info"):
                    raise ClientException("Operation cancelled by user.")

                # Purge plugins and regions
                purge_directory(Path(state.SC4MP_LAUNCHPATH) / "Plugins")
                purge_directory(Path(state.SC4MP_LAUNCHPATH) / "Regions")

                # Run the game launcher (on the current thread)
                game_launcher = GameLauncher()
                game_launcher.run()

        # Catch ClientExceptions silently
        except ClientException as e:

            # Show a silent error
            show_error(e, no_ui=True)

        # Catch any and all errors
        except Exception as e:

            # Show an error popup
            show_error(
                "An error occurred while launching the game in preview "
                f"mode.\n\n{e}"
            )

        # Restore the old config data
        state.sc4mp_config["SC4"] = config_data_backup

        # Show and lift the main ui and settings ui once the game has shutdown
        state.sc4mp_ui.deiconify()
        state.sc4mp_ui.lift()
        self.deiconify()
        self.lift()

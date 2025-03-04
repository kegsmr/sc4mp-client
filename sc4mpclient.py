from __future__ import annotations

import configparser
import ctypes
import hashlib
import inspect
import json
import math
import os
import platform
import random
import re
import shutil
import socket
import string
import struct
import subprocess
import sys
import threading as th
import time
import tkinter as tk
import tkinter.font as tkfont
import traceback
import urllib.request
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import Menu, filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Optional

try:
	from PIL import Image, ImageTk, UnidentifiedImageError
	sc4mp_has_pil = True
except ImportError:
	sc4mp_has_pil = False

#pylint: disable=wildcard-import
#pylint: disable=unused-wildcard-import
from core.config import *
from core.dbpf import *
from core.networking import *
from core.util import *


# Header

SC4MP_VERSION = "0.8.2"

SC4MP_SERVERS = get_server_list()

SC4MP_GITHUB_REPO = "kegsmr/sc4mp-client"

SC4MP_URL = "https://www.sc4mp.org/"
SC4MP_CONTRIBUTORS_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/contributors/"
SC4MP_ISSUES_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/issues/"
SC4MP_RELEASES_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/releases/"

SC4MP_AUTHOR_NAME = "SimCity 4 Multiplayer Project"
SC4MP_WEBSITE_NAME = "www.sc4mp.org"
SC4MP_LICENSE_NAME = "MIT-0"

SC4MP_CONFIG_PATH = "config.ini"
SC4MP_LOG_PATH = "sc4mpclient.log"
SC4MP_README_PATH = "readme.html"
SC4MP_RESOURCES_PATH = "resources"

SC4MP_TITLE = format_title("SC4MP Launcher", version=SC4MP_VERSION)
SC4MP_ICON: Path = Path(SC4MP_RESOURCES_PATH) / "icon.png"

SC4MP_HOST = "localhost" #SC4MP_SERVERS[0][0]
SC4MP_PORT = 7240 #SC4MP_SERVERS[0][1]

SC4MP_BUFFER_SIZE = 4096

SC4MP_DELAY = .1

SC4MP_LAUNCHERMAP_ENABLED = False 		#TODO replace with config setting eventually

SC4MP_CONFIG_DEFAULTS = [
	("GENERAL", [

		("default_host", SC4MP_HOST),
		("default_port", SC4MP_PORT),

		("auto_update", True),
		("release_notes_version", SC4MP_VERSION),
		("show_release_notes", True),

		("use_server_browser", True),
		("server_browser_filter", ""),
		("scan_lan", True),
		("stat_mayors_online_cutoff", 60),
		("show_actual_download", True),
		("show_rank_bars", True),
		("show_offline_servers", True),
		("use_fullscreen_background", True),
		("use_launcher_map", True),
		("use_game_overlay", 1),
		("allow_game_monitor_exit", True),

		("save_server_passwords", True),
		("ignore_third_party_server_warnings", False),
		("ignore_token_errors", False),
		("ignore_risky_file_warnings", False),

		("custom_plugins", False),
		("custom_plugins_path", Path("~/Documents/SimCity 4/Plugins").expanduser()),	

		("sync_simcity_4_cfg", True),

	]),
	("STORAGE", [

		("storage_path", Path("_SC4MP").absolute()),
		("cache_size", 8000)

	]),
	("SC4", [

		("game_path", ""),
		("use_steam_browser_protocol", 0),
		
		("resw", 0),			#1200
		("resh", 0),			#800
		("fullscreen", True),	#False

		("cpu_count", 1),
		("cpu_priority", "high"),

		("additional_properties", "")

	]),
	("DEBUG", [

		("random_server_stats", False),
		("ignore_incompatable_versions", False),
		
	])
]

SC4MP_LAUNCHPATH = None
SC4MP_LAUNCHRESW = None
SC4MP_LAUNCHRESH = None
SC4MP_CUSTOMPATH = None

SC4MP_RISKY_FILE_EXTENSIONS = [".bat", ".bin", ".cmd", ".com", ".cpl", ".dll", ".exe", ".gadget", ".inf1", ".ins",
							    ".inx", ".isu", ".jar", ".job", ".jse", ".lnk", ".msc", ".msi", ".msp", ".mst",
								".paf", ".pif", ".py", ".ps1", ".reg", ".rgs", ".scr", ".sct", ".sh", ".shb",
								".shs", ".u3p", ".vb", ".vbe", ".vbs", ".vbscript", ".ws", ".wsf", ".wsh"]

SC4MP_URL_PREFIX = "sc4mp://"

SC4MP_SERVERS_DOMAIN = "servers.sc4mp.org"
SC4MP_INVITES_DOMAIN = "invite.sc4mp.org"

sc4mp_args = sys.argv

sc4mp_ui = None

sc4mp_current_server = None

sc4mp_game_monitor_x = 10
sc4mp_game_monitor_y = 40

sc4mp_beta = None


# Functions

def main():
	"""The main function.

	Arguments:
		None

	Returns:
		None
	"""

	try:

		# URL launch behavior
		url_launch = len(sc4mp_args) > 1 and sc4mp_args[1].startswith(SC4MP_URL_PREFIX)
		url_launch_exit_after = True
	
		# Exit if already runnning (unless launching using URL)
		if not "-allow-multiple" in sc4mp_args:
			try:
				count = process_count("sc4mpclient.exe")
				if count is not None and count > 1:
					if url_launch:
						url_launch_exit_after = False
						if process_exists("simcity 4.exe"):
							return
						else:
							try:
								our_pid: int = os.getpid()
								pids: list[int] = get_image_pids("sc4mpclient.exe")
								if pids is not None:
									if our_pid in pids:
										pids.remove(our_pid)
									for pid in pids:
										if subprocess.call(f"TASKKILL /F /PID {pid}", shell=True) != 0:
											return
							except Exception:
								return
					else:
						tk.Tk().withdraw()
						close_splash()
						messagebox.showerror(title=SC4MP_TITLE, message="SC4MP Launcher is already running!")
						return
			except Exception:
				pass

		# Set working directory
		exec_path = Path(sys.executable)
		exec_file = exec_path.name
		exec_dir = exec_path.parent
		if exec_file == "sc4mpclient.exe":
			os.chdir(exec_dir)

		# Output
		sys.stdout = Logger()
		set_thread_name("Main", enumerate=False)

		# Title
		print(SC4MP_TITLE)

		# "-force-update"/"-skip-update" flags
		global sc4mp_force_update, sc4mp_skip_update
		sc4mp_force_update = "-force-update" in sc4mp_args
		sc4mp_skip_update = "-skip-update" in sc4mp_args or (len(sc4mp_args) > 1 and not sc4mp_force_update)

		# "-no-ui" flag
		global sc4mp_ui
		sc4mp_ui = not "-no-ui" in sc4mp_args

		# "-exit-after" flag
		global sc4mp_exit_after
		sc4mp_exit_after = "-exit-after" in sc4mp_args

		# "--host" argument
		global sc4mp_host
		sc4mp_host = None
		if "--host" in sc4mp_args:
			try:
				sc4mp_host = get_arg_value("--host", sc4mp_args)
			except Exception as e:
				raise ClientException("Invalid arguments.") from e

		# "--port" argument
		global sc4mp_port
		sc4mp_port = None
		if "--port" in sc4mp_args:
			try:
				sc4mp_port = int(get_arg_value("--port", sc4mp_args))
			except Exception as e:
				raise ClientException("Invalid arguments.") from e
			
		# "--password" argument
		global sc4mp_password
		sc4mp_password = None
		if "--password" in sc4mp_args:
			try:
				sc4mp_password = get_arg_value("--password", sc4mp_args)
			except Exception as e:
				raise ClientException("Invalid arguments.") from e

		# Launch using URL
		if url_launch:
			try:
				url = sc4mp_args[1]
				url = url.replace(SC4MP_URL_PREFIX, "", 1)
				if url.endswith("/"):
					url = url[:-1]
				url = url.split(":")
				if len(url) > 1:
					sc4mp_host = ":".join(url[:-1])
					sc4mp_port = int(url[-1])
				else:
					sc4mp_host = url[0]
					sc4mp_port = 7240
				sc4mp_exit_after = url_launch_exit_after
			except Exception:
				show_error(f"Invalid URL.\n\nURLs must adhere to:\nsc4mp://<host>:<port>\n\nURL given:\n{sc4mp_args[1]}")
				return

		# Prep
		prep()

		# Client
		if sc4mp_ui:
			if sc4mp_host is not None and sc4mp_port is not None:
				if sc4mp_exit_after:
					sc4mp_ui = tk.Tk()
					sc4mp_ui.withdraw()
				else:
					sc4mp_ui = UI()
				server = Server(sc4mp_host, sc4mp_port)
				server.password = sc4mp_password
				ServerLoaderUI(server)
			else:
				sc4mp_ui = UI()
			close_splash()
			sc4mp_ui.mainloop()
		else:
			sc4mp_ui = None
			if sc4mp_host == None or sc4mp_port == None:
				print("[PROMPT] Connect to server:")
			if sc4mp_host == None:
				sc4mp_host = input("[PROMPT] - Enter server address... ")
			if sc4mp_port == None:
				sc4mp_port = int(input("[PROMPT] - Enter server port... "))
			server = Server(sc4mp_host, sc4mp_port)
			server.fetch()
			if sc4mp_password == None and server.password_enabled:
				sc4mp_password = input("[PROMPT] - Enter server password... ")
			server.password = sc4mp_password
			ServerLoader(None, server).run()

	except KeyboardInterrupt:

		pass

	except Exception as e:

		# Fatal error 
		fatal_error()

	# Cleanup
	print("Shutting down...")
	cleanup()


def prep():
	"""Prepares the client to launch."""
	
	load_config()
	check_updates()
	create_subdirectories()
	load_database()


def cleanup():
	
	sc4mp_servers_database.end = True


def load_config():
	"""Loads settings from the configuration file."""

	global sc4mp_config

	print("Loading config...")

	sc4mp_config = Config(SC4MP_CONFIG_PATH, SC4MP_CONFIG_DEFAULTS, error_callback=show_error, update_constants_callback=update_config_constants)


def check_updates():

	if sc4mp_config["GENERAL"]["auto_update"] and (not sc4mp_skip_update):

		print("Checking for updates...")

		try:

			global sc4mp_ui

			# Get the path of the executable file which is currently running
			exec_path = Path(sys.executable)
			exec_file = exec_path.name
			exec_dir = exec_path.parent

			# Only update if running a Windows distribution
			if sc4mp_force_update or exec_file == "sc4mpclient.exe":

				# Get latest release info
				latest_release_info = get_release_info()

				# Download the update if the version is newer
				if sc4mp_force_update or unformat_version(latest_release_info["tag_name"]) > unformat_version(SC4MP_VERSION):

					# Local function for update thread
					def update(ui=None):
						
						try:

							set_thread_name("UpdtThread", enumerate=False)

							# Function to pause updates when user presses <ESC>
							def pause():
								while ui.pause:
									time.sleep(.1)

							# Function to write to console and update ui
							def report(message):
								print(message)
								ui.label["text"] = message

							# Change working directory to the one where the executable can be found
							if exec_file == "sc4mpclient.exe":
								os.chdir(exec_dir)

							# Purge update directory
							try:
								if os.path.exists("update"):
									purge_directory(Path("update"))
							except Exception:
								pass

							# Delete uninstaller if exists
							try:
								for filename in ["unins000.dat", "unins000.exe"]:
									if os.path.exists(filename):
										os.unlink(filename)
							except Exception:
								pass

							# Give the user a chance to cancel the update
							if ui is not None:
								report("Preparing update...")
								time.sleep(3)

							# Pause if necessary
							pause()

							# Loop until download is successful
							while True:

								try:

									# Update UI
									report("Downloading update...")

									# Pause if necessary
									pause()

									# Get download URL
									download_url = None
									for asset in latest_release_info["assets"]:
										if asset["name"].startswith("sc4mp-client-installer-windows"):
											download_url = asset["browser_download_url"]
											destination = os.path.join("update", asset["name"])
											break

									# Raise an exception if the download URL was not found
									if download_url is None:
										raise ClientException("The correct release asset was not found.")

									# Pause if necessary
									pause()

									# Prepare destination
									os.makedirs("update", exist_ok=True)
									if os.path.exists(destination):
										os.unlink(destination)

									# Pause if necessary
									pause()

									# Download file
									download_size = int(urllib.request.urlopen(download_url).headers["Content-Length"])
									if ui is not None:
										ui.label["text"] = "Downloading update... (0%)"
										ui.progress_bar["mode"] = "determinate"
										ui.progress_bar["maximum"] = download_size
										ui.progress_bar["value"] = 0
									with urllib.request.urlopen(download_url) as rfile:
										with open(destination, "wb") as wfile:
											download_size_downloaded = 0
											while download_size_downloaded < download_size:
												while ui.pause:
													time.sleep(.1)
												if ui is not None:
													ui.label["text"] = f"Downloading update... ({int(100 * (download_size_downloaded / download_size))}%)"
													ui.progress_bar["value"] = download_size_downloaded
												bytes_read = rfile.read(SC4MP_BUFFER_SIZE) 
												download_size_downloaded += len(bytes_read)
												wfile.write(bytes_read)

									# Pause if necessary
									pause()

									# Report installing update
									report("Installing update...")
									if ui is not None:
										ui.progress_bar['mode'] = "indeterminate"
										ui.progress_bar['maximum'] = 100
										ui.progress_bar.start(2)
										
									# Pause if necessary
									pause()

									# Start installer in very silent mode and exit
									subprocess.Popen([os.path.abspath(destination), f"/dir={os.getcwd()}", "/verysilent"])
									ui.destroy()
								
								except Exception as e:

									show_error(f"An error occurred in the update thread.\n\n{e}", no_ui=True)

									# Retry
									if ui is not None:
										ui.progress_bar['mode'] = "indeterminate"
										ui.progress_bar.start(2)
										for count in range(5):
											report(f"Update failed. Retrying in {5 - count}...")
											time.sleep(1)
						
						except Exception:

							# All uncaught errors in thread trigger a fatal error
							fatal_error()

					# Prepare the UI if not running in command-line mode
					if sc4mp_ui:

						# Create hidden top-level window
						sc4mp_ui = tk.Tk()
						sc4mp_ui.iconphoto(True, tk.PhotoImage(file=SC4MP_ICON))
						sc4mp_ui.withdraw()

						# Create updater UI
						updater_ui = UpdaterUI(sc4mp_ui)

						# Start update thread
						th.Thread(target=update, kwargs={"ui": updater_ui}, daemon=True).start()

						# Run the UI main loop
						close_splash()
						sc4mp_ui.mainloop()

						# Exit when complete
						sys.exit()

					else:

						# Run update thread directly
						update()
			
		except Exception as e:

			# Show error silently and continue as usual
			show_error(f"An error occurred while updating.\n\n{e}", no_ui=True)


def get_release_info(version="latest", timeout=10) -> dict:

	if version == "latest":
		github_api_call = f"https://api.github.com/repos/{SC4MP_GITHUB_REPO}/releases/latest"
	else:
		github_api_call = f"https://api.github.com/repos/{SC4MP_GITHUB_REPO}/releases/tags/v{version}"

	try:
		with urllib.request.urlopen(url=github_api_call, timeout=timeout) as url:
			return json.load(url)
	except urllib.error.URLError as e:
		raise ClientException("GitHub API call timed out.") from e
	
	
def update_config_constants(config):
	"""For backwards compatibility. Updates the global config constants that are sometimes used internally."""

	global SC4MP_LAUNCHPATH
	global SC4MP_LAUNCHRESW
	global SC4MP_LAUNCHRESH
	global SC4MP_CUSTOMPATH

	SC4MP_LAUNCHPATH = config['STORAGE']['storage_path']
	SC4MP_LAUNCHRESW = config['SC4']['resw']
	SC4MP_LAUNCHRESH = config['SC4']['resh']
	SC4MP_CUSTOMPATH = config['SC4']['game_path']


def create_subdirectories() -> None:
	"""Creates the required subdirectories in the launch directory if they do not yet exist."""

	print("Creating subdirectories...")

	directories = [
		Path("_Cache"),
		Path("_Configs"),
		Path("_Database"),
		Path("_Salvage"),
		Path("_Temp"),
		Path("_Temp") / "ServerList",
		Path("Plugins"),
		Path("Plugins") / "client",
		#Path("Plugins") / "default",
		Path("Plugins") / "server",
		Path("Regions")
	] #"SC4MPBackups", os.path.join("_Cache","Plugins"), os.path.join("_Cache","Regions")]

	# Update old directory names
	#if (os.path.exists(os.path.join(SC4MP_LAUNCHPATH, "_Profiles"))):
	#	os.rename(os.path.join(SC4MP_LAUNCHPATH, "_Database"), os.path.join(SC4MP_LAUNCHPATH, "_Database"))

	# Create new directories
	launchdir = Path(SC4MP_LAUNCHPATH)
	launchdir.mkdir(exist_ok=True, parents=True)
	for directory in directories:
		new_directory = launchdir / directory
		try:
			new_directory.mkdir(exist_ok=True, parents=True)
		except Exception as e:
			raise ClientException("Failed to create SC4MP subdirectories.\n\n" + str(e)) from e
		
	# Create notice files
	with open(launchdir / "_Cache" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
		file.write("These files are OK to delete if you want to save disk space. You can also delete them in the launcher in the storage settings.")
	with open(launchdir / "_Configs" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
		file.write("These files are OK to delete, but some of your in-game settings may change if you do.")
	with open(launchdir / "_Temp" / "___DELETE THESE FILES IF YOU WANT___", "w") as file:
		file.write("These files are OK to delete if you want to save disk space. Don't do it while the launcher is running though.")
	with open(launchdir / "_Database" / "___DO NOT DELETE OR SHARE THESE FILES___", "w") as file:
		file.write("Deleting these files can cause you to lose access to your claims in servers you've joined. Only delete them if you know what you're doing.\n\nSharing these files with someone else will let that person access all your claims and mess with your cities. Don't do it!")
	with open(launchdir / "_Salvage" / "___DO NOT DELETE THESE FILES___", "w") as file:
		file.write("Deleting these files will make you unable to restore the salvaged savegames stored here. If you don't care about that, then go ahead and delete them.")


def load_database():
	

	print("Loading database...")

	global sc4mp_servers_database
	sc4mp_servers_database = DatabaseManager(Path(SC4MP_LAUNCHPATH) / "_Database" / "servers.json")
	sc4mp_servers_database.start()


def get_sc4_path() -> Optional[Path]:
	"""Returns the path to the SimCity 4 executable if found."""

	# The path specified by the user
	config_path = Path(sc4mp_config['SC4']['game_path'])

	# Common SC4 dirs (alternate path used by GOG and Origin)
	sc4_dirs = Path("SimCity 4 Deluxe") / "Apps" / "SimCity 4.exe"
	sc4_dirs_alt = Path("SimCity 4 Deluxe Edition") / "Apps" / "SimCity 4.exe"

	# Common Steam dirs
	steam_dirs = Path("Steam") / "steamapps" / "common"

	# On Windows, this is most likely the C:\ drive
	home_drive = Path(Path.home().drive)

	# List of common SC4 install dirs, highest priority at the top
	possible_paths: list[Path] = [
		
		# Custom (specified by the user)
		config_path,
		config_path / "SimCity 4.exe",
		config_path / "Apps" / "SimCity 4.exe",

		# Generic (probably pirated copies lol)
		home_drive / "Games" / sc4_dirs,
		home_drive / "Games" / sc4_dirs_alt,
		home_drive / "Program Files" / sc4_dirs,
		home_drive / "Program Files" / sc4_dirs_alt,
		home_drive / "Program Files (x86)" / sc4_dirs,
		home_drive / "Program Files (x86)" / sc4_dirs_alt,

		# GOG (patched, no DRM, launches without issue)
		home_drive / "Program Files" / "GOG Galaxy" / "Games" / sc4_dirs_alt,
		home_drive / "Program Files (x86)" / "GOG Galaxy" / "Games" / sc4_dirs_alt,
		home_drive / "GOG Games" / sc4_dirs,
		home_drive / "GOG Games" / sc4_dirs_alt,

		# Steam (patched, but sometimes has launch issues)
		home_drive / "Program Files" / steam_dirs / sc4_dirs,
		home_drive / "Program Files (x86)" / steam_dirs / sc4_dirs,
		home_drive / "SteamLibrary" / steam_dirs / sc4_dirs,

		# Origin (maybe patched? Origin is crap)
		home_drive / "Program Files" / "Origin Games" / sc4_dirs_alt,
		home_drive / "Program Files (x86)" / "Origin Games" / sc4_dirs_alt,

		# Maxis (probably not patched, so this goes at the bottom)
		home_drive / "Program Files" / "Maxis" / sc4_dirs,
		home_drive / "Program Files (x86)" / "Maxis" / sc4_dirs,

	]

	# Return the FIRST path that exists in the list
	for possible_path in possible_paths:
		if possible_path.is_file():
			return possible_path

	# Return `None` if none of the paths exist
	return None


def start_sc4():
	"""Attempts to find the install path of SimCity 4 and launches the game with custom launch parameters if found."""

	print("Starting SimCity 4...")

	# Variables related to game monitor exit, etc. etc.
	global sc4mp_allow_game_monitor_exit_if_error, sc4mp_game_exit_ovveride
	sc4mp_allow_game_monitor_exit_if_error = False
	sc4mp_game_exit_ovveride = False

	# Check if SC4 is already running
	try:
		if process_exists("simcity 4.exe"):
			show_error("SimCity 4 is already running!")
			return
	except Exception as e:
		show_error(e, no_ui=True)
		
	# Get path to SC4 using a list of possible paths
	path = get_sc4_path()

	# Cancel launch if path to SC4 not found
	if not path:
		show_error("Path to SimCity 4 not found. Specify the correct path in settings.")
		return

	resw = sc4mp_config["SC4"]["resw"]
	resh = sc4mp_config["SC4"]["resh"]

	if 0 in (resw, resh):
		if sc4mp_ui:
			resw = sc4mp_ui.winfo_screenwidth()
			resh = sc4mp_ui.winfo_screenheight()
		else:
			resw = 1280
			resh = 800


	# Arguments set based on config settings
	arguments = [str(path),
			  f'-UserDir:"{SC4MP_LAUNCHPATH}{os.sep}"', # add trailing slash here because SC4 expects it
			  '-intro:off',
			  '-CustomResolution:enabled',
			  f'-r{resw}x{resh}x32',
			  f'-CPUCount:{sc4mp_config["SC4"]["cpu_count"]}',
			  f'-CPUPriority:{sc4mp_config["SC4"]["cpu_priority"]}'
			  ]
	if sc4mp_config["SC4"]["fullscreen"]:
		arguments.append('-f')
	else:
		arguments.append('-w')
	arguments.extend(sc4mp_config["SC4"]["additional_properties"].strip().split(' '))  # assumes that properties do not have spaces

	# `True` if the game is installed using Steam
	steam_sc4 = is_steam_sc4(path)

	# Set to `True` once the game is launched successfully with the Steam browser protocol
	steam_launch = False

	# If SC4 is installed through Steam, try to launch it using the Steam browser protocol
	if sc4mp_config["SC4"]["use_steam_browser_protocol"] == 2  or (sc4mp_config["SC4"]["use_steam_browser_protocol"] == 1 and steam_sc4):

		# Steam browser protocol command
		command = "steam://run/24780//" + ' '.join(arguments[1:]).replace("\\", "\\\\").replace('"', '\\"') + "/"
		
		# Notify the user about the Steam dialog box that will popup
		#messagebox.showinfo(title=SC4MP_TITLE, message="Steam will now ask your permission to launch SC4 with custom arguments.\n\nClick \"Continue\" on the Steam dialog box to launch SC4.\n\nConnection will be cancelled in 30 seconds if the game does not launch.")

		# Launch the game
		print(f"- using Steam browser protocol ('{command}').")
		try:
			steam_launch = webbrowser.open(command)
			if not steam_launch:
				print("[WARNING] Unable to launch SimCity 4 using the Steam browser protocol (`webbrowser.open` returned `False`).")
		except Exception as e:
			show_error(f"Unable to launch SimCity 4 using the Steam browser protocol.\n\n{e}", no_ui=True)

	# If SC4 isn't installed through Steam, or if launching it through the Steam browser protocol didn't work, launch the SC4 exe directly
	if not steam_launch:

		# Regular command
		command = ' '.join(arguments)

		# Launch the game
		print(f"- launching directly ('{command}').")
		try:
			if is_windows():
				subprocess.run(command) 			# `subprocess.run(arguments)` won't work on Windows for some unknowable reason
			else:
				subprocess.run(arguments)  			# on Linux, the first String passed as argument must be a file that exists
		except PermissionError as e:
			show_error(f"The launcher does not have the necessary privileges to launch SimCity 4. Try running the SC4MP Launcher as administrator.")

	else:

		# Using Steam SC4 otherwise
		steam_sc4 = True

	# Wait an extra 30 seconds if running the Steam version of SC4 (needed for Steam browser protocol, also sometimes Steam isn't started yet)
	if steam_sc4:
		try:
			time.sleep(1)
			count = 0
			while process_exists("Steam.exe") and not process_exists("simcity 4.exe") and count < 30:
				time.sleep(1)
				count += 1
		except Exception as e:
			show_error(e, no_ui=True)
			time.sleep(30)

	# Wait for SC4 to close if running the Steam version of SC4 (the Steam version of SC4 spawns a separate process)
	if steam_sc4:
		sc4mp_allow_game_monitor_exit_if_error = True
		time.sleep(5)
		while True:
			if sc4mp_game_exit_ovveride:
				print("Exiting without checking whether SC4 is still running...")
				return
			try:
				while process_exists("simcity 4.exe"):
					time.sleep(1)
				break
			except Exception as e:
				show_error("An error occured while checking if SC4 had exited yet.", no_ui=True)
				time.sleep(10)
	
	# SimCity 4 has closed
	print("SimCity 4 closed.")


def is_steam_sc4(path: Path):

	#COMMON_STEAM_FILES = ["Steam.dll", "steam_api.dll", "steam_api64.dll", "steam_appid.txt", "steamclient.dll", "steamclient64.dll"]

	#exec_dir = path.parent.parent
	#exec_dir_filenames = os.listdir(exec_dir)

	#for steam_filename in COMMON_STEAM_FILES:
	#	if steam_filename in exec_dir_filenames:
	#		return True

	return "steamapps" in [directory.name.lower() for directory in path.parents]


def process_exists(process_name): #TODO add MacOS compatability / deprecate in favor of `process_count`?
	
	if is_windows():
		call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
		output = subprocess.check_output(call, shell=True).decode()
		last_line = output.strip().split('\r\n')[-1]
		return last_line.lower().startswith(process_name.lower())
	else:
		return None


def get_sc4mp_path(filename: str) -> Path:
	"""Returns the path to a given file in the SC4MP "resources" subdirectory"""
	return Path(SC4MP_RESOURCES_PATH) / filename


def random_string(length):
	"""Returns a random string of ascii letters of the specified length."""
	return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(length))


def purge_directory(directory: Path, recursive=True) -> None:
	"""Deletes all files and subdirectories of a directory"""
	for path in directory.iterdir():
		try:
			if path.is_file():
				path.unlink()
			elif path.is_dir():
				if recursive:
					shutil.rmtree(path)
		except PermissionError as e:
			raise ClientException(f'Failed to delete "{path}" because the file is being used by another process.') from e #\n\n' + str(e)


def directory_size(directory: Path) -> int:
	"""Returns the size of a directory recursively."""

	size = 0

	with os.scandir(directory) as items:
		for item in items:
			if item.is_file():
				size += item.stat().st_size
			elif item.is_dir():
				size += directory_size(item.path)

	return size


def load_json(filename):
	"""Returns data from a json file as a dictionary."""
	try:
		with open(filename, 'r') as file:
			data = json.load(file)
			if data == None:
				return dict()
			else:
				return data
	except FileNotFoundError:
		return dict()


def update_json(filename, data):
	"""Writes data as a dictionary to a json file."""
	with open(filename, 'w') as file:
		file.seek(0)
		json.dump(data, file, indent=4)
		file.truncate()


def show_error(e, no_ui=False):
	"""Shows an error message in the console and optionally in the UI."""
	message = None
	if isinstance(e, str):
		message = e
	else: 
		message = str(e)

	print(f"[ERROR] {message}\n\n{traceback.format_exc()}")

	if not no_ui:
		if sc4mp_ui != None:
			if sc4mp_ui == True:
				tk.Tk().withdraw()
				close_splash()
			messagebox.showerror(SC4MP_TITLE, message)


def startfile(filename):
	syst = platform.system()
	if syst == "Windows":
		os.startfile(filename)
	else:
		opener = "open" if syst == "Darwin" else "xdg-open"  # Linux
		subprocess.call([opener, filename])


def open_logs():
	if has_powershell():
		subprocess.Popen([
			"cmd.exe", "/c", "start", "cmd.exe", "/k",
			f"@echo off && powershell -NoProfile -ExecutionPolicy Bypass -Command $Host.UI.RawUI.WindowTitle = \"{SC4MP_TITLE}\"; gc sc4mpclient.log -Wait -Tail 1000"
		])
	else:
		startfile(SC4MP_LOG_PATH)


def fatal_error():
	"""Shows a fatal error message in the console and the UI. Exits the program."""

	message = f"A fatal error occurred.\n\n{traceback.format_exc()}"

	print(f"[FATAL] {message}")

	if sc4mp_ui != None:
		if sc4mp_ui == True:
			tk.Tk().withdraw()
			close_splash()
		messagebox.showerror(SC4MP_TITLE, message)
		open_logs()

	try:
		cleanup()
	except Exception as e:
		show_error(e, no_ui=True)

	sys.exit()


def show_warning(e):
	"""Shows a warning in the console and the UI."""
	message = None
	if isinstance(e, str):
		message = e
	else: 
		message = str(e)

	print(f"[WARNING] {message}")

	if sc4mp_ui != None:
		if sc4mp_ui == True:
			tk.Tk().withdraw()
			close_splash()
		messagebox.showwarning(SC4MP_TITLE, message)


def center_window(window):
	"""Centers a tkinter window."""
	win = window
	win.update_idletasks()
	width = win.winfo_width()
	frm_width = win.winfo_rootx() - win.winfo_x()
	win_width = width + 2 * frm_width
	height = win.winfo_height()
	titlebar_height = win.winfo_rooty() - win.winfo_y()
	win_height = height + titlebar_height + frm_width
	x = win.winfo_screenwidth() // 2 - win_width // 2
	y = win.winfo_screenheight() // 2 - win_height // 2
	win.geometry(f'{width}x{height}+{x}+{y}')
	win.deiconify()


def prep_server(path: Path) -> None:
	"""Runs the server executable in prep mode. Takes the server path as an argument."""
	subprocess.Popen(f"sc4mpserver.exe -prep --server-path {path}")


def start_server(path: Path) -> None:
	"""Runs the server executable. Takes the server path as an argument."""
	subprocess.Popen(f"sc4mpserver.exe --server-path {path}", creationflags=subprocess.CREATE_NEW_CONSOLE)

	#th.Thread(target=lambda: subprocess.Popen("sc4mpserver.exe --server-path " + str(path))).start()


def update_config_value(section, item, value):
	"""Updates a value in the config, attempting to convert it to the proper data type."""
	try:
		t = type(sc4mp_config[section][item])
		sc4mp_config[section][item] = t(value)
	except Exception:
		show_error(f'Invalid config value for "{item}" in section "{section}"', no_ui=True)


def get_fullpaths_recursively(dir: Path) -> list[Path]:
	"""Returns full paths of all files in a directory recursively."""
	return [path for path in dir.rglob("*") if path.is_file()]


def get_relpaths_recursively(dir: Path) -> list[Path]:
	"""Returns relative paths of all files in a directory recursively."""
	return [path.relative_to(dir) for path in dir.rglob("*") if path.is_file()]


def get_arg_value(arg, args):
	"""Returns the following token in commandline arguments."""
	return args[args.index(arg) + 1]


def request_header(s, server):
	"""A "handshake" between the client and server which establishes that a request can be made."""

	s.recv(SC4MP_BUFFER_SIZE)
	s.sendall(SC4MP_VERSION.encode())

	if server.password_enabled:
		s.recv(SC4MP_BUFFER_SIZE)
		s.sendall(server.password.encode())

	s.recv(SC4MP_BUFFER_SIZE)
	s.sendall(server.user_id.encode())


def set_server_data(entry, server):
	"""Updates the json entry for a given server with the appropriate values."""
	entry["host"] = server.host
	entry["port"] = server.port
	entry["server_name"] = server.server_name
	entry["server_description"] = server.server_description
	entry["server_url"] = server.server_url
	entry["server_version"] = server.server_version
	entry["password_enabled"] = server.password_enabled
	entry["user_plugins"] = server.user_plugins_enabled
	entry.setdefault("first_contact", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	entry["last_contact"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_sc4_cfg_path() -> Path: #TODO can this find the cfg for the origin version?
	"""Returns the path to the `SimCity 4.cfg` file"""
	return Path(SC4MP_LAUNCHPATH) / "SimCity 4.cfg"


def get_sc4_cfg() -> dict:
	"""Returns data parsed from the SimCity 4.cfg file"""
	return SC4Config(get_sc4_cfg_path(), error_callback=show_error).get_simcity_4_cfg() 


def get_last_region_name() -> str:
	"""Returns the last open region stored in the `SimCity 4.cfg` file."""
	return get_sc4_cfg()["LastRegionName"]


def region_open(region) -> bool:
	"""Checks if a given region is open in SC4."""
	return region == get_last_region_name()

	#cfg_path = get_sc4_cfg_path()
	#return b"\x00" + region.encode() + b"\x00" in DBPF(cfg_path, error_callback=show_error).decompress_subfile("a9dd6e06").read()


def refresh_region_open() -> bool:
	"""Checks if the refresh region is open in SC4"""
	return region_open("Refresh...")


def prep_region_config(path):
	
	try:

		REGION_NAME_PREFIX = "[SC4MP] "

		config = configparser.RawConfigParser()
		config.read(path)
		
		region_name = config.get("Regional Settings", "Name")
		
		if not region_name.startswith(REGION_NAME_PREFIX):
			
			config.set("Regional Settings", "Name", REGION_NAME_PREFIX + region_name)

			with open(path, 'wt') as config_file:
				config.write(config_file)

	except Exception as e:

		raise ClientException(f"Failed to prepare region config at {path}.") from e


def format_download_size(size):
	if size == 0:
		return "..."
	else:
		return format_filesize(size)


def get_bitmap_dimensions(filename):
	

	with open(filename, "rb") as file:
		data = bytearray(file.read())

	width = struct.unpack_from('<i', data, 18)
	height = struct.unpack_from('<i', data, 22)

	return width[0], height[0]


def arp():
	if is_windows():
		call = 'arp', '-a'
		output = subprocess.check_output(call, shell=True).decode()
		return [line for line in re.findall('([-.0-9]+)\s+([-0-9a-f]{17})\s+(\w+)', output)]
	else: #TODO make this work on other platforms besides Windows
		return []


def format_url(url: str) -> str:
	if not (url.startswith("http://") or url.startswith("https://")):
		return f"http://{url}"
	else:
		return url


def sync_simcity_4_cfg(to_mp=False):

	try:

		# Get paths to singleplayer and multiplayer `SimCity 4.cfg` files
		sp_config_path = Path("~/Documents/SimCity 4/SimCity 4.cfg").expanduser()
		mp_config_path = SC4MP_LAUNCHPATH / "SimCity 4.cfg"

		# Pick the source and destination based on whether the transfer is to or from multiplayer
		source = sp_config_path if to_mp else mp_config_path
		destination = mp_config_path if to_mp else sp_config_path
		
		# Copy the files
		print(f"\"{source}\" -> \"{destination}\"")
		if source.exists():
			if destination.exists():
				backup = destination.with_suffix(destination.suffix + ".bak")
				if not backup.exists():
					shutil.copy(destination, backup)
				os.unlink(destination)
			shutil.copy(source, destination)

	except Exception as e:

		show_error(f"An error occurred while transfering the SimCity 4 config.\n\n{e}", no_ui=True)


def sanitize_relpath(basepath: Path, relpath: str) -> Path:

	fullpath = basepath / relpath

	if str(fullpath.resolve()).startswith(str(basepath.resolve())):
		return fullpath
	else:
		raise ValueError(f"Invalid relative path: \"{relpath}\".")


def copy_to_clipboard(text: str):

	sc4mp_ui.clipboard_clear()
	sc4mp_ui.clipboard_append(text)


def get_image_pids(image_name) -> list[int] | None:
	"""
	Find the PIDs of processes with the given image name on Windows.

	Args:
		image_name (str): The name of the process image (e.g., "notepad.exe").

	Returns:
	    list: A list of PIDs for processes matching the given image name.
	"""

	if is_windows():

		pids = []

		try:

			# Use tasklist to get the list of processes
			result = subprocess.run(["tasklist"], capture_output=True, text=True, check=True, shell=True)
			lines = result.stdout.splitlines()

			# Regex pattern to match process name followed by its PID
			pattern = re.compile(rf"^{re.escape(image_name)}\s+(\d+)", re.IGNORECASE)

			for line in lines:
				match = pattern.match(line)
				if match:
					try:
						pids.append(int(match.group(1)))  # Extract PID
					except ValueError:
						pass

			return pids if pids else None

		except subprocess.CalledProcessError as e:
			print(f"An error occurred while getting image PIDs.\n\n{e}")
			return None
		
	else:

		return None


def close_splash():

	try:
		import pyi_splash
		pyi_splash.close()
	except ImportError:
		pass


def window_open(image_name):
    """
    Check if a process with the given image name has an open, visible window.

    Args:
        image_name (str): The name of the process image (e.g., "notepad.exe").

    Returns:
        bool: True if at least one instance of the process has a visible window, False otherwise.
    """

    pids = get_image_pids(image_name)
    # print(f"PIDs for {image_name}: {pids}")  # Debugging

    if not pids:
        return False  # No matching processes found

    EnumWindows = ctypes.windll.user32.EnumWindows
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

    # Properly define the callback function with ctypes
    def callback(hwnd, lParam):
        """Callback function to check if a window belongs to the given PID and is visible."""
        window_pid = ctypes.c_ulong()
        GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

        if window_pid.value in pids and IsWindowVisible(hwnd):
            ctypes.cast(lParam, ctypes.POINTER(ctypes.c_bool)).contents.value = True
            return False  # Stop enumeration

        return True  # Continue searching

    # Create a ctypes boolean variable to store result
    found = ctypes.c_bool(False)

    # Convert callback to proper function pointer type
    CALLBACK_TYPE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
    EnumWindows(CALLBACK_TYPE(callback), ctypes.byref(found))

    return found.value


# Objects

class Server:
	"""An interface for interaction with a server."""


	def __init__(self, host, port):

		self.host = host
		self.port = port

		self.fetched = False
		#self.stats = False
		self.password = None
		self.user_id = None

		self.categories = ["All"]
		if self.host == SC4MP_SERVERS_DOMAIN:
			self.categories.append("Official")


	def fetch(self):
		"""Retreives basic information from a server and saves them as instance variables. Updates the json entry for the server if possible."""

		# Mark server as fetched
		self.fetched = True

		# Request server info
		try:
			s = socket.socket()
			s.settimeout(10)
			s.connect((self.host, self.port))
			s.send(b"info")
			server_info = recv_json(s)
		except Exception as e:
			raise ClientException("Unable to find server. Check the IP address and port, then try again.") from e

		#server_info = self.request("info")
		#if server_info is not None:
		#	try:
		#		server_info = json.loads("{"+ "{".join(server_info.split("{")[1:]))
		#		#print(server_info)
		#	except Exception:
		#		raise ClientException("Unable to fetch server info.")
		#else:
		#	raise ClientException("Unable to find server. Check the IP address and port, then try again.")
		
		self.server_id = sanitize_directory_name(server_info["server_id"]) #self.request("server_id")
		self.server_name = server_info["server_name"] #self.request("server_name")
		self.server_description = server_info["server_description"] #self.request("server_description")
		self.server_url = server_info["server_url"] #self.request("server_url")
		self.server_version = server_info["server_version"] #self.request("server_version")
		self.password_enabled = server_info["password_enabled"] #self.request("password_enabled") == "y"
		self.private = server_info["private"] #self.request("private") == "y"
		self.user_plugins_enabled = server_info["user_plugins_enabled"] #self.request("user_plugins_enabled") == "y"
		try:
			self.claim_duration = server_info["claim_duration"]
			self.max_region_claims = server_info["max_region_claims"]
			self.godmode_filter = server_info["godmode_filter"]
		except KeyError:
			pass

		if self.server_id in sc4mp_servers_database.keys():
			self.password = sc4mp_servers_database[self.server_id].get("password", None) # Needed for stat fetching private servers

		if self.password_enabled:
			self.categories.append("Private")
		else:
			self.categories.append("Public")

		#if (self.server_version != None):
		#	self.server_version = unformat_version(self.server_version)

		if self.fetched == True:
			try:
				self.update_database()
			except Exception as e:
				show_error("An error occured while updating the server database.", no_ui = True)


	def fetch_stats(self):
		

		if not sc4mp_config["DEBUG"]["random_server_stats"]:

			download = self.fetch_temp()

			regions_path: Path = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server_id / "Regions"

			server_time = self.time()

			mayors = []
			mayors_online = []
			claimed_area = 0
			total_area = 0
			for region in os.listdir(regions_path):
				try:
					region_path = regions_path / region
					region_config_path = region_path / "config.bmp"
					region_dimensions = get_bitmap_dimensions(region_config_path)
					region_database_path = region_path / "_Database" / "region.json"
					region_database = load_json(region_database_path)
					for coords in region_database.keys():
						city_entry = region_database[coords]
						if city_entry != None:
							owner = city_entry["owner"]
							locked = city_entry.get("locked", False)
							area = city_entry["size"] ** 2
							if locked:
								total_area -= area
							if owner != None:
								if not locked:
									claimed_area += area
								if owner not in mayors:
									mayors.append(owner)
								modified = city_entry["modified"]
								if modified != None:
									modified = datetime.strptime(modified, "%Y-%m-%d %H:%M:%S")
									if modified > server_time - timedelta(minutes=sc4mp_config["GENERAL"]["stat_mayors_online_cutoff"]) and owner not in mayors_online:
										mayors_online.append(owner)
					total_area += region_dimensions[0] * region_dimensions[1]
				except Exception as e:
					show_error(f"An error occurred while calculating region statistics for \"{region}\".", no_ui=True)

			self.stat_mayors = len(mayors) #(random.randint(0,1000))
			
			self.stat_mayors_online = len(mayors_online) #int(self.stat_mayors * (float(random.randint(0, 100)) / 100))
			
			try:
				self.stat_claimed = (float(claimed_area) / float(total_area)) #(float(random.randint(0, 100)) / 100)
			except ZeroDivisionError:
				self.stat_claimed = 1

			self.stat_download, self.stat_actual_download = download #(random.randint(0, 10 ** 11))

		ping = self.ping()
		if ping != None:
			self.stat_ping = ping

		sc4mp_servers_database[self.server_id]["stat_mayors"] = self.stat_mayors
		sc4mp_servers_database[self.server_id]["stat_mayors_online"] = self.stat_mayors_online
		sc4mp_servers_database[self.server_id]["stat_claimed"] = self.stat_claimed
		sc4mp_servers_database[self.server_id]["stat_download"] = self.stat_download
		sc4mp_servers_database[self.server_id]["stat_actual_download"] = self.stat_actual_download
		sc4mp_servers_database[self.server_id]["stat_ping"] = self.stat_ping


	def fetch_temp(self):
		

		REQUESTS = ["plugins", "regions"]
		DIRECTORIES = ["Plugins", "Regions"]

		total_size = 0
		download_size = 0

		cache_files = os.listdir(os.path.join(SC4MP_LAUNCHPATH, "_Cache"))

		for request, directory in zip(REQUESTS, DIRECTORIES):

			# Set destination
			destination = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server_id / directory

			# Create the socket
			s = socket.socket()
			s.settimeout(30)
			s.connect((self.host, self.port))

			# Request the type of data
			if not self.private:
				s.send(request.encode())
			else:
				s.send(f"{request} {SC4MP_VERSION} {self.user_id} {self.password}".encode())

			# Receive file table
			file_table = recv_json(s)

			# Get total and download size
			#size = sum([entry[1] for entry in file_table])
			for entry in file_table:
				total_size += entry[1]
				if not entry[0] in cache_files:
					download_size += entry[1]

			#size = sum([(0 if os.path.exists(os.path.join(SC4MP_LAUNCHPATH, "_Cache", entry[0])) else entry[1]) for entry in file_table])

			# Prune file table as necessary
			ft = []
			for entry in file_table:
				filename = Path(entry[2]).name
				if filename in ["region.json", "config.bmp"]:
					ft.append(entry)
			file_table = ft

			# Send pruned file table
			send_json(s, file_table)

			# Receive files
			for entry in file_table:

				# Get necessary values from entry
				filesize = entry[1]
				relpath = Path(entry[2])

				# Set the destination
				d = sanitize_relpath(Path(destination), relpath)

				# Create the destination directory if necessary
				d.parent.mkdir(parents=True, exist_ok=True)

				# Delete the destination file if it exists
				d.unlink(missing_ok=True)

				# Receive the file
				filesize_read = 0
				with d.open("wb") as dest:
					while filesize_read < filesize:
						filesize_remaining = filesize - filesize_read
						buffersize = SC4MP_BUFFER_SIZE if filesize_remaining > SC4MP_BUFFER_SIZE else filesize_remaining
						bytes_read = s.recv(buffersize)
						if not bytes_read:
							break
						dest.write(bytes_read)
						filesize_read += len(bytes_read)

			#total_size += size

			# Request the type of data
			#if not self.private:
			#	s.sendall(request.encode())
			#else:
			#	s.sendall(f"{request} {SC4MP_VERSION} {self.user_id} {self.password}".encode())

			# Receive file count
			#file_count = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Separator
			#s.sendall(SC4MP_SEPARATOR)

			# Receive file size
			#size = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Receive files
			#for files_received in range(file_count):
			#	s.sendall(SC4MP_SEPARATOR)
			#	size_downloaded += self.receive_or_cached(s, destination)

		return (total_size, download_size)


	def update_database(self):
		"""Updates the json entry for the server."""

		# Get database entry for server
		key = self.server_id
		entry = sc4mp_servers_database.get(key, dict())
		sc4mp_servers_database[key] = entry

		# Set server categories
		if "user_id" in entry.keys():
			self.categories.append("History")
		if entry.get("bookmarked", False):
			self.categories.append("Bookmarked")

		# Set values in database entry
		set_server_data(entry, self)


	def request(self, request):
		"""Requests a given value from the server."""

		if self.fetched == False:
			return

		host = self.host
		port = self.port

		try:
			s = socket.socket()
			s.settimeout(10)
			s.connect((host, port))
			s.sendall(request.encode())
			return s.recv(SC4MP_BUFFER_SIZE).decode()
		except Exception:
			self.fetched = False
			print(f'[WARNING] Unable to fetch "{request}" from {host}:{port}')
			return None


	def authenticate(self):
		

		# Get database entry for server
		key = self.server_id
		entry = sc4mp_servers_database.get(key, dict())
		sc4mp_servers_database[key] = entry

		# Get user_id
		user_id = None
		try:
			user_id = entry["user_id"]
		except Exception:
			user_id = random_string(32)

		# Get token
		token = None
		try:
			token = entry["token"]
		except Exception:
			pass

		# Verify server can produce the user_id from the hash of the user_id and token combined
		if token != None:
			hash = hashlib.sha256(((hashlib.sha256(user_id.encode()).hexdigest()[:32]) + token).encode()).hexdigest()
			s = socket.socket()
			s.settimeout(10)
			s.connect((self.host, self.port))
			s.sendall(f"user_id {hash}".encode())
			if s.recv(SC4MP_BUFFER_SIZE).decode() == hashlib.sha256(user_id.encode()).hexdigest()[:32]:
				self.user_id = user_id
			else:
				if not sc4mp_config["GENERAL"]["ignore_token_errors"]:
					if sc4mp_ui:
						if messagebox.askokcancel(title=SC4MP_TITLE, message="The server failed to authenticate.\n\nThe user ID corresponding to your last login could not be produced by the server. A recent rollback of the server, or a recent failed authentication attempt may be to blame.\n\nIf you proceed, your user ID may become compromised.", icon="warning"):
							self.user_id = user_id
						else:
							raise ClientException("Connection cancelled.")
					else:
						raise ClientException("Invalid token.") #"Authentication error."
			s.close()
		else:
			self.user_id = user_id

		# Get the new token
		s = socket.socket()
		s.settimeout(10)
		s.connect((self.host, self.port))
		s.sendall(f"token {SC4MP_VERSION} {self.user_id} {self.password}".encode())
		token = s.recv(SC4MP_BUFFER_SIZE).decode()

		# Raise exception if no token is received
		if len(token) < 1:
			raise ClientException("Authentication failed.\n\nThe reason could be any of the following:\n(1)   You are banned from this server.\n(2)   You have too many different user accounts on this server.\n(3)   There is a problem with your internet connection.")

		# Set user_id and token in the database entry
		entry["user_id"] = user_id
		entry["token"] = token
		entry.setdefault("first_logon", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		entry["last_logon"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


	def ping(self):

		host = self.host
		port = self.port

		s = socket.socket()
		
		s.settimeout(10)

		try:
			s.connect((host, port))
			start = time.time()
			s.sendall(b"ping")
			s.recv(SC4MP_BUFFER_SIZE)
			end = time.time()
			s.close()
			self.server_ping = round(1000 * (end - start))
			return self.server_ping
		except socket.error:
			return None


	def time(self):
		

		try:

			s = socket.socket()
			s.settimeout(10)
			s.connect((self.host, self.port))
			s.sendall(b"time")

			return datetime.strptime(s.recv(SC4MP_BUFFER_SIZE).decode(), "%Y-%m-%d %H:%M:%S")
		
		except Exception as e:

			show_error("Unable to get server time, using local time instead.", no_ui=True)

			return datetime.now()


# Workers

class ServerList(th.Thread):
	


	def __init__(self, ui, kill=None):
		

		th.Thread.__init__(self)

		self.ui: ServerListUI = ui

		if self.ui is not None and kill is None:
			self.ui.label["text"] = 'Getting server list...'

		self.setDaemon(True)

		self.end = False
		self.ended = False
		self.pause = False

		self.servers: dict[str:Server] = {}

		self.unfetched_servers: list[tuple] = SC4MP_SERVERS.copy()

		self.saved_servers: dict[tuple:str] = {}

		self.fetched_servers: list[tuple] = []
		self.tried_servers: list[tuple] = []
		self.hidden_servers: list[tuple] = []

		self.offline_server_count = 0

		self.server_fetchers = 0

		self.stat_mayors = dict()
		self.stat_mayors_online = dict()
		self.stat_claimed = dict()
		self.stat_actual_download = dict()
		self.stat_ping = dict()

		if self.ui:

			self.blank_icon = tk.PhotoImage(file=get_sc4mp_path("blank-icon.png"))
			self.lock_icon = tk.PhotoImage(file=get_sc4mp_path("lock-icon.png"))
			self.official_icon = tk.PhotoImage(file=get_sc4mp_path("official-icon.png"))
			self.error_icon = tk.PhotoImage(file=get_sc4mp_path("error-icon.png"))

			self.rank_bars = {}
			self.rank_bar_images = [tk.PhotoImage(file=get_sc4mp_path(f"rank-{i}.png")) for i in range(6)]
			self.ui.tree.bind("<<TreeviewSelect>>", self.update_rank_bars)

		self.temp_path = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList"

		self.kill = kill

		self.sort_mode_changed = False


	def run(self):
		

		try:

			set_thread_name("SLThread", enumerate=False)

			self.lan_servers = []
			if sc4mp_config["GENERAL"]["scan_lan"]:
				try:
					self.lan_servers = [(row[0], port) for port in range(7240, 7250) for row in [("localhost", None, None)] + arp()]
				except Exception as e:
					show_error("An error occurred while scanning for LAN servers, only internet servers will be shown.", no_ui=True)

			delete_server_ids = []
			for server_id in reversed(sc4mp_servers_database.keys()):
				server_entry = sc4mp_servers_database[server_id]
				if (server_entry.get("user_id", None) != None) or ("last_contact" not in server_entry.keys()) or (datetime.strptime(server_entry["last_contact"], "%Y-%m-%d %H:%M:%S") + timedelta(days=30) > datetime.now()):
					host = server_entry["host"]
					port = server_entry["port"]
					self.unfetched_servers.append((host, port))
					if sc4mp_config["GENERAL"]["show_offline_servers"]:
						self.saved_servers.setdefault((host, port), server_id)
				else:
					delete_server_ids.append(server_id)
			for delete_server_id in delete_server_ids:
				sc4mp_servers_database.data.pop(delete_server_id)

			if self.kill != None:
				self.kill.end = True
				while not self.kill.ended:
					time.sleep(SC4MP_DELAY)
				self.clear_tree()

			#try: #TODO is this needed?
			#	purge_directory(self.temp_path)
			#except Exception as e:
			#	show_error("Error deleting temporary server list files.", no_ui=True)

			print("Fetching servers...")

			while self.end == False:

				if self.pause == False:

					# Enable or disable buttons and update labels
					server_id = self.ui.tree.focus()
					if server_id == "" or server_id not in self.servers.keys():
						self.ui.connect_button['state'] = tk.DISABLED
						self.ui.details_button['state'] = tk.DISABLED
						self.ui.address_label["text"] = ""
						self.ui.description_label["text"] = ""
						self.ui.url_label["text"] = ""
					else:
						self.ui.connect_button['state'] = tk.NORMAL
						if "Offline" in self.servers[server_id].categories:
							self.ui.address_label["text"] = "Offline"
							self.ui.address_label["fg"] = "red"
							self.ui.details_button['state'] = tk.DISABLED
						else:
							self.ui.address_label["text"] = self.servers[server_id].host + ":" + str(self.servers[server_id].port)
							self.ui.address_label["fg"] = "gray"
							self.ui.details_button['state'] = tk.NORMAL
						self.ui.description_label["text"] = self.servers[server_id].server_description
						self.ui.url_label["text"] = self.servers[server_id].server_url
						
					# Add all fetched servers to the server dictionary if not already present
					while len(self.fetched_servers) > 0:
						fetched_server = self.fetched_servers.pop(0)
						if fetched_server.server_id not in self.servers.keys() or not self.servers[fetched_server.server_id].fetched:
							self.servers[fetched_server.server_id] = fetched_server

					# Fetch the next unfetched server
					for unfetched_servers in [self.unfetched_servers, self.lan_servers]:
						if self.server_fetchers < 25: #100 #TODO make configurable?
							if len(unfetched_servers) > 0:
								unfetched_server = unfetched_servers.pop(0)
								if unfetched_server not in self.tried_servers:
									self.tried_servers.append(unfetched_server)
									self.server_fetchers += 1
									ServerFetcher(self, Server(unfetched_server[0], unfetched_server[1])).start()

					# Clear the tree if sort mode changed
					if self.sort_mode_changed:
						self.sort_mode_changed = False
						self.clear_tree()

					# Update stats
					server_ids = self.servers.keys()
					for server_id in server_ids:
						try:
							update_server = self.servers[server_id]
							self.stat_mayors[server_id] = update_server.stat_mayors
							self.stat_mayors_online[server_id] = update_server.stat_mayors_online
							self.stat_actual_download[server_id] = update_server.stat_actual_download
							self.stat_claimed[server_id] = update_server.stat_claimed
							self.stat_ping[server_id] = update_server.stat_ping
							self.calculate_rating(update_server)
						except Exception: #Exception as e:
							#show_error(e)
							try:
								self.stat_ping[server_id] = update_server.stat_ping
								self.calculate_rating(update_server)
							except Exception:
								pass

					# Add missing rows to the tree
					server_ids = self.servers.keys()
					filter = self.ui.combo_box.get()
					if filter == self.ui.combo_box.PLACEHOLDER_TEXT:
						filter = ""
					for server_id in server_ids:
						if (not self.ui.tree.exists(server_id)) and (not self.filter(self.servers[server_id], self.filters(filter))): #(len(filter) < 1 or (not self.filter(self.servers[server_id], self.filters(filter)))):
							#while len(self.ui.tree.get_children()) >= 50:
							#	self.ui.tree.delete(self.ui.tree.get_children()[-1])
							server = self.servers[server_id]
							tags = []
							if "Offline" in server.categories:
								image = self.error_icon
								tags.append("red")
							elif server.password_enabled:
								image = self.lock_icon
							elif "Official" in server.categories:
								image = self.official_icon
							else:
								image = self.blank_icon
							values = self.format_server(server)
							self.ui.tree.insert("", self.in_order_index(server), server_id, text=server.server_name, values=values, image=image, tags=tuple(tags))					

					# Filter the tree
					filter = self.ui.combo_box.get()
					if filter == self.ui.combo_box.PLACEHOLDER_TEXT:
						filter = ""
					#if len(filter) > 0:
					try:
						category, search_terms = self.filters(filter)
						#print("Filtering by \"" + category + "\" and " + str(search_terms) + "...")
						if category == "History":
							self.ui.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#6")
							#self.ui.tree.column("#5", width=0)
							#self.ui.tree.column("#6", width=93)
							if self.ui.tree.sort == "Rank":
								self.ui.tree.sort = "Joined"
								self.clear_tree()
						else:
							self.ui.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#5")
							#self.ui.tree.column("#5", width=93)
							#self.ui.tree.column("#6", width=0)
							if self.ui.tree.sort == "Joined":
								self.ui.tree.sort = "Rank"
								self.clear_tree()
						server_ids = self.ui.tree.get_children()
						for server_id in server_ids:
							hide = self.filter(self.servers[server_id], (category, search_terms))
							if hide and (server_id in self.ui.tree.get_children()) and (server_id not in self.hidden_servers):
								self.hidden_servers.append(server_id)
								self.ui.tree.delete(server_id)
							elif (not hide) and (server_id in self.hidden_servers):
								self.hidden_servers.remove(server_id)
								#self.ui.tree.reattach(server_id, self.ui.tree.parent(server_id), self.in_order_index(self.servers[server_id]))
					except Exception as e:
						show_error("An error occurred while filtering the server list.", no_ui=True)
					#elif len(self.hidden_servers) > 0:
					#	server_ids = self.hidden_servers
					#	for server_id in server_ids:
					#		self.hidden_servers.remove(server_id)
					#		#self.ui.tree.reattach(server_id, self.ui.tree.parent(server_id), self.in_order_index(self.servers[server_id]))

					# Sort the tree
					if not self.sorted():
						#print("Sorting...")
						server_ids = self.ui.tree.get_children()
						for index in range(len(server_ids) - 1):
							server_a_id = server_ids[index]
							server_b_id = server_ids[index + 1]
							server_a = self.servers[server_a_id]
							server_b = self.servers[server_b_id]
							if not self.in_order(server_a, server_b):
								self.ui.tree.move(server_b_id, self.ui.tree.parent(server_b_id), index)
						"""server_indices = dict()
						for server_id in server_ids:
							server_indices[server_id] = server_ids.index(server_id)
						self.sort(server_indices)
						for server_id in server_ids:
							if (not server_id in self.hidden_servers):
								self.ui.tree.move(server_id, self.ui.tree.parent(server_id), server_indices[server_id])"""

					# Update the tree
					server_ids = self.ui.tree.get_children()
					for server_id in server_ids:
						server = self.servers[server_id]
						self.ui.tree.item(server_id, values=self.format_server(server))

					# Update primary label
					if len(self.servers) > self.offline_server_count:
						#if len(self.hidden_servers) < len(self.servers):
						self.ui.label["text"] = 'To get started, select a server below and click "Connect"'
						#else:
						#	self.ui.label["text"] = 'No servers found'
					else:
						self.ui.address_label["text"] = ""
						self.ui.description_label["text"] = ""
						self.ui.url_label["text"] = ""
						if self.server_fetchers > 0:
							self.ui.label["text"] = 'Getting server list...'
						else:
							self.ui.label["text"] = 'No servers found' #Select "Servers" then "Connect..." in the menu bar to connect to a server.'

					# Update rank bars
					self.update_rank_bars()

				# Delay
				time.sleep(SC4MP_DELAY)

			for canvas in self.rank_bars.values():
				canvas.destroy()

			self.ended = True

		except Exception as e:

			try:
				self.ended = True
			except Exception:
				pass

			show_error(f"An error occurred while fetching servers.\n\n{e}") #, no_ui=True)


	def clear_tree(self):
		
		self.ui.tree.delete(*self.ui.tree.get_children())


	def filters(self, filter):
		
		if len(filter) > 0:
			search_terms = filter.split(" ")
			category = "All"
			if len(search_terms) > 0:
				if search_terms[0] == "category:":
					if len(search_terms) > 1:
						category = search_terms[1].lower().capitalize()
						for count in range(2):
							search_terms.pop(0)
					else:
						search_terms.pop(0)
			for index in range(len(search_terms)):
				if search_terms[index] == "":
					search_terms.pop(index)
			return category, search_terms
		else:
			return "All", []


	def filter(self, server: Server, filters: list[str]):
		
		category = filters[0]
		search_terms = filters[1]
		search_fields = [server.server_name, server.server_description, server.server_url, server.server_id, server.host]
		if len(search_terms) > 0:
			for search_field in search_fields:
				search_field = search_field.lower()
				for search_term in search_terms:
					search_term = search_term.lower()
					if search_term in search_field and category in server.categories:
						return False
		elif category in server.categories:
			return False
		return True


	def sorted(self):
		
		server_ids = self.ui.tree.get_children()
		if len(server_ids) < 2:
			return True
		else:
			for index in range(len(server_ids) - 1):
				server_a_id = server_ids[index]
				server_b_id = server_ids[index + 1]
				server_a = self.servers[server_a_id]
				server_b = self.servers[server_b_id]
				if not self.in_order(server_a, server_b):
					return False
			return True

	
	def sort(self, server_indices): #TODO doesnt work in one pass!
		"""deprecated"""
		server_ids = list(server_indices.keys())
		index_a = 0
		while index_a < len(server_ids):
			server_a_id = server_ids[index_a]
			server_a = self.servers[server_a_id]
			index_b = 0
			while index_b < index_a:
				server_b_id = server_ids[index_b]
				server_b = self.servers[server_b_id]
				if not self.in_order(server_b, server_a):
					break
				index_b += 1
			server_ids[index_a], server_ids[index_b] = server_ids[index_b], server_ids[index_a]
			index_a += 1
		for index in range(len(server_ids)):
			server_id = server_ids[index]
			server_indices[server_id] = index


	def in_order(self, server_a, server_b):
		
		server_a_sort_value = self.get_sort_value(server_a)
		server_b_sort_value = self.get_sort_value(server_b)
		if server_a_sort_value is None and server_b_sort_value is None:
			return True
		elif server_a_sort_value is None:
			return False
		elif server_b_sort_value is None:
			return True
		else:
			if not self.ui.tree.reverse_sort:
				return server_a_sort_value >= server_b_sort_value
			else:
				return server_a_sort_value <= server_b_sort_value
	

	def in_order_index(self, server):
		
		if self.get_sort_value(server):
			existing_server_ids = self.ui.tree.get_children()
			for index in range(len(existing_server_ids)):
				existing_server_id = existing_server_ids[index]
				existing_server = self.servers[existing_server_id]
				if self.in_order(server, existing_server):
					return index
		return "end"

	
	def get_sort_value(self, server):
		
		sort_mode = self.ui.tree.sort
		try:
			if sort_mode == "Name":
				return server.server_name
			elif sort_mode == "Mayors":
				return server.stat_mayors
			elif sort_mode == "Claimed":
				return server.stat_claimed
			elif sort_mode == "Download":
				return server.stat_actual_download if sc4mp_config["GENERAL"]["show_actual_download"] else server.stat_download
			elif sort_mode == "Ping":
				return server.stat_ping
			elif sort_mode == "Joined":
				return server.last_logon
			else:
				return server.rating
		except Exception:
			return None


	def format_server(self, server):
		
		functions = [
			lambda: str(server.stat_mayors) + " (" + str(server.stat_mayors_online) + ")" if server.stat_mayors_online > 0 else str(server.stat_mayors),
	    	lambda: str(int(server.stat_claimed * 100)) + "%",
		    lambda: format_download_size(server.stat_actual_download) if sc4mp_config["GENERAL"]["show_actual_download"] else format_filesize(server.stat_download),
		    lambda: str(server.stat_ping) + "ms",
		    lambda: str(round(server.rating, 1)), # (lambda: "" if sc4mp_config["GENERAL"]["show_rank_bars"] else lambda: str(round(server.rating, 1))), # + " ⭐️",
			lambda: self.format_server_join_time(server)
		]
		if sc4mp_config["GENERAL"]["show_rank_bars"]:
			functions[4] = lambda: ""
		cells = []
		for function in functions:
			try:
				cells.append(function())
			except Exception as e: #Exception as e:
				#show_error(e)
				cells.append("...") #cells.append("")
		return cells


	def format_server_join_time(self, server: Server):

		try:
			last_logon = server.last_logon
		except AttributeError:
			last_logon = sc4mp_servers_database.get(server.server_id, {}).get("last_logon", None)

		server.last_logon = last_logon

		if last_logon:
			last_logon = datetime.strptime(last_logon, "%Y-%m-%d %H:%M:%S")

		return format_time_ago(last_logon)

	
	def calculate_rating(self, server):
		
		try:

			try:
				categories = [
					.5 * (self.max_category(server.stat_mayors, self.stat_mayors.values())) * (self.max_category(server.stat_mayors_online, self.stat_mayors_online.values()) + 1),
					self.min_category(server.stat_claimed, self.stat_claimed.values()),
					self.min_category(server.stat_actual_download, self.stat_actual_download.values()),
					self.min_category(server.stat_ping, self.stat_ping.values()),
				]
				rating = 1 + sum(categories)
			except Exception:
				rating = 1 + self.min_category(server.stat_ping, self.stat_ping.values())
			
			try:
				server.rating = ((99 * server.rating) + rating) / 100
			except Exception:
				server.rating = rating

		except Exception:
			pass
	

	def max_category(self, item, array):
		
		item = float(item)
		try:
			return (item - min(array)) / (max(array) - min(array))
		except Exception:
			return 1.0


	def min_category(self, item, array):
		
		item = float(item)
		try:
			return 1.0 - ((item - min(array)) / (max(array) - min(array)))
		except Exception:
			return 1.0


	def update_rank_bars(self, event=None):

		RANK_COLUMN_ID = "#5"

		CUTOFF_Y = 260

		OFFSET_X = 18
		OFFSET_Y = 154

		IMAGE_W = 29
		IMAGE_H = 12

		CELL_W = 93
		CELL_H = 20

		# For passing clicks from the canvas to the underlying row in the tree
		def handle_click(event):

			# Get the `server_id` associated with the canvas
			canvas = event.widget
			server_id = canvas.server_id

			# Select the row which the canvas is placed on
			self.ui.tree.selection_set([server_id])
			self.ui.tree.focus(server_id)

			# Call the event handler for a single click in `ServerListUI`
			self.ui.handle_single_click(event)


		def scheduled_update():

			# Allow the function to be scheduled again
			self.ui.rank_bar_update_scheduled = False

			# Keep the old rank bars so they can be deleted after the new ones are created
			r = self.rank_bars

			# Reset the list for new rank bars
			self.rank_bars = {}

			# If "Rank" column is being displayed
			if RANK_COLUMN_ID in self.ui.tree["displaycolumns"]:

				# Loop through rows in the tree by their `server_id`
				for server_id in self.ui.tree.get_children():
					
					try:

						# Try to get the server rank, if it blows up (no stats, probably), use `0`
						try:
							rank = round(self.servers[server_id].rating)
						except Exception:
							rank = 0

						# Needed to choose canvas bgcolor
						selected = server_id in self.ui.tree.selection()

						# Get the bounding box of the cell in the "Rank" column
						x, y, w, h = self.ui.tree.bbox(server_id, column=RANK_COLUMN_ID)

						# If row is visible
						if y < CUTOFF_Y:

							# Unique identifier for the canvas
							key = (x, y, w, h, rank, selected)

							# If the canvas doesn't need to be updated, use the old one
							if key in r.keys():

								self.rank_bars[key] = r.pop(key)

							# Otherwise, create a new one
							else:

								canvas = tk.Canvas(
									width=IMAGE_W, 
									height=IMAGE_H, 
									bd=0,
									bg=("#0078D7" if selected else "white"), 
									highlightthickness=0, 
									relief='flat'
								)
								
								# For click passthrough to the underlying row
								canvas.server_id = server_id
								canvas.bind("<Button-1>", handle_click)
								
								# Create the rank bar image associated with the rank value
								canvas.image = self.rank_bar_images[rank]
								canvas.create_image(0, 0, anchor="nw", image=canvas.image)
								canvas.place(
									x = x + OFFSET_X + ((CELL_W - IMAGE_W) / 2),
									y = y + OFFSET_Y + ((CELL_H - IMAGE_H) / 2),
								)
								
								# Store the canvas so it can be deleted later, when needed
								self.rank_bars[key] = canvas

					# Can't remember why I put this here. I guess we don't care about `ValueErrors`
					except ValueError:
						pass

					# Quietly report all errors
					except Exception as e:
						show_error(e, no_ui=True)

			# Delete all old rank bars
			for canvas in r.values():
				canvas.destroy()

		# Running the function from this thread seems to cause CTDs with 0x0000005 access violations, so we use the `after` method instead
		if self.ui and sc4mp_config["GENERAL"]["show_rank_bars"]:
			if not hasattr(self.ui, "rank_bar_update_scheduled") or not self.ui.rank_bar_update_scheduled:
				self.ui.rank_bar_update_scheduled = True
				self.ui.after(0, scheduled_update)


class ServerFetcher(th.Thread):


	def __init__(self, parent: ServerList, server: Server):

		th.Thread.__init__(self)

		self.parent = parent
		self.server = server

		self.setDaemon(True)


	def run(self):
		
		try:

			try:

				set_thread_name("SfThread")

				print(f"Fetching {self.server.host}:{self.server.port}...")

				#print("- fetching server info...")

				try:

					self.server.fetch()

					if not self.server.fetched:
						raise ClientException("Server is not fetched.")

				except Exception as e:

					if (self.server.host, self.server.port) in self.parent.saved_servers.keys():

						self.server.server_id = self.parent.saved_servers.pop((self.server.host, self.server.port))

						server_entry: dict = sc4mp_servers_database[self.server.server_id]

						if "user_id" in server_entry.keys():

							self.server.categories = ["Offline", "History"] # "All"

							self.server.server_name = server_entry.get("server_name", f"{self.server.host}:{self.server.port}")
							self.server.server_description = server_entry.get("server_description", "")
							self.server.server_url = server_entry.get("server_url", "")

							self.parent.fetched_servers.append(self.server)

							self.parent.offline_server_count += 1

					raise ClientException("Server not found.") from e

				if self.parent.end:
					raise ClientException("The parent thread was signaled to end.")

				self.server.categories.append("Online")

				#print("- populating server statistics")

				if sc4mp_config["DEBUG"]["random_server_stats"]:

					self.server.stat_mayors = random.randint(0,1000)
					self.server.stat_mayors_online = int(self.server.stat_mayors * (float(random.randint(0, 100)) / 100))
					self.server.stat_claimed = float(random.randint(0, 100)) / 100
					self.server.stat_download = random.randint(0, 10 ** 11)
					self.server.stat_actual_download = int(self.server.stat_download * (float(random.randint(0, 100)) / 100))
					self.server.stat_ping = random.randint(0, 300)

				else:

					#if not self.server.private:
					try:
						self.server.stat_ping = sc4mp_servers_database[self.server.server_id]["stat_ping"]
						self.server.stat_mayors = sc4mp_servers_database[self.server.server_id]["stat_mayors"]
						self.server.stat_mayors_online = sc4mp_servers_database[self.server.server_id]["stat_mayors_online"]
						self.server.stat_claimed = sc4mp_servers_database[self.server.server_id]["stat_claimed"]
						self.server.stat_download = sc4mp_servers_database[self.server.server_id]["stat_download"]
						self.server.stat_actual_download = sc4mp_servers_database[self.server.server_id]["stat_actual_download"]
					except Exception:
						pass
					#else:
					#	try:
					#		self.server.stat_ping = sc4mp_servers_database[self.server.server_id]["stat_ping"]
					#	except Exception:
					#		pass

				#print("- adding server to server list...")

				try:
					self.parent.fetched_servers.append(self.server)
				except Exception as e:
					raise ClientException("Unable to add server to server list.") from e

				#print("- starting server pinger...")

				try:
					ServerPinger(self.parent, self.server).start()
				except Exception as e:
					raise ClientException("Unable to start server pinger.") from e

				#print("- fetching server list...")

				try:
					self.server_list()
				except Exception as e:
					raise ClientException("Unable to fetch server list.") from e

				#if not self.server.private:

					#print("- fetching server stats...")
					
				try:
					self.fetch_stats()
				except Exception as e:
					print(f"[WARNING] Unable to fetch server stats for {self.server.host}:{self.server.port}! " + str(e))

				#print("- done.")

			except Exception as e:

				print(f"[WARNING] Failed to fetch {self.server.host}:{self.server.port}! " + str(e))

			self.parent.server_fetchers -= 1

		except Exception as e:

			show_error(f"A server fetcher thread encountered an unexpected error.\n\n{e}")


	def fetch_stats(self):
		
		self.server.fetch_stats()
		
	
	def server_list(self):
		
		
		# Create socket
		s = self.create_socket(self.server)
		
		# Request server list
		s.sendall(b"server_list")
		
		# Receive server list
		servers = recv_json(s)

		# Loop through server list and append them to the unfetched servers
		for host, port in servers:
			self.parent.unfetched_servers.append((host, port))

		#s = self.create_socket(self.server)
		#s.sendall(b"server_list")
		#size = int(s.recv(SC4MP_BUFFER_SIZE).decode())
		#s.sendall(SC4MP_SEPARATOR)
		#for count in range(size):
		#	host = s.recv(SC4MP_BUFFER_SIZE).decode()
		#	s.sendall(SC4MP_SEPARATOR)
		#	port = int(s.recv(SC4MP_BUFFER_SIZE).decode())
		#	s.sendall(SC4MP_SEPARATOR)
		#	self.parent.unfetched_servers.append((host, port))


	def create_socket(self, server):
		
		host = server.host
		port = server.port
		try:
			s = socket.socket()
			s.settimeout(10)
			s.connect((host, port))
			return s
		except Exception:
			return None


class ServerPinger(th.Thread):


	def __init__(self, parent, server):

		th.Thread.__init__(self)

		self.parent = parent
		self.server = server

		self.setDaemon(True)


	def run(self):

		try:

			set_thread_name("SpThread")

			while not self.parent.end:
				time.sleep(len(self.parent.servers) + 1)
				if not self.parent.pause:
					#print(f"Pinging {self.server.host}:{self.server.port}")
					ping = self.server.ping()
					if ping != None:
						self.server.stat_ping = ping #int((self.server.stat_ping + ping) / 2)
						sc4mp_servers_database[self.server.server_id]["stat_ping"] = ping

		except Exception as e:

			show_error(f"A server pinger thread encountered an unexpected error\n\n{e}", no_ui=True)


class ServerLoader(th.Thread):
	

	
	def __init__(self, ui, server):
		

		th.Thread.__init__(self)

		self.ui = ui
		self.server: Server = server

		self.setDaemon(True)

		if sc4mp_ui != None:
			sc4mp_ui.withdraw()

	
	def run(self):
		

		try:

			set_thread_name("SldThread", enumerate=False)

			if self.ui != None:
				
				# Prompt the SC4 intallation directory while not found
				while get_sc4_path() is None:
					if not messagebox.askokcancel(SC4MP_TITLE, 'No SimCity 4 installation found. \n\nPlease provide the correct installation path.'):
						self.ui.destroy()
						if sc4mp_exit_after:
							sc4mp_ui.destroy()
						else:
							sc4mp_ui.deiconify()
						return
					path = filedialog.askdirectory(parent=self.ui)
					if len(path) > 0:
						sc4mp_config["SC4"]["game_path"] = path
						if sc4mp_config["SC4"]["use_steam_browser_protocol"] in [0, 1]:
							sc4mp_config["SC4"]["use_steam_browser_protocol"] = (1 if is_steam_sc4(Path(path)) else 0)
						sc4mp_config.update()
					else:
						self.ui.destroy()
						if sc4mp_exit_after:
							sc4mp_ui.destroy()
						else:
							sc4mp_ui.deiconify()
						return
					
				# Prompt to apply the 4gb patch if not yet applied
				if is_windows():
					try:
						import ctypes
						sc4_exe_path = get_sc4_path()
						if not os.path.exists(sc4_exe_path.parent / (sc4_exe_path.name + ".Backup")):
							choice = messagebox.askyesnocancel(SC4MP_TITLE, "It appears the 4GB patch has not been applied to SimCity 4.\n\nLoading certain plugins may cause SimCity 4 to crash if the patch has not been applied.\n\nWould you like to apply the patch now?", icon="warning")
							if choice is None:
								self.ui.destroy()
								if sc4mp_exit_after:
									sc4mp_ui.destroy()
								else:
									sc4mp_ui.deiconify()
								return
							elif choice is True:
								exit_code = ctypes.windll.shell32.ShellExecuteW(None, "runas", f"{get_sc4mp_path('4gb-patch.exe').absolute()}", f"\"{sc4_exe_path}\"", None, 1)
								if exit_code not in [0, 42]:
									raise ClientException(f"Patcher exited with code {exit_code}.")
					except Exception as e:
						show_error(f"An error occurred while applying the 4GB patch.\n\n{e}")
		
			host = self.server.host
			port = self.server.port

			try:

				loading_start = time.time()

				self.report("", f'Connecting to server at {host}:{port}...')
				self.fetch_server()
				
				self.report("", 'Authenticating...')
				self.authenticate()

				self.report("", "Synchronizing plugins...")
				self.load("plugins")

				self.report("", "Synchronizing regions...")
				self.load("regions")

				self.report("", "Preparing plugins...")
				self.prep_plugins()

				self.report("", "Preparing regions...")
				self.prep_regions()

				if sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
					self.report("", "Preparing config...")
					self.prep_config()

				self.report("", "Launching SC4...")

				loading_end = time.time()

				print(f"- {round(loading_end - loading_start)} seconds")

				global sc4mp_current_server
				sc4mp_current_server = self.server

			except tk.TclError as e:
				
				pass

			except Exception as e:

				# pylint: disable-next=no-member
				if (self.ui is not None) and (self.ui.winfo_exists() == 1) and not (type(e) is ClientException and e.message == "Connection cancelled."):
					show_error(f"An error occurred while connecting to the server.\n\n{e}")
				else:
					show_error(e, no_ui=True)

			if sc4mp_current_server:

				sc4mp_config["GENERAL"]["default_host"] = self.server.host
				sc4mp_config["GENERAL"]["default_port"] = self.server.port
				sc4mp_config.update()

				self.server.categories.append("History")

				game_monitor = GameMonitor(self.server)
				game_monitor.start()
				if self.ui and self.ui.background:
					if self.ui.background:
						self.ui.background.lift()
					self.ui.lift()
				try:
					if is_windows():
						while (not self.ui or self.ui.winfo_exists()) and not window_open("simcity 4.exe"):
							time.sleep(SC4MP_DELAY)	
				except Exception as e:
					show_error(e, no_ui=True)

				if sc4mp_config["SC4"]["fullscreen"]:
					time.sleep(10)

				if self.ui:
					self.ui.destroy()

				if game_monitor.ui and game_monitor.ui.state() != "withdrawn":
					game_monitor.ui.grab_set()

				return

			if sc4mp_ui:
				if sc4mp_exit_after:
					sc4mp_ui.destroy()
				else:
					sc4mp_ui.deiconify()
			if self.ui:
				self.ui.destroy()

		except Exception as e:

			show_error(f"An unexpected error occurred in the server loader thread.\n\n{e}")


	def report(self, prefix, text):
		
		if self.ui != None:
			self.ui.label['text'] = text
			self.ui.progress_bar.start(2)
			self.ui.progress_bar['mode'] = "indeterminate"
			self.ui.progress_bar['maximum'] = 100
			self.ui.progress_label["text"] = ""
			self.ui.duration_label["text"] = ""
		print(prefix + text)
		#time.sleep(1) # for testing


	def report_progress(self, text, value, maximum):
		
		if self.ui != None:
			self.ui.label['text'] = text
			self.ui.progress_bar.stop()
			self.ui.progress_bar['mode'] = "determinate"
			self.ui.progress_bar['value'] = value
			self.ui.progress_bar['maximum'] = maximum
		print(text)


	def fetch_server(self):
		
		if self.server.fetched == False:
			self.server.fetch()
			if self.server.fetched == False:
				raise ClientException("Unable to find server. Check the IP address and port, then try again.")
		if not sc4mp_config["DEBUG"]["ignore_incompatable_versions"]:
			if unformat_version(self.server.server_version)[:2] < unformat_version(SC4MP_VERSION)[:2]:
				if sc4mp_beta is False:
					raise ClientException(f"The server requires an outdated version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please contact the server administrators.")
			if unformat_version(self.server.server_version)[:2] > unformat_version(SC4MP_VERSION)[:2]:
				raise ClientException(f"The server requires a newer version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please update the launcher to connect to this server.")
		if self.ui != None:
			self.ui.title(self.server.server_name)


	def authenticate(self):
		
		while True:
			try:
				tries = 0
				while not self.check_password():
					if sc4mp_ui:
						if tries >= 5:
							raise ClientException("Too many password attempts.")
						if tries > 0:
							print("[WARNING] Incorrect password.")
						PasswordDialogUI(self, tries)
						tries += 1
					else:
						raise ClientException("Incorrect password.")
				if self.server.password != "":
					self.server.authenticate()
				break
			except (socket.error, socket.timeout) as e:
				self.connection_failed_retrying(e)
		

	def check_password(self):
		
		if self.server.password_enabled:
			if self.server.password is None:
				if sc4mp_config["GENERAL"]["save_server_passwords"]:
					try:
						self.server.password = sc4mp_servers_database[self.server.server_id]["password"]
					except Exception:
						return False
			if self.server.password == "":
				return True
			s = self.create_socket()
			if self.ui is not None:
				self.ui.label['text'] = "Authenticating..."
			s.sendall(f"check_password {self.server.password}".encode())
			if s.recv(SC4MP_BUFFER_SIZE) == b'y':
				if sc4mp_config["GENERAL"]["save_server_passwords"]:
					try:
						sc4mp_servers_database[self.server.server_id]["password"] = self.server.password
					except Exception as e:
						show_error(e, no_ui=True)
				return True
			else:
				return False
		else:
			return True


	def load(self, target: str) -> None:
		

		# Select the destination directory according to the parameter
		destination = None
		if target == "plugins":
			destination = Path(SC4MP_LAUNCHPATH) / "Plugins" / "server"
		elif target == "regions":
			destination = Path(SC4MP_LAUNCHPATH) / "Regions"

		# Create destination if necessary
		if not destination.exists():
			destination.mkdir(parents=True, exist_ok=True)

		# Load or clear custom plugins (the code is organized like hell here, but it works)
		if target == "plugins":

			# For keeping track of DLL plugins
			self.dll_plugin_paths = []

			# Set source and destination for custom plugins
			client_plugins_source = Path(sc4mp_config["GENERAL"]["custom_plugins_path"])
			client_plugins_destination = Path(SC4MP_LAUNCHPATH) / "Plugins" / "client"

			# Synchronize custom plugins if the server permits custom plugins and the user wants to load them
			if self.server.user_plugins_enabled and sc4mp_config["GENERAL"]["custom_plugins"]:
				
				# Report for the loading sequence
				self.report("", "Synchronizing custom plugins...")
				#self.ui.duration_label["text"] = "(verifying)" # doesn't work :(

				# Get the paths to all files in the destination directory
				destination_relpaths = get_fullpaths_recursively(client_plugins_destination)

				# Delete all files in the destination directory that are not present in the source directory
				for relpath in destination_relpaths:
					if not Path(client_plugins_source, relpath).exists():
						filename = Path(client_plugins_destination) / relpath
						print(f'- removing "{filename}"')
						filename.unlink()

				# Get the paths to all files in the source directory
				source_relpaths = get_relpaths_recursively(client_plugins_source)

				# Get the size of the source directory
				source_size = directory_size(client_plugins_source)

				# These variables will be used to calculate the percentage for the progress bar
				destination_size = 0
				percent = -1

				# True if symlinks are allowed
				linking = False

				# Loop through the file paths in the source directory, and copy them to the destination if necessary
				for relpath in source_relpaths:

					# Progress bar stuff
					old_percent = percent
					percent = math.floor(100 * (destination_size / source_size))
					if percent > old_percent:
						self.report_progress(f'Synchronizing custom plugins... ({percent}%)', percent, 100)
					try:
						self.ui.progress_label["text"] = relpath.name
						if linking:
							self.ui.duration_label["text"] = "Link 🡒 SC4" #"(linking)"
						else:
							self.ui.duration_label["text"] = "Disk 🡒 SC4" #"(copying)"
					except Exception:
						pass

					# Set the source and destination paths for the file
					src = client_plugins_source / relpath
					dest = client_plugins_destination / relpath

					# For DLL plugins
					if relpath.suffix == ".dll":
						self.dll_plugin_paths.append((dest, "client"))

					# More progress bar stuff
					destination_size += src.stat().st_size

					# If the destination file exists, check the md5's to see if they match
					if dest.exists():

						# If the destination file is a link, or the md5's match, continue to the next iteration of the loop
						if os.path.islink(dest) or md5(src) == md5(dest):
							#print(f'- verified "{dest}"')
							continue
						
						# If the md5's don't match, delete the destination file
						else:
							print(f'- removing "{dest}"')
							dest.unlink()

					# Make the destination directory if necessary, then try to make a symbolic link (fast), and if the required priveleges are not held, copy the file (slower)
					dest.parent.mkdir(parents=True, exist_ok=True)
					try:
						os.symlink(src, dest)
						print(f'- linked "{src}"')
						linking = True
					except OSError:
						print(f'- copying "{src}"')
						shutil.copy(src, dest)
						linking = False
			
			# Clear custom plugins
			else:
				try:
					self.report("", "Clearing custom plugins...")
					purge_directory(client_plugins_destination)
				except Exception as e:
					show_error(f"Unable to delete \"{e}\"!", no_ui=True)


		# For keeping track of number of times the download is attempter
		tries = 0

		# Loop broken when the loading is successful, an unexpected error occurs, or the amount of tries is exceeded
		while True:

			try:

				# Purge the destination directory
				self.report("", f"Synchronizing {target}...") #"", "Purging " + type + " directory...")
				try:
					purge_directory(destination)
				except ClientException as e: 											# This is stupid
					raise ClientException("SimCity 4 is already running!") from e		# #TODO better to check if the process is actually running

				# Create the socket
				s = self.create_socket()
				#s.settimeout(None)

				# Report
				self.report("", f"Synchronizing {target}...")

				# Request the type of data
				if not self.server.private:
					s.sendall(target.encode())
				else:
					s.sendall(f"{target} {SC4MP_VERSION} {self.server.user_id} {self.server.password}".encode())

				# Receive file table
				file_table = recv_json(s)

				# Get total download size
				size = sum([entry[1] for entry in file_table])

				# Total size downloaded
				size_downloaded = 0

				# Download percent
				percent = 0

				# Set loading bar at 0%
				self.report_progress(f"Synchronizing {target}... (0%)", 0, 100)

				# Prune file table as necessary
				ft = []
				for entry in file_table:

					# Get necessary values from entry
					checksum = sanitize_directory_name(entry[0])
					filesize = entry[1]
					relpath = Path(entry[2])

					# Handle risky file types
					if not sc4mp_config["GENERAL"]["ignore_risky_file_warnings"]:
						if sc4mp_ui:
							if (relpath.suffix.lower() in SC4MP_RISKY_FILE_EXTENSIONS) and (sc4mp_servers_database[self.server.server_id].get("allowed_files", {}).get(checksum, "") != relpath.name.lower()):
								choice = messagebox.askyesnocancel(title=SC4MP_TITLE, message=f"You are about to download \"{relpath.name}\". This file could potentially harm your computer.\n\nWould you like to download it anyway?", icon="warning")
								if choice is True:
									sc4mp_servers_database[self.server.server_id].setdefault("allowed_files", {})
									sc4mp_servers_database[self.server.server_id]["allowed_files"][checksum] = relpath.name.lower()
								elif choice is False:
									size_downloaded += filesize
									continue
								else:
									raise ClientException("Connection cancelled.")
						else:
							print(f"[WARNING] Downloading risky file: \"{relpath.name}\"")

					# For DLL plugins
					if relpath.suffix == ".dll":
						self.dll_plugin_paths.append((Path(destination) / relpath, "server"))

					# Get path of cached file
					t = Path(SC4MP_LAUNCHPATH) / "_Cache" / checksum

					# Use the cached file if it exists and has the same size, otherwise append the entry to the new file table
					if t.exists() and t.stat().st_size == filesize:
						
						# Report
						print(f'- using cached "{checksum}"')

						# Set the destination
						d = sanitize_relpath(Path(destination), relpath)

						# Display current file in UI
						try:
							self.ui.progress_label["text"] = d.name #.relative_to(destination)
							self.ui.duration_label["text"] = "Cache 🡒 SC4" #"(cached)"
						except Exception:
							pass

						# Create the destination directory if necessary
						d.parent.mkdir(parents=True, exist_ok=True)

						# Delete the destination file if it exists
						d.unlink(missing_ok=True)

						# Copy the cached file to the destination
						shutil.copy(t, d)

						# Update progress bar
						size_downloaded += filesize
						old_percent = percent
						percent = math.floor(100 * (size_downloaded / (size + 1)))
						if percent > old_percent:
							self.report_progress(f"Synchronizing {target}... ({percent}%)", percent, 100)


					else:

						# Append to new file table
						ft.append(entry)
					
				file_table = ft

				if sc4mp_ui:
					self.ui.duration_label["text"] = "Server 🡒 SC4" #"(downloading)"

				download_start_time = time.time() + 2

				total_size_to_download = sum([entry[1] for entry in file_table])
				total_size_already_downloaded = 0.0

				old_eta = None
				old_eta_display_time = download_start_time + 2

				# Send pruned file table
				send_json(s, file_table)

				# Receive files
				for entry in file_table:

					# Get necessary values from entry
					checksum = sanitize_directory_name(entry[0])
					filesize = entry[1]
					relpath = Path(entry[2])

					# Report
					print(f'- caching "{checksum}"...')

					# Set the destination
					d = sanitize_relpath(Path(destination), relpath)

					# Display current file in UI
					try:
						self.ui.progress_label["text"] = d.name #.relative_to(destination)
					except Exception:
						pass

					# Set path of cached file
					t = Path(SC4MP_LAUNCHPATH) / "_Cache" / checksum

					# Create the destination directory if necessary
					d.parent.mkdir(parents=True, exist_ok=True)

					# Delete the destination file if it exists
					d.unlink(missing_ok=True)

					# Delete the cache file if it exists
					t.unlink(missing_ok=True)

					# Delete cache files if cache too large to accomadate the new cache file
					cache_directory = Path(SC4MP_LAUNCHPATH) / "_Cache"
					while any(cache_directory.iterdir()) and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize:
						random_cache = random.choice(list(cache_directory.iterdir()))
						random_cache.unlink()

					# Receive the file. Write to both the destination and cache
					filesize_read = 0
					with d.open("wb") as dest, t.open("wb") as cache:
						while filesize_read < filesize:
							filesize_remaining = filesize - filesize_read
							buffersize = SC4MP_BUFFER_SIZE if filesize_remaining > SC4MP_BUFFER_SIZE else filesize_remaining
							bytes_read = s.recv(buffersize)
							if not bytes_read:
								break
							for file in [dest, cache]:
								file.write(bytes_read)
							filesize_read += len(bytes_read)
							total_size_already_downloaded += len(bytes_read)
							size_downloaded += len(bytes_read)
							old_percent = percent
							percent = math.floor(100 * (size_downloaded / (size + 1)))
							if percent > old_percent:
								self.report_progress(f"Synchronizing {target}... ({percent}%)", percent, 100)
							if sc4mp_ui is not None:
								try:
									now = time.time()
									eta = int((total_size_to_download - total_size_already_downloaded) / (total_size_already_downloaded / float(now - download_start_time)))
									if (eta < 86400) and (old_eta is None or (old_eta > eta or int(now - old_eta_display_time) > 5)) and float(now - old_eta_display_time) >= .8:
										old_eta = eta
										old_eta_display_time = now
										hours = math.floor(eta / 3600)
										eta -= hours * 3600
										minutes = math.floor(eta / 60)
										eta -= minutes * 60
										seconds = eta
										if hours > 0:
											self.ui.duration_label["text"] = f"{hours}:{minutes:0>{2}}:{seconds:0>{2}}"
										else:
											self.ui.duration_label["text"] = f"{minutes}:{seconds:0>{2}}"
								except ZeroDivisionError as e:
									show_error(e, no_ui=True) # Lazy solution

				self.report_progress(f"Synchronizing {target}... (100%)", 100, 100)

				break

			except (socket.error, socket.timeout) as e:

				#tries += 1

				#if tries < 5:

				self.connection_failed_retrying(e)

				#else:

					#raise ClientException("Maximum connection attemps exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))


	def create_socket(self):
		

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		#tries_left = 5

		#while True:

		#	try:

		self.report("", "Connecting...")
		s.connect((host, port))

		self.report("", "Connected.")

		#		break

		#	except socket.error as e:
				
		#		if tries_left > 0:
				
		#			self.connection_failed_retrying(e)

		#			tries_left -= 1

		#		else:

		#			raise ClientException("Maximum connection attempts exceeded. Check your internet connection and firewall settings, then try again.") from e

		return s


	def receive_file(self, s: socket.socket, filename: Path) -> None:
		"""TODO: unused function?"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print("Receiving " + str(filesize) + " bytes...")
		print('writing to "' + filename + '"')

		filename.unlink(missing_ok=True)

		filesize_read = 0
		with filename.open("wb") as f:
			while filesize_read < filesize:
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				self.report_progress(f'Downloading "{filename}" ({filesize_read} / {filesize} bytes)...', int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def prep_plugins(self):

		# Get checksums of plugins installed to the top-level of the program files plugins folder (to avoid dobule-loading DLLs)
		toplevel_plugins_checksums = []
		try:
			installation_plugins_path = get_sc4_path().parent.parent / "Plugins"
			for file_name in os.listdir(installation_plugins_path):
				file_path = installation_plugins_path / file_name
				if file_path.is_file():
					toplevel_plugins_checksums.append(md5(file_path))
		except Exception as e: 
			show_error(e, no_ui=True)

		# Set source and destination for default plugins
		default_plugins_source = Path("resources")
		default_plugins_destination = Path(SC4MP_LAUNCHPATH) / "Plugins" #/ "default"

		# Clear default plugins directory
		try:
			purge_directory(default_plugins_destination, recursive=False)
		except Exception as e:
			raise ClientException("SimCity 4 is already running!") from e

		resw = sc4mp_config['SC4']['resw']
		resh = sc4mp_config['SC4']['resh']
		if 0 in (resw, resh) and sc4mp_ui:
			resw = sc4mp_ui.winfo_screenwidth()
			resh = sc4mp_ui.winfo_screenheight()

		# Load default plugins
		for default_plugin_file_name in [
			"sc4-fix.dll", 
			"sc4-fix-license.txt", 
			"sc4-thumbnail-fix.dll", 
			"sc4-thumbnail-fix-license.txt", 
			"sc4-thumbnail-fix-third-party-notices.txt",
			f"sc4mp-intro-{resw}-{resh}.dat",
			"sc4mp-local.dat",
			"sc4mp-ui.dat",
		]:
			try:
				default_plugin_file_path = default_plugins_source / default_plugin_file_name
				default_plugin_checksum = md5(default_plugin_file_path)
				if not default_plugin_checksum in toplevel_plugins_checksums:
					shutil.copy(default_plugin_file_path, default_plugins_destination / f"default-{default_plugin_file_name}")
					toplevel_plugins_checksums.append(default_plugin_checksum)
			except Exception as e:
				show_error(f"Failed to load default plugin \"{default_plugin_file_name}\".\n\n{e}", no_ui=True)

		# Copy DLLs from subfolders (DLL plugins do not load in subfolders)
		for path, basename in self.dll_plugin_paths:
			checksum = md5(path)
			if not checksum in toplevel_plugins_checksums:
				shutil.copy(path, default_plugins_destination / f"{basename}-{checksum}.dll")
				toplevel_plugins_checksums.append(checksum)

		# Write server URL local plugin file
		# with open(get_sc4mp_path("sc4mp-local-server-url.dat"), "rb") as rfile:
		# 	data = rfile.read().replace(b"{\x00{\x00U\x00R\x00L\x00}\x00}", bytes(self.server.server_url, encoding="utf-8"))
		# 	with open(default_plugins_destination / "server-url.dat", "wb") as wfile:
		# 		wfile.write(data)


	def prep_regions(self):
		

		# Declare instance variable to store the paths of the server region subdirectories
		self.server.regions: list[Path] = []

		# Path to regions directory
		regions_directory = Path(SC4MP_LAUNCHPATH) / "Regions"

		# Loop through the server regions, add them to the server regions instance variable and add prefixes to the region names in the region config files
		for child in regions_directory.iterdir():
			if child.is_dir():
				self.server.regions.append(child)
				config_path = regions_directory / child / "region.ini"
				prep_region_config(config_path)

		# Create `Downloads` directory in the `Regions` folder
		downloads_path = regions_directory / "Downloads"
		downloads_path.mkdir(exist_ok=True, parents=True)

		# Copy the latest failed save push into the `Downloads` directory
		try:
			
			# Pick the salvage subdirectory corresponding to the current server
			salvage_directory = Path(SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id

			# Pick the directory corresponding to the latest failed save push
			save_directory = os.path.join(salvage_directory, os.listdir(salvage_directory)[-1])

			# Pick the directory corresponding to the first region in the failed save push (there should only be one anyway)
			region_directory = os.path.join(save_directory, os.listdir(save_directory)[0])

			# Copy each file from the region directory to the `Downloads` directory
			for filename in os.listdir(region_directory):
				shutil.copy(os.path.join(region_directory, filename), os.path.join(downloads_path, filename))

		except Exception as e:
			
			pass #show_error(e, no_ui=True)

		# Create the auxiliary regions for launcher functions (eg. refreshing)
		AUXILIARY_REGIONS = ["Refresh"] #["Backups", "Export", "Refresh"]
		for auxiliary_region in AUXILIARY_REGIONS:

			# Create the auxiliary region directory
			auxiliary_region_path = regions_directory / f"_{auxiliary_region}" #TODO possible directory name conflicts?
			auxiliary_region_path.mkdir(parents=True)

			# Copy the blank `config.bmp` file to the auxiliary region directory
			shutil.copy(get_sc4mp_path("config.bmp"), auxiliary_region_path / "config.bmp")

			# Create a `region.ini` file for the auxiliary region
			with open(get_sc4mp_path("region.ini"), "r") as template_config_file:

				# Read the contents of the template `region.ini`
				config_file_contents: str = template_config_file.read()

				# Replace the region name
				config_file_contents = config_file_contents.replace("New Region", f"{auxiliary_region}...")

				# Write the file
				with open(auxiliary_region_path / "region.ini", "w") as config_file:
					config_file.write(config_file_contents)


	def prep_config(self):

		try:

			# Get the path to the SimCity 4 config last used on this server
			server_config_path = SC4MP_LAUNCHPATH / "_Configs" / f"{self.server.server_id}.cfg"

			# Get the path to the multiplayer config
			mp_config_path = SC4MP_LAUNCHPATH / "SimCity 4.cfg"

			# If the server's config exists
			if server_config_path.exists():

				# Delete the old multiplayer config if it exists
				if mp_config_path.exists():
					os.unlink(mp_config_path)

				# Copy the last used config to be the multiplayer config
				shutil.copy(server_config_path, mp_config_path)

				# Copy the multiplayer config to singleplayer
				sync_simcity_4_cfg()

			else:

				# Copy the singleplayer config to multiplayer if it does not exist
				if not mp_config_path.exists():
					sync_simcity_4_cfg(to_mp=True)

		except Exception as e:

			show_error(f"An error occurred while preparing the config.\n\n{e}", no_ui=True)


	def connection_failed_retrying(self, e, duration=5):

		show_error(e, no_ui=True)

		for count in range(duration):
			self.report("[WARNING] ", f"Connection failed. Retrying in {duration - count}...")
			time.sleep(1)


class GameMonitor(th.Thread):
	


	def __init__(self, server):
		

		th.Thread.__init__(self)

		self.server = server
		
		# Get list of city paths and their md5's
		self.city_paths, self.city_hashcodes = self.get_cities()

		# For backwards compatability
		self.PREFIX = ""

		# For status window and overlay window
		self.ui = None
		self.overlay_ui = None
		
		# If UI enabled (not commandline mode)
		if sc4mp_ui is not None:
			
			# If launcher map enabled, use the map UI for the status window
			if SC4MP_LAUNCHERMAP_ENABLED:
				self.ui = GameMonitorMapUI()

			# Otherwise, use the legacy status window
			else:
				self.ui = GameMonitorUI(self)

			# Create game overlay window if the game overlay is enabled (`1` is fullscreen-mode only; `2` is always enabled)
			if (sc4mp_config["GENERAL"]["use_game_overlay"] == 1 and sc4mp_config["SC4"]["fullscreen"]) or sc4mp_config["GENERAL"]["use_game_overlay"] == 2:
				self.overlay_ui = GameOverlayUI(self.ui, guest=(server.password == ""))
				if sc4mp_game_monitor_x > 0:
					self.ui.withdraw()
			else:
				self.ui.deiconify()

			# Set window title to server name
			self.ui.title(server.server_name)

		# Start the game launcher thread (starts the game)
		self.game_launcher = GameLauncher()
		self.game_launcher.start()

		# Thread shutsdown when this is set to `True`
		self.end = False


	def run(self):
		

		# Catch all errors and show an error message
		try:

			# Thead name for logging
			set_thread_name("GmThread", enumerate=False)

			# if self.ui:
				# self.ui.deiconify()
				# self.ui.grab_set()

			# Declare variable to break loop after the game closes
			end = False

			# Used for refresh stuff (`cfg_hashcode` is the md5 of `SimCity 4.cfg`)
			cfg_hashcode = None
			old_refresh_region_open = False

			# Set initial status in UI
			if self.server.password == "":
				self.report_quietly("Welcome, you've joined as a guest.")
			else:
				self.report_quietly("Welcome, start a city and save to claim a tile.") #Ready. #"Monitoring for changes...")
				
			# Show server description in UI (only for the legacy status window)
			if sc4mp_ui and not SC4MP_LAUNCHERMAP_ENABLED:
				self.ui.ping_frame.left["text"] = f"{self.server.host}:{self.server.port}"
				self.ui.description_label["text"] = self.server.server_description
				self.ui.url_label["text"] = self.server.server_url

			# Time the server was last pinged (`None` for now)
			last_ping_time = None

			# Infinite loop that can be broken by the "end" variable (runs an extra time once it's set to `True`)
			while True:

				# Catch all errors and show an error message in the console
				try:

					# Update server ping in UI every 5 seconds
					if last_ping_time is None or time.time() - last_ping_time >= 5:

						# Ping the server
						ping = self.ping()

						# If the server is responsive, print the ping in the console and display the ping in the ui
						if ping != None:
							print(f"Ping: {ping}")
							if self.ui != None:
								self.ui.ping_frame.right['text'] = f"{ping}ms"
								self.ui.ping_frame.right['fg'] = "gray"
						
						# If the server is unresponsive, print a warning in the console and update the ui accordingly
						else:
							print("[WARNING] Disconnected.")
							if self.ui != None:
								self.ui.ping_frame.right['text'] = "Disconnected"
								self.ui.ping_frame.right['fg'] = "red"
					
						# Set the last ping time
						last_ping_time = time.time()

					# If not in guest mode
					if self.server.password != "":

						#new_city_paths, new_city_hashcodes = self.get_cities()
						
						# Array of savegames to push to the server
						save_city_paths = []

						# Print statements for debugging
						#print("Old cities: " + str(self.city_paths))
						#print("New cities: " + str(new_city_paths))

						# Will be used to store the amount of savegames detected in the previous iteration of the following while loop (-1 means the while loop will always run at least one time!)
						save_city_paths_length = -1

						# Loop until no new/modified savegames were found in the last iteration of the loop (meant to prevent fragmented save pushes, not the best solution because it relies somewhat on the loop delay)
						while len(save_city_paths) != save_city_paths_length:

							# Update the new/modified savegame counter
							save_city_paths_length = len(save_city_paths)

							# Store the paths and hashcodes of savegames in the "Regions" directory to two local arrays
							new_city_paths, new_city_hashcodes = self.get_cities() #TODO I think this should be here...?
							
							# Loop through the paths of the savegames currently found in the "Regions" directory
							for new_city_path in new_city_paths:
								
								# If it's a new savegame, add it to the list of savegames to be pushed to the server
								if not new_city_path in self.city_paths:
									save_city_paths.append(new_city_path)
								
								# If it's not a new savegame, check if it's a modified savegame. If so, add it to the same list
								else:
									city_hashcode = self.city_hashcodes[self.city_paths.index(new_city_path)]
									new_city_hashcode = new_city_hashcodes[new_city_paths.index(new_city_path)]
									if city_hashcode != new_city_hashcode:
										save_city_paths.append(new_city_path)

							# For future comparisons
							self.city_paths = new_city_paths
							self.city_hashcodes = new_city_hashcodes

							# If modified savegames are found
							if len(save_city_paths) > 0:	

								# Report waiting to sync if new/modified savegames found
								self.report("", "Saving...")
								self.set_overlay_state("saving")

								# Wait
								time.sleep(1) #5 #6 #5 #6 #10 #3 #TODO make configurable?

								# Filter the savegames if more than two are found
								if len(save_city_paths) > 2:
									try:
										savegames = []
										for save_city_path in save_city_paths:
											savegame = SC4Savegame(save_city_path, error_callback=None)
											savegame.get_SC4ReadRegionalCity()
											savegames.append(savegame)
										filtered_savegames = self.filter_bordering_tiles(savegames)
										if len(filtered_savegames) == 1:
											save_city_paths = [savegame.filename for savegame in filtered_savegames]
											[savegame.close() for savegame in savegames]
											break
									except Exception as e:
										show_error(e, no_ui=True)

						# If there are any new/modified savegame files, push them to the server. If errors occur, log them in the console and display a warning
						if len(save_city_paths) > 0:
							tries = 0
							while True:
								try:
									self.report("", "Saving...")
									self.set_overlay_state('saving')
									self.push_save(save_city_paths)
									break
								except (socket.timeout, socket.error) as e: # Is `ConnectionResetError` a `socket.error`?
									show_error(e, no_ui=True)
								except Exception as e:
									show_error(e, no_ui=True)
									self.report("[WARNING] ", "Save push failed! Unexpected client-side error.", color="red")
									self.set_overlay_state("not-saved")
									break
								tries += 1
								for count in range(5):
									self.report("[WARNING] ", f"Connection failed. Retrying {5 - count}...")
									time.sleep(1)
								if tries >= 3:
									self.report("[WARNING] ", "Save push failed! Server unreachable.", color="red")
									self.set_overlay_state("not-saved")
									break
							time.sleep(5)

					# Break the loop when signaled
					if end == True:
						break

					# Signal to break the loop when the game is no longer running
					if not self.game_launcher.game_running:
						end = True
						# if self.ui:
						# 	self.ui.deiconify()
						# 	self.ui.deiconify()
						# 	self.ui.lift()
						# 	self.ui.grab_set()
						# 	self.ui.focus_set()
						# 	# I tried everything...

					# Wait
					time.sleep(1) #3 #1 #3

					# Refresh
					cfg_path = get_sc4_cfg_path()
					try:
						new_cfg_hashcode = md5(cfg_path)
						if cfg_hashcode != None and new_cfg_hashcode != cfg_hashcode:
							#print("Region switched!")
							sync_simcity_4_cfg()
							new_refresh_region_open = refresh_region_open()
							if new_refresh_region_open and (not old_refresh_region_open):
								#print("Refresh regions!")
								if ping == None:
									self.report("[WARNING] ", "Unable to refresh regions at this time.", color="red")
								else:
									old_text = self.ui.label["text"]
									self.report("", "Refreshing...")
									self.set_overlay_state("refreshing")
									if sc4mp_ui:
										regions_refresher_ui = RegionsRefresherUI(self.server)
										regions_refresher_ui.worker.run()
										try:
											regions_refresher_ui.destroy()
										except Exception:
											pass
									else:
										regions_refresher = RegionsRefresher(None, self.server)
										regions_refresher.run()
									self.city_paths, self.city_hashcodes = self.get_cities()
									if sc4mp_game_launcher.game_running:
										self.report("", "Regions refreshed at " + datetime.now().strftime("%H:%M") + ".", color="green")
										self.set_overlay_state("refreshed")
									#self.ui.label["text"] = old_text
							old_refresh_region_open = new_refresh_region_open
						cfg_hashcode = new_cfg_hashcode
					except Exception as e:
						show_error(f"An unexpected error occurred while refreshing regions.\n\n{e}", no_ui=True)
					
				except Exception as e:
					if self.end:
						break
					else:
						show_error("An unexpected error occurred in the game monitor loop.", no_ui=True)
						time.sleep(5) #3

			# Save the config used on the server to the `_Configs` directory and restore the singleplayer config
			if sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
				try:
					source = SC4MP_LAUNCHPATH / "SimCity 4.cfg"
					destination = SC4MP_LAUNCHPATH / "_Configs" / f"{self.server.server_id}.cfg"
					if destination.exists():
						destination.unlink()
					shutil.copy(source, destination)
				except Exception as e:
					show_error(f"An error occurred while saving the SimCity 4 config.\n\n{e}", no_ui=True)

			# Restore the singleplayer config backup
			if sc4mp_config["GENERAL"]["sync_simcity_4_cfg"]:
				try:
					sp_config_path = Path("~/Documents/SimCity 4/SimCity 4.cfg").expanduser()
					sp_config_backup_path = Path("~/Documents/SimCity 4/SimCity 4.cfg.bak").expanduser()
					if sp_config_backup_path.exists():
						if sp_config_path.exists():
							os.unlink(sp_config_path)
						shutil.copy(sp_config_backup_path, sp_config_path)
						os.unlink(sp_config_backup_path)
				except Exception as e:
					show_error(f"An error occurred while restoring the SimCity 4 config backup.\n\n{e}", no_ui=True)

			# Destroy the game monitor ui if running
			if self.ui:
				self.ui.destroy()

			# Destroy the game overlay ui if running
			if self.overlay_ui:
				self.overlay_ui.destroy()

			# Show the main ui once again	
			if sc4mp_exit_after:
				if sc4mp_ui is not None:
					sc4mp_ui.destroy()
			else:
				if sc4mp_ui is not None:
					if sc4mp_exit_after:
						sc4mp_ui.destroy()
					else:
						sc4mp_ui.deiconify()
						sc4mp_ui.lift()
						sc4mp_ui.focus_set()
						sc4mp_ui.grab_set()

		except Exception as e:
			
			show_error(f"An unexpected error occurred in the game monitor thread.\n\n{e}")


	def get_cities(self) -> tuple[list[Path], list[str]]:
		
		city_paths = []
		city_hashcodes = []
		regions_path = Path(SC4MP_LAUNCHPATH) / "Regions"
		for region in self.server.regions:
			region_path: Path = regions_path / region
			region_path.mkdir(parents=True, exist_ok=True)
			if region_path.is_file(): # is this necessary?
				continue
			for city in region_path.glob('*.sc4'):
				city_path = region_path / city
				city_paths.append(city_path)
				city_hashcodes.append(md5(city_path))
		return city_paths, city_hashcodes


	def receive_file(self, s: socket.socket, filename: Path):
		"""TODO: unused function?"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print(f"Receiving {filesize} bytes...")
		print(f'writing to "{filename}"')

		filename.unlink(missing_ok=True)

		filesize_read = 0
		with filename.open("wb") as f:
			while filesize_read < filesize:
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				#print('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def filter_bordering_tiles(self, savegames):

		#report("Savegame filter 1", self)

		filtered_savegames = []

		for savegame in savegames:

			add = True

			savegameX = savegame.SC4ReadRegionalCity["tileXLocation"]
			savegameY = savegame.SC4ReadRegionalCity["tileYLocation"]

			savegameSizeX = savegame.SC4ReadRegionalCity["citySizeX"]
			savegameSizeY = savegame.SC4ReadRegionalCity["citySizeY"]

			for neighbor in savegames:

				if neighbor == savegame:
					continue

				neighborX = neighbor.SC4ReadRegionalCity["tileXLocation"]
				neighborY = neighbor.SC4ReadRegionalCity["tileYLocation"]

				neighborSizeX = neighbor.SC4ReadRegionalCity["citySizeX"]
				neighborSizeY = neighbor.SC4ReadRegionalCity["citySizeY"]

				conditionX1 = (neighborX == savegameX - neighborSizeX)
				conditionX2 = (neighborX == savegameX + savegameSizeX)
				conditionY1 = (neighborY == savegameY - neighborSizeY)
				conditionY2 = (neighborY == savegameY + savegameSizeY)

				conditionX = xor(conditionX1, conditionX2) and ((neighborY + neighborSizeY > savegameY) or (neighborY < savegameY + savegameSizeY))
				conditionY = xor(conditionY1, conditionY2) and ((neighborX + neighborSizeX > savegameX) or (neighborX < savegameX + savegameSizeX))

				condition = xor(conditionX, conditionY)

				if not condition:
					add = False

			if add:

				filtered_savegames.append(savegame)

				#report("YES (" + str(savegameX) + ", " + str(savegameY) + ")", self)

			#else:

				#report("NO (" + str(savegameX) + ", " + str(savegameY) + ")", self)

		return filtered_savegames


	def push_save(self, save_city_paths: list[Path]) -> None:
		

		# Report progress: backups
		#self.report(self.PREFIX, 'Creating backups...')
		
		# Create backups #TODO salvage
		#for save_city_path in save_city_paths:
		#	self.backup_city(save_city_path)

		# Update overlay
		self.set_overlay_state("saving")

		# Salvage
		#self.report(self.PREFIX, 'Saving: copying to salvage...') #Pushing save #for "' + new_city_path + '"')
		salvage_directory = Path(SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id / datetime.now().strftime("%Y%m%d%H%M%S")
		for path in save_city_paths:
			relpath = path.relative_to(Path(SC4MP_LAUNCHPATH) / "Regions")
			filename = salvage_directory / relpath
			directory = filename.parent
			directory.mkdir(exist_ok=True, parents=True)
			shutil.copy(path, filename)

		# Verify that all saves come from the same region
		#self.report(self.PREFIX, 'Saving: verifying...')
		regions = set([save_city_path.parent.name for save_city_path in save_city_paths])
		if len(regions) > 1:
			self.report(self.PREFIX, 'Save push failed! Too many regions.', color="red") 
			self.set_overlay_state("not-saved")
			return
		else:
			region = list(regions)[0]

		# Create socket
		#self.report(self.PREFIX, 'Saving: connecting to server...')
		s = self.create_socket()
		if s == None:
			self.report(self.PREFIX, 'Save push failed! Server unreachable.', color="red") #'Unable to save the city "' + new_city + '" because the server is unreachable.'
			self.set_overlay_state("not-saved")
			return

		# Send save request
		#self.report(self.PREFIX, 'Saving: sending save request...')
		s.sendall(f"save {SC4MP_VERSION} {self.server.user_id} {self.server.password}".encode())
		
		# Separator
		s.recv(SC4MP_BUFFER_SIZE)

		# Send region name and file sizes
		#self.report(self.PREFIX, 'Saving: sending metadata...')
		send_json(s, [
			region,
			[os.path.getsize(save_city_path) for save_city_path in save_city_paths]
		])

		# Separator
		s.recv(SC4MP_BUFFER_SIZE)

		# Send file contents
		total_filesize = sum([save_city_path.stat().st_size for save_city_path in save_city_paths])
		filesize_sent = 0
		filesize_reported = None
		#self.report(self.PREFIX, f'Saving: sending gamedata...') # ({format_filesize(total_filesize)})...')
		for save_city_path in save_city_paths:
			#self.report(self.PREFIX, f'Saving: sending files ({save_city_paths.index(save_city_path) + 1} of {len(save_city_paths)})...')
			with open(save_city_path, "rb") as file:
				while True:
					data = file.read(SC4MP_BUFFER_SIZE)
					if not data:
						break
					s.sendall(data)
					filesize_sent += len(data)
					if filesize_sent == total_filesize or filesize_reported is None or filesize_sent > filesize_reported + 100000:
						filesize_reported = filesize_sent
						self.report_quietly(f'Saving... ({round(filesize_sent / 1000):,}/{round(total_filesize / 1000):,}KB)') #self.report_quietly(f'Saving: sending gamedata ({format_filesize(filesize_sent, scale=total_filesize)[:-2]}/{format_filesize(total_filesize)})...')

		# Send file count
		#s.sendall(str(len(save_city_paths)).encode())
		#.recv(SC4MP_BUFFER_SIZE)
		#
		# Send files
		#for save_city_path in save_city_paths:
		#
		#	# Get region and city names
		#	region = save_city_path.parent.name
		#	city = save_city_path.name
		#
		#	# Send region name
		#	s.sendall(region.encode())
		#	s.recv(SC4MP_BUFFER_SIZE)
		#
		#	# Send city name
		#	s.sendall(city.encode())
		#	s.recv(SC4MP_BUFFER_SIZE)
		#
		#	# Send file
		#	self.send_file(s, save_city_path)
		#	s.recv(SC4MP_BUFFER_SIZE)
		#
		# Separator
		#s.sendall(SC4MP_SEPARATOR)

		# Handle response from server
		#self.report(self.PREFIX, 'Saving: awaiting response...')
		response = s.recv(SC4MP_BUFFER_SIZE).decode()
		if response == "ok":
			self.report(self.PREFIX, f'Saved successfully at {datetime.now().strftime("%H:%M")}.', color="green") #TODO keep track locally of the client's claims
			self.set_overlay_state("saved")
			shutil.rmtree(salvage_directory) #TODO make configurable
		else:
			self.report(self.PREFIX + "[WARNING] ", f"Save push failed! {response}", color="red")
			self.set_overlay_state("not-saved")

		# Close socket
		s.close()


	def backup_city(self, city_path: Path) -> None:
		
		region = city_path.parent.name
		city = city_path.name
		backup_directory: Path = Path(SC4MP_LAUNCHPATH) / "SC4MPBackups" / self.server.server_id / region / city
		backup_directory.mkdir(exist_ok=True, parents=True)
		destination = backup_directory / datetime.now().strftime("%Y%m%d%H%M%S")
		shutil.copy(city_path, destination.with_suffix(".sc4"))


	def create_socket(self):
		

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		#tries_left = 3

		#while True:

		#	try:

				#self.report("", "Connecting...")
		s.connect((host, port))

				#self.report("", "Connected.")

		#		break

		#	except socket.error as e:
				
		#		if tries_left > 0:
				
		#			show_error(e, no_ui=True)

		#			count = 5
		#			while count > 0:
		#				self.report("[WARNING] ", f"Connection failed. Retrying in {count}...")
		#				count = count - 1
		#				time.sleep(1)

		#			tries_left = tries_left - 1

		#		else:

		#			return None

		return s


	def send_file(self, s: socket.socket, filename: Path) -> None:
		

		self.report_quietly("Saving...")
		self.set_overlay_state("saving")
		print(f'Sending file "{filename}"...')

		filesize = filename.stat().st_size

		s.sendall(str(filesize).encode())
		s.recv(SC4MP_BUFFER_SIZE)

		with filename.open("rb") as f:
			while True:
				bytes_read = f.read(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				s.sendall(bytes_read)


	def ping(self):
		
		return self.server.ping()


	def report(self, prefix, text, color="black"):
		
		if self.ui != None:
			self.ui.label['text'] = text
			self.ui.label.config(fg=color)
		print(prefix + text)


	def report_quietly(self, text):
		
		if self.ui != None:
			self.ui.label['text'] = text


	def set_overlay_state(self, state):
		if self.overlay_ui is not None:
			self.overlay_ui.set_state(state)


class GameLauncher(th.Thread):
	


	def __init__(self):
		
		super().__init__()
		
		global sc4mp_game_launcher
		sc4mp_game_launcher = self

		self.game_running = True
		self.setDaemon(True)


	def run(self):
		
		try:

			set_thread_name("GlThread", enumerate=False)

			start_sc4()

		except Exception as e:

			show_error(f"An unexpected error occurred while launching SimCity 4.\n\n{e}")

		finally:

			self.game_running = False

			global sc4mp_current_server
			sc4mp_current_server = None


class RegionsRefresher(th.Thread):
	

	def __init__(self, ui, server):

		th.Thread.__init__(self)

		self.ui = ui
		self.server = server

		self.setDaemon(True)


	def run(self):
		
		
		while sc4mp_game_launcher.game_running:

			try:

				set_thread_name("RrThread", enumerate=False)

				# Report
				self.report("", "Refreshing regions...")
				
				# Set destination
				destination = Path(SC4MP_LAUNCHPATH) / "Regions"

				# Purge the region directories
				for region in self.server.regions:
					purge_directory(destination / region)

				# Create the socket
				s = self.create_socket()

				# Request regions
				if not self.server.private:
					s.sendall(b"regions")
				else:
					s.sendall(f"regions {SC4MP_VERSION} {self.server.user_id} {self.server.password}".encode())

				# Receive file table
				file_table = recv_json(s)

				# Get total download size
				size = sum([entry[1] for entry in file_table])

				# Total size downloaded
				size_downloaded = 0

				# Download percent
				percent = 0

				# Set loading bar at 0%
				self.report_progress("Refreshing regions... (0%)", 0, 100)

				# Prune file table as necessary
				ft = []
				for entry in file_table:

					# Get necessary values from entry
					checksum = sanitize_directory_name(entry[0])
					filesize = entry[1]
					relpath = Path(entry[2])

					# Get path of cached file
					t = Path(SC4MP_LAUNCHPATH) / "_Cache" / checksum

					# Use the cached file if it exists and has the same size, otherwise append the entry to the new file table
					if t.exists() and t.stat().st_size == filesize:
						
						# Report
						print(f'- using cached "{checksum}"')

						# Set the destination
						d = sanitize_relpath(Path(destination), relpath)

						# Display current file in UI
						try:
							self.ui.progress_label["text"] = d.name #.relative_to(destination)
							self.ui.duration_label["text"] = "Cache 🡒 SC4" #"(cached)"
						except Exception:
							pass

						# Create the destination directory if necessary
						d.parent.mkdir(parents=True, exist_ok=True)

						# Delete the destination file if it exists
						d.unlink(missing_ok=True)

						# Copy the cached file to the destination
						shutil.copy(t, d)

						# Update progress bar
						size_downloaded += filesize
						old_percent = percent
						percent = math.floor(100 * (size_downloaded / (size + 1)))
						if percent > old_percent:
							self.report_progress(f"Refreshing regions... ({percent}%)", percent, 100)

					else:

						# Append to new file table
						ft.append(entry)
					
				file_table = ft

				# Send pruned file table
				send_json(s, file_table)

				# Receive files
				for entry in file_table:

					# Get necessary values from entry
					checksum = sanitize_directory_name(entry[0])
					filesize = entry[1]
					relpath = Path(entry[2])

					# Report
					print(f'- caching "{checksum}"...')

					# Set the destination
					d = sanitize_relpath(Path(destination), relpath)

					# Display current file in UI
					try:
						self.ui.progress_label["text"] = d.name #.relative_to(destination)
						self.ui.duration_label["text"] = "Server 🡒 SC4" #"(downloading)"
					except Exception:
						pass

					# Set path of cached file
					t = Path(SC4MP_LAUNCHPATH) / "_Cache" / checksum

					# Create the destination directory if necessary
					d.parent.mkdir(parents=True, exist_ok=True)

					# Delete the destination file if it exists
					d.unlink(missing_ok=True)

					# Delete the cache file if it exists
					t.unlink(missing_ok=True)

					# Delete cache files if cache too large to accomadate the new cache file
					cache_directory = Path(SC4MP_LAUNCHPATH) / "_Cache"
					while any(cache_directory.iterdir()) and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize:
						random_cache = random.choice(list(cache_directory.iterdir()))
						random_cache.unlink()

					# Receive the file. Write to both the destination and cache
					filesize_read = 0
					with d.open("wb") as dest, t.open("wb") as cache:
						while filesize_read < filesize:
							filesize_remaining = filesize - filesize_read
							buffersize = SC4MP_BUFFER_SIZE if filesize_remaining > SC4MP_BUFFER_SIZE else filesize_remaining
							bytes_read = s.recv(buffersize)
							if not bytes_read:
								break
							for file in [dest, cache]:
								file.write(bytes_read)
							filesize_read += len(bytes_read)
							size_downloaded += len(bytes_read)
							old_percent = percent
							percent = math.floor(100 * (size_downloaded / (size + 1)))
							if percent > old_percent:
								self.report_progress(f"Refreshing regions... ({percent}%)", percent, 100)

				self.report_progress("Refreshing regions... (100%)", 100, 100)

				# Receive file count
				#file_count = int(s.recv(SC4MP_BUFFER_SIZE).decode())
				#
				# Separator
				#s.sendall(SC4MP_SEPARATOR)
				#
				# Receive file size
				#size = int(s.recv(SC4MP_BUFFER_SIZE).decode())
				#
				# Receive files
				#size_downloaded = 0
				#for files_received in range(file_count):
				#	percent = math.floor(100 * (size_downloaded / (size + 1)))
				#	self.report_progress(f'Refreshing regions... ({percent}%)', percent, 100)
				#	s.sendall(SC4MP_SEPARATOR)
				#	size_downloaded += self.receive_or_cached(s, destination)
				#self.report_progress("Refreshing regions... (100%)", 100, 100)

				# Report
				self.report("", "Refreshing regions...")

				# Prep region configs
				for region in self.server.regions:
					prep_region_config(destination / region / "region.ini")

				# Report
				self.report("", "Done.")

				break

			except Exception as e:

				#if self.ui != None:
				#	self.ui.withdraw()

				show_error("An error occurred while refreshing regions.\n\n" + str(e), no_ui=True)


	def report(self, prefix, text):
		
		if self.ui != None:
			self.ui.label['text'] = text
			self.ui.progress_bar.start(2)
			self.ui.progress_bar['mode'] = "indeterminate"
			self.ui.progress_bar['maximum'] = 100
		print(prefix + text)
		#time.sleep(1) # for testing


	def report_progress(self, text, value, maximum):
		
		if self.ui != None:
			self.ui.label['text'] = text
			self.ui.progress_bar.stop()
			self.ui.progress_bar['mode'] = "determinate"
			self.ui.progress_bar['value'] = value
			self.ui.progress_bar['maximum'] = maximum
		print(text)


	def create_socket(self):
		

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		try:

			self.report("", "Connecting...")
			s.connect((host, port))

			self.report("", "Connected.")

		except socket.error as e:
			
			raise ClientException("Connection failed.\n\n" + str(e)) from e

		return s


class DatabaseManager(th.Thread):
	

	
	def __init__(self, filename: Path) -> None:
		

		super().__init__()

		self.end = False

		self.filename = filename
		self.backup_filename = Path(f"{filename}.bak")
		self.data = self.load_json()


	def run(self):
		
	
		try:
			
			set_thread_name("DbThread")

			old_data = str(self.data)
			
			while not self.end: #TODO pretty dumb way of checking if a dictionary has been modified
				try:
					time.sleep(SC4MP_DELAY * 5)
					new_data = str(self.data)
					if old_data != new_data:
						#report(f'Updating "{self.filename}"...', self)
						self.update_json()
						#report("- done.", self)
					old_data = new_data
				except Exception as e:
					show_error(f"An unexpected error occurred in the database thread.\n\n{e}")

		except Exception as e:

			fatal_error()


	def load_json(self):
		
		try:
			return load_json(self.filename)
		except Exception as e:
			show_error(e, no_ui=True)
			print(f"[WARNING] Falied to load \"{self.filename}\". Attempting to load backup...")
			try:
				return load_json(self.backup_filename)
			except Exception as e:
				raise ClientException(f"Failed to load \"{self.filename}\". Loading the backup at \"{self.backup_filename}\" also failed.") from e


	def update_json(self):
		
		if self.filename.exists():
			if self.backup_filename.exists():
				os.unlink(self.backup_filename)
			shutil.copy(self.filename, self.backup_filename)

		return update_json(self.filename, self.data)


	def keys(self):

		return self.data.keys()


	def get(self, key, default):

		return self.data.get(key, default)


	def __getitem__(self, key):

		return self.data.__getitem__(key)


	def __setitem__(self, key, value):

		return self.data.__setitem__(key, value)


# User Interfaces

class UI(tk.Tk):
	


	def __init__(self):
		


		#print("Initializing...")


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

		self.bind("<F1>", lambda event:self.direct_connect())
		self.bind("<F2>", lambda event:self.refresh())
		self.bind("<F3>", lambda event:self.host())
		self.bind("<F5>", lambda event:self.general_settings())
		self.bind("<F6>", lambda event:self.storage_settings())
		self.bind("<F7>", lambda event:self.SC4_settings())


		# Menu

		menu = Menu(self)  
		
		launcher = Menu(menu, tearoff=0)  
		settings_submenu = Menu(menu, tearoff=0)
		settings_submenu.add_command(label="General...", accelerator="F5", command=self.general_settings)     
		settings_submenu.add_command(label="Storage...", accelerator="F6", command=self.storage_settings)    
		settings_submenu.add_command(label="SC4...", accelerator="F7", command=self.SC4_settings)
		launcher.add_cascade(label="Settings", menu=settings_submenu) 
		launcher.add_separator()
		launcher.add_command(label="Updates...", command=lambda:webbrowser.open_new_tab(SC4MP_RELEASES_URL)) 
		launcher.add_separator()
		launcher.add_command(label="Exit", command=self.quit)  
		menu.add_cascade(label="Launcher", menu=launcher)  #TODO rename to "Launcher" and put settings in cascade?

		servers = Menu(menu, tearoff=0)  
		
		servers.add_command(label="Connect...", accelerator="F1", command=self.direct_connect)
		servers.add_command(label="Refresh", accelerator="F2", command=self.refresh)
		servers.add_separator() 
		servers.add_command(label="Host...", accelerator="F3", command=self.host)
		menu.add_cascade(label="Servers", menu=servers)  

		help = Menu(menu, tearoff=0)  	
		help.add_command(label="About...", command=self.about)
		help.add_command(label="Readme...", command=self.readme)
		help.add_separator()
		help.add_command(label="Logs...", command=open_logs)
		help.add_separator()
		help.add_command(label="Feedback...", command=lambda:webbrowser.open_new_tab(SC4MP_ISSUES_URL))
		#feedback_submenu = Menu(help, tearoff=0)
		#feedback_submenu.add_command(label=SC4MP_FEEDBACK_LINKS[0][0], command=lambda:webbrowser.open_new_tab(SC4MP_FEEDBACK_LINKS[0][1]))
		#feedback_submenu.add_command(label=SC4MP_FEEDBACK_LINKS[1][0], command=lambda:webbrowser.open_new_tab(SC4MP_FEEDBACK_LINKS[1][1]))
		#for link in SC4MP_FEEDBACK_LINKS:
		#	feedback_submenu.add_command(label=link[0], command=lambda:webbrowser.open_new_tab(link[1])) #TODO why does the github button open discord?
		#help.add_cascade(label="Feedback", menu=feedback_submenu)
		menu.add_cascade(label="Help", menu=help)
		
		self.config(menu=menu)  


		# Release notes
			
		th.Thread(target=self.release_notes, daemon=True).start()


		# Server browser

		if sc4mp_config["GENERAL"]["use_server_browser"]:
			self.server_list = ServerListUI(self)
			self.server_list.grid(row=0, column=0, padx=0, pady=0, sticky="w")
		else:
			self.label = tk.Label(self, text="SERVER BROWSER DISABLED") #\n\nTo get started, press <F1> and enter the IP address and port of the server you wish to connect to.")
			self.label.pack(anchor="center", pady=250)
			#self.label = tk.Label(self, justify="center", text='To get started, select "Servers" then "Connect..." in the menu bar and enter the hostname and port of the server you wish to connect to.')
			#self.label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")


	def release_notes(self):

		global sc4mp_beta

		try:

			# Set version for release info
			version = SC4MP_VERSION

			# Get current release info
			release_info = get_release_info(version=version)
			
			# Set beta flag to `True` if pre-release
			if "prerelease" in release_info.keys():
				sc4mp_beta = release_info["prerelease"]

			# Create release notes UI
			if sc4mp_config["GENERAL"]["show_release_notes"] and sc4mp_config["GENERAL"]["release_notes_version"] != SC4MP_VERSION:
				ReleaseNotesUI(version, release_info["name"], release_info["body"])

		except Exception as e:

			show_error(f"Unable to show release notes.\n\n{e}", no_ui=True)


	def show_error(self, *args):
		
		fatal_error()


	def to_implement(self):
		
		tk.messagebox.showerror(title=SC4MP_TITLE, message="This feature is incomplete and will be available in future versions of the client.")


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

		message = "One of the next releases of the SC4MP Launcher will be capable of hosting servers " \
			"from within the launcher, but for now, you can run the SC4MP Server manually. See the Github repository " \
			"for more information.\n\n" if is_windows() else ""

		if messagebox.askyesno(SC4MP_TITLE, f"Hosting a server requires the SC4MP Server application.\n\n{message}Would you like to view the GitHub repository?"):
			webbrowser.open_new_tab("https://github.com/kegsmr/sc4mp-server/")



	def direct_connect(self):
		
		print('"Direct connect..."')
		DirectConnectUI()


	def refresh(self):
		
		if sc4mp_config["GENERAL"]["use_server_browser"]:
			self.server_list.worker = ServerList(self.server_list, kill=self.server_list.worker)
			self.server_list.worker.start()


	def about(self):
		
		AboutUI()


	def readme(self):
		
		webbrowser.open_new_tab(SC4MP_README_PATH)


	def withdraw(self):
		super().withdraw()
		try:
			self.server_list.worker.pause = True
		except Exception as e:
			show_error("Unable to pause server list thread.", no_ui = True)


	def deiconify(self):
		super().deiconify()
		try:
			self.server_list.worker.pause = False
		except Exception as e:
			pass
			#show_error(e, no_ui = True)


class GeneralSettingsUI(tk.Toplevel):


	def __init__(self):
		

		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

		# Config update
		self.config_update = []

		# Updates frame
		self.updates_frame = tk.LabelFrame(self, text="Updates", width=50)
		self.updates_frame.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="nw")

		# Updates checkbutton
		self.updates_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["auto_update"])
		self.updates_frame.checkbutton = ttk.Checkbutton(self.updates_frame, text="Check for updates at startup", onvalue=True, offvalue=False, variable=self.updates_frame.checkbutton_variable)
		self.updates_frame.checkbutton.grid(row=0, column=0, columnspan=1, padx=10, pady=(10,10), sticky="w")
		self.config_update.append((self.updates_frame.checkbutton_variable, "auto_update"))

		# UI frame
		self.ui_frame = tk.LabelFrame(self, text="UI")		
		self.ui_frame.grid(row=1, column=0, columnspan=1, padx=10, pady=0, sticky="nw")

		# Use game overlay
		self.ui_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["use_game_overlay"])
		self.ui_frame.checkbutton = ttk.Checkbutton(self.ui_frame, text="Use game overlay", onvalue=True, offvalue=False, variable=self.ui_frame.checkbutton_variable)
		self.ui_frame.checkbutton.grid(row=0, column=0, columnspan=1, padx=(10,65), pady=(10,5), sticky="w")
		self.config_update.append((self.ui_frame.checkbutton_variable, "use_game_overlay"))

		# Use launcher map
		#self.ui_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["use_launcher_map"])
		#self.ui_frame.checkbutton = ttk.Checkbutton(self.ui_frame, text="Use launcher map", onvalue=True, offvalue=False, variable=self.ui_frame.checkbutton_variable)
		#self.ui_frame.checkbutton.grid(row=1, column=0, columnspan=1, padx=10, pady=(5,5), sticky="w")
		#self.config_update.append((self.ui_frame.checkbutton_variable, "use_launcher_map"))

		# Use fullscreen background
		self.ui_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["use_fullscreen_background"])
		self.ui_frame.checkbutton = ttk.Checkbutton(self.ui_frame, text="Use loading background", onvalue=True, offvalue=False, variable=self.ui_frame.checkbutton_variable)
		self.ui_frame.checkbutton.grid(row=2, column=0, columnspan=1, padx=10, pady=(5,10), sticky="w")
		self.config_update.append((self.ui_frame.checkbutton_variable, "use_fullscreen_background"))

		# Mayors online cutoff label
		#self.ui_frame.mayors_online_cutoff_label = tk.Label(self.ui_frame, text="Show mayors online in the past")
		#self.ui_frame.mayors_online_cutoff_label.grid(row=0, column=0, padx=10, pady=(10,5))

		# Mayors online cutoff combobox
		#self.ui_frame.mayors_online_cutoff_combobox = ttk.Combobox(self.ui_frame)
		#self.ui_frame.mayors_online_cutoff_combobox.grid(row=0, column=1)

		# Security frame
		self.security_frame = tk.LabelFrame(self, text="Security")
		self.security_frame.grid(row=0, column=1, columnspan=1, rowspan=2, padx=10, pady=10, sticky="nw")

		# Save server passwords checkbutton
		self.security_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["save_server_passwords"])
		self.security_frame.checkbutton = ttk.Checkbutton(self.security_frame, text="Save server passwords", onvalue=True, offvalue=False, variable=self.security_frame.checkbutton_variable)
		self.security_frame.checkbutton.grid(row=0, column=0, columnspan=1, padx=10, pady=(10,5), sticky="w")
		self.config_update.append((self.security_frame.checkbutton_variable, "save_server_passwords"))

		# Ignore 3rd-party server warnings checkbutton
		self.security_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["ignore_third_party_server_warnings"])
		self.security_frame.checkbutton = ttk.Checkbutton(self.security_frame, text="Hide 3rd-party server warnings", onvalue=True, offvalue=False, variable=self.security_frame.checkbutton_variable)
		self.security_frame.checkbutton.grid(row=1, column=0, columnspan=1, padx=10, pady=(5,5), sticky="w")
		self.config_update.append((self.security_frame.checkbutton_variable, "ignore_third_party_server_warnings"))

		# Ignore authentication errors checkbutton
		self.security_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["ignore_token_errors"])
		self.security_frame.checkbutton = ttk.Checkbutton(self.security_frame, text="Hide authentication warnings", onvalue=True, offvalue=False, variable=self.security_frame.checkbutton_variable)
		self.security_frame.checkbutton.grid(row=2, column=0, columnspan=1, padx=10, pady=(5,5), sticky="w")
		self.config_update.append((self.security_frame.checkbutton_variable, "ignore_token_errors"))

		# Ignore file warnings checkbutton
		self.security_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["ignore_risky_file_warnings"])
		self.security_frame.checkbutton = ttk.Checkbutton(self.security_frame, text="Hide dangerous file warnings", onvalue=True, offvalue=False, variable=self.security_frame.checkbutton_variable)
		self.security_frame.checkbutton.grid(row=3, column=0, columnspan=1, padx=10, pady=(5,32), sticky="w")
		self.config_update.append((self.security_frame.checkbutton_variable, "ignore_risky_file_warnings"))

		# Path frame
		self.path_frame = tk.LabelFrame(self, text="Custom plugins")		
		self.path_frame.grid(row=10, column=0, columnspan=3, padx=10, pady=10, sticky="w")

		# Path checkbutton
		self.path_frame.checkbutton_variable = tk.BooleanVar(value=sc4mp_config["GENERAL"]["custom_plugins"])
		self.path_frame.checkbutton = ttk.Checkbutton(self.path_frame, text="Enable", onvalue=True, offvalue=False, variable=self.path_frame.checkbutton_variable)
		self.path_frame.checkbutton.grid(row=0, column=0, columnspan=1, padx=10, pady=(10,5), sticky="w")
		self.config_update.append((self.path_frame.checkbutton_variable, "custom_plugins"))

		# Path entry
		self.path_frame.entry = ttk.Entry(self.path_frame, width = 50)
		self.path_frame.entry.grid(row=1, column=0, columnspan=1, padx=10, pady=10)
		self.path_frame.entry.insert(0, sc4mp_config["GENERAL"]["custom_plugins_path"])
		self.config_update.append((self.path_frame.entry, "custom_plugins_path"))

		# Path browse button
		self.path_frame.button = ttk.Button(self.path_frame, text="Browse...", command=self.browse_path)
		self.path_frame.button.grid(row=1, column=1, columnspan=1, padx=10, pady=10)

		# Path label
		self.path_frame.label = ttk.Label(self.path_frame, text='Some servers allow users to load their own plugins alongside the server \nplugins. Specify your plugins directory here so that they can be loaded \nwhen joining a server.')
		self.path_frame.label.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")

		# Reset button
		self.reset_button = ttk.Button(self, text="Reset", command=self.reset)
		self.reset_button.grid(row=99, column=0, columnspan=1, padx=10, pady=10, sticky="sw")

		# Ok/Cancel frame
		self.ok_cancel = tk.Frame(self)
		self.ok_cancel.grid(row=99, column=1, columnspan=2, sticky="se")

		# Ok button
		self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Ok", command=self.ok, default="active")
		self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w")

		# Cancel button
		self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.destroy)
		self.ok_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e")


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
		sc4mp_config.update()
		self.destroy()


	def reset(self):
		
		if messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning"):
			self.destroy()
			sc4mp_config.data.pop("GENERAL")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS, error_callback=show_error, update_constants_callback=update_config_constants).data
			self.__init__()


class StorageSettingsUI(tk.Toplevel):


	def __init__(self):
		

		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

		# Config update
		self.config_update = []

		# Path frame
		self.path_frame = tk.LabelFrame(self, text="Launch path")		
		self.path_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

		# Path entry
		self.path_frame.entry = ttk.Entry(self.path_frame, width = 50)
		self.path_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=10)
		self.path_frame.entry.insert(0, sc4mp_config["STORAGE"]["storage_path"])
		self.config_update.append((self.path_frame.entry, "storage_path"))

		# Path browse button
		self.path_frame.button = ttk.Button(self.path_frame, text="Browse...", command=self.browse_path)
		self.path_frame.button.grid(row=0, column=1, columnspan=1, padx=10, pady=10)

		# Path label
		self.path_frame.label = ttk.Label(self.path_frame, text='Do NOT change this to your normal launch directory, or else your plugins \nand regions will be deleted!')
		self.path_frame.label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="w")

		# Cache size frame
		self.cache_size_frame = tk.LabelFrame(self, text="Cache size")
		self.cache_size_frame.grid(row=99, column=0, columnspan=1, padx=10, pady=10, sticky="w")

		# Cache size entry
		self.cache_size_frame.entry = ttk.Entry(self.cache_size_frame, width=10)
		self.cache_size_frame.entry.insert(0, format_filesize(sc4mp_config["STORAGE"]["cache_size"] * 1000000))
		self.cache_size_frame.entry.grid(row=0, column=0, columnspan=1, padx=(10,0), pady=10, sticky="w")
		self.config_update.append((self.cache_size_frame.entry, "cache_size"))

		# Cache size label
		#self.cache_size_frame.label = ttk.Label(self.cache_size_frame, text="mb")
		#self.cache_size_frame.label.grid(row=0, column=1, columnspan=1, padx=(2,10), pady=10, sticky="w")

		# Clear cache button
		self.cache_size_frame.button = ttk.Button(self.cache_size_frame, text="Clear cache", command=self.clear_cache)
		self.cache_size_frame.button.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

		# Reset button
		self.reset_button = ttk.Button(self, text="Reset", command=self.reset)
		self.reset_button.grid(row=99, column=1, columnspan=1, padx=10, pady=10, sticky="sw")

		# Ok/Cancel frame
		self.ok_cancel = tk.Frame(self)
		self.ok_cancel.grid(row=99, column=2, columnspan=2, sticky="se")

		# Ok button
		self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Ok", command=self.ok, default="active")
		self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w")

		# Cancel button
		self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.destroy)
		self.ok_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e")


	def clear_cache(self):
		
		#if (messagebox.askokcancel(title=SC4MP_TITLE, message="Clear the download cache?", icon="warning")): #TODO make yes/no
		purge_directory(Path(SC4MP_LAUNCHPATH) / "_Cache")


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
			if key == "storage_path" and type(data) is str and Path(data) != Path(sc4mp_config["STORAGE"]["storage_path"]):
				if (Path(data) / 'Plugins').exists() or (Path(data) / 'Regions').exists():
					if not messagebox.askokcancel(title=SC4MP_TITLE, message=f'The directory "{data}" already contains SimCity 4 plugins and regions. \n\nProceeding will result in the IRREVERSIBLE DELETION of these files! \n\nThis is your final warning, do you wish to proceed?', icon="warning"): #TODO make message box show yes/no and not ok/cancel
						raise ClientException("Operation cancelled by user.")
				else:
					if not messagebox.askokcancel(title=SC4MP_TITLE, message="Changing the launch path will cause you to lose access to your claimed tiles on servers you play on.\n\nYou will only be able to access these claims in the future by setting the launch path back to what it's currently set to now.\n\nDo you wish to proceed?", icon="warning"):
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
				subprocess.Popen([sys.executable, "-skip-update", "-allow-multiple"])
			else:
				subprocess.Popen([sys.executable, os.path.abspath(__file__)])
			sc4mp_ui.quit()
		#create_subdirectories() 
		#load_database()
		

	def ok(self):
		
		try:
			self.update()
			sc4mp_config.update()
			self.destroy()
		except ClientException:
			pass


	def reset(self):
		
		if messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning"): #TODO make yes/no
			self.destroy()
			sc4mp_config.data.pop("STORAGE")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS, error_callback=show_error, update_constants_callback=update_config_constants).data
			self.__init__()


class SC4SettingsUI(tk.Toplevel):


	def __init__(self):
		

		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

		# Config update
		self.config_update = []

		# Path frame
		self.path_frame = tk.LabelFrame(self, text="Custom installation path")		
		self.path_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

		# Path entry
		self.path_frame.entry = ttk.Entry(self.path_frame, width = 40)
		self.path_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=10)
		self.path_frame.entry.insert(0, sc4mp_config["SC4"]["game_path"])
		self.config_update.append((self.path_frame.entry, "game_path"))

		# Path browse button
		self.path_frame.button = ttk.Button(self.path_frame, text="Browse...", command=self.browse_path)
		self.path_frame.button.grid(row=0, column=1, columnspan=1, padx=10, pady=10)

		# Path label
		self.path_frame.label = ttk.Label(self.path_frame, text='If the launcher fails to find SimCity 4 installed on your computer, \nspecify the path to the game installation here.')
		self.path_frame.label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10))

		# Resolution frame
		self.resolution_frame = tk.LabelFrame(self, text="Resolution")		
		self.resolution_frame.grid(row=1, column=0, columnspan=1, rowspan=2, padx=10, pady=5, sticky="w")

		# Resolution combo box
		self.resolution_frame.combo_box = ttk.Combobox(self.resolution_frame, width=15)
		if 0 in (sc4mp_config["SC4"]["resw"], sc4mp_config["SC4"]["resh"]):
			self.resolution_frame.combo_box.insert(0, "Automatic")
		else:
			self.resolution_frame.combo_box.insert(0, str(sc4mp_config["SC4"]["resw"]) + "x" + str(sc4mp_config["SC4"]["resh"]))
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
		self.resolution_frame.combo_box.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w")
		self.config_update.append((self.resolution_frame.combo_box, "res"))

		# Fullscreen checkbutton
		self.resolution_frame.fullscreen_checkbutton_variable = tk.BooleanVar(value=sc4mp_config["SC4"]["fullscreen"])
		self.resolution_frame.fullscreen_checkbutton = ttk.Checkbutton(self.resolution_frame, text="Fullscreen", onvalue=True, offvalue=False, variable=self.resolution_frame.fullscreen_checkbutton_variable)
		self.resolution_frame.fullscreen_checkbutton.grid(row=1, column=0, columnspan=1, padx=10, pady=(14,25), sticky="w")
		self.config_update.append((self.resolution_frame.fullscreen_checkbutton_variable, "fullscreen"))

		# CPU count frame
		self.cpu_count_frame = tk.LabelFrame(self, text="CPU count")
		self.cpu_count_frame.grid(row=1, column=1, columnspan=1, rowspan=1, padx=10, pady=5, sticky="w")

		# CPU count entry
		self.cpu_count_frame.entry = ttk.Entry(self.cpu_count_frame, width = 10)
		self.cpu_count_frame.entry.insert(0, str(sc4mp_config["SC4"]["cpu_count"]))
		self.cpu_count_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=5, sticky="w")
		self.config_update.append((self.cpu_count_frame.entry, "cpu_count"))

		# CPU priority frame
		self.cpu_priority_frame = tk.LabelFrame(self, text="CPU priority")
		self.cpu_priority_frame.grid(row=1, column=2, columnspan=1, rowspan=1, padx=10, pady=5, sticky="e")

		# CPU priority entry
		self.cpu_priority_frame.combo_box = ttk.Combobox(self.cpu_priority_frame, width=8)
		self.cpu_priority_frame.combo_box.insert(0, sc4mp_config["SC4"]["cpu_priority"])
		self.cpu_priority_frame.combo_box["values"] = ("low", "normal", "high")
		self.cpu_priority_frame.combo_box.grid(row=0, column=0, columnspan=1, padx=10, pady=5, sticky="w")
		self.config_update.append((self.cpu_priority_frame.combo_box, "cpu_priority"))

		# Additional properties frame
		self.additional_properties_frame = tk.LabelFrame(self, text="Additional launch properties")		
		self.additional_properties_frame.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="w")

		# Additional properties entry
		self.additional_properties_frame.entry = ttk.Entry(self.additional_properties_frame, width = 30)
		self.additional_properties_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w")
		self.additional_properties_frame.entry.insert(0, sc4mp_config["SC4"]["additional_properties"])
		self.config_update.append((self.additional_properties_frame.entry, "additional_properties"))

		# Reset/Preview frame
		self.reset_preview = tk.Frame(self)
		self.reset_preview.grid(row=99, column=0, columnspan=2, sticky="w")

		# Reset button
		self.reset_preview.reset_button = ttk.Button(self.reset_preview, text="Reset", command=self.reset)
		self.reset_preview.reset_button.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="w")

		# Preview button
		self.reset_preview.preview_button = ttk.Button(self.reset_preview, text="Preview", command=self.preview)
		self.reset_preview.preview_button.grid(row=0, column=1, columnspan=1, padx=0, pady=10, sticky="e")

		# Ok/Cancel frame
		self.ok_cancel = tk.Frame(self)
		self.ok_cancel.grid(row=99, column=1, columnspan=2, sticky="e")

		# Ok button
		self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Ok", command=self.ok, default="active")
		self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=0, pady=5, sticky="w")

		# Cancel button
		self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.destroy)
		self.ok_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=10, pady=10, sticky="e")


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
				if sc4mp_config["SC4"]["use_steam_browser_protocol"] in [0, 1]:
					update_config_value("SC4", "use_steam_browser_protocol", (1 if is_steam_sc4(Path(data)) else 0))
			if key == "res":
				if data.lower().startswith("auto"):
					resw = 0
					resh = 0
				else:
					res = data.split(' ')[0]
					resw, resh = res.split('x')
				update_config_value("SC4", "resw", resw)
				update_config_value("SC4", "resh", resh)
			else:
				update_config_value("SC4", key, data)
		

	def ok(self):
		
		self.update()
		sc4mp_config.update()
		self.destroy()


	def reset(self):
		
		if messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning"):
			self.destroy()
			sc4mp_config.data.pop("SC4")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS, error_callback=show_error, update_constants_callback=update_config_constants).data
			self.__init__()


	def preview(self):
		

		# Hide the settings window and main ui
		self.withdraw()
		sc4mp_ui.withdraw()

		# Backup the current config data
		config_data_backup = sc4mp_config["SC4"].copy()

		# Update the config
		self.update()

		# Load the game
		try:

			# Check if a path to SimCity 4 can be found, prompt for a custom path if needed
			while get_sc4_path() == None:
				show_warning('No SimCity 4 installation found. \n\nPlease provide the correct installation path.')
				path = filedialog.askdirectory(parent=sc4mp_ui)
				if len(path) > 0:
					sc4mp_config["SC4"]["game_path"] = path
					self.path_frame.entry.delete(0, 'end')
					self.path_frame.entry.insert(0, path)
				else:
					break
			
			# Load the game if a path to SimCity 4 can be found
			if get_sc4_path() != None:

				# Informational dialog
				if not messagebox.askokcancel(title=SC4MP_TITLE, message='You are about to launch SimCity 4 in preview mode.\n\nThe purpose of preview mode is to test your SC4 launch configuration before joining a server. Any cities you build in preview mode will NOT be saved.\n\nOnce the game exits, the SC4 settings window will reappear. If the game does not launch, your SC4 settings are invalid.', icon="info"):
					raise ClientException("Operation cancelled by user.")
			
				# Purge plugins and regions
				purge_directory(Path(SC4MP_LAUNCHPATH) / "Plugins")
				purge_directory(Path(SC4MP_LAUNCHPATH) / "Regions")
				
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
			show_error(f"An error occurred while launching the game in preview mode.\n\n{e}")

		# Restore the old config data
		sc4mp_config["SC4"] = config_data_backup

		# Show and lift the main ui and settings ui once the game has shutdown
		sc4mp_ui.deiconify()
		sc4mp_ui.lift()
		self.deiconify()
		self.lift()


class HostUI(tk.Toplevel):


	def __init__(self):
		

		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

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
		

		#TODO

		return
	

	def config(self):
		

		#TODO

		return
	

	def files(self):
		

		#TODO

		return
	

	def new(self):
		

		#TODO

		return


	def ok(self):
		

		path = Path("_Servers") / self.list_box_variable.get()[self.list_box.curselection()[0]]

		start_server(path)

		self.destroy()


class DirectConnectUI(tk.Toplevel):


	def __init__(self):
		
		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.connect())
		self.bind("<Escape>", lambda event:self.destroy())
		self.bind("<Up>", lambda event:self.host_entry.focus())
		self.bind("<Down>", lambda event:self.port_entry.focus())

		# Host Label
		self.host_label = ttk.Label(self, text="Host")
		self.host_label.grid(row=0, column=0, columnspan=1, padx=10, pady=20)

		# Host Entry
		self.host_entry = ttk.Entry(self, width=43)
		self.host_entry.insert(0, sc4mp_config["GENERAL"]["default_host"])
		self.host_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=20, sticky="w")
		self.host_entry.focus()

		# Port Label
		self.port_label = ttk.Label(self, text="Port")
		self.port_label.grid(row=1, column=0, columnspan=1, padx=10, pady=0)

		# Port Entry
		self.port_entry = ttk.Entry(self, width=5)
		self.port_entry.insert(0, sc4mp_config["GENERAL"]["default_port"])
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
				#raise ClientException("Invalid host")
			try:
				port = int(port)
			except Exception:
				port = SC4MP_PORT
				#raise ClientException("Invalid port")
			ServerLoaderUI(Server(host, port))
			self.destroy()
		except Exception as e:
			show_error(f"An unexpected error occured while starting the server loader thread.\n\n{e}")


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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.cancel())

		# Password label
		self.password_label = ttk.Label(self, text="Password")
		self.password_label.grid(row=0, column=0, columnspan=1, padx=10, pady=20)

		# Password entry
		self.password_entry = ttk.Entry(self, width=38)
		#self.password_entry.insert(0, sc4mp_config["GENERAL"]["default_host"])
		self.password_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=20, sticky="w")
		self.password_entry.config(show="*")
		self.password_entry.focus()
		#try:
		#	self.password_entry.insert(0, sc4mp_servers_database[self.server_loader.server.server_id]["password"])
		#except Exception:
		#	pass

		# OK/Cancel frame
		self.ok_cancel = tk.Frame(self)
		self.ok_cancel.grid(row=1, column=3, sticky="e")

		# OK button
		self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Ok", command=self.ok, default="active")
		self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=(3,0), pady=5, sticky="w")

		# Guest button
		#if True:
		#	self.ok_cancel.guest_button = ttk.Button(self.ok_cancel, text="Guest", command=self.ok)
		#	self.ok_cancel.guest_button.grid(row=0, column=0, columnspan=1, padx=(10,0), pady=5, sticky="w")

		# Cancel button
		self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.cancel)
		self.ok_cancel.cancel_button.grid(row=0, column=2, columnspan=1, padx=(10,7), pady=5, sticky="e")

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
				if not messagebox.askokcancel(self.server_loader.server.server_name, "You are about to join the server as a guest.\n\nAny cities you build will NOT be saved.", icon="info"):
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


class AboutUI(tk.Toplevel):


	def __init__(self):
		

		#print("Initializing...")

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
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

		# Image
		self.canvas = tk.Canvas(self, width=256, height=256)
		self.canvas.image = tk.PhotoImage(file=get_sc4mp_path("icon.png"))
		self.canvas.create_image(128, 128, anchor="center", image=self.canvas.image)    
		self.canvas.grid(row=0, column=0, rowspan=5, columnspan=1, padx=10, pady=(20,0), sticky="n")

		# Title label 1
		self.title_label_1 = ttk.Label(self, text="Title:")
		self.title_label_1.grid(row=0, column=1, columnspan=1, padx=10, pady=(20,5), sticky="e")

		# Title label 2
		self.title_label_2 = ttk.Label(self, text=SC4MP_TITLE)
		self.title_label_2.grid(row=0, column=2, columnspan=1, padx=10, pady=(20,5), sticky="w")

		# Author label 1
		self.author_label_1 = ttk.Label(self, text="Author:")
		self.author_label_1.grid(row=1, column=1, columnspan=1, padx=10, pady=5, sticky="e")

		# Author label 2
		self.author_label_2 = tk.Label(self, text=SC4MP_AUTHOR_NAME, fg="blue", cursor="hand2") #, font=font.Font(underline=True))
		self.author_label_2.grid(row=1, column=2, columnspan=1, padx=10, pady=5, sticky="w")
		self.author_label_2.bind("<Button-1>", lambda e:webbrowser.open_new_tab(SC4MP_CONTRIBUTORS_URL))

		# Website label 1
		self.website_label_1 = ttk.Label(self, text="Website:")
		self.website_label_1.grid(row=2, column=1, columnspan=1, padx=10, pady=5, sticky="e")

		# Website label 2
		self.website_label_2 = tk.Label(self, text=SC4MP_WEBSITE_NAME, fg="blue", cursor="hand2")
		self.website_label_2.grid(row=2, column=2, columnspan=1, padx=10, pady=5, sticky="w")
		self.website_label_2.bind("<Button-1>", lambda e:webbrowser.open_new_tab(SC4MP_URL))

		# License label 1
		self.license_label_1 = ttk.Label(self, text="License:")
		self.license_label_1.grid(row=3, column=1, columnspan=1, padx=10, pady=(5,80), sticky="e")

		# License label 2
		self.license_label_2 = tk.Label(self, text=SC4MP_LICENSE_NAME, fg="blue", cursor="hand2")
		self.license_label_2.grid(row=3, column=2, columnspan=1, padx=10, pady=(5,80), sticky="w")
		self.license_label_2.bind("<Button-1>", lambda e:startfile("License.txt"))

		# Ok button
		self.ok_button = ttk.Button(self, text="Ok", command=self.ok, default="active")
		self.ok_button.grid(row=4, column=2, columnspan=1, padx=0, pady=5, sticky="se")


	def ok(self):
		
		self.destroy()


class ServerListUI(tk.Frame):
	"""ServerList UI wrapper.

	Arguments:
		TODO

	Returns:
		TODO
	"""


	def __init__(self, root):
		


		#print("Initializing...")


		# Parameters

		self.root = root


		# Init

		super().__init__(self.root)


		# Geometry

		self.grid()


		# Key bindings

		self.root.bind("<Return>", lambda event: self.connect())
		self.root.bind("<Up>", lambda event:self.focus_tree())
		self.root.bind("<Down>", lambda event:self.focus_tree())


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
		#self.label['text'] = 'Loading...' #'To get started, select a server below and click "Connect."' #"Loading server list..."


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
			self.tree.heading(column_id, text=column_name, command=lambda column_name=column_name: self.handle_header_click(column_name))

		#self.tree['show'] = 'headings'
		self.tree['displaycolumns'] = ("#1", "#2", "#3", "#4", "#5")

		# self.tree.bind("<Double-1>", self.handle_double_click) #lambda event: self.connect())
		self.tree.bind("<Button-1>", self.handle_single_click)

		self.tree.sort = "Rank"
		self.tree.reverse_sort = False

		self.tree.tag_configure("strike", font=tkfont.Font(family="Segoe UI", size=9, weight="normal", overstrike=1))
		self.tree.tag_configure("red", foreground="red")

		self.tree.focus_set()

		self.tree.pack(side="left")

		self.tree.last_click = 0
		self.tree.last_click_coords = (0,0)


		# Scrollbar

		self.scrollbar = ttk.Scrollbar(self.frame, orient ="vertical", command = self.tree.yview)
		self.scrollbar.pack(side="right", fill="y")
		self.tree.configure(yscrollcommand=self.scrollbar.set)


		# Server info frame

		self.server_info = tk.Frame(self, width=540, height=120)
		self.server_info.grid(row=3, column=0, columnspan=2, padx=20, pady=0, sticky="nw")
		self.server_info.grid_propagate(0)


		# Description label

		self.description_label = ttk.Label(self.server_info, wraplength=self.server_info["width"])
		self.description_label.grid(row=0, column=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="nw")
		self.description_label['text'] = ""


		# URL label

		self.url_label = tk.Label(self.server_info, fg="blue", cursor="hand2")
		self.url_label.grid(row=1, column=0, columnspan=1, padx=0, pady=5, sticky="nw")
		self.url_label['text'] = ""
		self.url_label.bind("<Button-1>", lambda e:self.open_server_url())


		# Combo box

		self.combo_box = ttk.Combobox(self, width=23)
		self.combo_box["values"] = ("category: All", "category: Official", "category: Public", "category: Private", "category: History") #"category: Bookmarked" "category: Online"

		self.combo_box.PLACEHOLDER_TEXT = "Search/Filter servers"

		def on_focus_in(event):
			if self.combo_box.get() == self.combo_box.PLACEHOLDER_TEXT:
				self.combo_box.delete(0, tk.END)  # Clear placeholder when clicked
				self.combo_box.configure(foreground="black")

		def on_focus_out(event):
			if self.combo_box.get() == "":
				self.combo_box.set(self.combo_box.PLACEHOLDER_TEXT)  # Restore placeholder if nothing is typed
				self.combo_box.configure(foreground="gray")

		def on_key_release(event):
			if self.combo_box.get() == self.combo_box.PLACEHOLDER_TEXT:
				self.combo_box.delete(0, tk.END)
				self.combo_box.configure(foreground="black")

		self.combo_box.bind("<FocusIn>", on_focus_in)
		self.combo_box.bind("<FocusOut>", on_focus_out)
		self.combo_box.bind("<KeyRelease>", on_key_release)

		if sc4mp_config["GENERAL"]["server_browser_filter"]:
			self.combo_box.insert(0, sc4mp_config["GENERAL"]["server_browser_filter"])
			self.combo_box.configure(foreground="black")
		else:
			self.combo_box.insert(0, self.combo_box.PLACEHOLDER_TEXT)
			self.combo_box.configure(foreground="gray")
		
		self.combo_box.grid(row=3, column=2, rowspan=1, columnspan=1, padx=(0,16), pady=(5,10), sticky="ne")
		

		# Address label

		self.address_label = tk.Label(self, fg="gray")
		self.address_label.grid(row=4, column=0, columnspan=1, padx=20, pady=10, sticky="sw")
		self.address_label['text'] = ""


		# Server options frame

		self.server_options = tk.Frame(self)
		self.server_options.grid(row=4, column=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="se")


		# Details button

		self.details_button = ttk.Button(self.server_options, text="Details", command=self.details)
		self.details_button['state'] = tk.DISABLED
		self.details_button.grid(row=0, column=99, columnspan=1, padx=(15,20), pady=10, sticky="se")


		# Refresh / connect frame

		self.refresh_connect = tk.Frame(self)
		self.refresh_connect.grid(row=4, column=2, rowspan=1, columnspan=1, padx=0, pady=0, sticky="se")


		# Refresh button

		self.refresh_button = ttk.Button(self.refresh_connect, text="Refresh", command=self.root.refresh)
		self.refresh_button.grid(row=0, column=0, columnspan=1, padx=11, pady=10, sticky="se")


		# Connect button

		self.connect_button = ttk.Button(self.refresh_connect, text="Connect", command=self.connect, default="active")
		self.connect_button['state'] = tk.DISABLED
		self.connect_button.grid(row=0, column=1, columnspan=1, padx=(0,15), pady=10, sticky="se")


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

		if time.time() - self.tree.last_click < 500 and math.dist((event.x, event.y), self.tree.last_click_coords) < 1:
			self.handle_double_click(event)
		else:
			region = self.tree.identify_region(event.x, event.y)
			if region == "separator":
				return "break"
			else:
				self.tree.last_click = time.time()
				self.tree.last_click_coords = (event.x, event.y)
			
		

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
		#self.worker.sort = True


	def focus_tree(self):
		
		try:
			self.tree.focus_set()
			children = self.tree.get_children()
			if self.tree.focus() == "" and len(children) > 0:
				self.tree.focus(children[0])
				self.tree.selection_add([children[0]])
		except Exception as e:
			show_error("Error setting focus on server list UI.", no_ui=True) # Method not all that important so we'll just toss an error in the console and call it a day 


	def details(self):

		ServerDetailsUI(self.worker.servers[self.tree.focus()])


	def connect(self):
		
		print('"Connect"')
		server_id = self.tree.focus()
		if server_id == "":
			return
		server = self.worker.servers[server_id]
		if not ("Official" in server.categories or "History" in server.categories or sc4mp_config["GENERAL"]["ignore_third_party_server_warnings"]):
			if not messagebox.askokcancel(title=SC4MP_TITLE, message="You are about to join a third-party server.\n\nThe SimCity 4 Multiplayer Project is not responsible for content downloaded from third-party servers. Only join third-party servers you trust.", icon="warning"):
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

		if sc4mp_config["GENERAL"]["server_browser_filter"] != server_browser_filter:
			sc4mp_config["GENERAL"]["server_browser_filter"] = server_browser_filter
			sc4mp_config.update()

		return super().destroy()


class ServerLoaderUI(tk.Toplevel):
	


	def __init__(self, server):
		

		#print("Initializing...")

		# Init
		super().__init__()

		# Loading Background
		if sc4mp_has_pil and sc4mp_config["GENERAL"]["use_fullscreen_background"]:
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
		self.bind("<Escape>", lambda event:self.destroy())

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
		self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=(10,5))
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
		self.attributes("-fullscreen", sc4mp_config["SC4"]["fullscreen"])

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
		#self.after(100, self.loop)


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

			s = socket.socket()
			s.settimeout(10)
			s.connect((self.server.host, self.server.port))
		
			s.send(b"background")

			destination: Path = SC4MP_LAUNCHPATH / "_Temp" / "background.png"

			if destination.exists():
				os.unlink(destination)

			with open(destination, "wb") as file:
				while True:
					data = s.recv(SC4MP_BUFFER_SIZE)
					if not data:
						break
					if self.destroyed:
						return
					file.write(data)

			if destination.stat().st_size > 0:

				self.server_image = Image.open(destination)

				self.reload_image()

			return

		#except (UnidentifiedImageError, PermissionError):

		#	pass

		except Exception as e:

			show_error(f"An error occurred while fetching server background.\n\n{e}", no_ui=True)

			self.retry_fetch_background()


	def retry_fetch_background(self):

		if self.destroyed:
			return

		self.server_image = None
		self.after(3000, lambda: th.Thread(target=self.fetch_background, daemon=True).start())


	# def loop(self):

	# 	if sc4mp_ui.winfo_viewable():
	# 		self.destroy()
	# 	#elif process_exists("simcity 4.exe"):
	# 	#	self.destroy()
	# 		#self.after(10000, self.destroy)
	# 	elif not self.destroyed:
	# 		self.after(100, self.loop)

	
	def destroy(self):

		self.destroyed = True

		return super().destroy()


class ServerDetailsUI(tk.Toplevel):


	def __init__(self, server: Server):
		"""TODO"""


		#print("Initializing...")


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

		self.bind("<Return>", lambda event:self.destroy())
		self.bind("<Escape>", lambda event:self.destroy())
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
		invite_link_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10,0))

		invite_link_entry = ttk.Entry(inner_frame, width=40)
		invite_link_entry.insert(0, invite_link)
		invite_link_entry.after(100, lambda: self.reset_entrybox(invite_link_entry, invite_link))
		#invite_link_entry.configure(state="disabled")
		invite_link_entry.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=0)

		invite_link_copy_button = ttk.Button(inner_frame, text="Copy", command=lambda: copy_to_clipboard(invite_link))
		invite_link_copy_button.grid(row=1, column=2)

		#server_id_label = ttk.Label(inner_frame, text="ID", font=("Segoe UI", 9, "bold"))
		#server_id_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(10,0))

		#server_id_entry = ttk.Entry(inner_frame, width=40)
		#server_id_entry.insert(0, self.server.server_id)
		#server_id_entry.after(100, lambda: self.reset_entrybox(server_id_entry, self.server.server_id))
		##server_id_entry.configure(state="disabled")
		#server_id_entry.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=0)

		#server_id_copy_button = ttk.Button(inner_frame, text="Copy", command=lambda: copy_to_clipboard(self.server.server_id))
		#server_id_copy_button.grid(row=3, column=2)

		left_frame = ttk.Frame(inner_frame)
		left_frame.grid(row=10, column=0, pady=20, sticky="nw")

		version_label_1 = ttk.Label(left_frame, text="Version", font=("Segoe UI", 9, "bold"))
		version_label_1.grid(row=1, column=0, sticky="w", padx=10, pady=(10,0))

		version_label_2 = ttk.Label(left_frame, text=self.server.server_version, foreground=("red" if unformat_version(self.server.server_version)[:2] != unformat_version(SC4MP_VERSION)[:2] else "black"))
		version_label_2.grid(row=2, column=0, sticky="w", padx=10, pady=0)

		password_enabled_label_1 = ttk.Label(left_frame, text="Public", font=("Segoe UI", 9, "bold"))
		password_enabled_label_1.grid(row=3, column=0, sticky="w", padx=10, pady=(10,0))

		password_enabled_label_2 = ttk.Label(left_frame, text=("No" if self.server.password_enabled else "Yes"), foreground=("red" if self.server.password_enabled else "green"))
		password_enabled_label_2.grid(row=4, column=0, sticky="w", padx=10, pady=0)

		if self.server.password_enabled:

			private_label_1 = ttk.Label(left_frame, text="Guests", font=("Segoe UI", 9, "bold"))
			private_label_1.grid(row=5, column=0, sticky="w", padx=10, pady=(10,0))

			private_label_2 = ttk.Label(left_frame, text=("No" if self.server.private else "Yes"), foreground=("red" if self.server.private else "green"))
			private_label_2.grid(row=6, column=0, sticky="w", padx=10, pady=0)
		
		right_frame = ttk.Frame(inner_frame)
		right_frame.grid(row=10, column=1, columnspan=2, pady=20, sticky="nw")

		custom_plugins_label_1 = ttk.Label(right_frame, text="Custom plugins", font=("Segoe UI", 9, "bold"))
		custom_plugins_label_1.grid(row=1, column=0, sticky="w", padx=10, pady=(10,0))

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
			claim_duration_label_1.grid(row=3, column=0, sticky="w", padx=10, pady=(10,0))

			claim_duration_label_2 = ttk.Label(right_frame, text=claim_duration, foreground=("green" if claim_duration == "Forever" else "black"))
			claim_duration_label_2.grid(row=4, column=0, sticky="w", padx=10, pady=0)

			claim_limit_label_1 = ttk.Label(right_frame, text="Claim limit", font=("Segoe UI", 9, "bold"))
			claim_limit_label_1.grid(row=5, column=0, sticky="w", padx=10, pady=(10,0))

			claim_limit_label_2 = ttk.Label(right_frame, text=max_region_claims, foreground=("green" if max_region_claims == "None" else "black"))
			claim_limit_label_2.grid(row=6, column=0, sticky="w", padx=10, pady=0)

			if not godmode_filter:

				godmode_claims_label_1 = ttk.Label(right_frame, text="Godmode claims", font=("Segoe UI", 9, "bold"))
				godmode_claims_label_1.grid(row=7, column=0, sticky="w", padx=10, pady=(10,0))

				godmode_claims_label_2 = ttk.Label(right_frame, text=("No" if godmode_filter else "Yes"), foreground=("red" if godmode_filter else "green"))
				godmode_claims_label_2.grid(row=8, column=0, sticky="w", padx=10, pady=0)

		except AttributeError:

			pass

		#options_frame = tk.Frame(self.info_frame)
		#options_frame.grid(row=1, column=0, sticky="sw")

		#copy_link_button = ttk.Button(options_frame, text="Copy link", command=lambda: copy_to_clipboard(f"sc4mp://{self.server.host}:{self.server.port}"))
		#copy_link_button.grid(row=0, column=0, padx=20, pady=10)

		#invite_link_label = ttk.Label(self.info_frame, text="Link: ")
		#invite_link_label.grid(row=1, column=0)

		#invite_link_entry = ttk.Entry(self.info_frame)
		#invite_link_entry.insert(0, f"sc4mp://{self.server.host}:{self.server.port}")
		#invite_link_entry.grid(row=1, column=1)

		#self.info_frame.rules_frame: ttk.LabelFrame = ttk.Labelframe(self.info_frame, text="Rules")
		#self.info_frame.rules_frame.grid(row=0, column=0)

		#self.info_frame.rules_frame.label = ttk.Label(self.info_frame.rules_frame, text="TEST")
		#self.info_frame.rules_frame.label.grid(row=0, column=0)

		self.notebook.add(self.info_frame, text="Info")


		# Ok button

		self.ok_button = ttk.Button(self, text="Ok", command=self.destroy, default="active")
		self.ok_button.grid(row=1, column=0, padx=10, pady=5, sticky="se")


		# Create notebook frames asynchronously

		th.Thread(target=self.create_notebook_frames).start()

		#self.chain_functions([
		#	self.create_mayors_frame, 
		#	self.create_cities_frame, 
		#	lambda: th.Thread(target=self.create_files_frame).start()
		#])


		# Update window size periodically

		self.after(100, self.update_window_size)
		

		# Select tab from last server detail view
		self.after(200, self.select_last_tab)


	def select_last_tab(self):

		try:
			self.notebook.select(globals().get("sc4mp_server_details_ui_last_tab_index", 0))
		except Exception as e:
			pass


	def on_notebook_tab_changed(self, function: function):

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


		#function()

		#self.notebook.unbind("<<NotebookTabChanged>>")


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
				#current_selection = current_focus.selection()
				#if len(current_selection) > 0:
				#	current_selection = current_selection[0]
				#	if current_selection not in current_focus.get_children("") or right:
				#		return
					#if len(current_focus.get_children(current_selection)) > 0:
						#right = not left
						#expanded = current_focus.item(current_selection, "open")
						#collapsed = not expanded
						#if collapsed and right or expanded and left:
					#	return

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
			if not self.winfo_exists(): #self.destroyed:
				return

			# Update the UI to make sure `winfo` calls are correct
			sc4mp_ui.update()

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

			#print(f"Resized to {new_window_width}x{new_window_height}.")

			self.after(1, self.update_window_size)

		except Exception as e:

			show_error(e, no_ui=True)


	def reset_entrybox(self, entrybox: ttk.Entry, text: str):

		try:

			if entrybox.get() != text:
				entrybox.delete(0, "end")
				entrybox.insert(0, text)

			self.after(1, lambda: self.reset_entrybox(entrybox, text))

		except Exception as e:

			show_error(e, no_ui=True)


	def destroy(self):

		global sc4mp_server_details_ui_last_tab_index

		try:
			sc4mp_server_details_ui_last_tab_index = self.notebook.index(self.notebook.select())
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

			show_error(f"An error occurred while creating notebook frames.\n\n{e}") #, no_ui=True)


	def create_mayors_frame(self):


		regions_directory: Path = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server.server_id / "Regions"
		
		if not regions_directory.exists():
			return

		mayors = {}
		for region in os.listdir(regions_directory):
			region_database: dict = self.load_json(regions_directory / region / "_Database" / "region.json")
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

		#self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.on_notebook_tab_changed(self.collapse_mayors_treeview))

		#self.after(200, lambda: center_window(self))


	def collapse_mayors_treeview(self):

		self.mayors_frame.tree["displaycolumns"] = ["#7", "#8"]
		self.mayors_frame.button.configure(command=self.expand_mayors_treeview, text="Expand")

		#self.after(200, lambda: center_window(self))


	def create_cities_frame(self):
	

		regions_directory: Path = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server.server_id / "Regions"
		
		if not regions_directory.exists():
			return

		cities = {}
		for region in os.listdir(regions_directory):

			region_database: dict = self.load_json(regions_directory / region / "_Database" / "region.json")

			for coords, entry in region_database.items():

				if entry is not None:

					city_id = f"{region.replace(' ', '_')}_{coords}"

					city_name = entry.get("city_name", "New City")
					mayor_name = entry.get("mayor_name", "Defacto")

					if len(mayor_name) < 1:
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
			#self.files_frame.tree.tag_configure('red', foreground='red')

			files = {}

			for request in ["Plugins", "Regions"]:

				s = socket.socket()
				s.settimeout(10)
				s.connect((self.server.host, self.server.port))

				if not self.server.private:
					s.send(request.lower().encode())
				else:
					s.send(f"{request.lower()} {SC4MP_VERSION} {self.server.user_id} {self.server.password}".encode())

				file_table = recv_json(s)

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
					cached_file = SC4MP_LAUNCHPATH / "_Cache" / md5

					if cached_file.exists():
						download_size -= cached_file.stat().st_size

					entry[d] = [
						download_size
					]

			#update_json("test.json", files)

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

				#tree.item(parent, values=[format_download_size(download_size)])

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


class StatisticsTreeUI(tk.Frame):


	def __init__(self, *args, columns=[], formats=[], data={}, sort=-1, reverse=True, **kwargs):
		
		
		super().__init__(*args, **kwargs)

		self.columns = columns
		self.formats = formats
		self.data = data
		self.sort = sort
		self.reverse = reverse
		self.query = ""


		# Tree frame

		self.tree_frame = tk.Frame(self)
		self.tree_frame.grid(row=0, column=0, columnspan=2)


		# Tree canvas

		self.tree_canvas = tk.Canvas(self.tree_frame, width=350, height=323, bg="white", highlightthickness=0)
		self.tree_canvas.pack(side="left")


		# Tree

		column_ids = []
		for column in columns:
			column_ids.append(column[0])
		column_ids = tuple(column_ids[1:])

		self.tree = ttk.Treeview(self.tree_canvas, columns=column_ids, selectmode="browse", height=15)
		self.tree.bind("<<TreeviewOpen>>", self.on_item_expand)
		self.tree.bind("<<TreeviewClose>>", self.on_item_expand)
		self.tree.bind("<Double-1>", self.on_click)
		self.tree.bind("<Button-1>", self.on_click)

		for column in columns:
			column_id = column[0]
			column_name = column[1]
			column_width = column[2]
			column_anchor = column[3]
			self.tree.column(column_id, width=column_width, anchor=column_anchor, stretch=False)
			self.tree.heading(column_id, text=column_name, command=lambda index=columns.index(column): self.on_header_click(index))

		self.sort_data()
		self.populate_treeview()

		#self.master.configure(width=sum([column[2] for column in columns]))
		self.tree.pack()
		self.tree_canvas.create_window(0, 0, window=self.tree, anchor="nw")

		self.after(100, self.filter_treeview)


		# Scrollbar

		self.scrollbar = ttk.Scrollbar(self.tree_frame, orient ="vertical", command=self.tree.yview)
		self.scrollbar.pack(side="right", fill="y")
		self.tree.configure(yscrollcommand=self.scrollbar.set)


		# Button

		self.button = ttk.Button(self, text="Button")
		self.button.grid(row=1, column=0, sticky="nw", padx=(0,10), pady=(10,0))


		# Entry

		self.entry = ttk.Entry(self)
		self.entry.grid(row=1, column=1, sticky="ne", padx=(10,15), pady=(12, 0))


	def sort_data(self):

		self.data = {key:entry for key, entry in sorted(self.data.items(), key=lambda item: item[1][self.sort], reverse=self.reverse)}


	def populate_treeview(self, parent=""):

		# Get all child items of the parent item
		children: list[str] = list(self.tree.get_children(parent))

		# Set index for insertion
		index = 0

		# Loop through each item, format it, and add it to the tree
		for item, entry in self.data.items():

			# Generate search field for query
			field = ""
			for value in entry:
				if type(value) is str:
					field += value

			# Format the data
			entry = entry.copy()
			for i in range(len(entry)):
				try:
					entry[i] = self.formats[i](entry[i])
				except Exception as e:
					entry[i] = f"ERROR: {e}"

			# Divide the entry into text (column #0) and values (columns #1)
			text: str = entry[0]
			values = entry[1:]

			# If item satisfies the query
			if len(self.query) < 1 or self.query.lower() in field.lower():

				# If item in tree
				if item not in children:

					# Insert the item into the tree
					self.tree.insert("", index, id=item, text=text, values=values)
					children.insert(index, item)

				# Increment the index for insertion
				index += 1

			# If item does not satisfy query
			else:

				# If item in tree
				if item in children:

					# Remove the item
					self.tree.delete(item)
					children.remove(item)


	def filter_treeview(self):

		try:

			query = self.entry.get()

			if query != self.query:
				
				self.query = query

				self.populate_treeview()

		except Exception as e:

			show_error(f"An error occurred while filtering.\n\n{e}", no_ui=True)

			#self.query = query

			# Cache the tree structure if not already cached
			#if not hasattr(self, "original_tree"):
			#	self.original_tree = {}
			#	self.original_indices = {}

			#	def cache_tree_structure(parent):
			#		"""Recursively cache the tree structure and indices."""
			#		children = tree.get_children(parent)
			#		self.original_tree[parent] = children
			#		self.original_indices[parent] = {child: idx for idx, child in enumerate(children)}
			#		for child in children:
			#			cache_tree_structure(child)
			#
			#	cache_tree_structure("")

			#def recursive_filter(parent, query):
			#	"""Recursively filter the items in the tree."""
			#	match_found = False  # Tracks if any child matches the query

			#	visible_children = []

			#	for child in self.original_tree.get(parent, []):
			#		# Get the text of the current item
			#		item_text = tree.item(child, "text").lower()
			#		child_match = query in item_text if query else True  # Match all if query is empty

			#		# Recursively filter the children of this child
			#		child_visible = recursive_filter(child, query)

			#		# Show this item if it or any of its descendants match
			#		if child_match or child_visible:
			#			visible_children.append(child)
			#			match_found = True
			#		else:
			#			if child in tree.get_children(parent):
			#				tree.detach(child)  # Detach the item

				# Reattach children in original order
			#	for child in visible_children:
			#		tree.reattach(child, parent, "end")

			#	return match_found

			#if not query:
				# Reset the tree to its original structure
			#	def reset_tree(parent):
			#		children = self.original_tree.get(parent, [])
			#		for child in children:
			#			if child not in tree.get_children(parent):
			#				tree.reattach(child, parent, "end")
			#			reset_tree(child)

			#	reset_tree("")
			#else:
			#	# Start recursive filtering from the root
			#	recursive_filter("", query)

		# Continue filtering periodically
		self.after(100, self.filter_treeview)
		

	def on_click(self, event):
		
		region = self.tree.identify_region(event.x, event.y)
		if region == "separator":
			return "break"


	def on_item_expand(self, event):

		th.Thread(target=self.adjust_tree_column_widths).start()


	def on_header_click(self, index):

		# Get current selection (to be reselected after sorting)
		selection = self.tree.selection()

		# Set sort mode
		if index == self.sort:
			self.reverse = not self.reverse
		else:
			if self.columns[index][1] in ["Name", "Mayor"]:
				self.reverse = False
			else:
				self.reverse = True
		self.sort = index

		# Clear the tree
		for item in self.tree.get_children(""):
			self.tree.delete(item)

		# Sort the data
		self.sort_data()

		# Populate the tree
		self.populate_treeview()

		# Re-add the selection (if any)
		if len(selection) > 0:
			self.tree.selection_add(selection)
			self.tree.focus(selection[0])	


	def adjust_tree_column_widths(self):
		"""
		Adjusts column widths on the TreeView to fit contents.
		
		Trash code written by Chat-GPT
		"""

		try:

			time.sleep(.2) # Give time for the item to actually expand

			tree = self.tree

			# Get the style used in the Treeview
			font_name = "TkDefaultFont"
			font = tkfont.nametofont(font_name)
			
			indent = 40  # Default indentation for Treeview items (can be customized)
    
			# Adjust the #0 column (tree column)
			max_width = tree.column("#0", option="width") #font.measure(tree.heading("#0")["text"])  # Start with header width

			def calculate_width(item, level=0):

				nonlocal max_width

				children = tree.get_children(item)

				# Calculate the width of the item's text in the #0 column
				cell_content = tree.item(item, "text")
				item_width = font.measure(cell_content) + (level * indent)
				max_width = max(max_width, item_width)

				# Recursively calculate widths for child items
				if tree.item(item, "open"):
					for child in children:
						calculate_width(child, level + 1)

			# Process root-level items and their children for #0 column
			for root_item in tree.get_children(""):
				calculate_width(root_item)

			# Set the #0 column width to the calculated maximum
			tree.column("#0", width=min(1000, max_width))

			# Adjust other columns
			#for col in tree["columns"]:

			#	max_width = tree.column(col, option="width") #font.measure(col)  # Start with column header width

			#	def calculate_column_width(item, level=0):

			#		nonlocal max_width

			#		# Calculate the width of the current item's content in this column
			#		cell_content = tree.set(item, col)
			#		item_width = font.measure(cell_content)
			#		max_width = max(max_width, item_width)

			#		# Recursively calculate widths for child items
			#		if tree.item(item, "open"):
			#			for child in tree.get_children(item):
			#				calculate_column_width(child, level + 1)

			#	# Process root-level items and their children for each column
			#	for root_item in tree.get_children(""):
			#		calculate_column_width(root_item)

			#	# Set the column width to the calculated maximum
			#	tree.column(col, width=max_width)

		except Exception as e:
	
			show_error(f"Failed to adjust column widths.\n\n{e}", no_ui=True)


	def get_tree_width(self):

		width = self.tree.column("#0", "width")

		for column in self.tree["columns"]:
			try:
				if self.tree.heading(column, "text") != "⠀":
					width += self.tree.column(column, option="width")
			except:
				pass
			
		return width


	def winfo_width(self):

		#print(self.tree_canvas.configure("width"))
		#self.scrollbar.lift()

		tree_width = self.get_tree_width()

		self.tree_canvas.configure(width=tree_width - 2)

		return tree_width + 20
	

	def winfo_height(self):

		return 361


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
		self.geometry(f"400x400+{sc4mp_game_monitor_x}+{sc4mp_game_monitor_y}")
		self.minsize(420, 280)
		self.maxsize(420, 280)
		self.grid()

		# Iconify
		# if sc4mp_config["SC4"]["fullscreen"]:
		# 	self.iconify()

		# Priority
		# self.grab_set()

		# Protocol
		self.protocol("WM_DELETE_WINDOW", self.delete_window)

		# Status frame
		self.status_frame = tk.Frame(self)
		self.status_frame.grid(column=0, row=0, rowspan=1, columnspan=2, padx=0, pady=20, sticky="n")

		# Status label left
		#self.status_frame.left = tk.Label(self.status_frame, text="Status:")
		#self.status_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="w")

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
		self.description_label.grid(row=0, column=0, rowspan=1, columnspan=1, padx=10, pady=(10,0), sticky="nw")
		self.description_label['text'] = ""

		# URL label
		self.url_label = tk.Label(self.server_info, fg="blue", cursor="hand2", background="white")
		self.url_label.grid(row=1, column=0, columnspan=1, padx=10, pady=5, sticky="nw")
		self.url_label['text'] = ""
		self.url_label.bind("<Button-1>", lambda e:webbrowser.open_new_tab(format_url(self.url_label["text"])))

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
		
		if not sc4mp_config["GENERAL"]["allow_game_monitor_exit"]:	
			if sc4mp_allow_game_monitor_exit_if_error:
				try:
					process_exists("simcity 4.exe")
					return
				except Exception:
					pass
		if messagebox.askokcancel(title=SC4MP_TITLE, message="Disconnect from the server?\n\nAll unsaved changes will be lost.", icon="warning"):
			global sc4mp_game_exit_ovveride
			sc4mp_game_exit_ovveride = True
			self.parent.end = True
			self.destroy()

	
	def destroy(self):

		global sc4mp_game_monitor_x, sc4mp_game_monitor_y

		try:
			sc4mp_game_monitor_x = self.winfo_x()
			sc4mp_game_monitor_y = self.winfo_y()
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
		#self.label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

		# Canvas
		self.canvas_frame = tk.Frame(self)
		self.canvas_frame.grid(row=1, column=0, padx=15, pady=0, sticky="nw") #, sticky="ewns")
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
		#self.status_frame = tk.Frame(self)
		#self.status_frame.grid(column=0, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

		# Status label left
		#self.status_frame.left = ttk.Label(self.status_frame, text="Status:")
		#self.status_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="w")

		# Status label right
		#self.status_frame.right = ttk.Label(self.status_frame, text="")
		#self.status_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=10, sticky="w")
		#self.label = self.status_frame.right

		# Ping frame
		#self.ping_frame = tk.Frame(self)
		#self.ping_frame.grid(column=0, row=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

		# Ping label left
		#self.ping_frame.left = ttk.Label(self.ping_frame, text="Ping:")
		#self.ping_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=0, sticky="w")

		# Ping label right
		#self.ping_frame.right = ttk.Label(self.ping_frame, text="")
		#self.ping_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

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

		#VIEWPORT_WIDTH = 408 / WIDTH
		#VIEWPORT_HEIGHT = 408 / HEIGHT

		#if VIEWPORT_WIDTH < 1:
		#	self.canvas_horizontal_scrollbar.set((1 + VIEWPORT_WIDTH) / 2, (1 - VIEWPORT_WIDTH) / 2)
		
		#if VIEWPORT_HEIGHT < 1:
		#	self.canvas_vertical_scrollbar.set((1 + VIEWPORT_HEIGHT) / 2, (1 - VIEWPORT_HEIGHT) / 2)

		LARGE_TILE_COUNT_X = REGION_WIDTH / 4
		LARGE_TILE_COUNT_Y = REGION_HEIGHT / 4

		for y in range(int(-.5 * LARGE_TILE_COUNT_Y), int(.5 * LARGE_TILE_COUNT_Y)):
			for x in range(int(-.5 * LARGE_TILE_COUNT_X), int(.5 * LARGE_TILE_COUNT_X)):
				self.canvas.images[f"{x}_{y}"] = self.canvas.create_image(x*68, y*68, image=self.canvas.LAUNCHER_MAP_TILE_UNCLAIMED_LARGE, anchor="nw")


class GameOverlayUI(tk.Toplevel):
	
	

	def __init__(self, game_monitor_ui, guest=False):
		

		#print("Initializing...")

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
		for state in ["connected", "guest", "not-saved", "refreshed", "refreshing", "saved", "saving"]:
			self.images[state] = tk.PhotoImage(file=get_sc4mp_path(f"overlay-{state}.png"))

		# Canvas
		self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="hand2")
		self.canvas.bind("<Button-1>", self.click)
		if guest:
			self.set_state("guest")	
		else:
			self.set_state("connected")


	def overlay(self):
		
		try:

			if sc4mp_ui.focus_get() is self.game_monitor_ui:

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
		

		#print("Initializing...")

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
		
		#print("Overlaying...")
		try:
			self.overrideredirect(True)
			self.lift()
			self.after(100, self.overlay)
		except Exception as e:
			show_error("Unable to overlay region refresher UI.", no_ui=True)


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
		self.bind("<Escape>", lambda event:self.delete_window())

		# Label
		self.label = ttk.Label(self)
		self.label['text'] = "Loading..."
		self.label.grid(column=0, row=0, columnspan=2, padx=10, pady=(10,5))

		# Progress bar
		self.progress_bar = ttk.Progressbar(
			self,
			orient='horizontal',
			mode='indeterminate',
			length=380,
			maximum=100
		)
		self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=(10,5))
		self.progress_bar.start(2)

		# Small label
		self.label_small = tk.Label(self, fg="gray", font=("Segoe UI", 8), text="Press <ESC> to cancel")
		self.label_small.grid(column=0, row=2, columnspan=2, padx=10, pady=(0,5))

		# Pause underlying thread
		self.pause = False


	def delete_window(self):

		self.pause = True

		choice = messagebox.askyesnocancel(title=SC4MP_TITLE, icon="warning", message="Are you sure you want to continue without updating?")

		if choice is None:
			sys.exit()
		elif choice is True:
			subprocess.Popen([sys.executable, "-skip-update", "-allow-multiple"])
			sys.exit()
		elif choice is False:
			self.pause = False


	def destroy(self):

		super().destroy()

		self.parent.destroy()


class ReleaseNotesUI(tk.Toplevel):
	
	def __init__(self, version: str, title: str, body: str):
	

		#print("Initializing...")

		# Init
		super().__init__()
		self.version = version

		# Title
		self.title(f"Version {version}")

		# Icon
		self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

		# Geometry
		self.geometry('400x400')
		#self.maxsize(420, 375)
		#self.minsize(420, 375)
		self.grid()
		
		# Priority
		self.grab_set()

		# Key bindings
		self.bind("<Return>", lambda event:self.destroy())
		self.bind("<Escape>", lambda event:self.destroy())

		try:

			# Title
			#self.title = ttk.Label(self, text=SC4MP_TITLE, font=("Arial", 16))
			#self.title.grid(row=10, column=0, padx=10, pady=10)

			# Description
			#self.description = ttk.Label(self, text="Thank you for using the SC4MP launcher.")
			#self.description.grid(row=11, column=0, sticky="n", padx=10, pady=10)

			# Release notes label
			self.subtitle = ttk.Label(self, text="Release notes")
			self.subtitle.grid(row=19, column=0, columnspan=99, sticky="w", padx=10, pady=5)

			# Body
			self.body = tk.Frame(self, width=400, height=100, background="white", highlightbackground="gray", highlightthickness=1)
			self.body.grid(row=20, column=0, padx=(10,0), pady=0, sticky="nw")
			self.body.grid_propagate(0)

			# Body title
			self.body.title = ttk.Label(self.body, text=title, wraplength=(int(self.body["width"]) - 20), background="white", font=("Segoe UI", 8, "bold"))
			self.body.title.grid(row=0, column=0, columnspan=99, padx=10, pady=10, sticky="nw")

			# Body text
			lines = body.splitlines()
			if len(lines) > 0 and lines[-1].startswith("**Full Changelog**"):
				lines.pop(-1)
				if len(lines) > 0 and len(lines[-1]) == 0:
					lines.pop(-1)
			if len(lines) < 1:
				ttk.Label(self.body, text="No description provided.", background="white", font=("Segoe UI", 8, "italic")).grid(row=1, column=0, columnspan=99, padx=10, pady=2, sticky="nw")
			else:
				for line_number in range(len(lines)):
					line = lines[line_number]
					bold = "**" in line
					bulleted = line.startswith("- ")
					for sequence in ["**", "- "]:
						line = line.replace(sequence, "")
					if bulleted:
						ttk.Label(self.body, text="\u2022", background="white").grid(row=line_number + 1, column=0, columnspan=1, padx=(10,0), pady=2, sticky ="nw")
						ttk.Label(self.body, text=line, wraplength=(int(self.body["width"]) - 40), background="white").grid(row=line_number + 1, column=1, columnspan=1, padx=10, pady=2, sticky="nw")
					else:
						ttk.Label(self.body, text=line, wraplength=(int(self.body["width"]) - 20), background="white").grid(row=line_number + 1, column=0, columnspan=99, padx=10, pady=2, sticky="nw")

			# Body link
			self.body.link = ttk.Label(self.body, text="View all releases...", foreground="blue", background="white", cursor="hand2")
			self.body.link.grid(row=99, column=0, columnspan=99, padx=10, pady=10, sticky="nw")
			self.body.link.bind("<Button-1>", lambda e:webbrowser.open_new_tab(SC4MP_RELEASES_URL))

			# Resize body and window to fit content
			sc4mp_ui.update()
			body_height = self.body.link.winfo_y() + 30
			window_height = body_height + 75
			self.body.configure(height=body_height)
			self.maxsize(420, window_height)
			self.minsize(420, window_height)

			# Scrollbar
			#scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.body.yview)
			#self.body.configure(yscrollcommand=self.scrollbar.set)
			#self.scrollbar.grid(row=20, column=1, padx=0, pady=10)

			# Ok button
			self.ok_button = ttk.Button(self, text="Ok", command=self.destroy, default="active")
			self.ok_button.grid(row=99, column=0, columnspan=99, padx=0, pady=10, sticky="s")

			# Center window
			center_window(self)

		except Exception as e:

			self.destroy()

			raise e


	def destroy(self):

		sc4mp_config["GENERAL"]["release_notes_version"] = self.version

		sc4mp_config.update()

		return super().destroy()


# Exceptions

class ClientException(Exception):
	


	def __init__(self, message, *args):
		
		super().__init__(args)
		self.message = message
	

	def __str__(self):
		
		return self.message


# Logger

class Logger:
	
	

	def __init__(self):
		
		self.terminal = sys.stdout
		self.log = Path(SC4MP_LOG_PATH)
		self.log.unlink(missing_ok=True)


	def write(self, message):
		

		output = message

		if message != "\n":

			# Timestamp
			timestamp = datetime.now().strftime("[%H:%M:%S] ")

			# Label
			label = "[SC4MP/" + th.current_thread().getName() + "] "
			for item in inspect.stack()[1:]:
				try:
					label += "(" + item[0].f_locals["self"].__class__.__name__ + ") "
					break
				except Exception:
					pass
			

			# Type and color
			type = "[INFO] "
			color = '\033[90m '
			TYPES_COLORS = [
				("[INFO] ", '\033[90m '), #'\033[94m '
				("[PROMPT]", '\033[01m '),
				("[WARNING] ", '\033[93m '),
				("[ERROR] ", '\033[91m '),
				("[FATAL] ", '\033[91m ')
			]
			for index in range(len(TYPES_COLORS)):
				current_type = TYPES_COLORS[index][0]
				current_color = TYPES_COLORS[index][1]
				if message[:len(current_type)] == current_type:
					message = message[len(current_type):]
					type = current_type
					color = current_color
					break
			if th.current_thread().getName() == "Main" and type == "[INFO] ":
				color = '\033[00m '
			
			# Assemble
			output = color + timestamp + label + type + message

		# Print
		if self.terminal is not None:
			self.terminal.write(output)
		with open(self.log, "a") as log:
			log.write(output)
			log.close()  


	def flush(self):
		
		self.terminal.flush()


# Main

if __name__ == '__main__':
	main()
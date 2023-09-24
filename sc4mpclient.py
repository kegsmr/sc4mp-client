from __future__ import annotations

import configparser
import hashlib
import inspect
import io
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
import traceback
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import Menu, filedialog, messagebox, ttk
from typing import Optional

SC4MP_VERSION = "0.4.0"

SC4MP_SERVERS = [("servers.sc4mp.org", port) for port in range(7240, 7250)]

SC4MP_URL = "www.sc4mp.org"
SC4MP_CONTRIBUTORS_URL = "https://github.com/kegsmr/sc4mp-client/contributors/"
SC4MP_ISSUES_URL = "https://github.com/kegsmr/sc4mp-client/issues/"
SC4MP_RELEASES_URL = "https://github.com/kegsmr/sc4mp-client/releases/"

SC4MP_AUTHOR_NAME = "Simcity 4 Multiplayer Project"
SC4MP_WEBSITE_NAME = "www.sc4mp.org"
SC4MP_LICENSE_NAME = "MIT-0"

SC4MP_CONFIG_PATH = "config.ini"
SC4MP_LOG_PATH = "sc4mpclient.log"
SC4MP_README_PATH = "readme.html"
SC4MP_RESOURCES_PATH = "resources"

SC4MP_TITLE = f"SC4MP Launcher v{SC4MP_VERSION}"
SC4MP_ICON: Path() = Path(SC4MP_RESOURCES_PATH) / "icon.png"

SC4MP_HOST = SC4MP_SERVERS[0][0]
SC4MP_PORT = SC4MP_SERVERS[0][1]

SC4MP_SEPARATOR = b"<SEPARATOR>"
SC4MP_BUFFER_SIZE = 4096

SC4MP_DELAY = .1

SC4MP_SERVERLIST_ENABLED = True

SC4MP_CONFIG_DEFAULTS = [
	("GENERAL", [
		#("nickname", os.getlogin()), #TODO unused
		#(first_run, True) #TODO
		#("use_custom_user_id", False), #TODO
		#("custom_user_id", ""), #TODO
		("default_host", SC4MP_HOST),
		("default_port", SC4MP_PORT),
		#("use_overlay", 1), #TODO
		("custom_plugins", False),
		("custom_plugins_path", Path("~/Documents/SimCity 4/Plugins").expanduser())
	]),
	("STORAGE", [
		("storage_path", Path("~/Documents/SimCity 4/_SC4MP").expanduser()),
		("cache_size", 8000)
	]),
	("SC4", [
		("game_path", ""),
		("fullscreen", False),
		("resw", 1280),
		("resh", 800),
		("cpu_count", 1),
		("cpu_priority", "high"),
		("additional_properties", "")
	])
]

SC4MP_LAUNCHPATH = None
SC4MP_LAUNCHRESW = None
SC4MP_LAUNCHRESH = None
SC4MP_CUSTOMPATH = None

sc4mp_args = sys.argv

sc4mp_ui = None

sc4mp_current_server = None


# Methods

def main():
	"""The main method.

	Arguments:
		None

	Returns:
		None
	"""

	try:

		# Output
		sys.stdout = Logger()
		th.current_thread().name = "Main"

		# Title
		print(SC4MP_TITLE)

		# "-no-ui" argument
		global sc4mp_ui
		sc4mp_ui = not "-no-ui" in sc4mp_args

		# "--host" argument
		global sc4mp_host
		sc4mp_host = None
		if ("--host" in sc4mp_args):
			try:
				sc4mp_host = get_arg_value("--host", sc4mp_args)
			except:
				raise ClientException("Invalid arguments.")

		# "--port" argument
		global sc4mp_port
		sc4mp_port = None
		if ("--port" in sc4mp_args):
			try:
				sc4mp_port = int(get_arg_value("--port", sc4mp_args))
			except:
				raise ClientException("Invalid arguments.")
			
		# "--password" argument
		global sc4mp_password
		sc4mp_password = None
		if ("--password" in sc4mp_args):
			try:
				sc4mp_password = int(get_arg_value("--password", sc4mp_args))
			except:
				raise ClientException("Invalid arguments.")

		# Prep
		prep()

		# Client
		if (sc4mp_ui):
			sc4mp_ui = UI()
			if (sc4mp_host != None and sc4mp_port != None):
				server = Server(sc4mp_host, sc4mp_port)
				server.password = sc4mp_password
				ServerLoaderUI(server)
			sc4mp_ui.mainloop()
		else:
			sc4mp_ui = None
			if (sc4mp_host == None or sc4mp_port == None):
				print("[PROMPT] Connect to server:")
			if (sc4mp_host == None):
				sc4mp_host = input("[PROMPT] - Enter server address... ")
			if (sc4mp_port == None):
				sc4mp_port = int(input("[PROMPT] - Enter server port... "))
			server = Server(sc4mp_host, sc4mp_port)
			server.fetch()
			if (sc4mp_password == None and server.password_enabled):
				sc4mp_password = input("[PROMPT] - Enter server password... ")
			server.password = sc4mp_password
			ServerLoader(None, server).run()
		
		# Cleanup
		cleanup()

	except Exception as e:

		# Fatal error 
		fatal_error()


def prep():
	"""Prepares the client to launch."""
	
	load_config()
	create_subdirectories()
	load_database()


def cleanup():
	"""TODO"""
	sc4mp_servers_database.end = True


def load_config():
	"""Loads settings from the configuration file."""

	global sc4mp_config

	print("Loading config...")

	sc4mp_config = Config(SC4MP_CONFIG_PATH, SC4MP_CONFIG_DEFAULTS)

	
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
		Path("_Database"),
		Path("_Salvage"),
		Path("_Temp"),
		Path("_Temp") / "ServerList",
		Path("Plugins"),
		Path("Plugins") / "server",
		Path("Plugins") / "client",
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
			raise ClientException("Failed to create SC4MP subdirectories.\n\n" + str(e))


def load_database():
	"""TODO"""

	print("Loading database...")

	global sc4mp_servers_database
	sc4mp_servers_database = DatabaseManager(Path(SC4MP_LAUNCHPATH) / "_Database" / "servers.json")
	sc4mp_servers_database.start()


'''def connect(server):
	"""Deprecated."""
	
	if (sc4mp_ui != None):

		# Hide main window
		sc4mp_ui.withdraw()

		# Create the server loader ui
		server_loader_ui = ServerLoaderUI(sc4mp_ui, server)

		# Create and start the server loader
		server_loader = ServerLoader(server_loader_ui, server)
		server_loader.run()

		# If the server loads correctly
		if (sc4mp_current_server != None):

			# Start the TODO
			game_monitor_ui_thread = GameMonitorUIThread(sc4mp_ui, server)
			game_monitor_ui_thread.start()
			start_sc4()
			game_monitor_ui_thread.ui.worker.game_running = False
		sc4mp_ui.deiconify()
	else:
		server_loader = ServerLoader(None, server)
		server_loader.run()
		if (sc4mp_current_server != None):
			game_monitor = GameMonitor(None, server)
			game_monitor.start()
			start_sc4()
			game_monitor.game_running = False'''


def get_sc4_path() -> Optional[Path]:
	"""Returns the path to the Simcity 4 executable if found."""
	sc4_dirs = Path("SimCity 4 Deluxe") / "Apps" / "SimCity 4.exe"
	steam_dirs = Path("Steam") / "steamapps" / "common"
	config_path = Path(sc4mp_config['SC4']['game_path'])

	possible_paths: list[Path] = [
		Path("Program Files") / steam_dirs / sc4_dirs,
		Path("Program Files") / "Origin Games" / sc4_dirs,
		Path("Program Files") / "Maxis" / sc4_dirs,
		Path("Program Files (x86)") / steam_dirs / sc4_dirs,
		Path("Program Files (x86)") / "Origin Games" / sc4_dirs,
		Path("Program Files (x86)") / "Maxis" / sc4_dirs,
		config_path,
		config_path / "SimCity 4.exe",
		config_path / "Apps" / "SimCity 4.exe"
	]

	for possible_path in possible_paths:
		if possible_path.is_file():
			return possible_path

	return None


def start_sc4():
	"""Attempts to find the install path of Simcity 4 and launches the game with custom launch parameters if found."""

	print("Starting Simcity 4...")

	path = get_sc4_path()

	if not path:
		show_error("Path to Simcity 4 not found. Specify the correct path in settings.")
		return

	arguments = [str(path),
			  f'-UserDir:"{SC4MP_LAUNCHPATH}{os.sep}"', # add trailing slash here because SC4 expects it
			  '-intro:off',
			  '-CustomResolution:enabled',
			  f'-r{sc4mp_config["SC4"]["resw"]}x{sc4mp_config["SC4"]["resh"]}x32',
			  f'-CPUCount:{sc4mp_config["SC4"]["cpu_count"]}',
			  f'-CPUPriority:{sc4mp_config["SC4"]["cpu_priority"]}'
			  ]

	if (sc4mp_config["SC4"]["fullscreen"] == True):
		arguments.append('-f')
	else:
		arguments.append('-w')

	arguments.extend(sc4mp_config["SC4"]["additional_properties"].strip().split(' '))  # assumes that properties do not have spaces

	command = ' '.join(arguments)
	print(f"'{command}'")

	try:
		subprocess.run(arguments)  # on Linux, the first String passed as argument must be a file that exists
	except PermissionError as e:
		show_error("Permission denied. Run the program as administrator.\n\n" + str(e))

	# For compatability with the steam version of SC4
	time.sleep(3)
	while (process_exists("simcity 4.exe")):
		time.sleep(1)

	print("Simcity 4 closed.")


def process_exists(process_name): #TODO add macos compatability
	"""TODO"""
	try:
		if (platform.system() == "Windows"):
			call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
			output = subprocess.check_output(call, shell=True).decode()
			last_line = output.strip().split('\r\n')[-1]
			return last_line.lower().startswith(process_name.lower())
		else:
			return False
	except Exception as e:	# Hacky solution. It keeps the game monitor running (possibly infinitely) instead of closing it. Because that's better than closing it. 
		show_error(e, no_ui=True)
		return True 


def get_sc4mp_path(filename: str) -> Path:
	"""Returns the path to a given file in the SC4MP "resources" subdirectory"""
	return Path(SC4MP_RESOURCES_PATH) / filename


def md5(filename: Path) -> str:
	"""Returns an md5 hashcode generated from a given file."""
	hash_md5 = hashlib.md5()
	with filename.open("rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def random_string(length):
	"""Returns a random string of ascii letters of the specified length."""
	return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(length))


def purge_directory(directory: Path) -> None:
	"""Deletes all files and subdirectories of a directory"""
	for path in directory.iterdir():
		try:
			if path.is_file():
				path.unlink()
			elif path.is_dir():
				shutil.rmtree(path)
		except PermissionError as e:
			raise ClientException(f'Failed to delete "{path}" because the file is being used by another process.') #\n\n' + str(e)


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


def event_generate(ui, event, when):
	"""Deprecated."""
	if (ui != None):
		ui.event_generate(event, when=when)


'''def create_empty_json(filename):
	"""Deprecated."""
	with open(filename, 'w') as file:
		data = dict()
		file.seek(0)
		json.dump(data, file, indent=4)
		file.truncate()'''


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
	if (isinstance(e, str)):
		message = e
	else: 
		message = str(e)

	print(f"[ERROR] {message}\n\n{traceback.format_exc()}")

	if (not no_ui):
		if (sc4mp_ui != None):
			if (sc4mp_ui == True):
				tk.Tk().withdraw()
			messagebox.showerror(SC4MP_TITLE, message)


def startfile(filename):
	syst = platform.system()
	if syst == "Windows":
		os.startfile(filename)
	else:
		opener = "open" if syst == "Darwin" else "xdg-open"  # Linux
		subprocess.call([opener, filename])


def fatal_error():
	"""Shows a fatal error message in the console and the UI. Exits the program."""

	message = f"A fatal error occurred.\n\n{traceback.format_exc()}"

	print(f"[FATAL] {message}")

	if (sc4mp_ui != None):
		if (sc4mp_ui == True):
			tk.Tk().withdraw()
		messagebox.showerror(SC4MP_TITLE, message)

	startfile(SC4MP_LOG_PATH)

	cleanup()

	sys.exit()


def show_warning(e):
	"""Shows a warning in the console and the UI."""
	message = None
	if (isinstance(e, str)):
		message = e
	else: 
		message = str(e)

	print(f"[WARNING] {message}")

	if (sc4mp_ui != None):
		if (sc4mp_ui == True):
			tk.Tk().withdraw()
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
	except:
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
	s.send(SC4MP_VERSION.encode())

	if (server.password_enabled):
		s.recv(SC4MP_BUFFER_SIZE)
		s.send(server.password.encode())

	s.recv(SC4MP_BUFFER_SIZE)
	s.send(server.user_id.encode())


def format_version(version: tuple[int, int, int]) -> str:
	"""Converts a version number from a tuple to a string."""
	major, minor, patch = version
	return f'{major}.{minor}.{patch}'


def unformat_version(version: str) -> tuple[int, int, int]:
	"""Converts a version number from a string to a tuple."""
	return tuple([int(v) for v in version.split('.')])


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
	"""TODO"""
	return Path(SC4MP_LAUNCHPATH) / "SimCity 4.cfg"


def region_open(region):
	"""TODO"""
	cfg_path = get_sc4_cfg_path()
	return b"\x00" + region.encode() + b"\x00" in DBPF(cfg_path).decompress_subfile("a9dd6e06").read() #TODO maybe the surrounding zeroes are just from that decompression error?


def refresh_region_open():
	"""TODO"""
	return region_open("Refresh...")


def report(message, object):
	"""TODO"""
	print(message)


def prep_region_config(path):
	try:
		config = configparser.RawConfigParser()
		config.read(path)
		config.set("Regional Settings", "Name", "[SC4MP] " + config.get("Regional Settings", "Name"))
		with open(path, 'wt') as config_file:
			config.write(config_file)
	except:
		raise ClientException(f"Failed to prep region config at {path}.")


def format_filesize(size):
	if (size >= 10 ** 11):
		return ">99GB"
	elif (size >= 10 ** 10):
		return str(int(size / (10 ** 9))) + "GB"
	elif (size >= 10 ** 9):
		return str(float(int(size / (10 ** 8)) / 10)) + "GB"
	elif (size >= 10 ** 8):
		return str(int(size / (10 ** 6))) + "MB"
	elif (size >= 10 ** 7):
		return str(int(size / (10 ** 6))) + "MB"
	elif (size >= 10 ** 6):
		return str(float(int(size / (10 ** 5)) / 10)) + "MB"
	elif (size >= 10 ** 5):
		return str(int(size / (10 ** 3))) + "KB"
	elif (size >= 10 ** 4):
		return str(int(size / (10 ** 3))) + "KB"
	elif (size >= 10 ** 3):
		return str(float(int(size / (10 ** 2)) / 10)) + "KB"
	else:
		return str(int(size)) + "B"


def get_bitmap_dimensions(filename):
	"""TODO"""

	with open(filename, "rb") as file:
		data = bytearray(file.read())

	width = struct.unpack_from('<i', data, 18)
	height = struct.unpack_from('<i', data, 22)

	return (width[0], height[0])


def arp():
	try:
		if (platform.system() == "Windows"):
			call = 'arp', '-a'
			output = subprocess.check_output(call, shell=True).decode()
			return [line for line in re.findall('([-.0-9]+)\s+([-0-9a-f]{17})\s+(\w+)', output)]
		else: #TODO make this work on other platforms besides Windows
			return []
	except Exception as e:
		show_error(e, no_ui=True)
		return []


# Objects

class Config:
	"""Encapsules a dictionary that represents config values set by the user."""


	def __init__(self, path, defaults):

		# Parameters
		self.PATH = path
		self.DEFAULTS = defaults

		# Create dictionary with default config settings
		self.data = dict()
		for section in self.DEFAULTS:
			section_name = section[0]
			section_items = section[1]
			self.data.setdefault(section_name, dict())
			for item in section_items:
				item_name = item[0]
				item_value = item[1]
				self.data[section_name].setdefault(item_name, item_value)
		
		# Try to read settings from the config file and update the dictionary accordingly
		parser = configparser.RawConfigParser()
		try:
			parser.read(self.PATH)
			for section_name in self.data.keys():
				section = self.data[section_name]
				try:
					for item_name in section.keys():
						try:
							from_file = parser.get(section_name, item_name)
							if (from_file == "True"):
								self.data[section_name][item_name] = True
							elif (from_file == "False"):
								self.data[section_name][item_name] = False
							elif (from_file == "None"):
								self.data[section_name][item_name] = None
							else:
								t = type(self.data[section_name][item_name])
								self.data[section_name][item_name] = t(from_file)
						except:
							pass
				except:
					pass
		except:
			pass

		# Update config file
		self.update()


	def __getitem__(self, key):
		return self.data.__getitem__(key)


	def __setitem__(self, key, value):
		return self.data.__setitem__(key, value)


	def update(self):
		"""Writes config values set by the user to the config file."""
		parser = configparser.RawConfigParser()
		for section_name in self.data.keys():
			parser.add_section(section_name)
			section = self.data[section_name]
			for item_name in section.keys():
				item_value = section[item_name]
				parser.set(section_name, item_name, item_value)
		with open(self.PATH, 'wt') as file:
			parser.write(file)
		try:
			update_config_constants(self)
		except:
			pass


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
		if ((host, port) in SC4MP_SERVERS):
			self.categories.append("Official")


	def fetch(self):
		"""Retreives basic information from a server and saves them as instance variables. Updates the json entry for the server if possible."""

		# Mark server as fetched
		self.fetched = True

		# Request server info
		self.server_id = self.request("server_id")
		self.server_name = self.request("server_name")
		self.server_description = self.request("server_description")
		self.server_url = self.request("server_url")
		self.server_version = self.request("server_version")
		self.password_enabled = self.request("password_enabled") == "yes"
		self.user_plugins_enabled = self.request("user_plugins_enabled") == "yes"
		self.private = self.request("private") == "yes"

		if (self.password_enabled):
			self.categories.append("Private")
		else:
			self.categories.append("Public")

		#if (self.server_version != None):
		#	self.server_version = unformat_version(self.server_version)

		if (self.fetched == True):
			try:
				self.update_database()
			except Exception as e:
				show_error(e, no_ui = True)


	def fetch_stats(self):
		"""TODO"""

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
						if (owner != None):
							claimed_area += city_entry["size"] ** 2
							if (owner not in mayors):
								mayors.append(owner)
							modified = city_entry["modified"]
							if (modified != None):
								modified = datetime.strptime(modified, "%Y-%m-%d %H:%M:%S")
								if (modified > server_time - timedelta(hours=1) and owner not in mayors_online):
									mayors_online.append(owner)
				total_area += region_dimensions[0] * region_dimensions[1]
			except Exception as e:
				show_error(e, no_ui=True)

		self.stat_mayors = len(mayors) #(random.randint(0,1000))
		
		self.stat_mayors_online = len(mayors_online) #int(self.stat_mayors * (float(random.randint(0, 100)) / 100))
		
		try:
			self.stat_claimed = (float(claimed_area) / float(total_area)) #(float(random.randint(0, 100)) / 100)
		except ZeroDivisionError:
			self.stat_claimed = 1

		self.stat_download = download #(random.randint(0, 10 ** 11))

		ping = self.ping()
		if (ping != None):
			self.stat_ping = ping

		sc4mp_servers_database[self.server_id]["stat_mayors"] = self.stat_mayors
		sc4mp_servers_database[self.server_id]["stat_mayors_online"] = self.stat_mayors_online
		sc4mp_servers_database[self.server_id]["stat_claimed"] = self.stat_claimed
		sc4mp_servers_database[self.server_id]["stat_download"] = self.stat_download
		sc4mp_servers_database[self.server_id]["stat_ping"] = self.stat_ping


	def fetch_temp(self):
		"""TODO"""

		REQUESTS = [b"plugins", b"regions"]
		DIRECTORIES = ["Plugins", "Regions"]

		size_downloaded = 0

		for request, directory in zip(REQUESTS, DIRECTORIES):

			# Set destination
			destination = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList" / self.server_id / directory

			# Create the socket
			s = socket.socket()
			s.settimeout(10)
			s.connect((self.host, self.port))

			# Request the type of data
			s.send(request)

			# Request header
			if self.private:
				request_header(s, self)

			# Receive file count
			file_count = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Separator
			s.send(SC4MP_SEPARATOR)

			# Receive file size
			size = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Receive files
			for files_received in range(file_count):
				s.send(SC4MP_SEPARATOR)
				size_downloaded += self.receive_or_cached(s, destination)

		return size_downloaded


	def receive_or_cached(self, s:socket.socket, rootpath: Path) -> int:

		# Receive hashcode and set cache filename
		hash = s.recv(SC4MP_BUFFER_SIZE).decode()

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive relative path and set the destination
		relpath = Path(s.recv(SC4MP_BUFFER_SIZE).decode())
		filename = relpath.name
		destination = Path(rootpath) / relpath

		if not (filename == "region.json" or filename == "config.bmp"):

			# Tell the server that the file is cached
			s.send(b"cached")

		else:

			# Tell the server that the file is not cached
			s.send(b"not cached")

			# Create the destination directory if necessary
			destination.parent.mkdir(exist_ok=True, parents=True)

			# Delete the destination file if it exists
			destination.unlink(missing_ok=True)

			# Receive the file
			filesize_read = 0
			with destination.open("wb") as f:
				while (filesize_read < filesize):
					bytes_read = s.recv(SC4MP_BUFFER_SIZE)
					if not bytes_read:
						break
					f.write(bytes_read)
					filesize_read += len(bytes_read)

		# Return the file size
		return filesize


	def update_database(self):
		"""Updates the json entry for the server."""

		# Get database entry for server
		key = self.server_id
		entry = sc4mp_servers_database.get(key, dict())
		sc4mp_servers_database[key] = entry

		# Set server categories
		if "user_id" in entry.keys():
			self.categories.append("History")
		if entry.get("favorite", False):
			self.categories.append("Favorites")

		# Set values in database entry
		set_server_data(entry, self)


	def request(self, request):
		"""Requests a given value from the server."""

		if (self.fetched == False):
			return

		host = self.host
		port = self.port

		try:
			s = socket.socket()
			s.settimeout(10)
			s.connect((host, port))
			s.send(request.encode())
			return s.recv(SC4MP_BUFFER_SIZE).decode()
		except:
			self.fetched = False
			print(f'[WARNING] Unable to fetch "{request}" from {host}:{port}')
			return None


	def authenticate(self):
		"""TODO"""

		# Get database entry for server
		key = self.server_id
		entry = sc4mp_servers_database.get(key, dict())
		sc4mp_servers_database[key] = entry

		# Get user_id
		user_id = None
		try:
			user_id = entry["user_id"]
		except:
			user_id = random_string(32)

		# Get token
		token = None
		try:
			token = entry["token"]
		except:
			pass

		# Verify server can produce the user_id from the hash of the user_id and token combined
		if (token != None):
			hash = hashlib.sha256(((hashlib.sha256(user_id.encode()).hexdigest()[:32]) + token).encode()).hexdigest()
			s = socket.socket()
			s.connect((self.host, self.port))
			s.send(b"user_id")
			s.recv(SC4MP_BUFFER_SIZE)
			s.send(hash.encode())
			if (s.recv(SC4MP_BUFFER_SIZE).decode() == hashlib.sha256(user_id.encode()).hexdigest()[:32]):
				self.user_id = user_id
			else:
				raise ClientException("Invalid token.") #"Authentication error."
			s.close()
		else:
			self.user_id = user_id

		# Get the new token
		s = socket.socket()
		s.connect((self.host, self.port))
		s.send(b"token")
		request_header(s, self)
		token = s.recv(SC4MP_BUFFER_SIZE).decode()

		# Raise exception if no token is received
		if (len(token) < 1):
			raise ClientException("You are banned from this server.")

		# Set user_id and token in the database entry
		entry["user_id"] = user_id
		entry["token"] = token
		entry.setdefault("first_logon", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		entry["last_logon"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


	def ping(self):

		host = self.host
		port = self.port

		s = socket.socket()

		try:
			s.connect((host, port))
			start = time.time()
			s.send(b"ping")
			s.recv(SC4MP_BUFFER_SIZE)
			end = time.time()
			s.close()
			self.server_ping = round(1000 * (end - start))
			return self.server_ping
		except socket.error as e:
			return None


	def time(self):
		"""TODO"""

		try:

			s = socket.socket()
			s.settimeout(10)
			s.connect((self.host, self.port))
			s.send(b"time")

			return datetime.strptime(s.recv(SC4MP_BUFFER_SIZE).decode(), "%Y-%m-%d %H:%M:%S")
		
		except Exception as e:

			show_error(e, no_ui=True)

			return datetime.now()


class DBPF:
	"""TODO include credits to original php file"""


	def __init__(self, filename, offset=0):
		"""TODO"""

		report(f'Parsing "{filename}"...', self)

		self.filename = filename
		self.offset = offset

		self.NONSENSE_BYTE_OFFSET = 9

		# Try opening the file to read bytes
		try:
			self.file = open(self.filename, 'rb')
		except Exception as e:
			raise e #TODO

		# Advance to offset
		start = self.offset
		if (self.offset > 0):
			self.file.seek(self.offset)

		# Verify that the file is a DBPF
		test = self.file.read(4)
		if (test != b"DBPF"):
			return #TODO raise exception

		# Read the header
		self.majorVersion = self.read_UL4()
		self.minorVersion = self.read_UL4()
		self.reserved = self.file.read(12)
		self.dateCreated = self.read_UL4()
		self.dateModified = self.read_UL4()
		self.indexMajorVersion = self.read_UL4()
		self.indexCount = self.read_UL4()
		self.indexOffset = self.read_UL4()
		self.indexSize = self.read_UL4()
		self.holesCount = self.read_UL4()
		self.holesOffset = self.read_UL4()
		self.holesSize = self.read_UL4()
		self.indexMinorVersion = self.read_UL4() - 1
		self.reserved2 = self.file.read(32)
		self.header_end = self.file.tell()

		# Seek to index table
		self.file.seek(offset + self.indexOffset)

		# Read index table
		self.indexData = []
		for index in range(0, self.indexCount):
			self.indexData.append(dict())
			self.indexData[index]['typeID'] = self.read_ID()
			self.indexData[index]['groupID'] = self.read_ID()
			self.indexData[index]['instanceID'] = self.read_ID()
			if ((self.indexMajorVersion == "7") and (self.indexMinorVersion == "1")):
				self.indexData[index]['instanceID2'] = self.read_ID()
			self.indexData[index]['offset'] = self.read_UL4()
			self.indexData[index]['filesize'] = self.read_UL4()
			self.indexData[index]['compressed'] = False #TODO
			self.indexData[index]['truesize'] = 0 #TODO


	def decompress(self, length):

		#report('Decompressing ' + str(length) + ' bytes...', self)

		buf = ""
		answer = bytes()
		answerlen = 0
		numplain = ""
		numcopy = ""
		offset = ""

		while (length > 0):
			try:
				cc = self.read_UL1(self.file)
			except Exception as e:
				show_error(e)
				break
			length -= 1
			#print("Control char is " + str(cc) + ", length remaining is " + str(length) + ".\n")
			if (cc >= 252): #0xFC
				numplain = cc & 3 #0x03
				if (numplain > length):
					numplain = length
				numcopy = 0
				offset = 0
			elif (cc >= 224): #0xE0
				numplain = (cc - 223) << 2 #223 = 0xdf
				numcopy = 0
				offset = 0
			elif (cc >= 192): #0xC0
				length -= 3
				byte1 = self.read_UL1(self.file)
				byte2 = self.read_UL1(self.file)
				byte3 = self.read_UL1(self.file)
				numplain = cc & 3 #0x03
				numcopy = ((cc & 12) << 6) + 5 + byte3 #12 = 0x0c
				offset = ((cc & 16) << 12) + (byte1 << 8) + byte2 #16 = 0x10
			elif (cc >= 128): #0x80
				length -= 2
				byte1 = self.read_UL1(self.file)
				byte2 = self.read_UL1(self.file)
				numplain = (byte1 & 192) >> 6 #192 = 0xc0
				numcopy = (cc & 63) + 4 #63 = 0x3f
				offset = ((byte1 & 63) << 8) + byte2 #63 = 0x3f
			else:
				length -= 1
				byte1 = self.read_UL1(self.file)
				numplain = (cc & 3) #3 = 0x03
				numcopy = ((cc & 28) >> 2) + 3 #28 = 0x1c
				offset = ((cc & 96) << 3) + byte1 #96 = 0x60
			length -= numplain

			# This section basically copies the parts of the string to the end of the buffer:
			if (numplain > 0):
				buf = self.file.read(numplain)
				answer = answer + buf
			fromoffset = len(answer) - (offset + 1)  # 0 == last char
			for index in range(numcopy):
				#print(str(answer))
				#print(str(cc))
				#print(str(offset))
				#print(str(fromoffset))
				#TODO remove try and except block. decompression algorithm breaks with a control char of 206. the offset becomes larger than the length of the answer, causing a negative fromindex and an indexing error. for now it does not seem to affect city coordinates
				try:
					answer = answer + (answer[fromoffset + index]).to_bytes(1, 'little') #substr(fromoffset + index, 1)
				except Exception as e:
					#show_error(e) #TODO
					return io.BytesIO(answer)
			answerlen += numplain
			answerlen += numcopy

		return io.BytesIO(answer)


	def read_UL1(self, file=None):
		"""TODO"""
		if (file == None):
			file = self.file
		return struct.unpack('<B', file.read(1))[0]


	def read_UL2(self, file=None):
		"""TODO"""
		if (file == None):
			file = self.file
		return struct.unpack('<H', file.read(2))[0]
	
	
	def read_UL4(self, file=None):
		"""TODO"""
		if (file == None):
			file = self.file
		return struct.unpack('<L', file.read(4))[0]


	def read_ID(self, file=None):
		"""TODO"""
		if (file == None):
			file = self.file
		return file.read(4)[::-1].hex()


	def get_indexData_entry_by_type_ID(self, type_id):
		"""TODO"""
		for entry in self.indexData:
			if (entry['typeID'] == type_id):
				return entry


	def goto_subfile(self, type_id):
		"""TODO"""
		entry = self.get_indexData_entry_by_type_ID(type_id)
		self.file.seek(entry['offset'])
		#print(entry['offset'] + 9)


	def get_subfile_size(self, type_id):
		"""TODO"""
		entry = self.get_indexData_entry_by_type_ID(type_id)
		return entry['filesize']


	#def get_subfile_header(self, type_id):
	#	"""TODO"""
	#	self.goto_subfile(type_id)
	#	return (self.read_UL4(), self.read_ID(), ) #TODO how to read these values?


	def decompress_subfile(self, type_id):
		"""TODO"""
		#report('Decompressing "' + type_id + '"...', self)
		self.goto_subfile(type_id)
		self.file.read(self.NONSENSE_BYTE_OFFSET)
		return self.decompress(self.get_subfile_size(type_id))


	def get_SC4ReadRegionalCity(self):
		"""TODO"""

		report(f'Parsing region view subfile of "{self.filename}"...', self)

		data = self.decompress_subfile("ca027edb")
	
		#print(data.read())
		#data.seek(0)

		self.SC4ReadRegionalCity = dict()

		self.SC4ReadRegionalCity['majorVersion'] = self.read_UL2(data)
		self.SC4ReadRegionalCity['minorVersion'] = self.read_UL2(data)
		
		self.SC4ReadRegionalCity['tileXLocation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['tileYLocation'] = self.read_UL4(data)
		
		self.SC4ReadRegionalCity['citySizeX'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['citySizeY'] = self.read_UL4(data)
		
		self.SC4ReadRegionalCity['residentialPopulation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['commercialPopulation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['industrialPopulation'] = self.read_UL4(data)

		self.SC4ReadRegionalCity['unknown1'] = data.read(4) #TODO read float

		self.SC4ReadRegionalCity['mayorRating'] = self.read_UL1(data)
		self.SC4ReadRegionalCity['starCount'] = self.read_UL1(data)
		self.SC4ReadRegionalCity['tutorialFlag'] = self.read_UL1(data)

		self.SC4ReadRegionalCity['cityGUID'] = self.read_UL4(data)

		self.SC4ReadRegionalCity['unknown5'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['unknown6'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['unknown7'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['unknown8'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['unknown9'] = self.read_UL4(data)

		self.SC4ReadRegionalCity['modeFlag'] = self.read_UL1(data)

		#TODO keep reading file

		return self.SC4ReadRegionalCity

	
	def get_cSC4Simulator(self):
		"""TODO"""

		data = self.decompress_subfile("2990c1e5")

		print(data.read())
		data.seek(0)

		self.cSC4Simulator = dict()

		#TODO


# Workers

class ServerList(th.Thread):
	"""TODO"""


	def __init__(self, ui, kill=None):
		"""TODO"""

		th.Thread.__init__(self)

		self.ui = ui

		self.setDaemon(True)

		self.end = False
		self.ended = False
		self.pause = False

		self.servers = dict()

		self.unfetched_servers = SC4MP_SERVERS.copy()
		
		self.lan_servers = []
		lan_addresses = list(zip(*arp()))
		for lan_address in lan_addresses[0:1]:
			for port in range(7240, 7250):
				self.lan_servers.append((lan_address, port))

		delete_server_ids = []
		for server_id in reversed(sc4mp_servers_database.keys()):
			server_entry = sc4mp_servers_database[server_id]
			if (server_entry.get("user_id", None) != None) or ("last_contact" not in server_entry.keys()) or (datetime.strptime(server_entry["last_contact"], "%Y-%m-%d %H:%M:%S") + timedelta(days=30) > datetime.now()):
				self.unfetched_servers.append((sc4mp_servers_database[server_id]["host"], sc4mp_servers_database[server_id]["port"]))
			else:
				delete_server_ids.append(server_id)
		for delete_server_id in delete_server_ids:
			sc4mp_servers_database.data.pop(delete_server_id)

		self.fetched_servers = []
		self.tried_servers = []
		self.hidden_servers = []

		self.server_fetchers = 0

		self.stat_mayors = dict()
		self.stat_mayors_online = dict()
		self.stat_claimed = dict()
		self.stat_download = dict()
		self.stat_ping = dict()

		self.blank_icon = tk.PhotoImage(file=get_sc4mp_path("blank-icon.png"))
		self.lock_icon = tk.PhotoImage(file=get_sc4mp_path("lock-icon.png"))
		self.official_icon = tk.PhotoImage(file=get_sc4mp_path("official-icon.png"))

		self.temp_path = Path(SC4MP_LAUNCHPATH) / "_Temp" / "ServerList"

		self.kill = kill

		self.sort_mode_changed = False


	def run(self):
		"""TODO"""

		try:

			if (self.kill != None):
				self.kill.end = True
				while not self.kill.ended:
					time.sleep(SC4MP_DELAY)
				self.clear_tree()

			try:
				purge_directory(self.temp_path)
			except Exception as e:
				show_error(e, no_ui=True)

			print("Fetching servers...")

			while (self.end == False):

				if (self.pause == False):

					# Enable or disable connect button and update labels
					server_id = self.ui.tree.focus()
					if (server_id == "" or server_id not in self.servers.keys()):
						self.ui.connect_button['state'] = tk.DISABLED
						self.ui.address_label["text"] = ""
						self.ui.description_label["text"] = ""
						self.ui.url_label["text"] = ""
					else:
						self.ui.connect_button['state'] = tk.NORMAL
						self.ui.address_label["text"] = self.servers[server_id].host + ":" + str(self.servers[server_id].port)
						self.ui.description_label["text"] = self.servers[server_id].server_description
						self.ui.url_label["text"] = self.servers[server_id].server_url
						
					# Add all fetched servers to the server dictionary if not already present
					while len(self.fetched_servers) > 0:
						fetched_server = self.fetched_servers.pop(0)
						if (fetched_server.server_id not in self.servers.keys()):
							self.servers[fetched_server.server_id] = fetched_server

					# Fetch the next unfetched server #TODO fetch from LAN servers too
					if (self.server_fetchers < 100): #TODO make configurable?
						if (len(self.unfetched_servers) > 0):
							unfetched_server = self.unfetched_servers.pop(0)
							if (unfetched_server not in self.tried_servers):
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
							self.stat_download[server_id] = update_server.stat_download
							self.stat_claimed[server_id] = update_server.stat_claimed
							self.stat_ping[server_id] = update_server.stat_ping
							self.calculate_rating(update_server)
						except:
							pass

					# Add missing rows to the tree
					server_ids = self.servers.keys()
					filter = self.ui.combo_box.get()
					for server_id in server_ids:
						if (not self.ui.tree.exists(server_id)) and (len(filter) < 1 or (not self.filter(self.servers[server_id], self.filters(filter)))):
							#while len(self.ui.tree.get_children()) >= 50:
							#	self.ui.tree.delete(self.ui.tree.get_children()[-1])
							server = self.servers[server_id]
							if (server.password_enabled):
								image = self.lock_icon
							elif (server.host, server.port) in SC4MP_SERVERS:
								image = self.official_icon
							else:
								image = self.blank_icon
							self.ui.tree.insert("", self.in_order_index(server), server_id, text=server.server_name, values=self.format_server(server), image=image)

					# Filter the tree
					filter = self.ui.combo_box.get()
					if (len(filter) > 0):
						try:
							category, search_terms = self.filters(filter)
							#print("Filtering by \"" + category + "\" and " + str(search_terms) + "...")
							server_ids = self.ui.tree.get_children()
							for server_id in server_ids:
								hide = self.filter(self.servers[server_id], (category, search_terms))
								if (hide) and (server_id in self.ui.tree.get_children()) and (server_id not in self.hidden_servers):
									self.hidden_servers.append(server_id)
									self.ui.tree.delete(server_id)
								elif (not hide) and (server_id in self.hidden_servers):
									self.hidden_servers.remove(server_id)
									#self.ui.tree.reattach(server_id, self.ui.tree.parent(server_id), self.in_order_index(self.servers[server_id]))
						except Exception as e:
							show_error(e, no_ui=True)
					elif (len(self.hidden_servers) > 0):
						server_ids = self.hidden_servers
						for server_id in server_ids:
							self.hidden_servers.remove(server_id)
							#self.ui.tree.reattach(server_id, self.ui.tree.parent(server_id), self.in_order_index(self.servers[server_id]))

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
					if (len(self.servers) > 0):
						self.ui.label["text"] = 'To get started, select a server below and click "Connect"'
					else:
						self.ui.address_label["text"] = ""
						self.ui.description_label["text"] = ""
						self.ui.url_label["text"] = ""
						if (self.server_fetchers > 0):
							self.ui.label["text"] = 'Getting server list...'
						else:
							self.ui.label["text"] = 'No servers found' #Select "Servers" then "Connect..." in the menu bar to connect to a server.'

				# Delay
				time.sleep(SC4MP_DELAY)

			self.ended = True

		except Exception as e:

			try:
				self.ended = True
			except:
				pass

			show_error("An error occurred while fetching servers.\n\n" + str(e)) #, no_ui=True)


	def clear_tree(self):
		"""TODO"""
		self.ui.tree.delete(*self.ui.tree.get_children())


	def filters(self, filter):
		"""TODO"""
		if (len(filter) > 0):
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
			return None


	def filter(self, server, filters):
		"""TODO"""
		category = filters[0]
		search_terms = filters[1]
		search_fields = [server.server_name, server.server_description, server.server_url]
		if len(search_terms) > 0:
			for search_field in search_fields:
				search_field.lower()
				for search_term in search_terms:
					search_term.lower()
					if search_term in search_field and category in server.categories:
						return False
		elif category in server.categories:
			return False
		return True


	def sorted(self):
		"""TODO"""
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
		"""TODO"""
		server_a_sort_value = self.get_sort_value(server_a)
		server_b_sort_value = self.get_sort_value(server_b)
		if (server_a_sort_value == None and server_b_sort_value == None):
			return True
		elif (server_a_sort_value == None):
			return False
		elif (server_b_sort_value == None):
			return True
		else:
			if (not self.ui.tree.reverse_sort):
				return server_a_sort_value >= server_b_sort_value
			else:
				return server_a_sort_value <= server_b_sort_value
	

	def in_order_index(self, server):
		"""TODO"""
		existing_server_ids = self.ui.tree.get_children()
		for index in range(len(existing_server_ids)):
			existing_server_id = existing_server_ids[index]
			existing_server = self.servers[existing_server_id]
			if self.in_order(server, existing_server):
				return index
		return "end"

	
	def get_sort_value(self, server):
		"""TODO"""
		sort_mode = self.ui.tree.sort
		try:
			if sort_mode == "Name":
				return server.server_name
			elif sort_mode == "Mayors":
				return server.stat_mayors
			elif sort_mode == "Claimed":
				return server.stat_claimed
			elif sort_mode == "Download":
				return server.stat_download
			elif sort_mode == "Ping":
				return server.stat_ping
			else:
				return server.rating
		except:
			return None


	def format_server(self, server):
		"""TODO"""
		functions = [
			lambda: str(server.stat_mayors) + " (" + str(server.stat_mayors_online) + ")",
	    	lambda: str(int(server.stat_claimed * 100)) + "%",
		    lambda: format_filesize(server.stat_download),
		    lambda: str(server.stat_ping) + "ms",
		    lambda: str(round(server.rating, 1)),
		]
		cells = []
		for function in functions:
			try:
				cells.append(function())
			except:
				cells.append("...")
		return cells

	
	def calculate_rating(self, server):
		"""TODO"""
		try:
			categories = [
				.5 * self.max_category(server.stat_mayors, self.stat_mayors.values()),
				.5 * self.max_category(server.stat_mayors_online, self.stat_mayors_online.values()),
				self.min_category(server.stat_claimed, self.stat_claimed.values()),
				self.min_category(server.stat_download, self.stat_download.values()),
				self.min_category(server.stat_ping, self.stat_ping.values()),
			]
			rating = 1 + sum(categories)
			try:
				server.rating = ((99 * server.rating) + rating) / 100
			except:
				server.rating = rating
		except:
			pass
	

	def max_category(self, item, array):
		"""TODO"""
		item = float(item)
		try:
			return ((item - min(array)) / (max(array) - min(array)))
		except:
			return 1.0


	def min_category(self, item, array):
		"""TODO"""
		item = float(item)
		try:
			return 1.0 - ((item - min(array)) / (max(array) - min(array)))
		except:
			return 1.0


class ServerFetcher(th.Thread):


	def __init__(self, parent, server):

		th.Thread.__init__(self)

		self.parent = parent
		self.server = server

		self.setDaemon(True)


	def run(self):
		
		try:

			try:

				print(f"Fetching {self.server.host}:{self.server.port}...")

				print("- fetching server info...")

				try:
					self.server.fetch()
				except:
					raise ClientException("Unable to fetch server info.")

				if (self.parent.end):
					raise ClientException("The parent thread was signaled to end.")
				elif not self.server.fetched:
					raise ClientException("Server is not fetched.")

				print("- populating server statistics")

				if not self.server.private:
					try:
						self.server.stat_ping = sc4mp_servers_database[self.server.server_id]["stat_ping"]
						self.server.stat_mayors = sc4mp_servers_database[self.server.server_id]["stat_mayors"]
						self.server.stat_mayors_online = sc4mp_servers_database[self.server.server_id]["stat_mayors_online"]
						self.server.stat_claimed = sc4mp_servers_database[self.server.server_id]["stat_claimed"]
						self.server.stat_download = sc4mp_servers_database[self.server.server_id]["stat_download"]
					except:
						pass
				else:
					try:
						self.server.stat_ping = sc4mp_servers_database[self.server.server_id]["stat_ping"]
					except:
						pass

				print("- adding server to server list...")

				try:
					self.parent.fetched_servers.append(self.server)
				except:
					raise ClientException("Unable to add server to server list.")

				print("- starting server pinger...")

				try:
					ServerPinger(self.parent, self.server).start()
				except:
					raise ClientException("Unable to start server pinger.")

				print("- fetching server list...")

				try:
					self.server_list()
				except:
					raise ClientException("Unable to fetch server list.")

				if not self.server.private:

					print("- fetching server stats...")
					
					try:
						self.fetch_stats()
					except Exception as e:
						print(f"[WARNING] Unable to fetch server stats for {self.server.host}:{self.server.port}! " + str(e))

				print("- done.")

			except Exception as e:

				print(f"[WARNING] Failed to fetch {self.server.host}:{self.server.port}! " + str(e))

			self.parent.server_fetchers -= 1

		except Exception as e:

			show_error(e)


	def fetch_stats(self):
		"""TODO"""
		self.server.fetch_stats()
		
	
	def server_list(self):
		"""TODO"""
		s = self.create_socket(self.server)
		s.send(b"server_list")
		size = int(s.recv(SC4MP_BUFFER_SIZE).decode())
		s.send(SC4MP_SEPARATOR)
		for count in range(size):
			host = s.recv(SC4MP_BUFFER_SIZE).decode()
			s.send(SC4MP_SEPARATOR)
			port = int(s.recv(SC4MP_BUFFER_SIZE).decode())
			s.send(SC4MP_SEPARATOR)
			self.parent.unfetched_servers.append((host, port))


	def create_socket(self, server):
		"""TODO"""
		host = server.host
		port = server.port
		try:
			s = socket.socket()
			s.settimeout(10)
			s.connect((host, port))
			return s
		except:
			return None


class ServerPinger(th.Thread):


	def __init__(self, parent, server):

		th.Thread.__init__(self)

		self.parent = parent
		self.server = server

		self.setDaemon(True)


	def run(self):

		try:

			while (not self.parent.end):
				time.sleep(len(self.parent.servers) + 1)
				if (not self.parent.pause):
					print(f"Pinging {self.server.host}:{self.server.port}")
					ping = self.server.ping()
					if (ping != None):
						self.server.stat_ping = ping #int((self.server.stat_ping + ping) / 2)
						sc4mp_servers_database[self.server.server_id]["stat_ping"] = ping

		except Exception as e:

			show_error(e, no_ui=True)


class ServerLoader(th.Thread):
	"""TODO"""

	
	def __init__(self, ui, server):
		"""TODO"""

		th.Thread.__init__(self)

		self.ui = ui
		self.server = server

		self.setDaemon(True)

		if (sc4mp_ui != None):
			sc4mp_ui.withdraw()

	
	def run(self):
		"""TODO"""

		try:

			if (self.ui != None):
				while (get_sc4_path() == None):
					show_warning('No Simcity 4 installation found. \n\nPlease provide the correct installation path.')
					path = filedialog.askdirectory(parent=self.ui)
					if (len(path) > 0):
						sc4mp_config["SC4"]["game_path"] = path
						sc4mp_config.update()
					else:
						self.ui.destroy()
						sc4mp_ui.deiconify()
						return
		
			host = self.server.host
			port = self.server.port

			try:

				self.report("", f'Connecting to server at {host}:{port}...')
				self.fetch_server()
				
				self.report("", 'Authenticating...')
				self.authenticate()

				self.report("", "Synchronizing plugins...")
				self.load("plugins")

				self.report("", "Synchronizing regions...")
				self.load("regions")

				self.report("", "Prepping regions...")
				self.prep_regions()

				self.report("", "Done.")

				global sc4mp_current_server
				sc4mp_current_server = self.server

			except Exception as e:

				if (self.ui != None and self.ui.winfo_exists() == 1):
					show_error("An error occurred while connecting to the server.\n\n" + str(e))
				else:
					show_error(e, no_ui=True)

			#time.sleep(1)

			if (self.ui != None):
				self.ui.destroy()
			
			if (sc4mp_current_server != None):
				sc4mp_config["GENERAL"]["default_host"] = self.server.host
				sc4mp_config["GENERAL"]["default_port"] = self.server.port
				sc4mp_config.update()
				self.server.categories.append("History")
				game_monitor = GameMonitor(self.server)
				game_monitor.start()
			#elif (self.server == None):
			#	game_launcher = GameLauncher()
			#	game_launcher.run()
			#	if (sc4mp_ui != None):
			#		sc4mp_ui.deiconify()
			else:
				if (sc4mp_ui != None):
					sc4mp_ui.deiconify()

		except Exception as e:

			show_error(e)


	def report(self, prefix, text):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text
			self.ui.progress_bar.start(2)
			self.ui.progress_bar['mode'] = "indeterminate"
			self.ui.progress_bar['maximum'] = 100
		print(prefix + text)
		#time.sleep(1) # for testing


	def report_progress(self, text, value, maximum):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text
			self.ui.progress_bar.stop()
			self.ui.progress_bar['mode'] = "determinate"
			self.ui.progress_bar['value'] = value
			self.ui.progress_bar['maximum'] = maximum
		print(text)
		#time.sleep(.1) # for testing


	def fetch_server(self):
		"""TODO"""
		if (self.server.fetched == False):
			self.server.fetch()
			if (self.server.fetched == False):
				raise ClientException("Unable to find server. Check the IP address and port, then try again.")
		if (unformat_version(self.server.server_version)[:2] < unformat_version(SC4MP_VERSION)[:2]):
			raise ClientException(f"The server requires an outdated version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please contact the server administrators.")
		if (unformat_version(self.server.server_version)[:2] > unformat_version(SC4MP_VERSION)[:2]):
			raise ClientException(f"The server requires a newer version (v{self.server.server_version[:3]}) of the SC4MP Launcher. Please update the launcher to connect to this server.")
		if (self.ui != None):
			self.ui.title(self.server.server_name)


	def authenticate(self):
		"""TODO"""
		tries = 0
		while (not self.check_password()):
			if (sc4mp_ui):
				if (tries >= 5):
					raise ClientException("Too many password attempts.")
				if (tries > 0):
					print("[WARNING] Incorrect password.")
					#time.sleep(3) #TODO uncomment?
				PasswordDialogUI(self, tries)
				tries += 1
			else:
				raise ClientException("Incorrect password.")
		self.server.authenticate()
		

	def check_password(self):
		"""TODO"""
		if (self.server.password_enabled):
			if (self.server.password == None):
				return False
			s = self.create_socket()
			if (self.ui != None):
				self.ui.label['text'] = "Authenticating..."
			s.send(b'check_password')
			s.recv(SC4MP_BUFFER_SIZE)
			s.send(self.server.password.encode())
			if (s.recv(SC4MP_BUFFER_SIZE) == b'yes'):
				return True
			else:
				return False
		else:
			return True


	def load(self, target: str) -> None:
		"""TODO"""

		# Select the destination directory according to the parameter
		if (target == "plugins"):
			destination = Path(SC4MP_LAUNCHPATH) / "Plugins" / "server"
		elif (target == "regions"):
			destination = Path(SC4MP_LAUNCHPATH) / "Regions"

		# Create destination if necessary
		if not destination.exists():
			destination.mkdir(parents=True, exist_ok=True)

		# Synchronize or clear custom plugins
		if (target == "plugins"):
			client_plugins_source = Path(sc4mp_config["GENERAL"]["custom_plugins_path"])
			client_plugins_destination = Path(SC4MP_LAUNCHPATH) / "Plugins" / "client"
			if (self.server.user_plugins_enabled and sc4mp_config["GENERAL"]["custom_plugins"]):
				#try:
				self.report("", "Synchronizing custom plugins...")
				destination_relpaths = get_fullpaths_recursively(client_plugins_destination)
				for relpath in destination_relpaths:
					if not Path(client_plugins_source, relpath).exists():
						filename = Path(client_plugins_destination) / relpath
						print(f'- removing "{filename}"')
						filename.unlink()
				source_relpaths = get_relpaths_recursively(client_plugins_source)
				source_size = directory_size(client_plugins_source)
				destination_size = 0
				for relpath in source_relpaths:
					percent = math.floor(100 * (destination_size / source_size))
					self.report_progress(f'Synchronizing custom plugins... ("{percent}%)', percent, 100)
					src = client_plugins_source / relpath
					dest = client_plugins_destination / relpath
					destination_size += src.stat().st_size
					if dest.exists():
						if md5(src) == md5(dest):
							print(f'- verified "{dest}"')
							continue
						else:
							print(f'- removing "{dest}"')
							dest.unlink()
					print(f'- copying "{src}"')
					dest.parent.mkdir(parents=True, exist_ok=True)
					shutil.copy(src, dest)
				#shutil.copytree(sc4mp_config["GENERAL"]["custom_plugins_path"], client_plugins_destination, dirs_exist_ok=True) #zzz_SC4MP
				#except:
				#	raise ClientException("Unexpected error while loading custom plugins.")
			else:
				try:
					self.report("", "Clearing custom plugins...")
					purge_directory(client_plugins_destination)
				except: #ClientException:
					pass
					#raise ClientException("Simcity 4 is already running!")

		# Purge the destination directory
		self.report("", f"Synchronizing {target}...") #"", "Purging " + type + " directory...")
		try:
			purge_directory(destination)
		except ClientException:
			raise ClientException("Simcity 4 is already running!")

		# Create the socket
		s = self.create_socket() 

		# Request the type of data
		s.send(target.encode())

		# Request header
		if self.server.private:
			request_header(s, self.server)

		# Receive file count
		file_count = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive file size
		size = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Receive files
		size_downloaded = 0
		for files_received in range(file_count):
			percent = math.floor(100 * (size_downloaded / size))
			self.report_progress(f"Synchronizing {target}... ({percent}%)", percent, 100)
			s.send(SC4MP_SEPARATOR)
			size_downloaded += self.receive_or_cached(s, destination)
		self.report_progress(f"Synchronizing {target}... (100%)", 100, 100)

		#print("done.")

		
	'''def old_load(self, type):
		"""TODO"""

		host = self.server.host
		port = self.server.port
		server_id = self.server.server_id

		directory = None
		if (type == "plugins"):
			directory = "Plugins"
		elif (type == "regions"):
			directory = "Regions"

		self.report("", "Purging " + type + " directory...")
		purge_directory(os.path.join(SC4MP_LAUNCHPATH, directory))

		s = self.create_socket() 

		s.send(type.encode())

		filename = os.path.join(SC4MP_LAUNCHPATH, os.path.join("_Cache", os.path.join(directory, server_id + ".zip")))

		client_hashcode = None
		if (os.path.exists(filename)):
			client_hashcode = md5(filename)

		server_hashcode = ""
		try:
			server_hashcode = s.recv(SC4MP_BUFFER_SIZE).decode()
		except:
			self.report("", "Error reading server hashcode for " + type + ".")

		if (client_hashcode == server_hashcode):
			s.send(b"cached")
			self.report("", "Using cached " + type + "...")
		else:	
			s.send(b"not cached")
			self.report("", "Fetching " + type + "...")
			self.receive_file(s, filename) 

		self.report("", "Unpacking " + type + "...")
		shutil.unpack_archive(filename, os.path.join(SC4MP_LAUNCHPATH, directory))

		print("done.")'''


	def create_socket(self):
		"""TODO"""

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		tries_left = 6

		while(True):

			try:

				self.report("", "Connecting...")
				s.connect((host, port))

				self.report("", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					show_error(e, no_ui=True)

					count = 5
					while(count > 0):
						self.report("[ERROR] ", f"Connection failed. Retrying in {count}...")
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					raise ClientException("Maximum connection tries exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

		return s


	def receive_or_cached(self, s, rootpath):
		"""TODO"""

		# Receive hashcode and set cache filename
		hash = s.recv(SC4MP_BUFFER_SIZE).decode()
		target = Path(SC4MP_LAUNCHPATH) / "_Cache" / hash

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive relative path and set the destination
		relpath = Path(s.recv(SC4MP_BUFFER_SIZE).decode())
		destination = Path(rootpath) / relpath

		# Use the cached file if it exists and has the same size
		if (target.exists() and target.stat().st_size == filesize):

			print(f'- using cached "{hash}"')

			# Tell the server that the file is cached
			s.send(b"cached")

			# Create the destination directory if necessary
			destination.parent.mkdir(parents=True, exist_ok=True)

			# Delete the destination file if it exists
			destination.unlink(missing_ok=True)

			# Copy the cached file to the destination
			shutil.copy(target, destination)

		else:

			print(f'- caching "{hash}"...')

			# Tell the server that the file is not cached
			s.send(b"not cached")

			# Create the destination directory if necessary
			destination.parent.mkdir(parents=True, exist_ok=True)

			# Delete the destination file if it exists
			destination.unlink(missing_ok=True)

			# Delete the cache file if it exists
			target.unlink(missing_ok=True)

			# Delete cache files if cache too large to accomadate the new cache file
			cache_directory = Path(SC4MP_LAUNCHPATH) / "_Cache"
			while (any(cache_directory.iterdir()) and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize):
				random_cache = random.choice(list(cache_directory.iterdir()))
				random_cache.unlink()

			# Receive the file. Write to both the destination and cache
			filesize_read = 0
			with destination.open("wb") as dest, target.open("wb") as cache:
				while (filesize_read < filesize):
					bytes_read = s.recv(SC4MP_BUFFER_SIZE)
					if not bytes_read:
						break
					for file in [dest, cache]:
						file.write(bytes_read)
					filesize_read += len(bytes_read)
				
		# Return the file size
		return filesize


	def receive_file(self, s: socket.socket, filename: Path) -> None:
		"""TODO: unused function?"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print("Receiving " + str(filesize) + " bytes...")
		print('writing to "' + filename + '"')

		filename.unlink(missing_ok=True)

		filesize_read = 0
		with filename.open("wb") as f:
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				self.report_progress(f'Downloading "{filename}" ({filesize_read} / {filesize} bytes)...', int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def prep_regions(self):
		"""TODO"""

		# Declare instance variable to store the paths of the server region subdirectories
		self.server.regions: list[Path] = []

		# Path to regions directory
		region_dir = Path(SC4MP_LAUNCHPATH) / "Regions"

		# Loop through the server regions, add them to the server regions instance variable and add prefixes to the region names in the region config files
		for child in region_dir.iterdir():
			if child.is_dir():
				self.server.regions.append(child)
				config_path = region_dir / child / "region.ini"
				prep_region_config(config_path)

		# Copy the latest failed save push into the region downloads subdirectory
		downloads_path = region_dir / "downloads"
		downloads_path.mkdir(exist_ok=True, parents=True)

		try:
			salvage_directory = Path(SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id
			save_directory = os.path.join(salvage_directory, os.listdir(salvage_directory)[-1]) # TODO: this picks an arbitrary directory?
			region_directory = os.path.join(save_directory, os.listdir(save_directory)[0]) # TODO: arbitrary directory?
			for filename in os.listdir(region_directory):
				shutil.copy(os.path.join(region_directory, filename), os.path.join(downloads_path, filename))
		except Exception as e:
			pass
			#show_error(e, no_ui=True)

		# Create the refresh auxiliary region
		refresh_path = region_dir / "ZZZRefreshAuxiliary" #TODO possible name conflict!
		refresh_path.mkdir(parents=True)
		shutil.copy(get_sc4mp_path("refresh-config.bmp"), refresh_path / "config.bmp")
		shutil.copy(get_sc4mp_path("refresh-region.ini"), refresh_path / "region.ini")


class GameMonitor(th.Thread):
	"""TODO"""


	def __init__(self, server):
		"""TODO"""

		th.Thread.__init__(self)

		self.server = server
		self.city_paths, self.city_hashcodes = self.get_cities()

		self.PREFIX = ""

		self.ui = None
		if (sc4mp_ui != None):
			self.ui = GameMonitorUI()
			self.ui.title(server.server_name)

		self.game_launcher = GameLauncher()
		self.game_launcher.start()


	def run(self):
		"""TODO"""

		# Catch all errors and show an error message
		try:

			# Declare variable to break loop after the game closes
			end = False

			cfg_hashcode = None
			old_refresh_region_open = False

			# Set initial status in ui
			self.report_quietly("Welcome, start a city and save to claim a tile.") #Ready. #"Monitoring for changes...")
			
		
			# Infinite loop that can be broken by the "end" variable
			while (True):

				# Catch all errors and show an error message in the console
				try:

					# Ping the server
					ping = self.ping()

					# If the server is responsive print the ping in the console and display the ping in the ui
					if (ping != None):
						print(f"Ping: {ping}")
						if (self.ui != None):
							self.ui.ping_frame.right['text'] = f"{ping}ms"
					
					# If the server is unresponsive print a warning in the console and update the ui accordingly
					else:
						print("[WARNING] Disconnected.")
						if (self.ui != None):
							self.ui.ping_frame.right['text'] = "Server unresponsive."

					#new_city_paths, new_city_hashcodes = self.get_cities()
					
					# Array of savegames to push to the server
					save_city_paths = []

					# Print statements for debugging
					#print("Old cities: " + str(self.city_paths))
					#print("New cities: " + str(new_city_paths))

					# Will be used to store the amount of savegames detected in the previous iteration of the following while loop (-1 means the while loop will always run at least one time!)
					save_city_paths_length = -1

					# Loop until no new/modified savegames were found in the last iteration of the loop (meant to prevent fragmented save pushes, not the best solution because it relies somewhat on the loop delay)
					while (len(save_city_paths) != save_city_paths_length):

						# Update the new/modified savegame counter
						save_city_paths_length = len(save_city_paths)

						# Store the paths and hashcodes of savegames in the "Regions" directory to two local arrays
						new_city_paths, new_city_hashcodes = self.get_cities() #TODO I think this should be here...?
						
						# Loop through the paths of the savegames currently found in the "Regions" directory
						for new_city_path in new_city_paths:
							
							# If it's a new savegame, add it to the list of savegames to be pushed to the server
							if (not new_city_path in self.city_paths):
								save_city_paths.append(new_city_path)
							
							# If it's not a new savegame, check if it's a modified savegame. If so, add it to the same list
							else:
								city_hashcode = self.city_hashcodes[self.city_paths.index(new_city_path)]
								new_city_hashcode = new_city_hashcodes[new_city_paths.index(new_city_path)]
								if (city_hashcode != new_city_hashcode):
									save_city_paths.append(new_city_path)

						# For future comparisons
						self.city_paths = new_city_paths
						self.city_hashcodes = new_city_hashcodes

						if (len(save_city_paths) > 0):
							
							# Report waiting to sync if new/modified savegames found
							self.report("", "Saving...") #Scanning #Waiting to sync
							
							# Wait
							time.sleep(6) #5 #6 #10 #3 #TODO make configurable?
					
					# If there are any new/modified savegame files, push them to the server. If errors occur, log them in the console and display a warning
					if (len(save_city_paths) > 0):
						try:
							self.push_save(save_city_paths)
						except Exception as e:
							show_error(e, no_ui=True)
							self.report("[WARNING] ", "Save push failed! Unexpected client-side error.")
						time.sleep(6)

					# Break the loop when signaled
					if (end == True):
						break

					# Signal to break the loop when the game is no longer running
					if (not self.game_launcher.game_running):
						end = True

					# Wait
					time.sleep(3) #1 #3

					# Refresh
					cfg_path = get_sc4_cfg_path()
					try:
						new_cfg_hashcode = md5(cfg_path)
						if (cfg_hashcode != None and new_cfg_hashcode != cfg_hashcode):
							#print("Region switched!")
							new_refresh_region_open = refresh_region_open()
							if (new_refresh_region_open and (not old_refresh_region_open)):
								#print("Refresh regions!")
								if (ping == None):
									self.report("[WARNING] ", "Unable to refresh regions at this time.")
								else:
									old_text = self.ui.label["text"]
									self.report("", "Refreshing...")
									if (sc4mp_ui):
										regions_refresher_ui = RegionsRefresherUI(self.server)
										regions_refresher_ui.worker.run()
										try:
											regions_refresher_ui.destroy()
										except:
											pass
									else:
										regions_refresher = RegionsRefresher(None, self.server)
										regions_refresher.run()
									self.city_paths, self.city_hashcodes = self.get_cities()
									self.report("", "Regions refreshed at " + datetime.now().strftime("%H:%M") + ".")
									#self.ui.label["text"] = old_text
							old_refresh_region_open = new_refresh_region_open
						cfg_hashcode = new_cfg_hashcode
					except Exception as e:
						show_error(e, no_ui=True)
					# Refresh by asking the server for the hashcodes of all its savegames (excluding ones already claimed by the user) and downloading the savegames missing locally, tossing them directly into the respective region (was supposed to work but Simcity 4 actually tries to keep files of the same checksum)
					'''if (ping != None):
						old_text = self.ui.label["text"]
						self.report("", "Refreshing...")
						with self.create_socket() as s:
							self.report("", "Refreshing...")
							s.send(b'refresh')
							request_header(s, self.server)
							s.recv(SC4MP_BUFFER_SIZE)
							s.send(self.server.user_id.encode())
							timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
							file_count = 0
							while (True):
								message = s.recv(SC4MP_BUFFER_SIZE).decode()
								if (message == "done"):
									break
								else:
									hashcode = message
									#print(hashcode)
									if (hashcode in self.city_hashcodes):
										s.send(b'present')
									else:
										s.send(b'missing')
										region = s.recv(SC4MP_BUFFER_SIZE).decode()
										s.send(SC4MP_SEPARATOR)
										destination = os.path.join(SC4MP_LAUNCHPATH, "Regions", region, "_refresh_" + timestamp + "_" + str(file_count) + ".sc4")
										self.receive_file(s, destination)
										self.city_paths.append(destination)
										self.city_hashcodes.append(hashcode)
										s.send(SC4MP_SEPARATOR)
										file_count += 1
							s.close()
							print("- " + str(file_count) + " savegame(s) downloaded.")
						self.ui.label["text"] = old_text'''
					
				except Exception as e:
					show_error(e, no_ui=True)
					time.sleep(5) #3
			
			# Destroy the game monitor ui if running
			if (self.ui != None):
				self.ui.destroy()

			# Show the main ui once again
			if (sc4mp_ui != None):
				sc4mp_ui.deiconify()
				sc4mp_ui.lift()

		except Exception as e:
			show_error(e)


	def get_cities(self) -> tuple[list[Path], list[str]]:
		"""TODO"""
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


	'''def push_delete(self, city_path):
		"""TODO"""

		self.report(self.PREFIX, 'Pushing deletion of "' + city_path + '"')

		city = os.path.split(city_path)[1]
		region = os.path.split(os.path.dirname(city_path))[1]

		s = self.create_socket()

		if (s == None):
			self.report(self.PREFIX, 'Unable to delete the city "' + city + '" because the server is unreachable.')
			return

		s.send(b"push_delete")

		s.recv(SC4MP_BUFFER_SIZE)
		s.send(self.server.user_id.encode())
		s.recv(SC4MP_BUFFER_SIZE)
		s.send(region.encode())
		s.recv(SC4MP_BUFFER_SIZE)
		s.send(city.encode())

		if (s.recv(SC4MP_BUFFER_SIZE).decode() == "ok"):
			self.report(self.PREFIX, "Delete push authorized") #TODO placeholder
		else:
			self.report(self.PREFIX, "Delete push not authorized") #TODO placeholder'''

	
	def receive_file(self, s: socket.socket, filename: Path):
		"""TODO: unused function?"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print(f"Receiving {filesize} bytes...")
		print(f'writing to "{filename}"')

		filename.unlink(missing_ok=True)

		filesize_read = 0
		with filename.open("wb") as f:
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				#print('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def push_save(self, save_city_paths: list[Path]) -> None:
		"""TODO"""

		# Report progress: backups
		#self.report(self.PREFIX, 'Creating backups...')
		
		# Create backups #TODO salvage
		#for save_city_path in save_city_paths:
		#	self.backup_city(save_city_path)

		# Report progress: save
		self.report(self.PREFIX, 'Saving...') #Pushing save #for "' + new_city_path + '"')

		# Salvage
		salvage_directory = Path(SC4MP_LAUNCHPATH) / "_Salvage" / self.server.server_id / datetime.now().strftime("%Y%m%d%H%M%S")
		for path in save_city_paths:
			relpath = path.relative_to(Path(SC4MP_LAUNCHPATH) / "Regions")
			filename = salvage_directory / relpath
			directory = filename.parent
			directory.mkdir(exist_ok=True, parents=True)
			shutil.copy(path, filename)

		# Create socket
		s = self.create_socket()
		if (s == None):
			self.report(self.PREFIX, 'Save push failed! Server unreachable.') #'Unable to save the city "' + new_city + '" because the server is unreachable.'
			return

		# Send save request
		s.send(b"save")
		request_header(s, self.server)
		s.recv(SC4MP_BUFFER_SIZE)

		# Send file count
		s.send(str(len(save_city_paths)).encode())
		s.recv(SC4MP_BUFFER_SIZE)

		# Send files
		for save_city_path in save_city_paths:

			# Get region and city names
			region = save_city_path.parent.name
			city = save_city_path.name
	
			# Send region name
			s.send(region.encode())
			s.recv(SC4MP_BUFFER_SIZE)

			# Send city name
			s.send(city.encode())
			s.recv(SC4MP_BUFFER_SIZE)

			# Send file
			self.send_file(s, save_city_path)
			s.recv(SC4MP_BUFFER_SIZE)

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Handle response from server
		response = s.recv(SC4MP_BUFFER_SIZE).decode()
		if (response == "ok"):
			self.report(self.PREFIX, f'Saved successfully at {datetime.now().strftime("%H:%M")}.') #TODO keep track locally of the client's claims
			shutil.rmtree(salvage_directory) #TODO make configurable
		else:
			self.report(self.PREFIX + "[WARNING] ", f"Save push failed! {response}")

		# Close socket
		s.close()


	def backup_city(self, city_path: Path) -> None:
		"""TODO"""
		region = city_path.parent.name
		city = city_path.name
		backup_directory: Path = Path(SC4MP_LAUNCHPATH) / "SC4MPBackups" / self.server.server_id / region / city
		backup_directory.mkdir(exist_ok=True, parents=True)
		destination = backup_directory / datetime.now().strftime("%Y%m%d%H%M%S")
		shutil.copy(city_path, destination.with_suffix(".sc4"))


	def create_socket(self):
		"""TODO"""

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		tries_left = 36

		while(True):

			try:

				self.report("", "Connecting...")
				s.connect((host, port))

				self.report("", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					show_error(e, no_ui=True)

					count = 5
					while(count > 0):
						self.report("[ERROR] ", f"Connection failed. Retrying in {count}...")
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					return None

		return s


	def send_file(self, s: socket.socket, filename: Path) -> None:
		"""TODO"""

		self.report_quietly("Saving...")
		print(f'Sending file "{filename}"...')

		filesize = filename.stat().st_size

		s.send(str(filesize).encode())
		s.recv(SC4MP_BUFFER_SIZE)

		with filename.open("rb") as f:
			while True:
				bytes_read = f.read(SC4MP_BUFFER_SIZE)
				if not bytes_read:
					break
				s.sendall(bytes_read)


	def ping(self):
		"""TODO"""
		return self.server.ping()


	def report(self, prefix, text):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text
		print(prefix + text)


	def report_quietly(self, text):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text


class GameLauncher(th.Thread):
	"""TODO"""


	def __init__(self):
		"""TODO"""
		super().__init__()
		self.game_running = True
		self.setDaemon(True)


	def run(self):
		"""TODO"""
		
		try:

			start_sc4()
			
			self.game_running = False

			global sc4mp_current_server
			sc4mp_current_server = None

		except Exception as e:

			show_error(e)


class RegionsRefresher(th.Thread):
	

	def __init__(self, ui, server):

		th.Thread.__init__(self)

		self.ui = ui
		self.server = server

		self.setDaemon(True)


	def run(self):
		"""TODO"""
		
		try:

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
			s.send(b"regions")

			# Request header
			if self.server.private:
				request_header(s, self.server)

			# Receive file count
			file_count = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Separator
			s.send(SC4MP_SEPARATOR)

			# Receive file size
			size = int(s.recv(SC4MP_BUFFER_SIZE).decode())

			# Receive files
			size_downloaded = 0
			for files_received in range(file_count):
				percent = math.floor(100 * (size_downloaded / size))
				self.report_progress(f'Refreshing regions... ({percent}%)', percent, 100)
				s.send(SC4MP_SEPARATOR)
				size_downloaded += self.receive_or_cached(s, destination)
			self.report_progress("Refreshing regions... (100%)", 100, 100)

			# Report
			self.report("", "Refreshing regions...")

			# Prep region configs
			for region in self.server.regions:
				prep_region_config(destination / region / "region.ini")

			# Report
			self.report("", "- done.")

			# Wait
			#time.sleep(1)

		except Exception as e:

			if (self.ui != None):
				self.ui.withdraw()

			show_error("An error occurred while refreshing regions.\n\n" + str(e))


	def report(self, prefix, text):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text
			self.ui.progress_bar.start(2)
			self.ui.progress_bar['mode'] = "indeterminate"
			self.ui.progress_bar['maximum'] = 100
		print(prefix + text)
		#time.sleep(1) # for testing


	def report_progress(self, text, value, maximum):
		"""TODO"""
		if (self.ui != None):
			self.ui.label['text'] = text
			self.ui.progress_bar.stop()
			self.ui.progress_bar['mode'] = "determinate"
			self.ui.progress_bar['value'] = value
			self.ui.progress_bar['maximum'] = maximum
		print(text)
		#time.sleep(.1) # for testing


	def create_socket(self):
		"""TODO"""

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		s.settimeout(10)

		tries_left = 6

		while(True):

			try:

				self.report("", "Connecting...")
				s.connect((host, port))

				self.report("", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					show_error(e, no_ui=True)

					count = 5
					while(count > 0):
						self.report("[ERROR] ", f"Connection failed. Retrying in {count}...")
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					raise ClientException("Maximum connection tries exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

		return s


	def receive_or_cached(self, s: socket.socket, rootpath: Path) -> int:
		"""TODO"""

		# Receive hashcode and set cache filename
		hash = s.recv(SC4MP_BUFFER_SIZE).decode()
		target = Path(SC4MP_LAUNCHPATH) / "_Cache" / hash

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive relative path and set the destination
		relpath = Path(s.recv(SC4MP_BUFFER_SIZE).decode())
		destination = rootpath / relpath

		# Use the cached file if it exists and has the same size
		if (target.exists() and target.stat().st_size == filesize):
			
			print(f'- using cached "{hash}"')

			# Tell the server that the file is cached
			s.send(b"cached")

			# Create the destination directory if necessary
			destination.parent.mkdir(parents=True, exist_ok=True)

			# Delete the destination file if it exists
			destination.unlink(missing_ok=True)

			# Copy the cached file to the destination
			shutil.copy(target, destination)

		else:

			print(f'- caching "{hash}"...')

			# Tell the server that the file is not cached
			s.send(b"not cached")

			# Create the destination directory if necessary
			destination.parent.mkdir(parents=True, exist_ok=True)

			# Delete the destination file if it exists
			destination.unlink(missing_ok=True)

			# Delete the cache file if it exists
			target.unlink(missing_ok=True)

			# Delete cache files if cache too large to accomadate the new cache file
			cache_directory = Path(SC4MP_LAUNCHPATH) / "_Cache"
			while (any(cache_directory.iterdir()) and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize):
				random_cache = random.choice(list(cache_directory.iterdir()))
				random_cache.unlink()

			# Receive the file. Write to both the destination and cache
			filesize_read = 0
			with destination.open("wb") as dest, target.open("wb") as cache:
				while (filesize_read < filesize):
					bytes_read = s.recv(SC4MP_BUFFER_SIZE)
					if not bytes_read:
						break
					for file in [dest, cache]:
						file.write(bytes_read)
					filesize_read += len(bytes_read)
			
		# Return the file size
		return filesize


class DatabaseManager(th.Thread):
	"""TODO"""

	
	def __init__(self, filename: Path) -> None:
		"""TODO"""

		super().__init__()

		self.end = False

		self.filename = filename
		self.data = self.load_json()


	def run(self):
		"""TODO"""
	
		try:
			
			old_data = str(self.data)
			
			while (not self.end): #TODO pretty dumb way of checking if a dictionary has been modified
				try:
					time.sleep(SC4MP_DELAY)
					new_data = str(self.data)
					if (old_data != new_data):
						report(f'Updating "{self.filename}"...', self)
						self.update_json()
						report("- done.", self)
					old_data = new_data
				except Exception as e:
					show_error(e)

		except Exception as e:

			fatal_error(e)


	def load_json(self):
		"""TODO"""
		return load_json(self.filename)


	def update_json(self):
		"""TODO"""
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
	"""TODO"""


	def __init__(self):
		"""TODO"""


		#print("Initializing...")


		# Init

		super().__init__()


		# Exceptions

		self.report_callback_exception = self.show_error


		# Title

		self.title(SC4MP_TITLE)


		# Icon

		self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON)) #TODO looks bad
		#TODO taskbar icon


		# Geometry

		self.geometry("800x600")
		self.minsize(800, 600)
		self.maxsize(800, 600)
		self.grid()
		self.lift()
		center_window(self)


		# Key bindings

		self.bind("<F1>", lambda event:self.direct_connect())
		#self.bind("<F2>", lambda event:self.host()) #TODO


		# Menu

		menu = Menu(self)  
		
		launcher = Menu(menu, tearoff=0)  
		settings_submenu = Menu(menu, tearoff=0)
		settings_submenu.add_command(label="General...", command=self.general_settings)     
		settings_submenu.add_command(label="Storage...", command=self.storage_settings)    
		settings_submenu.add_command(label="SC4...", command=self.SC4_settings)
		launcher.add_cascade(label="Settings", menu=settings_submenu) 
		launcher.add_separator()
		launcher.add_command(label="Updates...", command=lambda:webbrowser.open_new_tab(SC4MP_RELEASES_URL)) 
		launcher.add_separator()
		launcher.add_command(label="Exit", command=self.quit)  
		menu.add_cascade(label="Launcher", menu=launcher)  #TODO rename to "Launcher" and put settings in cascade?

		servers = Menu(menu, tearoff=0)  
		
		#servers.add_command(label="Host...", command=self.host) #TODO
		#servers.add_separator() #TODO
		servers.add_command(label="Connect...", accelerator="F1", command=self.direct_connect)  #"Direct connect..."
		servers.add_command(label="Refresh", command=self.refresh)
		menu.add_cascade(label="Servers", menu=servers)  

		help = Menu(menu, tearoff=0)  	
		help.add_command(label="About...", command=self.about)
		help.add_command(label="Readme...", command=self.readme)
		help.add_separator()
		help.add_command(label="Logs...", command=lambda:startfile(SC4MP_LOG_PATH))
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


		# Server List

		if (SC4MP_SERVERLIST_ENABLED):
			self.server_list = ServerListUI(self)
			self.server_list.grid(row=0, column=0, padx=0, pady=0, sticky="w")
		else:
			self.label = tk.Label(self, justify="center", text='To get started, select "Servers" then "Connect..." in the menu bar and enter the hostname and port of the server you wish to connect to.')
			self.label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
	

	def show_error(self, *args):
		"""TODO"""
		#show_error("An error occurred.\n\n" + traceback.format_exception(*args)[-1])
		fatal_error()


	def to_implement(self):
		"""TODO"""
		tk.messagebox.showerror(title=SC4MP_TITLE, message="This feature is incomplete and will be available in future versions of the client.")


	def general_settings(self):
		print('"General settings..."')
		GeneralSettingsUI()

	
	def storage_settings(self):
		print('"Storage settings..."')
		StorageSettingsUI()


	def SC4_settings(self):
		"""TODO"""
		print('"SC4 settings..."')
		SC4SettingsUI()


	#def update(self):
	#	webbrowser.open_new_tab("https://github.com/kegsmr/sc4mp-client/releases/")


	def host(self):
		"""TODO"""
		print('"Host..."')
		HostUI()


	def direct_connect(self):
		"""TODO"""
		print('"Direct connect..."')
		DirectConnectUI()


	def refresh(self):
		"""TODO"""
		self.server_list.worker = ServerList(self.server_list, kill=self.server_list.worker)
		self.server_list.worker.start()


	def about(self):
		"""TODO"""
		AboutUI()


	def readme(self):
		"""TODO"""
		webbrowser.open_new_tab(SC4MP_README_PATH)


	def withdraw(self):
		super().withdraw()
		try:
			self.server_list.worker.pause = True
		except Exception as e:
			show_error(e, no_ui = True)


	def deiconify(self):
		super().deiconify()
		try:
			self.server_list.worker.pause = False
		except Exception as e:
			pass
			#show_error(e, no_ui = True)


class GeneralSettingsUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

		#print("Initializing...")

		# Init
		super().__init__()

		# Title
		self.title("General settings")

		# Icon
		self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

		# Geometry
		self.geometry('400x400')
		self.maxsize(450, 230)
		self.minsize(450, 230)
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
		self.path_frame = tk.LabelFrame(self, text="Custom plugins")		
		self.path_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="w")

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

		# Nickname frame
		'''self.nickname_frame = ttk.LabelFrame(self, text="Nickname")
		self.nickname_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10)'''

		# Nickname entry
		'''self.nickname_frame.entry = ttk.Entry(self.nickname_frame, width = 40)
		self.nickname_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=10)
		self.nickname_frame.entry.insert(0, sc4mp_config["GENERAL"]["nickname"])
		self.config_update.append((self.nickname_frame.entry, "nickname"))'''

		#TODO explain what the nickname is used for?

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
		"""TODO"""
		path = filedialog.askdirectory(parent=self)
		if (len(path) > 0):
			self.path_frame.entry.delete(0, 'end')
			self.path_frame.entry.insert(0, path)


	def update(self):
		for item in self.config_update:
			data = item[0].get()
			key = item[1]
			update_config_value("GENERAL", key, data)
		

	def ok(self):
		"""TODO"""
		self.update()
		sc4mp_config.update()
		self.destroy()


	def reset(self):
		"""TODO"""
		if (messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning")):
			self.destroy()
			sc4mp_config.data.pop("GENERAL")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS).data
			self.__init__()


class StorageSettingsUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

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
		self.cache_size_frame.entry.insert(0, str(sc4mp_config["STORAGE"]["cache_size"]))
		self.cache_size_frame.entry.grid(row=0, column=0, columnspan=1, padx=(10,0), pady=10, sticky="w")
		self.config_update.append((self.cache_size_frame.entry, "cache_size"))

		# Cache size label
		self.cache_size_frame.label = ttk.Label(self.cache_size_frame, text="mb")
		self.cache_size_frame.label.grid(row=0, column=1, columnspan=1, padx=(2,10), pady=10, sticky="w")

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
		"""TODO"""
		#if (messagebox.askokcancel(title=SC4MP_TITLE, message="Clear the download cache?", icon="warning")): #TODO make yes/no
		purge_directory(Path(SC4MP_LAUNCHPATH) / "_Cache")


	def browse_path(self):
		"""TODO"""
		path = filedialog.askdirectory(parent=self)
		if (len(path) > 0):
			self.path_frame.entry.delete(0, 'end')
			self.path_frame.entry.insert(0, path)


	def update(self):
		for item in self.config_update:
			data = item[0].get()
			key = item[1]
			if (key == "storage_path" and type(data) is str and not data == sc4mp_config["STORAGE"]["storage_path"]):
				if (Path(data) / 'Plugins').exists() or (Path(data) / 'Regions').exists():
					if (not messagebox.askokcancel(title=SC4MP_TITLE, message=f'The directory "{data}" already contains Simcity 4 plugins and regions. \n\nProceeding will result in the IRREVERSIBLE DELETION of these files! \n\nThis is your final warning, do you wish to proceed?', icon="warning")): #TODO make message box show yes/no and not ok/cancel
						raise ClientException("Operation cancelled by user.")
			update_config_value("STORAGE", key, data)
		create_subdirectories()
		load_database()
		

	def ok(self):
		"""TODO"""
		try:
			self.update()
			sc4mp_config.update()
			self.destroy()
		except ClientException:
			pass


	def reset(self):
		"""TODO"""
		if (messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning")): #TODO make yes/no
			self.destroy()
			sc4mp_config.data.pop("STORAGE")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS).data
			self.__init__()


class SC4SettingsUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

		#print("Initializing...")

		# Init
		super().__init__()

		# Title
		self.title("SC4 settings")

		# Icon
		self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON)) #TODO looks bad

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
		self.path_frame.label = ttk.Label(self.path_frame, text='If the launcher fails to find Simcity 4 installed on your computer, \nspecify the path to the game installation here.')
		self.path_frame.label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10))

		# Resolution frame
		self.resolution_frame = tk.LabelFrame(self, text="Resolution")		
		self.resolution_frame.grid(row=1, column=0, columnspan=1, rowspan=2, padx=10, pady=5, sticky="w")

		# Resolution combo box
		self.resolution_frame.combo_box = ttk.Combobox(self.resolution_frame, width=15)
		self.resolution_frame.combo_box.insert(0, str(sc4mp_config["SC4"]["resw"]) + "x" + str(sc4mp_config["SC4"]["resh"]))
		self.resolution_frame.combo_box["values"] = ("800x600 (4:3)", "1024x768 (4:3)", "1280x1024 (4:3)", "1600x1200 (4:3)", "1280x800 (16:9)", "1440x900 (16:9)", "1680x1050 (16:9)", "1920x1080 (16:9)", "2048x1152 (16:9)")
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
		self.cpu_priority_frame.combo_box = ttk.Combobox(self.cpu_priority_frame, width = 8)
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
		"""TODO"""
		path = filedialog.askdirectory(parent=self)
		if (len(path) > 0):
			self.path_frame.entry.delete(0, 'end')
			self.path_frame.entry.insert(0, path)


	def update(self):
		for item in self.config_update:
			data = item[0].get()
			key = item[1]
			if (key == "res"):
				res = data.split(' ')[0]
				resw, resh = res.split('x')
				update_config_value("SC4", "resw", resw)
				update_config_value("SC4", "resh", resh)
			else:
				update_config_value("SC4", key, data)
		

	def ok(self):
		"""TODO"""
		self.update()
		sc4mp_config.update()
		self.destroy()


	def reset(self):
		"""TODO"""
		if (messagebox.askokcancel(title=SC4MP_TITLE, message="Revert settings to the default configuration?", icon="warning")):
			self.destroy()
			sc4mp_config.data.pop("SC4")
			sc4mp_config.update()
			sc4mp_config.data = Config(sc4mp_config.PATH, sc4mp_config.DEFAULTS).data
			self.__init__()


	def preview(self):
		"""TODO"""

		# Hide the settings window and main ui
		self.withdraw()
		sc4mp_ui.withdraw()

		# Backup the current config data
		config_data_backup = sc4mp_config["SC4"].copy()

		# Update the config
		self.update()

		# Load the game
		try:

			# Check if a path to Simcity 4 can be found, prompt for a custom path if needed
			while (get_sc4_path() == None):
				show_warning('No Simcity 4 installation found. \n\nPlease provide the correct installation path.')
				path = filedialog.askdirectory(parent=sc4mp_ui)
				if (len(path) > 0):
					sc4mp_config["SC4"]["game_path"] = path
					self.path_frame.entry.delete(0, 'end')
					self.path_frame.entry.insert(0, path)
				else:
					break
			
			# Load the game if a path to Simcity 4 can be found
			if (get_sc4_path() != None):

				# Purge plugins and regions
				purge_directory(Path(SC4MP_LAUNCHPATH) / "Plugins")
				purge_directory(Path(SC4MP_LAUNCHPATH) / "Regions")
				
				# Run the game launcher (on the current thread)
				game_launcher = GameLauncher()
				game_launcher.run()

		# Catch any and all errors
		except Exception as e:

			# Show an error popup
			show_error("An error occurred.\n\n" + str(e))

		# Restore the old config data
		sc4mp_config["SC4"] = config_data_backup

		# Show and lift the main ui and settings ui once the game has shutdown
		sc4mp_ui.deiconify()
		sc4mp_ui.lift()
		self.deiconify()
		self.lift()


class HostUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

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
		"""TODO"""

		#TODO

		return
	

	def config(self):
		"""TODO"""

		#TODO

		return
	

	def files(self):
		"""TODO"""

		#TODO

		return
	

	def new(self):
		"""TODO"""

		#TODO

		return


	def ok(self):
		"""TODO"""

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
		"""TODO"""
		print('"Connect"')
		host = self.host_entry.get()
		port = self.port_entry.get()
		try:
			if (len(host) < 1):
				host = SC4MP_HOST
				#raise ClientException("Invalid host")
			try:
				port = int(port)
			except:
				port = SC4MP_PORT
				#raise ClientException("Invalid port")
			ServerLoaderUI(Server(host, port))
			self.destroy()
		except Exception as e:
			show_error(e)


class PasswordDialogUI(tk.Toplevel):

	
	def __init__(self, server_loader, tries):
		
		print("Initializing...")

		# Parameters
		self.server_loader = server_loader
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

		# OK/Cancel frame
		self.ok_cancel = tk.Frame(self)
		self.ok_cancel.grid(row=1, column=3, sticky="e")

		# OK button
		self.ok_cancel.ok_button = ttk.Button(self.ok_cancel, text="Ok", command=self.ok, default="active")
		self.ok_cancel.ok_button.grid(row=0, column=0, columnspan=1, padx=3, pady=5, sticky="w")

		# Cancel button
		self.ok_cancel.cancel_button = ttk.Button(self.ok_cancel, text="Cancel", command=self.cancel)
		self.ok_cancel.cancel_button.grid(row=0, column=1, columnspan=1, padx=7, pady=5, sticky="e")

		# Update loop
		self.wait = True
		while (self.wait):
			if (len(self.password_entry.get()) < 1):
				self.ok_cancel.ok_button['state'] = tk.DISABLED
			else:
				self.ok_cancel.ok_button['state'] = tk.NORMAL
			time.sleep(SC4MP_DELAY)


	def ok(self):
		"""TODO"""
		password = self.password_entry.get()
		if (len(password) > 0):
			self.server_loader.server.password = password
			self.wait = False
			self.destroy()
			self.server_loader.ui.deiconify()


	def cancel(self):
		"""TODO"""
		self.server_loader.ui.destroy()
		self.wait = False
		self.destroy()


class AboutUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

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
		self.canvas.grid(row=0, column=0, rowspan=5, columnspan=1, padx=10, pady=(10,0), sticky="n")

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
		"""TODO"""
		self.destroy()


class ServerListUI(tk.Frame):
	"""ServerList UI wrapper.

	Arguments:
		TODO

	Returns:
		TODO
	"""


	def __init__(self, root):
		"""TODO"""


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
		self.canvas.grid(row=0, column=0, rowspan=1, columnspan=2, padx=0, pady=0)


		# Label

		self.label = ttk.Label(self)
		self.label.grid(row=1, column=0, rowspan=1, columnspan=2, padx=10, pady=(15, 10))
		#self.label['text'] = 'Loading...' #'To get started, select a server below and click "Connect."' #"Loading server list..."


		# Frame

		self.frame = tk.Frame(self)
		self.frame.grid(row=2, column=0, rowspan=1, columnspan=2, padx=15, pady=10, sticky="n")


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
				"Rating",
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

		self.tree.bind("<Double-1>", self.handle_double_click) #lambda event: self.connect())
		self.tree.bind("<Button-1>", self.handle_single_click)

		self.tree.sort = "Rating"
		self.tree.reverse_sort = False

		self.tree.focus_set()

		self.tree.pack(side="left")


		# Scrollbar

		self.scrollbar = ttk.Scrollbar(self.frame, orient ="vertical", command = self.tree.yview)
		self.scrollbar.pack(side="right", fill="y")
		self.tree.configure(yscrollcommand=self.scrollbar.set)


		# Server info frame

		self.server_info = tk.Frame(self, width=540, height=120)
		self.server_info.grid(row=3, column=0, padx=20, pady=0, sticky="nw")
		self.server_info.grid_propagate(0)


		# Description label

		self.description_label = ttk.Label(self.server_info)
		self.description_label.grid(row=0, column=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="nw")
		self.description_label['text'] = ""


		# URL label

		self.url_label = tk.Label(self.server_info, fg="blue", cursor="hand2")
		self.url_label.grid(row=1, column=0, columnspan=1, padx=0, pady=5, sticky="nw")
		self.url_label['text'] = ""
		self.url_label.bind("<Button-1>", lambda e:webbrowser.open_new_tab(self.url_label["text"]))


		# Combo box

		self.combo_box = ttk.Combobox(self, width=20)
		self.combo_box["values"] = ("category: All", "category: Official", "category: Public", "category: Private", "category: History") #"category: Favorites"
		self.combo_box.grid(row=3, column=1, rowspan=1, columnspan=1, padx=(0,15), pady=(5,10), sticky="ne")
		

		# Address label

		self.address_label = ttk.Label(self)
		self.address_label.grid(row=4, column=0, columnspan=1, padx=20, pady=10, sticky="sw")
		self.address_label['text'] = ""


		# Refresh / connect frame

		self.refresh_connect = tk.Frame(self)
		self.refresh_connect.grid(row=4, column=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="se")


		# Refresh button

		self.refresh_button = ttk.Button(self.refresh_connect, text="Refresh", command=self.root.refresh)
		self.refresh_button.grid(row=0, column=0, columnspan=1, padx=10, pady=10, sticky="se")


		# Connect button

		self.connect_button = ttk.Button(self.refresh_connect, text="Connect", command=self.connect, default="active")
		self.connect_button['state'] = tk.DISABLED
		self.connect_button.grid(row=0, column=1, columnspan=1, padx=(0,15), pady=10, sticky="se")


		# Worker
		self.worker = ServerList(self)
		self.worker.start()


	def handle_double_click(self, event):
		"""TODO"""
		region = self.tree.identify_region(event.x, event.y)
		if region == "separator":
			return "break"
		elif region == "tree" or region == "cell":
			self.connect()


	def handle_single_click(self, event):
		"""TODO"""
		region = self.tree.identify_region(event.x, event.y)
		if region == "separator":
			return "break"
		

	def handle_header_click(self, name):
		"""TODO"""
		print("Sort by \"" + name + "\"")
		DEFAULT_REVERSED = ("Name", "Claimed", "Download", "Ping")
		if (self.tree.sort == name):
			self.tree.reverse_sort = not self.tree.reverse_sort
		else:
			self.tree.sort = name
			self.tree.reverse_sort = name in DEFAULT_REVERSED
		if self.tree.reverse_sort:
			print("- (reversed)")
		self.worker.sort_mode_changed = True
		#self.worker.sort = True


	def focus_tree(self):
		"""TODO"""
		try:
			self.tree.focus_set()
			if (self.tree.focus() == ""):
				children = self.tree.get_children()
				self.tree.focus(children[0])
		except Exception as e:
			show_error(e, no_ui=True) # Method not all that important so we'll just toss an error in the console and call it a day 


	def connect(self):
		"""TODO"""
		print('"Connect"')
		server_id = self.tree.focus()
		if (server_id == ""):
			return
		server = self.worker.servers[server_id]
		host = server.host
		port = server.port
		try:
			if (len(host) < 1):
				host = SC4MP_HOST
			try:
				port = int(port)
			except:
				port = SC4MP_PORT
			ServerLoaderUI(Server(host, port))
			self.tree.focus_set()
		except Exception as e:
			show_error(e)


class ServerLoaderUI(tk.Toplevel):
	"""TODO"""


	def __init__(self, server):
		"""TODO"""

		#print("Initializing...")

		# Init
		super().__init__()

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
		self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=10)
		self.progress_bar.start(2)

		# Worker
		self.worker = ServerLoader(self, server)
		self.worker.start()


class GameMonitorUI(tk.Toplevel):
	"""TODO"""


	def __init__(self):
		"""TODO"""

		print("Initializing...")

		# Init
		super().__init__()

		# Title
		self.title(SC4MP_TITLE)

		# Icon
		self.iconphoto(False, tk.PhotoImage(file=SC4MP_ICON))

		# Geometry
		self.geometry("400x400")
		self.minsize(420, 80)
		self.maxsize(420, 80)
		self.grid()

		# Protocol
		self.protocol("WM_DELETE_WINDOW", self.disable)

		# Status frame
		self.status_frame = tk.Frame(self)
		self.status_frame.grid(column=0, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

		# Status label left
		self.status_frame.left = ttk.Label(self.status_frame, text="Status:")
		self.status_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="w")

		# Status label right
		self.status_frame.right = ttk.Label(self.status_frame, text="")
		self.status_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=10, sticky="w")
		self.label = self.status_frame.right

		# Ping frame
		self.ping_frame = tk.Frame(self)
		self.ping_frame.grid(column=0, row=1, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")

		# Ping label left
		self.ping_frame.left = ttk.Label(self.ping_frame, text="Ping:")
		self.ping_frame.left.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=0, sticky="w")

		# Ping label right
		self.ping_frame.right = ttk.Label(self.ping_frame, text="")
		self.ping_frame.right.grid(column=1, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="w")


	def disable(self):
		"""TODO"""
		pass


class GameOverlayUI(tk.Toplevel):
	"""TODO"""
	

	def __init__(self):
		"""TODO"""

		#print("Initializing...")

		# Init
		super().__init__()

		# Geometry
		self.overlay()
		self.grid()
		
		# Priority
		self.wm_attributes("-topmost", True)

		# Label
		self.label = ttk.Label(self, anchor="center")
		self.label.grid(column=0, row=0, rowspan=1, columnspan=1, padx=0, pady=0, sticky="we")
	

	def overlay(self):
		"""TODO"""
		WIDTH = 100
		HEIGHT = 20
		#screen_height = self.winfo_screenheight()
		screen_width = self.winfo_screenwidth()
		self.geometry('{}x{}+{}+{}'.format(WIDTH, HEIGHT, screen_width - WIDTH, 0))
		self.overrideredirect(True)
		self.lift()
		self.after(100, self.overlay)


class RegionsRefresherUI(tk.Toplevel):
	"""TODO"""


	def __init__(self, server):
		"""TODO"""

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
		"""TODO"""
		#print("Overlaying...")
		try:
			self.overrideredirect(True)
			self.lift()
			self.after(100, self.overlay)
		except Exception as e:
			show_error(e, no_ui=True)


# Exceptions

class ClientException(Exception):
	"""TODO"""


	def __init__(self, message, *args):
		"""TODO"""
		super().__init__(args)
		self.message = message
	

	def __str__(self):
		"""TODO"""
		return self.message


# Logger

class Logger():
	"""TODO"""
	

	def __init__(self):
		"""TODO"""
		self.terminal = sys.stdout
		self.log = Path(SC4MP_LOG_PATH)
		self.log.unlink(missing_ok=True)

	def write(self, message):
		"""TODO"""

		output = message

		if (message != "\n"):

			# Timestamp
			timestamp = datetime.now().strftime("[%H:%M:%S] ")

			# Label
			label = "[SC4MP/" + th.current_thread().getName() + "] "
			for item in inspect.stack()[1:]:
				try:
					label += "(" + item[0].f_locals["self"].__class__.__name__ + ") "
					break
				except:
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
				if (message[:len(current_type)] == current_type):
					message = message[len(current_type):]
					type = current_type
					color = current_color
					break
			if (th.current_thread().getName() == "Main" and type == "[INFO] "):
				color = '\033[00m '
			
			# Assemble
			output = color + timestamp + label + type + message

		# Print
		self.terminal.write(output)
		with open(self.log, "a") as log:
			log.write(output)
			log.close()  


	def flush(self):
		"""TODO"""
		self.terminal.flush()


# Main

if __name__ == '__main__':
	main()
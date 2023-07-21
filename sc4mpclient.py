import configparser
import hashlib
import inspect
import io
import json
import math
import os
import platform
import random
import shutil
import socket
import ipaddress
import string
import struct
import subprocess
import sys
import threading as th
import time
import tkinter as tk
import traceback
import webbrowser
from datetime import datetime
from tkinter import Menu, filedialog, font, messagebox, ttk

SC4MP_VERSION = "0.3.0"

SC4MP_SERVERS = [
	("servers.sc4mp.org", 7240), 
	("servers.sc4mp.org", 7241), 
	("servers.sc4mp.org", 7242), 
	("servers.sc4mp.org", 7243),
	("servers.sc4mp.org", 7244),
	("servers.sc4mp.org", 7245),
	("servers.sc4mp.org", 7246),
	("servers.sc4mp.org", 7247),
	("servers.sc4mp.org", 7248),
	("servers.sc4mp.org", 7249),
]

SC4MP_URL = "www.sc4mp.org"
SC4MP_CONTRIBUTORS_URL = "https://github.com/keggre/sc4mp-client/contributors/"
SC4MP_ISSUES_URL = "https://github.com/keggre/sc4mp-client/issues/"
SC4MP_RELEASES_URL = "https://github.com/keggre/sc4mp-client/releases/"

SC4MP_AUTHOR_NAME = "Simcity 4 Multiplayer Project"
SC4MP_WEBSITE_NAME = "sc4mp.org"
SC4MP_LICENSE_NAME = "MIT-0"

SC4MP_CONFIG_PATH = "config.ini"
SC4MP_LOG_PATH = "sc4mpclient.log"
SC4MP_README_PATH = "readme.html"
SC4MP_RESOURCES_PATH = "resources"

SC4MP_TITLE = "SC4MP Launcher v" + SC4MP_VERSION
SC4MP_ICON = os.path.join(SC4MP_RESOURCES_PATH, "icon.ico")

SC4MP_HOST = SC4MP_SERVERS[0][0] #socket.gethostname()
SC4MP_PORT = SC4MP_SERVERS[0][1] #7240

SC4MP_SEPARATOR = b"<SEPARATOR>"
SC4MP_BUFFER_SIZE = 4096

SC4MP_DELAY = .1

SC4MP_SERVERLIST_ENABLED = True #TODO

SC4MP_CONFIG_DEFAULTS = [
	("GENERAL", [
		("nickname", os.getlogin()), #TODO unused
		#(first_run, True) #TODO
		#("use_custom_user_id", False), #TODO
		#("custom_user_id", ""), #TODO
		("default_host", SC4MP_HOST),
		("default_port", SC4MP_PORT),
		#("use_overlay", 1), #TODO
		("custom_plugins", False), #TODO needs to be added in ui 
		("custom_plugins_path", os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","Plugins")) #TODO needs to be added in ui 
	]),
	("STORAGE", [
		("storage_path", os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","_SC4MP") + "\\"),
		("cache_size", 16000)
	]),
	("SC4", [
		("game_path", ""),
		("fullscreen", False),
		("resw", 1280),
		("resh", 800),
		("cpu_count", 1),
		("cpu_priority", "normal"),
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

def prep():
	"""Prepares the client to launch."""
	
	load_config()
	create_subdirectories()


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


def create_subdirectories():
	"""Creates the required subdirectories in the launch directory if they do not yet exist."""

	print("Creating subdirectories...")

	directories = ["_Cache", "_Profiles", "_Salvage", "Plugins", os.path.join("Plugins", "server"), os.path.join("Plugins", "client"), "Regions"] #"SC4MPBackups", os.path.join("_Cache","Plugins"), os.path.join("_Cache","Regions")]

	for directory in directories:
		new_directory = os.path.join(SC4MP_LAUNCHPATH, directory)
		if not os.path.exists(new_directory):
			try:
				os.makedirs(new_directory)
			except Exception as e:
				raise CustomException("Failed to create SC4MP subdirectories.\n\n" + str(e))
		"""if directory == "Plugins":
			noticepath = os.path.join(SC4MP_LAUNCHPATH, directory, "__PUT YOUR PLUGINS IN THIS FOLDER__.txt")
			open(noticepath, 'a').close()"""


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


def get_sc4_path():
	"""Returns the path to the Simcity 4 executable if found."""

	possiblePaths = [
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Origin Games", "SimCity 4 Deluxe Edition", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Origin Games", "SimCity 4 Deluxe Edition", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		sc4mp_config['SC4']['game_path'],
		os.path.join(sc4mp_config['SC4']['game_path'], "SimCity 4.exe"),
		os.path.join(sc4mp_config['SC4']['game_path'], "Apps", "SimCity 4.exe")
	]

	path = None

	for possiblePath in possiblePaths:
		if possiblePath:
			if os.path.isfile(possiblePath):
				path = '"' + possiblePath + '"'
				break

	return path


def start_sc4():
	"""Attempts to find the install path of Simcity 4 and launches the game with custom launch parameters if found."""

	print("Starting Simcity 4...")

	path = get_sc4_path()

	if not path:
		show_error("Path to Simcity 4 not found. Specify the correct path in settings.")
		return

	arguments = [path, '-UserDir:"' + SC4MP_LAUNCHPATH + '"', '-intro:off', '-CustomResolution:enabled', '-r' + str(sc4mp_config["SC4"]["resw"]) + 'x' + str(sc4mp_config["SC4"]["resh"]) + 'x32', "-CPUCount:" + str(sc4mp_config["SC4"]["cpu_count"]), "-CPUPriority:" + sc4mp_config["SC4"]["cpu_priority"]]

	if (sc4mp_config["SC4"]["fullscreen"] == True):
		arguments.append('-f')
	else:
		arguments.append('-w')

	arguments.append(sc4mp_config["SC4"]["additional_properties"])

	command = ' '.join(arguments)
	print("'" + command + "'")

	try:
		subprocess.run(command)
	except PermissionError as e:
		show_error("Permission denied. Run the program as administrator.\n\n" + str(e))

	# For compatability with the steam version of SC4
	time.sleep(3)
	while (process_exists("simcity 4.exe")):
		time.sleep(1)

	print("Simcity 4 closed.")


def process_exists(process_name): #TODO add macos and linux compatability
	"""TODO"""
	if (platform.system() == "Windows"):
		call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
		output = subprocess.check_output(call, shell=True).decode()
		last_line = output.strip().split('\r\n')[-1]
		return last_line.lower().startswith(process_name.lower())
	else:
	    return False


def get_sc4mp_path(filename):
	"""Returns the path to a given file in the SC4MP "resources" subdirectory"""
	return os.path.join(SC4MP_RESOURCES_PATH, filename)


def md5(filename):
	"""Returns an md5 hashcode generated from a given file."""
	hash_md5 = hashlib.md5()
	with open(filename, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def random_string(length):
	"""Returns a random string of ascii letters of the specified length."""
	return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(length))


def purge_directory(directory):
	"""Deletes every file within a directory."""
	for filename in os.listdir(directory):
		file_path = os.path.join(directory, filename)
		try:
			if os.path.isfile(file_path) or os.path.islink(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path):
				shutil.rmtree(file_path)
		except PermissionError as e:
			raise CustomException('Failed to delete "' + file_path + '" because the file is being used by another process.') #\n\n' + str(e)


def directory_size(directory):
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
			if (data == None):
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

	print("[ERROR] " + message + "\n\n" + traceback.format_exc())

	if (not no_ui):
		if (sc4mp_ui != None):
			if (sc4mp_ui == True):
				tk.Tk().withdraw()
			messagebox.showerror(SC4MP_TITLE, message)


def fatal_error():
	"""Shows a fatal error message in the console and the UI. Exits the program."""

	message = "A fatal error occurred.\n\n" + traceback.format_exc()

	print("[FATAL] " + message)

	if (sc4mp_ui != None):
		if (sc4mp_ui == True):
			tk.Tk().withdraw()
		messagebox.showerror(SC4MP_TITLE, message)

	sys.exit()


def show_warning(e):
	"""Shows a warning in the console and the UI."""
	message = None
	if (isinstance(e, str)):
		message = e
	else: 
		message = str(e)

	print("[WARNING] " + message)

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
	win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
	win.deiconify()


def prep_server(path):
	"""Runs the server executable in prep mode. Takes the server path as an argument."""
	subprocess.Popen("sc4mpserver.exe -prep --server-path " + str(path))


def start_server(path):
	"""Runs the server executable. Takes the server path as an argument."""
	subprocess.Popen("sc4mpserver.exe --server-path " + str(path), creationflags=subprocess.CREATE_NEW_CONSOLE)

	#th.Thread(target=lambda: subprocess.Popen("sc4mpserver.exe --server-path " + str(path))).start()


def update_config_value(section, item, value):
	"""Updates a value in the config, attempting to convert it to the proper data type."""
	try:
		t = type(sc4mp_config[section][item])
		sc4mp_config[section][item] = t(value)
	except:
		show_error("Invalid config value for \"" + item + "\" in section \"" + section + "\"", no_ui=True)


def get_fullpaths_recursively(path):
	"""Returns full paths of all files in a directory recursively."""
	fullpaths = []
	for path, directories, files in os.walk(path):
		for file in files:
			fullpaths.append(os.path.join(path, file))
	return fullpaths


def get_relpaths_recursively(path):
	"""Returns relative paths of all files in a directory recursively."""
	fullpaths = get_fullpaths_recursively(path)
	relpaths = []
	for fullpath in fullpaths:
		relpaths.append(os.path.relpath(fullpath, path))
	return relpaths


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


def format_version(version):
	"""Converts a version number from a tuple to a string."""
	return str(version[0]) + "." + str(version[1]) + "." + str(version[2])


def unformat_version(version):
	"""Converts a version number from a string to a tuple."""
	strings = version.split(".")
	ints = []
	for string in strings:
		ints.append(int(string))
	return tuple(ints)


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


def get_sc4_cfg_path(): #TODO can this find the cfg for the origin version?
	"""TODO"""
	return os.path.join(SC4MP_LAUNCHPATH, "simcity 4.cfg")


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
		show_error("Failed to prep region config at " + path + ".")


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
		self.password = None
		self.user_id = None


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

		#if (self.server_version != None):
		#	self.server_version = unformat_version(self.server_version)

		if (self.fetched == True):
			try:
				self.update_database()
			except Exception as e:
				show_error(e, no_ui = True)


	def fetch_stats(self):
		"""TODO"""

		# Request server info
		self.stat_mayors = (random.randint(0,1000)) #TODO
		self.stat_mayors_online = int(self.stat_mayors * (float(random.randint(0, 100)) / 100)) #TODO
		self.stat_claimed = (float(random.randint(0, 100)) / 100) #TODO
		self.stat_download = (random.randint(0, 10 ** 11)) #TODO
		self.stat_ping = self.ping()


	def update_database(self):
		"""Updates the json entry for the server."""

		# Get database
		filename = os.path.join(SC4MP_LAUNCHPATH, "_Profiles", "servers.json")
		data = None
		try:
			data = load_json(filename)
		except:
			data = dict()

		# Get database entry for server
		key = self.server_id
		entry = data.get(key, dict())
		if (entry == None):
			entry = dict()
		data[key] = entry

		# Set values in database entry
		set_server_data(entry, self)

		# Update database
		update_json(filename, data)


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
			print('[WARNING] Unable to fetch "' + request + '" from ' + host + ":" + str(port) + '')
			return None


	def authenticate(self):
		"""TODO"""

		# Get database
		filename = os.path.join(SC4MP_LAUNCHPATH, "_Profiles", "servers.json")
		data = None
		try:
			data = load_json(filename)
		except:
			data = dict()

		# Get database entry for server
		key = self.server_id
		entry = data.get(key, dict())
		if (entry == None):
			entry = dict()
		data[key] = entry

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
				raise CustomException("Invalid token.") #"Authentication error."
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
			raise CustomException("You are banned from this server.")

		# Set user_id and token in the database entry
		entry["user_id"] = user_id
		entry["token"] = token
		entry.setdefault("first_logon", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
		entry["last_logon"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		# Update database
		update_json(filename, data)


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


class DBPF:
	"""TODO include credits to original php file"""


	def __init__(self, filename, offset=0):
		"""TODO"""

		report('Parsing "' + filename + '"...', self)

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

		report('Parsing region view subfile of "' + self.filename + '"...', self)

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


	def __init__(self, ui):
		"""TODO"""

		th.Thread.__init__(self)

		self.ui = ui

		self.setDaemon(True)

		self.end = False
		self.ended = False

		self.servers = dict()

		self.unfetched_servers = SC4MP_SERVERS.copy()
		
		#TODO get lan
		#for offset in range(64512):
		#	pass

		data = load_json(os.path.join(SC4MP_LAUNCHPATH, "_Profiles", "servers.json"))
		for key in data.keys():
			self.unfetched_servers.append((data[key]["host"], data[key]["port"]))

		self.fetched_servers = []
		self.tried_servers = []

		self.stat_mayors = []
		self.stat_mayors_online = []
		self.stat_claimed = []
		self.stat_download = []
		self.stat_ping = []


	def run(self):
		"""TODO"""

		try:

			print("Fetching servers...")

			while (self.end == False):

				# Enable or disable connect button and update labels
				if (self.ui.tree.focus() == ""):
					self.ui.connect_button['state'] = tk.DISABLED
				else:
					self.ui.connect_button['state'] = tk.NORMAL
					self.ui.address_label["text"] = self.servers[self.ui.tree.focus()].host + ":" + str(self.servers[self.ui.tree.focus()].port)
					self.ui.description_label["text"] = self.servers[self.ui.tree.focus()].server_description
					self.ui.url_label["text"] = self.servers[self.ui.tree.focus()].server_url
					
				# Fetch the next unfetched server
				if (len(self.unfetched_servers) > 0):
					unfetched_server = self.unfetched_servers.pop(0)
					if (unfetched_server not in self.tried_servers):
						self.tried_servers.append(unfetched_server)
						ServerFetcher(self, Server(unfetched_server[0], unfetched_server[1])).start()

				# Add all fetched servers to the server dictionary if not already present
				while (len(self.fetched_servers) > 0):
					fetched_server = self.fetched_servers.pop(0)
					if (fetched_server.server_id not in self.servers.keys()):
						self.servers[fetched_server.server_id] = fetched_server

				# Update the treeview
				new_rows = False
				for key in self.servers.keys():
					if (not self.ui.tree.exists(key)):
						self.ui.tree.insert('', 'end', key, values=self.format_server(self.servers[key]))
						new_rows = True

				# Update and sort the tree
				if (new_rows):
					for key in self.servers.keys():
						self.ui.tree.item(key, values=self.format_server(self.servers[key]))
						#TODO sort

				# Delay
				time.sleep(SC4MP_DELAY)

			self.ended = True

		except Exception as e:

			show_error("An error occurred while fetching servers.\n\n" + str(e))


	def format_server(self, server):
		"""TODO"""
		self.calculate_rating(server)
		return ("", server.server_name, str(server.stat_mayors) + " (" + str(server.stat_mayors_online) + ")", str(int(server.stat_claimed * 100)) + "%", format_filesize(server.stat_download), str(server.stat_ping) + "ms", str(round(server.rating)))

	
	def calculate_rating(self, server):
		"""TODO"""
		categories = [
			self.max_category(server.stat_mayors, self.stat_mayors),
			self.max_category(server.stat_mayors_online, self.stat_mayors_online),
			self.min_category(server.stat_claimed, self.stat_claimed),
			self.min_category(server.stat_download, self.stat_download),
			self.min_category(server.stat_ping, self.stat_ping),
		]
		server.rating = 1 + (4 * sum(categories) / len(categories))

	
	def max_category(self, item, array):
		"""TODO"""
		item = float(item)
		try:
			return ((item - min(array)) / (max(array) - min(array)))
		except ZeroDivisionError:
			return 1.0


	def min_category(self, item, array):
		"""TODO"""
		item = float(item)
		try:
			return 1.0 - ((item - min(array)) / (max(array) - min(array)))
		except ZeroDivisionError:
			return 1.0


class ServerFetcher(th.Thread):


	def __init__(self, parent, server):

		th.Thread.__init__(self)

		self.parent = parent
		self.server = server

		self.setDaemon(True)


	def run(self):

		try:

			print("Fetching " + self.server.host + ":" + str(self.server.port) + "...")

			self.server_list()

			self.server.fetch()

			if (self.parent.end or (not self.server.fetched)):
				raise CustomException("")

			self.fetch_stats()

			if (self.server.stat_ping == None or (not self.server.fetched)):
				raise CustomException("")

			print("Done.")

			self.parent.fetched_servers.append(self.server)

			#TODO start server pinger

		except Exception as e:

			#show_error(e, no_ui=True)
			print("[WARNING] Failed!")


	def fetch_stats(self):
		"""TODO"""
		self.server.fetch_stats()
		if (self.server.fetched and self.server.stat_ping != None):
			self.parent.stat_mayors.append(self.server.stat_mayors)
			self.parent.stat_mayors_online.append(self.server.stat_mayors_online)
			self.parent.stat_claimed.append(self.server.stat_claimed)
			self.parent.stat_download.append(self.server.stat_download)
			self.parent.stat_ping.append(self.server.stat_ping)

	
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

			print("TODO")

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

				self.report("", 'Connecting to server at ' + str(host) + ":" + str(port) + '...')
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
				raise CustomException("Unable to find server. Check the IP address and port, then try again.")
		if (unformat_version(self.server.server_version) < unformat_version(SC4MP_VERSION)):
			raise CustomException("The server requires an outdated version (v" + format_version(self.server.server_version) + ") of the SC4MP Launcher. Please contact the server administrators.")
		if (unformat_version(self.server.server_version) > unformat_version(SC4MP_VERSION)):
			raise CustomException("The server requires a newer version (v" + format_version(self.server.server_version) + ") of the SC4MP Launcher. Please update the launcher to connect to this server.")
		if (self.ui != None):
			self.ui.title(self.server.server_name)


	def authenticate(self):
		"""TODO"""
		tries = 0
		while (not self.check_password()):
			if (sc4mp_ui):
				if (tries >= 5):
					raise CustomException("Too many password attempts.")
				if (tries > 0):
					print("[WARNING] Incorrect password.")
					#time.sleep(3) #TODO uncomment?
				PasswordDialogUI(self, tries)
				tries += 1
			else:
				raise CustomException("Incorrect password.")
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


	def load(self, type):
		"""TODO"""

		# Select the destination directory according to the parameter
		destination = None
		if (type == "plugins"):
			destination = os.path.join("Plugins", "server")
		elif (type == "regions"):
			destination = "Regions"
		destination = os.path.join(SC4MP_LAUNCHPATH, destination)
		if (not os.path.exists(destination)):
			os.makedirs(destination)

		# Synchronize or clear custom plugins
		if (type == "plugins"):
			client_plugins_source = sc4mp_config["GENERAL"]["custom_plugins_path"]
			client_plugins_destination = os.path.join(SC4MP_LAUNCHPATH, "Plugins", "client")
			if (self.server.user_plugins_enabled and sc4mp_config["GENERAL"]["custom_plugins"]):
				#try:
				self.report("", "Synchronizing custom plugins...")
				destination_relpaths = get_fullpaths_recursively(client_plugins_destination)
				for relpath in destination_relpaths:
					if (not os.path.exists(os.path.join(client_plugins_source, relpath))):
						filename = os.path.join(client_plugins_destination, relpath)
						print("- removing \"" + filename + "\"")
						os.remove(u"\\\\?\\" + filename)
				source_relpaths = get_relpaths_recursively(client_plugins_source)
				source_size = 1
				for relpath in source_relpaths:
					source_size += os.path.getsize(u"\\\\?\\" + os.path.join(client_plugins_source, relpath))
				destination_size = 1
				for relpath in source_relpaths:
					percent = math.floor(100 * (destination_size / source_size))
					self.report_progress("Synchronizing custom plugins... (" + str(percent) + "%)", percent, 100)
					s = u"\\\\?\\" + os.path.join(client_plugins_source, relpath)
					d = u"\\\\?\\" + os.path.join(client_plugins_destination, relpath)
					destination_size += os.path.getsize(s)
					if (os.path.exists(d)):
						if (md5(s) == md5(d)):
							print("- verified \"" + d + "\"")
							continue
						else:
							print("- removing \"" + d + "\"")
							os.remove(d)
					print("- copying \"" + s + "\"")
					directory = os.path.split(d)[0]
					if (not os.path.exists(directory)):
						os.makedirs(directory)
					shutil.copy(s, d)
				#shutil.copytree(sc4mp_config["GENERAL"]["custom_plugins_path"], client_plugins_destination, dirs_exist_ok=True) #zzz_SC4MP
				#except:
				#	raise CustomException("Unexpected error while loading custom plugins.")
			else:
				try:
					self.report("", "Clearing custom plugins...")
					purge_directory(client_plugins_destination)
				except: #CustomException:
					pass
					#raise CustomException("Simcity 4 is already running!")

		# Purge the destination directory
		self.report("", 'Synchronizing ' + type + "...") #"", "Purging " + type + " directory...")
		try:
			purge_directory(destination)
		except CustomException:
			raise CustomException("Simcity 4 is already running!")

		# Create the socket
		s = self.create_socket() 

		# Request the type of data
		s.send(type.encode())

		# Request header
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
			self.report_progress('Synchronizing ' + type + "... (" + str(percent) + "%)", percent, 100)
			s.send(SC4MP_SEPARATOR)
			size_downloaded += self.receive_or_cached(s, destination)
		self.report_progress('Synchronizing ' + type + "... (100%)", 100, 100)

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
						self.report("[ERROR] ", "Connection failed. Retrying in " + str(count) + "...")					
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					raise CustomException("Maximum connection tries exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

		return s


	def receive_or_cached(self, s, rootpath):
		"""TODO"""

		# Receive hashcode and set cache filename
		hash = s.recv(SC4MP_BUFFER_SIZE).decode()
		target = os.path.join(SC4MP_LAUNCHPATH, "_Cache", hash)

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive relative path and set the destination
		relpath = os.path.normpath(s.recv(SC4MP_BUFFER_SIZE).decode())
		destination = os.path.join(rootpath, relpath)

		# Use the cached file if it exists and has the same size
		if (os.path.exists(target) and os.path.getsize(target) == filesize):
			
			print('- using cached "' + hash + '"')

			# Tell the server that the file is cached
			s.send(b"cached")

			# Create the destination directory if necessary
			destination_directory = os.path.split(destination)[0]
			if (not os.path.exists(destination_directory)):
				os.makedirs(destination_directory)

			# Delete the destination file if it exists
			if (os.path.exists(destination)):
				os.remove(destination)

			# Copy the cached file to the destination
			shutil.copy(target, destination)

		else:

			print('- caching "' + hash + '"...')

			# Tell the server that the file is not cached
			s.send(b"not cached")

			# Create the destination directory if necessary
			destination_directory = os.path.split(destination)[0]
			if (not os.path.exists(destination_directory)):
				os.makedirs(destination_directory)

			# Delete the destination file if it exists
			if (os.path.exists(destination)):
				os.remove(destination)

			# Delete the cache file if it exists
			if (os.path.exists(target)):
				os.remove(target)

			# Delete cache files if cache too large to accomadate the new cache file
			cache_directory = os.path.join(SC4MP_LAUNCHPATH, "_Cache")
			while (len(os.listdir(cache_directory)) > 0 and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize):
				os.remove(os.path.join(cache_directory, random.choice(os.listdir(cache_directory))))

			# Receive the file. Write to both the destination and cache
			filesize_read = 0
			destination_file = open(destination, "wb")
			cache_file = open(target, "wb")
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:    
					break
				for file in [destination_file, cache_file]:
					file.write(bytes_read)
				filesize_read += len(bytes_read)
			
		# Return the file size
		return filesize


	def receive_file(self, s, filename):
		"""TODO"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print("Receiving " + str(filesize) + " bytes...")
		print('writing to "' + filename + '"')

		if (os.path.exists(filename)):
			os.remove(filename)

		filesize_read = 0
		with open(filename, "wb") as f:
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:    
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				self.report_progress('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def prep_regions(self):
		"""TODO"""

		# Declare instance variable to store the names of the server region subdirectories
		self.server.regions = []

		# Path to regions directory
		path = os.path.join(SC4MP_LAUNCHPATH, "Regions")

		# Loop through the server regions, add them to the server regions instance variable and add prefixes to the region names in the region config files
		for directory in os.listdir(path):
			if os.path.isdir(os.path.join(path, directory)):
				self.server.regions.append(directory)
				config_path = os.path.join(path, directory, "region.ini")
				prep_region_config(config_path)

		# Copy the latest failed save push into the region downloads subdirectory
		downloads_path = os.path.join(path, "downloads")
		if (not os.path.exists(downloads_path)):
			os.makedirs(downloads_path)
		try:
			salvage_directory = os.path.join(SC4MP_LAUNCHPATH, "_Salvage", self.server.server_id)
			save_directory = os.path.join(salvage_directory, os.listdir(salvage_directory)[-1])
			region_directory = os.path.join(save_directory, os.listdir(save_directory)[0])
			for filename in os.listdir(region_directory):
				shutil.copy(os.path.join(region_directory, filename), os.path.join(downloads_path, filename))
		except Exception as e:
			pass
			#show_error(e, no_ui=True)

		# Create the refresh auxiliary region
		refresh_path = os.path.join(path, "ZZZRefreshAuxiliary") #TODO possible name conflict!
		os.makedirs(refresh_path)
		shutil.copy(get_sc4mp_path("refresh-config.bmp"), os.path.join(refresh_path, "config.bmp"))
		shutil.copy(get_sc4mp_path("refresh-region.ini"), os.path.join(refresh_path, "region.ini"))


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
						print("Ping: " + str(ping))
						if (self.ui != None):
							self.ui.ping_frame.right['text'] = str(ping) + "ms"
					
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


	def get_cities(self):
		"""TODO"""
		city_paths = []
		city_hashcodes = []
		regions_path = os.path.join(SC4MP_LAUNCHPATH, "Regions")
		for region in self.server.regions:
			region_path = os.path.join(regions_path, region)
			if (not os.path.exists(region_path)):
				os.makedirs(region_path)
			if (os.path.isfile(region_path)):
				continue
			for city in os.listdir(region_path):
				city_path = os.path.join(region_path, city)
				if (os.path.isdir(city_path)):
					continue
				filename, file_extension = os.path.splitext(city_path)
				if (file_extension == ".sc4"):
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

	
	def receive_file(self, s, filename):
		"""TODO"""

		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		print("Receiving " + str(filesize) + " bytes...")
		print('writing to "' + filename + '"')

		if (os.path.exists(filename)):
			os.remove(filename)

		filesize_read = 0
		with open(filename, "wb") as f:
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:    
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				#print('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def push_save(self, save_city_paths):
		"""TODO"""

		# Report progress: backups
		#self.report(self.PREFIX, 'Creating backups...')
		
		# Create backups #TODO salvage
		#for save_city_path in save_city_paths:
		#	self.backup_city(save_city_path)

		# Report progress: save
		self.report(self.PREFIX, 'Saving...') #Pushing save #for "' + new_city_path + '"')

		# Salvage
		salvage_directory = os.path.join(SC4MP_LAUNCHPATH, "_Salvage", self.server.server_id, datetime.now().strftime("%Y%m%d%H%M%S"))
		for path in save_city_paths:
			relpath = os.path.relpath(path, os.path.join(SC4MP_LAUNCHPATH, "Regions"))
			filename = os.path.join(salvage_directory, relpath)
			directory = os.path.split(filename)[0]
			if (not os.path.exists(directory)):
				os.makedirs(directory)
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
			region = os.path.split(os.path.dirname(save_city_path))[1]
			city = os.path.split(save_city_path)[1]
	
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
			self.report(self.PREFIX, "Saved successfully at " + datetime.now().strftime("%H:%M") + ".") #TODO keep track locally of the client's claims
			shutil.rmtree(salvage_directory) #TODO make configurable
		else:
			self.report(self.PREFIX + "[WARNING] ", "Save push failed! " + response)

		# Close socket
		s.close()


	def backup_city(self, filename):
		region = os.path.split(os.path.dirname(filename))[1]
		city = os.path.split(filename)[1]
		backup_directory = os.path.join(SC4MP_LAUNCHPATH, "SC4MPBackups", self.server.server_id, region, city)
		if (not os.path.exists(backup_directory)):
			os.makedirs(backup_directory)
		shutil.copy(filename, os.path.join(backup_directory, datetime.now().strftime("%Y%m%d%H%M%S") + ".sc4"))


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
						self.report("[ERROR] ", "Connection failed. Retrying in " + str(count) + "...")					
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					return None

		return s


	def send_file(self, s, filename):
		"""TODO"""

		self.report_quietly("Saving...")
		print('Sending file "' + filename + '"...')

		filesize = os.path.getsize(filename)

		s.send(str(filesize).encode())
		s.recv(SC4MP_BUFFER_SIZE)

		with open(filename, "rb") as f:
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
			destination = os.path.join(SC4MP_LAUNCHPATH, "Regions")

			# Purge the region directories
			for region in self.server.regions:
				purge_directory(os.path.join(destination, region))

			# Create the socket
			s = self.create_socket() 

			# Request regions
			s.send(b"regions")

			# Request header
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
				self.report_progress('Refreshing regions... ' + "(" + str(percent) + "%)", percent, 100)
				s.send(SC4MP_SEPARATOR)
				size_downloaded += self.receive_or_cached(s, destination)
			self.report_progress('Refreshing regions... ' + "(" + str(100) + "%)", 100, 100)

			# Report
			self.report("", "Refreshing regions...")

			# Prep region configs
			for region in self.server.regions:
				prep_region_config(os.path.join(destination, region, "region.ini"))

			# Report
			self.report("", "Done.")

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
						self.report("[ERROR] ", "Connection failed. Retrying in " + str(count) + "...")					
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					raise CustomException("Maximum connection tries exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

		return s


	def receive_or_cached(self, s, rootpath):
		"""TODO"""

		# Receive hashcode and set cache filename
		hash = s.recv(SC4MP_BUFFER_SIZE).decode()
		target = os.path.join(SC4MP_LAUNCHPATH, "_Cache", hash)

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(SC4MP_BUFFER_SIZE).decode())

		# Separator
		s.send(SC4MP_SEPARATOR)

		# Receive relative path and set the destination
		relpath = os.path.normpath(s.recv(SC4MP_BUFFER_SIZE).decode())
		destination = os.path.join(rootpath, relpath)

		# Use the cached file if it exists and has the same size
		if (os.path.exists(target) and os.path.getsize(target) == filesize):
			
			print('- using cached "' + hash + '"')

			# Tell the server that the file is cached
			s.send(b"cached")

			# Create the destination directory if necessary
			destination_directory = os.path.split(destination)[0]
			if (not os.path.exists(destination_directory)):
				os.makedirs(destination_directory)

			# Delete the destination file if it exists
			if (os.path.exists(destination)):
				os.remove(destination)

			# Copy the cached file to the destination
			shutil.copy(target, destination)

		else:

			print('- caching "' + hash + '"...')

			# Tell the server that the file is not cached
			s.send(b"not cached")

			# Create the destination directory if necessary
			destination_directory = os.path.split(destination)[0]
			if (not os.path.exists(destination_directory)):
				os.makedirs(destination_directory)

			# Delete the destination file if it exists
			if (os.path.exists(destination)):
				os.remove(destination)

			# Delete the cache file if it exists
			if (os.path.exists(target)):
				os.remove(target)

			# Delete cache files if cache too large to accomadate the new cache file
			cache_directory = os.path.join(SC4MP_LAUNCHPATH, "_Cache")
			while (len(os.listdir(cache_directory)) > 0 and directory_size(cache_directory) > (1000000 * int(sc4mp_config["STORAGE"]["cache_size"])) - filesize):
				os.remove(os.path.join(cache_directory, random.choice(os.listdir(cache_directory))))

			# Receive the file. Write to both the destination and cache
			filesize_read = 0
			destination_file = open(destination, "wb")
			cache_file = open(target, "wb")
			while (filesize_read < filesize):
				bytes_read = s.recv(SC4MP_BUFFER_SIZE)
				if not bytes_read:    
					break
				for file in [destination_file, cache_file]:
					file.write(bytes_read)
				filesize_read += len(bytes_read)
			
		# Return the file size
		return filesize


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

		self.wm_iconbitmap(SC4MP_ICON) #TODO looks bad
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
			self.label = tk.Label(self, justify="center", text='To get started, select "Servers" then "Connect..." in the menu bar and enter the IP address and port of the server you wish to connect to.')
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
	#	webbrowser.open_new_tab("https://github.com/keggre/sc4mp-client/releases/")


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
		self.server_list.worker.end = True
		#while (self.server_list.worker.ended == False):
		#	time.sleep(SC4MP_DELAY)
		self.server_list.tree.delete(*self.server_list.tree.get_children())
		self.server_list.worker = ServerList(self.server_list)
		self.server_list.worker.start()


	def about(self):
		"""TODO"""
		AboutUI()


	def readme(self):
		"""TODO"""
		webbrowser.open_new_tab(SC4MP_README_PATH)


class GeneralSettingsUI(tk.Toplevel):


	def __init__(self):
		"""TODO"""

		#print("Initializing...")

		# Init
		super().__init__()

		# Title
		self.title("General settings")

		# Icon
		self.iconbitmap(SC4MP_ICON)

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
		self.iconbitmap(SC4MP_ICON)

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
		purge_directory(os.path.join(SC4MP_LAUNCHPATH, "_Cache"))


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
				if (os.path.exists(os.path.join(data, "Plugins")) or os.path.exists(os.path.join(str(data), "Regions"))):
					if (not messagebox.askokcancel(title=SC4MP_TITLE, message="The directory \"" + data + "\" already contains Simcity 4 plugins and regions. \n\nProceeding will result in the IRREVERSIBLE DELETION of these files! \n\nThis is your final warning, do you wish to proceed?", icon="warning")): #TODO make message box show yes/no and not ok/cancel
						raise CustomException("Operation cancelled by user.")
			update_config_value("STORAGE", key, data)
		create_subdirectories
		

	def ok(self):
		"""TODO"""
		try:
			self.update()
			sc4mp_config.update()
			self.destroy()
		except CustomException:
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
		self.iconbitmap(SC4MP_ICON) #TODO looks bad

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
				purge_directory(os.path.join(SC4MP_LAUNCHPATH, "plugins"))
				purge_directory(os.path.join(SC4MP_LAUNCHPATH, "regions"))
				
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
		path = os.path.join("_Servers", "default")
		if (not os.path.exists(path)):
			os.makedirs(path)
			prep_server(path)

		# Init
		super().__init__()

		# Title
		self.title("Host")

		# Icon
		self.iconbitmap(SC4MP_ICON)

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

		path = os.path.join("_Servers", self.list_box_variable.get()[self.list_box.curselection()[0]])

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
		self.iconbitmap(SC4MP_ICON)

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
				#raise CustomException("Invalid host")
			try:
				port = int(port)
			except:
				port = SC4MP_PORT
				#raise CustomException("Invalid port")
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
		self.iconbitmap(SC4MP_ICON)

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
		self.iconbitmap(SC4MP_ICON)

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
		self.license_label_2.bind("<Button-1>", lambda e:os.startfile("License.txt"))

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


		# Image

		self.canvas = tk.Canvas(self, width=800, height=100)
		self.canvas.image = tk.PhotoImage(file=get_sc4mp_path("banner.png"))
		self.canvas.create_image(400, 50, image=self.canvas.image)    
		self.canvas["borderwidth"] = 0
		self.canvas["highlightthickness"] = 0
		self.canvas.grid(row=0, column=0, rowspan=1, columnspan=2, padx=0, pady=0)


		# Label

		self.label = ttk.Label(self)
		self.label.grid(column=0, row=1, rowspan=1, columnspan=2, padx=10, pady=(15, 10))
		self.label['text'] = 'To get started, select a server below and click "Connect."' #"Loading server list..."


		# Tree

		NORMAL_COLUMN_WIDTH = 93

		COLUMNS = [
			(
				"",
				int(NORMAL_COLUMN_WIDTH / 3),
				"w"
    		),
			(
				"Name",
				3 * NORMAL_COLUMN_WIDTH,
				"w"
    		),
		    (
				"Mayors",
				NORMAL_COLUMN_WIDTH,
				"center"
    		),
			(
				"Claimed",
				NORMAL_COLUMN_WIDTH,
				"center"
    		),
			(
				"Download",
				NORMAL_COLUMN_WIDTH,
				"center"
    		),
			(
				"Ping",
				NORMAL_COLUMN_WIDTH,
				"center"
    		),
			(
				"Rating",
				NORMAL_COLUMN_WIDTH,
				"center"
    		)
		]

		column_names = []
		for column in COLUMNS:
			column_names.append(column[0])
		column_names = tuple(column_names)

		self.tree = ttk.Treeview(self, selectmode="browse", height=12)

		self.tree['columns'] = column_names

		for column in COLUMNS:
			column_name = column[0]
			column_width = column[1]
			column_anchor = column[2]
			self.tree.column(column_name, width=column_width, anchor=column_anchor)
			self.tree.heading(column_name, text=column_name)
		
		self.tree['show'] = 'headings'

		self.tree.focus_set()

		self.tree.bind("<Double-1>", lambda event: self.connect())

		self.tree.grid(column=0, row=2, rowspan=1, columnspan=2, padx=11, pady=10, sticky="n")

		#SERVER = Server(SC4MP_HOST, SC4MP_PORT)
		#SERVER.fetch()
		#self.tree.insert('', 'end', SERVER.server_id, values=self.worker.format_server(SERVER))


		# Description label

		self.description_label = ttk.Label(self)
		self.description_label.grid(column=0, row=5, rowspan=1, columnspan=1, padx=20, pady=10, sticky="nw")
		self.description_label['text'] = ""


		# Address label

		self.address_label = ttk.Label(self)
		self.address_label.grid(row=5, column=1, columnspan=1, padx=15, pady=(10, 90), sticky="ne")
		self.address_label['text'] = ""


		# URL label

		self.url_label = tk.Label(self, fg="blue", cursor="hand2")
		self.url_label.grid(row=6, column=0, columnspan=1, padx=15, pady=(10, 10), sticky="sw")
		self.url_label['text'] = ""
		self.url_label.bind("<Button-1>", lambda e:webbrowser.open_new_tab(self.url_label["text"]))


		# Connect button

		self.connect_button = ttk.Button(self, text="Connect", command=self.connect, default="active")
		self.connect_button['state'] = tk.DISABLED
		self.connect_button.grid(row=6, column=1, columnspan=1, padx=15, pady=10, sticky="se")


		# Worker
		self.worker = ServerList(self)
		self.worker.start()


	def focus_tree(self):
		"""TODO"""
		self.tree.focus_set()
		if (self.tree.focus() == ""):
			children = self.tree.get_children()
			self.tree.focus(children[0])


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
		self.iconbitmap(SC4MP_ICON)

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
		self.iconbitmap(SC4MP_ICON)

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
		self.iconbitmap(SC4MP_ICON)

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

class CustomException(Exception):
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
		self.log = SC4MP_LOG_PATH
		if (os.path.exists(self.log)):
			os.remove(self.log)
   

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


# Main Method

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
				raise CustomException("Invalid arguments.")

		# "--port" argument
		global sc4mp_port
		sc4mp_port = None
		if ("--port" in sc4mp_args):
			try:
				sc4mp_port = int(get_arg_value("--port", sc4mp_args))
			except:
				raise CustomException("Invalid arguments.")
			
		# "--password" argument
		global sc4mp_password
		sc4mp_password = None
		if ("--password" in sc4mp_args):
			try:
				sc4mp_password = int(get_arg_value("--password", sc4mp_args))
			except:
				raise CustomException("Invalid arguments.")

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

	except Exception as e:

		# Error 
		fatal_error()
		#show_error("A fatal error occurred.\n\n" + str(e)) #traceback.format_exc() #Please send the following information to the developers of the " + SC4MP_TITLE + " so this can be resolved:

if __name__ == '__main__':
	main()
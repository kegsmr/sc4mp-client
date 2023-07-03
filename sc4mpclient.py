import configparser
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import threading as th
import time
import tkinter as tk
from datetime import datetime
from tkinter import Menu, messagebox, ttk, filedialog
import json
import random
import string
import math
import inspect
import traceback
import webbrowser

SC4MP_VERSION = (0,1,0)

SC4MP_OFFICIAL_SERVERS = [("servers.sc4mp.org", 7240)]

SC4MP_CONFIG_PATH = "config.ini"
SC4MP_LOG_PATH = "sc4mpclient.log"
SC4MP_RESOURCES_PATH = "resources"

SC4MP_TITLE = "SC4MP Launcher v" + str(SC4MP_VERSION[0]) + "." + str(SC4MP_VERSION[1]) + "." + str(SC4MP_VERSION[2])
SC4MP_ICON = os.path.join(SC4MP_RESOURCES_PATH, "icon.ico")

SC4MP_HOST = SC4MP_OFFICIAL_SERVERS[0][0] #socket.gethostname()
SC4MP_PORT = SC4MP_OFFICIAL_SERVERS[0][1] #7240

SC4MP_SEPARATOR = b"<SEPARATOR>"
SC4MP_BUFFER_SIZE = 4096

SC4MP_DELAY = .1

SC4MP_CONFIG_DEFAULTS = [
	("GENERAL", [
		("nickname", os.getlogin()),
		#("use_custom_user_id", False), #TODO
		#("custom_user_id", ""), #TODO
		("default_host", SC4MP_HOST),
		("default_port", SC4MP_PORT),
		#("use_overlay", 1), #TODO
		("custom_plugins", False),
		("custom_plugins_path", os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","Plugins"))
	]),
	("STORAGE", [
		("storage_path", os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","_SC4MP") + "\\"),
		("cache_size", 4000)
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
	"""TODO"""
	load_config()
	create_subdirectories()


def load_config():
	"""TODO"""	

	global sc4mp_config

	print("Loading config...")

	sc4mp_config = Config(SC4MP_CONFIG_PATH, SC4MP_CONFIG_DEFAULTS)

	
def update_config_constants(config):
	"""TODO"""

	global SC4MP_LAUNCHPATH
	global SC4MP_LAUNCHRESW
	global SC4MP_LAUNCHRESH
	global SC4MP_CUSTOMPATH

	SC4MP_LAUNCHPATH = config['STORAGE']['storage_path']
	SC4MP_LAUNCHRESW = config['SC4']['resw']
	SC4MP_LAUNCHRESH = config['SC4']['resh']
	SC4MP_CUSTOMPATH = config['SC4']['game_path']


def create_subdirectories():
	"""Creates the required subdirectories in the launch directory if they do not yet exist.

	Arguments:
		None

	Returns:
		TODO
	"""

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
	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	
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
	"""Attempts to find the install path of Simcity 4 and launches the game with custom launch parameters if found.

	Arguments:
		TODO

	Returns:
		TODO
	"""

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

	print("Simcity 4 closed.")


def get_sc4mp_path(filename):
	"""Gives the path of a given file in the SC4MP "resources" subdirectory

	Arguments:
		filename (str)

	Returns:
		TODO type: the path to the given file
	"""
	return os.path.join(SC4MP_RESOURCES_PATH, filename)


def md5(filename):
	"""Creates the hashcode for a given file.

	Arguments:
		filename (str)

	Returns:
		TODO type: hashcode
	"""
	hash_md5 = hashlib.md5()
	with open(filename, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def random_string(length):
	"""TODO"""
	return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(length))


def purge_directory(directory):
	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
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
	"""TODO"""

	size = 0

	with os.scandir(directory) as items:
		for item in items:
			if item.is_file():
				size += item.stat().st_size
			elif item.is_dir():
				size += directory_size(item.path)

	return size


def event_generate(ui, event, when):
	"""Not used."""
	if (ui != None):
		ui.event_generate(event, when=when)


'''def create_empty_json(filename):
	"""TODO"""
	with open(filename, 'w') as file:
		data = dict()
		file.seek(0)
		json.dump(data, file, indent=4)
		file.truncate()'''


def load_json(filename):
	"""TODO"""
	with open(filename, 'r') as file:
		return json.load(file)


def update_json(filename, data):
	"""TODO"""
	with open(filename, 'w') as file:
		file.seek(0)
		json.dump(data, file, indent=4)
		file.truncate()


def show_error(e, no_ui=False):
	"""TODO"""
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
	"""TODO"""

	message = "A fatal error occurred.\n\n" + traceback.format_exc()

	print("[FATAL] " + message)

	if (sc4mp_ui != None):
		if (sc4mp_ui == True):
			tk.Tk().withdraw()
		messagebox.showerror(SC4MP_TITLE, message)

	sys.exit()


def show_warning(e):
	"""TODO"""
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
	"""
	TODO
	centers a tkinter window
	:param win: the main window or Toplevel window to center
	"""
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
	"""TODO"""
	subprocess.Popen("sc4mpserver.exe -prep --server-path " + str(path))


def start_server(path):
	"""TODO"""
	subprocess.Popen("sc4mpserver.exe --server-path " + str(path), creationflags=subprocess.CREATE_NEW_CONSOLE)

	#th.Thread(target=lambda: subprocess.Popen("sc4mpserver.exe --server-path " + str(path))).start()


def update_config_value(section, item, value):
	"""TODO"""
	try:
		t = type(sc4mp_config[section][item])
		sc4mp_config[section][item] = t(value)
	except:
		show_error("Invalid config value for \"" + item + "\" in section \"" + section + "\"", no_ui=True)


def get_fullpaths_recursively(path):
	"""TODO"""
	fullpaths = []
	for path, directories, files in os.walk(path):
		for file in files:
			fullpaths.append(os.path.join(path, file))
	return fullpaths


def get_relpaths_recursively(path):
	"""TODO"""
	fullpaths = get_fullpaths_recursively(path)
	relpaths = []
	for fullpath in fullpaths:
		relpaths.append(os.path.relpath(fullpath, path))
	return relpaths


# Objects

class Config:
	"""TODO"""


	def __init__(self, path, defaults):
		"""TODO"""

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
		"""TODO"""
		return self.data.__getitem__(key)


	def __setitem__(self, key, value):
		"""TODO"""
		return self.data.__setitem__(key, value)


	def update(self):
		"""TODO"""
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
	"""TODO"""


	def __init__(self, host, port):
		"""TODO"""

		self.host = host
		self.port = port

		self.fetched = False
		self.password = None
		self.user_id = None


	def fetch(self):
		"""TODO"""

		# Mark server as fetched
		self.fetched = True

		# Request server info
		self.server_id = self.request("server_id")
		self.server_name = self.request("server_name")
		self.server_description = self.request("server_description")
		self.password_enabled = self.request("password_enabled") == "yes"
		self.user_plugins_enabled = self.request("user_plugins_enabled") == "yes"

		#TODO add server host and port to serverlist?

			
	def request(self, request):
		"""TODO"""

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
			show_error('Error fetching "' + request + '" from ' + host + ":" + str(port) + '', no_ui=True)
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

		# Set values in database entry
		entry["server_name"] = self.server_name
		entry["server_description"] = self.server_description
		entry["host"] = self.host
		entry["port"] = self.port	

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
		s.recv(SC4MP_BUFFER_SIZE)
		s.send(user_id.encode())
		token = s.recv(SC4MP_BUFFER_SIZE).decode()

		# Raise exception if no token is received
		if (len(token) < 1):
			raise CustomException("You are banned from this server.")

		# Set user_id and token in the database entry
		entry["user_id"] = user_id
		entry["token"] = token

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


# Workers

class ServerList(th.Thread):
	"""TODO"""


	def __init__(self):
		"""TODO"""

		self.setDaemon(True)

		print("(to implement)") #TODO


	def run(self):
		"""TODO"""

		try:

			print("TO IMPLEMENT") #TODO

		except Exception as e:

			show_error(e)


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
				if (self.ui != None):
					self.ui.title(self.server.server_name)

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
		

	def authenticate(self):
		"""TODO"""
		tries = 0
		while (not self.check_password()):
			if (sc4mp_ui):
				if (tries >= 5):
					raise CustomException("Too many password attempts.")
				if (tries > 0):
					print("[WARNING] Incorrect password.")
					time.sleep(3)
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
				except CustomException:
					raise CustomException("Simcity 4 is already running!")

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

		self.server.regions = []

		path = os.path.join(SC4MP_LAUNCHPATH, "Regions")

		for directory in os.listdir(path):
			
			# Backup directory
			#backup_directory = os.path.join(SC4MP_LAUNCHPATH, os.path.join("SC4MPBackups", os.path.join(self.server.server_id, directory)))
			#if (not os.path.exists(backup_directory)):
			#	os.makedirs(backup_directory)

			self.server.regions.append(directory)

			config_path = os.path.join(path, directory, "region.ini")
			
			try:
				config = configparser.RawConfigParser()
				config.read(config_path)
				config.set("Regional Settings", "Name", "[SC4MP] " + config.get("Regional Settings", "Name")) # can't choose between "[SC4MP]"", "[MP]", "[SC4MP]"
				with open(config_path, 'wt') as config_file:
					config.write(config_file)
			except:
				show_error("Failed to prep region config for " + directory + ".")

		#shutil.unpack_archive(get_sc4mp_path("Regions.zip"), path) #TODO maybe re-enable this at some point?


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

						# Report waiting to sync if new/modified savegames found
						if (len(save_city_paths) > 0):
							self.report("", "Saving...") #Scanning #Waiting to sync

						# Wait
						time.sleep(6) #10 #3 #TODO make configurable?
					
					# If there are any new/modified savegame files, push them to the server. If errors occur, log them in the console and display a warning
					if (len(save_city_paths) > 0):
						try:
							self.push_save(save_city_paths)
						except Exception as e:
							show_error(e, no_ui=True)
							self.report("[WARNING] ", "Save push failed! Unexpected client-side error.")

					# Break the loop when signaled
					if (end == True):
						break

					# Signal to break the loop when the game is no longer running
					if (not self.game_launcher.game_running):
						end = True

					# Wait
					time.sleep(3)

					#TODO fix refresh
					# Refresh by asking the server for the hashcodes of all its savegames (excluding ones already claimed by the user) and downloading the savegames missing locally, tossing them directly into the respective region (was supposed to work but Simcity 4 actually tries to keep files of the same checksum)
					'''if (ping != None): #TODO add configurable refresh interval
						old_text = self.ui.label["text"]
						self.report("", "Refreshing...")
						with self.create_socket() as s:
							self.report("", "Refreshing...")
							s.send(b'refresh')
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
					time.sleep(3)
			
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

		# Create socket
		s = self.create_socket()
		if (s == None):
			self.report(self.PREFIX, 'Save push failed! Server unreachable.') #'Unable to save the city "' + new_city + '" because the server is unreachable.'
			return

		# Send save request
		s.send(b"push_save")
		s.recv(SC4MP_BUFFER_SIZE)

		# Send password if required #TODO
		#if (self.server.password_enabled):
		#	s.send(self.server.password.encode())
		#	s.recv(SC4MP_BUFFER_SIZE)

		# Send user id
		s.send(self.server.user_id.encode())
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
		
		settings = Menu(menu, tearoff=0)  
		settings.add_command(label="General...", command=self.general_settings)     
		settings.add_command(label="Storage...", command=self.storage_settings)    
		settings.add_command(label="SC4...", command=self.SC4_settings)  
		settings.add_separator()
		settings.add_command(label="Updates...", command=self.update) 
		settings.add_separator()
		settings.add_command(label="Exit", command=self.quit)  
		menu.add_cascade(label="Settings", menu=settings)  #TODO rename to "Launcher" and put settings in cascade?

		servers = Menu(menu, tearoff=0)  
		
		#servers.add_command(label="Host...", command=self.host) #TODO
		#servers.add_separator() #TODO
		servers.add_command(label="Connect...", command=self.direct_connect)  #"Direct connect..."
		#servers.add_command(label="Refresh", command=self.refresh) #TODO
		menu.add_cascade(label="Servers", menu=servers)  

		help = Menu(menu, tearoff=0)  	
		help.add_command(label="Readme...", command=self.readme) 
		feedback_submenu = Menu(help, tearoff=0)
		feedback_submenu.add_command(label="Github...", command=self.github)
		feedback_submenu.add_command(label="Discord...", command=self.discord)
		#feedback_submenu.add_command(label="Simtropolis", command=self.simtropolis)
		help.add_cascade(label="Feedback", menu=feedback_submenu)  
		menu.add_cascade(label="Help", menu=help)  
		
		self.config(menu=menu)  


		# Server List

		if (False): #TODO re-enable server list
			self.server_list = ServerListUI(self)
			self.server_list.grid(row = 0, column = 0)
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


	def update(self):
		webbrowser.open_new_tab("https://github.com/keggre/sc4mp-client/releases/")


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
		self.to_implement() #TODO


	def readme(self):
		"""TODO"""
		webbrowser.open_new_tab("Readme.html")


	def github(self):
		"""TODO"""
		webbrowser.open_new_tab("https://github.com/keggre/sc4mp-client/issues")


	def discord(self):
		"""TODO"""
		webbrowser.open_new_tab("https://discord.gg/zb8gW2aARY")


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
		self.maxsize(290, 130)
		self.minsize(290, 130)
		self.grid()
		center_window(self)
		
		# Priority
		self.grab_set()

		# Key bindings
		self.bind("<Return>", lambda event:self.ok())
		self.bind("<Escape>", lambda event:self.destroy())

		# Config update
		self.config_update = []

		# Nickname frame
		self.nickname_frame = ttk.LabelFrame(self, text="Nickname")
		self.nickname_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

		# Nickname entry
		self.nickname_frame.entry = ttk.Entry(self.nickname_frame, width = 40)
		self.nickname_frame.entry.grid(row=0, column=0, columnspan=1, padx=10, pady=10)
		self.nickname_frame.entry.insert(0, sc4mp_config["GENERAL"]["nickname"])
		self.config_update.append((self.nickname_frame.entry, "nickname"))

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
		self.path_frame.label = ttk.Label(self.path_frame, text='Do NOT change this to your normal launch directory, or else your plugins\n and regions will be deleted!')
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


		# Label

		self.label = ttk.Label(self)
		self.label.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10)
		self.label['text'] = 'To get started, select a server below and click "Connect."' #"Loading server list..."


		# Tree

		NORMAL_COLUMN_WIDTH = 97

		COLUMNS = [
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
				"Rank",
				NORMAL_COLUMN_WIDTH,
				"center"
    		)
		]

		column_names = []
		for column in COLUMNS:
			column_names.append(column[0])
		column_names = tuple(column_names)

		self.tree = ttk.Treeview(self, selectmode="browse")

		self.tree['columns'] = column_names

		for column in COLUMNS:
			column_name = column[0]
			column_width = column[1]
			column_anchor = column[2]
			self.tree.column(column_name, width=column_width, anchor=column_anchor)
			self.tree.heading(column_name, text=column_name)
		
		self.tree['show'] = 'headings'

		self.tree.grid(column=0, row=5, rowspan=1, columnspan=1, padx=10, pady=10, sticky="we")

		self.tree.insert('', 'end', 'item1', values=("[SC4MP] Vanilla", "23 (2)", "36%", "542MB", "43ms", "5/5"))
		self.tree.insert('', 'end', 'item2')
		self.tree.insert('', 'end', 'item3')


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

'''def cmd(): #TODO incorporate this into the main method but enable this functionality using commandline arguments
	"""This method is meant to be run in a terminal instead of the main method for testing purposes.

	Arguments:
		None

	Returns:
		None
	"""

	sys.stdout = Logger()

	print(SC4MP_TITLE)

	prep()

	print("[PROMPT] Connect to server:")

	host = input("[PROMPT] - Enter server IP... ")
	port = input("[PROMPT] - Enter server port... ")

	if (len(host) < 1):
		host = socket.gethostname()

	if (len(port) < 1):
		port = 7246
	else:
		port = int(port)

	#global sc4mp_ui, sc4mp_ui_root
	#sc4mp_ui = True
	#sc4mp_ui_root = UI()
	#sc4mp_ui_root.withdraw()

	connect(Server(host, port))

	#sc4mp_ui.destroy()'''


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

		# Version
		print(SC4MP_TITLE)

		# Enable UI
		global sc4mp_ui
		sc4mp_ui = True

		# Prep
		prep()

		# UI
		sc4mp_ui = UI()
		sc4mp_ui.mainloop()

	except Exception as e:

		# Error 
		fatal_error()
		#show_error("A fatal error occurred.\n\n" + str(e)) #traceback.format_exc() #Please send the following information to the developers of the " + SC4MP_TITLE + " so this can be resolved:

if __name__ == '__main__':
	main()
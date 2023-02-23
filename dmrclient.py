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
from tkinter import Menu, messagebox, ttk
import json
import random
import string
import math
import inspect
import traceback
#import py2exe

# Version
DMR_VERSION = "v1.0.0 Alpha"

# Path to the resources subdirectory
DMR_RESOURCES_PATH = "resources"

# Global variables
dmr_ui = None
dmr_current_server = None

# Default config values
default_dmrpath = os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","_DMR") + "\\"
default_resw = 1280
default_resh = 800
default_sc4path = ""

# Config constants
DMR_LAUNCHPATH = None
DMR_LAUNCHRESW = None
DMR_LAUNCHRESH = None
#DMR_SERVERPATH = "http://api.getpmr.com/" #TODO: will probably replace with a website hosting a server list
DMR_CUSTOMPATH = None

# Hard-coded constants
DMR_TITLE = "DMR Client " + DMR_VERSION
DMR_ICON = os.path.join(DMR_RESOURCES_PATH, "icon.ico")
DMR_HOST = socket.gethostname() #"127.0.0.1"
DMR_PORT = 7246
DMR_SEPARATOR = b"<SEPARATOR>"
DMR_BUFFER_SIZE = 4096


# Methods

def prep():
	"""TODO"""
	load_config()
	create_subdirectories()


def load_config():
	"""Loads the config file from the resources subdirectory or creates it if it does not yet exist.

	Arguments:
		None

	Returns:
		None
	"""

	global DMR_LAUNCHPATH
	global DMR_LAUNCHRESW
	global DMR_LAUNCHRESH
	global DMR_CUSTOMPATH

	print("Loading config...")

	#TODO add cpu options for start parameters
	configpath = "config.ini"
	try:
		config = configparser.RawConfigParser()
		config.read(configpath)

		DMR_LAUNCHPATH = config.get('launcher', 'path')
		DMR_LAUNCHRESW = config.get('launcher', 'resw')
		DMR_LAUNCHRESH = config.get('launcher', 'resh')
		DMR_CUSTOMPATH = config.get('launcher', 'sc4path')
	except:
		config.remove_section('launcher')
		config.add_section('launcher')
		config.set('launcher', 'path', default_dmrpath)
		config.set('launcher', 'resw', default_resw)
		config.set('launcher', 'resh', default_resh)
		config.set('launcher', 'sc4path', default_sc4path)
		
		with open(configpath, 'wt') as configfile: #apparently you have to use 'wt' for this now instead of 'wb'
			config.write(configfile)

		DMR_LAUNCHPATH = default_dmrpath
		DMR_LAUNCHRESW = default_resw
		DMR_LAUNCHRESH = default_resh
		DMR_CUSTOMPATH = default_sc4path


def create_subdirectories():
	"""Creates the required subdirectories in the launch directory if they do not yet exist.

	Arguments:
		None

	Returns:
		TODO
	"""

	print("Creating subdirectories...")

	directories = ["DMRCache", "DMRProfiles", "DMRSalvage", "Plugins", "Regions"] #"DMRBackups", os.path.join("DMRCache","Plugins"), os.path.join("DMRCache","Regions")]

	for directory in directories:
		new_directory = os.path.join(DMR_LAUNCHPATH, directory)
		if not os.path.exists(new_directory):
			try:
				os.makedirs(new_directory)
			except Exception as e:
				raise CustomException("Failed to create DMR subdirectories.\n\n" + str(e))
		"""if directory == "Plugins":
			noticepath = os.path.join(DMR_LAUNCHPATH, directory, "__PUT YOUR PLUGINS IN THIS FOLDER__.txt")
			open(noticepath, 'a').close()"""


def connect(server):
	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	
	if (dmr_ui != None):

		# Hide main window
		dmr_ui.withdraw()

		# Create the server loader ui
		server_loader_ui = ServerLoaderUI(dmr_ui, server)

		# Create and start the server loader
		server_loader = ServerLoader(server_loader_ui, server)
		server_loader.run()

		# If the server loads correctly
		if (dmr_current_server != None):

			# Start the TODO
			game_monitor_ui_thread = GameMonitorUIThread(dmr_ui, server)
			game_monitor_ui_thread.start()
			start_sc4()
			game_monitor_ui_thread.ui.worker.game_running = False
		dmr_ui.deiconify()
	else:
		server_loader = ServerLoader(None, server)
		server_loader.run()
		if (dmr_current_server != None):
			game_monitor = GameMonitor(None, server)
			game_monitor.start()
			start_sc4()
			game_monitor.game_running = False


def start_sc4():
	"""Attempts to find the install path of Simcity 4 and launches the game with custom launch parameters if found.

	Arguments:
		TODO

	Returns:
		TODO
	"""

	print("Starting Simcity 4...")

	possiblePaths = [
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		DMR_CUSTOMPATH,
		os.path.join(DMR_CUSTOMPATH, "SimCity 4.exe"),
		os.path.join(DMR_CUSTOMPATH, "Apps", "SimCity 4.exe")
	]

	path = None

	for possiblePath in possiblePaths:
		if possiblePath:
			if os.path.isfile(possiblePath):
				path = '"' + possiblePath + '"'
				break

	if not path:
		show_error("Path to Simcity 4 not found. Specify the correct path in settings.")
		return

	arguments = [path, ' -UserDir:"' + DMR_LAUNCHPATH + '"', ' -intro:off', ' -w', ' -CustomResolution:enabled', ' -r' + str(DMR_LAUNCHRESW) + 'x' + str(DMR_LAUNCHRESH) + 'x32']

	try:
		subprocess.run(' '.join(arguments))
	except PermissionError as e:
		show_error("Permission denied. Run the program as administrator.\n\n" + str(e))

	print("Simcity 4 closed.")


def get_dmr_path(filename):
	"""Gives the path of a given file in the DMR "resources" subdirectory

	Arguments:
		filename (str)

	Returns:
		TODO type: the path to the given file
	"""
	return os.path.join(DMR_RESOURCES_PATH, filename)


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


def create_empty_json(filename):
	"""TODO"""
	with open(filename, 'w') as file:
		data = dict()
		file.seek(0)
		json.dump(data, file, indent=4)
		file.truncate()


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


def show_error(e):
	"""TODO"""
	message = None
	if (isinstance(e, str)):
		message = e
	else: 
		message = str(e)

	print("[ERROR] " + message)

	if (dmr_ui):
		messagebox.showerror(DMR_TITLE, message)


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


# Objects

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

		#TODO add server host and port to serverlist?

			
	def request(self, request):
		"""TODO"""

		if (self.fetched == False):
			return

		host = self.host
		port = self.port

		try:
			s = socket.socket()
			s.connect((host, port))
			s.send(request.encode())
			return s.recv(DMR_BUFFER_SIZE).decode()
		except:
			self.fetched = False
			print('[ERROR] Error fetching "' + request + '" from ' + host + ":" + str(port) + '')
			return None


	def authenticate(self):
		"""TODO"""

		# Get database
		filename = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRProfiles", "servers.json"))
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

		# Get user_id and salt
		user_id = None
		salt = None
		try:
			user_id = entry["user_id"]
			salt = entry["salt"]
		except:
			user_id = random_string(16)

		# Verify server can produce the user_id from the hash of the user_id and salt combined
		if (salt != None):
			hash = hashlib.md5((user_id + salt).encode()).hexdigest()
			s = socket.socket()
			s.connect((self.host, self.port))
			s.send(b"user_id")
			s.recv(DMR_BUFFER_SIZE)
			s.send(hash.encode())
			if (s.recv(DMR_BUFFER_SIZE).decode() == user_id):
				self.user_id = user_id
			else:
				raise CustomException("Authentication error.") #TODO needs a more helpful message
			s.close()

		# Get the new salt
		s = socket.socket()
		s.connect((self.host, self.port))
		s.send(b"salt")
		s.recv(DMR_BUFFER_SIZE)
		s.send(user_id.encode())
		salt = s.recv(DMR_BUFFER_SIZE).decode()

		# Set user_id and salt in the database entry
		entry["user_id"] = user_id
		entry["salt"] = salt

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
			s.recv(DMR_BUFFER_SIZE)
			end = time.time()
			s.close()
			return round(1000 * (end - start))
		except socket.error as e:
			return None
	

# Workers

class ServerList(th.Thread):
	"""TODO"""


	def __init__(self):
		"""TODO"""

		self.setDaemon(True)

		print("(to implement)") #TODO


class ServerLoader(th.Thread):
	"""TODO"""

	
	def __init__(self, ui, server):
		"""TODO"""

		th.Thread.__init__(self)

		self.ui = ui
		self.server = server

		self.setDaemon(True)

		if (dmr_ui != None):
			dmr_ui.withdraw()

	
	def run(self):
		"""TODO"""
	
		host = self.server.host
		port = self.server.port

		try:

			self.report("", 'Connecting to server at ' + str(host) + ":" + str(port) + '...')
			self.fetch_server()

			self.report("", 'Authenticating server...')
			self.authenticate()

			self.report("", "Loading plugins...")
			self.load("plugins")

			self.report("", "Loading regions...")
			self.load("regions")

			self.report("", "Prepping regions...")
			self.prep_regions()

			self.report("", "Done.")

			global dmr_current_server
			dmr_current_server = self.server

		except Exception as e:

			if (self.ui != None and self.ui.winfo_exists() == 1):
				show_error("An error occurred while connecting to the server.\n\n" + str(e))
			else:
				print("[ERROR] " + str(e))

		#time.sleep(1)

		if (self.ui != None):
			self.ui.destroy()
		
		if (dmr_current_server != None):
			#TODO set the host and port as the new default direct connect
			game_monitor = GameMonitor(self.server)
			game_monitor.start()
		else:
			if (dmr_ui != None):
				dmr_ui.deiconify()

		
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
		self.server.authenticate()
		

	def load(self, type):
		"""TODO"""

		# Select the destination directory according to the parameter
		destination = None
		if (type == "plugins"):
			destination = "Plugins"
		elif (type == "regions"):
			destination = "Regions"
		destination = os.path.join(DMR_LAUNCHPATH, destination)

		# Purge the destination directory
		self.report("", "Purging " + type + " directory...")
		purge_directory(destination)

		# Create the socket
		s = self.create_socket() 

		# Request the type of data
		s.send(type.encode())

		# Receive file count
		file_count = int(s.recv(DMR_BUFFER_SIZE).decode())

		# Separator
		s.send(DMR_SEPARATOR)

		# Receive file size
		size = int(s.recv(DMR_BUFFER_SIZE).decode())

		# Receive files
		size_downloaded = 0
		for files_received in range(file_count):
			percent = math.floor(100 * (size_downloaded / size))
			self.report_progress('Downloading ' + type + "... (" + str(percent) + "%)", percent, 100)
			s.send(DMR_SEPARATOR)
			size_downloaded += self.receive_or_cached(s, destination)
		self.report_progress('Downloading ' + type + "... (100%)", 100, 100)

		#print("done.")

		
	def old_load(self, type):
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
		purge_directory(os.path.join(DMR_LAUNCHPATH, directory))

		s = self.create_socket() 

		s.send(type.encode())

		filename = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRCache", os.path.join(directory, server_id + ".zip")))

		client_hashcode = None
		if (os.path.exists(filename)):
			client_hashcode = md5(filename)

		server_hashcode = ""
		try:
			server_hashcode = s.recv(DMR_BUFFER_SIZE).decode()
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
		shutil.unpack_archive(filename, os.path.join(DMR_LAUNCHPATH, directory))

		print("done.")


	def create_socket(self):
		"""TODO"""

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		tries_left = 6

		while(True):

			try:

				self.report("", "Connecting...")
				s.connect((host, port))

				self.report("", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					print("[ERROR] " + str(e))

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
		hash = s.recv(DMR_BUFFER_SIZE).decode()
		target = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRCache", hash))

		# Separator
		s.send(DMR_SEPARATOR)

		# Receive filesize
		filesize = int(s.recv(DMR_BUFFER_SIZE).decode())

		# Separator
		s.send(DMR_SEPARATOR)

		# Receive relative path and set the destination
		relpath = os.path.normpath(s.recv(DMR_BUFFER_SIZE).decode())
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
			cache_directory = os.path.join(DMR_LAUNCHPATH, "DMRCache")
			while (len(os.listdir(cache_directory)) > 0 and directory_size(cache_directory) > 4000000000 - filesize): #TODO: make cache size configurable
				os.remove(os.path.join(cache_directory, random.choice(os.listdir(cache_directory))))

			# Receive the file. Write to both the destination and cache
			filesize_read = 0
			destination_file = open(destination, "wb")
			cache_file = open(target, "wb")
			while (filesize_read < filesize):
				bytes_read = s.recv(DMR_BUFFER_SIZE)
				if not bytes_read:    
					break
				for file in [destination_file, cache_file]:
					file.write(bytes_read)
				filesize_read += len(bytes_read)
			
		# Return the file size
		return filesize


	def receive_file(self, s, filename):
		"""TODO"""

		filesize = int(s.recv(DMR_BUFFER_SIZE).decode())

		print("Receiving " + str(filesize) + " bytes...")
		print('writing to "' + filename + '"')

		if (os.path.exists(filename)):
			os.remove(filename)

		filesize_read = 0
		with open(filename, "wb") as f:
			while (filesize_read < filesize):
				bytes_read = s.recv(DMR_BUFFER_SIZE)
				if not bytes_read:    
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				self.report_progress('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))


	def prep_regions(self):
		"""TODO"""

		self.server.regions = []

		path = os.path.join(DMR_LAUNCHPATH, "Regions")

		for directory in os.listdir(path):
			
			# Backup directory
			#backup_directory = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRBackups", os.path.join(self.server.server_id, directory)))
			#if (not os.path.exists(backup_directory)):
			#	os.makedirs(backup_directory)

			self.server.regions.append(directory)

			config_path = os.path.join(path, os.path.join(directory, "region.ini"))
			
			try:
				config = configparser.RawConfigParser()
				config.read(config_path)
				config.set("Regional Settings", "Name", "[MP] " + config.get("Regional Settings", "Name")) #"[MP]" was "[DMR]"
				with open(config_path, 'wt') as config_file:
					config.write(config_file)
			except:
				show_error("Failed to prep region config for " + directory + ".")

		shutil.unpack_archive(get_dmr_path("Regions.zip"), path)


class GameMonitor(th.Thread):
	"""TODO"""


	def __init__(self, server):
		"""TODO"""

		th.Thread.__init__(self)

		self.server = server
		self.city_paths, self.city_hashcodes = self.get_cities()

		self.PREFIX = ""

		self.ui = None
		if (dmr_ui != None):
			self.ui = GameMonitorUI()

		self.game_launcher = GameLauncher()
		self.game_launcher.start()


	def run(self):
		"""TODO"""
		end = False
		while (True):
			ping = self.ping()
			#print("Ping: " + str(ping))
			if (ping != None):
				self.report_quietly("Connected to server. Monitoring for changes...")
			else:
				self.report(self.PREFIX, "Server unreachable.")
			new_city_paths, new_city_hashcodes = self.get_cities()
			save_city_paths = []
			#print("Old cities: " + str(self.city_paths))
			#print("New cities: " + str(new_city_paths))
			#for city_path in self.city_paths: #TODO
			#	if (not city_path in new_city_paths): #TODO
			#		self.push_delete(city_path) #TODO
			save_city_paths_length = -1
			while (len(save_city_paths) != save_city_paths_length):
				save_city_paths_length = len(save_city_paths)
				for new_city_path in new_city_paths:
					if (not new_city_path in self.city_paths):
						save_city_paths.append(new_city_path)
					else:
						city_hashcode = self.city_hashcodes[self.city_paths.index(new_city_path)]
						new_city_hashcode = new_city_hashcodes[new_city_paths.index(new_city_path)]
						if (city_hashcode != new_city_hashcode):
							#print(city_hashcode + " != " + new_city_hashcode)
							save_city_paths.append(new_city_path)
				self.city_paths = new_city_paths
				self.city_hashcodes = new_city_hashcodes
				time.sleep(3)
			if (len(save_city_paths) > 0):
				self.push_save(save_city_paths)
			if (end == True):
				break
			if (not self.game_launcher.game_running):
				end = True
			time.sleep(3)
		if (self.ui != None):
			self.ui.destroy()
		if (dmr_ui != None):
			dmr_ui.deiconify()
			dmr_ui.lift()


	def get_cities(self):
		"""TODO"""
		city_paths = []
		city_hashcodes = []
		regions_path = os.path.join(DMR_LAUNCHPATH, "Regions")
		for region in self.server.regions:
			region_path = os.path.join(regions_path, region)
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


	def push_delete(self, city_path):
		"""TODO"""

		self.report(self.PREFIX, 'Pushing deletion of "' + city_path + '"')

		city = os.path.split(city_path)[1]
		region = os.path.split(os.path.dirname(city_path))[1]

		s = self.create_socket()

		if (s == None):
			self.report(self.PREFIX, 'Unable to delete the city "' + city + '" because the server is unreachable.')
			return

		s.send(b"push_delete")

		s.recv(DMR_BUFFER_SIZE)
		s.send(self.server.user_id.encode())
		s.recv(DMR_BUFFER_SIZE)
		s.send(region.encode())
		s.recv(DMR_BUFFER_SIZE)
		s.send(city.encode())

		if (s.recv(DMR_BUFFER_SIZE).decode() == "ok"):
			self.report(self.PREFIX, "Delete push authorized") #TODO placeholder
		else:
			self.report(self.PREFIX, "Delete push not authorized") #TODO placeholder

		
	def push_save(self, save_city_paths):
		"""TODO"""

		# Report progress: backups
		#self.report(self.PREFIX, 'Creating backups...')
		
		# Create backups #TODO salvage
		#for save_city_path in save_city_paths:
		#	self.backup_city(save_city_path)

		# Report progress: save
		self.report(self.PREFIX, 'Pushing save...') #for "' + new_city_path + '"')

		# Create socket
		s = self.create_socket()
		if (s == None):
			self.report(self.PREFIX, 'Unable to push save because the server is unreachable.') #'Unable to save the city "' + new_city + '" because the server is unreachable.'
			return

		# Send save request
		s.send(b"push_save")
		s.recv(DMR_BUFFER_SIZE)

		# Send password if required
		if (self.server.password != None):
			s.send(self.server.password.encode())
			s.recv(DMR_BUFFER_SIZE)

		# Send user id
		s.send(self.server.user_id.encode())
		s.recv(DMR_BUFFER_SIZE)

		# Send file count
		s.send(str(len(save_city_paths)).encode())
		s.recv(DMR_BUFFER_SIZE)

		# Send files
		for save_city_path in save_city_paths:

			# Get region and city names
			region = os.path.split(os.path.dirname(save_city_path))[1]
			city = os.path.split(save_city_path)[1]
	
			# Send region name
			s.send(region.encode())
			s.recv(DMR_BUFFER_SIZE)

			# Send city name
			s.send(city.encode())
			s.recv(DMR_BUFFER_SIZE)

			# Send file
			self.send_file(s, save_city_path)
			s.recv(DMR_BUFFER_SIZE)

		# Separator
		s.send(DMR_SEPARATOR)

		# Handle response from server
		response = s.recv(DMR_BUFFER_SIZE).decode()
		if (response == "ok"):
			self.report(self.PREFIX, "Save push authorized") #TODO keep track locally of the client's claims
		else:
			self.report(self.PREFIX, "Save push not authorized. " + response)

		# Close socket
		s.close()


	def backup_city(self, filename):
		region = os.path.split(os.path.dirname(filename))[1]
		city = os.path.split(filename)[1]
		backup_directory = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRBackups", os.path.join(self.server.server_id, os.path.join(region, city))))
		if (not os.path.exists(backup_directory)):
			os.makedirs(backup_directory)
		shutil.copy(filename, os.path.join(backup_directory, datetime.now().strftime("%Y%m%d%H%M%S") + ".sc4"))


	def create_socket(self):
		"""TODO"""

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		tries_left = 60

		while(True):

			try:

				self.report("", "Connecting...")
				s.connect((host, port))

				self.report("", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					print("[ERROR] " + str(e))

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

		self.report("", 'Sending file "' + filename + '"...')

		filesize = os.path.getsize(filename)

		s.send(str(filesize).encode())
		s.recv(DMR_BUFFER_SIZE)

		with open(filename, "rb") as f:
			while True:
				bytes_read = f.read(DMR_BUFFER_SIZE)
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
		
		start_sc4()
		
		self.game_running = False

		global dmr_current_server
		dmr_current_server = None


# User Interfaces

class UI(tk.Tk):
	"""TODO"""


	def __init__(self):
		"""TODO"""


		print("Initializing...")


		# Init

		super().__init__()


		#Title

		self.title(DMR_TITLE)


		#Icon

		self.wm_iconbitmap(DMR_ICON) #TODO looks bad
		#TODO taskbar icon


		# Geometry

		self.geometry("500x500")
		self.minsize(500, 500)
		self.maxsize(500, 500)
		self.grid()
		self.lift()
		center_window(self)


		# Menu

		menu = Menu(self)  
		
		settings = Menu(menu, tearoff=0)  
		settings.add_command(label="SC4 Settings...", command=self.to_implement)      
		settings.add_separator()  
		settings.add_command(label="Exit", command=self.quit)  
		menu.add_cascade(label="Settings", menu=settings)  

		servers = Menu(menu, tearoff=0)  
		servers.add_command(label="Direct connect...", command=self.direct_connect)  
		servers.add_separator()  
		servers.add_command(label="Host...", command=self.to_implement)   
		menu.add_cascade(label="Servers", menu=servers)  

		help = Menu(menu, tearoff=0)  
		help.add_command(label="Readme...", command=self.to_implement)  
		help.add_command(label="Feedback...", command=self.to_implement)  
		menu.add_cascade(label="Help", menu=help)  
		
		self.config(menu=menu)  


		# Server List

		self.server_list = ServerListUI(self)
		self.server_list.grid(row = 0, column = 0)

	
	def to_implement(self):
		"""TODO"""
		tk.messagebox.showerror(title=DMR_TITLE, message="This feature is incomplete and will be available in future versions of the client.")


	def direct_connect(self):
		"""TODO"""
		print('"Direct connect..."')
		DirectConnectUI()


class DirectConnectUI(tk.Toplevel):


	def __init__(self):
		
		print("Initializing...")

		# Init
		super().__init__()

		# Title
		self.title('Direct Connect')

		# Icon
		self.iconbitmap(DMR_ICON) #TODO looks bad

		# Geometry
		self.geometry('290x110')
		self.maxsize(290, 110)
		self.minsize(290, 110)
		self.grid()
		center_window(self)
		
		# Priority
		self.grab_set()

		# Host Label
		self.host_label = ttk.Label(self, text="Host")
		self.host_label.grid(row=0, column=0, columnspan=1, padx=10, pady=20)

		# Host Entry
		self.host_entry = ttk.Entry(self, width=35)
		self.host_entry.insert(0, "") #TODO change to last server IP
		self.host_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=20, sticky="w")

		# Port Label
		self.port_label = ttk.Label(self, text="Port")
		self.port_label.grid(row=1, column=0, columnspan=1, padx=10, pady=0)

		# Port Entry
		self.port_entry = ttk.Entry(self, width=5)
		self.port_entry.insert(0, str(7246)) #TODO change to last server port
		self.port_entry.grid(row=1, column=1, columnspan=1, padx=10, pady=0, sticky="w")

		# Connect Button #TODO bind return key to button
		self.button = ttk.Button(self, text="Connect", command=self.connect, default="active")
		self.button.grid(row=1, column=3, columnspan=1, padx=10, pady=0, sticky="e")


	def connect(self):
		"""TODO"""
		print('"Connect"')
		host = self.host_entry.get()
		port = self.port_entry.get()
		try:
			if (len(host) < 1 or host == "0" or host == "localhost" or host == "127.0.0.1"):
				host = DMR_HOST
				#raise CustomException("Invalid host")
			try:
				port = int(port)
			except:
				port = DMR_PORT
				#raise CustomException("Invalid port")
			ServerLoaderUI(Server(host, port))
			self.destroy()
		except Exception as e:
			show_error(e)


class ServerListUI(tk.Frame):
	"""ServerList UI wrapper.

	Arguments:
		TODO

	Returns:
		TODO
	"""


	def __init__(self, root):
		"""TODO"""


		print("Initializing...")


		# Parameters

		self.root = root


		# Init

		super().__init__(self.root)


		# Geometry

		self.grid()


		# Label

		self.label = ttk.Label()
		self.label.grid(column=0, row=0, rowspan=1, columnspan=4, padx=10, pady=10)
		self.label['text'] = "Loading server list..."

		# Tree

		self.tree = ttk.Treeview(self)

		self.tree['columns'] = ('name', 'mayors', 'claimed', 'download', 'ping', 'rank')

		self.tree.column('name', width=10, anchor='w')
		self.tree.column('mayors', width=10, anchor='w')
		self.tree.column('claimed', width=10, anchor='w')
		self.tree.column('ping', width=10, anchor='w')
		
		self.tree.grid(column=0, row=1, rowspan=10, columnspan=4, padx=10, pady=10, sticky="we")

		self.tree.insert('', 'end', 'item1', values=("[SC4MP] Vanilla", "23", "36%", "542MB", "43ms", "1"))
		self.tree.insert('', 'end', 'item2')
		self.tree.insert('', 'end', 'item3')


class ServerLoaderUI(tk.Toplevel):
	"""TODO"""


	def __init__(self, server):
		"""TODO"""

		print("Initializing...")

		# Init
		super().__init__()

		# Geometry
		self.minsize(800, 100)
		self.maxsize(800, 100)
		self.grid()
		center_window(self)

		# Priority
		self.lift()

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

		# Geometry
		self.geometry("300x100")
		self.minsize(300, 50)
		self.maxsize(300, 50)
		self.grid()
		center_window(self)

		# Priority
		self.wm_attributes("-topmost", True)

		# Label
		self.label = ttk.Label(self, anchor="e")
		self.label.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10, sticky="e")


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
		self.log = "dmrclient.log" #"dmrclient-" + datetime.now().strftime("%Y%m%d%H%M%S") + ".log"
		if (os.path.exists(self.log)):
			os.remove(self.log)
   

	def write(self, message):
		"""TODO"""

		output = message

		if (message != "\n"):

			# Timestamp
			timestamp = datetime.now().strftime("[%H:%M:%S] ")

			# Label
			label = "[DMR"
			for item in inspect.stack()[1:]:
				try:
					label += "/" + item[0].f_locals["self"].__class__.__name__
					break
				except:
					pass
			label += "] "

			# Type and color
			type = "[INFO] "
			color = '\033[0m '
			TYPES_COLORS = [
				("[INFO] ", '\033[94m '),
				("[PROMPT]", '\033[1m '),
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
			if (label == "[DMR] " and type == "[INFO] "):
				color = '\033[94m '

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

def cmd(): #TODO incorporate this into the main method but enable this functionality using commandline arguments
	"""This method is meant to be run in a terminal instead of the main method for testing purposes.

	Arguments:
		None

	Returns:
		None
	"""

	sys.stdout = Logger()

	print("Client version " + DMR_VERSION)

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

	#global dmr_ui, dmr_ui_root
	#dmr_ui = True
	#dmr_ui_root = UI()
	#dmr_ui_root.withdraw()

	connect(Server(host, port))

	#dmr_ui.destroy()


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

		# Version
		print("Client version " + DMR_VERSION)

		# Prep
		prep()

		# UI
		global dmr_ui
		dmr_ui = UI()
		dmr_ui.mainloop()

	except Exception as e:

		# Error 
		show_error("A fatal error occurred.\n\n" + str(e)) # Please send the following information to the developers of the " + DMR_TITLE + " so this can be resolved: #TODO add traceback
		
		# Traceback
		traceback.print_exc()

if __name__ == '__main__':
	main()
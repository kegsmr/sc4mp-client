import configparser
import hashlib
import os
import shutil
import socket
import time
import subprocess
import threading as th
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox



# Path to the resources subdirectory
dmr_resources_path = "resources"

dmr_ui = False
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
DMR_TITLE = "DMR Client"
DMR_SEPARATOR = "<SEPARATOR>"
DMR_BUFFER_SIZE = 4096



# Methods

"""Loads the config file from the resources subdirectory or creates it if it does not yet exist.

Arguments:
	None

Returns:
	None
"""
def load_config():

	global DMR_LAUNCHPATH
	global DMR_LAUNCHRESW
	global DMR_LAUNCHRESH
	global DMR_CUSTOMPATH

	print("[DMR] Loading config...")

	#TODO add cpu options for start parameters
	configpath = get_dmr_path("config.ini")
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


"""Creates the required subdirectories in the launch directory if they do not yet exist.

Arguments:
	None

Returns:
	TODO
"""
def create_subdirectories():

	print("[DMR] Creating subdirectories...")

	directories = ["DMRCache", "DMRProfiles", "DMRSalvage", "Plugins", "Regions", os.path.join("DMRCache","Plugins"), os.path.join("DMRCache","Regions")]

	for directory in directories:
		new_directory = os.path.join(DMR_LAUNCHPATH, directory)
		if not os.path.exists(new_directory):
			try:
				os.makedirs(new_directory)
			except Exception as e:
				raise CustomException("Failed to create DMR subdirectories.\n\n" + str(e))
		#if directory == "Plugins":
			#noticepath = os.path.join(DMR_LAUNCHPATH, directory, "__PUT YOUR PLUGINS IN THIS FOLDER__.txt")
			#open(noticepath, 'a').close()


"""TODO

Arguments:
	TODO

Returns:
	TODO
"""
def connect(server):
	if (dmr_ui):
		ui_server_loader = ServerLoaderUI(server)
		ui_server_loader.mainloop()
		if (dmr_current_server != None):
			start_sc4()
	else:
		server_loader = ServerLoader(None, server)
		server_loader.run()
		if (dmr_current_server != None):
			game_monitor = GameMonitor(None, server)
			game_monitor.start()
			start_sc4()
			game_monitor.game_running = False


"""Attempts to find the install path of Simcity 4 and launches the game with custom launch parameters if found.

Arguments:
	TODO

Returns:
	TODO
"""
def start_sc4():
	print("[DMR] Starting Simcity 4...")

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

	print("[DMR] Simcity 4 closed.")


"""Gives the path of a given file in the DMR "resources" subdirectory

Arguments:
	filename (str)

Returns:
	TODO type: the path to the given file
"""
def get_dmr_path(filename):
	return os.path.join(dmr_resources_path, filename)


"""Creates the hashcode for a given file.

Arguments:
	filename (str)

Returns:
	TODO type: hashcode
"""
def md5(filename):
	hash_md5 = hashlib.md5()
	with open(filename, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


"""TODO

Arguments:
	TODO

Returns:
	TODO
"""
def purge_directory(directory):
	for filename in os.listdir(directory):
		file_path = os.path.join(directory, filename)
		try:
			if os.path.isfile(file_path) or os.path.islink(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path):
				shutil.rmtree(file_path)
		except PermissionError as e:
			raise CustomException('Failed to delete "' + file_path + '" because the file is being used by another process.') #\n\n' + str(e)


"""TODO"""
def event_generate(frame, event, when):
	if (frame != None):
		frame.event_generate(event, when=when)


"""TODO"""
def show_error(e):
	message = None
	if (isinstance(e, str)):
		message = e
	else: 
		message = str(e)

	print("[DMR] Error: " + message)

	if (dmr_ui):
		messagebox.showerror(DMR_TITLE, message)


"""
TODO
centers a tkinter window
:param win: the main window or Toplevel window to center
"""
def center_window(window):
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

"""TODO"""
class Server:


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.server_id = self.request_server_id()


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def request_server_id(self):
		print("(using placeholder server id)")
		return "server_id" #TODO actually get the server id


# Threads

"""TODO"""
class ServerList(th.Thread):


	"""TODO"""
	def __init__(self):

		print("(to implement)") #TODO


"""TODO"""
class ServerLoader(th.Thread):


	"""TODO"""
	def __init__(self, frame, server):
		th.Thread.__init__(self)
		self.frame = frame
		self.server = server


	"""TODO"""
	def run(self):
	
		host = self.server.host
		port = self.server.port

		try:

			self.report("[DMR Server Loader] ", 'Connecting to server at "' + str(host) + ":" + str(port) + '"...')

			self.report("[DMR Server Loader] ", "Loading plugins...")
			self.load("plugins")

			self.report("[DMR Server Loader] ", "Loading regions...")
			self.load("regions")

			self.report("[DMR Server Loader] ", "Prepping regions...")
			self.prep_regions()

			self.report("[DMR Server Loader] ", "Done.")

			global dmr_current_server
			dmr_current_server = self.server

		except Exception as e:

			if (self.frame != None):
				show_error("An error occurred while connecting to the server.\n\n" + str(e))
			else:
				print("[DMR Server Loader] Error: " + str(e))


		#time.sleep(1)

		if (self.frame != None):
			self.frame.destroy()

		
	def report(self, prefix, text):
		if (self.frame != None):
			self.frame.label['text'] = text
			self.frame.progress_bar['mode'] = "indeterminate"
			self.frame.progress_bar['maximum'] = 100
		print(prefix + text)
		#time.sleep(1)


	def report_progress(self, text, value, maximum):
		if (self.frame != None):
			self.frame.label['text'] = text
			self.frame.progress_bar['mode'] = "determinate"
			self.frame.progress_bar['value'] = value
			self.frame.progress_bar['maximum'] = maximum
		#time.sleep(.1)

	
	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def load(self, type):

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
		
		self.report("", "Fetching " + type + "...")

		s.send(type.encode())

		#TODO: get hash code and compare

		filename = os.path.join(DMR_LAUNCHPATH, os.path.join("DMRCache", os.path.join(directory, server_id + ".zip")))

		self.receive_file(s, filename) 

		self.report("", "Unpacking " + type + "...")
		shutil.unpack_archive(filename, os.path.join(DMR_LAUNCHPATH, directory))

		print("done.")


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def create_socket(self):

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		tries_left = 6

		while(True):

			try:

				self.report("[Socket] ", "Connecting...")
				s.connect((host, port))

				self.report("[Socket] ", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					print("[Socket] Error: " + str(e))

					count = 5
					while(count > 0):
						self.report("[Socket] ", "Connection failed. Retrying in " + str(count) + "...")					
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					raise CustomException("Maximum connection tries exceeded. Check your internet connection and firewall settings, then try again.\n\n" + str(e))

		return s


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def receive_file(self, s, filename):

		filesize = s.recv(DMR_BUFFER_SIZE).decode()

		print("[Socket] Receiving " + filesize + " bytes...")
		print("writing to " + filename)

		if (os.path.exists(filename)):
			os.remove(filename)

		filesize_read = 0
		with open(filename, "wb") as f:
			while True:
				bytes_read = s.recv(DMR_BUFFER_SIZE)
				if not bytes_read:    
					break
				f.write(bytes_read)
				filesize_read += len(bytes_read)
				self.report_progress('Downloading "' + filename + '" (' + str(filesize_read) + " / " + str(filesize) + " bytes)...", int(filesize_read), int(filesize)) #os.path.basename(os.path.normpath(filename))

		s.close()


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def prep_regions(self):

		self.server.regions = []

		path = os.path.join(DMR_LAUNCHPATH, "Regions")

		for directory in os.listdir(path):
			
			self.server.regions.append(directory)

			config_path = os.path.join(path, os.path.join(directory, "region.ini"))
			
			try:
				config = configparser.RawConfigParser()
				config.read(config_path)
				config.set("Regional Settings", "Name", "[DMR] " + config.get("Regional Settings", "Name"))
				with open(config_path, 'wt') as config_file:
					config.write(config_file)
			except:
				show_error("Failed to prep region config for " + directory + ".")

		shutil.unpack_archive(get_dmr_path("Regions.zip"), path)


"""TODO"""
class GameMonitor(th.Thread):


	"""TODO"""
	def __init__(self, frame, server):
		th.Thread.__init__(self)

		self.frame = frame
		self.server = server
		self.city_paths, self.city_hashcodes = self.get_cities()

		self.PREFIX = "[DMR Game Monitor] "

		self.game_running = True


	"""TODO"""
	def run(self):
		while (self.game_running):
			if (self.ping()):
				self.report_quietly("Connected to server. Monitoring for changes...")
			else:
				self.report(self.PREFIX, "Server unreachable.")
			new_city_paths, new_city_hashcodes = self.get_cities()
			for city_path in self.city_paths:
				if (not city_path in new_city_paths):
					self.push_delete(city_path)
			for new_city_path in new_city_paths:
				if (not new_city_path in self.city_paths):
					self.push_save(new_city_path)
				else:
					city_hashcode = self.city_hashcodes[self.city_paths.index(city_path)]
					new_city_hashcode = new_city_hashcodes[new_city_paths.index(new_city_path)]
					if (city_hashcode != new_city_hashcode):
						self.push_save(new_city_path)
			self.city_paths = new_city_paths
			self.city_hashcodes = new_city_hashcodes	
			time.sleep(5)
		if (self.frame != None):
			self.frame.destroy()


	"""TODO"""
	def get_cities(self):
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


	"""TODO"""
	def push_delete(self, city_path):

		self.report(self.PREFIX, 'Pushing deletion of "' + city_path + '"')

		city = os.path.split(city_path)[1]

		s = self.create_socket()

		if (s == None):
			self.report(self.PREFIX, 'Unable to delete the city "' + city + '" because the server is unreachable.')

		#TODO

	"""TODO"""
	def push_save(self, new_city_path):

		self.report(self.PREFIX, 'Pushing save for "' + new_city_path + '"')

		new_city = os.path.split(new_city_path)[1]

		s = self.create_socket()

		if (s == None):
			self.report(self.PREFIX, 'Unable to save the city "' + new_city + '" because the server is unreachable.')

		#TODO


	"""TODO

	Arguments:
		TODO

	Returns:
		TODO
	"""
	def create_socket(self):

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		tries_left = 60

		while(True):

			try:

				self.report("[Socket] ", "Connecting...")
				s.connect((host, port))

				self.report("[Socket] ", "Connected.")

				break

			except socket.error as e:
				
				if (tries_left > 0):
				
					print("[Socket] Error: " + str(e))

					count = 5
					while(count > 0):
						self.report("[Socket] ", "Connection failed. Retrying in " + str(count) + "...")					
						count = count - 1
						time.sleep(1)

					tries_left = tries_left - 1

				else:

					return None

		return s


	"""TODO"""
	def send_file(self, s, filename):

		self.report("Sending file " + filename + "...")

		filesize = os.path.getsize(filename)

		s.send(str(filesize).encode())

		with open(filename, "rb") as f:
			while True:
				bytes_read = f.read(DMR_BUFFER_SIZE)
				if not bytes_read:
					break
				s.sendall(bytes_read)


	"""TODO"""
	def ping(self):

		host = self.server.host
		port = self.server.port

		s = socket.socket()

		try:
			s.connect((host, port))
			s.send(b"ping")
			s.recv(DMR_BUFFER_SIZE)
			s.close()
			return True
		except socket.error as e:
			return False


	"""TODO"""
	def report(self, prefix, text):
		if (self.frame != None):
			self.frame.label['text'] = text
		print(prefix + text)


	"""TODO"""
	def report_quietly(self, text):
		if (self.frame != None):
			self.frame.label['text'] = text



# User Interfaces

"""ServerList UI wrapper.

Arguments:
	TODO

Returns:
	TODO
"""
class ServerListUI(tk.Tk):

	#TODO implement

	"""TODO"""
	def __init__(self):

		super().__init__()

		# Title
		self.winfo_toplevel().title(DMR_TITLE)

		#TODO Icon

		# Geometry
		self.geometry("500x500")
		self.minsize(500, 500)
		self.maxsize(500, 500)
		self.grid()
		center_window(self)

		# Menu
		menu = ttk.OptionMenu()

		# Label
		self.label = ttk.Label()
		self.label.grid(column=0, row=0, rowspan=1, columnspan=1, padx=10, pady=10)
		self.label['text'] = "Loading server list..."
		self.label['anchor'] = "center"


"""TODO"""
class ServerLoaderUI(tk.Tk):


	"""TODO"""
	def __init__(self, server):

		tk.Tk.__init__(self)

		# Title
		self.winfo_toplevel().title(DMR_TITLE)

		#TODO Icon

		# Geometry
		self.minsize(800, 100)
		self.maxsize(800, 100)
		self.grid()
		center_window(self)

		# Label
		self.label = ttk.Label()
		self.label.grid(column=0, row=0, columnspan=2, padx=10, pady=10)

		# Progress bar
		self.progress_bar = ttk.Progressbar(
			self,
			orient='horizontal',
			mode='determinate',
			length=780,
			maximum=100
		)
		self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=10)
		self.progress_bar.start(2)

		# Server loader
		self.server_loader = ServerLoader(self, server)
		self.server_loader.setDaemon(True)

	"""TODO"""
	def mainloop(self):
		self.server_loader.start()
		return tk.Tk.mainloop(self)


	"""TODO"""
	def progress_update(self):
		self.label['text'] = self.server_loader.label
		self.progress_bar['mode'] = self.server_loader.progress_bar_mode
		self.progress_bar['value'] = self.server_loader.progress_bar_value
		self.update()


"""TODO"""
class GameMonitorUI(tk.Tk):
	
	#TODO implement

	"""TODO"""
	def __init__(self):
		print("(to implement)")


# Exceptions

"""TODO"""
class CustomException(Exception):


	"""TODO"""
	def __init__(self, message, *args):
		super().__init__(args)
		self.message = message


	"""TODO"""
	def __str__(self):
		return self.message


# Main Method

"""This method is meant to be run in a terminal instead of the main method for testing purposes.

Arguments:
	None

Returns:
	None
"""
def cmd():
	#global dmr_ui
	#dmr_ui = True #TODO: just for testing!
	load_config()
	create_subdirectories()
	connect(Server(socket.gethostname(), 7246)) #TODO: replace with real server


"""The main method.

Arguments:
	None

Returns:
	None
"""
def main():

	global dmr_ui
	dmr_ui = True

	try:

		load_config()
		create_subdirectories()

		server_list_ui = ServerListUI()
		server_list_ui.mainloop()

	except Exception as e:

		show_error("A fatal error occurred.\n\n" + str(e)) # Please send the following information to the developers of the " + DMR_TITLE + " so this can be resolved:


if __name__ == '__main__':
	cmd()
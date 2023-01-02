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



# Path to the resources subdirectory
dmr_resources_path = "resources"

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
		except Exception as e:
			print('Failed to delete %s. Reason: %s' % (file_path, e))


"""TODO"""
def event_generate(frame, event, when):
	if (frame != None):
		frame.event_generate(event, when=when)


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
			except:
				return "Failed to create directories."
		#if directory == "Plugins":
			#noticepath = os.path.join(DMR_LAUNCHPATH, directory, "__PUT YOUR PLUGINS IN THIS FOLDER__.txt")
			#open(noticepath, 'a').close()

	return None


"""TODO

Arguments:
	TODO

Returns:
	TODO
"""
def connect(server):
	server_loader = ServerLoader(server)
	server_loader.run()


"""TODO

Arguments:
	TODO

Returns:
	TODO
"""
def ui_connect(server):
	ui_server_loader = UIServerLoader(server)
	ui_server_loader.mainloop()


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
		print("path to Simcity 4 not found")
		return

	arguments = [path, ' -UserDir:"' + DMR_LAUNCHPATH + '"', ' -intro:off', ' -w', ' -CustomResolution:enabled', ' -r' + str(DMR_LAUNCHRESW) + 'x' + str(DMR_LAUNCHRESH) + 'x32']
	
	try:
		subprocess.run(' '.join(arguments))
	except PermissionError:
		print("permission denied. Run the program as administrator.")

	print("[DMR] Simcity 4 closed.")



# Objects

"""TODO"""
class ServerList:


	"""TODO"""
	def __init__(self):

		print("(to implement)") #TODO


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


"""TODO"""
class ServerLoader(th.Thread):


	"""TODO"""
	def __init__(self, frame, server):
		self.frame = frame
		self.server = server
		th.Thread.__init__(self)


	"""TODO"""
	def run(self):
	
		host = self.server.host
		port = self.server.port

		self.report("[DMR Server Loader] ", 'Connecting to server at "' + str(host) + ":" + str(port) + '"...')

		self.report("[DMR Server Loader] ", "Loading plugins...")
		self.load("plugins")

		self.report("[DMR Server Loader] ", "Loading regions...")
		self.load("regions")

		self.report("[DMR Server Loader] ", "Prepping regions...")
		self.prep_regions()

		self.report("[DMR Server Loader] ", "Done.")

		time.sleep(1)

		if (self.frame != None):
			self.frame.destroy()

		
	def report(self, prefix, text):
		if (self.frame != None):
			self.frame.label['text'] = text
			self.frame.progress_bar['mode'] = "indeterminate"
			self.frame.progress_bar['maximum'] = 100
		print(prefix + text)
		time.sleep(.1)


	def report_progress(self, text, value, maximum):
		if (self.frame != None):
			self.frame.label['text'] = text
			self.frame.progress_bar['mode'] = "determinate"
			self.frame.progress_bar['value'] = value
			self.frame.progress_bar['maximum'] = maximum

	
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

		self.report("", "Fetching " + type + "...")

		s = self.create_socket() 
		
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

		print("[Socket] Connecting...")
		s.connect((host, port))

		print("[Socket] Connected.")

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

		path = os.path.join(DMR_LAUNCHPATH, "Regions")

		for directory in os.listdir(path):

			config_path = os.path.join(path, os.path.join(directory, "region.ini"))
			
			try:
				config = configparser.RawConfigParser()
				config.read(config_path)
				config.set("Regional Settings", "Name", "[DMR] " + config.get("Regional Settings", "Name"))
				with open(config_path, 'wt') as config_file:
					config.write(config_file)
			except:
				print("failed to prep region config for " + directory + ".")

		shutil.unpack_archive(get_dmr_path("Regions.zip"), path)


"""ServerList UI wrapper.

Arguments:
	TODO

Returns:
	TODO
"""
class UIServerList(tk.Tk):

	#TODO implement

	"""TODO"""
	def __init__(self):
		print("(to implement)")


	"""TODO"""
	def run(self):
		print("(to implement)")


"""TODO"""
class UIServerLoader(tk.Tk):


	"""TODO"""
	def __init__(self, server):

		tk.Tk.__init__(self)

		self.minsize(800, 100)
		self.maxsize(800, 100)

		self.winfo_toplevel().title(DMR_TITLE)

		self.grid()

		self.label = ttk.Label()

		self.label.grid(column=0, row=0, columnspan=2, padx=10, pady=10)

		self.progress_bar = ttk.Progressbar(
			self,
			orient='horizontal',
			mode='determinate',
			length=780,
			maximum=100
		)

		self.progress_bar.grid(column=0, row=1, columnspan=2, padx=10, pady=10)

		self.progress_bar.start(2)

		self.server_loader = ServerLoader(self, server)
		self.server_loader.setDaemon(True)

		self.eval('tk::PlaceWindow . center')

		#self.bind("<<progress_update>>", self.progress_update())


	def mainloop(self):
		self.server_loader.start()
		return tk.Tk.mainloop(self)


	"""TODO"""
	def progress_update(self):
		self.label['text'] = self.server_loader.label
		self.progress_bar['mode'] = self.server_loader.progress_bar_mode
		self.progress_bar['value'] = self.server_loader.progress_bar_value
		self.update()

	

# Main Method

"""This method is meant to be run in a terminal instead of the main method for testing purposes.

Arguments:
	None

Returns:
	None
"""
def cmd():
	load_config()
	create_subdirectories()
	ui_connect(Server(socket.gethostname(), 7246)) #TODO: replace with real server, no ui
	start_sc4()


"""The main method.

Arguments:
	None

Returns:
	None
"""
"""def main():
	dmr = wx.App()
	DMRClient(None)
	dmr.MainLoop()"""


if __name__ == '__main__':
	cmd()
from __future__ import annotations


def process_count(process_name): #TODO add MacOS compatability
	
	import platform
	import subprocess
	
	if platform.system() == "Windows":
		return int(subprocess.check_output(f"tasklist | find /I /C \"{process_name}\"", shell=True))
	else:
		return None
	

def md5(filename) -> str:

	import hashlib

	hash_md5 = hashlib.md5()
	with filename.open("rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


def format_version(version: tuple[int, int, int]) -> str:
	"""Converts a version number from a tuple to a string."""
	
	major, minor, patch = version

	return f'{major}.{minor}.{patch}'


def unformat_version(version: str) -> tuple[int, int, int]:
	"""Converts a version number from a string to a tuple."""

	return tuple([int(v) for v in version.split('.')])


def set_thread_name(name, enumerate=True):

	import threading as th

	if enumerate:

		thread_names = [thread.name for thread in th.enumerate()]

		count = 1
		while (True):
			thread_name = f"{name}-{count}"
			if not thread_name in thread_names:
				th.current_thread().name = thread_name
				return thread_name
			count += 1

	else:

		th.current_thread().name = name
		return name
	

def xor(conditionA, conditionB):
	
	return (conditionA or conditionB) and (not (conditionA and conditionB))


def filter_non_alpha_numeric(text: str) -> str:

	import re

	return " ".join(re.sub('[^0-9a-zA-Z ]+', " ", text).split())


def sanitize_directory_name(text: str) -> str:

	text = text.replace("..", "")
	
	for character in ["/", "\\"]:
		text = text.replace(character, "")

	text = text.replace("..", "")

	text = text.strip()

	return text


def format_filesize(size, scale=None):
	if scale is None:
		scale = size
	if scale >= 10 ** 13:
		return str(int(size / (10 ** 12))) + "TB"
	elif scale >= 10 ** 12:
		return str(float(int(size / (10 ** 11)) / 10)) + "TB"
	elif scale >= 10 ** 11:
		return str(int(size / (10 ** 9))) + "GB"
	elif scale >= 10 ** 10:
		return str(int(size / (10 ** 9))) + "GB"
	elif scale >= 10 ** 9:
		return str(float(int(size / (10 ** 8)) / 10)) + "GB"
	elif scale >= 10 ** 8:
		return str(int(size / (10 ** 6))) + "MB"
	elif scale >= 10 ** 7:
		return str(int(size / (10 ** 6))) + "MB"
	elif scale >= 10 ** 6:
		return str(float(int(size / (10 ** 5)) / 10)) + "MB"
	elif scale >= 10 ** 5:
		return str(int(size / (10 ** 3))) + "KB"
	elif scale >= 10 ** 4:
		return str(int(size / (10 ** 3))) + "KB"
	elif scale >= 10 ** 3:
		return str(float(int(size / (10 ** 2)) / 10)) + "KB"
	else:
		return str(int(size)) + "B"


def parse_filesize(filesize_str) -> int:
    """
    Parses a string representing a file size and returns its equivalent in bytes.

    Args:
        filesize_str (str): A string representing the file size (e.g., '8MB', '3.3KB').

    Returns:
        int: The file size in bytes.

    Raises:
        ValueError: If the input format is invalid.
    """

    # Define size multipliers
    size_multipliers = {
        'B': 1,
        'KB': 10**3,
        'MB': 10**6,
        'GB': 10**9,
        'TB': 10**12
    }

    import re

    # Regular expression to match the input pattern
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(B|KB|MB|GB|TB)", filesize_str.strip(), re.IGNORECASE)

    if not match:
        raise ValueError("Invalid file size format. Use format like '8MB' or '3.3KB'.")

    # Extract the numeric part and the unit
    size, unit = match.groups()
    size = float(size)
    unit = unit.upper()

    # Compute the size in bytes
    if unit not in size_multipliers:
        raise ValueError(f"Unsupported unit '{unit}'. Supported units are: {', '.join(size_multipliers.keys())}.")

    return int(size * size_multipliers[unit])


def format_time_ago(time, now=None):

	from datetime import datetime, timedelta

	if time is None:
		return "Never"

	if not now:
		now = datetime.now()

	if time + timedelta(days=30) > now:

		seconds = (now - time).total_seconds()

		if seconds < 60:
			return f"{int(seconds)}s ago"
		elif seconds < 3600:
			minutes = seconds // 60
			return f"{int(minutes)}m ago"
		elif seconds < 86400:
			hours = seconds // 3600
			return f"{int(hours)}h ago"
		else:
			days = seconds // 86400
			return f"{int(days)}d ago"

	else:

		months = (now.year - time.year) * 12 + now.month - time.month
		
		if months < 12:
			return f"{int(months)}mo ago"
		else:
			years = months / 12
			if years < 1000:
				return f"{int(years)}y ago"
			else:
				return "Never"
			

def get_server_list() -> list[tuple]:
	"""Returns a list of `(<host>, <port>)` tuples extracted from the `servers.txt` file."""

	from pathlib import Path

	servers = [("servers.sc4mp.org", port) for port in range(7240, 7250)]

	servers_txt_path = Path("resources") / "servers.txt"

	if servers_txt_path.exists():

		s = [(line.split()[0], int(line.split()[1])) for line in open(servers_txt_path) if line.strip()]
		s.reverse()

		for server in s:
			if server not in servers:
				servers.append(server)

	return servers


def update_server_list(maximum=100):
	"""Updates the `servers.txt` file with servers fetched from the SC4MP API. To be used in release workflows only!"""

	from pathlib import Path
	import requests

	URL = "https://api.sc4mp.org/servers"
	
	response = requests.get(URL)
	response.raise_for_status()
	
	servers = {(entry["host"], entry["port"]) for entry in response.json()}
	
	server_file = Path("resources") / "servers.txt"
	
	if server_file.exists():
		with server_file.open("r") as file:
			existing_servers = {
				tuple(line.strip().split("\t")) for line in file if line.strip()
			}
			existing_servers = {(host, int(port)) for host, port in existing_servers}
	else:
		existing_servers = set()
	
	# Identify new servers to append
	servers = servers - existing_servers
	
	# Append new servers to the file
	with server_file.open("a") as file:
		for server in servers:
			file.write(f"{server[0]}\t{server[1]}\n")

	# Open the file and read all lines
	with server_file.open("r") as file:
		lines = file.readlines()
	
	# If the file has more than `maxiumum`, slice the list to keep only the last `maxiumum` lines
	if len(lines) > maximum:

		lines = lines[-maximum:]
	
		# Write the remaining lines back to the file
		with server_file.open("w") as file:
			file.writelines(lines)


def format_title(title: str, version=None) -> str:

	t = title.split(" ")

	if version:
		t.append(f"v{version}")
	if is_frozen():
		if is_32_bit():
			if is_windows:
				t.append("(x86)")
			else:
				t.append("(32-bit)")
	else:
		t.append("(Python)")

	return " ".join(t)


def is_32_bit():

	import struct

	return 8 * struct.calcsize('P') == 32


def is_frozen():

	import sys

	return getattr(sys, 'frozen', False)


def is_windows():

	import platform

	return platform.system() == "Windows"


if __name__ == "__main__":
	update_server_list()


def format_filesize(size, scale=None):
	if scale is None:
		scale = size
	if scale >= 10 ** 13:
		return str(int(size / (10 ** 12))) + "TB"
	elif scale >= 10 ** 12:
		return str(float(int(size / (10 ** 11)) / 10)) + "TB"
	elif scale >= 10 ** 11:
		return str(int(size / (10 ** 9))) + "GB"
	elif scale >= 10 ** 10:
		return str(int(size / (10 ** 9))) + "GB"
	elif scale >= 10 ** 9:
		return str(float(int(size / (10 ** 8)) / 10)) + "GB"
	elif scale >= 10 ** 8:
		return str(int(size / (10 ** 6))) + "MB"
	elif scale >= 10 ** 7:
		return str(int(size / (10 ** 6))) + "MB"
	elif scale >= 10 ** 6:
		return str(float(int(size / (10 ** 5)) / 10)) + "MB"
	elif scale >= 10 ** 5:
		return str(int(size / (10 ** 3))) + "KB"
	elif scale >= 10 ** 4:
		return str(int(size / (10 ** 3))) + "KB"
	elif scale >= 10 ** 3:
		return str(float(int(size / (10 ** 2)) / 10)) + "KB"
	else:
		return str(int(size)) + "B"


def parse_filesize(filesize_str) -> int:
    """
    Parses a string representing a file size and returns its equivalent in bytes.

    Args:
        filesize_str (str): A string representing the file size (e.g., '8MB', '3.3KB').

    Returns:
        int: The file size in bytes.

    Raises:
        ValueError: If the input format is invalid.
    """

    # Define size multipliers
    size_multipliers = {
        'B': 1,
        'KB': 10**3,
        'MB': 10**6,
        'GB': 10**9,
        'TB': 10**12
    }

    import re

    # Regular expression to match the input pattern
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(B|KB|MB|GB|TB)", filesize_str.strip(), re.IGNORECASE)

    if not match:
        raise ValueError("Invalid file size format. Use format like '8MB' or '3.3KB'.")

    # Extract the numeric part and the unit
    size, unit = match.groups()
    size = float(size)
    unit = unit.upper()

    # Compute the size in bytes
    if unit not in size_multipliers:
        raise ValueError(f"Unsupported unit '{unit}'. Supported units are: {', '.join(size_multipliers.keys())}.")

    return int(size * size_multipliers[unit])


def is_socket_listening(host: str, port: int) -> bool:
	"""
	Check if a socket is in use on the specified host and port.

	Parameters:
	- host (str): The hostname or IP address to check.
	- port (int): The port number to check.

	Returns:
	- bool: True if the socket is in use, False otherwise.
	"""

	import socket

	s = socket.socket()

	try:

		s.settimeout(1)  # Set timeout to avoid hanging
		s.connect((host, port))

		return True  # Connection succeeded, so the socket is in use
	
	except (socket.error, socket.timeout):

		return False  # Connection failed, so the socket is not in use
	
	finally:

		s.close()  # Ensure the socket is closed


def get_process_creation_time(pid):
	"""
	Gets the creation date of a process from its PID on Windows.
	
	Parameters:
		pid (int): The process ID.
	
	Returns:
		datetime: The creation date and time of the process.
	"""

	import ctypes
	import ctypes.wintypes
	from datetime import datetime, timedelta

	# Constants
	PROCESS_QUERY_INFORMATION = 0x0400
	PROCESS_VM_READ = 0x0010

	# Open the process
	h_process = ctypes.windll.kernel32.OpenProcess(
		PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
	)
	if not h_process:
		raise Exception(f"Failed to open process with PID {pid}. Error code: {ctypes.GetLastError()}")

	# Create a FILETIME structure to store creation time
	creation_time = ctypes.wintypes.FILETIME()
	exit_time = ctypes.wintypes.FILETIME()
	kernel_time = ctypes.wintypes.FILETIME()
	user_time = ctypes.wintypes.FILETIME()

	# Get process times
	success = ctypes.windll.kernel32.GetProcessTimes(
		h_process,
		ctypes.byref(creation_time),
		ctypes.byref(exit_time),
		ctypes.byref(kernel_time),
		ctypes.byref(user_time),
	)
	if not success:
		ctypes.windll.kernel32.CloseHandle(h_process)
		raise Exception(f"Failed to get process times for PID {pid}. Error code: {ctypes.GetLastError()}")

	# Close the process handle
	ctypes.windll.kernel32.CloseHandle(h_process)

	# Convert FILETIME to a Python datetime
	def filetime_to_datetime(ft):
		# FILETIME is a 64-bit value representing the number of 100-nanosecond intervals since January 1, 1601 (UTC)
		time = (ft.dwHighDateTime << 32) + ft.dwLowDateTime
		return datetime(1601, 1, 1) + timedelta(microseconds=time // 10)

	return filetime_to_datetime(creation_time)


def get_public_ip_address(timeout=10):

	import urllib

	try:

		# Send a request to a public IP API and read the response
		with urllib.request.urlopen('https://api.ipify.org', timeout=timeout) as response:

			# The public IP is returned as a string
			public_ip = response.read().decode('utf-8')

		return public_ip

	except urllib.error.URLError as e:
		
		print(f"Error fetching IP address: {e}")
		return None
	

def has_powershell():
	"""Checks if PowerShell is available."""

	import platform

	if is_windows() and int(platform.version().split('.')[0]) >= 10:
		return True
	else:
		return False
	

def generate_server_id():

	import random
	import string

	return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(32))


def generate_server_name():

	import getpass
	import socket

	return getpass.getuser() + " on " + socket.gethostname()
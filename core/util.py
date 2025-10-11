from __future__ import annotations

import ctypes
import ctypes.wintypes
import datetime
import getpass
import glob
import hashlib
import mimetypes
import os
import platform
import random
import re
import socket
import string
import struct
import subprocess
import sys
import time
import threading as th
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

try:
	import requests
except ImportError:
	pass


#TODO add MacOS compatability
def process_count(process_name):

	if platform.system() == "Windows":
		return int(
			subprocess.check_output(
				f"tasklist | find /I /C \"{process_name}\"", shell=True
			)
		)
	else:
		return None


def md5(filename) -> str:

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

	if version.startswith("v"):
		version = version[1:]

	return tuple([int(v) for v in version.split('.')])


def set_thread_name(name, enumerate=True):

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

	return " ".join(re.sub('[^0-9a-zA-Z ]+', " ", text).split())


def sanitize_directory_name(text: str) -> str:

	text = text.replace("..", "")
	
	for character in ["/", "\\"]:
		text = text.replace(character, "")

	text = text.replace("..", "")

	text = text.strip()

	return text


def format_time_ago(time, now=None):

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
	"""
	Returns a list of `(<host>, <port>)` tuples extracted from the 
	`servers.txt` file.
	"""

	servers = [("servers.sc4mp.org", port) for port in range(7240, 7250)]

	servers_txt_path = Path("resources") / "servers.txt"

	if servers_txt_path.exists():

		s = [(line.split()[0], int(line.split()[1])) 
	   		for line in open(servers_txt_path) if line.strip()]
		s.reverse()

		for server in s:
			if server not in servers:
				servers.append(server)

	return servers


def update_server_list(maximum=100):
	"""
	Updates the `servers.txt` file with servers fetched from the SC4MP API. To 
	be used in release workflows only!
	"""

	URL = "https://api.sc4mp.org/servers"
	
	response = requests.get(URL)
	response.raise_for_status()
	
	servers = {(entry["host"], entry["port"]) for entry in response.json()}
	
	server_file = Path("resources") / "servers.txt"
	
	if server_file.exists():
		with server_file.open("r") as file:
			existing_servers = {
				tuple(line.strip().split("\t")) 
				for line in file if line.strip()
			}
			existing_servers = {
				(host, int(port)) for host, port in existing_servers
			}
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
	
	# If the file has more than `maxiumum`, slice the list to keep only the 
	# last `maxiumum` lines
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
			if is_windows():
				t.append("(x86)")
			else:
				t.append("(32-bit)")
	else:
		t.append("(Python)")

	return " ".join(t)


def is_32_bit():

	return 8 * struct.calcsize('P') == 32


def is_frozen():

	return getattr(sys, 'frozen', False)


def is_windows():

	return platform.system() == "Windows"


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
    Parses a string representing a file size and returns its equivalent in 
	bytes.

    Args:
        filesize_str (str): A string representing the file size (e.g., '8MB', 
		'3.3KB').

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

    # Regular expression to match the input pattern
    match = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(B|KB|MB|GB|TB)", 
		filesize_str.strip(), re.IGNORECASE)

    if not match:
        raise ValueError(
			"Invalid file size format. Use format like '8MB' or '3.3KB'."
		)

    # Extract the numeric part and the unit
    size, unit = match.groups()
    size = float(size)
    unit = unit.upper()

    # Compute the size in bytes
    if unit not in size_multipliers:
        raise ValueError(
			f"Unsupported unit '{unit}'. "
			f"Supported units are: {', '.join(size_multipliers.keys())}."
		)

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

	# Constants
	PROCESS_QUERY_INFORMATION = 0x0400
	PROCESS_VM_READ = 0x0010

	# Open the process
	h_process = ctypes.windll.kernel32.OpenProcess(
		PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
	)
	if not h_process:
		raise Exception(
			f"Failed to open process with PID {pid}. "
			f"Error code: {ctypes.GetLastError()}"
		)

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
		raise Exception(
			f"Failed to get process times for PID {pid}. "
			f"Error code: {ctypes.GetLastError()}"
		)

	# Close the process handle
	ctypes.windll.kernel32.CloseHandle(h_process)

	# Convert FILETIME to a Python datetime
	def filetime_to_datetime(ft):

		# FILETIME is a 64-bit value representing the number of 100-nanosecond 
		# intervals since January 1, 1601 (UTC)
		time = (ft.dwHighDateTime << 32) + ft.dwLowDateTime

		return datetime(1601, 1, 1) + timedelta(microseconds=time // 10)

	return filetime_to_datetime(creation_time)


def get_public_ip_address(timeout=10):

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

	if is_windows() and int(platform.version().split('.')[0]) >= 10:
		return True
	else:
		return False
	

def generate_server_id():

	return ''.join(
		random.SystemRandom().choice(string.ascii_letters + string.digits) for i in range(32)
	)


def generate_server_name():

	return getpass.getuser() + " on " + socket.gethostname()


def publish_release(repo, token, version, target="main", name="", body="", 
					assets=[], draft=True, prerelease=False):

	if not name:
		name = f"Draft {version}"

	# github_token = os.getenv("GITHUB_TOKEN")
	# if not github_token:
	# 	print("GITHUB_TOKEN not found in environment variables.")
	# 	return
	
	headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
	tag = f"v{version}"
	release_url = f"https://api.github.com/repos/{repo}/releases"

	# Fetch existing releases
	response = requests.get(release_url, headers=headers)
	response.raise_for_status()
	releases = response.json()

	# Check if the release exists
	release = next((r for r in releases if r["tag_name"] == tag), None)

	if release:
		if release["draft"]:
			# Delete draft release
			print(f"Deleting existing draft release {tag}...")
			delete_url = f"https://api.github.com/repos/{repo}/releases/{release['id']}"
			requests.delete(delete_url, headers=headers).raise_for_status()
		else:
			# If release is already published, do not modify it
			print(f"Release {tag} is already published. Skipping upload.")
			return

	# Create a new draft release
	print(f"Creating new draft release for {tag}...")
	data = {
		"tag_name": tag,
		"target_commitish": target,
		"name": name, 
		"body": body, 
		"draft": draft, 
		"prerelease": prerelease,
	}

	response = requests.post(release_url, headers=headers, json=data)
	response.raise_for_status()
	release = response.json()
	
	# Upload assets
	upload_url = release["upload_url"].split("{?name,label}")[0]
	for asset in assets:
		asset_name = os.path.basename(asset)
		print(f"Uploading {asset_name}...")
		mime_type, _ = mimetypes.guess_type(asset)
		mime_type = mime_type or 'application/octet-stream'
		with open(asset, "rb") as f:
			response = requests.post(
				f"{upload_url}?name={asset_name}",
				headers={"Authorization": f"token {token}", "Content-Type": mime_type},
				data=f.read()
			)
			response.raise_for_status()
		print(f"Successfully uploaded {asset_name}.")

	print(f"Release {tag} published successfully as a draft. You can edit the draft at https://github.com/{repo}/releases.")


def get_release_asset_path(directory, prefix):

	# Create a pattern to match all files that start with the given prefix
	pattern = os.path.join(directory, f"{prefix}*")
	
	# Get a list of all matching files
	files = glob.glob(pattern)
	
	if not files:
		return None  # Return None if no files match the prefix
	
	# Get the file with the newest modification time
	newest_file = max(files, key=os.path.getmtime)
	
	return newest_file


def get_current_git_branch():

	# Run the Git command to get the current branch
	result = subprocess.run(
		["git", "rev-parse", "--abbrev-ref", "HEAD"],
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
		check=True
	)

	# Return the current branch name
	return result.stdout.strip()


def replace_in_file(path, old, new):

    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace(old, new)
    
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)


def get_version():
    with open("VERSION") as file:
        return file.read().strip()


def update_readme_version(path: str, version: str) -> None:
	"""Replace the version inside <version>...</version> with new_version."""

	with open(path, 'r', encoding='utf-8') as f:
		content = f.read()

	# Replace the contents inside the <version> tag
	updated_content = re.sub(
		r'(<version>)(.*?)(</version>)',
		rf'\g<1>{version}\g<3>',
		content,
		flags=re.IGNORECASE | re.DOTALL
	)

	with open(path, 'w', encoding='utf-8') as f:
		f.write(updated_content)

	# print(f'Updated version to "{version}" in "{path}"')



def update_inno_setup_version(path: str, version: str) -> None:
    """Update the #define MyAppVersion directive in an Inno Setup script."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match a line like: #define MyAppVersion "0.8.5"
    pattern = r'^(#define\s+MyAppVersion\s+)".*?"'
    replacement = rf'\1"{version}"'

    updated_content, count = re.subn(
        pattern,
        replacement,
        content,
        flags=re.MULTILINE
    )

    if count == 0:
        print(f'Warning: No MyAppVersion definition found in "{path}".')
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        # print(f'Updated MyAppVersion to "{version}" in "{path}".')


def update_python_version(path: str, version: str) -> None:
    """Update SC4MP_VERSION = "..." in a Python file."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match SC4MP_VERSION = "..."
    updated_content, count = re.subn(
        r'^(SC4MP_VERSION\s*=\s*)["\'].*?["\']',
        rf'\1"{version}"',
        content,
        flags=re.MULTILINE
    )

    if count == 0:
        print(f'Warning: No SC4MP_VERSION assignment found in "{path}".')
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        print(f'Updated SC4MP_VERSION to "{version}" in "{path}".')


def sanitize_relpath(basepath: Path, relpath: str) -> Path:

	fullpath = basepath / relpath

	if str(fullpath.resolve()).startswith(str(basepath.resolve())):
		return fullpath
	else:
		raise ValueError(f"Invalid relative path: \"{relpath}\".")


def calculate_latency(function: Callable) -> int:
	"""
	Calls a function and returns the time in miliseconds it took to execute.
	"""

	start = time.time()
	function()
	end = time.time()
	return round(1000 * (end - start))

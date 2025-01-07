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


def format_time_ago(time):

	from datetime import datetime, timedelta

	if time is None:
		return "Never"

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

	return [(line.split()[0], int(line.split()[1])) for line in open(Path("resources") / "servers.txt") if line.strip()]


def update_server_list():
	"""Updates the `servers.txt` file with servers fetched from the SC4MP API. To be used in release workflows only!"""

	from pathlib import Path
	import requests

	official_servers = {("servers.sc4mp.org", port) for port in range(7240, 7250)}
	
	URL = "https://api.sc4mp.org/servers"

	response = requests.get(URL)
	response.raise_for_status()

	all_servers = official_servers.union(
		{(entry["host"], entry["port"]) for entry in response.json()}
	)

	official = sorted(server for server in all_servers if server[0] == "servers.sc4mp.org")
	others = sorted(server for server in all_servers if server[0] != "servers.sc4mp.org")
	
	lines = [f"{server[0]}\t{server[1]}\n" for server in official + others]
	
	with open(Path("resources") / "servers.txt", "w") as file:
		file.writelines(lines)
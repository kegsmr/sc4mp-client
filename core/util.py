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


def filter_non_alpha_numeric(text: str):

	import re

	return " ".join(re.sub('[^0-9a-zA-Z ]+', " ", text).split())


def sanitize_directory_name(text: str):

	for character in ["/", "\\"]:
		text.replace(character, "")

	return text
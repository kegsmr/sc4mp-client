from __future__ import annotations

import os
import json
import shutil
from threading import Lock
from pathlib import Path


class Database:


	def __init__(self, filename):

		self.filename = Path(filename)
	
		self._backup_filename = Path(f"{filename}.bak")
		self._data = {}

		self._serialized_data = None
		self._lock = Lock()

		self._load()


	@staticmethod
	def _load_file(filename: Path) -> str:
		try:
			with open(filename, encoding='utf-8') as file:
				return file.read()
		except FileNotFoundError:
			return "{}"
		
	
	@staticmethod
	def _update_file(filename: Path, serialized_data: str):
		with open(filename, 'w', encoding='utf-8') as file:
			file.write(serialized_data)

	
	@staticmethod
	def _serialize(data: dict) -> str:
		return json.dumps(data, indent=4)
	

	@staticmethod
	def _deserialize(serialized_data: str) -> dict:
		return json.loads(serialized_data)


	def _load(self):
		for filename in (self.filename, self._backup_filename):
			try:
				self._load_json(filename)
				return
			except Exception:
				continue
		raise DatabaseException(
			f"Failed to load \"{self.filename}\". "
			f"Loading the backup at \"{self._backup_filename}\" also failed."
		)


	def _load_json(self, filename: Path):
		self._serialized_data = self._load_file(filename)
		self._data = self._deserialize(self._serialized_data)


	def update_json(self):
		with self._lock:
			serialized_data = self._serialize(self._data.copy())
			if serialized_data == self._serialized_data:
				return
			if self.filename.exists():
				if self._backup_filename.exists():
					os.unlink(self._backup_filename)
				shutil.copy(self.filename, self._backup_filename)
			self._update_file(self.filename, serialized_data)
			self._serialized_data = serialized_data


	def __repr__(self):
		with self._lock:
			return self._data.__repr__()


	def __getitem__(self, key):
		with self._lock:
			return self._data[key]


	def __setitem__(self, key, value):
		with self._lock:
			self._data[key] = value


	def __delitem__(self, key):
		with self._lock:
			del self._data[key]


	def __iter__(self):
		with self._lock:
			return iter(list(self._data.keys()))  # snapshot


	def __len__(self):
		with self._lock:
			return len(self._data)


	def __contains__(self, key):
		with self._lock:
			return key in self._data


	def keys(self):
		with self._lock:
			return list(self._data.keys())


	def values(self):
		with self._lock:
			return list(self._data.values())


	def items(self):
		with self._lock:
			return list(self._data.items())


	def get(self, key, default=None):
		with self._lock:
			return self._data.get(key, default)


	def pop(self, key, default=None):
		with self._lock:
			return self._data.pop(key, default)


	def popitem(self):
		with self._lock:
			return self._data.popitem()


	def clear(self):
		with self._lock:
			self._data.clear()


	def update(self, other=(), **kwargs):
		with self._lock:
			self._data.update(other, **kwargs)


	def setdefault(self, key, default=None):
		with self._lock:
			return self._data.setdefault(key, default)


class DatabaseException(Exception):
	pass

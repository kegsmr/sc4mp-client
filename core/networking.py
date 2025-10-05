import socket
import json
import struct
import time
import hashlib
from pathlib import Path
from typing import Optional, Any, Type


SC4MP_BUFFER_SIZE = 4096
SC4MP_DELAY = 0.1

MESSAGE_PROTOCOL = 'SC4MP'

MESSAGE_TYPE_REQUEST = 'Req'
MESSAGE_TYPE_RESPONSE = 'Res'

COMMAND_ADD_SERVER = 'AddSrv'
COMMAND_CHECK_PASSWORD = 'ChkPwd'
COMMAND_INFO = 'Info'
COMMAND_PASSWORD_ENABLED = 'PwdEnb'
COMMAND_PING = 'Ping'
COMMAND_PLUGINS_TABLE = 'PlgTab'
COMMAND_PLUGINS_DATA = 'PlgDat'
COMMAND_PRIVATE = 'Prv'
COMMAND_REGIONS_TABLE = 'RgnTab'
COMMAND_REGIONS_DATA = 'RgnDat'


def send_json(s: socket.socket, data, length_encoding="I"):

	if data is None:
		data = b"" 
	else:
		data = json.dumps(data).encode()

	s.sendall(struct.pack(length_encoding, len(data)) + data)


def recv_json(s: socket.socket, length_encoding="I"):

	length_header_size = struct.calcsize(length_encoding)
	length_header = b""

	while len(length_header) < length_header_size:

		new_data = s.recv(length_header_size - len(length_header))

		if new_data:

			length_header += new_data

		else:

			time.sleep(SC4MP_DELAY)

	data_size = struct.unpack(length_encoding, length_header)[0]
	data_size_read = 0

	data = b""
	
	while data_size_read < data_size:

		buffer_size = min(SC4MP_BUFFER_SIZE, data_size - data_size_read)

		new_data = s.recv(buffer_size)

		if new_data:

			data += new_data
			
			data_size_read += len(new_data)

		else:
			
			time.sleep(SC4MP_DELAY)

	if len(data) < 1:
		raise NetworkException('No data received.')
	else:
		return json.loads(data.decode())


def recv_exact(s: socket.socket, length) -> bytes:

	data = b""

	while len(data) < length:
		data += s.recv(length - len(data))

	return data
	

def send_message(s: socket.socket, is_request=True, command="Ping", headers=None):

	try:

		if headers is None:
			headers = {}

		m = MESSAGE_PROTOCOL
		if is_request:
			m += MESSAGE_TYPE_REQUEST
		else:
			m += MESSAGE_TYPE_RESPONSE
		m += command

		message = m.encode('ascii')

		while len(message) < 14:
			message += b"\x00"

		h = json.dumps(headers).encode()
		l = struct.pack("H", len(h))

		message += l + h

		s.sendall(message)

	except Exception as e:
		raise NetworkException(
			f"Error sending {'request' if is_request else 'response'} "
			f"{command!r} with headers {headers!r}."
		) from e


def recv_message(s: socket.socket):

	try:

		pb = recv_exact(s, len(MESSAGE_PROTOCOL))
		p = pb.decode('ascii')
		if p != MESSAGE_PROTOCOL:
			raise NetworkException(
				f"Expected {MESSAGE_PROTOCOL!r}, but received {p!r}."
			)

		tb = recv_exact(s, max(len(MESSAGE_TYPE_REQUEST), len(MESSAGE_TYPE_RESPONSE)))
		t = tb.rstrip(b"\x00").decode('ascii')
		if t == MESSAGE_TYPE_REQUEST:
			is_request = True
		elif t == MESSAGE_TYPE_RESPONSE:
			is_request = False
		else:
			raise NetworkException(
				f"Expected message type {MESSAGE_TYPE_REQUEST!r} or "
				f"{MESSAGE_TYPE_RESPONSE!r} but received {t!r}."
			)

		c = recv_exact(s, 6)
		command = c.rstrip(b"\x00").decode('ascii')

		l = struct.unpack("H", recv_exact(s, 2))[0]
		headers = json.loads(recv_exact(s, l).decode())

	except Exception as e:
		raise NetworkException(
			"Error receiving message."
		) from e

	return is_request, command, headers
	

def request(s, command, **headers) -> dict:

	send_message(s, True, command, headers)

	is_request, c, h = recv_message(s)

	if is_request:
		raise NetworkException(
			"Expected response message but received request message."
		)

	if c != command:
		raise NetworkException(
			f"Expected command {command!r} but received {c!r}."
		)

	return h


def respond(s, command, **headers):

	return send_message(s, False, command, headers)


def is_success(headers: dict):

	STATUS = 'status'
	SUCCESS = 'success'

	if STATUS not in headers:
		raise NetworkException(f"Repsonse headers missing {STATUS!r}.")

	return headers[STATUS] == SUCCESS


def pluck_header(headers: dict, key: str, type: Type) -> Any:

	if key not in headers:
		raise NetworkException(f"Headers missing {key!r}.")
	
	data = headers[key]
	if not isinstance(data, type):
		try:
			data = type(data)
		except Exception as e:
			raise NetworkException(
				f"Expected type {type!r} for header {key!r}."
			) from e

	return data


def recv_files(s: socket.socket, file_table):
	
	for checksum, filesize, relpath in file_table:
		filesize_read: int = 0
		checksummer = hashlib.md5()
		while filesize_read < filesize:
			filesize_remaining = filesize - filesize_read
			buffersize = min(filesize_remaining, SC4MP_BUFFER_SIZE)
			chunk = s.recv(buffersize)
			if not chunk:
				raise NetworkException("Connection closed.")
			filesize_read += len(chunk)
			checksummer.update(chunk)
			yield (checksum, filesize, relpath), chunk
		checksum_actual = checksummer.hexdigest()
		if checksum != checksum_actual:
			raise NetworkException(
				f"Expected checksum {checksum!r} but received "
				f"{checksum_actual!r}."
			)


class Socket(socket.socket):


	def __init__(self, s:Optional[socket.socket]=None):

		self.headers = {}

		if s:

			super().__init__(s.family, s.type, s.proto, socket.dup(s.fileno()))
			self.settimeout(s.gettimeout())

		else:

			super().__init__()


	def set_headers(self, **headers):

		self.headers = headers


	def send_json(self, data, length_encoding="I"):

		send_json(self, data, length_encoding)


	def recv_json(self, length_encoding="I"):

		return recv_json(self, length_encoding)


	def send_message(self, is_request=True, command="Ping", headers=None):

		send_message(self, is_request, command, headers)


	def recv_message(self):

		return recv_message(self)


	def request(self, command, **headers):

		return request(self, command, **{**self.headers, **headers})


	def respond(self, command, **headers):

		return respond(self, command, **{**self.headers, **headers})


	def recv_files(self, file_table):

		return recv_files(self, file_table)


class ClientSocket(Socket):

	
	def __init__(self, address=None, timeout=10, **options):

		super().__init__(**options)

		self.settimeout(timeout)

		if address:
			self.connect(address)
	

	def add_server(self, port, **headers) -> bool:

		return is_success(
			self.request(COMMAND_ADD_SERVER, port=port, **headers)
		)


	def check_password(self, password, **headers) -> bool:

		return is_success(
			self.request(COMMAND_CHECK_PASSWORD, password=password, **headers)
		)


	def info(self, **headers) -> dict:

		return self.request(COMMAND_INFO, **headers)


	def password_enabled(self, **headers) -> bool:

		return pluck_header(
			self.request(COMMAND_PASSWORD_ENABLED, **headers),
			'password_enabled', bool
		)


	def ping(self, **headers) -> dict:

		return self.request(COMMAND_PING, **headers)
	

	def plugins_table(self, **headers) -> list:

		self.request(COMMAND_PLUGINS_TABLE, **headers)

		return self.recv_json()
	
	
	def plugins_data(self, file_table: list, **headers):

		self.request(COMMAND_PLUGINS_DATA, **headers)
		self.send_json(file_table)

		for chunk in self.recv_files(file_table):
			yield chunk


	def private(self, **headers) -> bool:
	
		return pluck_header(
			self.request(COMMAND_PRIVATE, **headers), 'private', bool
		)
		

	def regions_table(self, **headers) -> list:

		self.request(COMMAND_REGIONS_TABLE, **headers)

		return self.recv_json()
	

	def regions_data(self, file_table: list, **headers):

		self.request(COMMAND_REGIONS_DATA, **headers)
		self.send_json(file_table)

		for chunk in self.recv_files(file_table):
			yield chunk


class ServerSocket(Socket):


	def __init__(self, address):

		super().__init__()

		self.bind(address)
	

	def listen(self, backlog=5):

		return super().listen(backlog)


	def accept(self):

		connection, address = super().accept()

		connection = Socket(connection)
		connection.set_headers(**self.headers)

		return connection, address


class NetworkException(Exception):
	

	def __init__(self, message, *args):
		
		super().__init__(message, *args)

		self.message = message
	

	def __str__(self):
		
		return self.message


if __name__ == "__main__":

	import threading as th

	address = ("127.0.0.1", 8080)

	def test_serve():
		s = ServerSocket(address)
		s.listen()
		while True:
			c, _ = s.accept()
			_, command, headers = c.recv_message()
			print("MESSAGE RECEIVED")
			c.respond(command, **headers)

	th.Thread(target=test_serve).start()

	while True:

		s = ClientSocket(address)

		print(s.ping(test='sadgfasdfasdf'))
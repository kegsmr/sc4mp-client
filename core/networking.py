import errno
import socket
import json
import struct
import hashlib
from datetime import datetime
from typing import Optional, Any, Type
from threading import Thread


SC4MP_BUFFER_SIZE = 4096

MESSAGE_PROTOCOL = 'SC4MP'

MESSAGE_TYPE_REQUEST = 'Req'
MESSAGE_TYPE_RESPONSE = 'Res'

COMMAND_ADD_SERVER = 'AddSrv'
COMMAND_CHECK_PASSWORD = 'ChkPwd'
COMMAND_INFO = 'Info'
COMMAND_PASSWORD_ENABLED = 'PwdEnb'
COMMAND_PING = 'Ping'
COMMAND_PLUGINS_TABLE = 'PlgTbl'
COMMAND_PLUGINS_DATA = 'PlgDat'
COMMAND_PRIVATE = 'Prv'
COMMAND_REGIONS_TABLE = 'RgnTbl'
COMMAND_REGIONS_DATA = 'RgnDat'
COMMAND_SAVE = 'Save'
COMMAND_SERVER_LIST = 'SrvLst'
COMMAND_USER_ID = 'UserId'
COMMAND_TOKEN = 'Token'
COMMAND_TIME = 'Time'
COMMAND_LOADING_BACKGROUND = 'LdgBkg'


def send_json(s: socket.socket, data, length_encoding="I"):

	if data is None:
		data = {}

	data = json.dumps(data).encode()

	s.sendall(struct.pack(length_encoding, len(data)) + data)


def recv_json(s: socket.socket, length_encoding="I"):

	length_header_size = struct.calcsize(length_encoding)
	length_header = b""

	while len(length_header) < length_header_size:
		if d := s.recv(length_header_size - len(length_header)):
			length_header += d
		else:
			raise ConnectionClosedException()

	data_size = struct.unpack(length_encoding, length_header)[0]
	data_size_read = 0

	data = b""
	
	while data_size_read < data_size:

		buffer_size = min(SC4MP_BUFFER_SIZE, data_size - data_size_read)

		if d := s.recv(buffer_size):
			data += d
			data_size_read += len(d)
		else:
			raise ConnectionClosedException()

	if len(data) < 1:
		raise NetworkException('No data received.')
	
	return json.loads(data.decode())


def recv_exact(s: socket.socket, length: int) -> bytes:

	data = bytearray()
	remaining = length

	while remaining > 0:

		chunk = s.recv(remaining)

		if not chunk:
			raise ConnectionClosedException()
		
		data += chunk
		remaining -= len(chunk)

	return bytes(data)
	

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

	except NetworkException as e:
		raise e
	except Exception as e:
		raise NetworkException(e) from e


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

	except NetworkException:
		raise
	except Exception as e:
		raise NetworkException(e) from e

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
	
	if error := h.get('error'):
		raise NetworkException(error)

	return h


def respond(s, command, **headers):

	return send_message(s, False, command, headers)


def is_success(headers: dict):

	STATUS = 'status'
	SUCCESS = 'success'

	if STATUS not in headers:
		raise NetworkException(f"Response headers missing {STATUS!r}.")

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

		def _recv_file():

			filesize_read: int = 0
			checksummer = hashlib.md5()

			while filesize_read < filesize:

				filesize_remaining = filesize - filesize_read
				buffersize = min(filesize_remaining, SC4MP_BUFFER_SIZE)

				chunk = s.recv(buffersize)

				if not chunk:
					raise ConnectionClosedException()

				filesize_read += len(chunk)
				checksummer.update(chunk)

				yield chunk

			checksum_actual = checksummer.hexdigest()
			if checksum != checksum_actual:
				raise NetworkException(
					f"Checksum mismatch for {relpath!r}: "
					f"expected {checksum!r}, got {checksum_actual!r}."
				)

		yield checksum, filesize, relpath, _recv_file()


def interpret_socket_error(e: BaseException) -> str:
    """
    Inspect a socket-related exception and return a human-readable description
    of what went wrong. Useful for logging or rethrowing as a higher-level error.
    """

    if isinstance(e, socket.timeout):
        return "Operation timed out."

    if isinstance(e, ConnectionResetError):
        return "Connection reset by peer."

    if isinstance(e, ConnectionRefusedError):
        return "Connection refused by remote host."

    if isinstance(e, BrokenPipeError):
        return "Attempted to write to a closed socket (broken pipe)."

    if isinstance(e, OSError):
        err = e.errno

        # Use errno for detailed OS-specific cases
        if err == errno.ECONNRESET:
            return "Connection reset by peer."
        elif err == errno.ECONNREFUSED:
            return "Connection refused."
        elif err == errno.ECONNABORTED:
            return "Connection aborted."
        elif err == errno.ENETDOWN:
            return "Network is down."
        elif err == errno.ENETUNREACH:
            return "Network unreachable."
        elif err == errno.EHOSTDOWN:
            return "Host is down."
        elif err == errno.EHOSTUNREACH:
            return "Host unreachable."
        elif err == errno.ETIMEDOUT:
            return "Connection timed out."
        elif err == errno.EPIPE:
            return "Broken pipe."
        elif err == errno.EINVAL:
            return "Invalid argument to socket operation."
        elif err == errno.EBADF:
            return "Bad file descriptor (socket likely closed)."
        elif err == errno.EFAULT:
            return "Bad memory address in socket operation."
        elif err == errno.ENOBUFS:
            return "No buffer space available."
        elif err == errno.ENOMEM:
            return "Out of memory during socket operation."
        elif err == errno.EINTR:
            return "Socket operation interrupted."
        elif err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            return "Resource temporarily unavailable (non-blocking socket)."
        elif err == errno.ENOTCONN:
            return "Socket is not connected."
        elif err == errno.EISCONN:
            return "Socket is already connected."
        elif err == errno.EADDRINUSE:
            return "Address already in use."
        elif err == errno.EADDRNOTAVAIL:
            return "Cannot assign requested address."
        elif err == errno.EAFNOSUPPORT:
            return "Address family not supported."
        elif err == errno.EPROTONOSUPPORT:
            return "Protocol not supported."
        elif err == errno.ENETRESET:
            return "Network dropped connection because of reset."
        elif err == errno.EIO:
            return "I/O error on socket."
        elif err == errno.EPERM:
            return "Operation not permitted."
        elif err == errno.EACCES:
            return "Permission denied on socket operation."

        # Unrecognized errno — show details
        return f"Unrecognized socket error: [Errno {err}] {e.strerror or e}"

    # Fallback for unexpected types
    return f"Unknown error: {e.__class__.__name__!r}: {e}"


class Socket(socket.socket):


	def __init__(self, s:Optional[socket.socket]=None):

		self.headers = {}

		if s:

			super().__init__(s.family, s.type, s.proto, socket.dup(s.fileno()))
			self.settimeout(s.gettimeout())

		else:

			super().__init__()


	def set_headers(self, **headers):

		self.headers.update(headers)


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


	def recv_exact(self, length: int) -> bytes:
		
		return recv_exact(self, length)


class ClientSocket(Socket):

	
	def __init__(self, address=None, timeout=10, **options):

		super().__init__(**options)

		self.settimeout(timeout)

		try:
			if address:
				self.connect(address)
		except Exception as e:
			raise NetworkException(e) from e


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
	

	def file_table(self, target, **headers):

		if target == 'plugins':
			return self.plugins_table(**headers)
		elif target == 'regions':
			return self.regions_table(**headers)
		else:
			raise ValueError(f"Invalid target: {target!r}")


	def file_table_data(self, target, file_table, **headers):

		if target == 'plugins':
			return self.plugins_data(file_table, **headers)
		elif target == 'regions':
			return self.regions_data(file_table, **headers)
		else:
			raise ValueError(f"Invalid target: {target!r}")


	def plugins_table(self, **headers) -> list:

		self.request(COMMAND_PLUGINS_TABLE, **headers)

		return self.recv_json()
	
	
	def plugins_data(self, file_table: list, **headers):

		if not file_table:
			return []

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

		if not file_table:
			return []

		self.request(COMMAND_REGIONS_DATA, **headers)
		self.send_json(file_table)

		for chunk in self.recv_files(file_table):
			yield chunk

	
	def user_id(self, hash, **headers):

		response = self.request(COMMAND_USER_ID, hash=hash, **headers)

		if error := response.get('error'):
			raise NetworkException(f"Authentication failed.\n\n{error}")

		return response.get('user_id')


	def token(self, user_id, **headers):
		
		response = self.request(
			COMMAND_TOKEN, user_id=user_id, **headers
		)

		if error := response.get('error'):
			raise NetworkException(f"Authentication failed.\n\n{error}")

		return response.get('token')
	
	
	def time(self, **headers):

		response = self.request(
			COMMAND_TIME, **headers
		)

		time = pluck_header(response, 'time', str)

		return datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
	
	
	def server_list(self, **headers):

		self.request(
			command=COMMAND_SERVER_LIST, **headers
		)

		server_list = self.recv_json()

		return server_list
	

	def loading_background(self, **headers):

		response = self.request(
			command=COMMAND_LOADING_BACKGROUND, **headers
		)

		size = pluck_header(response, 'size', int)

		return self.recv_exact(size)


class ServerSocket(Socket):


	def __init__(self, address=None):

		super().__init__()

		if address is not None:
			self.bind(address)
	

	def listen(self, backlog=5):

		return super().listen(backlog)


	def accept(self):

		connection, address = super().accept()

		connection = Socket(connection)
		connection.set_headers(**self.headers)

		return connection, address


class BaseRequestHandler(Thread):


	def __init__(self, c: Socket, private=False):

		super().__init__()

		self.c = c

		self.command = None
		self.headers = {}

		self.commands = {
			COMMAND_ADD_SERVER: self.add_server,
			COMMAND_CHECK_PASSWORD: self.check_password,
			COMMAND_INFO: self.info,
			COMMAND_PASSWORD_ENABLED: self.password_enabled,
			COMMAND_PING: self.ping,
			COMMAND_PLUGINS_TABLE: self.plugins_table,
			COMMAND_PLUGINS_DATA: self.plugins_data,
			COMMAND_PRIVATE: self.private,
			COMMAND_REGIONS_TABLE: self.regions_table,
			COMMAND_REGIONS_DATA: self.regions_data,
			COMMAND_SAVE: self.save,
			COMMAND_SERVER_LIST: self.server_list,
			COMMAND_USER_ID: self.send_user_id,
			COMMAND_TOKEN: self.send_token,
			COMMAND_TIME: self.time,
			COMMAND_LOADING_BACKGROUND: self.loading_background
		}

		self.require_auth = [
			COMMAND_SAVE,
			COMMAND_TOKEN
		]

		if private:
			self.require_auth += [
				COMMAND_PLUGINS_DATA,
				COMMAND_PLUGINS_TABLE,
				COMMAND_REGIONS_DATA,
				COMMAND_REGIONS_TABLE
			]


	def authenticate(self): ...

	def add_server(self): self.respond()
	def check_password(self): self.respond()
	def info(self): self.respond()
	def password_enabled(self): self.respond()
	def plugins_table(self): self.respond()
	def plugins_data(self): self.respond()
	def private(self): self.respond()
	def regions_table(self): self.respond()
	def regions_data(self): self.respond()
	def save(self): self.respond()
	def server_list(self): self.respond()
	def send_user_id(self): self.respond()
	def send_token(self): self.respond()
	def time(self): self.respond()
	def loading_background(self): self.respond()


	def get_header(self, key: str, type: Type):
		return pluck_header(self.headers, key, type)


	def recv_request(self):

		is_request, command, headers = self.c.recv_message()

		if command not in self.commands:
			raise NetworkException(f"Invalid request: {command!r}")

		if not is_request:
			raise NetworkException("Expected request but got response.")

		self.command = command
		self.headers = headers

		return command, headers


	def handle_request(self):

		if self.command is None:
			self.recv_request()
		
		if self.command in self.require_auth:
			self.authenticate()

		return self.commands[self.command]()


	def respond(self, **headers):

		return self.c.respond(self.command, **headers)


	def ping(self):

		return self.respond()


class NetworkException(Exception):
	

	def __init__(self, e, *args):
		
		if isinstance(e, str):
			message = e
		else:
			message = interpret_socket_error(e)

		super().__init__(message, *args)

		self.message = message
	

	def __str__(self):
		
		return self.message


class ConnectionClosedException(NetworkException):

	def __init__(self):

		super().__init__("Connection closed.")


if __name__ == "__main__":

	# address = ("127.0.0.1", 8080)

	# def test_serve():
	# 	s = ServerSocket(address)
	# 	s.set_headers(test=456)
	# 	s.listen()
	# 	while True:
	# 		c, _ = s.accept()
	# 		c.settimeout(10)
	# 		rh = BaseRequestHandler(c)
	# 		rh.handle_request()
	# 		c.close()

	# Thread(target=test_serve).start()

	# while True:

	# 	s = ClientSocket(address, timeout=10)
	# 	s.set_headers(test=123)
	# 	s.ping()

	s = ClientSocket(('localhost', 7249))

	s.ping(test=123)

import socket
import json
import struct
import time


SC4MP_BUFFER_SIZE = 4096


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

			time.sleep(.1)

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
			
			time.sleep(.1)

	if len(data) < 1:
		return None
	else:
		return json.loads(data.decode())


def recv_exact(s: socket.socket, length):

	data = b""

	while len(data) < length:
		data += s.recv(length - len(data))

	return data
	

def send_message(s: socket.socket, is_request=True, command="Ping", headers=None):

	if headers is None:
		headers = {}

	m = "SC4MP"
	if is_request:
		m += "Req"
	else:
		m += "Res"
	m += command

	message = m.encode('ascii')

	while len(message) < 14:
		message += b"\x00"

	h = json.dumps(headers).encode()
	l = struct.pack("H", len(h))

	message += l + h

	s.send(message)


def recv_message(s: socket.socket):

	p = recv_exact(s, 5).decode('ascii')
	if p != "SC4MP": return

	t = recv_exact(s, 3).decode('ascii')
	if t == "Req":
		is_request = True
	elif t == "Res":
		is_request = False
	else: return

	c = recv_exact(s, 6)
	command = c.rstrip(b"\x00").decode('ascii')

	l = struct.unpack("H", recv_exact(s, 2))[0]
	headers = json.loads(recv_exact(s, l).decode())

	return is_request, command, headers
	

def request(s, command, **kwargs):

	send_message(s, True, command, kwargs)
	
	is_request, c, h = recv_message(s)

	if is_request is False and c == command:
		return h


def respond(s, command, **kwargs):

	return send_message(s, False, command, kwargs)


class Socket(socket.socket):


	def __init__(self, s:socket.socket=None):

		self.headers = {}

		if s:

			# Instead of creating a new socket, we "adopt" an existing one.
			super().__init__(s.family, s.type, s.proto)
			self.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.settimeout(s.gettimeout())

			# Duplicate the underlying file descriptor
			self._sock = s
			self._dup_sock()

		else:

			super().__init__()


	def set_headers(self, **kwargs):

		self.headers = kwargs


	def _dup_sock(self):
		"""Duplicate the socket's file descriptor so this object manages it properly."""

		# self.detach()
		self.fileno = self._sock.fileno
		self.recv = self._sock.recv
		self.send = self._sock.send
		self.close = self._sock.close
		self.settimeout = self._sock.settimeout
		self.gettimeout = self._sock.gettimeout


	def send_json(self, data, length_encoding="I"):

		send_json(self, data, length_encoding)


	def recv_json(self, length_encoding="I"):

		return recv_json(self, length_encoding)


	def send_message(self, is_request=True, command="Ping", headers=None):

		send_message(self, is_request, command, headers)


	def recv_message(self):

		return recv_message(self)


	def request(self, command, headers=None):

		return request(self, command, headers)


	def respond(self, command, headers=None):

		return respond(self, command, headers)


class ClientSocket(Socket):

	
	def __init__(self, address, timeout=10, **kwargs):

		super().__init__(**kwargs)

		self.settimeout(timeout)

		self.connect(address)
	

	def add_server(self, port, **kwargs):

		return self.request("AddSrv", port=port, **kwargs)["status"] == "success"


	def check_password(self, password, **kwargs):

		return self.request("ChkPwd", password=password, **kwargs)["status"] == "success"


	def info(self, **kwargs):

		return self.request("Info", **kwargs)


	def password_enabled(self, **kwargs):

		return self.request("PwdEnb", **kwargs)["password_enabled"]


	def ping(self, **kwargs):

		return self.request("Ping", **kwargs)
	

	def plugins_table(self, **kwargs):

		self.request("PlgTab", **kwargs)

		return self.recv_json()
	
	
	def plugins_data(self, **kwargs):

		return int(self.request("PlgDat", **kwargs)["size"])
	

	def private(self, **kwargs):

		return self.request("PwdEnb", **kwargs)["private"]
		

	def regions_table(self, **kwargs):

		self.request("RgnTab", **kwargs)

		return self.recv_json()
	

	def regions_data(self, **kwargs):

		return int(self.request("RgnDat", **kwargs)["size"])


class ServerSocket(Socket):


	def __init__(self, address):

		super().__init__()

		self.bind(address)
	

	def listen(self, backlog=5):

		return super().listen(backlog)


	def accept(self):

		connection, address = super().accept()

		connection = Socket(connection)
		connection.set_headers(self.headers)

		return connection, address


class NetworkException(Exception):
	

	def __init__(self, message, *args):
		
		super().__init__(args)

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
			c.respond(command, headers)

	th.Thread(target=test_serve).start()

	while True:

		s = ClientSocket(address)

		print(s.ping({
			"test":"asdfsaddfsadfasdfhyuboqewrfvopiueqwrvneqpifvuhneqriujgbnqeariufveqnwhrgviuqenbrfvqeioujprvfnqeriujpvnqerpiufvnqerfvipunqerfvgujeqrfbnqeuirgvhnbqeiu"
		}))
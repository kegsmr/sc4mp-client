import socket
import json
import struct
import time


SC4MP_BUFFER_SIZE = 4096


def send_json(s, data, length_encoding="I"):

	if data is None:
		data = b"" 
	else:
		data = json.dumps(data).encode()

	s.sendall(struct.pack(length_encoding, len(data)) + data)


def recv_json(s, length_encoding="I"):

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
	

class Socket(socket.socket):


	def send_json(self, data, **kwargs):
		
		return send_json(self, data, **kwargs)
	
	
	def recv_json(self, **kwargs):

		return recv_json(self, **kwargs)
	

	def recv_exact(self, length):

		data = b""

		while len(data) < length:
			data += self.recv(length - len(data))

		return data
	

	def send_message(self, is_request=True, command="Ping", headers=None):

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

		print(message) #TODO remove

		self.send(message)


	def recv_message(self):

		print("RECEIVING MESSAGE") #TODO

		p = self.recv_exact(5).decode('ascii')
		if p != "SC4MP": return

		print("PROTOCOL CHECKED")

		t = self.recv_exact(3).decode('ascii')
		if t == "Req":
			is_request = True
		elif t == "Res":
			is_request = False
		else: return

		c = self.recv_exact(6)
		command = c.rstrip(b"\x00").decode('ascii')

		l = struct.unpack("H", self.recv_exact(2))[0]
		headers = json.loads(self.recv_exact(l).decode())

		return is_request, command, headers
		

	def request(self, command, headers=None):

		self.send_message(True, command, headers)
		
		is_request, c, h = self.recv_message()

		if is_request is False and c == command:
			return h


class ClientSocket(Socket):

	
	def __init__(self, address, timeout=10, **kwargs):

		super().__init__(**kwargs)

		self.settimeout(timeout)

		self.connect(address)

	
	def ping(self, headers=None):

		return self.request("Ping", headers)


class ServerSocket(Socket):


	def __init__(self, address):

		super().__init__()

		self.bind(address)
	
	def listen(self, backlog=5):
		return super().listen(backlog)

	def accept(self):
		conn, addr = super().accept()
		return Socket(_sock=conn), addr

	def respond(self, command, headers=None):
		return self.send_message(False, command, headers)


if __name__ == "__main__":

	import threading as th

	address = ("127.0.0.1", 7239)

	def test_serve():
		s = ServerSocket(address)
		s.listen()
		while True:
			c, _ = s.accept()
			_, command, headers = c.recv_message()
			print("MESSAGE RECEIVED")
			c.respond(command, headers)

	th.Thread(target=test_serve).start()

	time.sleep(5)

	s = ClientSocket(address)

	print(s.ping({
		"test":"test"
	}))
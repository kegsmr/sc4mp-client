import socket
import json
import struct
import time


SC4MP_BUFFER_SIZE = 4096


def send_json(s, data, length_encoding="I"):

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

	return json.loads(data.decode())
import io
import struct


class DBPF:
	"""TODO include credits to original php file"""


	def __init__(self, filename, offset=0, error_callback=None, require_identifier=True):
		"""TODO"""

		print(f'Parsing "{filename}"...')

		self.filename = filename
		self.offset = offset
		self.show_error = error_callback
		self.require_identifier = require_identifier

		self.NONSENSE_BYTE_OFFSET = 9

		# Open file to read bytes
		self.file = open(self.filename, 'rb')

		# Advance to offset
		if self.offset > 0:
			self.file.seek(self.offset)

		# Read the identifier
		self.identifier = self.file.read(4).decode()		# Always "DBPF"
		if self.require_identifier and self.identifier != "DBPF":
			raise Exception()

		# Read the header
		self.majorVersion = self.read_UL4()					# Always 1
		self.minorVersion = self.read_UL4()					# Always 0
		self.reserved = self.file.read(12)
		self.dateCreated = self.read_UL4()
		self.dateModified = self.read_UL4()
		self.indexMajorVersion = self.read_UL4()
		self.indexCount = self.read_UL4()
		self.indexOffset = self.read_UL4()
		self.indexSize = self.read_UL4()
		self.holesCount = self.read_UL4()
		self.holesOffset = self.read_UL4()
		self.holesSize = self.read_UL4()
		self.indexMinorVersion = self.read_UL4() - 1
		self.reserved2 = self.file.read(32)
		self.header_end = self.file.tell()

		# Seek to index table
		self.file.seek(offset + self.indexOffset)

		# Read index table
		self.indexData = []
		for index in range(0, self.indexCount):
			self.indexData.append({})
			self.indexData[index]['typeID'] = self.read_ID()
			self.indexData[index]['groupID'] = self.read_ID()
			self.indexData[index]['instanceID'] = self.read_ID()
			if (self.indexMajorVersion == 7) and (self.indexMinorVersion == 1):
				self.indexData[index]['instanceID2'] = self.read_ID()
			self.indexData[index]['offset'] = self.read_UL4()
			self.indexData[index]['filesize'] = self.read_UL4()
			#self.indexData[index]['compressed'] = #TODO
			#self.indexData[index]['truesize'] = #TODO

	
	def close(self):

		self.file.close()


	def decompress(self, length):

		buf = ""			# TODO what does this do?
		answer = bytes()	# TODO what does this do?
		answerlen = 0		# TODO what does this do?
		numplain = ""		# TODO what does this do?
		numcopy = ""		# TODO what does this do?
		offset = ""			# TODO what does this do?

		# Read until there's nothing left to read
		while length > 0:
			
			# Read control char
			try:
				cc = self.read_UL1(self.file) # This line causes errors sometimes for some reason. End of file?
				length -= 1
			except Exception as e:
				self.show_error(e)
				return io.BytesIO(answer) # Just return what we've got so far. 

			# For development
			#print(f"Control char is {cc}, length remaining is {length}.")

			if cc >= 252:	#0xFC

				numplain = cc & 3										#3 = 0x03
				numplain = length if numplain > length else numplain
				
				numcopy = 0
				offset = 0

			elif cc >= 224:	#0xE0

				numplain = (cc - 223) << 2								#223 = 0xdf

				numcopy = 0
				offset = 0

			elif cc >= 192:	#0xC0

				length -= 3

				byte1 = self.read_UL1(self.file)
				byte2 = self.read_UL1(self.file)
				byte3 = self.read_UL1(self.file)

				numplain = cc & 3										#3 = 0x03
				
				numcopy = ((cc & 12) << 6) + 5 + byte3 					#12 = 0x0c
				offset = ((cc & 16) << 12) + (byte1 << 8) + byte2 		#16 = 0x10

			elif cc >= 128: #0x80

				length -= 2

				byte1 = self.read_UL1(self.file)
				byte2 = self.read_UL1(self.file)

				numplain = (byte1 & 192) >> 6 							#192 = 0xc0

				numcopy = (cc & 63) + 4 								#63 = 0x3f
				offset = ((byte1 & 63) << 8) + byte2 					#63 = 0x3f

			else:

				length -= 1

				byte1 = self.read_UL1(self.file)

				numplain = cc & 3 										#3 = 0x03

				numcopy = ((cc & 28) >> 2) + 3 							#28 = 0x1c
				offset = ((cc & 96) << 3) + byte1 						#96 = 0x60

			length -= numplain

			# This section basically copies the parts of the string to the end of the buffer:
			if numplain > 0:

				buf = self.file.read(numplain)

				answer += buf

			fromoffset = len(answer) - (offset + 1)  # 0 == last char
			for index in range(numcopy):

				#print(str(answer))
				#print(str(cc))
				#print(str(offset))
				#print(str(fromoffset))
				
				#TODO remove try and except block. decompression algorithm breaks with a control char of 206. the offset becomes larger than the length of the answer, causing a negative fromindex and an indexing error. for now it does not seem to affect city coordinates
				try:
					answer = answer + (answer[fromoffset + index]).to_bytes(1, 'little') #substr(fromoffset + index, 1)
				except Exception as e:
					#show_error(e) #TODO
					return io.BytesIO(answer)
				
			answerlen += numplain
			answerlen += numcopy

		return io.BytesIO(answer)


	def read_UL1(self, file=None):
		"""TODO"""
		if file is None:
			file = self.file
		return struct.unpack('<B', file.read(1))[0]


	def read_UL2(self, file=None):
		"""TODO"""
		if file is None:
			file = self.file
		return struct.unpack('<H', file.read(2))[0]
	
	
	def read_UL4(self, file=None):
		"""TODO"""
		if file is None:
			file = self.file
		return struct.unpack('<L', file.read(4))[0]


	def read_unistr(self, file=None, length=None):
		if file is None:
			file = self.file
		if length is None:
			length = struct.unpack("<L", file.read(4))[0]
		return file.read(length).decode()


	def read_nullstring(self, file=None):
		if file is None:
			file = self.file
		text = ""
		while True:
			byte = file.read(1)
			if byte == b"\x00":
				return text
			else:
				text += byte.decode()


	def read_ID(self, file=None):
		"""TODO"""
		if file is None:
			file = self.file
		return file.read(4)[::-1].hex()


	def get_indexData_entry_by_type_ID(self, type_id):
		"""TODO"""
		for entry in self.indexData:
			if entry['typeID'] == type_id:
				return entry


	def goto_subfile(self, type_id):
		"""TODO"""
		entry = self.get_indexData_entry_by_type_ID(type_id)
		self.file.seek(entry['offset'])
		#print(entry['offset'] + 9)


	def get_subfile_size(self, type_id):
		"""TODO"""
		entry = self.get_indexData_entry_by_type_ID(type_id)
		return entry['filesize']


	def get_subfile_header(self, type_id):
		"""TODO"""
		#self.goto_subfile(type_id)
		#return (self.read_UL4(), self.read_ID(), ) #TODO how to read these values?
		pass


	def decompress_subfile(self, type_id):
		"""TODO"""
		#report('Decompressing "' + type_id + '"...', self)
		self.goto_subfile(type_id)
		self.file.read(self.NONSENSE_BYTE_OFFSET)
		return self.decompress(self.get_subfile_size(type_id))


class SC4Config(DBPF):


	def __init__(self, *args, **kwargs):

		super().__init__(*args, **kwargs)

	
	def get_simcity_4_cfg(self):

		data = self.decompress_subfile("a9dd6e06")

		self.simcity_4_cfg = {}

		data.seek(110)														# 0x06E
		self.simcity_4_cfg["LastCityName"] = self.read_nullstring(data)

		data.seek(622)														# 0x26E
		self.simcity_4_cfg["LastMayorName"] = self.read_nullstring(data)

		data.seek(3774)														# 0xEBE
		self.simcity_4_cfg["LastRegionName"] = self.read_nullstring(data)

		return self.simcity_4_cfg


class SC4Savegame(DBPF):


	def __init__(self, *args, **kwargs):

		super().__init__(*args, **kwargs)

	
	def get_SC4ReadRegionalCity(self):

		print(f'Parsing region view subfile of "{self.filename}"...')

		# Decompress the subfile and get the data as a bytes stream
		data = self.decompress_subfile("ca027edb")

		# Dictionary to return
		self.SC4ReadRegionalCity = {}

		# DBPF file version
		self.SC4ReadRegionalCity['majorVersion'] = self.read_UL2(data)
		self.SC4ReadRegionalCity['minorVersion'] = self.read_UL2(data)
		
		# City location
		self.SC4ReadRegionalCity['tileXLocation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['tileYLocation'] = self.read_UL4(data)
		
		# City size
		self.SC4ReadRegionalCity['citySizeX'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['citySizeY'] = self.read_UL4(data)
		
		# City population 
		self.SC4ReadRegionalCity['residentialPopulation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['commercialPopulation'] = self.read_UL4(data)
		self.SC4ReadRegionalCity['industrialPopulation'] = self.read_UL4(data)

		# Unknown
		data.read(4) #self.SC4ReadRegionalCity['unknown1'] = data.read(4) #TODO read float

		# Mayor rating, difficulty and tutorial mode flag
		self.SC4ReadRegionalCity['mayorRating'] = self.read_UL1(data)
		self.SC4ReadRegionalCity['starCount'] = self.read_UL1(data)
		self.SC4ReadRegionalCity['tutorialFlag'] = self.read_UL1(data)

		# Not sure what this is for
		self.SC4ReadRegionalCity['cityGUID'] = self.read_UL4(data)

		# Unknown
		data.read(20)
		#self.SC4ReadRegionalCity['unknown5'] = self.read_UL4(data)
		#self.SC4ReadRegionalCity['unknown6'] = self.read_UL4(data)
		#self.SC4ReadRegionalCity['unknown7'] = self.read_UL4(data)
		#self.SC4ReadRegionalCity['unknown8'] = self.read_UL4(data)
		#self.SC4ReadRegionalCity['unknown9'] = self.read_UL4(data)

		# Gamemode
		self.SC4ReadRegionalCity['modeFlag'] = self.read_UL1(data)

		# City name
		self.SC4ReadRegionalCity['cityName'] = self.read_unistr(data)

		# Former city name
		self.SC4ReadRegionalCity['formerCityName'] = self.read_unistr(data)

		# Mayor name
		self.SC4ReadRegionalCity['mayorName'] = self.read_unistr(data)

		#TODO keep reading subfile

		return self.SC4ReadRegionalCity


if __name__ == "__main__":

	import sys

	def error(e):
		print(f"{e}")

	filename = sys.argv[1]

	if filename.endswith(".sc4"):

		savegame = SC4Savegame(filename, 0, error)

		print(savegame.indexData)

		print(savegame.indexOffset)

		with open("SC4ReadRegionalCity.sc4", "wb") as file:
			file.write(savegame.decompress_subfile("ca027edb").read())

		print(savegame.get_SC4ReadRegionalCity())

	elif filename.endswith(".cfg"):

		cfg = SC4Config(filename, 0, error)

		print(cfg.get_simcity_4_cfg())

		#print(f"{dbpf.majorVersion}.{dbpf.minorVersion}")

		#for entry in dbpf.indexData:
		#	with open(f"{entry['typeID']}.cfg", "wb") as file:
		#		file.write(dbpf.decompress_subfile(entry["typeID"]).read())
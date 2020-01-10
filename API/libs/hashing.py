import hashlib, binascii, os

class Hasher():
	"""
	La presente clase Hashea cadenas de forma predeterminada en SHA a 512 bits
	"""
	def __init__(self, algorithm):
		self.__algorithm = algorithm

	def hashString(self, stringToEncrypt):
		"""Hash a password for storing."""
		salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
		stringHashed = hashlib.pbkdf2_hmac(self.__algorithm, stringToEncrypt.encode('utf-8'),
									salt, 100000)
		stringHashed = binascii.hexlify(stringHashed)
		return (salt + stringHashed).decode('ascii')

	def matchString(self, stored_string, provided_string):
		"""Verify a stored password against one provided by user"""
		salt = stored_string[:64]
		stored_string = stored_string[64:]
		pwdhash = hashlib.pbkdf2_hmac(self.__algorithm,
									  provided_string.encode('utf-8'),
									  salt.encode('ascii'),
									  100000)
		pwdhash = binascii.hexlify(pwdhash).decode('ascii')
		return pwdhash == stored_string
import os
import base64
import binascii
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

load_dotenv()
get = os.getenv

MASTER_KEK = get("MASTER_AES_KEY")
kek = binascii.unhexlify(MASTER_KEK)
aesgcm_master = AESGCM(kek)


def encrypt_dek(dek):
	nonce = os.urandom(12)
	ciphertext = aesgcm_master.encrypt(nonce, dek, None)
	return base64.b64encode(nonce + ciphertext).decode()


def generate_key():
	key_bytes = os.urandom(32)
	p = encrypt_dek(key_bytes)
	return p


def decrypt_dek(encrypted_b64):
	decoded = base64.b64decode(encrypted_b64)
	nonce = decoded[:12]
	ciphertext = decoded[12:]
	return aesgcm_master.decrypt(nonce, ciphertext, None)


def encrypt_text(plaintext: str, dek: bytes) -> str:
	if len(dek) != 32:
		raise ValueError("DEK must be 32 bytes")
	aesgcm = AESGCM(dek)
	nonce = os.urandom(12)
	ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
	return base64.b64encode(nonce + ciphertext).decode()


def decrypt_text(encrypted_b64: str, dek: bytes) -> str:
	decoded = base64.b64decode(encrypted_b64)
	nonce = decoded[:12]
	ciphertext = decoded[12:]

	aesgcm = AESGCM(dek)
	plaintext = aesgcm.decrypt(nonce, ciphertext, None)
	return plaintext.decode()


def encrypt_dek_with_rsa(dek: bytes, public_key_pem: str) -> str:
	pem = public_key_pem.strip()

	try:
		public_key = serialization.load_pem_public_key(pem.encode("utf-8"))
	except ValueError:
		if pem.startswith("-----BEGIN RSA PUBLIC KEY-----"):
			body = pem.replace("-----BEGIN RSA PUBLIC KEY-----", "") \
				.replace("-----END RSA PUBLIC KEY-----", "") \
				.strip()
			der_bytes = base64.b64decode(body)
			public_key = serialization.load_der_public_key(der_bytes)
		else:
			raise

	encrypted_dek = public_key.encrypt(
		dek,
		padding.PKCS1v15()
	)

	return base64.b64encode(encrypted_dek).decode("utf-8")


def decrypt_dek_with_rsa(encrypted_dek_b64: str, private_key_pem: str) -> bytes:
	encrypted_dek = base64.b64decode(encrypted_dek_b64)

	private_key = serialization.load_pem_private_key(
		private_key_pem.encode(),
		password=None
	)

	decrypted_dek = private_key.decrypt(
		encrypted_dek,
		padding.PKCS1v15()
	)

	return decrypted_dek


def encrypt_file(input_path: str, output_path: str, dek: bytes):

	with open(input_path, "rb") as f:
		data = f.read()

	nonce = os.urandom(12)
	aesgcm = AESGCM(dek)
	ciphertext = aesgcm.encrypt(nonce, data, None)

	with open(output_path, "wb") as f:
		f.write(nonce + ciphertext)


def decrypt_file(input_path: str, output_path: str, dek: bytes):

	with open(input_path, "rb") as f:
		blob = f.read()

	nonce = blob[:12]
	ciphertext = blob[12:]

	aesgcm = AESGCM(dek)
	plaintext = aesgcm.decrypt(nonce, ciphertext, None)

	with open(output_path, "wb") as f:
		f.write(plaintext)

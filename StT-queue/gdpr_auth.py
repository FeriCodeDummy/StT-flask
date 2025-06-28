from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decrypt_file(input_path: str, output_path: str, dek: bytes):

	with open(input_path, "rb") as f:
		blob = f.read()

	nonce = blob[:12]
	ciphertext = blob[12:]

	aesgcm = AESGCM(dek)
	plaintext = aesgcm.decrypt(nonce, ciphertext, None)

	with open(output_path, "wb") as f:
		f.write(plaintext)

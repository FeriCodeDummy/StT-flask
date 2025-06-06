import os
import base64
import binascii
from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
load_dotenv() 
get = os.getenv

MASTER_KEK = get("MASTER_AES_KEY")
kek = binascii.unhexlify(MASTER_KEK) 
aesgcm = AESGCM(kek)

def encrypt_dek(dek):
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, dek, None)
    return base64.b64encode(nonce + ciphertext).decode()

def generate_key():
    key_bytes = os.urandom(32)
    p = encrypt_dek(key_bytes)
    return p

def decrypt_dek(encrypted_b64):
    decoded = base64.b64decode(encrypted_b64)
    nonce = decoded[:12]
    ciphertext = decoded[12:]
    return aesgcm.decrypt(nonce, ciphertext, None)

def encrypt_text(plaintext: str, dek: bytes) -> str:
    if len(dek) != 32:
        raise ValueError("DEK must be 32 bytes")
    aesgcm = AESGCM(dek)
    nonce = os.urandom(12)
    print("Nonce: ")
    print(nonce.hex())
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    print("ciphertext: ")
    print(ciphertext.hex())
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_text(encrypted_b64: str, dek: bytes) -> str:
    decoded = base64.b64decode(encrypted_b64)
    # print(decoded.hex())
    nonce = decoded[:12]
    # print(nonce.hex())
    ciphertext = decoded[12:]
    # print(ciphertext.hex())
    tag = decoded[-16:]
    # print(tag.hex())
    
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

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


def encrypt_key_rsa(patient_key, doctor_key, public_key, text):
    dek = decrypt_dek(patient_key)
    plaintext = decrypt_text(text, dek)
    dek_d = decrypt_dek(doctor_key)    
    secure = encrypt_text(dek_d)
    encrypted_key = encrypt_dek_with_rsa(dek_d, public_key)
    return secure_







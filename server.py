from flask import Flask, request, jsonify, request, Response
import jwt
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import wave
import io
import json
import time
import mysql.connector
import os
from dbm import save_transcribed, fetch_anamnesis, save_anamnesis, fetch_pid, fetch_stat_doctors,fetch_stat_hospitals, fetch_anamnesis_reencrypted
from dotenv import load_dotenv, dotenv_values 
import whisper
import tempfile
from flask_cors import CORS, cross_origin
from medic import to_medical_format
from gdpr_auth import generate_key, encrypt_text, decrypt_text, encrypt_dek_with_rsa, decrypt_dek
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64, os
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import dsa, rsa
from openai import OpenAI
from utils import to_medical_format, concat_mp3_files
load_dotenv() 
get = os.getenv

SECRET_KEY = os.getenv("JWT_SECRET", "fallback-dev-secret")

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))
AES_KEY = get("MASTER_AES_KEY")
OPENAI_API_KEY = get("OPENAI_API_KEY")

def get_database():
    return mysql.connector.connect(
        host=HOST,
        user=USER,
        password=PSWD,
        database="mediphone",
        port=PORT
    )

print("[*] Connecting to MySQL database ...")
try:
	database = mysql.connector.connect(
		  host=HOST,
		  user=USER,
		  password=PSWD,
		  database="mediphone",
		  port=PORT
	)
	print("[+] Connection successful")
except Exception as e:
	print("[!] Failed to connect to the database. Quitting...")
	exit(-1)

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

@app.before_request
def handle_preflight():
	if request.method == "OPTIONS":
		res = Response()
		res.headers['X-Content-Type-Options'] = '*'
		return res

# @app.route("/test-rsa", methods=["POST"])
# def test_rsa():

# 	data = request.get_json()
# 	print(data)
	
# 	pub_key = data.get("public_key")
# 	text = "Yeeeeeeeeeet"
# 	key = os.urandom(32)
# 	enc_key = encrypt_dek_with_rsa(key, pub_key)
# 	text_encrypted = encrypt_text(text, key)

# 	print(enc_key)
# 	return jsonify({
# 		"encrypted_key": enc_key,
# 		"encrypted_text": text_encrypted
# 	}), 200



def decrypt_dek_with_rsa(encrypted_dek_b64: str, private_key_pem: str) -> bytes:
	encrypted_dek = base64.b64decode(encrypted_dek_b64)

	private_key = serialization.load_pem_private_key(
		private_key_pem.encode(),
		password=None  # or passphrase bytes if your private key is encrypted
	)

	decrypted_dek = private_key.decrypt(
		encrypted_dek,
		padding.PKCS1v15()
	)

	return decrypted_dek

@app.route('/fetch-anamnesis', methods=['POST'])
def fetch_anamnesis_request():
	data = request.get_json()
	public_key_pem = data['public_key']
	aes_key = os.urandom(32)
	encrypted_key = encrypt_dek_with_rsa(aes_key, public_key_pem)

	data = fetch_anamnesis_reencrypted(database, aes_key)

	return jsonify({
		'encrypted_key': encrypted_key,
		'anamnesis': data 
	}), 200

@app.route("/test-rsa-update", methods=["POST"])
def test_rsa_update():
	data = request.get_json()
	enc_key = data.get("encrypted_key")
	enc_text = data.get("encrypted_text")
	pid = data.get("patientid")

	# 1. Load your RSA private key from PEM 
		
	with open("private_key.pem", "rb") as f:
		# print(f.read().hex())
		private_key = serialization.load_pem_private_key(
			f.read(),
			password=None
		)
		
	# print(private_key)

	encrypted_key_bytes = base64.b64decode(enc_key)

	aes_key = private_key.decrypt(
		encrypted_key_bytes,
		padding.PKCS1v15()
	).decode()
	aes_key = base64.b64decode(aes_key)
	# print(aes_key.hex())
	# print(len(aes_key))
	# print(decrypt_text(enc_text, aes_key))

	return jsonify({"status": "Success."}), 200

@app.route('/anamnesis', methods=["GET"])
@cross_origin()
def get_anamnesis():
	res = fetch_anamnesis(database)
	return jsonify({"anamnesis": res}), 200

@app.route('/stats/doctors', methods=['GET'])
def get_stat_doctors():
    db = get_database()
    rows = fetch_stat_doctors(db)
    db.close()
    return jsonify([
        {
            "name": row[0],
            "surname": row[1],
            "email": row[2],
            "n_patients": row[3],
            "n_anamnesis": row[4]
        }
        for row in rows
    ]), 200

@app.route('/stats/hospitals', methods=['GET'])
def get_stat_hospitals():
	db = get_database()
	rows = fetch_stat_hospitals(db)
	db.close()
	return jsonify(rows), 200

@app.route('/verify-token', methods=['POST'])
def verify_token():
	start = time.time()
	print(f"[{time.time()}] /verify-token hit", flush=True)
	print("Received request!")
	data = request.get_json()
	token = data.get("idToken")

	if not token:
		return jsonify({"error": "Missing idToken"}), 400

	try:
		idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
		email = idinfo["email"]
		name = idinfo["name"]

		cursor = database.cursor(dictionary=True)

		cursor.execute("SELECT * FROM Doctor WHERE email = %s", (email,))
		doctor = cursor.fetchone()
		print(f"[LOGIN ATTEMPT] Email: {email}, Name: {name}")
		if doctor:
			role = "doctor"
		else:
			cursor.execute("SELECT * FROM Personel WHERE email = %s", (email,))
			personel = cursor.fetchone()

			if personel:
				role = "personel"
			else:
				return jsonify({"error": "User not registered as Doctor or Personel"}), 403


		payload = {
			"sub": idinfo["sub"],
			"email": idinfo["email"],
			"name": idinfo["name"],
			"role": role,
			"exp": datetime.utcnow() + timedelta(hours=2)
		}

		jwt_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
		print(f"/verify-token completed in {time.time() - start:.2f}s", flush=True)  # ✅ ADD HERE

		return jsonify({
			"message": "Token is valid",
			"jwt": jwt_token,
			"email": idinfo["email"],
			"name": idinfo["name"],
			"role": role
		}), 200

	except ValueError as e:
		print(f"[!] Token verification failed: {e}", flush=True)
		return jsonify({"error": "Invalid token", "details": str(e)}), 401

def debug(request):
    print("---- REQUEST START ----")
    print("Method:", request.method)
    print("Path:", request.path)
    print("Headers:\n", request.headers)
    print("Form Data:\n", request.form)
    print("Files:\n", request.files)
    print("Raw Body:\n", request.get_data())
    print("---- REQUEST END ----")

@app.route('/transcribe', methods=["POST"])
def transcribe_audio():
	# debug(request)

	if 'title' not in request.form:
		return jsonify({"error": "Mising anamnesis title"}), 400
	
	if 'id_' not in request.form:
		return jsonify({"error": "Missing patient key"}), 400

	# pid, did, hid, enc_key = fetch_pid(database, request.body["id_"])
	# if pid == -1:
	# 	return jsonify({"error": "Patient id is invalid"}), 400

	if 'audio_file' not in request.files:
		return jsonify({"error": "Missing 'audio_file'"}), 400
	uploaded_file = request.files['audio_file']

	with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
		uploaded_file.save(temp.name)
		temp_path = temp.name

	try:
		model = whisper.load_model('base')
		result = model.transcribe(temp_path, language='en')
		transcription = result['text']
		# TODO make a funciton validate_text to convert trasncription into proper anamnesis via gpt
		#text = to_medical_format(transcription, client)
		text = transcription
		# save_anamnesis(database, text, request.body["title"], pid, did, hid, enc_key)

	except Exception as e:
		print(e)
		return jsonify({"error": e}), 500
	finally:
		os.remove(temp_path)  

	return jsonify({"transription": transcription}), 200

def debug(request):
    print("---- REQUEST START ----")
    print("Method:", request.method)
    print("Path:", request.path)
    print("Headers:\n", request.headers)
    print("Form Data:\n", request.form)
    print("Files:\n", request.files)
    print("Raw Body:\n", request.get_data())
    print("---- REQUEST END ----")

@app.route("/test-multiple-recordings", methods=["POST"])
def test_combo():
	debug(request)	


	if 'audio_files' not in request.files:
		return jsonify({"error": "Missing 'audio_files'"}), 400
	
	filenames = []
	uploaded_files = request.files.getlist("audio_files")
	
	for uploaded_file in uploaded_files:
		with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
			uploaded_file.save(temp.name)
			filenames.append(temp.name)


	temp_path = concat_mp3_files(filenames, "final.mp3") 
	try:
		model = whisper.load_model('base')
		result = model.transcribe("final.mp3", language='en')
		transcription = result['text']
		#text = to_medical_format(transcription, client)
		#save_anamnesis(database, text, request.body["title"], pid, did, hid, enc_key)
		text=transcription
		return jsonify({"message": text, "status": "success"}), 200
	except Exception as e:
		return jsonify({"error": e}), 500
	finally:
		os.remove(temp_path)
		for file in filenames:
			os.remove(file)

if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

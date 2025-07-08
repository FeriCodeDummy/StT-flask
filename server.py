import base64
import os
import tempfile
from functools import wraps
import requests
import mysql.connector
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from openai import OpenAI
from binascii import hexlify
from dbm import fetch_doctor_patients, confirm_anamnesis, fetch_pid, fetch_anamnesis_reencrypted, update_anamnesis_data, \
	fetch_anamnesis_reencrypted_doctor
from gdpr_auth import encrypt_text, decrypt_text, encrypt_dek_with_rsa, decrypt_dek, encrypt_file, decrypt_dek_with_rsa, \
	decrypt_file
from utils import concat_wav_files

load_dotenv()
get = os.getenv

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))
AES_KEY = get("MASTER_AES_KEY")
OPENAI_API_KEY = get("OPENAI_API_KEY")

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


def log_access(action_type, target_table=None, target_id=None):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			user_email = getattr(request, 'user_email', 'anonymous')  # Customize this
			ip = request.remote_addr
			ua = request.headers.get('User-Agent')

			sql = "INSERT INTO AccessLog (user_email, action_type, target_table, target_id, ip_address, user_agent) VALUES (%s, %s, %s, %s, %s, %s)"
			cursor = database.cursor()
			cursor.execute(sql, (user_email, action_type, target_table, target_id, ip, ua))
			database.commit()
			return func(*args, **kwargs)

		return wrapper

	return decorator


@app.before_request
def handle_preflight():
	if request.method == "OPTIONS":
		res = Response()
		res.headers['X-Content-Type-Options'] = '*'
		return res


@app.route("/accept-anamnesis", methods=["POST"])
@log_access(action_type="UPDATE", target_table='Anamnesis')
def accept_anamnesis():
	# TODO Add verification?
	data = request.get_json()
	aid = data.get('anamnesis_id')
	confirm_anamnesis(database, aid)
	return jsonify({"message": "updated", "status": "success"}), 200


@app.route('/fetch-anamnesis', methods=['POST'])
@log_access(action_type="READ", target_table='Anamnesis')
def fetch_anamnesis_request():
	data = request.get_json()
	public_key_pem = data['public_key']
	doctor_email = data['doctor_email']
	aes_key = os.urandom(32)
	encrypted_key = encrypt_dek_with_rsa(aes_key, public_key_pem)

	data = fetch_anamnesis_reencrypted_doctor(database, aes_key, doctor_email)

	return jsonify({
		'encrypted_key': encrypted_key,
		'anamnesis': data
	}), 200

@app.route('/fetch-anamnesis-admin', methods=['POST'])
@log_access(action_type="READ", target_table='Anamnesis')
def fetch_anamnesis_request_admin():
	data = request.get_json()
	public_key_pem = data['public_key']
	aes_key = os.urandom(32)
	encrypted_key = encrypt_dek_with_rsa(aes_key, public_key_pem)

	data = fetch_anamnesis_reencrypted(database, aes_key, )

	return jsonify({
		'encrypted_key': encrypted_key,
		'anamnesis': data
	}), 200


@app.route("/update-anamnesis", methods=["POST"])
@log_access(action_type="UPDATE", target_table='Anamnesis')
def update_anamnesis_data_():
	data = request.get_json()
	enc_key = data.get("encrypted_key")
	enc_text = data.get("encrypted_text")
	enc_diagnosis = data.get("encrypted_diagnosis")
	mkb_10 = data.get("mkb10")
	aid = data.get("anamnesis_id")

	with open("private_key.pem", "rb") as f:
		private_key = serialization.load_pem_private_key(
			f.read(),
			password=None
		)

	encrypted_key_bytes = base64.b64decode(enc_key)

	aes_key = private_key.decrypt(
		encrypted_key_bytes,
		padding.PKCS1v15()
	).decode()

	aes_key = base64.b64decode(aes_key)

	updated_text = decrypt_text(enc_text, aes_key)
	updated_diagnosis = decrypt_text(enc_diagnosis, aes_key)
	key_ = decrypt_dek(enc_key)
	text = encrypt_text(updated_text, key_)
	diagnosis = encrypt_text(updated_diagnosis, key_)
	del key_

	update_anamnesis_data(database, text, diagnosis, mkb_10, aid)

	return jsonify({"status": "Success."}), 200


@app.route('/fetch-patients', methods=["POST"])
@log_access(action_type="READ", target_table='Patient')
def fetch_patients():
	data = request.get_json()
	try:
		did = data.get("doctor_email")
	except:
		return jsonify({"error": "Missing required field doctor_id"}), 400

	res = fetch_doctor_patients(database, did)
	patients = []

	for item in res:
		patients.append({
			"patient_id": item[2],
			"name": item[0],
			"surname": item[1],
			"medical_card_id": item[3],
			"birtday": item[4]
		})

	return jsonify({"patients": patients}), 200


@app.route("/save-transcribed-anamnesis", methods=["POST"])
@log_access(action_type="WRITE", target_table='Anamnesis')
def transcribed_anamnesis():
	data = request.get_json()
	pid = data.get("patient_id")
	did = data.get("doctor_id")
	title = data.get("title")

	#	return jsonify({"error": "Missing anamnesis transcription"}), 400
	print(request.form['transcription'])
	return jsonify({"message": request.form['transcription']}), 200


@app.route("/multiple-recordings", methods=["POST"])
@log_access(action_type="READ", target_table='Patient')
def multiple_recordings():

	if 'audio_files' not in request.files:
		print(request.files)
		return jsonify({"error": "Missing 'audio_files'"}), 400

	uploaded_files = request.files.getlist("audio_files")

	if len(uploaded_files) == 0:
		return jsonify({"error": "No audio files"}), 400

	data = request.get_json()
	if 'encrypted_key' not in data:
		return jsonify({"message": "Missing decryption key"}), 400
	key = data['encrypted_key']
	with open('_/private_key.pem', 'r') as pkey:
		private = pkey.read()
	dec_key = decrypt_dek_with_rsa(key, private)

	filenames = []
	try:
		for uploaded_file in uploaded_files:
			with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as temp:
				uploaded_file.save(temp.name)
				decrypt_file(temp.name, temp.name.replace('bin', 'wav'), dec_key)
				filenames.append(temp.name.replace('bin', 'wav'))

		temp_path = concat_wav_files(filenames, "final.wav")
		temp_key = os.urandom(32)
		temp_enc_path = "audio.bin"
		encrypt_file(temp_path, temp_enc_path, temp_key)
		key = hexlify(temp_key).decode('utf-8')
		data = {
			"decryption_key": key
		}
		try:
			with open(temp_enc_path, 'rb') as f:
				files = {
					"file": ("audio.bin", f, "application/octet-stream")
				}
				#response = requests.post('http://localhost:4000/upload', files=files, data=data)
				for f in filenames:
					os.remove(f)
#				return jsonify({"status": response.status_code, "message": response.text}), 200
				return jsonify({"status": 200, "message": "nothing crashed"}), 200

		except Exception as e:
			return jsonify({"Error": str(e)}), 500

	except Exception as e:
		return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

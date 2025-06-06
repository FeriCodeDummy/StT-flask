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
from dbm import fetch_doctor_patients, confirm_anamnesis, save_anamnesis, fetch_pid, fetch_stat_doctors,fetch_stat_hospitals, fetch_anamnesis_reencrypted, update_anamnesis_data
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
from functools import wraps # JWT Wrapper
from flask import request, jsonify
load_dotenv() 
get = os.getenv

SECRET_KEY = os.getenv("JWT_SECRET", "fallback-dev-secret")

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))
AES_KEY = get("MASTER_AES_KEY")
OPENAI_API_KEY = get("OPENAI_API_KEY")



def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return wrapper

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

@app.route("/accept-anamnesis", methods=["POST"])
@jwt_required
def accept_anamnesis():
	data = request.get_json()
	aid = data.get('anamnesis_id')
	confirm_anamnesis(database, aid)
	return jsonify({"message": "updated", "status": "success"}), 200

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

@app.route('/fetch-anamnesis', methods=['POST'])
@jwt_required
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
@jwt_required
def test_rsa_update():
	data = request.get_json()
	enc_key = data.get("encrypted_key")
	enc_text = data.get("encrypted_text")
	pid = data.get("patient_id")
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

	pid, did, hid, enc_key = fetch_pid(database, pid)
	if pid == -1:
		return jsonify({"error": "Patient id is invalid"}), 400

	key_ = decrypt_dek(enc_key)
	text = encrypt_text(updated_text, key_)
	del key_

	update_anamnesis_data(database, text, aid)

	return jsonify({"status": "Success."}), 200

@app.route('/stats/doctors', methods=['GET'])
@jwt_required
def get_stat_doctors():
    db = get_database()
    rows = fetch_stat_doctors(db)
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


@app.route('/fetch-patients', methods=["POST"])
@jwt_required
def fetch_patients():
    data = request.get_json()
    try:
        did = data.get("doctor_email")
    except:
        return jsonify({"error": "Missing required field doctor_id"}), 400
    print("It did: ")
    print(did)
    res = fetch_doctor_patients(database, did)
    patients = []

    for item in res:
        patients.append({
            "patient_id": item[2],
            "name": item[0],
            "surname": item[1]
        })

    return jsonify({"patients": patients}), 200

@app.route('/stats/hospitals', methods=['GET'])
@jwt_required
def get_stat_hospitals():
	db = get_database()
	rows = fetch_stat_hospitals(db)
	db.close()
	return jsonify(rows), 200

@app.route('/verify-token', methods=['POST'])
def verify_token():
    start = time.time()
    data = request.get_json()
    token = data.get("idToken")
    if not token:
        return jsonify({ "error": "Missing idToken" }), 400

    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request())
        email = idinfo["email"]
        name  = idinfo["name"]

        cursor = database.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Doctor WHERE email = %s", (email,))
        doctor = cursor.fetchone()
        print(f"[VERIFY‐TOKEN] Looking in Doctor for {email} → doctor row = {doctor}")

        if doctor:
            role = "doctor"
        else:
            cursor.execute("SELECT * FROM Personel WHERE email = %s", (email,))
            personel = cursor.fetchone()
            print(f"[VERIFY‐TOKEN] Looking in Personel for {email} → personel row = {personel}")

            if personel:
                role = "personel"
            else:
                print(f"[VERIFY‐TOKEN] NO doctor AND NO personel row for {email}.")
                return jsonify({ "error": "User not registered as Doctor or Personel" }), 403

        payload = {
            "sub":   idinfo["sub"],
            "email": email,
            "name":  name,
            "role":  role,
            "exp":   datetime.utcnow() + timedelta(hours=2)
        }
        jwt_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        print(f"[VERIFY‐TOKEN] → issuing JWT with role={role}")

        return jsonify({
            "message": "Token is valid",
            "jwt":     jwt_token,
            "email":   email,
            "name":    name,
            "role":    role
        }), 200

    except ValueError as e:
        print(f"[VERIFY‐TOKEN] Token verification failed: {e}")
        return jsonify({ "error": "Invalid token", "details": str(e) }), 401

@app.route('/transcribe', methods=["POST"])
@jwt_required
def transcribe_audio():
    if 'title' not in request.form:
        return jsonify({"error": "Missing anamnesis title"}), 400

    if 'id_' not in request.form:
        return jsonify({"error": "Missing patient key"}), 400

    if 'audio_file' not in request.files:
        return jsonify({"error": "Missing 'audio_file'"}), 400

    uploaded_file = request.files['audio_file']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
        uploaded_file.save(temp.name)
        temp_path = temp.name

    transcription = ""
    try:
        model = whisper.load_model('base')
        result = model.transcribe(temp_path, language='en')
        transcription = result['text']

        hashed_id = request.form['id_']
        pid, did, hid, enc_key = fetch_pid(database, hashed_id)
        if pid == -1:
            return jsonify({"error": "Patient id is invalid"}), 400

        save_anamnesis(
            database,
            request.form['title'],
            transcription,
            pid,
            did,
            hid,
            enc_key
        )

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

    finally:
        os.remove(temp_path)

    return jsonify({"transription": transcription}), 200

@app.route("/test-multiple-recordings", methods=["POST"])
@jwt_required
def test_combo():
    debug(request)

    if 'audio_files' not in request.files:
        return jsonify({"error": "Missing 'audio_files'"}), 400

    uploaded_files = request.files.getlist("audio_files")
    if len(uploaded_files) == 0:
        return jsonify({"error": "No audio files"}), 400

    filenames = []
    try:
        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp:
                uploaded_file.save(temp.name)
                filenames.append(temp.name)

        temp_path = concat_mp3_files(filenames, "final.mp3")

        model = whisper.load_model('base')
        result = model.transcribe("final.mp3", language='en')
        transcription = result['text']

        if 'id_' not in request.form:
            return jsonify({"error": "Missing patient key"}), 400
        hashed_id = request.form['id_']

        pid, did, hid, enc_key = fetch_pid(database, hashed_id)
        if pid == -1:
            return jsonify({"error": "Patient id is invalid"}), 400

        if 'title' not in request.form:
            return jsonify({"error": "Missing anamnesis title"}), 400
        title = request.form['title']

        save_anamnesis(
            database,
            title,
            transcription,
            pid,
            did,
            hid,
            enc_key
        )
        return jsonify({"message": transcription, "status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists("final.mp3"):
            os.remove("final.mp3")
        for file in filenames:
            if os.path.exists(file):
                os.remove(file)

@app.route('/fetch-pending-anamnesis-all', methods=['GET'])
@jwt_required
def fetch_pending_anamnesis_all():
    """
    For personnel: return a JSON array of all pending anamnesis entries.
    Each item: {
        "id_anamnesis": <int>,
        "p_name": <patient name>,
        "p_surname": <patient surname>,
        "title": <title>,
        "contents": <decrypted plaintext>,
        "d_name": <doctor name>,
        "d_surname": <doctor surname>
    }
    """
    db = get_database()
    cursor = db.cursor()

    sql = """
        SELECT a.idAnamnesis,
               p.name AS p_name,
               p.surname AS p_surname,
               a.title,
               a.contents,       -- encrypted blob
               d.name AS d_name,
               d.surname AS d_surname,
               p.enc_key         -- the patient's encrypted DEK
        FROM Anamnesis AS a
        JOIN Patient   AS p ON a.fk_patient = p.idPatient
        JOIN Doctor    AS d ON a.fk_doctor  = d.idDoctor
        WHERE a.status = 'pending';
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    db.close()

    result = []
    for row in rows:
        (
            id_anam,
            p_name,
            p_surname,
            title,
            enc_contents_blob,
            d_name,
            d_surname,
            patient_enc_key_b64
        ) = row

        try:
            patient_dek = decrypt_dek(patient_enc_key_b64)
            plaintext = decrypt_text(enc_contents_blob, patient_dek)

        except Exception as e:
            plaintext = ""
            print(f"Failed to decrypt anamnesis #{id_anamnes}: {e}")

        result.append({
            "id_anamnesis": id_anam,
            "p_name":       p_name,
            "p_surname":    p_surname,
            "title":        title,
            "contents":     plaintext,
            "d_name":       d_name,
            "d_surname":    d_surname
        })

    return jsonify(result), 200
@app.route('/update-personel-anamnesis', methods=['POST'])
@jwt_required
def update_personel_anamnesis():
    """
    Accepts JSON: { "anamnesis_id": <int>, "contents": "<plaintext string>" }
    Re-encrypts the new plaintext under the patient’s DEK, updates the row,
    and sets status = 'approved'.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    anam_id = data.get("anamnesis_id")
    new_plain = data.get("contents", "").strip()

    if anam_id is None or new_plain == "":
        return jsonify({"error": "Missing required fields"}), 400

    db = get_database()
    cursor = db.cursor()
    cursor.execute(
        "SELECT fk_patient FROM Anamnesis WHERE idAnamnesis = %s AND status = 'pending';",
        (anam_id,)
    )
    row = cursor.fetchone()
    if not row:
        db.close()
        return jsonify({"error": "No such pending anamnesis or already approved"}), 404

    pid = row[0]

    cursor.execute("SELECT enc_key FROM Patient WHERE idPatient = %s;", (pid,))
    patient_row = cursor.fetchone()
    if not patient_row:
        db.close()
        return jsonify({"error": "Invalid patient ID"}), 400

    patient_enc_key_b64 = patient_row[0]

    try:
        patient_dek = decrypt_dek(patient_enc_key_b64)

        new_enc = encrypt_text(new_plain, patient_dek)

        cursor.execute(
            "UPDATE Anamnesis SET contents = %s, status = 'approved', updated_at = NOW() WHERE idAnamnesis = %s;",
            (new_enc, anam_id)
        )
        db.commit()

    except Exception as e:
        db.close()
        print(f"Failed to update anamnesis #{anam_id}: {e}")
        return jsonify({"error": "Encryption or DB update failed"}), 500

    db.close()
    return jsonify({"status": "approved"}), 200
if __name__ == '__main__':
	app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)

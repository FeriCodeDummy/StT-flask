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
from dbm import save_transcribed, fetch_anamnesis
from dotenv import load_dotenv, dotenv_values 
import whisper
import tempfile
from flask_cors import CORS, cross_origin
load_dotenv() 
get = os.getenv

SECRET_KEY = os.getenv("JWT_SECRET", "fallback-dev-secret")

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))

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

app = Flask(__name__)
CORS(app)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers['X-Content-Type-Options'] = '*'
        return res

@app.route('/anamnesis', methods=["GET"])
@cross_origin()
def get_anamnesis():
    res = fetch_anamnesis(database)
    return jsonify({"anamnesis": res}), 200

@app.route('/verify-token', methods=['POST'])
def verify_token():
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

        return jsonify({
            "message": "Token is valid",
            "jwt": jwt_token,
            "email": idinfo["email"],
            "name": idinfo["name"],
	        "role": role
        }), 200

    except ValueError as e:
        return jsonify({"error": "Invalid token", "details": str(e)}), 401
    
@app.route('/transcribe', methods=["POST"])
def transcribe_audio():
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
        print(transcription)
        #save_transcribed(database, transcription)

    except Exception as e:
        print(e)

    finally:
        os.remove(temp_path)  

    return jsonify({"transribtion": transcription}), 200



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

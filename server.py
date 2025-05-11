from flask import Flask, request, jsonify
from vosk import Model, KaldiRecognizer
import wave
import io
from pydub import AudioSegment
import json
import time
from speech_to_text import stt
from datetime import datetime
import mysql.connector
import os
from dbm import save_transcribed
from dotenv import load_dotenv, dotenv_values 
load_dotenv() 
get = os.getenv

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))
VOSK_MODEL = "vosk-model-en-us-0.22"


print(f"[*] Loading model {VOSK_MODEL}")
try:
    s = time.time()
    model = Model(VOSK_MODEL)
    e = time.time()
    print(f"[+] Loaded Vosk model in {e-s}s")
except Exception as e:
    print("[!] Vosk model failed to load. Quitting...")
    exit(-1)

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

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_file' not in request.files:
        return jsonify({"error": "Missing 'audio_file'"}), 400

    uploaded_file = request.files['audio_file'].stream
    suf = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename = f"audio_{suf}.wav"

    
    text = stt(uploaded_file, filename, model)
    save_transcribed(database, text)
    return jsonify({"transcript": text}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
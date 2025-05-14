from flask import Flask, request, jsonify
import io
import json
import time
import mysql.connector
import os
from dbm import save_transcribed
from dotenv import load_dotenv, dotenv_values 
import whisper
import tempfile
from flask_cors import CORS

load_dotenv() 
get = os.getenv

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
        save_transcribed(database, transcription)

    finally:
        os.remove(temp_path)  

    return jsonify({"transribtion": transcription}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

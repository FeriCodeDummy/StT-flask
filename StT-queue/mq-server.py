from flask import Flask, request
from queue_stt import audio_queue
import os
import uuid
from dotenv import load_dotenv
from binascii import unhexlify
from gdpr_auth import decrypt_file

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        print("File not appended")
        return {"error": "No file uploaded"}, 400

    if 'decryption_key' not in request.form:
        print("Key not appended")
        return {"error": "No decryption key provided"}, 400

    # Get file and key
    file = request.files['file']
    dek_hex = request.form['decryption_key']

    try:
        key = unhexlify(dek_hex)
    except Exception:
        return {"error": "Invalid decryption key format"}, 400

    filename_base = uuid.uuid4().hex
    encrypted_filename = f"{filename_base}.bin"
    encrypted_path = os.path.join(UPLOAD_FOLDER, encrypted_filename)
    file.save(encrypted_path)

    decrypted_filename = f"{filename_base}.wav"
    decrypted_path = os.path.join(UPLOAD_FOLDER, decrypted_filename)

    try:
        decrypt_file(encrypted_path, decrypted_path, key)
    except Exception as e:
        return {"error": f"Decryption failed: {str(e)}"}, 500

    audio_queue.put(decrypted_path)

    return {"message": "File decrypted and queued", "file": decrypted_filename}, 202


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=True, threaded=True)

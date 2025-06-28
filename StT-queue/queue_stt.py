# queue_stt.py
import os
import queue
import threading
import azure.cognitiveservices.speech as speechsdk
import time

import requests
from dotenv import load_dotenv
load_dotenv()

speech_key = os.getenv("speech_key")
service_region = os.getenv("service_region")
print(speech_key, service_region)
audio_queue = queue.Queue()


def transcribe_worker():
    while True:
        path = audio_queue.get()
        print(f"Transcribing: {path}")
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
        speech_config.speech_recognition_language = "sl-SI"
        audio_config = speechsdk.AudioConfig(filename=path)
        recognizer = speechsdk.SpeechRecognizer(speech_config, audio_config)

        results = []

        def result_handler(evt):
            results.append(evt.result.text)

        def stop_handler(evt):
            audio_queue.task_done()

        recognizer.recognized.connect(result_handler)
        recognizer.session_stopped.connect(stop_handler)
        recognizer.canceled.connect(stop_handler)

        recognizer.start_continuous_recognition()
        while not audio_queue.empty():
            time.sleep(0.5)

        recognizer.stop_continuous_recognition()
        with open(path + '.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
            print('\n'.join(results))
            requests.post("http://localhost:5000/save-transcribed-anamnesis")
        print(f"Saved transcription to: {path}.txt")


# Start worker thread
threading.Thread(target=transcribe_worker, daemon=True).start()

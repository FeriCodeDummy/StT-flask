from pydub import AudioSegment
from vosk import Model, KaldiRecognizer
import json
import wave
import os
import time
# Load and convert mp3 to wav

def stt(stream, filename, model):
    
    audio = AudioSegment.from_file(stream, format='mp3')
    audio.export(filename, format="wav")
    wf = wave.open(filename, "rb")

    recognizer = KaldiRecognizer(model, wf.getframerate())
    results = []

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            results.append(json.loads(recognizer.Result())["text"])

    results.append(json.loads(recognizer.FinalResult())["text"])

    transcript = " ".join(results)
    print("Transcription: ", transcript)
    return transcript

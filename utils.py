import threading

from pydub import AudioSegment
import azure.cognitiveservices.speech as speechsdk
import os
from dotenv import load_dotenv
load_dotenv()


def concat_wav_files(file_list, output_file="processed.wav", silence_duration=500):
    silence = AudioSegment.silent(duration=silence_duration)

    combined = AudioSegment.empty()
    for i, file in enumerate(file_list):
        audio = AudioSegment.from_file(file)
        combined += audio
        if i < len(file_list) - 1:
            combined += silence

    combined.export(output_file, format="wav")
    return output_file


def to_medical_format(anamnesis, client):
    user_query = (
        "Prosimo, pretvori naslednjo anamnezo v strukturirano, a neprekinjeno klinično pripoved. "
        "Ne uporabljaj naslovov ali alinej. Uporabi ustrezno strokovno medicinsko terminologijo "
        "in oblikuj besedilo v jasne, povezane odstavke:\n\n"
    )
    message = user_query + anamnesis
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ti si medicinski dokumentacijski asistent. Na podlagi neformalnih ali prepisanih kliničnih zapiskov "
                    "preoblikuj besedilo v uradno medicinsko pripoved, primerno za vnos v elektronsko zdravstveno kartoteko "
                    "ali napotno pismo. Uporabi jasne odstavke za boljšo berljivost. Izogibaj se uporabi naslovov ali alinej. "
                    "Uporabi natančno in strokovno medicinsko terminologijo v neprekinjeni pripovedni obliki."
                )
            },
            {
                "role": "user",
                "content": message
            }
        ],
    )
    return response.choices[0].message.content


def transcribe(path):
    speech_key = os.getenv("speech_key")
    service_region = os.getenv("service_region")
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
    speech_config.speech_recognition_language = "sl-SI"

    audio_config = speechsdk.AudioConfig(filename=path)
    recognizer = speechsdk.SpeechRecognizer(speech_config, audio_config)

    results = []

    def result_handler(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            results.append(evt.result.text)

    recognizer.recognized.connect(result_handler)

    done = threading.Event()

    def stop_handler(evt):
        done.set()

    recognizer.session_stopped.connect(stop_handler)
    recognizer.canceled.connect(stop_handler)

    recognizer.start_continuous_recognition()
    done.wait()
    recognizer.stop_continuous_recognition()

    final_text = '\n'.join(results)

    return final_text

# syntax=docker/dockerfile:1.4

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY server.py .
COPY speech_to_text.py .
COPY vosk-model-en-us-0.22/ vosk-model-en-us-0.22/

RUN pip install flask vosk pydub

EXPOSE 5000

CMD ["python", "server.py"]

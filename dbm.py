import os

def save_transcribed(db, text):
	sql = f"INSERT INTO temp (`idTemp`, `transcription`) VALUES (NULL, \"{text}\")"
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()

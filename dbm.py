import os
from gdpr_auth import generate_key, decrypt_text, decrypt_dek, encrypt_text

def save_transcribed(db, text):
	sql = f"INSERT INTO temp (`idTemp`, `transcription`) VALUES (NULL, \"{text}\")"
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()

def fetch_anamnesis(db):
	sql = f"SELECT text from Temp;"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	return res

def create_hospital(db, name, country, city, address):
	sql = f'INSERT INTO Hospital(`idHospital`, `name`, `country`, `city`, `address`) VALUES (NULL, "{name}", "{country}", "{city}", "{address}");'
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()
	return cursor.lastrowid


def fetch_hospitals(db):
	"""
	Create table Hospital (
	idHospital INT PRIMARY KEY NOT NULL AUTO_INCREMENT,
	name VARCHAR(256) NOT NULL UNIQUE,
	country VARCHAR(128) NOT NULL, 
	city VARCHAR(256) NOT NULL,
	address VARCHAR(256) NOT NULL
);	"""
	sql = f"SELECT * from Hospital;"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	return res

def save_doctor(db, name, surname, specialization, email, fk_hospital):
	enc_key = generate_key()
	sql = f"INSERT INTO Doctor VALUES (NULL, '{name}', '{surname}', '{specialization}', '{enc_key}', '{email}', {fk_hospital});"
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()
	return cursor.lastrowid

def fetch_doctor_hospital(db):
	sql = f'SELECT d.idDoctor as "fk_doc", d.name as "Name", surname, h.idHospital as "fk_hos", h.name as "Hospital" FROM Doctor as d JOIN Hospital as h ON h.idHospital = d.fk_hospital';
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()	
	return res

def save_patient(db, name, surname, email, fk_doctor, fk_hospital):
	enc_key = generate_key()
	sql = f"INSERT INTO Patient VALUES (NULL, '{name}', '{surname}', '{email}', '{enc_key}', {fk_doctor}, {fk_hospital});"
	print(sql)
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()
	return cursor.lastrowid



def fetch_decrypted_anamnesis(db):
	sql = f"""select p.enc_key, p.name as "Name", p.surname as "Surname", title as "Title", contents, d.name, d.surname, idAnamnisa from Anamnesis
	JOIN Patient as p on p.idPatient = Anamnesis.fk_patient
	JOIN Doctor as d on d.idDoctor = p.fk_doctor;
	"""
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	decrypted = []
	for item in res:
		enc_key = item[0]
		dec = decrypt_dek(enc_key)
		text = decrypt_text(item[4], dec)
		decrypted.append([item[1], item[2], item[3], text, item[5], item[6], item[7], enc_key])
	return decrypted

def update_anamnesis(db, text, aid, enc_key):
	enc_key = decrypt_dek(enc_key)
	print(text)
	contents = encrypt_text(text, enc_key)
	sql = f"UPDATE Anamnesis SET contents='{contents}' where idAnamnisa = {aid};"
	cursor = db.cursor()
	cursor.execute(sql)
	db.commit()
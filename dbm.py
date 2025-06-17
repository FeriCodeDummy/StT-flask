import os
from gdpr_auth import decrypt_text, decrypt_dek, encrypt_text
from hashlib import sha256


def fetch_anamnesis_reencrypted(db, key_):
	sql = """SELECT p.name AS "Name", p.surname AS "Surname", title AS "Title", contents, d.name, d.surname, idAnamnesis, p.enc_key, p.idPatient FROM Anamnesis
	JOIN Patient AS p on p.idPatient = Anamnesis.fk_patient
	JOIN patient_has_doctor AS phd ON phd.fk_patient = p.idPatient
	JOIN Doctor AS d on d.idDoctor = phd.fk_doctor
	WHERE status = 'pending';
	"""
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	decrypted = []
	for item in res:
		dec = decrypt_dek(item[7])
		text = decrypt_text(item[3], dec)
		renc = encrypt_text(text, key_)
		js = {
			"p_name": item[0],
			"p_surname": item[1],
			"title": item[2],
			"contents": renc,
			"d_name": item[4],
			"d_surname": item[5],
			"id_anamnesis": item[6],
			"id_patient": item[8]
		}
		decrypted.append(js)
	return decrypted


def confirm_anamnesis(db, aid):
	sql = "UPDATE Anamnesis SET status = 'approved' WHERE idAnamesis = %s;"
	cursor = db.cursor()
	cursor.execute(sql, (aid))
	db.commit()


def update_anamnesis_data(db, text, aid):
	sql = "UPDATE Anamnesis SET contents = %s WHERE idAnamnesis = %s;"
	cursor = db.cursor()
	cursor.execute(sql, (text, aid))
	db.commit()


def save_anamnesis(db, title, text, pid, did, enc_key):
	# TODO Encrypt title of anamnesis too
	enc_key = decrypt_dek(enc_key)
	contents = encrypt_text(text, enc_key)

	sql = """INSERT INTO Anamnesis (`idAnamnesis`, `content`, `title`, `fk_patient`, `fk_doctor`)
		VALUES(NULL, %s, %s, %s, %s);"""
	cursor = db.cursor()
	cursor.execute(sql, (contents, title, pid, did))
	db.commit()
	return cursor.lastrowid


def fetch_pid(db, hashed):
	sql = "SELECT idPatient, fk_doctor, fk_hospital, enc_key FROM Patient"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	pid = -1
	hid = -1
	did = -1
	enc = ''
	for item in res:
		h = sha256(str(item[0]).encode('utf-8')).hexdigest()
		if hashed == h:
			pid = item[0]
			did = item[1]
			hid = item[2]
			enc = item[3]
			break

	return [pid, did, hid, enc]


def fetch_doctor_patients(db, email):
	sql = """SELECT p.name, p.surname, p.idPatient
			FROM Doctor AS d
			JOIN patient_has_doctor AS phd ON phd.fk_doctor = idDoctor
			JOIN Patient AS p ON idPatient = phd.fk_patient
			WHERE d.email = %s;
			"""
	cursor = db.cursor()
	cursor.execute(sql, (email,))
	res = cursor.fetchall()
	return res

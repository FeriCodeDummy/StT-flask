import os
from gdpr_auth import decrypt_text, decrypt_dek, encrypt_text
from hashlib import sha256


def fetch_anamnesis_reencrypted(db, key_):
	sql = """SELECT p.name, p.surname, title, content, d.name, d.surname, idAnamnesis, p.enc_key, p.idPatient, diagnosis, mkb_10, status, created_at FROM Anamnesis
	JOIN Patient AS p on p.idPatient = Anamnesis.fk_patient
	JOIN patient_has_doctor AS phd ON phd.fk_patient = p.idPatient
	JOIN Doctor AS d on d.idDoctor = phd.fk_doctor
	WHERE status =  'UNPROCESSED';
	"""
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	decrypted = []
	for item in res:
		dec = decrypt_dek(item[7])
		text = decrypt_text(item[3], dec)
		renc = encrypt_text(text, key_)
		diag = decrypt_text(item[9], dec)
		diag_r = encrypt_text(diag, key_)
		js = {
			"p_name": item[0],
			"p_surname": item[1],
			"title": item[2],
			"contents": renc,
			"d_name": item[4],
			"d_surname": item[5],
			"id_anamnesis": item[6],
			"id_patient": item[8],
			"diagnosis": diag_r,
			"mkb10": item[10],
			"status": item[11],
			"date": item[12]
		}
		decrypted.append(js)
	return decrypted


def fetch_anamnesis_reencrypted_doctor(db, key_, email):
    sql = """SELECT p.name, p.surname, title, content, d.name, d.surname, idAnamnesis, p.enc_key, p.idPatient, diagnosis, mkb_10, status, created_at, Country.country, zipcode, City.city, address_1, specialty, medical_card_id, birthday FROM Anamnesis
    JOIN Patient AS p on p.idPatient = Anamnesis.fk_patient
    JOIN patient_has_doctor AS phd ON phd.fk_patient = p.idPatient
    JOIN Doctor AS d on d.idDoctor = phd.fk_doctor
    JOIN Address on idAddress = fk_address
    JOIN Country on idCountry = fk_country
    JOIN City on idCity = fk_city
    JOIN Specialty on fk_specialty = idSpecialty
    WHERE d.email = %s;
    """

    cursor = db.cursor()
    cursor.execute(sql, (email,))
    res = cursor.fetchall()
    decrypted = []
    for item in res:
        dec = decrypt_dek(item[7])
        text = decrypt_text(item[3], dec)
        renc = encrypt_text(text, key_)
        diag = decrypt_text(item[9], dec)
        diag_r = encrypt_text(diag, key_)
        js = {
            "p_name": item[0],
            "p_surname": item[1],
            "title": item[2],
            "contents": renc,
            "d_name": item[4],
            "d_surname": item[5],
            "id_anamnesis": item[6],
            "id_patient": item[8],
            "diagnosis": diag_r,
            "mkb10": item[10],
            "status": item[11],
            "date": item[12],
            "country": item[13],
            "zipcode": item[14],
            'city': item[15],
            "address": item[16],
            "specialty": item[17],
            "kzz": item[18],
            "birthday": item[19]
        }

        decrypted.append(js)
    return decrypted


def confirm_anamnesis(db, aid):
	sql = "UPDATE Anamnesis SET status = 'PENDING', processed_at = NOW() WHERE idAnamesis = %s;"
	cursor = db.cursor()
	cursor.execute(sql, (aid,))
	db.commit()


def update_anamnesis_data(db, text, diagnosis, mkb_10, aid, pid):
	sq = "SELECT enc_key from Patient where idPatient = %s;"
	cursor = db.cursor()
	cursor.execute(sq, (pid,))
	enc_key = cursor.fetchall()[0][0]
	key = decrypt_dek(enc_key)
	text = encrypt_text(text, key)
	diagnosis = encrypt_text(diagnosis, key)

	sql = "UPDATE Anamnesis SET content = %s, mkb_10 = %s, status='CONFIRMED', diagnosis = %s, confirmed_at = NOW()  WHERE idAnamnesis = %s;"
	cursor = db.cursor()
	cursor.execute(sql, (text, mkb_10, diagnosis, aid))
	db.commit()


def save_anamnesis(db, title, text, pid, did_):
	sql = "SELECT idDoctor from Doctor where email = %s"
	cursor = db.cursor()
	cursor.execute(sql, (did_,))
	did = cursor.fetchall()[0][0]
	sql = "SELECT enc_key from Patient where idPatient = %s"
	cursor = db.cursor()
	cursor.execute(sql, (pid,))
	enc_key = cursor.fetchall()[0][0]

	enc_key = decrypt_dek(enc_key)
	contents = encrypt_text(text, enc_key)
	diagnosis = encrypt_text("", enc_key)

	sql = """INSERT INTO Anamnesis (`idAnamnesis`, `content`, `title`, `fk_patient`, `fk_doctor`, `diagnosis`, `created_at`, `mkb_10`)
		VALUES(NULL, %s, %s, %s, %s, %s, NOW(), 'F00.00');"""
	cursor = db.cursor()
	cursor.execute(sql, (contents, title, pid, did, diagnosis))
	db.commit()
	return cursor.lastrowid


def fetch_pid(db, hashed):
	sql = "SELECT idPatient, enc_key from Patient;"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	pid = -1
	enc = ''
	for item in res:
		h = sha256(str(item[0]).encode('utf-8')).hexdigest()
		if hashed == h:
			pid = item[0]
			enc = item[1]
			break

	return [pid, enc]


def fetch_doctor_patients(db, email):
	sql = """SELECT p.name, p.surname, p.idPatient, p.medical_card_id,p.birthday
			FROM Doctor AS d
			JOIN patient_has_doctor AS phd ON phd.fk_doctor = idDoctor
			JOIN Patient AS p ON idPatient = phd.fk_patient
			WHERE d.email = %s;
			"""
	cursor = db.cursor()
	cursor.execute(sql, (email,))
	res = cursor.fetchall()
	return res

import os
from gdpr_auth import generate_key, decrypt_text, decrypt_dek, encrypt_text
from hashlib import sha256 


def create_hospital(db, name, country, city, address):
	sql = 'INSERT INTO Hospital(`idHospital`, `name`, `country`, `city`, `address`) VALUES (NULL, %s, %s, %s, %s);'
	cursor = db.cursor()
	cursor.execute(sql, (name, country, citry, address))
	db.commit()
	return cursor.lastrowid

def fetch_hospitals(db):
	sql = "SELECT * FROM Hospital;"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	return res

def save_doctor(db, name, surname, email, fk_specialty, fk_hospital):
	enc_key = generate_key()
	sql = """INSERT INTO Doctor (`idDoctor`, `name`, `surname`, `enc_key`, `email`, `fk_specialty`, `fk_hospital`)
				VALUES (NULL, %s, %s, %s, %s, %s, %s)"""
	cursor = db.cursor()
	cursor.execute(sql, (name, surname, enc_key, email, fk_specialty, fk_hospital, fk_specialty,fk_hospital))
	db.commit()
	return cursor.lastrowid

def fetch_doctor_hospital(db):
	sql = 'SELECT d.idDoctor as "fk_doc", d.name as "Name", surname, h.idHospital as "fk_hos", h.name as "Hospital" FROM Doctor as d JOIN Hospital as h ON h.idHospital = d.fk_hospital';
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()	
	return res

def save_patient(db, name, surname, email, fk_doctor, fk_hospital):
	enc_key = generate_key()
	sql = """INSERT INTO Patient (`idPatient`, `name`, `surname`, `email`, `enc_key`, `fk_doctor`, `fk_hospital`)
		VALUES (NULL, %s, %s, %s, %s, %s, %s);"""
	cursor = db.cursor()
	cursor.execute(sql, (name, surname, email, enc_key, fk_doctor, fk_hospital))
	db.commit()
	return cursor.lastrowid

def fetch_stat_doctors(db):
    cursor = db.cursor()
    cursor.execute("""
        SELECT name, surname, email, n_patients, n_anamnesis
        FROM stat_doctors
    """)
    return cursor.fetchall()

def fetch_stat_hospitals(db):
    sql = """
        SELECT name, n_patients, n_doctors, n_anamnesis, fk_hospital
        FROM stat_hospital
    """
    cursor = db.cursor()
    cursor.execute(sql)
    res = cursor.fetchall()

    hospitals = []
    for row in res:
        hospitals.append({
            "name": row[0],
            "n_patients": row[1],
            "n_doctors": row[2],
            "n_anamnesis": row[3],
            "fk_hospital": row[4]
        })

    return hospitals

def fetch_decrypted_anamnesis(db):
	sql = """SELECT p.enc_key, p.name AS "Name", p.surname AS "Surname", title AS "Title", contents, d.name, d.surname, idAnamnesis FROM Anamnesis
	JOIN Patient AS p on p.idPatient = Anamnesis.fk_patient
	JOIN Doctor AS d on d.idDoctor = p.fk_doctor;
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

def fetch_anamnesis_reencrypted(db, key_):
	sql = """SELECT p.name AS "Name", p.surname AS "Surname", title AS "Title", contents, d.name, d.surname, idAnamnesis, p.enc_key, p.idPatient FROM Anamnesis
	JOIN Patient AS p on p.idPatient = Anamnesis.fk_patient
	JOIN Doctor AS d on d.idDoctor = p.fk_doctor
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

def update_anamnesis(db, text, aid, enc_key):
	enc_key = decrypt_dek(enc_key)
	contents = encrypt_text(text, enc_key)
	sql = "UPDATE Anamnesis SET contents=%s WHERE idAnamnesis = %s;"

	cursor = db.cursor()
	cursor.execute(sql, (text, aid))
	db.commit()

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

def save_anamnesis(db, title, text, pid, did, hid, enc_key):
	enc_key = decrypt_dek(enc_key)
	contents = encrypt_text(text, enc_key)

	sql = """INSERT INTO Anamnesis (`idAnamnesis`, `contents`, `title`, `fk_patient`, `fk_doctor`, `fk_hospital`)
		VALUES(NULL, %s, %s, %s, %s, %s);"""	
	cursor = db.cursor()
	cursor.execute(sql, (contents, title, pid, did, hid))
	db.commit()
	return cursor.lastrowid


def fetch_specialties(db):
	sql = "SELECT * FROM Specialty;"
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	return res

def fetch_all_patients(db):
	sql = """SELECT idPatient, p.enc_key, p.name, p.surname, fk_doctor, p.fk_hospital, d.name, d.surname FROM Patient AS p
		JOIN Doctor AS d ON fk_doctor = idDoctor;"""
	cursor = db.cursor()
	cursor.execute(sql)
	res = cursor.fetchall()
	return res

def fetch_pid(db, hashed): #or ids, to be discussed
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
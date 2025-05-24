import tkinter as tk
from tkinter import messagebox, ttk
from dbm import save_anamnesis, fetch_all_patients, create_hospital, fetch_hospitals, save_doctor, save_patient, fetch_doctor_hospital, fetch_decrypted_anamnesis, update_anamnesis, fetch_specialties
import mysql.connector
import os
from dotenv import load_dotenv, dotenv_values

load_dotenv() 
get = os.getenv

HOST = get("MYSQL_HOST")
USER = get("MYSQL_USER")
PSWD = get("MYSQL_PASSWORD")
PORT = int(get("MYSQL_PORT"))
print("[*] Connecting to MySQL database ...")
try:
	database = mysql.connector.connect(
		  host=HOST,
		  user=USER,
		  password=PSWD,
		  database="mediphone",
		  port=PORT
	)
	print("[+] Connection successful")
except Exception as e:
	print("[!] Failed to connect to the database. Quitting...")
	exit(-1)

def save_hospital(name, country, city, address):
	id_ = create_hospital(database, name, country, city, address)
	messagebox.showinfo("Info", f"Hospital saved successfully ({id_})!")

def build_hospital_section(parent, refresh):
	hospital_frame = ttk.LabelFrame(parent, text="Create Hospital")
	hospital_frame.pack(fill="x", padx=10, pady=10)

	name = tk.Entry(hospital_frame, width=30)
	country = tk.Entry(hospital_frame, width=30)
	city = tk.Entry(hospital_frame, width=30)
	address = tk.Entry(hospital_frame, width=30)

	for idx, (label, widget) in enumerate([
		("Name", name),
		("Country", country),
		("City", city),
		("Address", address),
	]):
		ttk.Label(hospital_frame, text=label).grid(row=idx, column=0, padx=5, pady=5, sticky="e")
		widget.grid(row=idx, column=1, padx=5, pady=5)

	def on_create():
		save_hospital(name.get(), country.get(), city.get(), address.get())
		refresh()
	ttk.Button(hospital_frame, text="Create", command=on_create).grid(row=4, column=1, pady=10)

def build_doctor_section(parent, refresh):
	doctor_frame = ttk.LabelFrame(parent, text="Create Doctor")
	doctor_frame.pack(fill="x", padx=10, pady=10)

	doc_name = tk.Entry(doctor_frame, width=30)
	doc_surname = tk.Entry(doctor_frame, width=30)
	
	doc_email = tk.Entry(doctor_frame, width=30)

	ttk.Label(doctor_frame, text="Name").grid(row=0, column=0, padx=5, pady=5, sticky="e")
	doc_name.grid(row=0, column=1, padx=5, pady=5)

	ttk.Label(doctor_frame, text="Surname").grid(row=1, column=0, padx=5, pady=5, sticky="e")
	doc_surname.grid(row=1, column=1, padx=5, pady=5)

	ttk.Label(doctor_frame, text="Email").grid(row=2, column=0, padx=5, pady=5, sticky="e")
	doc_email.grid(row=2, column=1, padx=5, pady=5)


	# Fetch specialties
	res_s = fetch_specialties(database)
	s_labels = [i[1] for i in res_s] 
	s_idxs = [i[0] for i in res_s]

	selected_option_s = tk.StringVar()
	ttk.Label(doctor_frame, text="Specialty").grid(row=3, column=0, padx=5, pady=5,sticky="e")
	combo_s = ttk.Combobox(doctor_frame, textvariable=selected_option_s, values=s_labels, state="readonly")
	combo_s.grid(row=3, column=1, padx=5, pady=5)

	# Fetch hospitals
	res = fetch_hospitals(database)  # make sure this function exists
	h_labels = [f"{i[1]} in {i[2]}" for i in res]
	h_ids = [i[0] for i in res]  # assuming fetch_hospitals returns (id, name, city)

	selected_option = tk.StringVar()
	ttk.Label(doctor_frame, text="Hospital").grid(row=4, column=0, padx=5, pady=5, sticky="e")
	combo = ttk.Combobox(doctor_frame, textvariable=selected_option, values=h_labels, state="readonly")
	combo.grid(row=4, column=1, padx=5, pady=5)

	def on_create():
		selected_index = combo.current()
		if selected_index == -1:
			messagebox.showerror("Error", "Please select a hospital.")
			return
		fk_hospital = h_ids[selected_index]
		
		selected_index_s = combo_s.current()
		if selected_index_s == -1:
			messagebox.showerror("Error", "Please select a specialty.")
			return
		fk_specialty = s_idxs[selected_index_s]
		
		save_doctor(
			database,
			doc_name.get(),
			doc_surname.get(),
			doc_email.get(),
			fk_specialty,
			fk_hospital
		)

		refresh()

	ttk.Button(doctor_frame, text="Create", command=on_create).grid(row=5, column=1, pady=10)

def build_patient_section(parent, refresh):
	patient_frame = ttk.LabelFrame(parent, text="Create patient")
	patient_frame.pack(fill="x", padx=10, pady=10)

	name = tk.Entry(patient_frame, width=30)
	surname = tk.Entry(patient_frame, width=30)
	email = tk.Entry(patient_frame, width=30)

	ttk.Label(patient_frame, text="Name").grid(row=0, column=0, padx=5, pady=5, sticky="e")
	name.grid(row=0, column=1, padx=5, pady=5)

	ttk.Label(patient_frame, text="Surname").grid(row=1, column=0, padx=5, pady=5, sticky="e")
	surname.grid(row=1, column=1, padx=5, pady=5)

	
	ttk.Label(patient_frame, text="Email").grid(row=3, column=0, padx=5, pady=5, sticky="e")
	email.grid(row=3, column=1, padx=5, pady=5)
	res = fetch_doctor_hospital(database)
	d_labels = []
	d_idxs = []
	h_idxs = []

	for i in res:
		d_labels.append(f"Dr. {i[1]} {i[2]} ({i[4]})")
		d_idxs.append(i[0])
		h_idxs.append(i[3])
		
	selected_option = tk.StringVar()
	ttk.Label(patient_frame, text="Doctor").grid(row=4, column=0, padx=5, pady=5, sticky="e")
	combo = ttk.Combobox(patient_frame, textvariable=selected_option, values=d_labels, state="readonly")
	combo.grid(row=4, column=1, padx=5, pady=5)

	def on_create():
		selected_index = combo.current()
		if selected_index == -1:
			messagebox.showerror("Error", "Please select a doctor.")
			return
		fk_hospital = h_idxs[selected_index]
		fk_doctor = d_idxs[selected_index]
		try:
			save_patient(
				database,
				name.get(),
				surname.get(),
				email.get(),
				fk_doctor,
				fk_hospital
				)
			refresh()
		except Exception as e:
			print(e)

	ttk.Button(patient_frame, text="Create", command=on_create).grid(row=5, column=1, pady=10)

def show_details(text, aid, enc_key):
	detail_window = tk.Toplevel()
	detail_window.title("Edit Row")
	detail_window.geometry("600x400")

	ttk.Label(detail_window, text="Edit Anamnesis", font=("Arial", 14, "bold")).pack(pady=10)

	text_frame = ttk.Frame(detail_window)
	text_frame.pack(fill="both", expand=True, padx=10, pady=10)

	text_widget = tk.Text(text_frame, wrap="word", font=("Courier", 10))
	text_widget.pack(side="left", fill="both", expand=True)

	scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
	scrollbar.pack(side="right", fill="y")
	text_widget.configure(yscrollcommand=scrollbar.set)
	text_widget.insert("1.0", text)
	button_frame = ttk.Frame(detail_window)
	button_frame.pack(pady=10)
	
	def on_save():
		new_data = text_widget.get("1.0", "end").strip()
		update_anamnesis(database, new_data, aid, enc_key)

		detail_window.destroy()
		
	def on_cancel():
		detail_window.destroy()

	ttk.Button(button_frame, text="Save", command=on_save).pack(side="left", padx=10)
	ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side="left", padx=10)

def build_decoded_anamnesis(parent):
	dec_frame = ttk.LabelFrame(parent, text="Edit amnesis")
	dec_frame.pack(fill="x", padx=10, pady=10)

	res = fetch_decrypted_anamnesis(database)
	for i, row in enumerate(res):
		name = row[0]
		surname = row[1]

		ttk.Label(dec_frame, text=name).grid(row=i, column=0, padx=5, pady=5, sticky="w")
		ttk.Label(dec_frame, text=surname).grid(row=i, column=1, padx=5, pady=5, sticky="w")

		ttk.Button(
			dec_frame,
			text="show anamnesis",
			command=lambda r=row: show_details(r[3], r[6], r[7]) 
		).grid(row=i, column=2, padx=5, pady=5)

def build_anamnesis_tab(notebook):
	anamnesis_tab = ttk.Frame(notebook)
	notebook.add(anamnesis_tab, text="Anamnesis")

	form_frame = ttk.LabelFrame(anamnesis_tab, text="Create Anamnesis")
	form_frame.pack(padx=10, pady=10, fill="both", expand=True)

	# Text input field
	ttk.Label(form_frame, text="Title:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
	title_entry = ttk.Entry(form_frame, width=40)
	title_entry.grid(row=0, column=1, padx=5, pady=5)

	res = fetch_all_patients(database)
	p_labels = [f"{item[2]} {item[3]} (Dr. {item[6]} {item[7]})" for item in res]
	p_keys = [item[1] for item in res]
	p_docs = [item[4] for item in res]
	p_hos = [item[5] for item in res]
	p_ids = [item[0] for item in res]


	ttk.Label(form_frame, text="Patient:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
	selected_option = tk.StringVar()
	type_dropdown = ttk.Combobox(form_frame, textvariable=selected_option, values=p_labels, state="readonly")
	type_dropdown.grid(row=1, column=1, padx=5, pady=5)
   
	ttk.Label(form_frame, text="Anamnesis:").grid(row=2, column=0, sticky="ne", padx=5, pady=5)
	details_text = tk.Text(form_frame, height=10, width=60, wrap="word")
	details_text.grid(row=2, column=1, padx=5, pady=5)

	
	def submit_anamnesis():
		title = title_entry.get()
		details = details_text.get("1.0", tk.END).strip()
		selected_index = type_dropdown.current()

		if selected_index == -1:
			messagebox.showerror("Error", "Please select a patient.")
			return
		pid = p_ids[selected_index]
		enc = p_keys[selected_index]
		hid= p_hos[selected_index]
		did = p_docs[selected_index]
		save_anamnesis(database, title, details, pid, did, hid, enc)
	submit_btn = ttk.Button(form_frame, text="Submit", command=submit_anamnesis)
	submit_btn.grid(row=3, column=1, sticky="e", padx=5, pady=10)

def create_admin_gui():
	root = tk.Tk()
	root.title("Admin Panel")
	root.geometry("800x700")

	notebook = ttk.Notebook(root)
	notebook.pack(expand=True, fill='both')
	create_tab = ttk.Frame(notebook)
	notebook.add(create_tab, text="Create objects")
	
	def refresh_create_tab():
		for widget in create_tab.winfo_children():
			widget.destroy()

		canvas = tk.Canvas(create_tab)
		scrollbar_c = ttk.Scrollbar(create_tab, orient="vertical", command=canvas.yview)
		scrollable_frame_c = ttk.Frame(canvas)

		scrollable_frame_c.bind(
			"<Configure>",
			lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
		)

		canvas.create_window((0, 0), window=scrollable_frame_c, anchor="nw")
		canvas.configure(yscrollcommand=scrollbar_c.set)
		canvas.pack(side="left", fill="both", expand=True)
		scrollbar_c.pack(side="right", fill="y")

		build_hospital_section(scrollable_frame_c, refresh_create_tab)
		build_doctor_section(scrollable_frame_c, refresh_create_tab)
		build_patient_section(scrollable_frame_c, refresh_create_tab)

	# Initial render
	refresh_create_tab()

	# Anamnesis tab
	anamnesis_tab = ttk.Frame(notebook)

	notebook.add(anamnesis_tab, text="View anamnesis")

	canvas_a = tk.Canvas(anamnesis_tab)
	scrollbar = ttk.Scrollbar(anamnesis_tab, orient="vertical", command=canvas_a.yview)
	scrollable_frame = ttk.Frame(canvas_a)

	scrollable_frame.bind(
		"<Configure>",
		lambda e: canvas_a.configure(scrollregion=canvas_a.bbox("all"))
	)

	canvas_a.create_window((0, 0), window=scrollable_frame, anchor="nw")
	canvas_a.configure(yscrollcommand=scrollbar.set)

	canvas_a.pack(side="left", fill="both", expand=True)
	scrollbar.pack(side="right", fill="y")
	build_decoded_anamnesis(scrollable_frame)
	
	build_anamnesis_tab(notebook)


	root.mainloop()


if __name__ == "__main__":
	create_admin_gui()

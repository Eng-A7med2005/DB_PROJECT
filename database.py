import sqlite3
import os
import pandas as pd
from datetime import datetime

# Database file path
DB_FILE = "medical_records.db"

def init_db():
    """Initialize the database and create tables if they don't exist"""
    # Create the database directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_FILE) if os.path.dirname(DB_FILE) else '.', exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create patients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        date_of_birth TEXT,
        gender TEXT,
        phone TEXT,
        address TEXT,
        registration_date TEXT
    )
    ''')
    
    # Create medical records table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medical_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        record_date TEXT NOT NULL,
        blood_pressure TEXT,
        glucose_level REAL,
        temperature REAL,
        notes TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    # Create files table to store file paths
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        upload_date TEXT NOT NULL,
        file_type TEXT,
        description TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Create directory for patient files
    os.makedirs("patient_files", exist_ok=True)

def add_patient(national_id, name, date_of_birth=None, gender=None, phone=None, address=None):
    """Add a new patient to the database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        registration_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO patients (national_id, name, date_of_birth, gender, phone, address, registration_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (national_id, name, date_of_birth, gender, phone, address, registration_date)
        )
        conn.commit()
        patient_id = cursor.lastrowid
        conn.close()
        return {"success": True, "patient_id": patient_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "Patient with this national ID already exists"}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}

def get_patient_by_national_id(national_id):
    """Get patient details by national ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM patients WHERE national_id = ?", (national_id,))
    patient = cursor.fetchone()
    
    if patient:
        columns = [desc[0] for desc in cursor.description]
        patient_dict = dict(zip(columns, patient))
        conn.close()
        return {"success": True, "patient": patient_dict}
    else:
        conn.close()
        return {"success": False, "error": "Patient not found"}

def get_all_patients():
    """Get all patients"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, national_id, name, date_of_birth, gender, phone FROM patients ORDER BY name", conn)
    conn.close()
    return df

def add_medical_record(patient_id, blood_pressure=None, glucose_level=None, temperature=None, notes=None):
    """Add a new medical record for a patient"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        record_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Handle empty values properly
        if glucose_level == 0:
            glucose_level = None
        if temperature == 37.0:  # Default value
            temperature = None
            
        cursor.execute(
            "INSERT INTO medical_records (patient_id, record_date, blood_pressure, glucose_level, temperature, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, record_date, blood_pressure, glucose_level, temperature, notes)
        )
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        return {"success": True, "record_id": record_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}

def get_patient_medical_records(patient_id):
    """Get all medical records for a patient"""
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(
            "SELECT id, record_date, blood_pressure, glucose_level, temperature, notes FROM medical_records WHERE patient_id = ? ORDER BY record_date DESC",
            conn, params=(patient_id,)
        )
        conn.close()
        return df
    except Exception as e:
        conn.close()
        print(f"Error fetching medical records: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error

def save_patient_file(patient_id, uploaded_file, description=None):
    """Save uploaded file information to database and file to disk"""
    try:
        # Create directory for patient files if it doesn't exist
        os.makedirs("patient_files", exist_ok=True)
        patient_dir = f"patient_files/patient_{patient_id}"
        os.makedirs(patient_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1] if "." in file_name else ""
        safe_filename = f"{timestamp}_{file_name}"
        file_path = f"{patient_dir}/{safe_filename}"
        
        # Debug print
        print(f"Attempting to save file to: {file_path}")
        
        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Verify file was saved
        if not os.path.exists(file_path):
            print(f"Error: File was not saved to {file_path}")
            return {"success": False, "error": "File could not be saved to disk"}
        
        # Save file information to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO patient_files (patient_id, file_name, file_path, upload_date, file_type, description) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, file_name, file_path, upload_date, file_type, description)
        )
        conn.commit()
        file_id = cursor.lastrowid
        conn.close()
        
        print(f"File saved successfully with ID: {file_id}")
        return {"success": True, "file_id": file_id, "file_path": file_path}
    except Exception as e:
        print(f"Error saving file: {str(e)}")
        return {"success": False, "error": str(e)}

def get_patient_files(patient_id):
    """Get all files for a patient"""
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query(
            "SELECT id, file_name, file_path, upload_date, file_type, description FROM patient_files WHERE patient_id = ? ORDER BY upload_date DESC",
            conn, params=(patient_id,)
        )
        conn.close()
        return df
    except Exception as e:
        conn.close()
        print(f"Error fetching patient files: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error
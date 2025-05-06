import sqlite3
import os
import pandas as pd
from datetime import datetime
import traceback

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
    
    # Create files_blob table to store file content in DB (alternative method)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS patient_files_blob (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        file_type TEXT,
        file_content BLOB,
        upload_date TEXT NOT NULL,
        description TEXT,
        file_size INTEGER,
        FOREIGN KEY (patient_id) REFERENCES patients (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Create directory for patient files
    os.makedirs("patient_files", exist_ok=True)

def ensure_patient_directory(patient_id):
    """
    Ensure patient directory exists, create it if it doesn't
    """
    try:
        # Get current directory
        current_dir = os.getcwd()
        
        # Create main patient_files directory if it doesn't exist
        patient_files_dir = os.path.join(current_dir, "patient_files")
        if not os.path.exists(patient_files_dir):
            os.makedirs(patient_files_dir)
            print(f"Created main directory: {patient_files_dir}")
        
        # Create specific patient directory
        patient_dir = os.path.join(patient_files_dir, f"patient_{patient_id}")
        if not os.path.exists(patient_dir):
            os.makedirs(patient_dir)
            print(f"Created patient directory: {patient_dir}")
        
        return patient_dir
    except Exception as e:
        print(f"Error creating patient directory: {str(e)}")
        return None

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
        
        # Create directory for the new patient
        ensure_patient_directory(patient_id)
        
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
        
        # Ensure patient directory exists
        ensure_patient_directory(patient_dict["id"])
        
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
        # 1. Ensure patient directory exists
        current_dir = os.getcwd()
        patient_dir = os.path.join(current_dir, "patient_files", f"patient_{patient_id}")
        os.makedirs(patient_dir, exist_ok=True)
        
        # 2. Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1] if "." in file_name else ""
        safe_filename = f"{timestamp}_{file_name}"
        file_path = os.path.join(patient_dir, safe_filename)
        
        # 3. Write file to disk
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 4. Verify file was created
        if os.path.exists(file_path):
            # 5. Save file information to database
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO patient_files (patient_id, file_name, file_path, upload_date, file_type, description) VALUES (?, ?, ?, ?, ?, ?)",
                (patient_id, file_name, file_path, upload_date, file_type, description)
            )
            conn.commit()
            file_id = cursor.lastrowid
            conn.close()
            
            return {"success": True, "file_id": file_id, "file_path": file_path}
        else:
            return {"success": False, "error": "File was not saved to disk properly"}
    
    except Exception as e:
        print(f"Exception in save_patient_file: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def get_patient_files(patient_id):
    """Get all files for a patient"""
    # Ensure patient directory exists
    patient_dir = ensure_patient_directory(patient_id)
    
    conn = sqlite3.connect(DB_FILE)
    try:
        # Get files from database
        df = pd.read_sql_query(
            "SELECT id, file_name, file_path, upload_date, file_type, description FROM patient_files WHERE patient_id = ? ORDER BY upload_date DESC",
            conn, params=(patient_id,)
        )
        conn.close()
        return df
    except Exception as e:
        conn.close()
        print(f"Error fetching patient files: {e}")
        print(traceback.format_exc())
        return pd.DataFrame()  # Return empty DataFrame on error

# وظائف التصحيح

def debug_database():
    """وظيفة للتحقق من حالة قاعدة البيانات وعرض جميع البيانات الموجودة"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # التحقق من وجود الجداول
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("الجداول الموجودة في قاعدة البيانات:")
    for table in tables:
        print(f"- {table[0]}")
    
    # عرض بيانات المرضى
    print("\nبيانات المرضى:")
    try:
        cursor.execute("SELECT id, national_id, name FROM patients")
        patients = cursor.fetchall()
        if patients:
            for p in patients:
                print(f"المريض ID: {p[0]}, الرقم الوطني: {p[1]}, الاسم: {p[2]}")
        else:
            print("لا يوجد مرضى في قاعدة البيانات")
    except Exception as e:
        print(f"خطأ في استعلام بيانات المرضى: {str(e)}")
    
    # عرض السجلات الطبية
    print("\nالسجلات الطبية:")
    try:
        cursor.execute("SELECT id, patient_id, record_date FROM medical_records")
        records = cursor.fetchall()
        if records:
            for r in records:
                print(f"سجل ID: {r[0]}, المريض ID: {r[1]}, التاريخ: {r[2]}")
        else:
            print("لا توجد سجلات طبية في قاعدة البيانات")
    except Exception as e:
        print(f"خطأ في استعلام السجلات الطبية: {str(e)}")
    
    # عرض ملفات المرضى
    print("\nملفات المرضى:")
    try:
        cursor.execute("SELECT id, patient_id, file_name, file_path FROM patient_files")
        files = cursor.fetchall()
        if files:
            for f in files:
                print(f"ملف ID: {f[0]}, المريض ID: {f[1]}, اسم الملف: {f[2]}")
                print(f"  مسار الملف: {f[3]}")
                print(f"  الملف موجود: {os.path.exists(f[3])}")
        else:
            print("لا توجد ملفات مرضى في قاعدة البيانات")
    except Exception as e:
        print(f"خطأ في استعلام ملفات المرضى: {str(e)}")
    
    # عرض محتويات جدول patient_files_blob إذا كان موجوداً
    print("\nملفات المرضى في BLOB:")
    try:
        cursor.execute("SELECT id, patient_id, file_name, file_size FROM patient_files_blob")
        blobs = cursor.fetchall()
        if blobs:
            for b in blobs:
                print(f"ملف BLOB ID: {b[0]}, المريض ID: {b[1]}, اسم الملف: {b[2]}, الحجم: {b[3]} بايت")
        else:
            print("لا توجد ملفات BLOB في قاعدة البيانات")
    except sqlite3.OperationalError:
        print("جدول patient_files_blob غير موجود")
    except Exception as e:
        print(f"خطأ في استعلام BLOB: {str(e)}")
    
    conn.close()
    
    return "تم عرض معلومات التصحيح في سجل التطبيق"

def save_patient_file_debug(patient_id, uploaded_file, description=None):
    """حفظ معلومات الملف المرفوع إلى قاعدة البيانات والملف إلى القرص مع تصحيح مفصل"""
    try:
        # 1. طباعة معلومات مفصلة عن الملف المرفوع
        print(f"معلومات الملف المرفوع:")
        print(f"الاسم: {uploaded_file.name}")
        print(f"النوع: {uploaded_file.type}")
        print(f"الحجم: {uploaded_file.size} بايت")
        
        # 2. التأكد من وجود دليل المريض
        current_dir = os.getcwd()
        print(f"الدليل الحالي: {current_dir}")
        
        patient_files_dir = os.path.join(current_dir, "patient_files")
        os.makedirs(patient_files_dir, exist_ok=True)
        print(f"دليل ملفات المرضى: {patient_files_dir}")
        
        patient_dir = os.path.join(patient_files_dir, f"patient_{patient_id}")
        os.makedirs(patient_dir, exist_ok=True)
        print(f"دليل المريض: {patient_dir}")
        
        # 3. إنشاء اسم ملف فريد مع الطابع الزمني
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1] if "." in file_name else ""
        safe_filename = f"{timestamp}_{file_name}"
        file_path = os.path.join(patient_dir, safe_filename)
        print(f"مسار الملف المستهدف: {file_path}")
        
        # 4. قراءة محتوى الملف في الذاكرة أولاً
        file_content = uploaded_file.getbuffer()
        print(f"تمت قراءة {len(file_content)} بايت في الذاكرة")
        
        # 5. كتابة الملف إلى القرص باستخدام نهج بسيط أولاً
        with open(file_path, "wb") as f:
            f.write(file_content)
            print(f"تمت كتابة محتوى الملف إلى القرص")
        
        # 6. التحقق من إنشاء الملف
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"الملف موجود على القرص بحجم: {file_size} بايت")
            
            if file_size != len(file_content):
                print(f"تحذير: عدم تطابق حجم الملف. المتوقع {len(file_content)} بايت، تم الحصول على {file_size} بايت")
        else:
            print(f"خطأ: لم يتم إنشاء الملف في {file_path}")
            return {"success": False, "error": "لم يتم حفظ الملف على القرص بشكل صحيح"}
        
        # 7. حفظ معلومات الملف في قاعدة البيانات
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            "INSERT INTO patient_files (patient_id, file_name, file_path, upload_date, file_type, description) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, file_name, file_path, upload_date, file_type, description)
        )
        conn.commit()
        file_id = cursor.lastrowid
        
        # التحقق من إدخال السجل
        cursor.execute("SELECT * FROM patient_files WHERE id = ?", (file_id,))
        record = cursor.fetchone()
        if record:
            print(f"تم إدخال السجل في قاعدة البيانات، التحقق من وجوده:")
            print(f"السجل: {record}")
        else:
            print(f"تحذير: لم يتم العثور على السجل بعد الإدخال!")
            
        conn.close()
        
        print(f"تم حفظ سجل الملف في قاعدة البيانات بمعرف: {file_id}")
        print(f"الملفات في دليل المريض بعد الحفظ: {os.listdir(patient_dir)}")
        
        return {"success": True, "file_id": file_id, "file_path": file_path}
    
    except Exception as e:
        print(f"استثناء في save_patient_file: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def get_patient_files_debug(patient_id):
    """الحصول على جميع ملفات المريض مع معلومات تصحيح مفصلة"""
    # ضمان وجود دليل المريض
    patient_dir = os.path.join(os.getcwd(), "patient_files", f"patient_{patient_id}")
    print(f"التحقق من دليل المريض: {patient_dir}")
    print(f"دليل المريض موجود: {os.path.exists(patient_dir)}")
    
    if os.path.exists(patient_dir):
        print(f"محتويات دليل المريض: {os.listdir(patient_dir)}")
    
    conn = sqlite3.connect(DB_FILE)
    try:
        # الحصول على الملفات من قاعدة البيانات
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_files WHERE patient_id = ?", (patient_id,))
        records = cursor.fetchall()
        print(f"تم العثور على {len(records)} سجل(سجلات) في جدول patient_files للمريض {patient_id}")
        
        if records:
            # عرض السجلات في وحدة التحكم للتصحيح
            print("سجلات الملفات في قاعدة البيانات:")
            for record in records:
                print(f"  ID: {record[0]}, الاسم: {record[2]}, المسار: {record[3]}")
                print(f"  الملف موجود: {os.path.exists(record[3])}")
        
        df = pd.read_sql_query(
            "SELECT id, file_name, file_path, upload_date, file_type, description FROM patient_files WHERE patient_id = ? ORDER BY upload_date DESC",
            conn, params=(patient_id,)
        )
        conn.close()
        
        # التحقق من كل ملف موجود
        if not df.empty:
            for i, row in df.iterrows():
                path = row['file_path']
                exists = os.path.exists(path)
                print(f"ملف {i+1}: {path} - موجود: {exists}")
                
        return df
    except Exception as e:
        conn.close()
        print(f"خطأ في استرجاع ملفات المريض: {e}")
        print(traceback.format_exc())
        return pd.DataFrame()  # إرجاع DataFrame فارغ عند وجود خطأ

# وظيفة لتخزين الملفات في قاعدة البيانات كـ BLOB
def save_file_to_blob(patient_id, uploaded_file, description=None):
    """حفظ الملف مباشرة في قاعدة البيانات كـ BLOB"""
    try:
        # قراءة محتوى الملف
        file_content = uploaded_file.getbuffer()
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1] if "." in file_name else ""
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_size = len(file_content)
        
        print(f"حفظ الملف في قاعدة البيانات: {file_name}، الحجم: {file_size} بايت")
        
        # إنشاء اتصال بقاعدة البيانات
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # إدخال الملف في قاعدة البيانات
        cursor.execute(
            "INSERT INTO patient_files_blob (patient_id, file_name, file_type, file_content, upload_date, description, file_size) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (patient_id, file_name, file_type, file_content, upload_date, description, file_size)
        )
        
        conn.commit()
        file_id = cursor.lastrowid
        conn.close()
        
        print(f"تم حفظ الملف في قاعدة البيانات بمعرف: {file_id}")
        
        return {"success": True, "file_id": file_id}
    except Exception as e:
        print(f"خطأ في حفظ الملف في قاعدة البيانات: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def get_blob_files(patient_id):
    """استرجاع قائمة ملفات المريض من قاعدة البيانات BLOB"""
    conn = sqlite3.connect(DB_FILE)
    try:
        # استرجاع معلومات الملفات (بدون محتوى الملفات)
        df = pd.read_sql_query(
            "SELECT id, file_name, file_type, upload_date, description, file_size FROM patient_files_blob WHERE patient_id = ? ORDER BY upload_date DESC",
            conn, params=(patient_id,)
        )
        conn.close()
        
        print(f"تم العثور على {len(df)} ملف(ملفات) في قاعدة البيانات BLOB للمريض {patient_id}")
        return df
    except Exception as e:
        conn.close()
        print(f"خطأ في استرجاع ملفات المريض من قاعدة البيانات BLOB: {e}")
        print(traceback.format_exc())
        return pd.DataFrame()  # إرجاع DataFrame فارغ عند وجود خطأ

def get_blob_content(file_id):
    """استرجاع محتوى ملف محدد من قاعدة البيانات BLOB"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # استرجاع محتوى الملف ومعلوماته
        cursor.execute(
            "SELECT file_name, file_type, file_content FROM patient_files_blob WHERE id = ?",
            (file_id,)
        )
        
        file_data = cursor.fetchone()
        conn.close()
        
        if file_data:
            return {
                "success": True,
                "file_name": file_data[0],
                "file_type": file_data[1],
                "file_content": file_data[2]
            }
        else:
            return {"success": False, "error": "الملف غير موجود"}
    except Exception as e:
        print(f"خطأ في استرجاع محتوى الملف: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}
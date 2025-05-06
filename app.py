import streamlit as st
import pandas as pd
import os
import base64
import traceback
from datetime import datetime
from datetime import date
import sqlite3
from database import (
    init_db, add_patient, get_patient_by_national_id, get_all_patients,
    add_medical_record, get_patient_medical_records, get_patient_files,
    save_patient_file, debug_database, save_patient_file_debug, get_patient_files_debug
)

# Database file path
DB_FILE = "medical_records.db"

# Initialize the database
init_db()

# Session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'current_patient_id' not in st.session_state:
    st.session_state.current_patient_id = None

# Login function
def login():
    st.title("Medical Records System - Login")
    
    # Simple authentication
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    # For demo purposes, use simple credentials
    if st.button("Login"):
        if username == "doctor" and password == "password":
            st.session_state.authenticated = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password")

# Main application
def main_app():
    st.title("Medical Records Management System")
    
    # Sidebar menu
    menu = st.sidebar.selectbox(
        "Menu", 
        ["Home", "Add Patient", "Search Patient", "View All Patients", "File Upload Test", "Debug"]
    )
    
    # Add logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
    
    if menu == "Home":
        home_page()
    elif menu == "Add Patient":
        add_patient_page()
    elif menu == "Search Patient":
        search_patient_page()
    elif menu == "View All Patients":
        view_all_patients_page()
    elif menu == "File Upload Test":
        file_upload_test_page()
    elif menu == "Debug":
        debug_app_page()

def file_upload_test_page():
    st.title("File Upload Test")
   
    # Display current directory
    current_dir = os.getcwd()
    st.write(f"Current Directory: {current_dir}")
   
    # Upload file
    uploaded_file = st.file_uploader("Choose a file to upload", type=["jpg", "jpeg", "png", "pdf", "txt", "doc", "docx"])
   
    if uploaded_file is not None:
        st.write("File details:")
        st.json({
            "Name": uploaded_file.name,
            "Type": uploaded_file.type,
            "Size": uploaded_file.size
        })
        
        # Show preview for images
        if uploaded_file.type.startswith('image'):
            st.image(uploaded_file, width=200, caption="Preview")
       
       
        # Save file button
        if st.button("Save File to Database"):
            try:
                # Use the debug version of save_patient_file
                result = save_patient_file_debug(1, uploaded_file)  # Using patient_id=1 for testing
                
                if result["success"]:
                    st.success(f"File saved successfully to database! ID: {result.get('file_id', '')}")
                    
                    # Show image if it's an image
                    if uploaded_file.type.startswith('image'):
                        st.image(uploaded_file, width=300, caption="Uploaded image")
                else:
                    st.error(f"Failed to save file: {result.get('error', 'Unknown error')}")
           
            except Exception as e:
                st.error(f"Error while saving file: {str(e)}")
                st.code(traceback.format_exc())

def home_page():
    st.header("Welcome to Medical Records Management System")
    st.write("This application helps doctors manage patient medical records.")
    st.write("Use the sidebar menu to navigate through different features.")
    
    # Today's stats
    st.subheader("Today's Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            patients_df = get_all_patients()
            st.metric(label="Total Patients", value=len(patients_df))
        except Exception as e:
            st.error(f"Error loading statistics: {str(e)}")
            st.metric(label="Total Patients", value="Error")
    
    # Display last 5 added patients
    st.subheader("Recently Added Patients")
    try:
        patients_df = get_all_patients()
        if not patients_df.empty:
            st.dataframe(patients_df.head(5))
        else:
            st.info("No patients registered yet.")
    except Exception as e:
        st.error(f"Error loading patients: {str(e)}")

def add_patient_page():
    st.header("Add New Patient")
    
    # Form to add a new patient
    with st.form("add_patient_form"):
        national_id = st.text_input("National ID (Required)")
        name = st.text_input("Full Name (Required)")
        date_of_birth = st.date_input("Date of Birth", value=None, min_value=date(1950, 1, 1), max_value=date.today())
        gender = st.selectbox("Gender", ["", "Male", "Female", "Other"])
        phone = st.text_input("Phone Number")
        address = st.text_area("Address")
        
        submit_button = st.form_submit_button("Add Patient")
        
        if submit_button:
            if not national_id or not name:
                st.error("National ID and Full Name are required.")
            else:
                try:
                    dob_str = date_of_birth.strftime("%Y-%m-%d") if date_of_birth else None
                    result = add_patient(national_id, name, dob_str, gender, phone, address)
                    
                    if result["success"]:
                        st.success(f"Patient {name} added successfully!")
                        st.session_state.current_patient_id = result["patient_id"]
                        # Store the national ID in session state for later use
                        st.session_state.last_added_national_id = national_id
                    else:
                        st.error(f"Error: {result['error']}")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error(traceback.format_exc())
    
    # Add a button outside the form to navigate to the patient's records
    if 'last_added_national_id' in st.session_state:
        if st.button("View Medical Records for Last Added Patient"):
            try:
                patient_result = get_patient_by_national_id(st.session_state.last_added_national_id)
                if patient_result["success"]:
                    st.session_state.current_patient_id = patient_result["patient"]["id"]
                    st.session_state.current_view = "Search Patient"
                    st.rerun()
                else:
                    st.error(patient_result["error"])
            except Exception as e:
                st.error(f"Error retrieving patient: {str(e)}")

# قم بتعديل وظيفة البحث كاملة لتحسين تجربة المستخدم

def search_patient_page():
    st.header("Search Patient")
    
    # حفظ معرف المريض في حالة الجلسة إذا كان موجودًا
    if 'current_search_patient_id' not in st.session_state:
        st.session_state.current_search_patient_id = None
        st.session_state.current_search_patient = None
    
    # مربع إدخال للبحث عن الرقم الوطني
    national_id = st.text_input("Enter National ID")
    
    # زر البحث
    search_button = st.button("Search")
    
    # عندما يتم الضغط على زر البحث وإدخال الرقم الوطني
    if search_button and national_id:
        try:
            result = get_patient_by_national_id(national_id)
            
            if result["success"]:
                patient = result["patient"]
                # حفظ بيانات المريض في حالة الجلسة
                st.session_state.current_search_patient = patient
                st.session_state.current_search_patient_id = patient["id"]
                st.session_state.current_patient_id = patient["id"]  # للتوافق مع بقية التطبيق
            else:
                st.error(result["error"])
        except Exception as e:
            st.error(f"Error searching for patient: {str(e)}")
            st.error(traceback.format_exc())
    
    # عرض بيانات المريض إذا كان موجودًا في حالة الجلسة
    if st.session_state.current_search_patient:
        patient = st.session_state.current_search_patient
        
        # عرض تفاصيل المريض
        st.subheader("Patient Information")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Name:** {patient['name']}")
            st.write(f"**National ID:** {patient['national_id']}")
            st.write(f"**Date of Birth:** {patient['date_of_birth'] if patient['date_of_birth'] else 'Not provided'}")
        
        with col2:
            st.write(f"**Gender:** {patient['gender'] if patient['gender'] else 'Not provided'}")
            st.write(f"**Phone:** {patient['phone'] if patient['phone'] else 'Not provided'}")
            st.write(f"**Registered:** {patient['registration_date']}")
        
        st.write(f"**Address:** {patient['address'] if patient['address'] else 'Not provided'}")
        
        # علامات تبويب للسجلات الطبية والملفات
        tab1, tab2, tab3 = st.tabs(["Medical Records", "Files", "Add New Data"])
        
        with tab1:
            display_medical_records(patient["id"])
        
        with tab2:
            display_patient_files_improved(patient["id"])
        
        with tab3:
            add_patient_data_improved(patient["id"])

def display_medical_records(patient_id):
    st.subheader("Medical Records")
    
    try:
        records_df = get_patient_medical_records(patient_id)
        
        if not records_df.empty:
            # Add a column for showing detailed view
            for i, record in records_df.iterrows():
                st.write(f"**Date:** {record['record_date']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"Blood Pressure: {record['blood_pressure'] if record['blood_pressure'] else 'Not recorded'}")
                with col2:
                    st.write(f"Glucose: {record['glucose_level'] if not pd.isna(record['glucose_level']) else 'Not recorded'} mg/dL")
                with col3:
                    st.write(f"Temperature: {record['temperature'] if not pd.isna(record['temperature']) else 'Not recorded'} °C")
                
                st.write(f"Notes: {record['notes'] if record['notes'] else 'No notes'}")
                st.divider()
        else:
            st.info("No medical records found for this patient.")
    except Exception as e:
        st.error(f"Error displaying medical records: {str(e)}")
        st.error(traceback.format_exc())

def display_patient_files_improved(patient_id):
    """عرض ملفات المريض مع تحسينات"""
    st.subheader("Patient Files")
    
    try:
        # استخدام وظيفة التصحيح لاسترجاع الملفات
        files_df = get_patient_files_debug(patient_id)
        
        if not files_df.empty:
            st.success(f"Found {len(files_df)} file(s) for patient ID: {patient_id}")
            
            # عرض جدول الملفات
            st.dataframe(files_df)
            
            # إنشاء قائمة منسدلة لاختيار ملف للعرض/التنزيل
            if "file_name" in files_df.columns and len(files_df) > 0:
                file_options = files_df.apply(lambda row: f"{row['file_name']} (ID: {row['id']})", axis=1).tolist()
                selected_file = st.selectbox("Select a file to view/download", options=file_options, key=f"file_select_{patient_id}")
                
                if selected_file:
                    # استخراج معرف الملف من النص المحدد
                    file_id = int(selected_file.split("ID: ")[1].strip(")"))
                    selected_row = files_df[files_df['id'] == file_id].iloc[0]
                    
                    # للملفات المخزنة في نظام الملفات
                    file_path = selected_row['file_path']
                    
                    st.write(f"File path: {file_path}")
                    st.write(f"File exists: {os.path.exists(file_path)}")
                    
                    if os.path.exists(file_path):
                        # عرض الصور مباشرة
                        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            st.image(file_path, caption=selected_row['file_name'])
                        
                        # إضافة زر تنزيل للملف
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                            st.download_button(
                                label=f"Download {selected_row['file_name']}",
                                data=file_bytes,
                                file_name=selected_row['file_name'],
                                mime="application/octet-stream"
                            )
                    else:
                        st.error(f"File not found at: {file_path}")
        else:
            st.info("No files found for this patient.")
    except Exception as e:
        st.error(f"Error displaying patient files: {str(e)}")
        st.error(traceback.format_exc())


# تعديل وظيفة add_patient_data فقط
def add_patient_data_improved(patient_id):
    """وظيفة محسنة لإضافة بيانات المريض"""
    # علامات تبويب لإضافة أنواع مختلفة من البيانات
    data_tab1, data_tab2 = st.tabs(["Add Medical Record", "Upload File"])
    
    with data_tab1:
        st.subheader("Add Medical Record")
        
        with st.form(key=f"add_record_form_{patient_id}"):
            blood_pressure = st.text_input("Blood Pressure (e.g., 120/80)", key=f"bp_{patient_id}")
            glucose_level = st.number_input("Glucose Level (mg/dL)", min_value=0.0, format="%.1f", key=f"glucose_{patient_id}")
            temperature = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=37.0, format="%.1f", key=f"temp_{patient_id}")
            notes = st.text_area("Notes", key=f"notes_{patient_id}")
            
            submit_record = st.form_submit_button("Save Medical Record")
            
            if submit_record:
                try:
                    # التحقق من صحة وحفظ السجل الطبي
                    result = add_medical_record(
                        patient_id, 
                        blood_pressure=blood_pressure if blood_pressure else None,
                        glucose_level=glucose_level if glucose_level > 0 else None,
                        temperature=temperature if temperature > 30 else None,
                        notes=notes
                    )
                    
                    if result["success"]:
                        st.success("Medical record added successfully!")
                    else:
                        st.error(f"Error: {result['error']}")
                except Exception as e:
                    st.error(f"Error saving medical record: {str(e)}")
                    st.error(traceback.format_exc())
    
    with data_tab2:
        st.subheader("Upload Patient File")
        
        
        
        # تعامل خاص مع أداة رفع الملفات خارج النموذج
        uploaded_file = st.file_uploader("Choose a file to upload", 
                                        type=["jpg", "jpeg", "png", "pdf", "doc", "docx", "txt"], 
                                        key=f"file_upload_{patient_id}")
        
        # عرض معاينة الملف إذا تم تحديده
        if uploaded_file is not None:
            st.write("File details:")
            st.json({
                "Name": uploaded_file.name,
                "Type": uploaded_file.type,
                "Size": uploaded_file.size
            })
            
            # عرض معاينة للصور
            if uploaded_file.type.startswith('image'):
                st.image(uploaded_file, width=200, caption="Preview")
            
            # زر منفصل خارج النموذج لرفع الملف
            if st.button("Save Selected File", key=f"upload_button_{patient_id}"):
                try:
                    # استخدام وظيفة التصحيح لحفظ الملف
                    result = save_patient_file_debug(patient_id, uploaded_file)
                    
                    if result["success"]:
                        st.success(f"File uploaded successfully! ID: {result.get('file_id', 'N/A')}")
                        st.write(f"File path: {result.get('file_path', 'N/A')}")
                        
                        # عرض الصورة إذا كانت ملف صورة
                        if uploaded_file.type.startswith('image'):
                            st.image(result.get('file_path'), caption="Uploaded image")
                    else:
                        st.error(f"Failed to save file: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error while saving file: {str(e)}")
                    st.error(traceback.format_exc())

def view_all_patients_page():
    st.header("All Patients")
    
    try:
        patients_df = get_all_patients()
        
        if not patients_df.empty:
            st.dataframe(patients_df)
            
            # Allow searching for a specific patient from the list
            selected_patient = st.selectbox(
                "Select patient to view details",
                options=patients_df["national_id"].tolist(),
                format_func=lambda x: f"{patients_df[patients_df['national_id'] == x]['name'].values[0]} ({x})"
            )
            
            if st.button("View Selected Patient"):
                result = get_patient_by_national_id(selected_patient)
                if result["success"]:
                    st.session_state.current_patient_id = result["patient"]["id"]
                    st.session_state.current_view = "Search Patient"
                    st.rerun()
        else:
            st.info("No patients registered yet.")
    except Exception as e:
        st.error(f"Error viewing all patients: {str(e)}")
        st.error(traceback.format_exc())

def debug_app_page():
    st.title("Debug Page")
    
    st.write("Use this page to debug application and database status")
    
    # Button to check database
    if st.button("Check Database"):
        try:
            # Call debug function from database.py
            result = debug_database()
            st.success("Database check completed")
            st.info("Check console/logs for detailed results")
        except Exception as e:
            st.error(f"Error checking database: {str(e)}")
            st.code(traceback.format_exc())
    
    # Add test patient
    st.subheader("Add Test Patient")
    test_id = st.text_input("Test National ID", "TEST123")
    test_name = st.text_input("Test Name", "Test Patient")
    
    if st.button("Add Test Patient"):
        try:
            result = add_patient(test_id, test_name)
            if result["success"]:
                st.success(f"Test patient added successfully! ID: {result['patient_id']}")
                # Store patient ID in session state for later use
                st.session_state.test_patient_id = result["patient_id"]
            else:
                st.error(f"Failed to add test patient: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"Error adding test patient: {str(e)}")
            st.code(traceback.format_exc())
    
    # Add test medical record
    if 'test_patient_id' in st.session_state:
        st.subheader("Add Test Medical Record")
        st.write(f"Patient ID: {st.session_state.test_patient_id}")
        
        if st.button("Add Test Medical Record"):
            try:
                result = add_medical_record(
                    st.session_state.test_patient_id,
                    blood_pressure="120/80",
                    glucose_level=100.0,
                    temperature=37.0,
                    notes="Test record"
                )
                if result["success"]:
                    st.success(f"Test medical record added successfully! ID: {result['record_id']}")
                else:
                    st.error(f"Failed to add test medical record: {result.get('error', 'Unknown error')}")
            except Exception as e:
                st.error(f"Error adding test medical record: {str(e)}")
                st.code(traceback.format_exc())
    
    # Upload test file
    if 'test_patient_id' in st.session_state:
        st.subheader("Upload Test File")
        st.write(f"Patient ID: {st.session_state.test_patient_id}")
        
        uploaded_file = st.file_uploader("Choose a file to upload", type=["jpg", "jpeg", "png", "pdf", "txt"])
        
        if uploaded_file is not None:
            st.write("File details:")
            st.json({
                "Name": uploaded_file.name,
                "Type": uploaded_file.type,
                "Size": uploaded_file.size
            })
            
            if st.button("Upload Test File"):
                try:
                    # Use debug version of save_patient_file
                    result = save_patient_file_debug(st.session_state.test_patient_id, uploaded_file, "Test file")
                    
                    if result["success"]:
                        st.success(f"Test file uploaded successfully! ID: {result.get('file_id', 'N/A')}")
                        st.write(f"File path: {result.get('file_path', 'N/A')}")
                        st.write(f"File exists: {os.path.exists(result.get('file_path', ''))}")
                        
                        # Display image if it's an image
                        if uploaded_file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                            st.image(result.get('file_path'), caption="Uploaded image")
                    else:
                        st.error(f"Failed to upload test file: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error uploading test file: {str(e)}")
                    st.code(traceback.format_exc())
    
    # View patient files
    if 'test_patient_id' in st.session_state:
        st.subheader("View Patient Files")
        st.write(f"Patient ID: {st.session_state.test_patient_id}")
        
        if st.button("View Patient Files"):
            try:
                # Use debug version of get_patient_files
                files_df = get_patient_files_debug(st.session_state.test_patient_id)
                
                if not files_df.empty:
                    st.success(f"Found {len(files_df)} file(s)")
                    st.dataframe(files_df)
                else:
                    st.info("No files found for this patient")
            except Exception as e:
                st.error(f"Error viewing patient files: {str(e)}")
                st.code(traceback.format_exc())

# Run the app
if __name__ == "__main__":
    try:
        if st.session_state.authenticated:
            main_app()
        else:
            login()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error(traceback.format_exc())

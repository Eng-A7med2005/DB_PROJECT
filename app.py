import streamlit as st
import pandas as pd
import os
import base64
import traceback
from database import (
    init_db, add_patient, get_patient_by_national_id, get_all_patients,
    add_medical_record, get_patient_medical_records, save_patient_file, get_patient_files
)
from datetime import datetime

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
        ["Home", "Add Patient", "Search Patient", "View All Patients"]
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
        date_of_birth = st.date_input("Date of Birth", value=None)
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

def search_patient_page():
    st.header("Search Patient")
    
    # Search by national ID
    national_id = st.text_input("Enter National ID")
    
    if st.button("Search") and national_id:
        try:
            result = get_patient_by_national_id(national_id)
            
            if result["success"]:
                patient = result["patient"]
                st.session_state.current_patient_id = patient["id"]
                
                # Display patient details
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
                
                # Tabs for medical records and files
                tab1, tab2, tab3 = st.tabs(["Medical Records", "Files", "Add New Data"])
                
                with tab1:
                    display_medical_records(patient["id"])
                
                with tab2:
                    display_patient_files(patient["id"])
                
                with tab3:
                    add_patient_data(patient["id"])
            else:
                st.error(result["error"])
        except Exception as e:
            st.error(f"Error searching for patient: {str(e)}")
            st.error(traceback.format_exc())

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

def display_patient_files(patient_id):
    st.subheader("Patient Files")
    
    try:
        files_df = get_patient_files(patient_id)
        
        if not files_df.empty:
            for i, file in files_df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{file['file_name']}**")
                    st.write(f"Uploaded: {file['upload_date']}")
                    if file['description']:
                        st.write(f"Description: {file['description']}")
                
                with col2:
                    file_path = file['file_path']
                    if os.path.exists(file_path):
                        file_extension = file['file_type'].lower() if file['file_type'] else ""
                        
                        if file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                            st.image(file_path, width=100)
                        elif file_extension in ['pdf']:
                            st.write("PDF File")
                        else:
                            st.write(f"{file_extension.upper()} File")
                    else:
                        st.error(f"File not found at path: {file_path}")
                
                with col3:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                            b64 = base64.b64encode(file_bytes).decode()
                            href = f'<a href="data:application/octet-stream;base64,{b64}" download="{file["file_name"]}">Download</a>'
                            st.markdown(href, unsafe_allow_html=True)
                
                st.divider()
        else:
            st.info("No files found for this patient.")
    except Exception as e:
        st.error(f"Error displaying patient files: {str(e)}")
        st.error(traceback.format_exc())

def add_patient_data(patient_id):
    # Tabs for adding different types of data
    data_tab1, data_tab2 = st.tabs(["Add Medical Record", "Upload File"])
    
    with data_tab1:
        st.subheader("Add Medical Record")
        
        with st.form(key="add_record_form"):
            blood_pressure = st.text_input("Blood Pressure (e.g., 120/80)")
            glucose_level = st.number_input("Glucose Level (mg/dL)", min_value=0.0, format="%.1f")
            temperature = st.number_input("Temperature (°C)", min_value=30.0, max_value=45.0, value=37.0, format="%.1f")
            notes = st.text_area("Notes")
            
            submit_record = st.form_submit_button("Save Medical Record")
            
            if submit_record:
                try:
                    # Validate and save the medical record
                    result = add_medical_record(
                        patient_id, 
                        blood_pressure=blood_pressure if blood_pressure else None,
                        glucose_level=glucose_level if glucose_level > 0 else None,
                        temperature=temperature if temperature > 30 else None,
                        notes=notes
                    )
                    
                    if result["success"]:
                        st.success("Medical record added successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result['error']}")
                except Exception as e:
                    st.error(f"Error saving medical record: {str(e)}")
                    st.error(traceback.format_exc())
    
    with data_tab2:
        st.subheader("Upload Patient File")
        
        with st.form(key="upload_file_form"):
            uploaded_file = st.file_uploader("Choose a file", type=["jpg", "jpeg", "png", "pdf", "doc", "docx"])
            file_description = st.text_area("File Description")
            
            submit_file = st.form_submit_button("Upload File")
            
            if submit_file and uploaded_file is not None:
                try:
                    # Save the file
                    result = save_patient_file(patient_id, uploaded_file, file_description)
                    
                    if result["success"]:
                        st.success("File uploaded successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {result['error']}")
                except Exception as e:
                    st.error(f"Error uploading file: {str(e)}")
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
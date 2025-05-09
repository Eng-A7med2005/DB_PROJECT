# 🏥 Medical Records Management System

## 📋 Overview
The Medical Records Management System is a web-based application built with Streamlit that allows healthcare providers to manage patient information, medical records, and associated files. The system provides a secure, user-friendly interface for storing and retrieving patient data, including medical history and file attachments.

## ✨ Features
* **🔐 User Authentication**: Secure login system for healthcare providers
* **👨‍👩‍👧‍👦 Patient Management**: Add, search, and view patient information
* **📝 Medical Records**: Create and manage patient medical records including:
   * 💉 Blood pressure
   * 🧪 Glucose levels
   * 🌡️ Temperature
   * 📋 Clinical notes
* **📁 File Management**: Upload, view, and download patient-related files
   * 🖼️ Supports multiple file formats (images, PDFs, documents)
   * 🔒 Secure storage with proper file organization
* **🛠️ Debugging Tools**: Built-in debugging features for troubleshooting

## 💻 System Requirements
* 🐍 Python 3.7 or higher
* 🗄️ SQLite database
* 📦 Required Python packages:
   * streamlit
   * pandas
   * sqlite3
   * pillow (for image processing)

## 💡 Usage Tips
1. **👤 Adding Patients**:
   * 🆔 National ID and Full Name are required fields
   * 📅 Date of Birth selector supports dates from 1950 to present

2. **📤 Uploading Files**:
   * 📄 Supported formats: JPG, JPEG, PNG, PDF, DOC, DOCX, TXT
   * 🏷️ File descriptions help organize and identify documents
   * 🗂️ All files are securely stored within the patient_files directory

3. **🔍 Viewing Patient Data**:
   * 🔎 Use "Search Patient" to find records by National ID
   * 📊 Use "View All Patients" to browse the complete patient list

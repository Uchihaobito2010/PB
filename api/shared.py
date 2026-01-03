import os
import json
import hashlib
import uuid
from datetime import datetime

# File paths
UPLOAD_FOLDER = 'uploads'
PASSWORD_FILE = 'passwords.json'
DATA_FILE = 'files.json'

# Ensure uploads directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def load_passwords():
    try:
        if os.path.exists(PASSWORD_FILE):
            with open(PASSWORD_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def save_passwords(passwords):
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(passwords, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_file_id():
    return str(uuid.uuid4())[:8]

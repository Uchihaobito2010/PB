import os
import uuid
import hashlib
from flask import Flask, request, render_template, send_file, redirect, url_for
from werkzeug.utils import secure_filename
import json
from datetime import datetime

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
PASSWORD_FILE = 'passwords.json'
DATA_FILE = 'files.json'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load existing data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_passwords():
    if os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

def save_passwords(passwords):
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(passwords, f)

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    
    # Check if it's a Python file
    if not file.filename.endswith('.py'):
        return 'Only Python files (.py) are allowed'
    
    # Generate unique ID
    file_id = str(uuid.uuid4())[:8]
    
    # Save the file
    original_filename = secure_filename(file.filename)
    save_filename = f"{file_id}_{original_filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
    file.save(file_path)
    
    # Get privacy settings
    is_private = request.form.get('is_private') == 'on'
    password = request.form.get('password', '')
    
    # Store file info
    files_data = load_data()
    passwords_data = load_passwords()
    
    files_data[file_id] = {
        'original_name': original_filename,
        'saved_name': save_filename,
        'upload_time': datetime.now().isoformat(),
        'is_private': is_private,
        'has_password': bool(password and is_private)
    }
    
    if is_private and password:
        passwords_data[file_id] = hash_password(password)
    
    save_data(files_data)
    save_passwords(passwords_data)
    
    # Generate URLs
    raw_url = url_for('raw_file', file_id=file_id, _external=True)
    execute_url = url_for('execute_file', file_id=file_id, _external=True)
    
    return render_template('result.html', 
                          raw_url=raw_url, 
                          execute_url=execute_url,
                          file_id=file_id,
                          is_private=is_private)

@app.route('/raw/<file_id>')
def raw_file(file_id):
    files_data = load_data()
    
    if file_id not in files_data:
        return 'File not found', 404
    
    file_info = files_data[file_id]
    
    # Check if private and password protected
    if file_info['is_private'] and file_info['has_password']:
        return '''
        <form method="POST" action="/auth/{}">
            <input type="password" name="password" placeholder="Enter password" required>
            <button type="submit">Access File</button>
        </form>
        '''.format(file_id)
    
    # Serve the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['saved_name'])
    
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/plain'}
    
    return 'File not found', 404

@app.route('/auth/<file_id>', methods=['POST'])
def authenticate(file_id):
    password = request.form.get('password', '')
    passwords_data = load_passwords()
    
    if file_id in passwords_data:
        hashed_input = hash_password(password)
        if passwords_data[file_id] == hashed_input:
            # Store authenticated session (simplified version)
            files_data = load_data()
            file_info = files_data[file_id]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['saved_name'])
            
            with open(file_path, 'r') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/plain'}
    
    return 'Invalid password', 403

@app.route('/execute/<file_id>')
def execute_file(file_id):
    files_data = load_data()
    
    if file_id not in files_data:
        return 'File not found', 404
    
    file_info = files_data[file_id]
    
    # Check if private and password protected
    if file_info['is_private'] and file_info['has_password']:
        return '''
        <form method="POST" action="/execute_auth/{}">
            <input type="password" name="password" placeholder="Enter password" required>
            <button type="submit">Execute File</button>
        </form>
        '''.format(file_id)
    
    # Execute the file
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['saved_name'])
    
    if os.path.exists(file_path):
        import subprocess
        try:
            result = subprocess.run(['python', file_path], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            output = f"Exit Code: {result.returncode}\n\n"
            output += "STDOUT:\n" + result.stdout + "\n\n"
            output += "STDERR:\n" + result.stderr
            return f'<pre>{output}</pre>'
        except subprocess.TimeoutExpired:
            return 'Execution timed out'
    
    return 'File not found', 404

@app.route('/execute_auth/<file_id>', methods=['POST'])
def execute_auth(file_id):
    password = request.form.get('password', '')
    passwords_data = load_passwords()
    
    if file_id in passwords_data:
        hashed_input = hash_password(password)
        if passwords_data[file_id] == hashed_input:
            # Execute the file
            files_data = load_data()
            file_info = files_data[file_id]
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_info['saved_name'])
            
            if os.path.exists(file_path):
                import subprocess
                try:
                    result = subprocess.run(['python', file_path], 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=10)
                    output = f"Exit Code: {result.returncode}\n\n"
                    output += "STDOUT:\n" + result.stdout + "\n\n"
                    output += "STDERR:\n" + result.stderr
                    return f'<pre>{output}</pre>'
                except subprocess.TimeoutExpired:
                    return 'Execution timed out'
    
    return 'Invalid password', 403

@app.route('/update/<file_id>', methods=['POST'])
def update_file(file_id):
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    
    # Check if it's a Python file
    if not file.filename.endswith('.py'):
        return 'Only Python files (.py) are allowed'
    
    # Check if file exists
    files_data = load_data()
    if file_id not in files_data:
        return 'File not found', 404
    
    # Check password if private
    file_info = files_data[file_id]
    if file_info['is_private'] and file_info['has_password']:
        password = request.form.get('password', '')
        passwords_data = load_passwords()
        
        if file_id not in passwords_data or \
           passwords_data[file_id] != hash_password(password):
            return 'Invalid password', 403
    
    # Update the file
    original_filename = secure_filename(file.filename)
    save_filename = f"{file_id}_{original_filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], save_filename)
    file.save(file_path)
    
    # Update file info
    files_data[file_id] = {
        'original_name': original_filename,
        'saved_name': save_filename,
        'upload_time': datetime.now().isoformat(),
        'is_private': file_info['is_private'],
        'has_password': file_info['has_password']
    }
    
    save_data(files_data)
    
    return 'File updated successfully!<br>Raw URL: {}'.format(
        url_for('raw_file', file_id=file_id, _external=True)
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

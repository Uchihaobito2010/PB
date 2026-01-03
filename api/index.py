from flask import Flask, request, jsonify, render_template_string
import os
import hashlib
import uuid
import base64
import subprocess
import json
from datetime import datetime
from pathlib import Path
import html

# Initialize Flask app
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'  # Use /tmp for Vercel serverless
PASSWORD_FILE = '/tmp/passwords.json'
DATA_FILE = '/tmp/files.json'

# Ensure tmp directory exists
os.makedirs('/tmp', exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize JSON files if they don't exist
for json_file in [PASSWORD_FILE, DATA_FILE]:
    if not os.path.exists(json_file):
        with open(json_file, 'w') as f:
            json.dump({}, f)

# Utility functions
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def load_passwords():
    try:
        with open(PASSWORD_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_passwords(passwords):
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(passwords, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_file_id():
    return str(uuid.uuid4())[:8]

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    import re
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    return filename[:100]

# HTML Templates
UPLOAD_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <title>🐍 Python Pastebin</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
        }
        input[type="file"], input[type="password"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            background: #0070f3;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
            margin-top: 20px;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .url-box {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
            margin: 10px 0;
            word-break: break-all;
            font-family: monospace;
        }
        .private-badge {
            background: #ff6b6b;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            display: inline-block;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐍 Python Pastebin on Vercel</h1>
        
        <form id="uploadForm">
            <div class="form-group">
                <label>Select Python File (.py):</label>
                <input type="file" id="fileInput" accept=".py" required>
            </div>
            
            <div class="form-group">
                <label>
                    <input type="checkbox" id="isPrivate"> Make Private (Password Protected)
                </label>
            </div>
            
            <div class="form-group" id="passwordField" style="display: none;">
                <label>Password:</label>
                <input type="password" id="password" placeholder="Enter password">
            </div>
            
            <button type="button" onclick="uploadFile()">Upload Python File</button>
        </form>
        
        <div id="result"></div>
    </div>
    
    <script>
        document.getElementById('isPrivate').addEventListener('change', function() {
            document.getElementById('passwordField').style.display = 
                this.checked ? 'block' : 'none';
        });
        
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const isPrivate = document.getElementById('isPrivate').checked;
            const password = document.getElementById('password').value;
            
            if (!fileInput.files[0]) {
                alert('Please select a Python file');
                return;
            }
            
            const file = fileInput.files[0];
            
            if (!file.name.endsWith('.py')) {
                alert('Only Python files (.py) are allowed');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = async function(e) {
                const content = e.target.result;
                const base64Content = btoa(unescape(encodeURIComponent(content)));
                
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        filename: file.name,
                        content: base64Content,
                        is_private: isPrivate,
                        password: password
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    const resultHTML = `
                        <div class="result">
                            <h3>✅ Upload Successful!</h3>
                            <p><strong>File ID:</strong> ${result.file_id}</p>
                            <p><strong>Filename:</strong> ${file.name}</p>
                            ${result.is_private ? '<span class="private-badge">🔒 PRIVATE</span>' : ''}
                            
                            <p><strong>📄 Raw URL:</strong></p>
                            <div class="url-box">
                                <a href="${result.raw_url}" target="_blank">${result.raw_url}</a>
                            </div>
                            
                            <p><strong>🚀 Execute URL:</strong></p>
                            <div class="url-box">
                                <a href="${result.execute_url}" target="_blank">${result.execute_url}</a>
                            </div>
                            
                            ${result.is_private ? 
                                '<p style="color: #ff6b6b;">🔒 Password protected - password required to access</p>' : 
                                ''
                            }
                        </div>
                    `;
                    
                    document.getElementById('result').innerHTML = resultHTML;
                } else {
                    document.getElementById('result').innerHTML = 
                        `<p style="color: red;">Error: ${result.error}</p>`;
                }
            };
            
            reader.readAsText(file);
        }
    </script>
</body>
</html>
'''

PASSWORD_FORM = '''
<!DOCTYPE html>
<html>
<head>
    <title>Password Required</title>
    <style>
        body { 
            font-family: Arial; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh;
            background: #f5f5f5;
        }
        .card {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        input, button {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
        }
        button {
            background: #0070f3;
            color: white;
            border: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>🔒 Password Required</h2>
        <p>This file is password protected.</p>
        <form method="GET" action="{{ action_url }}">
            <input type="hidden" name="file_id" value="{{ file_id }}">
            <input type="password" name="password" placeholder="Enter password" required>
            <button type="submit">Access</button>
        </form>
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def home():
    return render_template_string(UPLOAD_PAGE)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        filename = data.get('filename', '').strip()
        content = data.get('content', '').strip()
        is_private = data.get('is_private', False)
        password = data.get('password', '').strip()
        
        if not filename or not content:
            return jsonify({'error': 'Missing filename or content'}), 400
        
        if not filename.endswith('.py'):
            return jsonify({'error': 'Only Python files (.py) are allowed'}), 400
        
        # Sanitize filename
        filename = sanitize_filename(filename)
        
        # Generate unique ID
        file_id = generate_file_id()
        save_filename = f"{file_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, save_filename)
        
        # Decode and save file
        try:
            file_content = base64.b64decode(content)
        except:
            return jsonify({'error': 'Invalid file encoding'}), 400
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Store metadata
        files_data = load_data()
        passwords_data = load_passwords()
        
        files_data[file_id] = {
            'original_name': filename,
            'saved_name': save_filename,
            'upload_time': datetime.now().isoformat(),
            'is_private': is_private,
            'has_password': bool(password and is_private),
            'size_bytes': len(file_content)
        }
        
        if is_private and password:
            passwords_data[file_id] = hash_password(password)
        
        save_data(files_data)
        save_passwords(passwords_data)
        
        # Get base URL
        base_url = request.host_url.rstrip('/')
        
        response = {
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'raw_url': f"{base_url}/api/raw?file_id={file_id}",
            'execute_url': f"{base_url}/api/execute?file_id={file_id}",
            'is_private': is_private,
            'has_password': bool(password and is_private),
            'message': 'File uploaded successfully'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/raw')
def raw_file():
    try:
        file_id = request.args.get('file_id', '').strip()
        password = request.args.get('password', '').strip()
        
        if not file_id:
            return 'Missing file_id parameter', 400
        
        files_data = load_data()
        
        if file_id not in files_data:
            return 'File not found', 404
        
        file_info = files_data[file_id]
        
        # Check password if needed
        if file_info['is_private'] and file_info['has_password']:
            if not password:
                # Show password form
                return render_template_string(PASSWORD_FORM, 
                    file_id=file_id,
                    action_url=f"{request.path}?file_id={file_id}"
                )
            
            # Verify password
            passwords_data = load_passwords()
            if file_id not in passwords_data or \
               passwords_data[file_id] != hash_password(password):
                return 'Invalid password', 403
        
        # Serve the file
        file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        else:
            return 'File not found', 404
            
    except Exception as e:
        return f'Server error: {str(e)}', 500

@app.route('/api/execute')
def execute_file():
    try:
        file_id = request.args.get('file_id', '').strip()
        password = request.args.get('password', '').strip()
        
        if not file_id:
            return 'Missing file_id parameter', 400
        
        files_data = load_data()
        
        if file_id not in files_data:
            return 'File not found', 404
        
        file_info = files_data[file_id]
        
        # Check password if needed
        if file_info['is_private'] and file_info['has_password']:
            if not password:
                # Show password form
                return render_template_string(PASSWORD_FORM,
                    file_id=file_id,
                    action_url=f"{request.path}?file_id={file_id}"
                )
            
            # Verify password
            passwords_data = load_passwords()
            if file_id not in passwords_data or \
               passwords_data[file_id] != hash_password(password):
                return 'Invalid password', 403
        
        # Execute the file
        file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
        
        if os.path.exists(file_path):
            try:
                # Run Python file with timeout
                result = subprocess.run(
                    ['python', file_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    encoding='utf-8'
                )
                
                output = f"""=== Python Code Execution Result ===

File: {file_info['original_name']}
File ID: {file_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {'Success' if result.returncode == 0 else f'Failed (Code: {result.returncode})'}

=== STDOUT ===
{result.stdout}

=== STDERR ===
{result.stderr}
"""
                return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
                
            except subprocess.TimeoutExpired:
                return 'Execution timed out (10 seconds)', 200
            except Exception as e:
                return f'Execution error: {str(e)}', 200
        else:
            return 'File not found', 404
            
    except Exception as e:
        return f'Server error: {str(e)}', 500

@app.route('/api/update', methods=['POST'])
def update_file():
    try:
        file_id = request.args.get('file_id', '').strip()
        data = request.get_json()
        
        if not file_id:
            return jsonify({'error': 'Missing file_id parameter'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        filename = data.get('filename', '').strip()
        content = data.get('content', '').strip()
        password = data.get('password', '').strip()
        
        if not filename or not content:
            return jsonify({'error': 'Missing filename or content'}), 400
        
        # Check if file exists
        files_data = load_data()
        if file_id not in files_data:
            return jsonify({'error': 'File not found'}), 404
        
        file_info = files_data[file_id]
        
        # Check password if private
        if file_info['is_private'] and file_info['has_password']:
            passwords_data = load_passwords()
            
            if file_id not in passwords_data or \
               passwords_data[file_id] != hash_password(password):
                return jsonify({'error': 'Invalid password'}), 403
        
        # Sanitize filename
        filename = sanitize_filename(filename)
        
        # Update the file
        save_filename = f"{file_id}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, save_filename)
        
        # Decode and save new file
        try:
            file_content = base64.b64decode(content)
        except:
            return jsonify({'error': 'Invalid file encoding'}), 400
        
        # Remove old file if name changed
        old_file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
        if os.path.exists(old_file_path) and old_file_path != file_path:
            os.remove(old_file_path)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Update metadata
        files_data[file_id] = {
            'original_name': filename,
            'saved_name': save_filename,
            'upload_time': datetime.now().isoformat(),
            'is_private': file_info['is_private'],
            'has_password': file_info['has_password'],
            'size_bytes': len(file_content),
            'updated': True
        }
        
        save_data(files_data)
        
        # Generate URLs
        base_url = request.host_url.rstrip('/')
        
        response = {
            'success': True,
            'message': 'File updated successfully',
            'file_id': file_id,
            'raw_url': f"{base_url}/api/raw?file_id={file_id}",
            'execute_url': f"{base_url}/api/execute?file_id={file_id}"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/status')
def status():
    try:
        files_data = load_data()
        total_files = len(files_data)
        
        public_files = 0
        private_files = 0
        
        for file_info in files_data.values():
            if file_info.get('is_private', False):
                private_files += 1
            else:
                public_files += 1
        
        status_data = {
            'status': 'online',
            'total_files': total_files,
            'public_files': public_files,
            'private_files': private_files,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(status_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Vercel serverless function handler
def handler(request, context):
    # Convert Vercel request to WSGI
    environ = {
        'REQUEST_METHOD': request.method,
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query_string.decode() if request.query_string else '',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'wsgi.url_scheme': 'http',
        'wsgi.input': request.body,
        'CONTENT_TYPE': request.headers.get('content-type', ''),
        'CONTENT_LENGTH': str(len(request.body)) if request.body else '0',
    }
    
    # Add headers
    for key, value in request.headers.items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    # WSGI response
    response_headers = []
    response_body = []
    
    def start_response(status, headers):
        response_headers[:] = [status, headers]
        return response_body.append
    
    # Run Flask app
    result = app(environ, start_response)
    
    # Build response
    status_code = int(response_headers[0].split()[0])
    headers = dict(response_headers[1])
    
    # Combine body chunks
    body = b''.join([chunk if isinstance(chunk, bytes) else chunk.encode() 
                    for chunk in response_body + list(result)])
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': body.decode('utf-8') if isinstance(body, bytes) else body
    }

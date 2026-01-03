from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import hashlib
import uuid
import base64
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
UPLOAD_FOLDER = 'uploads'
PASSWORD_FILE = 'passwords.json'
DATA_FILE = 'files.json'

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Utility functions
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

def get_base_url(headers):
    """Get base URL from headers"""
    host = headers.get('Host', 'localhost:3000')
    proto = headers.get('X-Forwarded-Proto', 'https')
    return f"{proto}://{host}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Route handling
        if path == '/api' or path == '/api/':
            self.handle_upload_page()
        elif path.startswith('/api/raw'):
            self.handle_raw_file(query_params)
        elif path.startswith('/api/execute'):
            self.handle_execute_file(query_params)
        elif path.startswith('/api/upload'):
            self.handle_upload_page()
        else:
            self.handle_upload_page()
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        if path.startswith('/api/upload'):
            self.handle_upload_post()
        elif path.startswith('/api/update'):
            self.handle_update_post(query_params)
        else:
            self.send_error(404, 'Not Found')
    
    def handle_upload_page(self):
        """Render upload page"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>Python Pastebin - Vercel</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            background: #f5f5f5;
            line-height: 1.6;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #333; 
            margin-bottom: 30px;
            text-align: center;
        }
        h2 {
            color: #666;
            margin-top: 30px;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #444;
        }
        input[type="file"], input[type="password"], input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #0070f3;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            margin: 15px 0;
        }
        .checkbox-group input {
            width: auto;
            margin-right: 10px;
        }
        button {
            background: #0070f3;
            color: white;
            border: none;
            padding: 14px 28px;
            font-size: 16px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            transition: background 0.3s;
            width: 100%;
        }
        button:hover {
            background: #0051cc;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #0070f3;
        }
        .url-box {
            background: white;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin: 10px 0;
            word-break: break-all;
            font-family: monospace;
            font-size: 14px;
        }
        .password-required {
            color: #e74c3c;
            font-weight: bold;
            background: #ffeaea;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .update-section {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }
        .info {
            background: #e8f4fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            color: #0366d6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🐍 Python Pastebin on Vercel</h1>
        
        <div class="info">
            <strong>Features:</strong>
            <ul>
                <li>Upload Python files (.py only)</li>
                <li>Password protection for private files</li>
                <li>Direct raw file access</li>
                <li>Execute code directly from browser</li>
                <li>Update files without changing URL</li>
            </ul>
        </div>
        
        <h2>📤 Upload New Python File</h2>
        <form id="uploadForm">
            <div class="form-group">
                <label for="fileInput">Select Python File (.py):</label>
                <input type="file" id="fileInput" accept=".py" required>
            </div>
            
            <div class="checkbox-group">
                <input type="checkbox" id="isPrivate">
                <label for="isPrivate" style="display: inline; margin: 0;">Make Private (Password Protected)</label>
            </div>
            
            <div class="form-group" id="passwordField" style="display: none;">
                <label for="password">Set Password:</label>
                <input type="password" id="password" placeholder="Enter password for private access">
            </div>
            
            <button type="button" onclick="uploadFile()">Upload Python File</button>
        </form>
        
        <div id="result"></div>
        
        <div id="updateSection" class="update-section" style="display: none;">
            <h2>🔄 Update Existing File</h2>
            <div class="form-group">
                <label for="updateFile">Select New Python File:</label>
                <input type="file" id="updateFile" accept=".py">
            </div>
            <div id="updatePasswordField" class="form-group" style="display: none;">
                <label for="updatePassword">Password (required for private files):</label>
                <input type="password" id="updatePassword" placeholder="Enter password">
            </div>
            <button type="button" onclick="updateFile()">Update File</button>
        </div>
    </div>
    
    <script>
        // Show/hide password field
        document.getElementById('isPrivate').addEventListener('change', function() {
            document.getElementById('passwordField').style.display = 
                this.checked ? 'block' : 'none';
        });
        
        let currentFileId = '';
        
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const isPrivate = document.getElementById('isPrivate').checked;
            const password = document.getElementById('password').value;
            
            if (!fileInput.files[0]) {
                alert('Please select a Python file');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Check if Python file
            if (!file.name.endsWith('.py')) {
                alert('Only Python files (.py) are allowed');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = async function(e) {
                const content = e.target.result;
                const base64Content = btoa(unescape(encodeURIComponent(content)));
                
                const data = {
                    filename: file.name,
                    content: base64Content,
                    is_private: isPrivate,
                    password: password
                };
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        currentFileId = result.file_id;
                        
                        const resultHTML = `
                            <div class="result">
                                <h3>✅ Upload Successful!</h3>
                                <p><strong>File ID:</strong> ${result.file_id}</p>
                                <p><strong>Filename:</strong> ${file.name}</p>
                                
                                <p><strong>📄 Raw File URL:</strong></p>
                                <div class="url-box">
                                    <a href="${result.raw_url}" target="_blank">${result.raw_url}</a>
                                </div>
                                
                                <p><strong>🚀 Execute URL:</strong></p>
                                <div class="url-box">
                                    <a href="${result.execute_url}" target="_blank">${result.execute_url}</a>
                                </div>
                                
                                ${result.is_private ? 
                                    '<div class="password-required">🔒 Password Protected: Password required to access</div>' : 
                                    ''
                                }
                                
                                <p><strong>Usage Examples:</strong></p>
                                <div class="url-box">
                                    # Direct access<br>
                                    curl "${result.raw_url}"<br><br>
                                    # Execute code<br>
                                    curl "${result.execute_url}"
                                </div>
                            </div>
                        `;
                        
                        document.getElementById('result').innerHTML = resultHTML;
                        
                        // Show update section
                        document.getElementById('updateSection').style.display = 'block';
                        document.getElementById('updatePasswordField').style.display = 
                            result.is_private ? 'block' : 'none';
                        
                    } else {
                        document.getElementById('result').innerHTML = 
                            `<div style="color: red; padding: 20px; background: #ffeaea; border-radius: 5px;">
                                Error: ${result.error || 'Upload failed'}
                            </div>`;
                    }
                } catch (error) {
                    document.getElementById('result').innerHTML = 
                        `<div style="color: red; padding: 20px; background: #ffeaea; border-radius: 5px;">
                            Network Error: ${error.message}
                        </div>`;
                }
            };
            
            reader.readAsText(file);
        }
        
        async function updateFile() {
            const fileInput = document.getElementById('updateFile');
            const passwordInput = document.getElementById('updatePassword');
            
            if (!fileInput.files[0]) {
                alert('Please select a new Python file');
                return;
            }
            
            if (!currentFileId) {
                alert('No file selected for update');
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
                
                const data = {
                    filename: file.name,
                    content: base64Content,
                    password: passwordInput ? passwordInput.value : ''
                };
                
                try {
                    const response = await fetch(`/api/update?file_id=${currentFileId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        alert('✅ File updated successfully!\nURLs remain the same.');
                    } else {
                        alert(`Error: ${result.error || 'Update failed'}`);
                    }
                } catch (error) {
                    alert(`Network Error: ${error.message}`);
                }
            };
            
            reader.readAsText(file);
        }
    </script>
</body>
</html>'''
        
        self.wfile.write(html.encode())
    
    def handle_raw_file(self, query_params):
        """Handle raw file access"""
        try:
            file_id = query_params.get('file_id', [''])[0]
            password = query_params.get('password', [''])[0]
            
            if not file_id:
                self.send_error(400, 'Missing file_id parameter')
                return
            
            files_data = load_data()
            
            if file_id not in files_data:
                self.send_error(404, 'File not found')
                return
            
            file_info = files_data[file_id]
            
            # Check password if needed
            if file_info['is_private'] and file_info['has_password']:
                if not password:
                    # Show password form
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    base_url = get_base_url(self.headers)
                    html = f'''<!DOCTYPE html>
                    <html>
                    <head>
                        <title>Password Required</title>
                        <style>
                            body {{ font-family: Arial; text-align: center; padding: 50px; }}
                            form {{ max-width: 300px; margin: 0 auto; }}
                            input, button {{ padding: 10px; margin: 5px; width: 100%; }}
                        </style>
                    </head>
                    <body>
                        <h2>🔒 Password Required</h2>
                        <p>This file is password protected.</p>
                        <form method="GET" action="/api/raw">
                            <input type="hidden" name="file_id" value="{file_id}">
                            <input type="password" name="password" placeholder="Enter password" required>
                            <button type="submit">Access File</button>
                        </form>
                        <p style="margin-top: 20px; color: #666;">
                            <small>File ID: {file_id}</small>
                        </p>
                    </body>
                    </html>'''
                    self.wfile.write(html.encode())
                    return
                
                # Verify password
                passwords_data = load_passwords()
                if file_id not in passwords_data or \
                   passwords_data[file_id] != hash_password(password):
                    self.send_error(403, 'Invalid password')
                    return
            
            # Serve the file
            file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode())
            else:
                self.send_error(404, 'File not found')
                
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
    
    def handle_execute_file(self, query_params):
        """Handle code execution"""
        try:
            file_id = query_params.get('file_id', [''])[0]
            password = query_params.get('password', [''])[0]
            
            if not file_id:
                self.send_error(400, 'Missing file_id parameter')
                return
            
            files_data = load_data()
            
            if file_id not in files_data:
                self.send_error(404, 'File not found')
                return
            
            file_info = files_data[file_id]
            
            # Check password if needed
            if file_info['is_private'] and file_info['has_password']:
                if not password:
                    # Show password form
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    base_url = get_base_url(self.headers)
                    html = f'''<!DOCTYPE html>
                    <html>
                    <head>
                        <title>Password Required</title>
                        <style>
                            body {{ font-family: Arial; text-align: center; padding: 50px; }}
                            form {{ max-width: 300px; margin: 0 auto; }}
                            input, button {{ padding: 10px; margin: 5px; width: 100%; }}
                        </style>
                    </head>
                    <body>
                        <h2>🔒 Password Required</h2>
                        <p>This file is password protected.</p>
                        <form method="GET" action="/api/execute">
                            <input type="hidden" name="file_id" value="{file_id}">
                            <input type="password" name="password" placeholder="Enter password" required>
                            <button type="submit">Execute File</button>
                        </form>
                        <p style="margin-top: 20px; color: #666;">
                            <small>File ID: {file_id}</small>
                        </p>
                    </body>
                    </html>'''
                    self.wfile.write(html.encode())
                    return
                
                # Verify password
                passwords_data = load_passwords()
                if file_id not in passwords_data or \
                   passwords_data[file_id] != hash_password(password):
                    self.send_error(403, 'Invalid password')
                    return
            
            # Execute the file
            file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
            
            if os.path.exists(file_path):
                try:
                    # Run Python file
                    result = subprocess.run(
                        ['python', file_path],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding='utf-8'
                    )
                    
                    output = f"""=== Python Code Execution Result ===

Exit Code: {result.returncode}

=== STDOUT ===
{result.stdout}

=== STDERR ===
{result.stderr}

=== File Info ===
File ID: {file_id}
Filename: {file_info['original_name']}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(output.encode())
                    
                except subprocess.TimeoutExpired:
                    output = "Execution timed out (10 seconds limit)"
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(output.encode())
                    
                except Exception as e:
                    output = f"Execution error: {str(e)}"
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(output.encode())
            else:
                self.send_error(404, 'File not found')
                
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
    
    def handle_upload_post(self):
        """Handle file upload"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            filename = data.get('filename', '').strip()
            content = data.get('content', '').strip()
            is_private = data.get('is_private', False)
            password = data.get('password', '').strip()
            
            if not filename or not content:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing filename or content'}).encode())
                return
            
            if not filename.endswith('.py'):
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Only Python files (.py) are allowed'}).encode())
                return
            
            # Generate unique ID
            file_id = generate_file_id()
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Decode and save file
            try:
                file_content = base64.b64decode(content)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            except:
                # Try alternative decoding for text
                file_content = content.encode('utf-8')
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
                'has_password': bool(password and is_private)
            }
            
            if is_private and password:
                passwords_data[file_id] = hash_password(password)
            
            save_data(files_data)
            save_passwords(passwords_data)
            
            # Generate URLs
            base_url = get_base_url(self.headers)
            
            response = {
                'file_id': file_id,
                'filename': filename,
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}",
                'is_private': is_private,
                'has_password': bool(password and is_private),
                'message': 'File uploaded successfully'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Server error: {str(e)}'}).encode())
    
    def handle_update_post(self, query_params):
        """Handle file update"""
        try:
            file_id = query_params.get('file_id', [''])[0]
            
            if not file_id:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing file_id parameter'}).encode())
                return
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            filename = data.get('filename', '').strip()
            content = data.get('content', '').strip()
            password = data.get('password', '').strip()
            
            if not filename or not content:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Missing filename or content'}).encode())
                return
            
            # Check if file exists
            files_data = load_data()
            if file_id not in files_data:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'File not found'}).encode())
                return
            
            file_info = files_data[file_id]
            
            # Check password if private
            if file_info['is_private'] and file_info['has_password']:
                passwords_data = load_passwords()
                
                if file_id not in passwords_data or \
                   passwords_data[file_id] != hash_password(password):
                    self.send_response(403)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Invalid password'}).encode())
                    return
            
            # Update the file
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Remove old file if name changed
            old_file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
            if os.path.exists(old_file_path) and old_file_path != file_path:
                os.remove(old_file_path)
            
            # Save new file
            try:
                file_content = base64.b64decode(content)
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            except:
                file_content = content.encode('utf-8')
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            
            # Update metadata
            files_data[file_id] = {
                'original_name': filename,
                'saved_name': save_filename,
                'upload_time': datetime.now().isoformat(),
                'is_private': file_info['is_private'],
                'has_password': file_info['has_password']
            }
            
            save_data(files_data)
            
            # Generate URLs
            base_url = get_base_url(self.headers)
            
            response = {
                'message': 'File updated successfully',
                'file_id': file_id,
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': f'Server error: {str(e)}'}).encode())

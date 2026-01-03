from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import hashlib
import uuid
import base64
import subprocess
from datetime import datetime
import html

# Configuration
UPLOAD_FOLDER = 'uploads'
PASSWORD_FILE = 'passwords.json'
DATA_FILE = 'files.json'

# Ensure directories exist
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

def get_base_url(headers):
    """Get base URL from headers"""
    host = headers.get('Host', 'localhost:3000')
    proto = headers.get('X-Forwarded-Proto', 'https')
    return f"{proto}://{host}"

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    # Remove directory components
    filename = os.path.basename(filename)
    # Keep only alphanumeric, dots, dashes, underscores
    import re
    filename = re.sub(r'[^\w\.\-]', '_', filename)
    return filename[:100]  # Limit length

class PastebinHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Route handling
        if path in ['/', '/api', '/api/']:
            self.handle_upload_page()
        elif path.startswith('/api/raw'):
            self.handle_raw_file(query_params)
        elif path.startswith('/api/execute'):
            self.handle_execute_file(query_params)
        elif path.startswith('/api/status'):
            self.handle_status()
        else:
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
    
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
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Pastebin - Vercel</title>
    <style>
        :root {
            --primary: #0070f3;
            --primary-dark: #0051cc;
            --danger: #e74c3c;
            --success: #2ecc71;
            --warning: #f39c12;
            --dark: #333;
            --light: #f8f9fa;
            --gray: #6c757d;
        }
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Segoe UI', Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: var(--dark);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        
        .header h1 {
            font-size: 3rem;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: var(--dark);
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid var(--primary);
            display: inline-block;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: var(--dark);
        }
        
        input[type="file"], input[type="password"], input[type="text"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s;
            background: var(--light);
        }
        
        input:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(0,112,243,0.1);
        }
        
        .checkbox-group {
            display: flex;
            align-items: center;
            margin: 20px 0;
        }
        
        .checkbox-group input {
            width: 20px;
            height: 20px;
            margin-right: 10px;
        }
        
        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .btn:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        
        .btn-block {
            width: 100%;
        }
        
        .btn-danger {
            background: var(--danger);
        }
        
        .btn-success {
            background: var(--success);
        }
        
        .result {
            margin-top: 30px;
            padding: 25px;
            background: var(--light);
            border-radius: 10px;
            border-left: 5px solid var(--primary);
        }
        
        .url-box {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #ddd;
            margin: 15px 0;
            word-break: break-all;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
            font-size: 14px;
            position: relative;
        }
        
        .copy-btn {
            position: absolute;
            right: 10px;
            top: 10px;
            background: var(--primary);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .info-box {
            background: #e8f4fd;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            border-left: 5px solid var(--primary);
        }
        
        .info-box ul {
            padding-left: 20px;
            margin: 10px 0;
        }
        
        .info-box li {
            margin-bottom: 8px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            margin-left: 10px;
        }
        
        .status-public {
            background: #d4edda;
            color: #155724;
        }
        
        .status-private {
            background: #f8d7da;
            color: #721c24;
        }
        
        .update-section {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }
        
        .footer {
            text-align: center;
            margin-top: 50px;
            color: white;
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .card {
                padding: 20px;
            }
            
            .url-box {
                font-size: 12px;
            }
        }
        
        .loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
            display: none;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--success);
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 1000;
        }
        
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }
        
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
            color: var(--primary);
        }
        
        .stat-label {
            color: var(--gray);
            font-size: 0.9rem;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐍 Python Pastebin</h1>
            <p>Upload, share, and execute Python code instantly</p>
        </div>
        
        <div class="card">
            <h2>📤 Upload Python File</h2>
            
            <div class="info-box">
                <strong>Features:</strong>
                <ul>
                    <li>🔒 Password protection for private files</li>
                    <li>⚡ Direct execution from browser</li>
                    <li>🔄 Update files without changing URLs</li>
                    <li>🔗 GitHub-like raw file access</li>
                    <li>🚫 No registration required</li>
                </ul>
            </div>
            
            <form id="uploadForm">
                <div class="form-group">
                    <label for="fileInput">Select Python File (.py only):</label>
                    <input type="file" id="fileInput" accept=".py" required>
                </div>
                
                <div class="checkbox-group">
                    <input type="checkbox" id="isPrivate">
                    <label for="isPrivate" style="display: inline; margin: 0; cursor: pointer;">
                        🔒 Make Private (Password Protected)
                    </label>
                </div>
                
                <div class="form-group" id="passwordField" style="display: none;">
                    <label for="password">Password:</label>
                    <input type="password" id="password" placeholder="Enter password for private access">
                </div>
                
                <button type="button" class="btn btn-block" onclick="uploadFile()">
                    📎 Upload Python File
                </button>
            </form>
            
            <div class="loader" id="loader"></div>
            
            <div id="result"></div>
        </div>
        
        <div class="card" id="updateSection" style="display: none;">
            <h2>🔄 Update File</h2>
            <div class="form-group">
                <label for="updateFile">Select New Python File:</label>
                <input type="file" id="updateFile" accept=".py">
            </div>
            <div id="updatePasswordField" class="form-group" style="display: none;">
                <label for="updatePassword">Password (required for private files):</label>
                <input type="password" id="updatePassword" placeholder="Enter password">
            </div>
            <button type="button" class="btn btn-success btn-block" onclick="updateFile()">
                🔄 Update File
            </button>
        </div>
        
        <div class="card" id="statsSection">
            <h2>📊 Stats</h2>
            <div class="stats" id="stats"></div>
        </div>
        
        <div class="footer">
            <p>Python Pastebin on Vercel • <a href="https://github.com" style="color: white;">GitHub</a></p>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
        // Show/hide password field
        document.getElementById('isPrivate').addEventListener('change', function() {
            document.getElementById('passwordField').style.display = 
                this.checked ? 'block' : 'none';
        });
        
        let currentFileId = '';
        let currentFilePrivate = false;
        
        // Show toast notification
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.style.background = type === 'success' ? '#2ecc71' : '#e74c3c';
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
        
        // Copy to clipboard
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('Copied to clipboard!');
            }).catch(err => {
                console.error('Copy failed:', err);
            });
        }
        
        // Load stats
        async function loadStats() {
            try {
                const response = await fetch('/api/status');
                const stats = await response.json();
                
                document.getElementById('stats').innerHTML = `
                    <div class="stat-card">
                        <div class="stat-number">${stats.total_files}</div>
                        <div class="stat-label">Total Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.public_files}</div>
                        <div class="stat-label">Public Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.private_files}</div>
                        <div class="stat-label">Private Files</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">${stats.uptime}</div>
                        <div class="stat-label">Uptime (days)</div>
                    </div>
                `;
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }
        
        // Load stats on page load
        loadStats();
        
        async function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const isPrivate = document.getElementById('isPrivate').checked;
            const password = document.getElementById('password').value;
            const loader = document.getElementById('loader');
            const resultDiv = document.getElementById('result');
            
            if (!fileInput.files[0]) {
                showToast('Please select a Python file', 'error');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Check if Python file
            if (!file.name.endsWith('.py')) {
                showToast('Only Python files (.py) are allowed', 'error');
                return;
            }
            
            // Check file size (4MB limit for Vercel)
            if (file.size > 4 * 1024 * 1024) {
                showToast('File size must be less than 4MB', 'error');
                return;
            }
            
            loader.style.display = 'block';
            resultDiv.innerHTML = '';
            
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
                        currentFilePrivate = result.is_private;
                        
                        const resultHTML = `
                            <div class="result">
                                <h3>✅ Upload Successful!</h3>
                                <p><strong>File ID:</strong> ${result.file_id}</p>
                                <p><strong>Filename:</strong> ${file.name}</p>
                                <p><strong>Status:</strong> 
                                    <span class="status-badge ${result.is_private ? 'status-private' : 'status-public'}">
                                        ${result.is_private ? '🔒 Private' : '🌍 Public'}
                                    </span>
                                </p>
                                
                                <p><strong>📄 Raw File URL:</strong></p>
                                <div class="url-box">
                                    ${result.raw_url}
                                    <button class="copy-btn" onclick="copyToClipboard('${result.raw_url}')">Copy</button>
                                </div>
                                
                                <p><strong>🚀 Execute URL:</strong></p>
                                <div class="url-box">
                                    ${result.execute_url}
                                    <button class="copy-btn" onclick="copyToClipboard('${result.execute_url}')">Copy</button>
                                </div>
                                
                                ${result.is_private ? 
                                    '<div class="info-box">🔒 <strong>Password Protected:</strong> Password required to access this file</div>' : 
                                    ''
                                }
                                
                                <h4>Usage Examples:</h4>
                                <div class="url-box">
                                    <strong>Direct access:</strong><br>
                                    curl "${result.raw_url}"<br><br>
                                    <strong>Execute code:</strong><br>
                                    curl "${result.execute_url}"
                                </div>
                            </div>
                        `;
                        
                        resultDiv.innerHTML = resultHTML;
                        
                        // Show update section
                        document.getElementById('updateSection').style.display = 'block';
                        document.getElementById('updatePasswordField').style.display = 
                            result.is_private ? 'block' : 'none';
                        
                        showToast('File uploaded successfully!');
                        
                        // Reload stats
                        loadStats();
                        
                    } else {
                        resultDiv.innerHTML = 
                            `<div style="color: #e74c3c; padding: 20px; background: #fde8e8; border-radius: 5px;">
                                <strong>Error:</strong> ${result.error || 'Upload failed'}
                            </div>`;
                        showToast('Upload failed', 'error');
                    }
                } catch (error) {
                    resultDiv.innerHTML = 
                        `<div style="color: #e74c3c; padding: 20px; background: #fde8e8; border-radius: 5px;">
                            <strong>Network Error:</strong> ${error.message}
                        </div>`;
                    showToast('Network error', 'error');
                } finally {
                    loader.style.display = 'none';
                }
            };
            
            reader.readAsText(file);
        }
        
        async function updateFile() {
            const fileInput = document.getElementById('updateFile');
            const passwordInput = document.getElementById('updatePassword');
            
            if (!fileInput.files[0]) {
                showToast('Please select a new Python file', 'error');
                return;
            }
            
            if (!currentFileId) {
                showToast('No file selected for update', 'error');
                return;
            }
            
            const file = fileInput.files[0];
            
            if (!file.name.endsWith('.py')) {
                showToast('Only Python files (.py) are allowed', 'error');
                return;
            }
            
            // Check file size
            if (file.size > 4 * 1024 * 1024) {
                showToast('File size must be less than 4MB', 'error');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = async function(e) {
                const content = e.target.result;
                const base64Content = btoa(unescape(encodeURIComponent(content)));
                
                const data = {
                    filename: file.name,
                    content: base64Content,
                    password: currentFilePrivate ? (passwordInput ? passwordInput.value : '') : ''
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
                        showToast('✅ File updated successfully! URLs remain the same.');
                    } else {
                        showToast(`Error: ${result.error || 'Update failed'}`, 'error');
                    }
                } catch (error) {
                    showToast(`Network Error: ${error.message}`, 'error');
                }
            };
            
            reader.readAsText(file);
        }
        
        // Auto-refresh stats every 30 seconds
        setInterval(loadStats, 30000);
    </script>
</body>
</html>'''
        
        self.wfile.write(html_content.encode('utf-8'))
    
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
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    
                    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Password Required - Python Pastebin</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
        }}
        .card {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }}
        .lock-icon {{
            font-size: 50px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #333;
            margin-bottom: 20px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 15px;
            margin: 15px 0;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
        }}
        button {{
            background: #0070f3;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }}
        .file-info {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="lock-icon">🔒</div>
        <h2>Password Required</h2>
        <p>This file is password protected.</p>
        <form method="GET" action="/api/raw">
            <input type="hidden" name="file_id" value="{html.escape(file_id)}">
            <input type="password" name="password" placeholder="Enter password" required autofocus>
            <button type="submit">Access File</button>
        </form>
        <div class="file-info">
            <strong>File ID:</strong> {html.escape(file_id)}<br>
            <strong>Filename:</strong> {html.escape(file_info.get('original_name', 'Unknown'))}
        </div>
    </div>
</body>
</html>'''
                    
                    self.wfile.write(html_content.encode('utf-8'))
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
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
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
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    
                    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Password Required - Python Pastebin</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            margin: 0;
            padding: 20px;
        }}
        .card {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }}
        .execute-icon {{
            font-size: 50px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #333;
            margin-bottom: 20px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 15px;
            margin: 15px 0;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
        }}
        button {{
            background: #f5576c;
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="execute-icon">⚡</div>
        <h2>Password Required</h2>
        <p>Password required to execute this file.</p>
        <form method="GET" action="/api/execute">
            <input type="hidden" name="file_id" value="{html.escape(file_id)}">
            <input type="password" name="password" placeholder="Enter password" required autofocus>
            <button type="submit">Execute File</button>
        </form>
    </div>
</body>
</html>'''
                    
                    self.wfile.write(html_content.encode('utf-8'))
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
                    # Run Python file with timeout
                    result = subprocess.run(
                        ['python', file_path],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding='utf-8'
                    )
                    
                    output = f"""=== Python Code Execution Result ===
File ID: {file_id}
Filename: {file_info['original_name']}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Execution Time: {datetime.now().strftime('%H:%M:%S')}
Status: {'Success' if result.returncode == 0 else f'Failed (Exit Code: {result.returncode})'}

=== STDOUT ===
{result.stdout}

=== STDERR ===
{result.stderr}

=== EXECUTION COMPLETE ===
"""
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(output.encode('utf-8'))
                    
                except subprocess.TimeoutExpired:
                    output = """=== Execution Timeout ===
Error: Execution timed out (10 seconds limit)
This might be due to:
1. Infinite loop in code
2. Long-running operations
3. Network requests
Please optimize your code and try again.
"""
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(output.encode('utf-8'))
                    
                except Exception as e:
                    output = f"""=== Execution Error ===
Error Type: {type(e).__name__}
Error Message: {str(e)}

Possible causes:
1. Syntax error in Python code
2. Missing dependencies
3. Permission issues
4. System limitations

Please check your Python code and try again.
"""
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(output.encode('utf-8'))
            else:
                self.send_error(404, 'File not found')
                
        except Exception as e:
            self.send_error(500, f'Server error: {str(e)}')
    
    def handle_status(self):
        """Handle status endpoint"""
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
            
            # Calculate uptime (simulated)
            import time
            start_time = 1704067200  # Jan 1, 2024
            uptime_days = int((time.time() - start_time) / (24 * 3600))
            
            status_data = {
                'status': 'online',
                'total_files': total_files,
                'public_files': public_files,
                'private_files': private_files,
                'uptime': uptime_days,
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status_data).encode('utf-8'))
            
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
                self.wfile.write(json.dumps({
                    'error': 'Missing filename or content',
                    'code': 'MISSING_FIELDS'
                }).encode('utf-8'))
                return
            
            if not filename.endswith('.py'):
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Only Python files (.py) are allowed',
                    'code': 'INVALID_FILE_TYPE'
                }).encode('utf-8'))
                return
            
            # Sanitize filename
            filename = sanitize_filename(filename)
            
            # Check content size (approx 4MB limit)
            if len(content) > 4 * 1024 * 1024 * 1.33:  # Base64 overhead
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'File size must be less than 4MB',
                    'code': 'FILE_TOO_LARGE'
                }).encode('utf-8'))
                return
            
            # Generate unique ID
            file_id = generate_file_id()
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Decode and save file
            try:
                file_content = base64.b64decode(content)
            except:
                # Try alternative decoding
                try:
                    import base64
                    file_content = base64.b64decode(content + '=' * (-len(content) % 4))
                except:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': 'Invalid file content encoding',
                        'code': 'INVALID_ENCODING'
                    }).encode('utf-8'))
                    return
            
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
            
            # Generate URLs
            base_url = get_base_url(self.headers)
            
            response = {
                'success': True,
                'file_id': file_id,
                'filename': filename,
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}",
                'is_private': is_private,
                'has_password': bool(password and is_private),
                'size_bytes': len(file_content),
                'upload_time': datetime.now().isoformat(),
                'message': 'File uploaded successfully'
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': f'Server error: {str(e)}',
                'code': 'SERVER_ERROR'
            }).encode('utf-8'))
    
    def handle_update_post(self, query_params):
        """Handle file update"""
        try:
            file_id = query_params.get('file_id', [''])[0]
            
            if not file_id:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'Missing file_id parameter',
                    'code': 'MISSING_FILE_ID'
                }).encode('utf-8'))
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
                self.wfile.write(json.dumps({
                    'error': 'Missing filename or content',
                    'code': 'MISSING_FIELDS'
                }).encode('utf-8'))
                return
            
            # Check if file exists
            files_data = load_data()
            if file_id not in files_data:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': 'File not found',
                    'code': 'FILE_NOT_FOUND'
                }).encode('utf-8'))
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
                    self.wfile.write(json.dumps({
                        'error': 'Invalid password',
                        'code': 'INVALID_PASSWORD'
                    }).encode('utf-8'))
                    return
            
            # Sanitize filename
            filename = sanitize_filename(filename)
            
            # Update the file
            save_filename = f"{file_id}_{filename}"
            file_path = os.path.join(UPLOAD_FOLDER, save_filename)
            
            # Remove old file if name changed
            old_file_path = os.path.join(UPLOAD_FOLDER, file_info['saved_name'])
            if os.path.exists(old_file_path) and old_file_path != file_path:
                os.remove(old_file_path)
            
            # Decode and save new file
            try:
                file_content = base64.b64decode(content)
            except:
                try:
                    import base64
                    file_content = base64.b64decode(content + '=' * (-len(content) % 4))
                except:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'error': 'Invalid file content encoding',
                        'code': 'INVALID_ENCODING'
                    }).encode('utf-8'))
                    return
            
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
            base_url = get_base_url(self.headers)
            
            response = {
                'success': True,
                'message': 'File updated successfully',
                'file_id': file_id,
                'raw_url': f"{base_url}/api/raw?file_id={file_id}",
                'execute_url': f"{base_url}/api/execute?file_id={file_id}",
                'update_time': datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': f'Server error: {str(e)}',
                'code': 'SERVER_ERROR'
            }).encode('utf-8'))

def handler(request, context):
    """Vercel serverless function handler"""
    return PastebinHandler()
